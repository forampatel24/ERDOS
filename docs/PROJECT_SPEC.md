# PROJECT_SPEC.md

# Explainable Real-Time Emergency Disaster Orchestration System (ERDOS)

**Version:** 1.0
**Status:** Planning & Architecture Specification
**Primary Domain:** Artificial Intelligence + Explainable AI + Distributed Systems + Geospatial Computing + Disaster Management

---

# 1. Vision

The goal of this project is to build a complete **Explainable Real-Time Emergency Disaster Orchestration System** capable of continuously monitoring an evolving disaster, predicting future risks, orchestrating emergency response operations, and providing transparent, human-understandable explanations for every critical decision.

Unlike traditional disaster prediction systems that stop after estimating flood risk or damage, this system actively assists emergency commanders by recommending evacuation plans, rescue resource allocation, and dynamic route updates while explaining **why** those recommendations are made.

The project is designed as a **stream-first intelligent decision platform**, where AI continuously reacts to a changing environment rather than performing one-time predictions.

---

# 2. Problem Statement

Modern AI models can process enormous volumes of disaster-related information far faster than humans.

However, during real emergencies, decision-makers cannot trust recommendations that lack justification.

For example:

* Why was an evacuation route changed?
* Why was one rescue team redirected?
* Why was a hospital deprioritized?
* Why did the AI suddenly predict a road would become inaccessible?

Without immediate explanations, emergency commanders must either blindly trust the AI or ignore it completely.

This project bridges that gap by integrating real-time Explainable AI into the complete emergency decision-making pipeline.

---

# 3. Objectives

The system should:

* Continuously ingest disaster-related data
* Maintain a live digital twin of the affected region
* Predict disaster evolution
* Predict road accessibility
* Predict infrastructure risk
* Recommend evacuation routes
* Recommend rescue resource allocation
* Detect when existing plans become unsafe
* Recalculate plans dynamically
* Explain every prediction
* Explain every operational decision
* Present all information through an interactive command dashboard

---

# 4. Disaster Scenario

The initial implementation focuses on:

> **Urban Flood Disaster Management**

Target Region:

> **One Indian State (Kerala)**

The architecture should remain generic enough to support:

* Floods
* Cyclones
* Wildfires
* Landslides
* Earthquakes

with minimal architectural changes.

---

# 5. System Overview

The platform consists of eight major subsystems.

```text
                    DATA SOURCES
                          │
                          ▼
                STREAMING INGESTION
                          │
                          ▼
                REAL-TIME Digital Twin State Manager
                          │
                          ▼
                 AI PREDICTION LAYER
                          │
                          ▼
               ORCHESTRATION ENGINE
                          │
                          ▼
              DECISION VALIDATION
                          │
                          ▼
                  EXPLAINABLE AI
                          │
                          ▼
                COMMAND DASHBOARD
```

---

# 6. Major System Modules

## Module 1 — Digital Twin

Responsible for building the virtual representation of the state.

Contains:

* Road network
* Rivers
* Bridges
* Hospitals
* Fire stations
* Police stations
* Shelters
* Administrative zones
* Elevation
* Population density

Primary Sources

* OpenStreetMap
* OSMnx
* NASA DEM
* WorldPop

---

## Module 2 — Disaster Simulation Engine

Generates realistic disaster events.

Simulates:

* Rainfall
* Water accumulation
* Flood propagation
* Road flooding
* Sensor readings
* Emergency calls
* Rescue requests
* Resource movement

Outputs:

Continuous event streams.

---

## Module 3 — Streaming Infrastructure

Processes all incoming events.

Responsibilities

* Receive sensor events
* Receive weather updates
* Receive emergency calls
* Normalize data
* Window-based aggregation
* Feature generation

Technology

* Apache Kafka
* Apache Flink
* Protocol Buffers

---

## Module 4 — Digital Twin State Manager

Maintains the current state of the world.

Tracks

Current

