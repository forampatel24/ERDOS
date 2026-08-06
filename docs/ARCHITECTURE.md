# ARCHITECTURE.md

# Explainable Real-Time Emergency Disaster Orchestration System (ERDOS)

**Version:** 1.0

**Status:** Frozen Architecture

---

# 1. Purpose

This document describes the complete software architecture of the Explainable Real-Time Emergency Disaster Orchestration System (ERDOS).

Unlike the Project Specification, which explains **what** the system does, and the Data Pipeline, which explains **how data flows**, this document explains **how every software component is organized, how each module communicates, and how the complete platform functions as a single integrated system.**

---

# 2. Architectural Philosophy

The system follows a **Stream-First, Event-Driven Architecture**.

Rather than processing requests one at a time, the platform continuously processes incoming events and updates a live Digital Twin of the disaster environment.

The architecture is built around five core principles.

## 2.1 Event Driven

Every change in the environment is treated as an event.

Examples

- Rainfall update
- River level update
- Emergency call
- Rescue boat movement
- Shelter occupancy change

Events continuously drive the entire platform.

---

## 2.2 Stream Processing

The system processes information while it is arriving.

Incoming events are immediately processed rather than stored and analyzed later.

---

## 2.3 Digital Twin

A continuously updated virtual representation of Kerala acts as the single source of truth for the entire system.

Every AI model, optimization algorithm and dashboard component operates on this Digital Twin.

---

## 2.4 Explainable AI

Every operational recommendation must be accompanied by evidence explaining why the recommendation was generated.

No recommendation is presented without an explanation.

---

## 2.5 Human-in-the-loop

The system never executes disaster response actions automatically.

It only recommends actions.

Human commanders always retain final authority.

---

# 3. High-Level Architecture

```text
                    STATIC DATASETS
(OSM, DEM, Population, Historical Flood Data)
                        │
                        ▼
               Digital Twin Builder
                        │
──────────────────────────────────────────────

 Live APIs                  Simulation Engine
(Weather, Rivers)      (IoT, Calls, GPS, Traffic)
        │                     │
        └─────────────┬───────┘
                      ▼
               Apache Kafka
                      ▼
               Apache Flink
                      ▼
      Feature Engineering Pipeline
                      ▼
      Digital Twin State Manager
                      ▼
          Prediction Layer
      (XGBoost + ST-GNN)
                      ▼
       Orchestration Engine
                      ▼
 Decision Validation Engine
                      ▼
     Explainability Layer
    (Captum + Treelite)
                      ▼
 Structured Explanation Object
                      ▼
          LLM API
                      ▼
      FastAPI + WebSockets
                      ▼
 React Command Dashboard
```

---

# 4. Architecture Layers

The platform is divided into five logical layers.

```
Data Layer

↓

Prediction Layer

↓

Orchestration Layer

↓

Explainability Layer

↓

Presentation Layer
```

Each layer has exactly one responsibility.

---

# 5. Component Architecture

## 5.1 Digital Twin Builder

### Purpose

Creates the initial virtual model of Kerala.

### Inputs

- OpenStreetMap
- NASA DEM
- Population datasets
- Administrative boundaries
- Rivers
- Hospitals
- Shelters

### Outputs

Digital Twin

### Responsibilities

- Import GIS data
- Build road graph
- Build infrastructure graph
- Initialize system state

### Does NOT

- Run AI
- Predict floods
- Generate routes

---

## 5.2 Simulation Engine

### Purpose

Generate operational events unavailable through public APIs.

### Simulated Components

- IoT Sensors
- Emergency Calls
- Rescue Requests
- Shelter Occupancy
- Ambulance GPS
- Boat GPS
- Traffic Updates
- Road Failures

### Outputs

Kafka Events

---

## 5.3 Live Data Services

### Purpose

Collect live environmental information.

Sources

- Weather API
- River Level API

Outputs

Kafka Events

---

## 5.4 Apache Kafka

### Purpose

Event Streaming Platform

Responsibilities

- Receive events
- Store events
- Distribute events

Kafka performs no analytics.

It only transports information.

---

## 5.5 Apache Flink

### Purpose

Real-time Stream Processing

Responsibilities

- Event aggregation
- Sliding windows
- Feature Engineering
- Stream transformations

Outputs

Engineered Features

---

## 5.6 Digital Twin State Manager

### Purpose

Maintain the current state of Kerala.

### Responsibilities

Update

- Roads
- Weather
- Rivers
- Resources
- Shelters
- Traffic
- Flood Status

### Acts As

Single Source of Truth

Every downstream component reads from this module.

---

## 5.7 Prediction Layer

Contains two independent AI models.

---

### Road Flood Prediction

Algorithm

XGBoost

Responsibilities

Predict

- Road Flood Probability
- Road Accessibility

---

### Flood Propagation Prediction

Algorithm

Spatio-Temporal Graph Neural Network

Framework

PyTorch Geometric

Responsibilities

Predict

- Flood Spread
- Infrastructure Impact
- Future Disaster Evolution

---

### Prediction Output

Both models together produce the predicted future state of the Digital Twin.

---

## 5.8 Orchestration Engine

### Purpose

Transform predictions into operational decisions.

Responsibilities

- Shelter Selection
- Route Planning
- Resource Allocation
- Ambulance Assignment
- Boat Assignment
- Dynamic Replanning

Uses

- Graph Algorithms
- Optimization
- Constraint Solving

