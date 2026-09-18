# AgriSense AI

**An honest, real-data agricultural decision-support platform for Andhra Pradesh & Telangana.**

AgriSense AI combines a validated crop-suitability ML model, live weather,
location-based soil intelligence, and optional real soil-test data to help
answer: *"Given my farm location, season, soil, irrigation, and current
weather, what crop is most suitable, what yield can I reasonably expect,
and why?"* — and, just as importantly, **what this system honestly does
not know yet.**

> **Read `docs/limitations.md` before demoing this.** Six economically
> important crops for this region — Chilli, Tobacco, Wheat, Sugarcane,
> Turmeric, Groundnut — have **no validated model** in this version. The
> app says so explicitly everywhere they'd appear, rather than guessing.

---

## 1. Project Overview

This is a from-scratch rebuild of an earlier single-file "Smart Crop"
demo (~2,200-row dataset, 22 crops) into a modular, two-mode agricultural
platform:

- **Planning Mode** — "What crop should I plant?" (Quick / Smart Assisted / Expert input tiers)
- **Current Farm Mode** — "I have a crop already — help me understand my situation"

with a Crop Master registry that treats data availability as a first-class
concept, a rule-based risk layer, Soil Health Card-style soil intelligence
with document upload, an optional local farm profile, and full data-source
transparency throughout.

## 2. Features

- **Location-first**: map click, search, GPS (with a confirm-your-district step), or manual State→District (full lists for AP & Telangana)
- **Three Planning input tiers** + **Current Farm situational analysis**
- **Crop Master registry**: 22 crops with real validated data, 6 explicitly marked "data unavailable" — see `/api/crops` and the Crop Directory page
- **Soil intelligence**: manual Soil Health Card entry (pH, EC, OC, N/P/K, S/Zn/Fe/Mn/Cu/B), PDF/image report upload with mandatory confirm-before-use, SoilGrids/ISRIC-based pH estimate, transparent fallback chain
- **Explainable recommendations**: feature importance + "why this crop" checklist derived directly from real training-data statistics
- **Yield estimation with range**, always labeled as a documented synthetic/estimated model
- **Rule-based risk assessment** (rainfall/temperature/irrigation/data-availability), each with its exact triggering rule shown
- **Crop comparison, weather & 7-day forecast, prediction history, optional local farm profile**
- **Crop Plan & Economics**: seed/planting-material requirement, crop duration, fertilizer
  recommendation, and plant-protection guidance for the recommended crop, scaled to your farm
  area, each field tagged verified-source/derived-estimate/honestly-unavailable — see
  `/api/crop-plan/<crop_id>` and `docs/data-sources.md` §7. For rice, maize and cotton, a real
  published cost-of-cultivation survey total (₹/ha, with region/year/source) is also shown; other
  crops show sourced input quantities with cost left unavailable rather than guessed.
- **Never fabricates**: unsupported crops get an honest message, not a guess; every environmental value carries a source/status/confidence tag

## 3. Architecture

See `docs/architecture.md` for the full breakdown. Short version: modular
Flask blueprints (`routes/`), isolated external-service wrappers
(`services/`), training/inference split (`ml/`), a Crop Master + geography
reference registry (`config/`), and a vanilla-JS multi-section dashboard
frontend (`templates/`, `static/`).

## 4. Technology Stack

- **Backend**: Flask 3, Python 3.12
- **ML**: scikit-learn (RandomForestClassifier + RandomForestRegressor), pandas, NumPy, joblib
- **Frontend**: Server-rendered Jinja2 + vanilla JS + Leaflet (map) + Chart.js (charts) — no build step required
- **Soil report extraction**: pypdf (PDF text) + optional pytesseract/Pillow (image OCR)
- **Storage**: plain JSON files for local prediction history / farm profile (no database — see `docs/architecture.md` for why)

## 5. Datasets

See `docs/data-sources.md` for the complete, honest breakdown, including
what real Andhra Pradesh/Telangana government sources were researched but
**not yet integrated**, and exactly why.

## 6. Data Sources (summary)

