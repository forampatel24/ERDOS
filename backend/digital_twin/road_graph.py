"""Road network graph construction and querying.

The :class:`RoadGraph` maintains road segments and their endpoint nodes and
supports routing over them. It works in pure Python (dict/heap based) without
external dependencies; ``networkx`` is imported lazily and only used to expose
a real ``networkx.DiGraph`` to consumers (for example the ST-GNN prediction
module) via :meth:`RoadGraph.build_graph`.
"""

from __future__ import annotations

import heapq
import math
from typing import Any, Callable, Dict, List, Set, Tuple

from backend.models.road import Road
from backend.utils.logging import get_logger

logger = get_logger("digital_twin.road_graph")

#: A ``(latitude, longitude)`` coordinate pair.
LatLon = Tuple[float, float]

#: Signature of a function mapping a road to a non-negative traversal cost.
WeightFn = Callable[[Road], float]


def _coordinate_node_id(point: LatLon) -> str:
    """Build a stable node id from a coordinate pair."""
    return f"{point[0]:.6f},{point[1]:.6f}"


class _PureDiGraph:
    """Minimal directed graph used when ``networkx`` is not installed.

    Implements the small subset of the ``networkx.DiGraph`` interface that
    ERDOS consumers rely on (nodes, edges, predecessors, successors) so that
    downstream modules keep working without an optional dependency.
    """

    def __init__(self) -> None:
        self._node_attrs: Dict[Any, Dict[str, Any]] = {}
        self._adj: Dict[Any, Dict[Any, Dict[str, Any]]] = {}

    def add_node(self, node: Any, **attr: Any) -> None:
        """Add a node with optional attributes."""
        self._node_attrs.setdefault(node, {}).update(attr)
        self._adj.setdefault(node, {})

    def add_edge(self, u: Any, v: Any, **attr: Any) -> None:
        """Add a directed edge ``u -> v`` with optional attributes."""
        self.add_node(u)
        self.add_node(v)
        self._adj[u][v] = attr

    @property
    def nodes(self) -> List[Any]:
        """List of node identifiers."""
        return list(self._node_attrs.keys())

    @property
    def edges(self) -> List[Tuple[Any, Any, Dict[str, Any]]]:
        """List of ``(u, v, attrs)`` tuples for every directed edge."""
        return [
            (u, v, dict(attrs))
            for u, neighbours in self._adj.items()
            for v, attrs in neighbours.items()
        ]

    def successors(self, node: Any) -> List[Any]:
        """List of nodes reachable from ``node`` via one directed edge."""
        return list(self._adj.get(node, {}).keys())

    def predecessors(self, node: Any) -> List[Any]:
        """List of nodes with a directed edge into ``node``."""
        return [u for u, neighbours in self._adj.items() if node in neighbours]


