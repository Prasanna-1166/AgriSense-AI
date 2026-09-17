# Data Pipeline

## Training-time pipeline (offline, explicit, never run by the web server)

```
ml/train_crop_model.py
  1. ml.preprocessing.load_training_dataframe()
     - Try local cache (data/crop_dataset_cache.csv)
     - Try online source (GitHub-hosted CSV mirror)
     - Fall back to a small bundled offline sample (config/settings.py::FALLBACK_DATASET)
       if both fail — training never hard-crashes for lack of network access
  2. ml.preprocessing.clean_dataset()
     - Drop rows with nulls in critical columns
     - Drop duplicates
     - Drop rows whose label isn't one of the 22 known crops
     - Drop 1st/99th percentile outliers per feature
  3. Train/test split (80/20, stratified by crop, fixed random_seed=42)
  4. Train RandomForestClassifier(n_estimators=200)
  5. Evaluate: accuracy + full classification report
  6. Compute per-crop feature statistics (mean/std/min/max) — used later by
     ml/explainability.py for "why this crop" and by the synthetic yield generator
  7. Save: models/crop_model.joblib, models/crop_stats.json, models/metadata.json

ml/train_yield_model.py
  1. Reuse the cleaned crop dataset + per-crop statistics from step 6 above
  2. ml.preprocessing.build_synthetic_yield_dataset()
     - For each crop, generate 160 synthetic samples around its real
       statistical comfort zone
     - Synthetic yield = reference_avg_yield x suitability_factor x irrigation_adjustment
     - This is the ONLY step that is synthetic - clearly isolated to one
       function, one dataset, one documented purpose
  3. Train RandomForestRegressor(n_estimators=200, max_depth=12)
  4. Evaluate: R-squared, MAE
  5. Save: models/yield_model.joblib, updated models/metadata.json
```

Re-running either script overwrites the previous model artifact - this is
intentional (no dataset versioning system was built for a single, static
public dataset with no update cadence; see Future Work in `limitations.md`
for what a real dataset-versioning system would need once live government
data is integrated).

## Data quality checks actually implemented

`ml/preprocessing.py::clean_dataset()`:
- Missing-value removal (critical columns only)
- Duplicate removal
- Label-validity check (crop must be one of the 22 known classes)
- Outlier trimming (1st/99th percentile per numeric feature)

`utils/validation.py`:
- Range validation on every prediction input (pH 2-12, temperature -10-55C,
  humidity 0-100%, N/P/K 0-300 kg/ha, rainfall 0-6000 mm/year)
- Soil Health Card field validation (`services/soil_service.py::SOIL_HEALTH_CARD_PARAMS`)
  with per-field plausible ranges

## Request-time (runtime) pipeline

```
User input (location + optional overrides)
        |
        v
services/environment_service.py
  - weather_service.fetch_elevation/fetch_climate_averages (Open-Meteo)
  - soil_service.get_soil_profile (SoilGrids + regional fallback)
  - Every value tagged: source, status (retrieved/estimated/fallback/manual), confidence
        |
        v
merge_with_user_overrides()  -- manual/soil-test values always take precedence
        |
        v
utils/validation.DataQualityAssessor -- computes overall data-quality label
        |
        v
ml/predictor.py -- loads cached model singleton, runs inference
        |
        v
services/risk_service.py -- rule-based risk labels from forecast + rainfall
```

## No temporal leakage - by construction, not by validation

Because there is no historical time-series training data in this version
(the crop-recommendation dataset is a static, undated reference set - see
`data-sources.md` section 1), there is no temporal leakage risk to guard
against in the current models. This is noted explicitly rather than
glossed over: **time-aware train/test splitting (Section 27 of the
project brief) applies once real historical multi-year production data
is integrated - it is not yet meaningfully applicable to this version's
dataset.**
