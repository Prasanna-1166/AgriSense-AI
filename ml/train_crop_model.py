#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AgriSense AI - Crop Recommendation Model Training
===================================================

Trains the RandomForestClassifier used for crop suitability prediction.
This is a SEPARATE process from the Flask application - the app only
loads the trained model, it never retrains on startup.

Usage:
    python -m ml.train_crop_model

Or directly:
    cd AgriSense-AI
    python ml/train_crop_model.py
"""
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone

# Allow running as script
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split

from config.settings import (
    CROP_MODEL_PATH, DATASET_CACHE_PATH, RANDOM_SEED,
    CROP_FEATURES, METADATA_PATH
)
from ml.preprocessing import load_training_dataframe, clean_dataset, compute_crop_stats

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s %(message)s")
log = logging.getLogger("train_crop_model")


def train():
    """Train and save the crop recommendation model."""
    log.info("=" * 60)
    log.info("AgriSense AI - Crop Model Training")
    log.info("=" * 60)

    start_time = time.time()

    # Load dataset
    log.info("Loading training dataset...")
    df, is_full_dataset, source = load_training_dataframe(
        cache_path=DATASET_CACHE_PATH,
        force_online=True
    )

    if df.empty:
        log.error("Failed to load any training data. Aborting.")
        return False

    log.info(f"Dataset loaded: {len(df)} rows from '{source}' (full dataset: {is_full_dataset})")

    # Clean dataset
    df = clean_dataset(df)
    log.info(f"Dataset after cleaning: {len(df)} rows")

    if len(df) < 30:
        log.error("Insufficient training data after cleaning. Aborting.")
        return False

    # Prepare features and labels
    X = df[CROP_FEATURES].values
    y = df["label"].values

    # Train/test split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=RANDOM_SEED, stratify=y
    )

    log.info(f"Training set: {len(X_train)} rows, Test set: {len(X_test)} rows")

    # Train model
    log.info("Training RandomForestClassifier...")
    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=None,
        min_samples_split=2,
        min_samples_leaf=1,
        random_state=RANDOM_SEED,
        n_jobs=-1
    )
    model.fit(X_train, y_train)

    # Evaluate
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    log.info(f"Test accuracy: {accuracy:.4f}")

    report = classification_report(y_test, y_pred, output_dict=True, zero_division=0)

    # Compute crop statistics (needed for explanations)
    crop_stats = compute_crop_stats(df)

    # Save model
    os.makedirs(os.path.dirname(CROP_MODEL_PATH), exist_ok=True)
    joblib.dump(model, CROP_MODEL_PATH)
    log.info(f"Model saved to: {CROP_MODEL_PATH}")

    # Save crop stats separately for the predictor
    crop_stats_path = os.path.join(os.path.dirname(CROP_MODEL_PATH), "crop_stats.json")
    with open(crop_stats_path, "w") as f:
        json.dump(crop_stats, f, indent=2)
    log.info(f"Crop statistics saved to: {crop_stats_path}")

    # Update metadata
    update_metadata(
        model_type="crop_model",
        dataset_size=len(df),
        is_full_dataset=is_full_dataset,
        source=source,
        accuracy=accuracy,
        training_time=time.time() - start_time
    )

    log.info(f"Training complete in {time.time() - start_time:.1f}s")
    log.info("=" * 60)
    return True


def update_metadata(model_type, dataset_size, is_full_dataset, source, accuracy=None,
                     r2_score=None, mae=None, training_time=None):
    """Update the model metadata file."""
    metadata = {}
    if os.path.exists(METADATA_PATH):
        try:
            with open(METADATA_PATH, "r") as f:
                metadata = json.load(f)
        except Exception:
            metadata = {}

    timestamp = datetime.now(timezone.utc).isoformat()

    if model_type == "crop_model":
        metadata["crop_model"] = {
            "type": "RandomForestClassifier",
            "features": CROP_FEATURES,
            "training_timestamp": timestamp,
            "dataset_size": dataset_size,
            "dataset_full": is_full_dataset,
            "dataset_source": source,
            "accuracy": round(float(accuracy), 4) if accuracy is not None else None,
            "random_seed": RANDOM_SEED,
            "training_time_seconds": round(training_time, 1) if training_time else None,
            "notes": "Trained on the public Crop Recommendation Dataset (N, P, K, temperature, humidity, pH, rainfall -> crop label)."
        }
    elif model_type == "yield_model":
        metadata["yield_model"] = {
            "type": "RandomForestRegressor",
            "features": CROP_FEATURES + ["crop_index", "irrigation"],
            "training_timestamp": timestamp,
            "dataset_size": dataset_size,
            "r2_score": round(float(r2_score), 4) if r2_score is not None else None,
            "mae": round(float(mae), 4) if mae is not None else None,
            "random_seed": RANDOM_SEED,
            "training_time_seconds": round(training_time, 1) if training_time else None,
            "notes": "DOCUMENTED SYNTHETIC/ESTIMATED yield model. Trained on reference average yields scaled by how closely input conditions match each crop's statistical comfort zone, plus an irrigation adjustment. NOT a field-validated real-world yield dataset.",
            "limitation": "This is an estimate for general guidance only, not a scientifically validated real-world yield prediction."
        }

    metadata["last_updated"] = timestamp

    os.makedirs(os.path.dirname(METADATA_PATH), exist_ok=True)
    with open(METADATA_PATH, "w") as f:
        json.dump(metadata, f, indent=2)


if __name__ == "__main__":
    success = train()
    sys.exit(0 if success else 1)
