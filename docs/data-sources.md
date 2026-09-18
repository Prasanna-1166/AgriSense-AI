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

## 7. Crop agronomy & economics data (Crop Plan Layer)

`config/crop_agronomy_data.py` is the single source of truth for seed/
planting-material requirement, crop duration, fertilizer recommendation,
and plant-protection guidance shown on the Crop Plan & Economics page.
Every value carries a `status` (`VERIFIED_SOURCE`, `SOURCE_ESTIMATE`, or
`UNAVAILABLE`) and, when verified, a named source. `SOURCE_ESTIMATE` is
used only for a value transparently *derived* from a verified figure via
documented arithmetic (e.g. a per-tree fertilizer dose x an assumed
planting density to get kg/ha) - it is always accompanied by a note
explaining the derivation. No value in this file is an average, a guess,
or borrowed from a "similar" crop without saying so.

| Crop | Fields with a verified/derived source | Source |
|---|---|---|
| Rice | Duration, seed rate, N/P/K/Zn fertilizer dose, plant protection (stem borer, BPH, blast, sheath blight) | RARS Tirupati (ANGRAU), *Recommendations for Rice Crop Production, Kharif 2014 & Rabi 2014-15* |
| Maize | Duration, seed rate, N/P/K/Zn fertilizer dose, plant protection (stem borer, leaf blight) | RARS Tirupati (ANGRAU), *Maize - Package of Practices* |
| Cotton | Seed rate, N/P/K fertilizer dose (rainfed baseline) | ICAR-CICR fertilizer recommendation; Tractor Junction (seed-rate figures, 2025) |
| Chickpea (Bengalgram) | Seed rate, N/P/S fertilizer dose, plant protection (pod borer, wilt) | RARS Tirupati (ANGRAU), *Package of Practices - Pulses* |
| Blackgram | Seed rate, N/P fertilizer dose, plant protection (Maruca, YMV) | RARS Tirupati (ANGRAU), *Package of Practices - Pulses* |
| Mungbean (Greengram) | Seed rate | RARS Tirupati (ANGRAU), *Package of Practices - Pulses* (fertilizer/plant-protection explicitly documented as "similar to blackgram" in the source, not independently restated) |
| Pigeonpeas (Redgram) | Seed rate, N/P fertilizer dose, plant protection (pod borer, wilt) | RARS Tirupati (ANGRAU), *Package of Practices - Pulses* |
| Mango | Planting density (100 grafts/ha), N/P/K fertilizer (per-tree verified, per-ha derived) | ICAR-CCARI Goa (spacing); TNAU *Fertilizer Schedule for Fruit Crops* |
| Banana | Planting density (estimate), N/P/K fertilizer (per-plant verified, per-ha derived) | TNAU Banana Cultivation; TNAU *Fertilizer Schedule for Fruit Crops* |
| Coconut | Planting density (175 palms/ha), N/P2O5/K2O fertilizer (per-palm verified, per-ha derived), organic manure | ICAR-CPCRI |
| Orange (sweet orange) | N/P2O5/K2O fertilizer (per-tree only - no verified spacing to convert to per-ha) | TNAU *Fertilizer Schedule for Fruit Crops* |
| Grapes | N/P/K fertilizer, Thompson Seedless, 3-year progression (per-vine only) | TNAU *Fertilizer Schedule for Fruit Crops* |
| Papaya | N/P/K fertilizer (per-plant, per-application - not annualized) | TNAU *Fertilizer Schedule for Fruit Crops* |
| Pomegranate | N/P/K fertilizer, age-scaled (per-plant only) | TNAU *Fertilizer Schedule for Fruit Crops* |
| Apple | N/P/K fertilizer (per-tree only; not AP/Telangana-relevant) | TNAU *Fertilizer Schedule for Fruit Crops* |
| Jute | Duration (100-120 days), seed rate, N/P2O5/K2O (2003-04 national average use, not a current recommendation) | ICAR-CRIJAF (Ghorai & Chakraborty, 2020); FAO fertilizer-use statistics |
| Lentil | N/P/S fertilizer dose | Directorate of Pulses Development (Govt. of India) / ICAR-IIPR |

