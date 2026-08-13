"""Integration tests for the ERDOS API layer (Part 6).

Covers app boot, health/version, JWT auth, digital twin endpoints,
prediction endpoints, orchestration endpoints, dashboard and error handling.
"""

from __future__ import annotations

import jwt
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.utils.settings import get_settings


@pytest.fixture(scope="module")
def client():
    """TestClient with full lifespan (services initialized)."""
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def auth_headers():
    """Valid JWT auth headers for protected endpoints."""
    settings = get_settings()
    token = jwt.encode(
        {
            "sub": "tester",
            "roles": ["admin"],
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            "iat": datetime.now(timezone.utc),
            "permissions": ["*"],
            "aud": "erdos-api",
        },
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    return {"Authorization": f"Bearer {token}"}


# ------------------------------------------------------------ health

class TestHealth:
    def test_health_check(self, client):
        r = client.get("/api/v1/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] in {"healthy", "degraded", "unhealthy"}
        assert "state_manager" in data["checks"]
        assert "settings" in data["checks"]

    def test_version(self, client):
        r = client.get("/api/v1/version")
        assert r.status_code == 200
        data = r.json()
        assert data["version"]
        assert data["python_version"].startswith("3.")


# ------------------------------------------------------------ auth

class TestAuth:
    def test_protected_route_requires_token(self, client):
        r = client.get("/api/v1/twin/snapshot")
        assert r.status_code == 401

    def test_invalid_token_rejected(self, client):
        r = client.get(
            "/api/v1/twin/snapshot",
            headers={"Authorization": "Bearer not-a-real-token"},
        )
        assert r.status_code == 401

    def test_valid_token_accepted(self, client, auth_headers):
        r = client.get("/api/v1/twin/snapshot", headers=auth_headers)
        assert r.status_code == 200


# ------------------------------------------------------------ digital twin

class TestDigitalTwin:
    def test_snapshot(self, client, auth_headers):
        r = client.get("/api/v1/twin/snapshot", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        for key in ("roads", "shelters", "resources", "incidents", "timestamp"):
            assert key in data

    def test_roads_list(self, client, auth_headers):
        r = client.get("/api/v1/twin/roads", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_incidents_list(self, client, auth_headers):
        r = client.get("/api/v1/incidents", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_shelters_list(self, client, auth_headers):
        r = client.get("/api/v1/shelters", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_resources_list(self, client, auth_headers):
        r = client.get("/api/v1/resources", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)


# ------------------------------------------------------------ prediction

class TestPrediction:
    def test_models(self, client, auth_headers):
        r = client.get("/api/v1/prediction/models", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_flood_prediction(self, client, auth_headers):
        r = client.post(
            "/api/v1/prediction/flood",
            headers=auth_headers,
            json={"road_ids": ["road_1"], "horizon_hours": 6},
        )
        assert r.status_code == 200
        data = r.json()
        assert "predictions" in data
        assert "model_version" in data

    def test_heatmap(self, client, auth_headers):
        r = client.post(
            "/api/v1/prediction/heatmap",
            headers=auth_headers,
            json={"bbox": "76.2,9.9,76.3,10.0", "resolution_m": 500, "horizon_hours": 6},
        )
        assert r.status_code == 200
        assert "cells" in r.json()


# ------------------------------------------------------------ orchestration

class TestOrchestration:
    def test_route(self, client, auth_headers):
        r = client.post(
            "/api/v1/orchestration/route",
            headers=auth_headers,
            json={"origin": {"node_id": "node_1"}, "destination": {"node_id": "node_2"}},
        )
        assert r.status_code == 200
        assert "route" in r.json()

    def test_evacuate(self, client, auth_headers):
        r = client.post(
            "/api/v1/orchestration/evacuate",
            headers=auth_headers,
            json={"incident_id": "inc_1", "affected_people": 100},
        )
        assert r.status_code == 200
        assert "status" in r.json()

    def test_validate(self, client, auth_headers):
        r = client.post(
            "/api/v1/orchestration/validate",
            headers=auth_headers,
            json={"plan": {"type": "evacuation", "shelter_id": "sh1", "route": []}},
        )
        assert r.status_code == 200
        assert "valid" in r.json()

    def test_allocate_invalid_resource_type(self, client, auth_headers):
        r = client.post(
            "/api/v1/orchestration/allocate",
            headers=auth_headers,
            json={
                "incident_id": "inc_1",
                "resource_type": "NOT_A_TYPE",
                "origin": {"node_id": "node_1"},
                "priority": "HIGH",
                "min_capacity": 1,
            },
        )
        assert r.status_code == 422
        data = r.json()
        assert data["error"]["code"] == "VALIDATION_ERROR"
        assert "valid_types" in data["error"]["details"]

    def test_replan_missing_plan(self, client, auth_headers):
        r = client.post(
            "/api/v1/orchestration/replan?plan_id=does_not_exist",
            headers=auth_headers,
        )
        assert r.status_code == 404
        assert r.json()["error"]["code"] == "NOT_FOUND"


# ------------------------------------------------------------ dashboard

class TestDashboard:
    def test_summary(self, client, auth_headers):
        r = client.get("/api/v1/dashboard/summary", headers=auth_headers)
        assert r.status_code == 200
        assert "total_roads" in r.json()

    def test_zones(self, client, auth_headers):
        r = client.get("/api/v1/dashboard/zones", headers=auth_headers)
        assert r.status_code == 200
        assert "zones" in r.json()

    def test_resources(self, client, auth_headers):
        r = client.get("/api/v1/dashboard/resources", headers=auth_headers)
        assert r.status_code == 200
        assert "deployments" in r.json()


# ------------------------------------------------------------ incident CRUD

class TestIncidentCRUD:
    @pytest.fixture(scope="class")
    def created_incident(self, client, auth_headers):
        r = client.post(
            "/api/v1/incidents",
            headers=auth_headers,
            json={
                "incident_id": "INC_TEST",
                "incident_type": "FLOOD",
                "priority": "HIGH",
                "geometry": {"coordinates": [{"lat": 9.95, "lon": 76.25}]},
                "reported_people": 50,
                "severity": 0.8,
            },
        )
        assert r.status_code == 201
        return r.json()

    def test_create_incident(self, created_incident):
        assert created_incident["incident_id"] == "INC_TEST"
        assert created_incident["status"] == "ACTIVE"
        assert created_incident["priority"] == "HIGH"
        assert created_incident["geometry"]["coordinates"][0]["lat"] == 9.95

    def test_get_incident(self, client, auth_headers, created_incident):
        r = client.get("/api/v1/incidents/INC_TEST", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["incident_type"] == "FLOOD"

    def test_update_incident(self, client, auth_headers, created_incident):
        r = client.patch(
            "/api/v1/incidents/INC_TEST",
            headers=auth_headers,
            json={"status": "RESOLVED", "priority": "LOW"},
        )
        assert r.status_code == 200
        assert r.json()["status"] == "RESOLVED"
        assert r.json()["priority"] == "LOW"

    def test_filter_by_status(self, client, auth_headers, created_incident):
        r = client.get("/api/v1/incidents?status=ACTIVE", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_filter_by_priority(self, client, auth_headers, created_incident):
        r = client.get("/api/v1/incidents?priority=HIGH", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_pagination(self, client, auth_headers, created_incident):
        r = client.get("/api/v1/incidents?page=1&page_size=1", headers=auth_headers)
        assert r.status_code == 200
        assert len(r.json()) <= 1


# ------------------------------------------------------------ infrastructure CRUD

@pytest.fixture(scope="module")
def seeded_twin():
    """Seed the singleton twin with default infrastructure for CRUD tests."""
    from backend.digital_twin.builder import DigitalTwinBuilder
    from backend.digital_twin.state_manager import get_state_manager

    builder = DigitalTwinBuilder(get_state_manager())
    builder.register_default_infrastructure()
    yield
    # leave the twin as-is; tests use unique ids where they create entities


class TestShelterCRUD:
    @pytest.fixture(scope="class")
    def shelter_id(self, client, auth_headers, seeded_twin):
        r = client.get("/api/v1/shelters", headers=auth_headers)
        assert r.status_code == 200
        shelters = r.json()
        assert shelters, "expected seeded shelters"
        return shelters[0]["shelter_id"]

    def test_list_shelters(self, client, auth_headers, shelter_id):
        r = client.get("/api/v1/shelters", headers=auth_headers)
        assert r.status_code == 200
        assert any(s["shelter_id"] == shelter_id for s in r.json())

    def test_get_shelter(self, client, auth_headers, shelter_id):
        r = client.get(f"/api/v1/shelters/{shelter_id}", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["shelter_id"] == shelter_id

    def test_update_shelter(self, client, auth_headers, shelter_id):
        r = client.patch(
            f"/api/v1/shelters/{shelter_id}",
            headers=auth_headers,
            json={"occupancy": 42, "status": "OPERATIONAL", "risk_level": "MEDIUM"},
        )
        assert r.status_code == 200
        assert r.json()["occupancy"] == 42
        assert r.json()["risk_level"] == "MEDIUM"

    def test_filter_shelters_by_status(self, client, auth_headers):
        r = client.get("/api/v1/shelters?status=OPERATIONAL", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_filter_shelters_by_bbox(self, client, auth_headers):
        r = client.get("/api/v1/shelters?bbox=76.2,9.9,76.3,10.0", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_get_missing_shelter_returns_404(self, client, auth_headers):
        r = client.get("/api/v1/shelters/DOES_NOT_EXIST", headers=auth_headers)
        assert r.status_code == 404


class TestResourceCRUD:
    @pytest.fixture(scope="class")
    def resource_id(self, client, auth_headers, seeded_twin):
        r = client.get("/api/v1/resources", headers=auth_headers)
        assert r.status_code == 200
        resources = r.json()
        assert resources, "expected seeded resources"
        return resources[0]["resource_id"]

    def test_list_resources(self, client, auth_headers, resource_id):
        r = client.get("/api/v1/resources", headers=auth_headers)
        assert r.status_code == 200
        assert any(res["resource_id"] == resource_id for res in r.json())

    def test_get_resource(self, client, auth_headers, resource_id):
        r = client.get(f"/api/v1/resources/{resource_id}", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["resource_id"] == resource_id

    def test_update_resource_status(self, client, auth_headers, resource_id):
        r = client.patch(
            f"/api/v1/resources/{resource_id}",
            headers=auth_headers,
            json={"status": "DEPLOYED"},
        )
        assert r.status_code == 200
        assert r.json()["status"] == "DEPLOYED"

    def test_update_resource_geometry(self, client, auth_headers, resource_id):
        r = client.patch(
            f"/api/v1/resources/{resource_id}",
            headers=auth_headers,
            json={"geometry": {"coordinates": [{"lat": 9.9, "lon": 76.2}]}},
        )
        assert r.status_code == 200
        assert r.json()["geometry"]["coordinates"][0]["lat"] == 9.9

    def test_filter_resources_by_type(self, client, auth_headers, resource_id):
        r = client.get("/api/v1/resources?resource_type=RESCUE_BOAT", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_get_missing_resource_returns_404(self, client, auth_headers):
        r = client.get("/api/v1/resources/DOES_NOT_EXIST", headers=auth_headers)
        assert r.status_code == 404


class TestRoadCRUD:
    @pytest.fixture(scope="class")
    def road_id(self, client, auth_headers, seeded_twin):
        r = client.get("/api/v1/twin/roads", headers=auth_headers)
        assert r.status_code == 200
        roads = r.json()
        assert roads, "expected seeded roads"
        return roads[0]["road_id"]

    def test_list_roads(self, client, auth_headers, road_id):
        r = client.get("/api/v1/twin/roads", headers=auth_headers)
        assert r.status_code == 200
        assert any(rr["road_id"] == road_id for rr in r.json())

    def test_get_road(self, client, auth_headers, road_id):
        r = client.get(f"/api/v1/twin/roads/{road_id}", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["road_id"] == road_id

    def test_update_road(self, client, auth_headers, road_id):
        r = client.patch(
            f"/api/v1/twin/roads/{road_id}",
            headers=auth_headers,
            json={"status": "BLOCKED", "traffic_density": 0.9, "water_level": 1.2},
        )
        assert r.status_code == 200
        assert r.json()["status"] == "BLOCKED"
        assert r.json()["traffic_density"] == 0.9

    def test_filter_roads_by_status(self, client, auth_headers):
        r = client.get("/api/v1/twin/roads?road_status=SAFE", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_filter_roads_by_bbox(self, client, auth_headers):
        r = client.get("/api/v1/twin/roads?bbox=76.2,9.9,76.3,10.0", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_get_missing_road_returns_404(self, client, auth_headers):
        r = client.get("/api/v1/twin/roads/DOES_NOT_EXIST", headers=auth_headers)
        assert r.status_code == 404


# ------------------------------------------------------------ error handling

class TestErrorHandling:
    def test_missing_body_returns_422(self, client, auth_headers):
        r = client.post("/api/v1/orchestration/route", headers=auth_headers)
        assert r.status_code == 422
        assert r.json()["error"]["code"] == "VALIDATION_ERROR"

    def test_invalid_json_returns_422(self, client, auth_headers):
        r = client.post(
            "/api/v1/prediction/flood",
            headers=auth_headers,
            json={"horizon_hours": -5},  # violates ge=1
        )
        assert r.status_code == 422
        assert r.json()["error"]["code"] == "VALIDATION_ERROR"

    def test_error_response_contains_request_id(self, client, auth_headers):
        r = client.post(
            "/api/v1/orchestration/replan?plan_id=does_not_exist",
            headers=auth_headers,
        )
        assert r.status_code == 404
        assert r.json()["error"]["request_id"]

    def test_unknown_route_returns_404(self, client, auth_headers):
        r = client.get("/api/v1/does_not_exist", headers=auth_headers)
        assert r.status_code == 404

    def test_wrong_method_returns_405(self, client, auth_headers):
        r = client.get("/api/v1/orchestration/route", headers=auth_headers)
        assert r.status_code == 405


# ------------------------------------------------------------ explainability

class TestExplainability:
    def test_prediction_explanation(self, client, auth_headers):
        r = client.post(
            "/api/v1/explainability/prediction",
            headers=auth_headers,
            json={"target_type": "prediction", "target_id": "road_1"},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["road_id"] == "road_1"
        assert "top_features" in data

    def test_decision_explanation(self, client, auth_headers):
        r = client.post(
            "/api/v1/explainability/decision",
            headers=auth_headers,
            json={"target_type": "decision", "target_id": "d1"},
        )
        assert r.status_code == 200
        assert "rationale" in r.json()