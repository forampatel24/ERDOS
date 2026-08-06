# ML_PIPELINE.md

# Machine Learning Pipeline

**Project:** Explainable Real-Time Emergency Disaster Orchestration System (ERDOS)

**Version:** 1.0

---

# 1. Purpose

This document describes the complete Machine Learning lifecycle of ERDOS.

It covers the entire AI workflow from collecting raw datasets to generating real-time predictions during an active disaster.

Unlike the Architecture document, this document focuses only on the AI models, data preparation, training pipeline, evaluation methodology and inference workflow.

---

# 2. AI Philosophy

The AI subsystem has one responsibility:

> Predict the future state of the disaster.

It does **not**

- Plan evacuation routes
- Select shelters
- Allocate rescue teams
- Explain decisions
- Generate natural language

Those responsibilities belong to later system components.

---

# 3. AI Pipeline Overview

```text
Raw Datasets
      │
      ▼
Data Cleaning
      │
      ▼
Data Preprocessing
      │
      ▼
Feature Engineering
      │
      ▼
Training Dataset
      │
      ▼
Model Training
      │
      ▼
Model Validation
      │
      ▼
Model Evaluation
      │
      ▼
Model Export
      │
      ▼
Inference Pipeline
      │
      ▼
Prediction Output
```

---

# 4. Machine Learning Components

The AI subsystem consists of two independent prediction models.

## Model 1

Road Flood Prediction

Algorithm

- XGBoost

Purpose

Predict the probability that an individual road segment becomes flooded.

---

## Model 2

Flood Propagation Prediction

Algorithm

Spatio-Temporal Graph Neural Network (ST-GNN)

Framework

PyTorch Geometric

Purpose

Predict how flooding spreads throughout the road network over time.

---

# 5. Training Data Sources

The training pipeline combines multiple datasets.

## Geographic Data

- OpenStreetMap
- Administrative Boundaries
- Road Network

Purpose

Build graph topology.

---

## Terrain Data

- NASA DEM

Purpose

Extract

- Elevation
- Slope
- Water Flow Direction

---

## Weather Data

- IMD Rainfall
- NASA GPM

Purpose

Historical rainfall information.

---

## River Data

- CWC River Levels

Purpose

Historical river behaviour.

---

## Flood Maps

- ISRO Flood Maps
- Sentinel Satellite Images

Purpose

Ground truth labels.

---

## Population Data

- WorldPop

Purpose

Population density.

---

# 6. Dataset Preparation

Raw datasets require preprocessing before training.

Steps

```
Raw Dataset

↓

Cleaning

↓

Missing Value Handling

↓

Coordinate Conversion

↓

Feature Extraction

↓

Dataset Merge

↓

Training Dataset
```

---

# 7. Data Cleaning

Cleaning operations include

- Duplicate removal
- Missing value handling
- Coordinate normalization
- Timestamp normalization
- Invalid sensor removal

---

# 8. Feature Engineering

The AI models never receive raw data directly.

Instead, engineered features are created.

---

## Weather Features

- Rainfall
- Rainfall Rate
- Rainfall Accumulation
- Rainfall Trend

---

## River Features

- River Level
- Rise Rate
- Overflow Risk

---

## Terrain Features

- Elevation
- Slope
- Distance to River

---

## Road Features

- Road Length
- Road Type
- Number of Lanes
- Bridge Presence

---

## Graph Features

- Node Degree
- Neighbor Connectivity
- Distance to Hospital
- Distance to Shelter

---

## Historical Features

- Previous Flood Events
- Historical Flood Frequency
- Historical Maximum Water Level

---

## Dynamic Features

- Current Flood Status
- Neighbor Flood Status
- Traffic Density
- Shelter Occupancy
- Resource Density

---

# 9. Training Dataset

Every row represents one road segment at one point in time.

Example

| Feature | Value |
|----------|------:|
| Rainfall | 54 mm |
| Elevation | 8 m |
| River Level | 4.2 m |
| Distance to River | 230 m |
| Road Type | Primary |
| Neighbor Flooded | Yes |
| Flood Label | Flooded |

---

# 10. Model 1 - Road Flood Prediction

Algorithm

XGBoost

Input

Engineered road features.

Output

Flood probability.

Example