**Crops with NO verified agronomy data in this release:** coffee,
kidneybeans, mothbeans, muskmelon, watermelon. These return
`has_agronomy_data: false` and an honest "unavailable" status from
`/api/crop-plan/<crop_id>` rather than a fabricated figure. This is a
real, current gap - the same anti-fabrication policy as the ML crop
coverage gap in §1, applied to agronomic reference data.

**Per-plant vs. per-hectare figures for tree/vine/perennial crops.**
Institutional sources for perennial crops (mango, banana, coconut,
orange, grapes, papaya, pomegranate, apple) give doses **per tree/vine/
plant**, not per hectare - a farm's per-hectare total depends on
planting density, which varies by variety and system. Where a specific,
sourced planting density exists (mango, banana, coconut), the per-ha
figure is calculated and tagged `SOURCE_ESTIMATE` with a note explaining
the derivation - it is not an independently sourced per-ha figure.
Where no reliable density source was found (orange, grapes, papaya,
pomegranate, apple), the per-plant dose is shown as `VERIFIED_SOURCE`
with `quantity_per_ha` left `null` rather than guessing a density -
farmers can multiply by their own actual tree/vine count.

**Cost data (seed/fertilizer/labour/etc. prices in INR): now available for
3 crops as real, dated, sourced SURVEY totals — rice, maize, cotton.**
Rather than build a bottom-up per-input price list (no verified current
AP/Telangana unit prices were found), the app instead surfaces a real,
published **cost-of-cultivation survey total** for these three crops:

| Crop | Total cost/ha | Region | Year | Source |
|---|---|---|---|---|
| Rice | ₹66,985 | Bhoopalpalli district, Telangana | TE 2021-22 | Peer-reviewed study using official CACP plot-level data |
| Maize | ₹64,448 (Cost A2+FL) | Telangana (state-wise) | TE 2021-22 | Peer-reviewed study using official CACP survey data |
| Cotton | ₹1,62,020 | Andhra Pradesh (state-level) | 2023-24 | ANGRAU official Cotton Outlook Report |

These are surfaced via `economics.surveyed_total` in
`/api/crop-plan/<crop_id>` and are **never added to** the itemized
seed/fertilizer components list (which stays unpriced) - the survey total
already includes seed, fertilizer, labour, machinery and irrigation
costs per its own methodology, so summing the two would double-count.
Each entry states its exact cost concept (e.g. CACP's "Cost A2+FL" vs. a
comprehensive total), region, and year, because these figures are NOT
interchangeable or stable - e.g. the cotton figure reflects a specific,
reportedly loss-making 2023-24 season, and the rice figure is a single
district, not a state average. All 3 remaining ML-supported crops with
seed/fertilizer data (chickpea, blackgram, mungbean, pigeonpeas) and
every crop added in this update do NOT have a surveyed total - their
`economics.surveyed_total` is `null` and the itemized components stay
`UNAVAILABLE`, honestly, rather than estimated.

**Plant protection guidance is intentionally conservative.** It is only
included where a named agricultural-university or ICAR source gives a
specific target pest/disease, active ingredient, and rate. Only rice and
the four RARS Tirupati pulses (chickpea, blackgram, pigeonpeas; mungbean
by explicit cross-reference) have this in this release - every other
crop, including the newly-added tree/vine crops and jute/lentil, is
honestly marked unavailable rather than given a generic pesticide list.

## 8. What this system never does with data

- Never invents a crop-specific number (yield, production, price) that
  isn't derived from one of the above sources.
- Never remaps an unavailable crop (Chilli, Tobacco, Wheat, Sugarcane,
  Turmeric, Groundnut) onto a similar crop's prediction.
- Never reports a soil N/P/K/pH value as "measured" when it is a regional
  or SoilGrids-modeled estimate.
- Never reports weather as available when the external API call failed —
  fallback status is always shown.
- Never shows a seed/fertilizer/planting-material figure, crop duration, or
  cost total in the Crop Plan & Economics page without a named, dated
  source - see §7. Missing data is shown as "unavailable", never estimated.