class RoadGraph:
    """Holds road segments and their endpoint nodes for routing queries."""

    def __init__(self) -> None:
        self._roads: Dict[str, Road] = {}
        #: node_id -> (lat, lon)
        self._nodes: Dict[str, LatLon] = {}
        #: node_id -> set of road ids incident to the node
        self._node_roads: Dict[str, Set[str]] = {}
        #: node_id -> {neighbour_node_id: road_id} (bidirectional adjacency)
        self._node_edges: Dict[str, Dict[str, str]] = {}

    # ------------------------------------------------------------------ setup

    def add_node(self, node_id: str, lat: float, lon: float) -> None:
        """Register a routing node with its coordinates."""
        self._nodes[node_id] = (float(lat), float(lon))
        self._node_edges.setdefault(node_id, {})
        self._node_roads.setdefault(node_id, set())

    def add_road(self, road: Road) -> None:
        """Register a road segment and link its endpoints into the graph.

        If the road does not declare ``start_node``/``end_node`` they are
        derived from the geometry endpoints using stable coordinate node ids,
        so roads sharing endpoints automatically share nodes.
        """
        self._roads[road.road_id] = road
        self._ensure_nodes_for_road(road)
        self._link_road(road)

    def _ensure_nodes_for_road(self, road: Road) -> None:
        """Make sure the road's endpoint nodes exist in the node registry."""
        start, end = road.start_node, road.end_node
        if road.geometry:
            first = road.geometry[0]
            last = road.geometry[-1]
            if start is None:
                start = road.start_node = _coordinate_node_id(first)
            if end is None:
                end = road.end_node = _coordinate_node_id(last)
            self.add_node(start, first[0], first[1])
            self.add_node(end, last[0], last[1])
        else:
            if start is not None and start not in self._nodes:
                self.add_node(start, 0.0, 0.0)
            if end is not None and end not in self._nodes:
                self.add_node(end, 0.0, 0.0)

    def _link_road(self, road: Road) -> None:
        """Connect the road's endpoints in the adjacency structures."""
        start, end = road.start_node, road.end_node
        if start and start not in self._node_roads:
            self._node_roads.setdefault(start, set())
            self._node_edges.setdefault(start, {})
        if end and end not in self._node_roads:
            self._node_roads.setdefault(end, set())
            self._node_edges.setdefault(end, {})
        if start and end and start != end:
            self._node_roads[start].add(road.road_id)
            self._node_roads[end].add(road.road_id)
            self._node_edges[start][end] = road.road_id
            self._node_edges[end][start] = road.road_id
        elif start == end:
            logger.warning(
                "Road {} is a self-loop; not linked for routing", road.road_id
            )

    # ------------------------------------------------------------- querying

    def nodes_for_routing(self) -> List[str]:
        """Return node ids that are endpoints of at least one road."""
        return sorted({node for node, roads in self._node_roads.items() if roads})

    def neighbors_of(self, road_id: str) -> List[str]:
        """Return road ids sharing a node with the given road."""
        road = self._roads.get(road_id)
        if road is None:
            raise KeyError(f"Road '{road_id}' not found")
        neighbours: Set[str] = set()
        for node in (road.start_node, road.end_node):
            if node is None:
                continue
            neighbours.update(self._node_roads.get(node, set()))
        neighbours.discard(road_id)
        return sorted(neighbours)

    def build_graph(self) -> Any:
        """Build a copy of the network as a graph object.

        Returns a :class:`networkx.DiGraph` when networkx is installed; falls
        back to a pure-Python :class:`_PureDiGraph` otherwise. Edges are
        bidirectional so both travel directions are routable; each edge carries
        the traversed ``road_id``.
        """
        try:
            import networkx as nx  # lazy optional dependency
        except ImportError:
            logger.debug(
                "networkx is not installed; returning pure-python graph fallback"
            )
            return self._build_pure_graph()

        graph: Any = nx.DiGraph()
        for node_id, (lat, lon) in self._nodes.items():
            graph.add_node(node_id, lat=lat, lon=lon)
        for road in self._roads.values():
            start, end = road.start_node, road.end_node
            if not start or not end or start == end:
                continue
            attrs: Dict[str, Any] = {
                "road_id": road.road_id,
                "road_name": road.road_name,
                "length_m": road.length_m,
                "weight": 1.0,
            }
            graph.add_edge(start, end, **attrs)
            graph.add_edge(end, start, **attrs)
        return graph

    def _build_pure_graph(self) -> _PureDiGraph:
        """Build the pure-Python graph fallback."""
        graph = _PureDiGraph()
        for node_id, (lat, lon) in self._nodes.items():
            graph.add_node(node_id, lat=lat, lon=lon)
        for road in self._roads.values():
            start, end = road.start_node, road.end_node
            if not start or not end or start == end:
                continue
            attrs: Dict[str, Any] = {
                "road_id": road.road_id,
                "road_name": road.road_name,
                "length_m": road.length_m,
            }
            graph.add_edge(start, end, **attrs)
            graph.add_edge(end, start, **attrs)
        return graph

    # -------------------------------------------------------------- routing

    def shortest_path(
        self,
        origin: str,
        destination: str,
        weight_fn: WeightFn,
    ) -> List[str]:
        """Return the road ids along the lowest-cost path between two nodes.

        ``origin`` and ``destination`` are node ids (see
        :meth:`nodes_for_routing`). ``weight_fn`` maps a :class:`Road` to a
        non-negative traversal cost. Returns an empty list when either node is
        unknown or no path exists. Implemented with a pure-Python Dijkstra so
        routing always works, even without ``networkx``.
        """
        if origin not in self._node_edges or destination not in self._node_edges:
            return []
        if origin == destination:
            return []

        distances: Dict[str, float] = {origin: 0.0}
        prev_node: Dict[str, str] = {}
        prev_road: Dict[str, str] = {}
        visited: Set[str] = set()
        heap: List[Tuple[float, str]] = [(0.0, origin)]

        while heap:
            cost, node = heapq.heappop(heap)
            if node in visited:
                continue
            visited.add(node)
            if node == destination:
                break
            for neighbour, road_id in self._node_edges[node].items():
                road = self._roads.get(road_id)
                if road is None:
                    continue
                weight = max(0.0, float(weight_fn(road)))
                new_cost = cost + weight
                if new_cost < distances.get(neighbour, math.inf):
                    distances[neighbour] = new_cost
                    prev_node[neighbour] = node
                    prev_road[neighbour] = road_id
                    heapq.heappush(heap, (new_cost, neighbour))

        if destination not in visited:
            return []

        road_ids: List[str] = []
        node = destination
        while node != origin:
            road_id = prev_road.get(node)
            if road_id is None:
                return []
            road_ids.append(road_id)
            node = prev_node.get(node, origin)
        road_ids.reverse()
        return road_ids