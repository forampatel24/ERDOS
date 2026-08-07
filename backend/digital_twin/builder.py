"""Builds the initial Digital Twin from static GIS datasets and defaults.

The :class:`DigitalTwinBuilder` ingests static GeoJSON, optionally fetches the
road network from OpenStreetMap, assigns elevation from a DEM, registers a
small in-memory default infrastructure set for local/development operation and
returns a populated :class:`StateManager`.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union

from backend.digital_twin.infrastructure import InfrastructureManager
from backend.digital_twin.road_graph import RoadGraph
from backend.digital_twin.state_manager import StateManager, get_state_manager
from backend.models.bridge import Bridge
from backend.models.hospital import Hospital
from backend.models.resource import Resource
from backend.models.road import Road
from backend.models.shelter import Shelter
from backend.utils.logging import get_logger
from config.constants import (
    DEFAULT_LOCATION,
    DEFAULT_STATE,
    InfrastructureStatus,
    ResourceStatus,
    ResourceType,
)

logger = get_logger("digital_twin.builder")

PathLike = Union[str, Path]


def _representative_point(geometry: list[tuple[float, float]]) -> Tuple[float, float]:
    """Return the midpoint of a polyline geometry as a ``(lat, lon)`` point."""
    if not geometry:
        return DEFAULT_LOCATION
    first, last = geometry[0], geometry[-1]
    return ((first[0] + last[0]) / 2.0, (first[1] + last[1]) / 2.0)


class DigitalTwinBuilder:
    """Assembles the digital twin and returns the populated state manager."""

    def __init__(self, state_manager: Optional[StateManager] = None) -> None:
        self.state_manager = state_manager or get_state_manager()
        self.infrastructure = InfrastructureManager(self.state_manager)
        self.road_graph = RoadGraph()
        self._default_loaded = False

    # ------------------------------------------------------------ static GIS

    def load_static(self, geojson_path: PathLike) -> "DigitalTwinBuilder":
        """Load roads and infrastructure from a GeoJSON FeatureCollection.

        LineString features become :class:`Road` objects; Point features become
        hospitals, shelters or bridges based on their ``kind``/``entity_type``
        property. Coordinates are converted from GeoJSON ``[lon, lat]`` order
        to the ``(lat, lon)`` order used by the domain models.
        """
        path = Path(geojson_path)
        if not path.exists():
            raise FileNotFoundError(f"GeoJSON file not found: {path}")
        with path.open("r", encoding="utf-8") as handle:
            data: Any = json.load(handle)

        features = data.get("features", []) if isinstance(data, dict) else []
        for feature in features:
            self._ingest_feature(feature)
        logger.info("Loaded {} features from {}", len(features), path)
        return self

    def _ingest_feature(self, feature: Dict[str, Any]) -> None:
        geometry = feature.get("geometry") or {}
        properties = feature.get("properties") or {}
        geometry_type = geometry.get("type")
        coordinates = geometry.get("coordinates") or []

        if geometry_type == "LineString":
            self._ingest_road(properties, coordinates)
        elif geometry_type == "Point":
            self._ingest_point(properties, coordinates)

    def _ingest_road(self, properties: Dict[str, Any], coordinates: list) -> None:
        geometry = [(lat, lon) for lon, lat in coordinates]
        road_id = str(
            properties.get("road_id")
            or properties.get("id")
            or f"R{len(self.state_manager.roads) + 1:03d}"
        )
        road = Road(
            road_id=road_id,
            road_name=str(properties.get("name") or properties.get("road_name") or road_id),
            road_type=str(properties.get("road_type", "UNCLASSIFIED")),
            lanes=int(properties.get("lanes", 2)),
            length_m=float(properties.get("length_m", 0.0)),
            elevation_m=float(properties.get("elevation", 0.0)),
            distance_to_river_m=float(properties.get("distance_to_river_m", 0.0)),
            geometry=geometry,
        )
        self.state_manager.add_road(road)
        self.road_graph.add_road(road)

    def _ingest_point(self, properties: Dict[str, Any], coordinates: list) -> None:
        if not coordinates:
            return
        lon, lat = coordinates[0], coordinates[1]
        geometry = [(float(lat), float(lon))]
        kind = str(properties.get("kind") or properties.get("entity_type") or "").lower()
        identifier = str(
            properties.get("id")
            or properties.get("name")
            or f"{kind.upper()}{len(self.state_manager.shelters) + len(self.state_manager.hospitals) + len(self.state_manager.bridges) + 1:03d}"
        )
        name = str(properties.get("name") or identifier)

        if kind == "hospital":
            self.infrastructure.register(
                Hospital(
                    hospital_id=identifier,
                    name=name,
                    geometry=geometry,
                    capacity=int(properties.get("capacity", 0)),
                    occupancy=int(properties.get("occupancy", 0)),
                )
            )
        elif kind == "shelter":
            self.infrastructure.register(
                Shelter(
                    shelter_id=identifier,
                    name=name,
                    geometry=geometry,
                    capacity=int(properties.get("capacity", 0)),
                    occupancy=int(properties.get("occupancy", 0)),
                )
            )
        elif kind == "bridge":
            self.infrastructure.register(
                Bridge(
                    bridge_id=identifier,
                    geometry=geometry,
                    road_id=properties.get("road_id"),
                )
            )
        else:
            logger.debug("Skipping unsupported Point feature: {}", kind)

    # ---------------------------------------------------------------- OSM

    def fetch_osm(self, place: str = "Kerala, India") -> "DigitalTwinBuilder":
        """Fetch the drive road network for ``place`` from OpenStreetMap.

        Requires ``osmnx`` (not installed by default). Raises
        :class:`RuntimeError` when osmnx is unavailable. Use
        :meth:`register_default_infrastructure` for local development instead.
        """
        try:
            import osmnx as ox  # lazy optional dependency
        except ImportError as exc:
            raise RuntimeError(
                "osmnx is not installed. Run 'pip install osmnx' to fetch roads "
                "from OpenStreetMap, or call register_default_infrastructure() "
                "for local/development operation."
            ) from exc

        graph = ox.graph_from_place(place, network_type="drive")
        for node_id, data in graph.nodes(data=True):
            self.road_graph.add_node(str(node_id), float(data["y"]), float(data["x"]))
        for start, end, data in graph.edges(data=True):
            raw_id = data.get("osmid")
            road_id = raw_id if isinstance(raw_id, str) else str(raw_id)
            road_name = str(data.get("name", road_id))
            geometry = self._osm_geometry(data, graph, start, end)
            road = Road(
                road_id=road_id,
                road_name=road_name,
                road_type=str(data.get("highway", "UNCLASSIFIED")),
                lanes=int(data.get("lanes", 2) or 2),
                length_m=float(data.get("length", 0.0)),
                start_node=str(start),
                end_node=str(end),
                geometry=geometry,
            )
            self.state_manager.add_road(road)
            self.road_graph.add_road(road)
        logger.info("Fetched OSM road network for '{}'", place)
        return self

    @staticmethod
    def _osm_geometry(data: Dict[str, Any], graph: Any, start: Any, end: Any) -> list:
        """Extract a polyline geometry for an OSM edge.

        Uses the linestring embedded in the edge when available, otherwise
        builds a two-point line from the endpoint node coordinates.
        """
        embedded = data.get("geometry")
        if embedded is not None:
            try:
                return [(float(lat), float(lon)) for lon, lat in embedded.coords]
            except (AttributeError, TypeError):
                pass
        start_lat = float(graph.nodes[start]["y"])
        start_lon = float(graph.nodes[start]["x"])
        end_lat = float(graph.nodes[end]["y"])
        end_lon = float(graph.nodes[end]["x"])
        return [(start_lat, start_lon), (end_lat, end_lon)]

    # -------------------------------------------------------------- elevation

    def assign_elevation(self, dem_path: Optional[PathLike] = None) -> "DigitalTwinBuilder":
        """Assign elevation to roads from a DEM raster if available.

        Requires ``rasterio`` and a DEM file. When either is missing this is a
        no-op placeholder that keeps the default road elevations.
        """
        try:
            import rasterio  # lazy optional dependency
        except ImportError:
            logger.info("rasterio not installed; keeping default elevations")
            return self

        if dem_path is None:
            dem_path = Path("datasets") / "static" / "dem.tif"
        path = Path(dem_path)
        if not path.exists():
            logger.info("No DEM found at {}; keeping default elevations", path)
            return self

        with rasterio.open(path) as dataset:
            for road in self.state_manager.roads.values():
                lat, lon = _representative_point(road.geometry)
                try:
                    row, col = dataset.index(lon, lat)
                    value = float(dataset.read(1, window=((row, row + 1), (col, col + 1)))[0, 0])
                    road.elevation_m = value
                except Exception:  # noqa: BLE001 - skip out-of-bounds samples
                    logger.debug("No elevation sample for road {}", road.road_id)
        logger.info("Assigned elevations from {}", path)
        return self

    # ------------------------------------------------------------- road graph

    def build_road_graph(self) -> RoadGraph:
        """Build the road graph from the roads held in the state manager."""
        for road in self.state_manager.roads.values():
            self.road_graph.add_road(road)
        logger.info("Road graph built with {} roads", len(self.state_manager.roads))
        return self.road_graph

    # ---------------------------------------------------------------- defaults

    def register_default_infrastructure(self) -> "DigitalTwinBuilder":
        """Register an in-memory default infrastructure set for local operation.

        Adds a small connected road grid plus sample shelters, hospitals,
        bridges and resources around the default location (Kochi, Kerala). The
        operation is idempotent.
        """
        if self._default_loaded:
            return self
        self._default_loaded = True

        roads = _default_roads()
        for road in roads:
            self.state_manager.add_road(road)
            self.road_graph.add_road(road)

        for shelter in _default_shelters():
            self.infrastructure.register(shelter)
        for hospital in _default_hospitals():
            self.infrastructure.register(hospital)
        for bridge in _default_bridges():
            self.infrastructure.register(bridge)
        for resource in _default_resources():
            self.state_manager.update_resource(resource)

        logger.info(
            "Registered default infrastructure for {} at ({:.4f}, {:.4f})",
            DEFAULT_STATE, DEFAULT_LOCATION[0], DEFAULT_LOCATION[1],
        )
        return self

    # ------------------------------------------------------------------ build

    def build(self) -> StateManager:
        """Populate the singleton state manager and return it.

        Ensures the default infrastructure is registered and the road graph is
        built, then returns the fully populated :class:`StateManager`.
        """
        self.register_default_infrastructure()
        self.build_road_graph()
        return self.state_manager


# ---------------------------------------------------------------- defaults

def _default_roads() -> list[Road]:
    """Return the default connected road grid around Kochi, Kerala.

    Grid layout::

        N10 ---- R003 ---- N11 ---- R004 ---- N12
         |                 |                  |
        R005              R006              R007
         |                 |                  |
        N00 ---- R001 ---- N01 ---- R002 ---- N02

    All roads carry realistic static attributes for development/testing.
    """
    nodes: dict[str, tuple[float, float]] = {
        "N00": (9.9200, 76.2600),
        "N01": (9.9200, 76.2800),
        "N02": (9.9200, 76.3000),
        "N10": (9.9400, 76.2600),
        "N11": (9.9400, 76.2800),
        "N12": (9.9400, 76.3000),
    }

    def polyline(a: str, b: str) -> list[tuple[float, float]]:
        return [nodes[a], nodes[b]]

    specs = [
        # (id, name, type, start, end, length, slope, river_dist, lanes)
        ("R001", "Marine Drive", "PRIMARY", "N00", "N01", 2.2, 0.01, 60.0, 4),
        ("R002", "Shanmugham Road", "SECONDARY", "N01", "N02", 2.2, 0.02, 120.0, 2),
        ("R003", "Kaloor Road", "PRIMARY", "N10", "N11", 2.2, 0.01, 90.0, 4),
        ("R004", "S.A. Road", "SECONDARY", "N11", "N12", 2.2, 0.02, 150.0, 2),
        ("R005", "M.G. Road", "PRIMARY", "N00", "N10", 2.2, 0.03, 40.0, 4),
        ("R006", "Vyttila Junction Rd", "SECONDARY", "N01", "N11", 2.2, 0.02, 25.0, 2),
        ("R007", "Chittoor Road", "PRIMARY", "N02", "N12", 2.2, 0.01, 75.0, 4),
    ]

    roads: list[Road] = []
    for road_id, name, road_type, start, end, length, slope, river_dist, lanes in specs:
        roads.append(
            Road(
                road_id=road_id,
                road_name=name,
                road_type=road_type,
                lanes=lanes,
                elevation_m=10.0,
                length_m=length,
                slope=slope,
                distance_to_river_m=river_dist,
                geometry=polyline(start, end),
                start_node=start,
                end_node=end,
                bridges=1 if road_id in {"R002", "R006"} else 0,
            )
        )
    return roads


def _default_shelters() -> list[Shelter]:
    """Return default relief shelters around Kochi, Kerala."""
    return [
        Shelter(
            shelter_id="SH001",
            name="Kochi Town Hall Shelter",
            geometry=[(9.9400, 76.2800)],
            capacity=500,
            occupancy=120,
            status=InfrastructureStatus.OPERATIONAL,
            risk_level="LOW",
        ),
        Shelter(
            shelter_id="SH002",
            name="Fort Kochi Community Hall",
            geometry=[(9.9657, 76.2427)],
            capacity=350,
            occupancy=0,
            status=InfrastructureStatus.OPERATIONAL,
            risk_level="LOW",
        ),
        Shelter(
            shelter_id="SH003",
            name="Edappally Relief Centre",
            geometry=[(10.0248, 76.3098)],
            capacity=800,
            occupancy=300,
            status=InfrastructureStatus.OPERATIONAL,
            risk_level="MEDIUM",
        ),
    ]


def _default_hospitals() -> list[Hospital]:
    """Return default hospitals around Kochi, Kerala."""
    return [
        Hospital(
            hospital_id="H001",
            name="Kochi General Hospital",
            geometry=[(9.9400, 76.2700)],
            capacity=400,
            occupancy=220,
            status=InfrastructureStatus.OPERATIONAL,
            risk_level="LOW",
        ),
        Hospital(
            hospital_id="H002",
            name="Lakeshore Hospital",
            geometry=[(9.9803, 76.2912)],
            capacity=500,
            occupancy=150,
            status=InfrastructureStatus.OPERATIONAL,
            risk_level="MEDIUM",
        ),
    ]


def _default_bridges() -> list[Bridge]:
    """Return default bridges across the local road network."""
    return [
        Bridge(
            bridge_id="B001",
            geometry=[(9.9200, 76.2900)],
            status=InfrastructureStatus.OPERATIONAL,
            road_id="R002",
        ),
        Bridge(
            bridge_id="B002",
            geometry=[(9.9300, 76.2800)],
            status=InfrastructureStatus.WARNING,
            road_id="R006",
        ),
    ]


def _default_resources() -> list[Resource]:
    """Return default deployable emergency resources around Kochi, Kerala."""
    return [
        Resource(
            resource_id="RB01",
            resource_type=ResourceType.RESCUE_BOAT,
            geometry=[(9.9200, 76.2600)],
            status=ResourceStatus.AVAILABLE,
            speed_kmh=20.0,
            capacity=12,
        ),
        Resource(
            resource_id="RB02",
            resource_type=ResourceType.RESCUE_BOAT,
            geometry=[(9.9400, 76.3000)],
            status=ResourceStatus.AVAILABLE,
            speed_kmh=20.0,
            capacity=12,
        ),
        Resource(
            resource_id="AM01",
            resource_type=ResourceType.AMBULANCE,
            geometry=[(9.9400, 76.2700)],
            status=ResourceStatus.AVAILABLE,
            speed_kmh=50.0,
            capacity=2,
        ),
        Resource(
            resource_id="AM02",
            resource_type=ResourceType.AMBULANCE,
            geometry=[(9.9657, 76.2427)],
            status=ResourceStatus.AVAILABLE,
            speed_kmh=50.0,
            capacity=2,
        ),
        Resource(
            resource_id="FT01",
            resource_type=ResourceType.FIRE_UNIT,
            geometry=[(9.9200, 76.2600)],
            status=ResourceStatus.AVAILABLE,
            speed_kmh=40.0,
            capacity=6,
        ),
        Resource(
            resource_id="RT01",
            resource_type=ResourceType.RESCUE_TEAM,
            geometry=[(9.9200, 76.2800)],
            status=ResourceStatus.AVAILABLE,
            speed_kmh=5.0,
            capacity=8,
        ),
    ]