# Limitations

This document is the single most important one in this repository. Read
it before demoing or evaluating the project.

## Crop coverage gap (the biggest one)

Six of the project's nine mandatory priority crops - **Chilli, Tobacco,
Wheat, Sugarcane, Turmeric, Groundnut** - have **no validated
recommendation or yield model** in this version, because the only crop
dataset available to this project (see `data-sources.md`) does not
include them. AgriSense AI marks these explicitly as `UNSUPPORTED` /
"data unavailable" everywhere they appear (Crop Directory, Current Farm
Mode, comparison) rather than approximating them with a similar crop or
fabricating numbers. This is a real, current gap - not a hidden one.

## No real Indian government production/yield data is integrated

`data-sources.md` §6 documents three real, legitimate sources
(data.gov.in, Dataful.in/Directorate of Economics & Statistics, ICRISAT
District Level Data) that were researched during development. None of
them were integrated into a working, harmonized pipeline in this version
because they are distributed through interactive portals rather than a
scriptable bulk-download path available to this project's build process.
Regional evidence, district-specific suitability, and state/national
production statistics are therefore **not** part of any recommendation
in this version.

## Yield figures are a documented synthetic estimate

Not field-validated. Not tied to any specific district, year, or real
harvest record. See `data-sources.md` §2 and `ml-methodology.md` for
exactly how the synthetic target is constructed. Treat all yield/
production numbers as rough general guidance only.

## Risk assessment is rule-based, not a calibrated model

`services/risk_service.py` uses fixed, documented thresholds (e.g. 50mm/day
= "High" rainfall risk) rather than a statistically calibrated
probability-of-failure model, because no validated failure-probability
dataset exists for this project. Every risk item states its exact rule.

## Soil N/P/K are never true measurements unless you provide them

GPS location cannot measure soil chemistry. Automatic soil values (Quick/
Assisted modes) are always `estimated` or `fallback` status. Only
`USER_ENTERED` (manual Soil Health Card entry) or a confirmed
`DOCUMENT_EXTRACTED` value should be trusted as close to a real
measurement.

## No time-aware validation

Because the training dataset has no temporal dimension (it's a static
reference set, not a multi-year historical series), there is no
train/test split by year, and therefore no meaningful check for temporal
leakage in the current models. This becomes necessary and implementable
only once real historical multi-year district production data (per
`data-sources.md` §6) is integrated.

## Soil report extraction is best-effort regex matching

`services/soil_extraction_service.py` uses regex pattern matching over
extracted PDF/image text, not a trained document-understanding model. It
will miss unusually formatted reports, and image OCR requires optional
dependencies (`pytesseract`+`Pillow`) that may not be installed. Failure
always falls back to a clear "please enter manually" message rather than
guessing.

## Single-user, local-only persistence

Prediction history and the farm profile are local JSON files with no
authentication and no multi-user isolation. This is intentional (see the
brief's anti-overengineering guidance) but means this version is not
suitable for a shared multi-farmer deployment without adding real user
accounts and a proper database.

## Disease detection, multilingual support, market prices, fertilizer
## recommendation, irrigation scheduling, satellite imagery

None of these are implemented. They are explicitly V3 scope per the
project brief and are not exposed anywhere in the UI as if they were
available (no placeholder buttons, no fake results).

## Sandbox development constraint (transparency about this build)

This version was built in a sandboxed environment without outbound
network access to Indian government data portals, Open-Meteo, Nominatim,
or SoilGrids. All service-layer fallback paths (weather-unavailable,
soil-fallback, geocoding-unavailable) were verified to degrade gracefully
under exactly these conditions. The crop-recommendation training dataset
was reachable (via GitHub) and was downloaded fresh and used for real
training - it is the one real dataset genuinely exercised end-to-end
during this build. Live weather/soil/geocoding retrieval should be
re-verified on a network with access to those services.

## Future Work

- Integrate real district-level government production data (Phase 2-4 of
  the original brief) once a scriptable data-access path is confirmed -
  this is the single highest-value next step, since it unlocks regional
  evidence, time-aware validation, and coverage for the six missing
  mandatory crops if per-crop training data can be assembled.
- Multilingual UI (English/Telugu/Hindi)
- Fertilizer recommendation and irrigation scheduling modules
- Disease detection (image-based) as a genuinely separate, honestly-scoped
  future module
- SQLite-backed multi-farmer profiles with real authentication, if/when
  shared deployment is needed
- Calibrated (not rule-based) risk modeling, once a real crop-loss/weather
  outcomes dataset is available
