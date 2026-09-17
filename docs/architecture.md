# Architecture

## Overview

AgriSense AI is a modular Flask application with a single-page dashboard
frontend. It is intentionally NOT a microservices architecture — see
"Why not more infrastructure?" below.

```
AgriSense-AI/
├── app.py                 Flask app factory + entry point
├── config/                 Central configuration
│   ├── settings.py          Paths, feature lists, dataset config
│   ├── crop_master.py       THE crop data-availability registry (see data-sources.md)
│   └── geography.py         India state/AP+Telangana district reference data
├── ml/                      Training (offline) + inference (online)
│   ├── train_crop_model.py  Trains RandomForestClassifier, writes models/
│   ├── train_yield_model.py Trains RandomForestRegressor (synthetic target)
│   ├── predictor.py         Loads trained models, runs inference ONLY
│   ├── preprocessing.py     Dataset loading/cleaning/synthetic-yield generation
│   └── explainability.py    Feature importance + "why this crop" checklist
├── services/                External integrations, one per concern
│   ├── geocoding_service.py   Nominatim search/reverse
│   ├── weather_service.py     Open-Meteo current/forecast/climate-average
│   ├── soil_service.py        SoilGrids + regional fallback + Soil Health Card validation
│   ├── soil_extraction_service.py  PDF/image soil-report text extraction
│   ├── environment_service.py Orchestrates weather+soil into one profile
│   └── risk_service.py        Rule-based rainfall/temperature/irrigation risk
├── routes/                  Flask blueprints (one per resource)
│   ├── health.py, location.py, environment.py, prediction.py, history.py
│   ├── crops.py             Crop Master + comparison
│   ├── soil.py               Manual soil validation + report upload
│   ├── farm.py                Optional local farm profile
│   └── current_farm.py       Current Farm Mode (situational analysis)
├── utils/                   validation, caching, history storage, helpers, logging
├── templates/, static/      Frontend (no HTML/JS embedded in Python)
├── models/                   Trained model artifacts + metadata.json
├── data/                     Cached dataset, local prediction history, uploads/ (transient)
├── tests/                    pytest suite (64 tests)
└── docs/                     This documentation set
```

## Data flow (Planning Mode)

```
Location (map/search/GPS/state-district)
        │
        ▼
environment_service.build_environment_profile(lat, lon)
        │           (calls weather_service + soil_service)
        ▼
merge_with_user_overrides()  ← optional manual/soil-test values
        │
        ▼
ml.predictor.predict_recommendations()
        │           (loads pre-trained models, never trains here)
        ▼
risk_service.build_risk_summary()
        │
        ▼
JSON response → frontend renders Dashboard/Recommendation/Yield/Insights/Risk
```

## Data flow (Current Farm Mode)

Same environment/soil pipeline, but instead of ranking all 22 crops, it
looks up `config.crop_master.is_crop_supported(current_crop)` first:

- If unsupported (e.g. Chilli, Tobacco) → returns weather/soil context only,
  with an explicit "no validated model coverage" message. No fabricated
  suitability or yield is generated.
- If supported → `ml.predictor.predict_for_specific_crop()` evaluates that
  one crop's suitability/yield against current conditions.

## Why not more infrastructure?

Per the project's own engineering constraints: no unnecessary
microservices, message queues, or heavy databases. Local prediction
history and the optional farm profile use plain JSON files — SQLite would
be a reasonable next step only if history/profile scale requirements grow
beyond a single farmer's local usage.

## Models are trained offline, loaded online

`app.py` never calls the training scripts on a web request. Training is a
deliberate, separate step (`python -m ml.train_crop_model`), producing
versioned artifacts in `models/` plus `models/metadata.json` recording
dataset size, accuracy, and training timestamp. The running app only
calls `ml/predictor.py::load_models()`, which fails soft (returns a
"models not trained" 503) rather than crashing if artifacts are missing.
