# datasets/

Organized data used to build the Digital Twin, train AI models and exercise live pipelines.

| Directory         | Purpose                                          |
|-------------------|--------------------------------------------------|
| `raw/`            | Downloaded raw datasets (OSM, DEM, WorldPop, IMD, CWC) |
| `processed/`      | Cleaned / merged training datasets               |
| `static/`         | Static GIS layers (boundaries, rivers, shelters) |
| `historical/`     | Historical disaster records and flood maps       |
| `live_samples/`   | Sample captures of live API / simulated events   |

Raw and processed data are git-ignored; see `.gitignore`.
