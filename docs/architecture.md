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
│   ├── crop_agronomy_data.py THE crop agronomy/economics registry (seed, fertilizer,
│   │                          duration, plant protection - see data-sources.md §7)
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
│   ├── risk_service.py        Rule-based rainfall/temperature/irrigation risk
│   └── agronomy_service.py    Crop Plan Layer: scales agronomy data to farm
│                               area and assembles the (honestly-unpriced) cost
│                               breakdown - see "Crop Plan Layer" below
├── routes/                  Flask blueprints (one per resource)
│   ├── health.py, location.py, environment.py, prediction.py, history.py
│   ├── crops.py             Crop Master + comparison
│   ├── soil.py               Manual soil validation + report upload
│   ├── farm.py                Optional local farm profile
│   ├── current_farm.py       Current Farm Mode (situational analysis)
│   └── crop_plan.py          GET /api/crop-plan/<crop_id>?area_ha=.. (Crop Plan Layer)
├── utils/                   validation, caching, history storage, helpers, logging
├── templates/, static/      Frontend (no HTML/JS embedded in Python)
│                            static/js/crop_plan.js renders the Crop Plan & Economics page
├── models/                   Trained model artifacts + metadata.json
├── data/                     Cached dataset, local prediction history, uploads/ (transient)
├── tests/                    pytest suite (95 tests)
└── docs/                     This documentation set

## Crop Plan Layer (agronomy + economics)

Added to complement the ML prediction pipeline without touching it:

```
ML pipeline (unchanged):
  Location → Environmental data → ML crop recommendation → ML yield estimate → ranked crops

Crop Plan Layer (new, independent):
  crop_id + farm area_ha
    → config/crop_agronomy_data.py   (single source of truth, sourced values only)
    → services/agronomy_service.py   (scales quantity_per_ha × area_ha; builds cost
                                       breakdown as quantity × unit_price = cost,
                                       currently unpriced everywhere - see data-sources.md §7)
    → GET /api/crop-plan/<crop_id>   (routes/crop_plan.py)
    → static/js/crop_plan.js          (renders Crop Plan & Economics page)
```

This is a **read-only consumer** of `ml/predictor.py`'s output (it takes a
`crop_id` string, typically `top_crop.crop` from a prediction response) and
never recomputes, overrides, or feeds back into the crop/yield models. It is
exposed as its own endpoint rather than folded into `/api/predict/*` so the
two concerns - ML suitability/yield vs. agronomic planning/cost - stay
independently testable and independently extensible (see
`docs/limitations.md` for what is not yet covered, and the "Future
extensibility" note below).

**Future extensibility:** the schema in `crop_agronomy_data.py` and the
cost-calculation shape in `agronomy_service.py` were designed so that adding
market-price data, irrigation scheduling, a crop calendar, or multilingual
labels later requires adding fields/files, not restructuring what already
exists.
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
