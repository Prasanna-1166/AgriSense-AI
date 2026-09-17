# API Reference

All responses are JSON. Error responses follow:
```json
{"success": false, "error": {"code": "INSUFFICIENT_DATA", "message": "..."}}
```
(Some legacy endpoints inherited from the earlier CropWise version return
a flatter `{"error": "..."}` shape - both are documented below per
endpoint. Stack traces are never returned to the client; see `app.py`
error handlers.)

## Health

**GET `/api/health`**
Returns model load status, dataset/accuracy metadata, and Crop Master summary.

## Location

**GET `/api/location/search?q=<text>`** — Nominatim place search
**GET `/api/location/reverse?lat=&lon=`** — Reverse geocode to a place name
**GET `/api/location/states`** — List Indian states
**GET `/api/location/districts?state=<name>`** — List districts (full lists for AP/Telangana)
**GET `/api/location/resolve?lat=&lon=`** — Resolve GPS to state/district + confirmation prompt text

## Environment / Weather / Soil

**POST `/api/environment`** `{lat, lon}` — Full climate+soil profile with source/status/confidence per value
**GET `/api/weather?lat=&lon=`** — Current conditions + 7-day forecast (Open-Meteo)
**POST `/api/soil`** `{lat, lon}` — Soil profile only
**POST `/api/soil/validate`** `{ph?, ec?, organic_carbon?, N?, P?, K?, sulphur?, zinc?, iron?, manganese?, copper?, boron?}` — Validates Soil Health Card values you supply; empty body returns an explicit "no soil test available" response
**POST `/api/soil/extract`** multipart file upload (`file` field, PDF/PNG/JPG, max 8MB) — Attempts extraction; response always requires frontend confirmation before use

## Prediction — Planning Mode

**POST `/api/predict/quick`** `{lat, lon, area_ha?, irrigation?}` — Location only
**POST `/api/predict/assisted`** (default) `{lat, lon, area_ha?, irrigation?, N?, P?, K?, temperature?, humidity?, ph?, rainfall?}` — Auto-fill + optional overrides
**POST `/api/predict/expert`** `{N, P, K, temperature, humidity, ph, rainfall, area_ha?, irrigation?, lat?, lon?}` — All 7 fields required
**POST `/api/predict`** — Generic, routes by `"mode"` field

All three return: `ranked_crops[]`, `top_crop`, `feature_importance[]`,
`data_quality`, `water_requirement`, `insights[]`, `risks[]`. `ranked_crops`
only ever contains the 22 model-supported crops - never an unsupported one.

## Current Farm Mode

**POST `/api/farm/analyze-current`**
```json
{
  "lat": 16.5, "lon": 80.6,
  "current_crop": "rice", "crop_stage": "flowering (optional)",
  "area_ha": 2, "irrigation": "partial",
  "N": 80 
}
```
If `current_crop` has no validated model coverage (e.g. `chilli`,
`tobacco`, `wheat`, `sugarcane`, `turmeric`, `groundnut`), the response has
`"suitability_available": false`, `"yield_available": false`, and a plain-
language `"message"` explaining why - weather/soil context is still
returned. If supported, `"crop_analysis"` contains suitability/yield/
explanation for that specific crop.

## Crops

**GET `/api/crops[?category=]`** — Full Crop Master registry (supported + unsupported)
**GET `/api/crops/<crop_id>`** — Single crop's registry entry
**POST `/api/crops/compare`** `{N, P, K, temperature, humidity, ph, rainfall, area_ha?, irrigation?, crops: [ids]}` — Compare specific crops; requesting an unsupported crop returns its reason instead of a fabricated comparison row

## Farm Profile (optional, local, no auth)

**GET `/api/farm/profile`** / **POST `/api/farm/profile`** / **DELETE `/api/farm/profile`**

## History

**GET `/api/history?limit=`** / **POST `/api/history`** / **DELETE `/api/history/<id>`** / **DELETE `/api/history`**
