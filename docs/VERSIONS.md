# VERSIONS.md

Tracks version changes and technology replacements for ERDOS.

| Version | Date | Change |
|---------|------|--------|
| 1.0.0   | 2026-08-06 | Initial scaffold. Canonical stack per `RESOURCES.md`. |
| 1.1.0   | 2026-09-25 | Phases 1–2: Digital Twin + Simulator — OSM road graph, elevation, signals, `SimulationEngine` (weather/river/sensors/GPS/traffic/road-failure), 7 roads/3 shelters/6 resources seeded (Kochi 9.9312,76.2673). |
| 1.2.0   | 2026-09-25 | Phase 3: Streaming — `kafka-python` `KAFKA_ENABLED=true` producers (weather/river/simulator) + `EventConsumer` in lifespan, pure-Python `FeatureEngineer` sliding-window, Protobuf `event_pb2` schemas. |
| 1.3.0   | 2026-09-25 | Backend API (Phase 6/7): REST CRUD (incidents/shelters/resources/roads), WebSocket `/ws`, JWT auth, error handling; fixes for param-mismatch/enum-string/geometry bugs. `100 tests` baseline. |
| 1.4.0   | 2026-09-25 | Database + Vector layer: PostGIS 3.6 / TimescaleDB 2.29 (PostgreSQL 18.4 `D:\PostreSQL`), migration `0001_initial`, `session_scope` + `SessionLocal` persistence for twin/incidents/predictions/explanations in `backend/main.py`; ChromaDB 1.5.9 HNSW `M=16 efConstruction=200 efSearch=100`, `seed_historical_disasters` (5 samples) + retrieval wired into `ExplainabilityService` (`similar_disasters`). |
| 1.5.0   | 2026-09-25 | Prediction — XGBoost 3.4 (12 features, `xgboost_model.pkl`) + ST-GNN `SpatioTemporalGNN` (GRU+GraphConv, 4→32→1, horizon 6, 27 KB `stgnn_model.pt` 60 epochs val 1.0) with heuristic fallback; fixes for `model.py` recursion + `torch_available`. |
| 1.6.0   | 2026-09-25 | Explainability + LLM — `prediction_explainer` (XGBoost `pred_contribs` SHAP → Treelite → Captum → heuristic, counterfactuals), `decision_explainer` (shelter/route/resource evidence), `structured_explanation`; Groq OpenAI-compatible `LLMClient` (`httpx`, `https://api.groq.com/openai/v1`, `llama-3.3-70b-versatile`) + `prompts`/`generator` with templated fallback, `narrative` field on `PredictionExplanation`/`DecisionExplanation`. |
| 1.7.0   | 2026-09-25 | Frontend Phase 7 — React 18 + Vite 6 + Leaflet 1.9 dark (`CartoDB dark_all`), Zustand, glass dark theme (Inter/JetBrains Mono), live map (roads colored by risk, heatmap `500m`, shelters/resources/incidents markers, planned route), KPI cards, predictions table, models/health, shelters/resources logistics, evacuation/allocate forms, SHAP + LLM narratives + Chroma similar disasters; `frontend/dist` built `193KB` gz `59KB`. |
| 1.8.0   | 2026-09-25 | Phase 8 Optimization + Coverage — `backend/optimization` (`ray_utils` parallel predict/route with sequential fallback, `performance` TTLCache/BatchProcessor/timed, `chroma_tuning` batch_search/benchmark), embedding/prediction caches, Ray init best-effort in lifespan; tests expanded `100→182` (`prediction`/`explainability`/`llm`/`database`/`simulator`/`optimization`). |
