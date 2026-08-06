# RESOURCES.md

# Explainable Real-Time Emergency Disaster Orchestration System

This document contains every major technology, framework, dataset, API, library and software required to build the project from scratch.

**Target Disaster:** Urban Floods

**Target Region:** Kerala, India

**License Preference:** Free • Open Source • Unlimited (or generous free tier)

---

# 1. Programming Languages

## Backend

* Python 3.12+

Purpose

* AI
* Backend APIs
* Simulation
* Data Engineering
* Streaming
* Machine Learning

---

## Frontend

* React
* TypeScript

Purpose

* Dashboard
* Maps
* Live visualization
* Control panel

---

## Database

* SQL (PostgreSQL)

---

# 2. Backend Framework

## FastAPI

Purpose

* REST APIs
* WebSocket server
* AI inference APIs

Website

https://fastapi.tiangolo.com/

---

# 3. Frontend Stack

## React

https://react.dev/

Purpose

* Dashboard UI

---

## TypeScript

https://www.typescriptlang.org/

Purpose

* Type-safe frontend

---

## Vite

https://vitejs.dev/

Purpose

* React project bundler

---

# 4. Mapping Libraries

## MapLibre GL JS

https://maplibre.org/

Purpose

* Interactive maps
* Roads
* Flood layers
* Buildings

Open Source

Yes

---

## Deck.gl

https://deck.gl/

Purpose

* Heatmaps
* Animated data
* Large-scale geospatial visualization

---

## React Map GL

https://visgl.github.io/react-map-gl/

Purpose

React wrapper for MapLibre.

---

# 5. Streaming Infrastructure

## Apache Kafka

https://kafka.apache.org/

Purpose

* Event streaming
* Message queue
* Real-time communication

Open Source

Yes

---

## Apache Flink

https://flink.apache.org/

Purpose

* Streaming computation
* Sliding windows
* Feature engineering

Open Source

Yes

---

## Protocol Buffers

https://protobuf.dev/

Purpose

Fast message serialization.

---

# 6. AI Frameworks

## PyTorch

https://pytorch.org/

Purpose

Deep learning.

---

## PyTorch Geometric

https://pytorch-geometric.readthedocs.io/

Purpose

Graph Neural Networks.

---

## XGBoost

https://xgboost.ai/

Purpose

Road flood prediction.

---

## Scikit-Learn

https://scikit-learn.org/

Purpose

Preprocessing

Evaluation

Classical ML

---

## NumPy

https://numpy.org/

Purpose

Numerical computing.

---

## Pandas

https://pandas.pydata.org/

Purpose

Data processing.

---

## SciPy

https://scipy.org/

Purpose

Scientific computing.

---

# 7. Explainable AI

## Captum

https://captum.ai/

Purpose

Integrated Gradients

Feature attribution

PyTorch explainability

---

## Treelite

https://treelite.readthedocs.io/

Purpose

Compile XGBoost models

Fast inference

Decision path extraction


---

# 8. Natural Language Generation

Purpose

Convert structured explanations produced by the Explainability Layer into concise, operational language for emergency responders.

Implementation

• OpenAI API
• Gemini API
• OpenAI-compatible APIs

Input

• Structured Explanation Object

Output

• Human-readable operational explanation

Notes

The LLM is never responsible for:
• Flood prediction
• Resource allocation
• Route optimization
• Decision making

It is only responsible for translating structured evidence into natural language.

# 9. Graph Processing

## NetworkX

https://networkx.org/

Purpose

Road graph

Routing

Graph algorithms

---

## Google OR-Tools

https://developers.google.com/optimization

Purpose

Vehicle Routing

Constraint Optimization

Scheduling

Resource Allocation

Open Source

Yes
## OSMnx

https://osmnx.readthedocs.io/

Purpose

Download road network from OpenStreetMap.

---

# 10. Route Planning

AAlgorithms

• Dijkstra
• A*
• Yen's K Shortest Paths

Optimization

• Vehicle Routing Problem (VRP)
• Constraint Optimization

Libraries

• NetworkX
• Google OR-Tools

---

# 11. Databases

## PostgreSQL

https://www.postgresql.org/

Purpose

Main relational database.

---

## TimescaleDB

https://www.timescale.com/

