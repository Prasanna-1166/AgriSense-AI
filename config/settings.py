"""
AgriSense AI Configuration Settings
"""
import os
from datetime import datetime, timezone

# Flask Configuration
FLASK_HOST = os.getenv("AGRISENSE_HOST", "127.0.0.1")
FLASK_PORT = int(os.getenv("AGRISENSE_PORT", "5000"))
FLASK_DEBUG = os.getenv("AGRISENSE_DEBUG", "0") == "1"

# Project Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_DIR = os.path.join(BASE_DIR, "models")
DATA_DIR = os.path.join(BASE_DIR, "data")
CACHE_DIR = os.path.join(DATA_DIR, "cache")

# Ensure directories exist
os.makedirs(MODEL_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)

# Model Files
CROP_MODEL_PATH = os.path.join(MODEL_DIR, "crop_model.joblib")
YIELD_MODEL_PATH = os.path.join(MODEL_DIR, "yield_model.joblib")
METADATA_PATH = os.path.join(MODEL_DIR, "metadata.json")
DATASET_CACHE_PATH = os.path.join(DATA_DIR, "crop_dataset_cache.csv")

# ML Configuration
RANDOM_SEED = 42
FORCE_RETRAIN = os.getenv("AGRISENSE_FORCE_RETRAIN", "0") == "1"

# Feature Configuration
CROP_FEATURES = ["N", "P", "K", "temperature", "humidity", "ph", "rainfall"]
YIELD_FEATURES = CROP_FEATURES + ["crop_index", "irrigation"]

# Crop List (alphabetically sorted, matching RandomForestClassifier order)
CROPS = [
    "apple", "banana", "blackgram", "chickpea", "coconut", "coffee", "cotton",
    "grapes", "jute", "kidneybeans", "lentil", "maize", "mango", "mothbeans",
    "mungbean", "muskmelon", "orange", "papaya", "pigeonpeas", "pomegranate",
    "rice", "watermelon",
]

# Crop Emojis
CROP_EMOJIS = {
    "apple": "🍎", "banana": "🍌", "blackgram": "🫘",
    "chickpea": "🌰", "coconut": "🥥", "coffee": "☕",
    "cotton": "🌱", "grapes": "🍇", "jute": "🌿",
    "kidneybeans": "🫘", "lentil": "🟡", "maize": "🌽",
    "mango": "🥭", "mothbeans": "🌱", "mungbean": "🌱",
    "muskmelon": "🍈", "orange": "🍊", "papaya": "🧉",
    "pigeonpeas": "🌱", "pomegranate": "🔴", "rice": "🌾",
    "watermelon": "🍉",
}

# Base Yield References (tonnes/hectare)
BASE_YIELD_TONNES_PER_HA = {
    "apple": 14.0, "banana": 32.0, "blackgram": 0.7, "chickpea": 1.0,
    "coconut": 7.5, "coffee": 0.8, "cotton": 0.45, "grapes": 18.0,
    "jute": 2.0, "kidneybeans": 1.4, "lentil": 0.9, "maize": 3.2,
    "mango": 8.5, "mothbeans": 0.5, "mungbean": 0.6, "muskmelon": 16.0,
    "orange": 11.0, "papaya": 28.0, "pigeonpeas": 0.9, "pomegranate": 9.0,
    "rice": 3.5, "watermelon": 22.0,
}

# Feature Display Labels
FEATURE_LABELS = {
    "N": "Nitrogen (N)", "P": "Phosphorus (P)", "K": "Potassium (K)",
    "temperature": "Temperature", "humidity": "Humidity", "ph": "Soil pH",
    "rainfall": "Rainfall",
}

# API Configuration
NOMINATIM_BASE_URL = "https://nominatim.openstreetmap.org"
OPENMETEO_BASE_URL = "https://api.open-meteo.com/v1"
SOILGRIDS_BASE_URL = "https://rest.isric.org/soilgrids/v2.0"

