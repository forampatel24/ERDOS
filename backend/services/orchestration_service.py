"""Service exposing orchestration operations to API.

This service wraps the orchestration modules (RoutePlanner, EvacuationPlanner,
ResourceAllocator, DecisionValidator, Replanner) and provides a clean
async interface for the API routes, including WebSocket event broadcasting.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from uuid import uuid4

from backend.digital_twin.state_manager import StateManager
from backend.orchestration import (
    DecisionValidator,
    EvacuationPlanner,
    Replanner,
    ResourceAllocator,
    RoutePlanner,
    ROAD_BLOCKED,
    SHELTER_FULL,
    PREDICTION_CHANGE,
)

if TYPE_CHECKING:
    from backend.api.websocket.connection import WebSocketManager

from backend.api.middleware.error_handler import NotFoundError, ValidationError

from backend.schemas.orchestration import (
    RoutePoint,
    RouteRequest,
    RouteResponse,
    RouteSegment,
    EvacuationPlan,
    EvacuationRequest,
    EvacuationStatusResponse,
    AllocationRequest,
    AllocationResponse,
    ResourceCandidate,
    ValidationRequest,
    ValidatedPlan,
    ValidationWarning,
    ReplanTrigger,
    ReplanResponse,
    OrchestrationEvent,
)


class OrchestrationService:
    """Async service for orchestration operations."""

    def __init__(
        self,
        state_manager: StateManager,
        ws_manager: "WebSocketManager",
    ) -> None:
        self._state_manager = state_manager
        self._ws = ws_manager
        self._route_planner = RoutePlanner()
        self._evacuation_planner = EvacuationPlanner()
        self._resource_allocator = ResourceAllocator()
        self._validator = DecisionValidator()
        self._replanner = Replanner()
        self._active_plans: Dict[str, Dict[str, Any]] = {}
        self._monitor_task: Optional[asyncio.Task] = None
        self._monitor_interval = 30  # seconds

    # ------------------------------------------------------------ lifecycle

    async def start_background_tasks(self) -> None:
        """Start background monitoring of active plans."""
        self._monitor_task = asyncio.create_task(self._monitor_active_plans())

    async def stop_background_tasks(self) -> None:
        """Stop background tasks."""
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass

    async def _monitor_active_plans(self) -> None:
        """Periodically re-validate active plans and trigger replanning."""
        while True:
            await asyncio.sleep(self._monitor_interval)
            try:
                await self._check_active_plans()
            except Exception:  # pragma: no cover - best effort
                pass

    async def _check_active_plans(self) -> None:
        """Check all active plans for validity and replan if needed."""
        snapshot = self._state_manager.get_snapshot()
        for plan_id, plan_data in list(self._active_plans.items()):
            try:
                validated = await self.validate_plan(plan_data)
                if not validated.valid:
                    # Trigger replan
                    replan_result = await self.replan(plan_data)
                    if replan_result.trigger != ReplanTrigger.NONE:
                        await self._broadcast_event(
                            OrchestrationEvent(
                                event_type="replan_triggered",
                                timestamp=datetime.now(timezone.utc),
                                payload={
                                    "plan_id": plan_id,
                                    "trigger": replan_result.trigger,
                                    "reason": replan_result.reason,
                                    "new_plan": replan_result.new,
                                },
                            )
                        )
                        # Update stored plan
                        if replan_result.new:
                            self._active_plans[plan_id] = replan_result.new
            except Exception:  # pragma: no cover
                pass

    # ------------------------------------------------------------ routing

    async def compute_route(self, request: RouteRequest) -> RouteResponse:
        """Compute a risk-aware route."""
        # Convert RoutePoint to orchestration format
        origin = self._point_to_orchestration(request.origin)
        destination = self._point_to_orchestration(request.destination)

        # Get fresh snapshot
        snapshot = self._state_manager.get_snapshot()

        # Compute route
        result = self._route_planner.safest_route(origin, destination, snapshot)

        # Build response
        segments = []
        for road_id in result.get("route", []):
            road_data = snapshot.get("roads", {}).get(road_id, {})
            segments.append(
                RouteSegment(
                    road_id=road_id,
                    road_name=road_data.get("road_name", road_id),
                    length_m=road_data.get("length_m", 0),
                    flood_probability=road_data.get("flood_probability", 0),
                    status=road_data.get("status", "SAFE"),
                    estimated_minutes=road_data.get("length_m", 0) / (40 * 1000 / 60),  # 40 km/h
                )
            )

        response = RouteResponse(
            route=segments,
            total_length_m=sum(s.length_m for s in segments),
            estimated_minutes=result.get("estimated_minutes", 0),
            total_risk=result.get("total_risk", 0),
            predicted_blockages=result.get("predicted_blockages", []),
        )

        # Broadcast event
        await self._broadcast_event(
            OrchestrationEvent(
                event_type="route_computed",
                timestamp=datetime.now(timezone.utc),
                payload={"request": request.model_dump(), "response": response.model_dump()},
            )
        )

        return response

    async def compute_alternatives(
        self, request: RouteRequest
    ) -> List[RouteResponse]:
        """Compute alternative routes."""
        origin = self._point_to_orchestration(request.origin)
        destination = self._point_to_orchestration(request.destination)
        snapshot = self._state_manager.get_snapshot()

        alternatives = self._route_planner.alternate_routes(
            origin, destination, k=request.alternatives, snapshot=snapshot
        )

        return [
            RouteResponse(
                route=[
                    RouteSegment(
                        road_id=r,
                        road_name=snapshot.get("roads", {}).get(r, {}).get("road_name", r),
                        length_m=snapshot.get("roads", {}).get(r, {}).get("length_m", 0),
                        flood_probability=snapshot.get("roads", {}).get(r, {}).get("flood_probability", 0),
                        status=snapshot.get("roads", {}).get(r, {}).get("status", "SAFE"),
                        estimated_minutes=snapshot.get("roads", {}).get(r, {}).get("length_m", 0)
                        / (40 * 1000 / 60),
                    )
                    for r in alt.get("route", [])
                ],
                total_length_m=sum(
                    snapshot.get("roads", {}).get(r, {}).get("length_m", 0)
                    for r in alt.get("route", [])
                ),
                estimated_minutes=alt.get("estimated_minutes", 0),
                total_risk=alt.get("total_risk", 0),
                predicted_blockages=alt.get("predicted_blockages", []),
            )
            for alt in alternatives
        ]

    # ------------------------------------------------------------ evacuation

    async def create_evacuation_plan(self, request: EvacuationRequest) -> EvacuationPlan:
        """Generate a complete evacuation plan."""
        # Resolve zone/origin
        if isinstance(request.zone, str):
            zone = request.zone
            origin = self._point_to_orchestration(request.origin) if request.origin else None
        else:
            zone = "Custom"
            origin = self._point_to_orchestration(request.zone)

        snapshot = self._state_manager.get_snapshot()
        plan = self._evacuation_planner.plan_evacuation(
            district=request.district,
            zone=zone,
            people=request.people,
            snapshot=snapshot,
        )

        # Validate the plan
        validated = self._validator.validate_plan(plan)
        plan.update(validated)

        # Store as active plan
        plan_id = str(uuid4())
        self._active_plans[plan_id] = plan

        # Convert to response schema
        response = self._plan_to_response(plan, plan_id)

        # Broadcast event
        await self._broadcast_event(
            OrchestrationEvent(
                event_type="evacuation_created",
                timestamp=datetime.now(timezone.utc),
                payload={"plan_id": plan_id, "plan": response.model_dump()},
            )
        )

        return response

    async def get_evacuation_status(self, plan_id: str) -> EvacuationStatusResponse:
        """Get status of an active evacuation plan."""
        plan = self._active_plans.get(plan_id)
        if not plan:
            from backend.api.middleware.error_handler import NotFoundError
            raise NotFoundError("Evacuation plan", plan_id)

        validated = self._validator.validate_plan(plan)
        return EvacuationStatusResponse(
            plan_id=plan_id,
            plan=self._plan_to_response(plan, plan_id),
            is_valid=validated.get("valid", False),
            warnings=validated.get("warnings", []),
            last_validated=datetime.now(timezone.utc),
        )

    async def list_active_evacuations(self) -> List[EvacuationStatusResponse]:
        """List all active evacuation plans."""
        results = []
        for plan_id, plan in self._active_plans.items():
            validated = self._validator.validate_plan(plan)
            results.append(
                EvacuationStatusResponse(
                    plan_id=plan_id,
                    plan=self._plan_to_response(plan, plan_id),
                    is_valid=validated.get("valid", False),
                    warnings=validated.get("warnings", []),
                    last_validated=datetime.now(timezone.utc),
                )
            )
        return results

    # ------------------------------------------------------------ allocation

    async def allocate_resource(self, request: AllocationRequest) -> AllocationResponse:
        """Allocate a resource to an incident."""
        from config.constants import ResourceType as CoreResourceType

        try:
            CoreResourceType(request.resource_type)
        except ValueError:
            raise ValidationError(
                f"Invalid resource_type '{request.resource_type}'",
                details={"valid_types": [rt.value for rt in CoreResourceType]},
            )

        origin = self._point_to_orchestration(request.origin)
        snapshot = self._state_manager.get_snapshot()

        # Find nearby candidates first
        candidates_data = self._resource_allocator.find_nearby(
            request.resource_type,
            (origin[0], origin[1]) if isinstance(origin, tuple) else (0, 0),
            snapshot=snapshot,
        )

        candidates = [
            ResourceCandidate(
                resource_id=c["resource_id"],
                resource_type=c["resource_type"],
                distance_km=c.get("distance_km", 0),
                capacity=c.get("capacity", 1),
                speed_kmh=c.get("speed_kmh", 30),
                status=c.get("status", "AVAILABLE"),
            )
            for c in candidates_data
        ]

        # Perform allocation
        result = self._resource_allocator.allocate(
            request.incident_id,
            request.resource_type,
            (origin[0], origin[1]) if isinstance(origin, tuple) else (0, 0),
            priority=request.priority,
            min_capacity=request.min_capacity,
            snapshot=snapshot,
        )

        response = AllocationResponse(
            incident_id=request.incident_id,
            resource_id=result.get("resource_id"),
            allocated=result.get("allocated", False),
            reason=result.get("reason", ""),
            allocated_at=datetime.now(timezone.utc),
            candidate=candidates[0] if candidates and result.get("allocated") else None,
        )

        # Broadcast event
        await self._broadcast_event(
            OrchestrationEvent(
                event_type="resource_allocated",
                timestamp=datetime.now(timezone.utc),
                payload={"request": request.model_dump(), "response": response.model_dump()},
            )
        )

        return response

    async def find_nearby_resources(
        self, resource_type: str, origin: RoutePoint, radius_km: float = 10.0
    ) -> List[ResourceCandidate]:
        """Find available resources near a location."""
        from config.constants import ResourceType as CoreResourceType

        try:
            CoreResourceType(resource_type)
        except ValueError:
            raise ValidationError(
                f"Invalid resource_type '{resource_type}'",
                details={"valid_types": [rt.value for rt in CoreResourceType]},
            )

        point = self._point_to_orchestration(origin)
        snapshot = self._state_manager.get_snapshot()

        candidates_data = self._resource_allocator.find_nearby(
            resource_type,
            (point[0], point[1]) if isinstance(point, tuple) else (0, 0),
            radius_km=radius_km,
            snapshot=snapshot,
        )

        return [
            ResourceCandidate(
                resource_id=c["resource_id"],
                resource_type=c["resource_type"],
                distance_km=c.get("distance_km", 0),
                capacity=c.get("capacity", 1),
                speed_kmh=c.get("speed_kmh", 30),
                status=c.get("status", "AVAILABLE"),
            )
            for c in candidates_data
        ]

    # ------------------------------------------------------------ validation

    async def validate_plan(self, plan: Dict[str, Any]) -> ValidatedPlan:
        """Validate a plan against current twin state."""
        snapshot = self._state_manager.get_snapshot()
        validated = self._validator.validate_plan(plan)

        warnings = [
            ValidationWarning(code="BLOCKED_ROAD" if "BLOCKED" in w else "FLOOD_RISK", message=w)
            for w in validated.get("warnings", [])
        ]

        return ValidatedPlan(
            plan=validated,
            valid=validated.get("valid", False),
            warnings=warnings,
            validated_at=datetime.now(timezone.utc),
        )

    # ------------------------------------------------------------ replanning

    async def replan(self, plan: Dict[str, Any]) -> ReplanResponse:
        """Replan if conditions have changed."""
        snapshot = self._state_manager.get_snapshot()
        result = self._replanner.replan(plan)

        trigger_map = {
            "NONE": ReplanTrigger.NONE,
            ROAD_BLOCKED: ReplanTrigger.ROAD_BLOCKED,
            SHELTER_FULL: ReplanTrigger.SHELTER_FULL,
            PREDICTION_CHANGE: ReplanTrigger.PREDICTION_CHANGE,
        }

        return ReplanResponse(
            trigger=trigger_map.get(result["trigger"], ReplanTrigger.NONE),
            reason=result.get("reason", ""),
            previous=result.get("previous", {}),
            new=result.get("new"),
            replanned_at=datetime.now(timezone.utc),
        )

    # ------------------------------------------------------------ helpers

    def _point_to_orchestration(self, point: Optional[RoutePoint]) -> Any:
        """Convert API RoutePoint to orchestration format."""
        if point is None:
            return None
        if point.node_id:
            return point.node_id
        if point.location_name:
            return point.location_name
        if point.lat is not None and point.lon is not None:
            return (point.lat, point.lon)
        return None

    def _plan_to_response(self, plan: Dict[str, Any], plan_id: str) -> EvacuationPlan:
        """Convert internal plan dict to response schema."""
        shelter_data = plan.get("selected_shelter")
        shelter = None
        if shelter_data and isinstance(shelter_data, dict):
            shelter = ShelterSelection(**shelter_data)

        route_data = plan.get("route")
        route = None
        if route_data:
            # Build route response from road IDs
            snapshot = self._state_manager.get_snapshot()
            segments = []
            for road_id in route_data:
                road = snapshot.get("roads", {}).get(road_id, {})
                segments.append(
                    RouteSegment(
                        road_id=road_id,
                        road_name=road.get("road_name", road_id),
                        length_m=road.get("length_m", 0),
                        flood_probability=road.get("flood_probability", 0),
                        status=road.get("status", "SAFE"),
                        estimated_minutes=road.get("length_m", 0) / (40 * 1000 / 60),
                    )
                )
            route = RouteResponse(
                route=segments,
                total_length_m=sum(s.length_m for s in segments),
                estimated_minutes=plan.get("estimated_minutes", 0),
                total_risk=sum(s.flood_probability for s in segments),
                predicted_blockages=[],
            )

        return EvacuationPlan(
            district=plan.get("district", ""),
            zone=plan.get("zone", ""),
            selected_shelter=shelter,
            route=route,
            estimated_minutes=plan.get("estimated_minutes", 0),
            people=plan.get("people", 0),
            status=plan.get("status", "NO_SAFE_OPTION"),
            reason=plan.get("reason", ""),
            capacity_remaining=plan.get("capacity_remaining", 0),
            created_at=plan.get("created_at", datetime.now(timezone.utc)),
        )

    async def _broadcast_event(self, event: OrchestrationEvent) -> None:
        """Broadcast event to WebSocket clients."""
        await self._ws.broadcast("orchestration", event.model_dump(mode="json"))