Purpose

Time-series data.

---

## PostGIS

https://postgis.net/

Purpose

Spatial database.

---

## ChromaDB

https://github.com/chroma-core/chroma

Purpose

Vector database.

Historical disaster retrieval.

Open Source

Yes

---

# 12. Backend Utilities

## Uvicorn

https://www.uvicorn.org/

Purpose

FastAPI server.

---

## Pydantic

https://docs.pydantic.dev/

Purpose

Validation.

---

## SQLAlchemy

https://www.sqlalchemy.org/

Purpose

ORM.

---

## Alembic

https://alembic.sqlalchemy.org/

Purpose

Database migrations.

---

# 13. Data Visualization

## Plotly

https://plotly.com/

Purpose

Graphs

Analytics

---

## Matplotlib

https://matplotlib.org/

Purpose

Research visualization.

---

# 14. Real-Time Communication

## WebSockets

Built into FastAPI.

Purpose

Live dashboard updates.

---

# 15. State Management (Frontend)

## Zustand

https://zustand-demo.pmnd.rs/

Purpose

React global state.

---

# 16. Styling

## Tailwind CSS

https://tailwindcss.com/

Purpose

Frontend styling.

---

# 17. GIS Libraries

## GeoPandas

https://geopandas.org/

Purpose

Spatial dataframe processing.

---

## Shapely

https://shapely.readthedocs.io/

Purpose

Geometry operations.

---

## Rasterio

https://rasterio.readthedocs.io/

Purpose

DEM

Satellite raster processing.

---

## PyProj

https://pyproj4.github.io/

Purpose

Coordinate transformations.

---

## H3

https://uber.github.io/h3-py/

Purpose

Hexagonal spatial indexing

Spatial aggregation

Risk heatmaps

Geospatial indexing

# 18. Python Utilities

* tqdm
* loguru
* python-dotenv
* joblib
* requests
* httpx
* PyArrow
* Purpose
* Fast parquet support
* Columnar storage
* High-performance data exchange

Polars

Purpose

High-performance dataframe processing

Optional alternative to Pandas

---

# 19. Static Datasets

## OpenStreetMap

Purpose

Roads

Buildings

Hospitals

Bridges

Schools

Fire Stations

Police Stations

Water bodies

Website

https://www.openstreetmap.org/

---

## Geofabrik

Purpose

Download OSM extracts.

Website

https://download.geofabrik.de/asia/india.html

---

## NASA SRTM DEM

Purpose

Elevation

Slope

Terrain

Website

https://earthexplorer.usgs.gov/

Alternative

https://opentopography.org/

---

## WorldPop

Purpose

Population density.

Website

https://www.worldpop.org/

---

## GADM

Purpose

Administrative boundaries.

Website

https://gadm.org/

---

# 20. Historical Disaster Datasets

## IMD

India Meteorological Department

Purpose

Historical rainfall.

Website

https://imd.gov.in/

---

## NASA GPM IMERG

Purpose

Historical rainfall.

Global precipitation.

Website

https://gpm.nasa.gov/data/imerg

---

## Central Water Commission

Purpose

Historical river levels.

Website

https://ffs.india-water.gov.in/

---

## ISRO Bhuvan

Purpose

Flood inundation maps.

Disaster maps.

Website

https://bhuvan.nrsc.gov.in/

---

## Copernicus Sentinel

Purpose

Satellite imagery.

Website

https://dataspace.copernicus.eu/

---

## NASA EarthData

Purpose

Satellite imagery.

Website

https://earthdata.nasa.gov/

---

## EM-DAT

Purpose

Historical disaster database.

Website

https://www.emdat.be/

---

# 21. Real-Time Data Sources

## Open-Meteo API

Purpose

Current weather

Forecast

Rainfall

Wind

Temperature

Humidity

Pressure

Free

Yes

API Key

No

Website

https://open-meteo.com/

---

## Central Water Commission

Purpose

Real-time river gauges.

Website

https://ffs.india-water.gov.in/

---

## OpenStreetMap

Purpose

Live map updates.

Website

https://www.openstreetmap.org/

---

# 22. Simulated Data Sources

These datasets will be generated by the simulator.

