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

# 8. Explanation Generation

## Rule-Based Explanation Engine

Purpose

Generate deterministic, human-readable explanations from AI outputs.

Implementation

- Python
- Jinja2 Templates (optional)
- Custom Explanation Generator

Example Output

Road R27 has been marked HIGH RISK because:

• Rainfall exceeded 60 mm
• Water level increased by 0.18 m
• Elevation is below 5 m

Advantages

- No GPU required
- No model downloads
- Fully deterministic
- Explainable
- Easy to debug

# 9. Graph Processing

## NetworkX

https://networkx.org/

Purpose

Road graph

Routing

Graph algorithms

---

## OSMnx

https://osmnx.readthedocs.io/

Purpose

Download road network from OpenStreetMap.

---

# 10. Route Planning

Algorithms

* Dijkstra
* A*
* Yen's K Shortest Paths

Python Libraries

* NetworkX

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

## Qdrant

https://qdrant.tech/

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

# 18. Python Utilities

* tqdm
* loguru
* python-dotenv
* joblib
* requests
* httpx

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

backend/
frontend/
database/
simulator/
streaming/
models/
xai/
llm/
graph/
datasets/
scripts/
docs/
tests/
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

numpy
pandas
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

sqlalchemy
alembic
psycopg2

qdrant-client

protobuf

kafka-python

requests
httpx

plotly
matplotlib

python-dotenv
joblib
loguru
tqdm
```

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
| Deep Learning    | PyTorch                        |
| GNN              | PyTorch Geometric              |
| XAI              | Captum + Treelite                              |
| Database         | PostgreSQL                     |
| Time Series      | TimescaleDB                    |
| Spatial DB       | PostGIS                        |
| Vector DB        | Qdrant                         |
| Graph Algorithms | NetworkX                       |
| Road Graph       | OSMnx                          |
| GIS              | GeoPandas + Rasterio + Shapely |
| Communication    | WebSockets                     |
| Charts           | Plotly                         |
| Styling          | Tailwind CSS                   |

---

# 29. Free/Open-Source Policy

Every technology selected for this project satisfies at least one of the following:

* Open Source
* Free for local development
* No paid cloud dependency
* Self-hostable
* Suitable for research projects
* No deployment cost required during development

The only external services used are publicly available datasets and free weather/hydrology APIs. All AI models, databases, and processing pipelines are intended to run locally during development.
