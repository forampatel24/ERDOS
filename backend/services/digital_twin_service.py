"""Service exposing Digital Twin operations to API."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional

from backend.digital_twin.state_manager import StateManager
from backend.schemas.digital_twin import (
    RoadRead,
    RoadUpdate,
    ShelterRead,
    ShelterUpdate,
    ResourceRead,
    ResourceUpdate,
    IncidentRead,
    IncidentCreate,
    IncidentUpdate,
    TwinSnapshot,
    TwinQueryParams,
    RoadStatus,
    InfrastructureStatus,
    ResourceType,
    ResourceStatus,
    IncidentPriority,
)

if TYPE_CHECKING:
    from backend.api.websocket.connection import WebSocketManager

from backend.api.middleware.error_handler import NotFoundError
from backend.database.postgres.session import session_scope
from backend.utils.logging import get_logger

logger = get_logger("services.digital_twin")


class DigitalTwinService:
    """Async service for digital twin operations."""

    def __init__(
        self,
        state_manager: StateManager,
        ws_manager: "WebSocketManager",
        session_factory: Optional[Callable[[], Any]] = None,
    ) -> None:
        self._state_manager = state_manager
        self._ws = ws_manager
        self._session_factory = session_factory

    # ------------------------------------------------------------ persistence

    def _persist_incident(
        self, incident_id: str, values: Dict[str, Any]
    ) -> None:
        """Best-effort persistence of an incident to PostgreSQL.

        The incidents table uses an integer primary key while the API exposes
        string incident IDs, so rows whose ID is not numeric are skipped with
        a warning.  Failures are logged and never raised to the caller.
        """
        if self._session_factory is None:
            return
        if not incident_id.isdigit():
            logger.warning(
                "skipping incident persistence for non-integer id '{}'",
                incident_id,
            )
            return
        try:
            from backend.database.postgres import crud

            with session_scope(self._session_factory) as session:
                crud.create_incident(
                    session,
                    incident_id=int(incident_id),
                    incident_type=values.get("incident_type"),
                    priority=values.get("priority"),
                    status=values.get("status"),
                )
        except Exception as exc:  # noqa: BLE001 - persistence is best effort
            logger.warning("incident persistence failed for {}: {}", incident_id, exc)

    def _persist_incident_update(
        self, incident_id: str, values: Dict[str, Any]
    ) -> None:
        """Best-effort update of an incident row in PostgreSQL."""
        if self._session_factory is None:
            return
        if not incident_id.isdigit():
            return
        try:
            from backend.database.postgres import crud

            with session_scope(self._session_factory) as session:
                crud.update_incident_status(
                    session,
                    incident_id=int(incident_id),
                    status=values.get("status") or "ACTIVE",
                )
        except Exception as exc:  # noqa: BLE001 - persistence is best effort
            logger.warning("incident update persistence failed for {}: {}", incident_id, exc)

    # ------------------------------------------------------------ snapshot

    async def get_snapshot(self) -> TwinSnapshot:
        """Get the current complete twin snapshot."""
        data = self._state_manager.get_snapshot()
        return self._build_snapshot(data)

    async def get_roads(
        self,
        params: TwinQueryParams,
    ) -> List[RoadRead]:
        """Get filtered list of roads."""
        data = self._state_manager.get_snapshot()
        roads = data.get("roads", {})

        # Filter
        filtered = []
        road_status = getattr(params, "road_status", None)
        for road_id, road_data in roads.items():
            if road_status and road_data.get("status") != getattr(road_status, "value", road_status):
                continue
            if params.bbox and not self._in_bbox(road_data.get("geometry", {}), params.bbox):
                continue
            filtered.append(RoadRead(**self._coerce_road(road_id, road_data)))

        # Paginate
        start = (params.page - 1) * params.page_size
        end = start + params.page_size
        return filtered[start:end]

    async def get_road(self, road_id: str) -> RoadRead:
        """Get a single road by ID."""
        data = self._state_manager.get_snapshot()
        road_data = data.get("roads", {}).get(road_id)
        if not road_data:
            raise NotFoundError("Road", road_id)
        return RoadRead(**self._coerce_road(road_id, road_data))

    async def update_road(self, road_id: str, update: RoadUpdate) -> RoadRead:
        """Update a road's dynamic attributes."""
        data = self._state_manager.get_snapshot()
        road_data = data.get("roads", {}).get(road_id)
        if not road_data:
            raise NotFoundError("Road", road_id)

        # Merge update
        updated = {**road_data}
        if update.traffic_density is not None:
            updated["traffic_density"] = update.traffic_density
        if update.flood_probability is not None:
            updated["flood_probability"] = update.flood_probability
        if update.water_level is not None:
            updated["water_level"] = update.water_level
        if update.status is not None:
            updated["status"] = getattr(update.status, "value", update.status)

        # Update via state manager
        from backend.models.road import Road
        from config.constants import RoadStatus

        updated["geometry"] = self._schema_geometry_to_domain(updated.get("geometry"))
        road = Road(**updated)
        self._state_manager.update_road(road)

        # Broadcast update
        await self._ws.broadcast(
            "digital_twin",
            {
                "event_type": "road_updated",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "payload": {"road_id": road_id, **updated},
            },
        )

        return RoadRead(**self._coerce_road(road_id, updated))

    # ------------------------------------------------------------ shelters

    async def get_shelters(self, params: TwinQueryParams) -> List[ShelterRead]:
        """Get filtered list of shelters."""
        data = self._state_manager.get_snapshot()
        shelters = data.get("shelters", {})

        filtered = []
        shelter_status = getattr(params, "shelter_status", None) or getattr(params, "status", None)
        risk_level = getattr(params, "risk_level", None)
        for shelter_id, shelter_data in shelters.items():
            if shelter_status and shelter_data.get("status") != getattr(shelter_status, "value", shelter_status):
                continue
            if risk_level and shelter_data.get("risk_level") != risk_level:
                continue
            if params.bbox and not self._in_bbox(shelter_data.get("geometry", {}), params.bbox):
                continue
            filtered.append(ShelterRead(**self._coerce_shelter(shelter_id, shelter_data)))

        start = (params.page - 1) * params.page_size
        end = start + params.page_size
        return filtered[start:end]

    async def get_shelter(self, shelter_id: str) -> ShelterRead:
        """Get a single shelter by ID."""
        data = self._state_manager.get_snapshot()
        shelter_data = data.get("shelters", {}).get(shelter_id)
        if not shelter_data:
            raise NotFoundError("Shelter", shelter_id)
        return ShelterRead(**self._coerce_shelter(shelter_id, shelter_data))

    async def update_shelter(self, shelter_id: str, update: ShelterUpdate) -> ShelterRead:
        """Update a shelter."""
        data = self._state_manager.get_snapshot()
        shelter_data = data.get("shelters", {}).get(shelter_id)
        if not shelter_data:
            raise NotFoundError("Shelter", shelter_id)

        updated = {**shelter_data}
        if update.occupancy is not None:
            updated["occupancy"] = update.occupancy
        if update.status is not None:
            updated["status"] = getattr(update.status, "value", update.status)
        if update.risk_level is not None:
            updated["risk_level"] = update.risk_level

        from backend.models.shelter import Shelter
        from config.constants import InfrastructureStatus

        updated["geometry"] = self._schema_geometry_to_domain(updated.get("geometry"))
        shelter = Shelter(**updated)
        self._state_manager.update_shelter(shelter)

        await self._ws.broadcast(
            "digital_twin",
            {
                "event_type": "shelter_updated",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "payload": {"shelter_id": shelter_id, **updated},
            },
        )

        return ShelterRead(**self._coerce_shelter(shelter_id, updated))

    # ------------------------------------------------------------ resources

    async def get_resources(self, params: TwinQueryParams) -> List[ResourceRead]:
        """Get filtered list of resources."""
        data = self._state_manager.get_snapshot()
        resources = data.get("resources", {})

        filtered = []
        resource_type = getattr(params, "resource_type", None)
        resource_status = getattr(params, "resource_status", None) or getattr(params, "status", None)
        for resource_id, resource_data in resources.items():
            if resource_type and resource_data.get("resource_type") != getattr(resource_type, "value", resource_type):
                continue
            if resource_status and resource_data.get("status") != getattr(resource_status, "value", resource_status):
                continue
            if params.bbox and not self._in_bbox(resource_data.get("geometry", {}), params.bbox):
                continue
            filtered.append(ResourceRead(**self._coerce_resource(resource_id, resource_data)))

        start = (params.page - 1) * params.page_size
        end = start + params.page_size
        return filtered[start:end]

    async def get_resource(self, resource_id: str) -> ResourceRead:
        """Get a single resource by ID."""
        data = self._state_manager.get_snapshot()
        resource_data = data.get("resources", {}).get(resource_id)
        if not resource_data:
            raise NotFoundError("Resource", resource_id)
        return ResourceRead(**self._coerce_resource(resource_id, resource_data))

    async def update_resource(self, resource_id: str, update: ResourceUpdate) -> ResourceRead:
        """Update a resource."""
        data = self._state_manager.get_snapshot()
        resource_data = data.get("resources", {}).get(resource_id)
        if not resource_data:
            raise NotFoundError("Resource", resource_id)

        updated = {**resource_data}
        if update.status is not None:
            updated["status"] = getattr(update.status, "value", update.status)
        if update.geometry is not None:
            updated["geometry"] = self._schema_geometry_to_domain(update.geometry.model_dump())
        if update.assigned_incident_id is not None:
            updated["assigned_incident_id"] = update.assigned_incident_id
        if update.speed_kmh is not None:
            updated["speed_kmh"] = update.speed_kmh
        if update.capacity is not None:
            updated["capacity"] = update.capacity

        from backend.models.resource import Resource
        from config.constants import ResourceStatus

        resource = Resource(**updated)
        self._state_manager.update_resource(resource)

        await self._ws.broadcast(
            "digital_twin",
            {
                "event_type": "resource_updated",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "payload": {"resource_id": resource_id, **updated},
            },
        )

        return ResourceRead(**self._coerce_resource(resource_id, updated))

    # ------------------------------------------------------------ incidents

    async def get_incidents(self, params: TwinQueryParams) -> List[IncidentRead]:
        """Get filtered list of incidents."""
        data = self._state_manager.get_snapshot()
        incidents = data.get("incidents", {})

        filtered = []
        priority = getattr(params, "incident_priority", None) or getattr(params, "priority", None)
        status = getattr(params, "incident_status", None) or getattr(params, "status", None)
        incident_type = getattr(params, "incident_type", None)
        for incident_id, incident_data in incidents.items():
            if priority and incident_data.get("priority") != getattr(priority, "value", priority):
                continue
            if status and incident_data.get("status") != status:
                continue
            if incident_type and incident_data.get("incident_type") != incident_type:
                continue
            filtered.append(IncidentRead(**self._coerce_incident(incident_id, incident_data)))

        start = (params.page - 1) * params.page_size
        end = start + params.page_size
        return filtered[start:end]

    async def get_incident(self, incident_id: str) -> IncidentRead:
        """Get a single incident by ID."""
        data = self._state_manager.get_snapshot()
        incident_data = data.get("incidents", {}).get(incident_id)
        if not incident_data:
            raise NotFoundError("Incident", incident_id)
        return IncidentRead(**self._coerce_incident(incident_id, incident_data))

    async def create_incident(self, incident: IncidentCreate) -> IncidentRead:
        """Create a new incident."""
        from backend.models.incident import Incident

        data = incident.model_dump()
        data["geometry"] = self._schema_geometry_to_domain(data.get("geometry"))
        incident_model = Incident(**data)
        self._state_manager.update_incident(incident_model)
        self._persist_incident(incident_model.incident_id, incident_model.model_dump())

        await self._ws.broadcast(
            "digital_twin",
            {
                "event_type": "incident_created",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "payload": incident_model.model_dump(mode="json"),
            },
        )

        return IncidentRead(**self._coerce_incident(incident_model.incident_id, incident_model.model_dump()))

    async def update_incident(self, incident_id: str, update: IncidentUpdate) -> IncidentRead:
        """Update an incident."""
        data = self._state_manager.get_snapshot()
        incident_data = data.get("incidents", {}).get(incident_id)
        if not incident_data:
            raise NotFoundError("Incident", incident_id)

        updated = {**incident_data}
        if update.priority is not None:
            updated["priority"] = getattr(update.priority, "value", update.priority)
        if update.status is not None:
            updated["status"] = update.status
        if update.description is not None:
            updated["description"] = update.description
        if update.reported_people is not None:
            updated["reported_people"] = update.reported_people
        if update.severity is not None:
            updated["severity"] = update.severity

        from backend.models.incident import Incident

        updated["geometry"] = self._schema_geometry_to_domain(updated.get("geometry"))
        incident = Incident(**updated)
        self._state_manager.update_incident(incident)
        self._persist_incident_update(incident_id, updated)

        await self._ws.broadcast(
            "digital_twin",
            {
                "event_type": "incident_updated",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "payload": {"incident_id": incident_id, **updated},
            },
        )

        return IncidentRead(**self._coerce_incident(incident_id, updated))

    # ------------------------------------------------------------ helpers

    def _build_snapshot(self, data: Dict[str, Any]) -> TwinSnapshot:
        """Build TwinSnapshot from raw data."""
        return TwinSnapshot(
            roads={k: RoadRead(**self._coerce_road(k, v)) for k, v in data.get("roads", {}).items()},
            shelters={k: ShelterRead(**self._coerce_shelter(k, v)) for k, v in data.get("shelters", {}).items()},
            resources={k: ResourceRead(**self._coerce_resource(k, v)) for k, v in data.get("resources", {}).items()},
            incidents={k: IncidentRead(**self._coerce_incident(k, v)) for k, v in data.get("incidents", {}).items()},
            hospitals=data.get("hospitals", {}),
            bridges=data.get("bridges", {}),
            weather=data.get("weather"),
            rivers=data.get("rivers"),
            timestamp=datetime.now(timezone.utc),
        )

    def _schema_geometry_to_domain(self, geometry: Any) -> list:
        """Convert schema geometry to the domain model's list-of-pairs form.

        Accepts either a schema ``{"coordinates": [{"lat": ..., "lon": ...}]}``
        dict or the domain form (a list of ``[lat, lon]`` pairs) so it is safe
        to call on snapshot data that is already domain-shaped.
        """
        if isinstance(geometry, dict):
            coords = geometry.get("coordinates") or []
            return [(c["lat"], c["lon"]) for c in coords if isinstance(c, dict)]
        if isinstance(geometry, list):
            return [(c[0], c[1]) for c in geometry if isinstance(c, (list, tuple))]
        return []

    def _coerce_road(self, road_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Coerce road data to match schema."""
        result = dict(data)
        result.setdefault("road_id", road_id)
        result.setdefault("road_name", road_id)
        result.setdefault("geometry", {"coordinates": []})
        if "geometry" in result and isinstance(result["geometry"], list):
            result["geometry"] = {"coordinates": [{"lat": p[0], "lon": p[1]} for p in result["geometry"]]}
        if "status" in result and isinstance(result["status"], str):
            pass  # already string
        return result

    def _coerce_shelter(self, shelter_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        result = dict(data)
        result.setdefault("shelter_id", shelter_id)
        result.setdefault("geometry", {"coordinates": []})
        if "geometry" in result and isinstance(result["geometry"], list):
            result["geometry"] = {"coordinates": [{"lat": p[0], "lon": p[1]} for p in result["geometry"]]}
        if "status" in result and isinstance(result["status"], str):
            pass
        return result

    def _coerce_resource(self, resource_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        result = dict(data)
        result.setdefault("resource_id", resource_id)
        result.setdefault("geometry", {"coordinates": []})
        if "geometry" in result and isinstance(result["geometry"], list):
            result["geometry"] = {"coordinates": [{"lat": p[0], "lon": p[1]} for p in result["geometry"]]}
        if "resource_type" in result and isinstance(result["resource_type"], str):
            pass
        if "status" in result and isinstance(result["status"], str):
            pass
        return result

    def _coerce_incident(self, incident_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        result = dict(data)
        result.setdefault("incident_id", incident_id)
        result.setdefault("geometry", {"coordinates": []})
        if "geometry" in result and isinstance(result["geometry"], list):
            result["geometry"] = {"coordinates": [{"lat": p[0], "lon": p[1]} for p in result["geometry"]]}
        if "priority" in result and isinstance(result["priority"], str):
            pass
        return result

    def _in_bbox(self, geometry: Any, bbox: str) -> bool:
        """Check if geometry intersects bounding box.

        Accepts both the schema form ``{"coordinates": [{"lat": ..., "lon": ...}]}``
        and the snapshot/domain list form ``[[lat, lon], ...]``.
        """
        try:
            min_lon, min_lat, max_lon, max_lat = map(float, bbox.split(","))
            if isinstance(geometry, dict):
                coords = geometry.get("coordinates", [])
            elif isinstance(geometry, list):
                coords = geometry
            else:
                return False
            if not coords:
                return False
            for coord in coords:
                if isinstance(coord, dict):
                    lat, lon = coord.get("lat"), coord.get("lon")
                elif isinstance(coord, list) and len(coord) >= 2:
                    lat, lon = coord[0], coord[1]
                else:
                    continue
                if min_lon <= lon <= max_lon and min_lat <= lat <= max_lat:
                    return True
        except Exception:
            return False
        return False