```
Road R21

↓

Flood Probability

0.91
```

---

# 11. Model 2 - Flood Propagation Prediction

Framework

PyTorch Geometric

Architecture

Spatio-Temporal Graph Neural Network

Graph Representation

Nodes

- Road Intersections
- Bridges
- Hospitals
- Shelters

Edges

- Roads

Node Features

- Rainfall
- Water Level
- Elevation
- Current Flood Status

Output

Predicted flood propagation across the graph.

---

# 12. Model Training Pipeline

```
Training Dataset

↓

Train/Test Split

↓

Model Training

↓

Hyperparameter Tuning

↓

Validation

↓

Evaluation

↓

Model Export
```

---

# 13. Train-Test Split

Suggested

Training

70%

Validation

15%

Testing

15%

Random shuffling should not be used for temporal datasets.

Chronological splitting is preferred.

---

# 14. Hyperparameter Optimization

For XGBoost

Tune

- Learning Rate
- Max Depth
- Number of Trees
- Subsample
- Regularization

---

For ST-GNN

Tune

- Hidden Dimensions
- Number of Layers
- Learning Rate
- Batch Size
- Temporal Window

---

# 15. Evaluation Metrics

## XGBoost

- Accuracy
- Precision
- Recall
- F1 Score
- ROC-AUC

---

## ST-GNN

- Precision
- Recall
- F1 Score
- RMSE
- MAE

---

# 16. Model Export

After training, models are stored.

```
models/

prediction/

checkpoints/

trained_models/
```

Files

```
xgboost_model.pkl

stgnn_model.pt
```

---

# 17. Inference Pipeline

After deployment, models no longer train.

They only perform inference.

```
Digital Twin

↓

Engineered Features

↓

XGBoost

↓

Flood Probability
```

Parallel

```
Digital Twin Graph

↓

ST-GNN

↓

Flood Propagation
```

Both predictions are merged.

---

# 18. Prediction Output

The Prediction Layer produces a structured prediction object.

Example

```json
{
  "road_id":"R21",
  "flood_probability":0.91,
  "predicted_accessibility":"Blocked",
  "future_spread":["R22","R23"],
  "confidence":0.94
}
```

This output becomes the input to the Orchestration Engine.

---

# 19. Explainability Integration

The Prediction Layer itself does not generate explanations.

Instead

```
Prediction Output

↓

Captum

↓

Treelite

↓

Structured Explanation Object
```

This object is forwarded to the Explainability Layer.

---

# 20. Model Retraining

Models are retrained offline.

Triggers

- New historical datasets
- Seasonal updates
- Performance degradation
- New disaster data

The live system never retrains during an active disaster.

---

# 21. Pipeline Responsibilities

| Component | Responsibility |
|------------|----------------|
| Dataset Collection | Acquire raw data |
| Data Cleaning | Prepare datasets |
| Feature Engineering | Generate model inputs |
| XGBoost | Road flood prediction |
| ST-GNN | Flood propagation prediction |
| Evaluation | Measure model quality |
| Model Export | Save trained models |
| Inference | Generate live predictions |

---

# 22. Future Improvements

Potential enhancements

- Graph Attention Networks (GAT)
- Graph Transformers
- Multi-Hazard Prediction
- Online Learning
- Transfer Learning
- Self-Supervised Learning
- Physics-Informed Neural Networks
- Ensemble Models

---

# 23. ML Pipeline Summary

```text
Historical Datasets
        │
        ▼
Data Cleaning
        │
        ▼
Feature Engineering
        │
        ▼
Training Dataset
        │
        ▼
XGBoost Training
        │
        ├───────────────┐
        ▼               │
Road Prediction         │
                        │
Road Graph              │
        │               │
        ▼               │
ST-GNN Training         │
        │               │
        └──────┬────────┘
               ▼
      Model Evaluation
               ▼
        Trained Models
               ▼
      Live Inference
               ▼
     Prediction Output
               ▼
      Orchestration Engine
```

---

# 24. Conclusion

The Machine Learning Pipeline is responsible only for forecasting the future state of the disaster environment.

It transforms raw historical and geospatial datasets into trained AI models capable of predicting road flooding and flood propagation in real time. These predictions become the foundation upon which the Orchestration Engine, Explainability Layer and Dashboard operate.