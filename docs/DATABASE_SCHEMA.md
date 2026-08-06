# DATABASE_SCHEMA.md

# Database Schema

**Project:** Explainable Real-Time Emergency Disaster Orchestration System (ERDOS)

**Version:** 1.0

---

# 1. Purpose

The ERDOS platform uses multiple databases because no single database is suitable for all data types.

The system stores:

- Geospatial Data
- Time-Series Data
- Operational Data
- AI Predictions
- Historical Disaster Events
- Vector Embeddings

Each database has a clearly defined responsibility.

---

# 2. Database Architecture

```
                    ERDOS DATABASES

          PostgreSQL + PostGIS
                 │
     Operational + Spatial Data

                 │

          TimescaleDB
                 │
      Time-Series Sensor Data

                 │
             ChromaDB
                 │
 Historical Disaster Embeddings
```

---

# 3. PostgreSQL

Purpose

Primary relational database.

Stores

- Roads
- Bridges
- Hospitals
- Shelters
- Resources
- Users
- Incidents
- Evacuation Plans

---

# 4. TimescaleDB

Purpose

Store continuously arriving sensor information.

Stores

- Rainfall
- River Levels
- IoT Sensors
- Traffic
- GPS

Optimized for

- Time-series queries

---

# 5. PostGIS

Purpose

Spatial extension for PostgreSQL.

Used for

- Geometry
- Distance calculations
- Route queries
- Spatial joins

---

# 6. ChromaDB

Purpose

Store vector representations of historical disaster situations.

Used for

- Similar disaster retrieval

Not used for

- Predictions

- Routing

---

# 7. PostgreSQL Tables

---

## roads

Primary Key

road_id

Columns

- road_id
- road_name
- geometry
- road_type
- lanes
- elevation
- status

---
---

## districts

Purpose

Stores administrative boundaries and metadata for each district in Kerala.

Primary Key

district_id

Columns

- district_id
- district_name
- geometry
- population
- area_sq_km
- risk_level

Used By

- Digital Twin
- Dashboard
- Orchestration
- Reporting

---

## weather_stations

Purpose

Stores metadata for weather monitoring stations.

Primary Key

station_id

Columns

- station_id
- station_name
- geometry
- provider
- elevation
- status

Referenced By

TimescaleDB

rainfall.station_id

---

## river_stations

Purpose

Stores metadata for river level monitoring stations.

Primary Key

station_id

Columns

- station_id
- river_name
- station_name
- geometry
- provider
- warning_level
- danger_level
- status

Referenced By

TimescaleDB

river_levels.station_id


## bridges

- bridge_id
- geometry
- status

---

## hospitals

- hospital_id
- name
- geometry
- capacity
- occupancy
- status

---

## shelters

- shelter_id
- name
- geometry
- capacity
- occupancy
- status

---

## emergency_resources

- resource_id
- resource_type
- geometry
- status
- assigned_incident_id

---

## incidents

- incident_id
- incident_type
- geometry
- priority
- status
- created_at

---

## evacuation_plans

- plan_id
- incident_id
- shelter_id
- route
- created_at
- status

---

## predictions

Stores latest prediction outputs.

Columns

- prediction_id
- prediction_type
- road_id
- flood_probability
- accessibility
- confidence
- timestamp

---

## explanations

Stores generated explanations.

Columns

- explanation_id
- prediction_id
- decision_id (nullable)
- explanation
- explanation_type
- timestamp

---

## administrative_regions

Purpose

Store hierarchical administrative boundaries.

Columns

- region_id
- region_name
- region_type
- parent_region
- geometry

Examples

Kerala

↓

Ernakulam

↓

Kochi

↓

Ward

---

# 8. TimescaleDB Hypertables

---

## rainfall

Columns

- timestamp
- station_id
- rainfall

---

## river_levels

- timestamp
- station_id
- water_level

---

## traffic

- timestamp
- road_id
- congestion

---

## gps_locations

- timestamp
- resource_id
- latitude
- longitude
- heading
- speed

---

## sensor_events

- timestamp
- sensor_id
- sensor_type
- value
- source

---

# 9. ChromaDB Collection

Collection

historical_disasters

Payload

- disaster_type
- district_name
- rainfall
- river_level
- flood_extent
- casualties
- response_summary

Embedding

Generated using an embedding model.

---

# 10. Relationships

# 10. Entity Relationships

roads
    │
    ├── belongs_to → districts
    │
    ├── referenced_by → predictions
    │
    └── used_in → evacuation_plans

districts
    └── contain → roads, hospitals, shelters

weather_stations
    └── referenced_by → rainfall

river_stations
    └── referenced_by → river_levels

incidents
    └── assigned_to → emergency_resources

evacuation_plans
    ├── reference → shelters
    ├── reference → incidents
    └── use → roads

predictions
    └── generate → explanations

---

# 11. Indexes

Primary Keys

All IDs

Spatial Index

GiST Index

(on geometry columns)

Geometry Columns

Time Index

timestamp

Vector Index

ChromaDB HNSW

---

# 12. Data Retention

Operational Data

Forever

Sensor Data

Configurable

Predictions

30 Days

Logs

90 Days

Embeddings

Permanent

---

# 13. Backup Strategy

Daily PostgreSQL Backup

Weekly Timescale Snapshot

Monthly ChromaDB Backup

---

# 14. Summary

| Database | Responsibility |
|------------|---------------|
| PostgreSQL | Operational Data |
| PostGIS | Spatial Queries |
| TimescaleDB | Time-Series Data |
| ChromaDB | Disaster Similarity Search |

## Database Philosophy

Operational data, geospatial data, time-series data and vector embeddings are intentionally separated into specialized databases.

Each database is responsible only for the data it is optimized to store, improving scalability, maintainability and performance while keeping the overall architecture modular.