The engine does not use an LLM.

---

## 5.9 Decision Validation Engine

### Purpose

Continuously monitor active plans.

Responsibilities

- Detect unsafe plans
- Trigger replanning
- Compare old and new recommendations

Example

Old Route

↓

Road R27

↓

Flood Prediction changes

↓

Route recalculated

---

## 5.10 Explainability Layer

### Purpose

Generate structured evidence for every prediction and operational recommendation.

Techniques

- Captum
- Treelite

Outputs

- Feature Importance
- Decision Paths
- Structured Explanation Object

---

## 5.11 Natural Language Layer

Purpose

Convert structured explanations into concise operational language.

Technology

LLM API

Examples

- OpenAI API
- Gemini API

The LLM never performs

- Prediction
- Optimization
- Decision Making

It only converts structured evidence into natural language.

---

## 5.12 Backend

Technology

FastAPI

Responsibilities

- REST APIs
- Authentication
- WebSockets
- Request Handling
- LLM Communication

---

## 5.13 Frontend

Technology

React

Responsibilities

- Live Dashboard
- Interactive Map
- Timeline
- Resource View
- Alert Panel
- Explanation Panel

---

# 6. Component Communication

| Component | Communicates With | Protocol |
|------------|------------------|----------|
| Weather Producer | Kafka | Protobuf |
| River Producer | Kafka | Protobuf |
| Simulator | Kafka | Protobuf |
| Kafka | Flink | Event Streams |
| Flink | Digital Twin | Python Objects |
| Digital Twin | Prediction Layer | Python |
| Prediction Layer | Orchestration Engine | Python |
| Orchestration Engine | Decision Validation | Python |
| Decision Validation | Explainability | Python |
| Explainability | LLM API | JSON |
| LLM API | FastAPI | JSON |
| FastAPI | React Dashboard | WebSockets |

---

# 7. Dependency Hierarchy

```text
React Dashboard

↑

FastAPI Backend

↑

LLM API

↑

Explainability Layer

↑

Decision Validation Engine

↑

Orchestration Engine

↑

Prediction Layer

↑

Digital Twin State Manager

↑

Apache Flink

↑

Apache Kafka

↑

Live APIs

Simulation Engine

Static Datasets
```

Lower components never depend on higher components.

---

# 8. Event Lifecycle

## Example: Rainfall Update

```
Weather API

↓

Weather Producer

↓

Kafka

↓

Apache Flink

↓

Feature Engineering

↓

Digital Twin Updated

↓

Prediction Layer

↓

Orchestration Engine

↓

Decision Validation

↓

Explainability Layer

↓

LLM API

↓

FastAPI

↓

WebSockets

↓

Dashboard
```

---

## Example: Emergency Call

```
Citizen Emergency Call

↓

Simulation Engine

↓

Kafka

↓

Apache Flink

↓

Digital Twin

↓

Resource Allocation

↓

Explanation

↓

Dashboard
```

---

# 9. Component Responsibilities

| Component | Allowed | Not Responsible For |
|------------|----------|---------------------|
| Digital Twin | Maintain system state | Prediction |
| Simulation | Generate events | AI Prediction |
| Kafka | Event Streaming | Analytics |
| Flink | Stream Processing | AI Decisions |
| Prediction Layer | Forecast disasters | Route Planning |
| Orchestration | Operational Planning | Natural Language |
| Decision Validation | Monitor plans | Prediction |
| Explainability | Generate evidence | Decision Making |
| LLM API | Natural language generation | Prediction, Optimization |
| Dashboard | Visualization | Business Logic |

---

# 10. Fault Tolerance

If Weather API fails

- Use latest cached value

If River API fails

- Continue with previous readings

If Kafka fails

- Buffer events temporarily

If Flink fails

- Pause prediction pipeline

If LLM API fails

- Display structured explanation directly

Prediction and orchestration continue even without the LLM.

---

# 11. Scalability

Current Target

- Single Laptop
- Kerala

Future

- Multiple States
- National Deployment
- Distributed Kafka Cluster
- Multiple AI Nodes

No architectural redesign is required for scaling.

---

# 12. Security

Authentication

- JWT

Communication

- HTTPS
- Secure WebSockets

Secrets

- Environment Variables

Input Validation

- Pydantic

---

# 13. Performance Goals

| Component | Target |
|------------|--------|
| Weather Update | < 2 sec |
| Kafka Processing | < 100 ms |
| Flink Processing | < 500 ms |
| Prediction | < 2 sec |
| Route Planning | < 2 sec |
| Explanation | < 3 sec |
| Dashboard Update | < 1 sec |

---

# 14. Folder Mapping

```text
backend/
│
├── api/
├── services/
├── streaming/
├── simulator/
├── digital_twin/
├── prediction/
├── orchestration/
├── explainability/
├── database/
├── websocket/
└── utils/

frontend/
│
├── components/
├── pages/
├── hooks/
├── services/
├── store/
├── maps/
└── assets/
```

---

# 15. Architecture Summary

The architecture follows a layered, event-driven design where every incoming event updates a live Digital Twin of Kerala.

The Prediction Layer forecasts future disaster conditions, the Orchestration Engine computes operational decisions, the Explainability Layer produces structured evidence, and the LLM API converts those explanations into clear operational language.

Each module has a single responsibility, communicates only with adjacent layers, and contributes to a transparent, scalable, and explainable disaster response platform.