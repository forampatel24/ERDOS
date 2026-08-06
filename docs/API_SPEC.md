# API_SPEC.md

# API Specification

**Project:** Explainable Real-Time Emergency Disaster Orchestration System (ERDOS)

**Version:** 1.0

---

# 1. Purpose

This document defines all backend APIs exposed by the ERDOS platform.

The API layer serves as the communication bridge between:

- React Dashboard
- FastAPI Backend
- Digital Twin
- Prediction Layer
- Orchestration Engine
- Explainability Layer

It also defines the WebSocket events used for real-time updates.

---

# 2. API Design Principles

The backend follows REST for request-response operations and WebSockets for live updates.

Guidelines

- Stateless REST APIs
- JSON request/response format
- Consistent endpoint naming
- Versioned APIs
- WebSockets for streaming events

Base URL

```
/api/v1
```

---

# 3. Authentication

Authentication Method

JWT Bearer Token

Headers

```
Authorization: Bearer <token>
```

Future versions may support

- OAuth
- Role-Based Access Control

---

# 4. REST API Overview

| Module | Purpose |
|---------|---------|
| Digital Twin | Current system state |
| Prediction | AI predictions |
| Orchestration | Decision generation |
| Explainability | AI explanations |
| Resources | Rescue resources |
| Shelters | Shelter information |
| Incidents | Emergency incidents |
| Dashboard | Dashboard statistics |

---

# 5. Health APIs

## GET /health

Purpose

Check backend status.

Response

```json
{
  "status":"healthy"
}
```

---

## GET /version

Returns

```json
{
  "project":"ERDOS",
  "version":"1.0"
}
```

---

# 6. Digital Twin APIs

## GET /digital-twin

Returns the current Digital Twin state.

Response

```json
{
  "timestamp":"...",
  "roads":[],
  "shelters":[],
  "resources":[]
}
```

---

## GET /digital-twin/roads

Returns

Current road network.

---

## GET /digital-twin/shelters

Returns

Current shelter status.

---

## GET /digital-twin/resources

Returns

Current emergency resources.

---

# 7. Prediction APIs

## GET /prediction/roads

Returns flood predictions.

Example

```json
{
  "road_id":"R21",
  "probability":0.91,
  "status":"Blocked"
}
```

---

## GET /prediction/flood

Returns

Predicted flood propagation.

---

## GET /prediction/heatmap

Returns

Flood heatmap data.

---

# 8. Orchestration APIs

## POST /orchestration/evacuate

Purpose

Generate evacuation plan.

Request

```json
{
  "district":"Ernakulam",
  "zone":"Zone 4"
}
```

Response

```json
{
  "selected_shelter":"Shelter B",
  "route":["R21","R31","R42"]
}
```

---

## POST /orchestration/route

Generate safest route.

Request

```json
{
  "origin":"Hospital A",
  "destination":"Shelter B"
}
```

---

## POST /orchestration/resources

Allocate rescue resources.

Request

```json
{
  "incident":"Flood Rescue"
}
```

---

# 9. Explainability APIs

## GET /explain/prediction/{road_id}

Returns

Prediction explanation.

Example

```json
{
  "road":"R21",
  "importance":{
    "rainfall":0.42,
    "water_level":0.31,
    "elevation":0.19
  }
}
```

---

## GET /explain/decision/{decision_id}

Returns explanation for an orchestration decision.

---

# 10. Incident APIs

## GET /incidents

Returns all active incidents.

---

## POST /incidents

Create new incident.

---

## GET /incidents/{incident_id}

Returns incident details.

---

# 11. Resource APIs

## GET /resources

Returns

All emergency resources.

---

## GET /resources/{resource_id}

Returns

Specific resource.

---

## PATCH /resources/{resource_id}

Update resource status.

---

# 12. Shelter APIs

## GET /shelters

Returns

All shelters.

---

## GET /shelters/{id}

Returns

Shelter information.

---

# 13. Dashboard APIs

## GET /dashboard/summary

Returns

```json
{
  "active_incidents":12,
  "available_resources":43,
  "safe_shelters":18
}
```

---

## GET /dashboard/statistics

Returns operational metrics.

---

# 14. WebSocket APIs

Endpoint

```
/ws/live
```

Purpose

Real-time dashboard updates.

---

# 15. WebSocket Events

## Weather Update

```json
{
  "type":"weather_update",
  "payload":{}
}
```

---

## River Update

```json
{
  "type":"river_update",
  "payload":{}
}
```

---

## Flood Prediction

```json
{
  "type":"prediction_update",
  "payload":{}
}
```

---

## Route Update

```json
{
  "type":"route_update",
  "payload":{}
}
```

---

## Resource Update

```json
{
  "type":"resource_update",
  "payload":{}
}
```

---

## Incident Update

```json
{
  "type":"incident_update",
  "payload":{}
}
```

---

## Explanation Update

```json
{
  "type":"explanation_update",
  "payload":{}
}
```

---

# 16. HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Created |
| 400 | Invalid Request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not Found |
| 422 | Validation Error |
| 500 | Internal Server Error |

---

# 17. Error Format

```json
{
  "success":false,
  "error":"Road not found",
  "code":404
}
```

---

# 18. API Versioning

Current Version

```
/api/v1
```

Future

```
/api/v2
```

---

# 19. Future APIs

Future versions may expose

- Drone APIs
- Satellite APIs
- SMS Alert APIs
- Mobile APIs
- Multi-State APIs

---

# 20. API Summary

| Module | Endpoint Count |
|---------|----------------|
| Health | 2 |
| Digital Twin | 4 |
| Prediction | 3 |
| Orchestration | 3 |
| Explainability | 2 |
| Incidents | 3 |
| Resources | 3 |
| Shelters | 2 |
| Dashboard | 2 |
| WebSocket | 1 |

---

# 21. Conclusion

The ERDOS API layer provides a clean separation between the frontend and backend through versioned REST APIs and WebSocket streams. REST endpoints are used for querying state and requesting orchestration actions, while WebSockets ensure that predictions, explanations and operational updates are delivered to the dashboard in real time.