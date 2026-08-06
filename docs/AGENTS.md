# AGENTS.md

# ERDOS AI Agent Guidelines

**Project:** Explainable Real-Time Emergency Disaster Orchestration System (ERDOS)

**Version:** 1.0

---

# Purpose

This document defines the implementation rules that every AI coding agent must follow while contributing to ERDOS.

The objective is to ensure that every implementation remains consistent with the approved project architecture, documentation, and engineering standards.

This document is the implementation contract for the repository.

---

# Project Overview

ERDOS is an Explainable Real-Time Emergency Disaster Orchestration System designed to assist emergency responders during active disasters.

The platform continuously collects environmental data, updates a Digital Twin of the disaster environment, predicts future disaster evolution, recommends operational decisions, explains every recommendation, and presents everything through a real-time command dashboard.

The system follows a Stream-First, Event-Driven Architecture.

---

# Documentation Hierarchy

Before implementing any feature, always read the project documentation.

Documentation priority:

1. PROJECT_SPEC.md
2. ARCHITECTURE.md
3. DATA_PIPELINE.md
4. DATABASE_SCHEMA.md
5. API_SPEC.md
6. ML_PIPELINE.md
7. PROJECT_STRUCTURE.md
8. FEATURES.md
9. RESOURCES.md

If documentation conflicts are found:

- Stop implementation.
- Report the conflict.
- Wait for clarification.

Never make architectural assumptions.

---

# Implementation Philosophy

Implementation must follow the documentation exactly.

The documentation represents the approved system design.

Do not redesign the architecture during implementation.

Do not replace technologies.

Do not merge modules.

Do not introduce additional architectural layers.

Only implement what is already documented.

---

# Development Environment

Target development environment

- Windows 11
- Python 3.12+
- Node.js (Latest LTS)
- PostgreSQL
- TimescaleDB
- PostGIS
- ChromaDB

The project should run entirely on a local machine.

Do not assume

- Docker
- Kubernetes
- GPU acceleration
- Cloud infrastructure

Every component should work using standard local installation procedures.

---

# Architecture Rules

The architecture is divided into independent layers.

Each layer has one responsibility.

Lower layers must never depend on higher layers.

Architecture flow:

```
Data Layer

↓

Digital Twin

↓

Prediction Layer

↓

Orchestration Engine

↓

Decision Validation

↓

Explainability Layer

↓

Natural Language Layer

↓

Backend API

↓

Frontend Dashboard
```

---

# Module Responsibilities

## Data Layer

Responsible for

- Data ingestion
- Streaming
- Database communication

Must never

- perform predictions
- perform orchestration
- generate explanations

---

## Digital Twin

Responsible for

- Maintaining the current virtual state of the disaster environment

Must never

- perform predictions
- allocate resources
- generate routes

---

## Prediction Layer

Responsible for

- Flood prediction
- Flood propagation prediction
- AI inference

Must never

- allocate resources
- generate evacuation plans
- explain predictions

---

## Orchestration Engine

Responsible for

- Route planning
- Shelter selection
- Resource allocation
- Operational recommendations

Must never

- predict disasters
- generate explanations

---

## Decision Validation Engine

Responsible for

- Monitoring active recommendations
- Detecting unsafe plans
- Triggering replanning

Must never

- perform AI prediction

---

## Explainability Layer

Responsible for

- Captum integration
- Treelite integration
- Feature attribution
- Decision evidence generation

Must never

- make decisions
- perform prediction

---

## Natural Language Layer

Responsible only for converting structured explanations into concise operational language.

The LLM API must never

- predict disasters
- allocate resources
- optimize routes
- generate operational decisions

---

## Backend

Responsible for

- REST APIs
- WebSockets
- Authentication
- Service orchestration

Business logic belongs in backend services, not in API route files.

---

## Frontend

Responsible only for visualization.

The frontend must never contain

- prediction logic
- orchestration logic
- database logic

---

# Coding Standards

Follow these principles throughout the project.

- Single Responsibility Principle
- Separation of Concerns
- Clean Architecture
- Modular Design
- Reusable Components
- Strong Type Hints
- Consistent Naming
- Small Functions
- Clear Documentation

Avoid

- duplicated code
- unnecessary abstractions
- deeply nested functions
- hardcoded values