* IoT Water Sensors
* Rain Sensors
* Emergency Calls
* Rescue Requests
* Ambulance GPS
* Rescue Boat GPS
* Shelter Occupancy
* Hospital Capacity
* Road Closures
* Bridge Failures
* Traffic Density

---

# 23. Machine Learning Dataset Construction

The training dataset will be created by merging data from multiple sources.

Features

* Road ID
* Latitude
* Longitude
* Elevation
* Slope
* Distance to River
* Rainfall
* Rainfall (10 min)
* Rainfall (30 min)
* Water Level
* Water Rise Rate
* Nearby Flooded Roads
* Traffic Density
* Population Density
* Road Type
* Bridge Indicator
* Historical Flood Frequency

Target Labels

* Flooded / Not Flooded
* Flood Probability
* Road Accessibility
* Estimated Flood Time

---

# 24. Graph Dataset

Each node represents

* Road Intersection
* Hospital
* Shelter
* Critical Infrastructure

Each edge represents

* Road

Node Features

* Rainfall
* Elevation
* Water Level
* Traffic
* Population
* Flood State

Edge Features

* Distance
* Road Width
* Road Type
* Slope
* Speed Limit

---

# 25. Recommended Project Structure

```text
project/
│
├── backend/
├── frontend/
├── datasets/
├── models/
│   ├── prediction/
│   └── checkpoints/
├── digital_twin/
├── simulator/
├── streaming/
├── orchestration/
├── explainability/
├── graph/
├── docs/
└── tests/
```

---

# 26. Development Tools

## VS Code

https://code.visualstudio.com/

---

## Git

https://git-scm.com/

---

## GitHub

https://github.com/

---

## Postman

https://www.postman.com/

---

## pgAdmin

https://www.pgadmin.org/

---

# 27. Major Python Libraries

```text
fastapi
uvicorn
pydantic

numpy
pandas
polars
pyarrow
scipy

scikit-learn
xgboost

torch
torch-geometric
captum

networkx
osmnx

geopandas
shapely
rasterio
pyproj
h3

sqlalchemy
alembic
psycopg2

protobuf
kafka-python

ChromaDB-client

ortools

requests
httpx

plotly
matplotlib

python-dotenv
joblib
loguru
tqdm
jinja2
```
## Optional Libraries

### Jinja2

Purpose

- Prompt templates
- Fallback explanation formatting
---

# 28. Technology Summary

| Layer            | Technology                     |
| ---------------- | ------------------------------ |
| Backend          | Python + FastAPI               |
| Frontend         | React + TypeScript             |
| Maps             | MapLibre + Deck.gl             |
| Streaming        | Kafka + Flink                  |
| Serialization    | Protocol Buffers               |
| ML               | XGBoost                        |
| Deep Learning    | PyTorch + ST-GNN                       |
| GNN              | PyTorch Geometric              |
| XAI              | Captum + Treelite                              |
| Database         | PostgreSQL                     |
| Time Series      | TimescaleDB                    |
| Spatial DB       | PostGIS                        |
| Vector DB        | ChromaDB                         |
| Graph Algorithms | NetworkX                       |
| Road Graph       | OSMnx                          |
| GIS              | GeoPandas + Rasterio + Shapely |
| Communication    | WebSockets                     |
| Visualization           | Plotly + Deck.gl                        |
| Styling          | Tailwind CSS                   |
| Natural Language  | LLM API (OpenAI / Gemini / OpenAI-compatible)
|Optimization | Google OR-Tools|
---

# 29. Development Environment

OS

Windows 11

Python

3.12+

Node.js

Latest LTS

Database

PostgreSQL 17+

IDE

VS Code

Version Control

Git

Package Managers

pip

npm

# 30. Free/Open-Source Policy

Every technology selected for this project satisfies at least one of the following:

* Open Source
* Free for local development
* No paid cloud dependency
* Self-hostable
* Suitable for research projects
* No deployment cost required during development

The only external services used are publicly available datasets and free weather/hydrology APIs. All AI models, databases, and processing pipelines are intended to run locally during development.

# 31. Version Policy

This document represents the canonical technology stack for ERDOS Version 1.0.

Technologies listed here should remain unchanged unless a future version of the project explicitly replaces them.

Future changes should be documented in VERSIONS.md rather than modifying this document.