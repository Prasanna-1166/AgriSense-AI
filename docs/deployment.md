# Deployment

## Local (recommended for evaluation / demos)

See the root `README.md` — Python 3.12 venv, `pip install -r requirements.txt`,
`python app.py`. Models are pre-trained and bundled, so this works
immediately offline (Expert mode and Current Farm Mode for a supported
crop with manual values need no network at all; Quick/Assisted mode and
live weather need outbound internet to Nominatim/Open-Meteo/SoilGrids).

## Production-style deployment (single Python host)

AgriSense AI is a stateless-per-request Flask app (the only local state is
`data/prediction_history.json` and `data/farm_profile.json`, both plain
JSON files) so it deploys straightforwardly to any platform that runs a
long-lived Python process:

1. Set environment variables (see `.env.example`): `AGRISENSE_HOST=0.0.0.0`,
   `AGRISENSE_PORT` (per platform convention), leave `AGRISENSE_DEBUG=0`.
2. Run model training once during the build step (`python -m ml.train_crop_model
   && python -m ml.train_yield_model`) or commit the pre-trained `models/*.joblib`
   files (already small: ~1-2 MB total).
3. Run behind a production WSGI server rather than Flask's dev server, e.g.:
   ```
   pip install gunicorn
   gunicorn -w 2 -b 0.0.0.0:$PORT app:app
   ```
   (`gunicorn` is not in `requirements.txt` by default since it's Linux-only
   and the base requirement is "runs on a student's Windows laptop" -
   add it only for your actual deployment target.)
4. Ensure outbound HTTPS access to `nominatim.openstreetmap.org`,
   `api.open-meteo.com`, `archive-api.open-meteo.com`, and
   `rest.isric.org` is allowed by your platform's network policy - if
   blocked, the app still runs, but Quick/Assisted modes will show
   `fallback` status instead of `retrieved`/`estimated`.
5. `data/uploads/soil_reports/` is used only transiently during
   `/api/soil/extract` (files are deleted immediately after the extraction
   attempt) - no persistent file storage is required for that feature.

## What this project deliberately does NOT include

Per the project brief's own anti-overengineering constraints: no
Kubernetes, no message queue, no separate frontend build step (the
frontend is server-rendered Jinja2 + vanilla JS, so "deploy the backend"
is "deploy the whole app"), no authentication system (the only
"personalization" is a single local farm profile file, not multi-user
accounts).

## Choosing a host

The brief intentionally leaves the hosting provider unspecified pending
evaluation of the actual stack - this is a standard Flask + scikit-learn
app with no GPU requirement and small model artifacts, so it fits
comfortably on any conventional Python-application hosting platform.
Evaluate based on your own cost/familiarity constraints rather than a
recommendation baked into this document.