# Timeouts (seconds)
API_TIMEOUT = 10
GEOCODE_TIMEOUT = 8
WEATHER_TIMEOUT = 8

# Rate Limiting
NOMINATIM_RATE_LIMIT = 1.0  # seconds between requests

# Soil Data Configuration
# Estimated default soil values (fallback)
DEFAULT_SOIL_VALUES = {
    "N": 50,
    "P": 35,
    "K": 40,
    "ph": 6.5,
}

# Soil Quality Indicators
SOIL_CONFIDENCE_HIGH = 0.8
SOIL_CONFIDENCE_MODERATE = 0.5
SOIL_CONFIDENCE_LOW = 0.3

# Dataset URLs for Training
DATASET_URLS = [
    "https://raw.githubusercontent.com/Gladiator07/Harvestify/master/Data-processed/crop_recommendation.csv",
]

# Fallback Dataset (small, real data subset for offline capability)
FALLBACK_DATASET = """N,P,K,temperature,humidity,ph,rainfall,label
38,135,203,23.76,93.66,5.97,100.83,apple
28,136,200,23.06,92.4,6.25,114.74,apple
15,123,204,22.53,92.55,6.37,115.38,apple
15,133,199,24.0,91.61,5.82,117.61,apple
95,88,52,28.0,78.9,6.24,94.68,banana
93,81,50,27.72,76.58,6.04,102.21,banana
108,72,46,25.16,84.98,6.11,90.95,banana
82,78,46,25.06,84.97,5.74,110.44,banana
58,79,17,27.25,66.1,7.04,62.32,blackgram
33,75,21,33.05,68.94,6.69,62.3,blackgram
37,62,17,25.69,69.84,7.12,74.62,blackgram
34,80,19,31.49,63.06,6.52,71.48,blackgram
53,73,77,19.71,18.1,7.33,73.64,chickpea
29,77,75,17.5,15.48,7.78,72.94,chickpea
42,74,83,19.26,14.28,7.55,65.78,chickpea
35,64,78,17.93,14.27,7.5,85.37,chickpea
17,29,26,26.14,93.28,6.07,195.41,coconut
24,27,34,28.88,95.11,6.2,145.06,coconut
26,18,27,27.46,92.91,5.84,142.14,coconut
39,7,29,27.54,94.59,6.36,150.2,coconut
93,26,27,24.59,56.47,7.29,137.7,coffee
120,20,34,23.57,50.56,6.91,130.38,coffee
114,20,26,25.56,62.67,7.28,193.59,coffee
113,15,29,27.1,63.55,6.78,190.24,coffee
116,56,17,24.71,77.73,7.98,85.25,cotton
107,36,21,25.29,75.67,6.21,62.64,cotton
132,52,19,24.16,76.74,6.44,61.95,cotton
110,39,25,22.61,77.34,7.21,75.14,cotton
39,140,203,21.12,80.63,6.35,69.28,grapes
8,139,199,29.37,81.54,6.34,66.13,grapes
6,140,205,17.67,82.93,6.31,69.87,grapes
31,136,197,31.11,83.34,5.65,71.43,grapes
90,50,44,26.92,73.49,6.25,171.47,jute
100,58,41,23.17,87.88,6.66,160.62,jute
61,41,35,24.97,79.48,6.84,195.76,jute
75,41,35,24.97,78.63,6.86,166.64,jute
14,59,15,21.35,22.91,5.78,146.45,kidneybeans
3,77,25,24.85,22.89,5.61,62.21,kidneybeans
37,56,25,22.06,19.6,5.77,126.73,kidneybeans
17,77,24,20.77,18.93,5.57,109.02,kidneybeans
14,76,20,29.06,62.11,7.04,36.5,lentil
32,79,22,27.6,63.46,5.92,54.38,lentil
26,66,22,18.06,65.1,6.3,51.55,lentil
24,61,17,22.64,65.45,6.23,38.3,lentil
71,52,18,25.11,55.98,5.79,78.16,maize
60,38,17,18.42,64.24,6.47,76.41,maize
99,39,18,19.2,68.31,6.11,87.85,maize
96,46,22,20.58,69.0,6.5,66.29,maize
7,28,35,30.02,46.78,4.67,96.64,mango
23,23,30,32.82,47.46,4.76,90.89,mango
18,20,26,31.67,51.99,5.44,89.98,mango
34,34,35,27.27,47.17,6.42,95.26,mango
29,41,21,31.49,62.85,8.87,64.57,mothbeans
39,36,22,29.34,60.5,9.07,34.03,mothbeans
23,58,19,24.17,58.25,5.24,59.19,mothbeans
29,44,20,30.04,63.56,8.62,31.83,mothbeans
24,44,17,29.86,80.03,6.67,50.66,mungbean
21,44,18,27.07,86.9,7.13,50.47,mungbean
20,41,20,29.27,89.49,7.07,50.92,mungbean
2,39,15,28.07,82.91,6.48,49.62,mungbean
83,15,49,28.93,91.39,6.44,23.2,muskmelon
93,22,48,29.13,91.52,6.78,21.9,muskmelon
115,12,52,27.51,94.96,6.69,21.02,muskmelon
99,12,52,28.7,94.31,6.0,22.22,muskmelon
24,30,11,32.4,94.52,6.6,113.25,orange
14,22,9,17.25,91.14,6.54,112.51,orange
31,5,14,17.67,91.7,6.58,110.69,orange
40,22,6,24.54,91.91,6.49,115.98,orange
39,69,53,25.93,93.02,6.96,241.82,papaya
49,54,50,25.62,93.18,6.76,97.26,papaya
69,67,52,27.72,94.44,6.83,82.83,papaya
52,59,53,28.2,93.56,6.72,93.0,papaya
20,47,10,27.72,56.1,6.91,49.32,pigeonpeas
32,47,7,29.9,53.5,7.5,59.82,pigeonpeas
27,44,9,25.78,59.48,6.8,52.3,pigeonpeas
21,57,8,31.13,55.22,8.13,39.36,pigeonpeas
23,45,77,32.58,84.5,6.55,120.79,pomegranate
23,57,77,26.85,80.27,6.54,106.76,pomegranate
14,52,79,24.92,83.26,6.6,108.25,pomegranate
23,41,77,28.64,80.44,6.29,114.92,pomegranate
60,55,41,27.53,66.41,6.74,244.97,rice
56,62,42,27.15,67.55,6.79,265.25,rice
58,40,39,27.51,66.8,6.82,244.47,rice
47,50,36,26.99,66.09,6.74,218.97,rice
32,64,80,23.59,98.9,6.53,34.2,watermelon
35,35,78,29.32,98.0,6.49,34.9,watermelon
26,75,87,28.12,98.54,6.77,32.49,watermelon
28,34,84,27.7,98.51,6.5,33.13,watermelon
"""

# Application Metadata
APP_VERSION = "2.0.0"
APP_NAME = "AgriSense AI"
APP_DESCRIPTION = "Agricultural Decision-Support Platform for Andhra Pradesh & Telangana"

# Model Metadata Template
MODEL_METADATA_TEMPLATE = {
    "version": "1.0",
    "app_version": APP_VERSION,
    "crop_model": {
        "type": "RandomForestClassifier",
        "features": CROP_FEATURES,
        "n_classes": len(CROPS),
        "training_date": None,
        "dataset_size": None,
        "accuracy": None,
    },
    "yield_model": {
        "type": "RandomForestRegressor",
        "features": YIELD_FEATURES,
        "training_date": None,
        "dataset_size": None,
        "r2_score": None,
        "mae": None,
    },
    "dataset": {
        "source": "Crop Recommendation Dataset (ICFA/ICAR)",
        "url": DATASET_URLS[0],
        "note": "Well-known public dataset for ML education",
    },
    "limitations": {
        "yield_model": "Documented synthetic/estimated yield model, not field-validated real-world data",
        "soil_data": "Location-based estimates, not laboratory measurements",
    }
}