* Water levels
* Rainfall
* Flood extent
* Road status
* Traffic
* Rescue resources
* Shelters
* Hospitals

This module acts as the single source of truth.

---

## Module 5 — Prediction Layer

Responsible for forecasting future disaster behavior.

Sub-models

### 5.1 Road Flood Risk Predictor

Purpose

Predict which roads become inaccessible.

Model

XGBoost

Input

* Rainfall
* Elevation
* Water level
* Water rise rate
* Road slope
* Distance from river
* Nearby flooded roads
* Traffic

Output

Probability of flooding.

---

### 5.2 Disaster Propagation Model

Purpose

Predict spatial spread of flooding.

Model

Spatio-Temporal Graph Neural Network

Framework

PyTorch Geometric

Input

Graph

*

Historical temporal snapshots

Output

Future flood map.


---

The outputs of the Road Flood Risk Predictor and the Disaster Propagation Model together represent the predicted future state of the Digital Twin, which becomes the input for the Orchestration Engine.

## Module 6 — Decision Orchestration Engine

Transforms predictions into actionable plans.

Responsible for

### Evacuation Planning

Calculates

* Safe routes
* Safe shelters
* Estimated travel time
* Future route safety

Outputs

Recommended evacuation plans.

---

### Resource Allocation

Assigns

* Rescue boats
* Ambulances
* Fire units
* Emergency teams

Optimization Criteria

* Distance
* Capacity
* Severity
* Predicted accessibility
* Future risk

---

### Dynamic Route Planning

Instead of finding the shortest path, the engine minimizes

* Travel time
* Flood risk
* Predicted future blockage
* Congestion

---

## Module 7 — Decision Validation Engine

Monitors active plans.

Whenever the environment changes,

the engine checks

```text
Has the current plan become unsafe?
```

If yes

* Recompute
* Replace
* Notify commander

Stores

* Previous decision
* New decision
* Trigger
* Reason

---

## Module 8 — Explainable AI Layer

Provides transparent explanations.

The XAI system explains

### Prediction Explanations

Why a road was predicted to flood.

Methods

* TreeLite
* Captum

---

### Decision Explanations

Why evacuation changed.

Why resources moved.

Why a road became unsafe.

---

### Natural Language Generation

LLM API
(OpenAI / Gemini / OpenAI-compatible)

Purpose

Convert structured explanations into concise operational language.

The LLM never performs prediction, optimization or decision making.
Outputs

Military-style concise explanations.

Example

> Route changed because Road R27 flood probability increased from 18% to 84% due to rapidly rising water levels and heavy rainfall.

---

# 7. Dashboard

The command dashboard displays

## Live Map

* Flood zones
* Rescue vehicles
* Hospitals
* Shelters
* Roads
* Risk heatmap

---

## AI Panel

Shows

* Current alerts
* Predictions
* Confidence
* Recommended actions

---

## Explanation Panel

Shows

* Why prediction happened
* Why decision changed
* Feature importance
* Supporting evidence

---

## Resource Panel

Displays

* Boats
* Ambulances
* Fire units
* Rescue teams

---

## Timeline

Displays

* Sensor updates
* Predictions
* Decision changes
* Resource assignments

---

# 8. Data Sources

## Static

* OpenStreetMap
* NASA DEM
* WorldPop
* Administrative boundaries

---

## Historical

* IMD Rainfall
* CWC River Levels
* ISRO Flood Maps
* Sentinel
* NASA

---

## Live

* Open-Meteo
* CWC Gauge Data

---

## Simulated

* IoT sensors
* Rescue GPS
* Emergency calls
* Shelter occupancy
* Traffic
* Road failures

---

# 9. Machine Learning Pipeline

```text
Raw Events
      │
      ▼
Feature Engineering
      │
      ▼
Flood Prediction
      │
      ▼
Disaster Spread Prediction
      │
      ▼
Decision Generation
      │
      ▼
Decision Validation
      │
      ▼
Explanation
      │
      ▼
Dashboard
```

