"""Service for dashboard aggregation."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from backend.digital_twin.state_manager import StateManager
from backend.schemas.dashboard import (
    DashboardSummary,
    ZoneStatus,
    DashboardZones,
    ResourceDeployment,
    DashboardResources,
)
from backend.schemas.digital_twin import RoadStatus, InfrastructureStatus, ResourceStatus, IncidentPriority


class DashboardService:
    """Service for dashboard data aggregation."""

    def __init__(self, state_manager: StateManager) -> None:
        self._state_manager = state_manager

    async def get_summary(self) -> DashboardSummary:
        """Get high-level dashboard summary."""
        data = self._state_manager.get_snapshot()

        roads = data.get("roads", {})
        shelters = data.get("shelters", {})
        resources = data.get("resources", {})
        incidents = data.get("incidents", {})

        # Roads by status
        roads_by_status = {status: 0 for status in RoadStatus}
        for road in roads.values():
            status = road.get("status", "SAFE")
            if status in roads_by_status:
                roads_by_status[RoadStatus(status)] += 1

        # Shelters
        shelters_operational = sum(
            1 for s in shelters.values() if s.get("status") == "OPERATIONAL"
        )
        shelters_at_capacity = sum(
            1 for s in shelters.values() if s.get("capacity", 0) - s.get("occupancy", 0) <= 0
        )
        total_capacity = sum(s.get("capacity", 0) for s in shelters.values())
        current_occupancy = sum(s.get("occupancy", 0) for s in shelters.values())

        # Resources
        resources_available = sum(
            1 for r in resources.values() if r.get("status") == "AVAILABLE"
        )
        resources_deployed = sum(
            1 for r in resources.values() if r.get("status") == "DEPLOYED"
        )

        # Incidents
        incidents_by_priority = {p: 0 for p in IncidentPriority}
        active_incidents = 0
        for inc in incidents.values():
            priority = inc.get("priority", "MEDIUM")
            if priority in incidents_by_priority:
                incidents_by_priority[IncidentPriority(priority)] += 1
            if inc.get("status") == "ACTIVE":
                active_incidents += 1

        return DashboardSummary(
            total_roads=len(roads),
            roads_by_status=roads_by_status,
            total_shelters=len(shelters),
            shelters_operational=shelters_operational,
            shelters_at_capacity=shelters_at_capacity,
            total_capacity=total_capacity,
            current_occupancy=current_occupancy,
            total_resources=len(resources),
            resources_available=resources_available,
            resources_deployed=resources_deployed,
            total_incidents=len(incidents),
            incidents_by_priority=incidents_by_priority,
            active_incidents=active_incidents,
            timestamp=datetime.now(timezone.utc),
        )

    async def get_zones(self) -> DashboardZones:
        """Get zone-level status (simplified - one zone per district)."""
        data = self._state_manager.get_snapshot()

        # Group by district/zone - simplified implementation
        zones = [
            ZoneStatus(
                zone="Zone 1",
                district="Ernakulam",
                flood_risk="MODERATE",
                affected_roads=sum(1 for r in data.get("roads", {}).values() if r.get("flood_probability", 0) > 0.3),
                blocked_roads=sum(1 for r in data.get("roads", {}).values() if r.get("status") == "BLOCKED"),
                available_shelters=sum(
                    1 for s in data.get("shelters", {}).values() if s.get("status") == "OPERATIONAL"
                ),
                shelter_capacity_remaining=sum(
                    max(0, s.get("capacity", 0) - s.get("occupancy", 0))
                    for s in data.get("shelters", {}).values()
                    if s.get("status") == "OPERATIONAL"
                ),
                deployed_resources=sum(
                    1 for r in data.get("resources", {}).values() if r.get("status") == "DEPLOYED"
                ),
                active_incidents=sum(
                    1 for i in data.get("incidents", {}).values() if i.get("status") == "ACTIVE"
                ),
                last_updated=datetime.now(timezone.utc),
            )
        ]

        overall_risk = "HIGH" if any(z.flood_risk == "HIGH" for z in zones) else "MODERATE"

        return DashboardZones(
            zones=zones,
            overall_risk=overall_risk,
            timestamp=datetime.now(timezone.utc),
        )

    async def get_resources(self) -> DashboardResources:
        """Get resource deployment overview."""
        data = self._state_manager.get_snapshot()

        deployments = []
        for resource_id, resource in data.get("resources", {}).items():
            if resource.get("status") in ("DEPLOYED", "EN_ROUTE"):
                deployments.append(
                    ResourceDeployment(
                        resource_id=resource_id,
                        resource_type=resource.get("resource_type", "UNKNOWN"),
                        incident_id=resource.get("assigned_incident_id"),
                        origin={"type": "Point", "coordinates": [0, 0]},  # Placeholder
                        destination=None,
                        status=ResourceStatus(resource.get("status", "AVAILABLE")),
                        progress_pct=50.0,
                        eta_minutes=10.0,
                    )
                )

        available = sum(1 for r in data.get("resources", {}).values() if r.get("status") == "AVAILABLE")
        deployed = sum(1 for r in data.get("resources", {}).values() if r.get("status") in ("DEPLOYED", "EN_ROUTE"))

        return DashboardResources(
            deployments=deployments,
            available_count=available,
            deployed_count=deployed,
            timestamp=datetime.now(timezone.utc),
        )