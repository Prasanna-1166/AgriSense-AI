# Data Sources

This document exists so an evaluator, farmer, or future contributor can
verify exactly what data this system actually uses — and, just as
importantly, what it does **not** have and does not pretend to have.

## 1. Crop recommendation training data

| Field | Value |
|---|---|
| Dataset | Crop Recommendation Dataset |
| Source URL used by this project | `https://raw.githubusercontent.com/Gladiator07/Harvestify/master/Data-processed/crop_recommendation.csv` |
| Publisher | Public/community-maintained mirror (originally derived from an Indian agricultural/ML competition dataset widely used in academic crop-recommendation research) |
| Access date | Downloaded fresh at training time by `ml/train_crop_model.py`; cached to `data/crop_dataset_cache.csv` |
| Coverage | 2,200 rows before cleaning, 1,935 after removing duplicates/outliers |
| Crops | 22: apple, banana, blackgram, chickpea, coconut, coffee, cotton, grapes, jute, kidneybeans, lentil, maize, mango, mothbeans, mungbean, muskmelon, orange, papaya, pigeonpeas, pomegranate, rice, watermelon |
| Geographic scope | Not geo-tagged per row — the dataset provides agronomic feature ranges (N/P/K/temperature/humidity/pH/rainfall) per crop, not district-level Indian observations |
| Temporal scope | Not dated — static reference dataset |
| Variables | N, P, K (soil nutrients, kg/ha), temperature (°C), humidity (%), pH, rainfall (mm), crop label |
| License/usage | Publicly redistributed for ML education; no explicit restrictive license found |
| **Limitation** | **Does not include Chilli, Tobacco, Wheat, Sugarcane, Turmeric, or Groundnut** — six of this project's nine mandatory priority crops. See `config/crop_master.py` for how this gap is surfaced rather than hidden. |

## 2. Yield estimation training data

**There is no real yield dataset.** The yield model (`ml/train_yield_model.py`)
is trained on a **documented synthetic target**:

1. Take each crop's reference average yield (a single static figure per crop, `config/settings.py::BASE_YIELD_TONNES_PER_HA` — these are commonly cited approximate national/regional averages, not measured observations tied to any specific farm or year).
2. Generate synthetic feature samples around each crop's real statistical comfort zone (computed from item 1's real training data).
3. Scale the reference yield by how closely the synthetic sample matches that comfort zone, plus an irrigation adjustment.
4. Train a RandomForestRegressor on this synthetic target.

This is disclosed in the UI (Yield Prediction page), the API (`top_crop`/`crop_analysis` responses are never called "measured"), and `models/metadata.json`. **No claim of field-validated real-world yield accuracy is made anywhere in this system.**

## 3. Weather & climate

| Field | Value |
|---|---|
| Provider | [Open-Meteo](https://open-meteo.com) |
| Endpoints used | `/v1/forecast` (current + 7-day forecast), `/v1/elevation`, `archive-api.open-meteo.com/v1/archive` (90-day historical archive used as a climate-average proxy) |
| Access | Free, keyless, no registration required |
| Variables | temperature, relative humidity, precipitation, wind speed, weather code, daily max/min temperature, daily precipitation sum, FAO evapotranspiration |
| Limitation | "Climate average" is a 90-day recent archive, not a multi-year climatological normal — a genuine limitation stated plainly rather than implying a longer baseline |

## 4. Soil data

| Field | Value |
|---|---|
| Provider | [SoilGrids / ISRIC](https://www.isric.org/explore/soilgrids) |
| Endpoint used | `rest.isric.org/soilgrids/v2.0/properties/query` |
| Variables used | `phh2o` (pH, 0–5cm depth), `nitrogen` (total N indicator, 0–5cm depth) |
| Access | Free, keyless |
| **Critical limitation** | SoilGrids provides **modeled, global-resolution** soil property predictions — not laboratory measurements. It also does not provide plant-available P or K at all. This project therefore treats SoilGrids output as one input to a **regional estimate**, never as a substitute for a real soil test. |

### Soil Health Card (manual entry)

Farmers can enter real values from an actual Government of India Soil
Health Card (pH, EC, organic carbon, N, P, K, S, Zn, Fe, Mn, Cu, B) via
`/api/soil/validate`. These are tagged `USER_ENTERED` and are the highest-
confidence soil input the system accepts. AgriSense AI does not host or
scrape the Soil Health Card database itself — the farmer supplies their
own card's values.

### Soil report upload

`/api/soil/extract` attempts best-effort text extraction from an uploaded
PDF/image soil report using regex pattern matching over the document's
extracted text. Every extracted value is tagged `DOCUMENT_EXTRACTED` and
the frontend requires explicit user confirmation before any extracted
value is used — extraction is never auto-trusted (see `services/soil_extraction_service.py`).

## 5. Location & administrative geography

| Field | Value |
|---|---|
| Search / reverse geocoding | OpenStreetMap Nominatim, free/keyless, self-rate-limited to ~1 req/sec per Nominatim's usage policy |
| State/district reference lists | Static administrative reference data maintained in `config/geography.py`, current as of Andhra Pradesh's 2022 district reorganization (26 districts) and Telangana's 33 districts. This is boundary/name reference data, not agricultural observation data. |

## 6. Real Indian government agricultural data — researched but NOT integrated in this version

The project brief calls for Directorate of Economics & Statistics /
data.gov.in / ICAR-sourced district-level crop production statistics for
Andhra Pradesh and Telangana. These were researched during development:

| Source | What it has | Why it isn't wired into this version |
|---|---|---|
| **data.gov.in** — district-wise crop production statistics | Real area/production/yield by district, season, crop, year | Distributed via an interactive government portal rather than a stable bulk-download API from this deployment environment |
| **Dataful.in** (repackages Ministry of Agriculture / Directorate of Economics & Statistics data) | AP/Telangana district-season-crop area-production-yield | Structured but not scriptable from this project's build environment without a manual export step |
| **ICRISAT District Level Data** (`data.icrisat.org`) | District-level crops, irrigation, soil type, rainfall, 1958–present | Confirmed real and well documented, but delivered through a JS filter-and-export tool rather than a direct file URL |

**This version does not fabricate a regional-evidence layer to compensate
for this gap.** Regional crop-production evidence is listed under
`limitations.md` and `Future Work` rather than approximated. If real
exported CSVs from these sources are supplied (e.g. by a user with portal
access), `ml/preprocessing.py` and `config/crop_master.py` are structured
so that a genuine Phase 2/3 data-harmonization pass could integrate them
without an architecture rewrite.

## 7. What this system never does with data

- Never invents a crop-specific number (yield, production, price) that
  isn't derived from one of the above sources.
- Never remaps an unavailable crop (Chilli, Tobacco, Wheat, Sugarcane,
  Turmeric, Groundnut) onto a similar crop's prediction.
- Never reports a soil N/P/K/pH value as "measured" when it is a regional
  or SoilGrids-modeled estimate.
- Never reports weather as available when the external API call failed —
  fallback status is always shown.
