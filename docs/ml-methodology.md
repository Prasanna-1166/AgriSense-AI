# ML Methodology

## Model selection

| Model | Algorithm | Why this one |
|---|---|---|
| Crop recommendation | RandomForestClassifier (scikit-learn) | Handles the mixed-scale numeric features (N/P/K in kg/ha, pH 2-12, rainfall in hundreds of mm) without feature scaling; robust to the dataset's per-crop feature clustering; gives usable `predict_proba` for suitability percentages and native `feature_importances_` for explainability |
| Yield estimation | RandomForestRegressor (scikit-learn) | Same practical benefits; per-tree prediction variance (`estimators_`) is used to produce a defensible yield range rather than a single point estimate presented as exact |

Simpler models (Logistic Regression, single Decision Tree) and heavier
ones (XGBoost/LightGBM) were considered per the project brief's Section
26. A single RandomForest was kept for both models because:
- The dataset is small (under 2,000 rows after cleaning) - ensemble
  boosting libraries offer little practical benefit at this scale and add
  a dependency-installation burden for a "should just work on a student's
  Windows laptop" project (Section 50).
- `feature_importances_` and per-tree variance are used directly by the
  explainability and yield-range features - swapping models would require
  re-deriving those.

## Evaluation

**Crop model** (measured on a held-out 20% stratified test split, `random_seed=42`):
- Accuracy: **99.22%** on 387 held-out rows (from `models/metadata.json`, regenerated each training run)
- This measures how well the model separates the 22 crops **it was trained on**, from their characteristic N/P/K/climate ranges. It is not a claim about real-farm outcome accuracy - see `limitations.md`.

**Yield model**:
- R-squared and MAE are computed against its own synthetic target (see `data-sources.md` section 2) - a high score here confirms the model learned the synthetic function correctly, and explicitly does **not** mean the yield figures match real-world harvests.

## Train/test strategy

A stratified random 80/20 split is used, **not** a time-aware split, because
the underlying dataset (`data-sources.md` section 1) is a static, undated
reference dataset with no temporal dimension to split on. Time-aware
validation (train on older years, test on newer years) is the documented
plan for when real multi-year district production data is integrated (see
`limitations.md` Future Work) - implementing it against a dataset with no
dates would be theater, not rigor.

## Reproducibility

- `RANDOM_SEED = 42` fixed in `config/settings.py`, used for the train/test
  split and both RandomForest estimators
- Every training run regenerates `models/metadata.json` with: dataset
  size, dataset source (`online`/`cache`/`fallback`), accuracy/R2/MAE,
  training timestamp, and the exact feature list used
- Training and inference are fully separated (`ml/train_*.py` vs
  `ml/predictor.py`) so the running app's behavior is deterministic
  between training runs

## Explainability

`ml/explainability.py` implements two mechanisms, both derived directly
from the trained model/data - never templated or invented text:

1. **Feature importance** - read directly from `model.feature_importances_`,
   normalized to percentages.
2. **"Why this crop?" checklist** - for each of the 7 features, compares
   the farmer's input value to that crop's real mean/std (from the actual
   training data, computed once at training time and cached in
   `models/crop_stats.json`), producing a z-score. `|z| <= 1` -> suitable,
   `1 < |z| <= 2` -> borderline, `|z| > 2` -> outside typical range. The
   single worst-scoring feature above `|z| > 1` becomes the "limiting
   factor" callout.

## Unsupported-crop handling

`ml/predictor.py::predict_for_specific_crop()` checks the crop against the
model's actual trained `classes_` list before running any inference. If
the crop isn't one the model was trained on, the function returns `None`
and the calling route (`routes/current_farm.py`) returns an explicit
"no validated data" message rather than ever calling `.predict()` on an
unknown class or silently mapping it to a similar one.