| Purpose | Source | Real / Synthetic |
|---|---|---|
| Crop recommendation training | Public Crop Recommendation Dataset (22 crops) | Real |
| Yield estimation training | Reference average yields, scaled by real per-crop statistics | **Synthetic** — always labeled as such |
| Weather / forecast / elevation | Open-Meteo | Real, live |
| Soil pH estimate | SoilGrids / ISRIC | Real, modeled (not lab-measured) |
| Soil N/P/K (automatic) | Regional/climatic-zone estimate | Estimate, not measured |
| Soil N/P/K/pH (manual) | Your Soil Health Card / lab test | Real, if you enter it |
| Location search/reverse | OpenStreetMap Nominatim | Real |
| State/district names | Static administrative reference | Real |

## 7. ML Methodology

See `docs/ml-methodology.md`. Crop model: RandomForestClassifier,
99.22% test accuracy on the crops it was trained on. Yield model:
RandomForestRegressor on a documented synthetic target — see
`docs/data-sources.md` §2 before quoting this number anywhere.

## 8. Model Evaluation

Regenerated on every training run into `models/metadata.json`:
- Crop model: accuracy, dataset size/source, training timestamp
- Yield model: R², MAE, explicit "synthetic/estimated" note

## 9. Installation (Windows PowerShell)

Requires **Python 3.12**.

```powershell
cd AgriSense-AI
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

If PowerShell blocks script execution, run once as Administrator:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

## 10. Environment Variables

See `.env.example`. All optional — no API keys required anywhere in this
project.

```powershell
$env:AGRISENSE_PORT = "8080"
$env:AGRISENSE_DEBUG = "1"
```

## 11. Development — Running the App

Models are pre-trained and bundled in `models/`, so this works immediately:

```powershell
python app.py
```
Open **http://127.0.0.1:5000**.

## 12. Training / Retraining Models

Never run automatically by the web app — always an explicit step:

```powershell
python -m ml.train_crop_model
python -m ml.train_yield_model
```

## 13. Refreshing Data

The crop dataset is re-downloaded automatically the next time you run
`train_crop_model` with an empty/deleted `data/crop_dataset_cache.csv`.
There is no live-updating agricultural dataset in this version — see
`docs/limitations.md`.

## 14. Testing

```powershell
python -m pytest tests/ -v
```
**95 tests**, including dedicated anti-fabrication checks (e.g.
`test_supported_crops_match_trained_model_classes` fails loudly if the
Crop Master registry and the actual trained model ever disagree about
which crops are supported, and `test_no_crop_has_a_fabricated_cost_total`
for the Crop Plan & Economics layer).

## 15. API Reference

See `docs/api.md` for every endpoint.

## 16. Project Structure

See `docs/architecture.md`.

## 17. Deployment

See `docs/deployment.md`.

## 18. Troubleshooting

- **"Models not yet trained" / 503 on predict endpoints** → run the training commands in §12.
- **A crop shows "data unavailable"** → this is intentional, not a bug — see `docs/limitations.md`. Chilli, Tobacco, Wheat, Sugarcane, Turmeric, and Groundnut have no validated model in this version.
- **Weather/soil/location shows `fallback` status** → your network can't reach `nominatim.openstreetmap.org` / `api.open-meteo.com` / `rest.isric.org`. The app still works; those values just won't be `retrieved`/`estimated`.
- **Soil report upload says extraction failed** → this is expected for unusual formats or if `pypdf`/`pytesseract` aren't installed; use manual entry instead.
- **`pip install` fails** → confirm Python 3.12, and that the venv is activated.

## 19. Limitations

**Read `docs/limitations.md` in full before evaluating or demoing this
project.** The short version: 6 of 9 mandatory crops are explicitly
unsupported due to a real training-data gap, yield figures are a
documented synthetic estimate, and real Andhra Pradesh/Telangana
government production data was researched but not yet integrated.

## 20. Future Work

See `docs/limitations.md` §Future Work — headlined by integrating real
district-level government production data, which is the single highest-
value next step for this project.

---

*This README was written to be read alongside `docs/limitations.md` —
together they are the actual, current state of the project, not an
aspirational description of it.*