---

# 10. Event Pipeline

```text
Simulator + Live API / Live Sources
          │
          ▼
      Protobuf
          │
          ▼
        Kafka
          │
          ▼
        Flink
          │
          ▼
 Feature Engineering
      │
      ▼
Digital Twin State Manager
          │
          ▼
 AI Prediction Layer
          │
          ▼
 Decision Engine
          │
          ▼
 Explainability Layer
          │
          ▼
       FastAPI
          │
          ▼
     WebSockets
          │
          ▼
React Dashboard
```

---

# 11. Storage Layer

## TimescaleDB

Stores

* Sensor history
* Predictions
* Weather
* Incidents
* Resources

---

## PostGIS

Stores

* Roads
* Rivers
* Shelters
* Hospitals
* Spatial queries

---

## Vector Database

ChromaDB
pip install chromadb

Stores

Historical disaster embeddings
Vector representations of historical disaster situations and operational contexts for similarity retrieval.

Supports

Similarity search

Example

> "Find the closest historical disaster."

---

# 12. Technology Stack

## Backend

* Python
* FastAPI

---

## Streaming

* Apache Kafka
* Apache Flink
* Protocol Buffers

---

## Machine Learning

* XGBoost
* PyTorch
* PyTorch Geometric
* Captum
* TreeLite

---

## Distributed Computing

* Ray

---

## Databases

* PostgreSQL
* TimescaleDB
* PostGIS
* ChromaDB

---

## Frontend

* React
* TypeScript
* Deck.gl
* MapLibre
* WebSockets

---

## Natural Language Layer

* LLM API
* (OpenAI / Gemini / OpenAI-compatible)

---

# 13. Functional Workflow

```text
Live Data
      │
      ▼
Streaming
      │
      ▼
Current World State
      │
      ▼
Future Prediction
      │
      ▼
Operational Decision
      │
      ▼
Decision Validation
      │
      ▼
Decision Updated
      │
      ▼
Explain Why
      │
      ▼
Human Commander
```

---

# 14. Human-in-the-Loop Design

The AI never directly executes high-impact actions.

Instead, it produces recommendations.

The command dashboard allows operators to:

* Accept
* Reject
* Override

Every override is stored for future analysis and model improvement.

---

# 15. Project Phases

## Phase 1

Digital Twin

* OSM download
* Road graph
* Elevation
* Infrastructure mapping

---

## Phase 2

Disaster Simulator

* Rainfall
* Flood spread
* Emergency generation

---

## Phase 3

Streaming Infrastructure

* Kafka
* Flink
* Protobuf

---

## Phase 4

Prediction Models

* XGBoost
* ST-GNN

---

## Phase 5

Decision Orchestration

* Evacuation
* Resource allocation
* Dynamic rerouting

---

## Phase 6

Explainable AI

* TreeLite
* Captum
* LLM API Integration

---

## Phase 7

Dashboard

* React
* Deck.gl
* Live visualization

---

## Phase 8

Optimization

* Ray
* ChromaDB
* Performance tuning

---

# 16. Expected Deliverables

The completed project will provide:

* A digital twin of the selected Indian state
* Live disaster simulation
* Event-driven streaming architecture
* Real-time flood prediction
* Disaster propagation prediction
* Dynamic evacuation planning
* Rescue resource orchestration
* Automatic decision validation
* Real-time explainable AI
* Interactive command dashboard
* Historical disaster retrieval
* Human-in-the-loop emergency decision support system

---

# 17. Future Scope

The architecture is intentionally modular and can later be extended to:

* Multi-disaster response
* Drone fleet orchestration
* Autonomous robotic rescue systems
* Smart city IoT integration
* Satellite-assisted disaster monitoring
* Multi-state disaster coordination
* Reinforcement learning for long-term resource optimization
* Digital twin simulation for emergency preparedness and training
