# PROJECT_STRUCTURE.md

# Project Structure

**Project:** Explainable Real-Time Emergency Disaster Orchestration System (ERDOS)

**Version:** 1.0

---

# 1. Purpose

This document defines the complete repository structure of ERDOS.

It specifies

- Folder hierarchy
- Module ownership
- File organization
- Import boundaries
- Naming conventions

The objective is to maintain a clean, scalable and modular codebase throughout development.

---

# 2. Repository Overview

```text
ERDOS/
│
├── backend/
├── frontend/
├── datasets/
├── models/
├── docs/
├── tests/
├── scripts/
├── notebooks/
├── logs/
├── config/
├── .env
├── requirements.txt
├── package.json
├── README.md
└── LICENSE
```

---

# 3. Backend Structure

```text
backend/
│
├── api/
│   ├── routes/
│   ├── websocket/
│   ├── middleware/
│   └── dependencies/
│
├── digital_twin/
│
├── streaming/
│   ├── kafka/
│   ├── flink/
│   └── producers/
│
├── simulator/
│
├── prediction/
│   ├── xgboost/
│   ├── stgnn/
│   └── inference/
│
├── orchestration/
│
├── explainability/
│
├── llm/
│
├── database/
│   ├── postgres/
│   ├── timescaledb/
│   ├── chromadb/
│   └── migrations/
│
├── services/
│
├── schemas/
│
├── models/
│
├── utils/
│
└── main.py
```

---

# 4. Frontend Structure

```text
frontend/
│
├── public/
│
├── src/
│   ├── assets/
│   ├── components/
│   ├── pages/
│   ├── layouts/
│   ├── hooks/
│   ├── context/
│   ├── services/
│   ├── websocket/
│   ├── maps/
│   ├── store/
│   ├── styles/
│   ├── types/
│   ├── utils/
│   ├── App.tsx
│   └── main.tsx
│
├── package.json
└── vite.config.ts
```

---

# 5. Dataset Structure

```text
datasets/
│
├── raw/
│
├── processed/
│
├── static/
│
├── historical/
│
├── live_samples/
│
└── README.md
```

---

# 6. Model Structure

```text
models/
│
├── checkpoints/
│
├── trained/
│
├── exports/
│
└── metadata/
```

---

# 7. Documentation Structure

```text
docs/
│
├── PROJECT_SPEC.md
├── ARCHITECTURE.md
├── DATA_PIPELINE.md
├── DATABASE_SCHEMA.md
├── API_SPEC.md
├── ML_PIPELINE.md
├── FEATURES.md
├── RESOURCES.md
├── PROJECT_STRUCTURE.md
├── ROADMAP.md
└── VERSIONS.md
```

---

# 8. Test Structure

```text
tests/
│
├── backend/
├── frontend/
├── prediction/
├── orchestration/
├── api/
└── integration/
```

---

# 9. Configuration

```text
config/
│
├── development.py
├── production.py
├── logging.py
└── constants.py
```

---

# 10. Scripts

Reusable utility scripts.

```text
scripts/
│
├── download_data.py
├── preprocess.py
├── train_models.py
├── evaluate_models.py
├── build_digital_twin.py
└── generate_embeddings.py
```

---

# 11. Naming Conventions

Folders

```
snake_case
```

Python files

```
snake_case.py
```

Python Classes

```
PascalCase
```

Python Variables

```
snake_case
```

React Components

```
PascalCase.tsx
```

React Hooks

```
useSomething.ts
```

Constants

```
UPPER_CASE
```

---

# 12. Import Rules

The architecture is layered.

Allowed dependencies

```text
Frontend

↓

API

↓

Services

↓

Digital Twin

↓

Prediction

↓

Orchestration

↓

Explainability

↓

LLM

↓

Database
```

Lower layers never import higher layers.

Examples

✅ Prediction → Database

❌ Database → Prediction

---

# 13. Module Responsibilities

| Module | Responsibility |
|----------|----------------|
| digital_twin | Maintain current world state |
| streaming | Kafka and Flink integration |
| simulator | Generate simulated events |
| prediction | AI inference |
| orchestration | Route planning and resource allocation |
| explainability | Captum and Treelite integration |
| llm | Natural-language generation |
| database | Data persistence |
| api | REST APIs and WebSockets |
| frontend | User interface |

---

# 14. Coding Guidelines

- Single Responsibility Principle
- Modular architecture
- Type hints for Python
- Pydantic for request validation
- Reusable utility functions
- No hardcoded values
- Environment variables for secrets
- Consistent logging across modules

---

# 15. Logging Structure

```text
logs/
│
├── backend.log
├── prediction.log
├── orchestration.log
├── api.log
└── errors.log
```

---

# 16. Development Workflow

```text
Build Digital Twin

↓

Implement Streaming

↓

Build Prediction Layer

↓

Implement Orchestration

↓

Implement Explainability

↓

Integrate LLM

↓

Build Dashboard

↓

Testing

↓

Deployment
```

---

# 17. Repository Philosophy

The repository follows a layered architecture where every module has a single responsibility.

Each directory owns one major subsystem of the platform and communicates only through clearly defined interfaces.

This organization minimizes coupling, improves maintainability and allows the project to scale without restructuring the repository.

---

# 18. Final Repository Layout

```text
ERDOS/
│
├── backend/
├── frontend/
├── datasets/
├── models/
├── docs/
├── tests/
├── scripts/
├── notebooks/
├── logs/
├── config/
├── .env
├── requirements.txt
├── package.json
├── README.md
└── LICENSE
```