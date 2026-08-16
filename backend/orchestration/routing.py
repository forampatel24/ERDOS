"""Risk-aware route planning over the digital twin road network.

The :class:`RoutePlanner` builds a road graph from a digital-twin snapshot and
computes routes that minimise travel time weighted by flood risk. Road segments
whose status is ``BLOCKED`` are excluded from routing; roads under
``HIGH_RISK``/``MODERATE_RISK`` incur a risk penalty proportional to their
predicted flood probability.

Routing is pure Python (Dijkstra over the twin's :class:`RoadGraph`), so it
works without ``networkx`` or ``ortools`` installed.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Union

from backend.digital_twin.road_graph import RoadGraph
from backend.digital_twin.state_manager import get_state_manager
from backend.models.road import Road
from backend.utils.geometry import approx_distance_km
from backend.utils.logging import get_logger
from config.constants import DEFAULT_LATITUDE, DEFAULT_LONGITUDE, RoadStatus

logger = get_logger("orchestration.routing")

#: Traversal cost for a blocked road (effectively infinite).
INF = float(1e9)
#: Flood probability above which a road counts as a predicted blockage.
BLOCK_THRESHOLD = 0.85
#: Risk multiplier applied per unit of predicted flood probability.
FLOOD_RISK_PENALTY = 4.0
#: Additional multiplier for roads already under high/moderate risk.
HIGH_RISK_MULTIPLIER = 2.0
MODERATE_RISK_MULTIPLIER = 1.4
#: Assumed vehicle speed for travel-time estimates (km/h).
DEFAULT_SPEED_KMH = 40.0

#: A point as ``(lat, lon)``.
LatLon = Tuple[float, float]

#: Origin/destination accepted by the planner: a graph node id, a road id, a
#: shelter/hospital id or name, a coordinate pair, or ``None`` for the default
#: location.
RoutePoint = Union[str, LatLon, Sequence[float], None]


def _point_to_latlon(point: RoutePoint) -> LatLon:
    """Coerce a route point into a ``(lat, lon)`` pair.

    ``None`` resolves to the default Kochi location. A 2-element sequence is
    treated as ``(lat, lon)`` (mirroring the twin's geometry convention).
    """
    if point is None:
        return (DEFAULT_LATITUDE, DEFAULT_LONGITUDE)
    if isinstance(point, str):
        # Node ids are serialised as "<lat>,<lon>".
        if "," in point:
            parts = point.split(",")
            return (float(parts[0]), float(parts[1]))
        raise ValueError(f"Cannot resolve string route point '{point}' to lat/lon")
    seq = list(point)
    if len(seq) != 2:
        raise ValueError(f"Route point must be (lat, lon), got {point!r}")
    return (float(seq[0]), float(seq[1]))


class RoutePlanner:
    """Plans flood-risk-aware routes over the digital twin road graph."""

    def __init__(self, snapshot: Optional[Dict[str, Any]] = None) -> None:
        self._cached_snapshot = snapshot
        self._node_coords: Dict[str, LatLon] = {}

    # ------------------------------------------------------------ graph build

    def _snapshot(self) -> Dict[str, Any]:
        """Return the snapshot used by this planner (fresh if not supplied)."""
        if self._cached_snapshot is None:
            self._cached_snapshot = get_state_manager().get_snapshot()
        return self._cached_snapshot

    def build_graph(self, snapshot: Optional[Dict[str, Any]] = None) -> RoadGraph:
        """Build a :class:`RoadGraph` from the twin's roads."""
        data = snapshot or self._snapshot()
        graph = RoadGraph()
        self._node_coords.clear()
        roads = data.get("roads") or {}
        for road_id, road_data in roads.items():
            road = _road_from_data(road_id, road_data)
            graph.add_road(road)
            geometry = road.geometry
            if geometry:
                if road.start_node:
                    self._node_coords.setdefault(
                        road.start_node,
                        (float(geometry[0][0]), float(geometry[0][1])),
                    )
                if road.end_node:
                    self._node_coords.setdefault(
                        road.end_node,
                        (float(geometry[-1][0]), float(geometry[-1][1])),
                    )
        return graph

    # ------------------------------------------------------------ resolution

    def resolve_node(
        self, graph: RoadGraph, point: RoutePoint
    ) -> Optional[str]:
        """Resolve a route point to a graph node id (nearest if not a node).

        ``point`` may be a node id (``"<lat>,<lon>"``), a road id, a
        shelter/hospital id or name, or a coordinate pair. Returns ``None`` when
        the graph is empty.
        """
        data = self._snapshot()
        nodes = graph.nodes_for_routing()
        if not nodes:
            return None

        # Explicit node id.
        if isinstance(point, str) and point in nodes:
            return point

        # Road id -> its start node.
        if isinstance(point, str):
            roads = data.get("roads") or {}
            if point in roads:
                road = _road_from_data(point, roads[point])
                if road.start_node:
                    return road.start_node if road.start_node in nodes else None

        # Shelter / hospital id or name.
        latlon = _resolve_named_location(data, point)
        if latlon is None:
            try:
                latlon = _point_to_latlon(point)
            except ValueError:
                # An unresolvable string (e.g. a node id that no longer exists
                # in the graph) is treated as an unknown location.
                return None

        return _nearest_node(nodes, self._node_coords, latlon)

    # ------------------------------------------------------------ weighting

    def _edge_weight(self, road: Road) -> float:
        """Return the risk-weighted traversal cost for one road segment."""
        if road.status == RoadStatus.BLOCKED:
            return INF
        length = max(1.0, road.length_m)
        flood = max(0.0, min(1.0, road.flood_probability))
        risk = 1.0 + FLOOD_RISK_PENALTY * flood
        if road.status == RoadStatus.HIGH_RISK:
            risk *= HIGH_RISK_MULTIPLIER
        elif road.status == RoadStatus.MODERATE_RISK:
            risk *= MODERATE_RISK_MULTIPLIER
        return length * risk

    def _road_weight_fn(self) -> Callable[[Road], float]:
        return self._edge_weight

    # -------------------------------------------------------------- planning

    def safest_route(
        self,
        origin: RoutePoint,
        destination: RoutePoint,
        snapshot: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Compute the lowest-risk route between two points.

        Returns a dict with ``route`` (ordered road ids), ``estimated_minutes``,
        ``total_risk`` and ``predicted_blockages``. An empty ``route`` means no
        safe path exists (all roads blocked / disconnected).
        """
        data = snapshot or self._snapshot()
        graph = self.build_graph(data)
        start = self.resolve_node(graph, origin)
        end = self.resolve_node(graph, destination)
        if start is None or end is None:
            return {
                "route": [],
                "estimated_minutes": 0.0,
                "total_risk": 0.0,
                "predicted_blockages": [],
            }
        if start == end:
            return {
                "route": [],
                "estimated_minutes": 0.0,
                "total_risk": 0.0,
                "predicted_blockages": [],
            }

        route = graph.shortest_path(start, end, self._road_weight_fn())
        return self._summarise_route(route, data)

    def alternate_routes(
        self,
        origin: RoutePoint,
        destination: RoutePoint,
        k: int = 3,
        snapshot: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Return up to ``k`` distinct safe-ish routes (successive exclusion).

        Each successive route avoids the edge that made the previous one risky,
        producing alternatives rather than exact k-shortest paths.
        """
        data = snapshot or self._snapshot()
        graph = self.build_graph(data)
        start = self.resolve_node(graph, origin)
        end = self.resolve_node(graph, destination)
        if start is None or end is None:
            return []

        results: List[Dict[str, Any]] = []
        avoided_roads: List[str] = []

        def restricted_weight(road: Road) -> float:
            if road.road_id in avoided_roads:
                return INF
            return self._edge_weight(road)

        for _ in range(max(1, k)):
            route = graph.shortest_path(start, end, restricted_weight)
            if not route:
                break
            summary = self._summarise_route(route, data)
            results.append(summary)
            # Block the riskiest traversed road to force a different path.
            if len(route) == 1:
                break
            avoided_roads.append(
                max(route, key=lambda rid: _flood_of(data, rid))
            )
        return results

    def is_route_safe(
        self,
        route: Sequence[str],
        snapshot: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Return ``True`` when no road on the route is blocked or predicted to flood."""
        data = snapshot or self._snapshot()
        roads = data.get("roads") or {}
        for road_id in route:
            road = _road_from_data(road_id, roads.get(road_id, {}))
            if road.status == RoadStatus.BLOCKED:
                return False
            if road.flood_probability >= BLOCK_THRESHOLD:
                return False
        return True

    # -------------------------------------------------------------- helpers

    def _summarise_route(
        self, route: List[str], data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Convert a road-id list into the documented route summary."""
        if not route:
            return {
                "route": [],
                "estimated_minutes": 0.0,
                "total_risk": 0.0,
                "predicted_blockages": [],
            }

        total_length = 0.0
        total_risk = 0.0
        blockages: List[str] = []
        roads = data.get("roads") or {}
        for road_id in route:
            road = _road_from_data(road_id, roads.get(road_id, {}))
            total_length += max(0.0, road.length_m)
            total_risk += road.flood_probability
            if road.flood_probability >= BLOCK_THRESHOLD:
                blockages.append(road_id)

        speed_kmh = max(1.0, DEFAULT_SPEED_KMH)
        minutes = total_length / (speed_kmh * 1000.0 / 60.0)
        return {
            "route": route,
            "estimated_minutes": round(minutes, 1),
            "total_risk": round(total_risk, 4),
            "predicted_blockages": blockages,
        }


# --------------------------------------------------------------------------- #
# Module-level helpers (shared by evacuation / replanning).
# --------------------------------------------------------------------------- #

def _road_from_data(road_id: str, data: Dict[str, Any]) -> Road:
    """Rehydrate a Road model from a snapshot dict entry."""
    payload = dict(data)
    payload.setdefault("road_id", road_id)
    if "status" in payload and payload["status"] is not None:
        try:
            payload["status"] = RoadStatus(payload["status"])
        except ValueError:
            payload["status"] = RoadStatus.SAFE
    return Road(**payload)


def _flood_of(data: Dict[str, Any], road_id: str) -> float:
    """Return the flood probability recorded for ``road_id`` in a snapshot."""
    roads = data.get("roads") or {}
    road = roads.get(road_id) or {}
    try:
        return float(road.get("flood_probability", 0.0))
    except (TypeError, ValueError):
        return 0.0


def _resolve_named_location(
    data: Dict[str, Any], point: RoutePoint
) -> Optional[LatLon]:
    """Resolve a shelter/hospital id or name to a ``(lat, lon)`` pair."""
    if not isinstance(point, str):
        return None
    for key in ("shelters", "hospitals"):
        entities = data.get(key) or {}
        for entity_id, entity in entities.items():
            if entity_id == point or entity.get("name") == point:
                geometry = entity.get("geometry") or []
                if geometry:
                    first = geometry[0]
                    return (float(first[0]), float(first[1]))
    return None


def _nearest_node(
    node_ids: List[str], coords: Dict[str, LatLon], latlon: LatLon
) -> Optional[str]:
    """Return the node id in ``coords`` closest to ``latlon`` (haversine)."""
    best: Optional[str] = None
    best_dist = float("inf")
    for node_id in node_ids:
        point = coords.get(node_id)
        if point is None:
            continue
        dist = approx_distance_km(
            latlon[0], latlon[1], float(point[0]), float(point[1])
        )
        if dist < best_dist:
            best_dist = dist
            best = node_id
    return best