---

# Repository Rules

Follow the folder structure defined in PROJECT_STRUCTURE.md.

Do not

- create unnecessary directories
- duplicate modules
- place files in incorrect locations
- reorganize the repository without approval

---

# Database Rules

Database implementation must follow DATABASE_SCHEMA.md exactly.

Do not

- rename tables
- rename columns
- introduce undocumented relationships
- store AI models inside databases

Use

- PostgreSQL for relational data
- PostGIS for spatial data
- TimescaleDB for time-series data
- ChromaDB for vector embeddings

---

# API Rules

Backend implementation must follow API_SPEC.md.

Requirements

- Versioned endpoints
- REST conventions
- JSON request/response
- Proper HTTP status codes
- WebSockets for live updates

Never expose internal AI modules directly through public APIs.

---

# Machine Learning Rules

Follow ML_PIPELINE.md.

The AI layer is responsible only for prediction.

Models

- XGBoost
- Spatio-Temporal Graph Neural Network

Never allow the AI models to

- generate explanations
- allocate resources
- perform orchestration

---

# Explainability Rules

Every prediction and every operational recommendation must be explainable.

The Explainability Layer produces structured evidence.

The Natural Language Layer converts that evidence into human-readable text.

Keep these responsibilities separate.

---

# Error Handling

If any of the following occur

- missing documentation
- unclear requirements
- architectural conflicts
- dependency conflicts
- inconsistent specifications

Stop implementation immediately.

Report the issue.

Do not invent missing functionality.

---

# Logging

Every major subsystem should maintain independent logs.

Suggested logs

```
logs/

backend.log

prediction.log

orchestration.log

database.log

api.log

errors.log
```

Use structured logging wherever possible.

---

# Git Guidelines

Each commit should represent one logical change.

Examples

- Build Digital Twin module
- Implement Prediction API
- Add PostgreSQL schema
- Implement Flood Prediction

Avoid large mixed-purpose commits.

---

# Definition of Done

A task is complete only if

- It follows the documentation.
- It follows the architecture.
- It compiles successfully.
- It does not break existing modules.
- It remains modular.
- It is readable.
- It is maintainable.

---

# Forbidden Actions

Never

- redesign the architecture
- replace approved technologies
- modify documentation without approval
- hardcode secrets
- commit API keys
- bypass the Digital Twin
- place business logic in the frontend
- allow the LLM to make operational decisions
- tightly couple independent modules

---
# Documentation Responsibilities

Every implementation task has a corresponding design document.

Before modifying or implementing a subsystem, consult the appropriate documentation.

| Document | Purpose | Read Before Working On |
|----------|---------|------------------------|
| PROJECT_SPEC.md | Overall project vision and scope | Any implementation |
| ARCHITECTURE.md | System architecture and module interactions | Backend, Frontend, AI, Streaming |
| DATA_PIPELINE.md | End-to-end data movement | Kafka, Flink, Digital Twin, Prediction |
| DATABASE_SCHEMA.md | Database structure and relationships | PostgreSQL, TimescaleDB, PostGIS, ChromaDB |
| API_SPEC.md | REST APIs and WebSocket contracts | FastAPI Backend |
| ML_PIPELINE.md | AI training and inference pipeline | XGBoost, ST-GNN, Feature Engineering |
| FEATURES.md | Functional capabilities of the system | Dashboard, Backend, AI |
| RESOURCES.md | Technologies, datasets, APIs, libraries | Environment setup and dependencies |
| PROJECT_STRUCTURE.md | Repository layout and module ownership | Repository organization |
| AGENTS.md | AI implementation rules | Every task |
| ROADMAP.md | Development milestones and implementation phases | Planning work |
| VERSIONS.md | Architecture and feature evolution history | Understanding project changes |

No implementation should begin without consulting the relevant documentation.

# Required Workflow

For every implementation task, follow this workflow:

1. Understand the requested feature.
2. Identify the affected subsystem.
3. Read the relevant documentation.
4. Verify that no documentation conflicts exist.
5. Plan the implementation.
6. Implement only the requested functionality.
7. Validate that the implementation follows the documented architecture.
8. Ensure no existing functionality is broken.
9. Do not modify documentation unless explicitly instructed.

This workflow is mandatory for every implementation task.