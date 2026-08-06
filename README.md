# ERDOS — Explainable Real-Time Emergency Disaster Orchestration System

A stream-first, event-driven AI platform for real-time disaster monitoring, prediction,
orchestration, validation and explainability. Initial target: urban floods in Kerala, India.

## Modules

| Module         | Responsibility                                |
|----------------|-----------------------------------------------|
| `backend`      | FastAPI REST + WebSocket layer                |
| `frontend`     | React / TypeScript command dashboard          |
| `digital_twin` | Live virtual representation of the region     |
| `streaming`    | Kafka / Flink integration                     |
| `simulator`    | Simulated disaster event generation           |
| `prediction`   | AI inference (XGBoost + ST-GNN)               |
| `orchestration`| Route planning and resource allocation        |
| `explainability`| Captum + Treelite evidence generation        |
| `llm`          | Natural-language explanation generation       |
| `database`     | PostgreSQL / PostGIS / TimescaleDB / ChromaDB |

## Documentation

See `docs/`. `PROJECT_SPEC.md` is the source of truth.

## Setup

```bash
py -3.12 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

---