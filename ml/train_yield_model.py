#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AgriSense AI - Yield Estimation Model Training
================================================

Trains the RandomForestRegressor used for yield estimation.

IMPORTANT TRANSPARENCY NOTE:
This model is trained on a documented SYNTHETIC dataset, not real-world
field-validated yield records. No verified, freely redistributable dataset
pairing these exact soil/climate features with real yield figures could be
located. The synthetic target is built from reference average yields per
crop, scaled by how closely input conditions match that crop's statistical
comfort zone (from the real crop-recommendation training data), plus an
irrigation adjustment.

This is explicitly surfaced to users in the UI/API as an ESTIMATE, not a
validated real-world yield model.

Usage:
    python -m ml.train_yield_model
"""
import json
import logging
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import joblib
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split

from config.settings import (
    YIELD_MODEL_PATH, DATASET_CACHE_PATH, RANDOM_SEED,
    CROP_FEATURES, YIELD_FEATURES
)
from ml.preprocessing import (
    load_training_dataframe, clean_dataset, compute_crop_stats,
    build_synthetic_yield_dataset
)
from ml.train_crop_model import update_metadata

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s %(message)s")
log = logging.getLogger("train_yield_model")


def train():
    """Train and save the yield estimation model."""
    log.info("=" * 60)
    log.info("AgriSense AI - Yield Model Training (SYNTHETIC dataset)")
    log.info("=" * 60)

    start_time = time.time()

    # Load base dataset to compute crop stats
    log.info("Loading base dataset for crop statistics...")
    df, is_full_dataset, source = load_training_dataframe(
        cache_path=DATASET_CACHE_PATH,
        force_online=False  # Use cache if available (already fetched by crop model training)
    )

    if df.empty:
        log.error("Failed to load base dataset. Aborting.")
        return False

    df = clean_dataset(df)
    crop_stats = compute_crop_stats(df)

    # Build synthetic yield dataset
    log.info("Building synthetic yield training dataset...")
    yield_df = build_synthetic_yield_dataset(crop_stats, samples_per_crop=160)
    log.info(f"Synthetic dataset: {len(yield_df)} rows")

    # Prepare features and target
    X = yield_df[YIELD_FEATURES].values
    y = yield_df["yield_t_per_ha"].values

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=RANDOM_SEED
    )

    log.info(f"Training set: {len(X_train)} rows, Test set: {len(X_test)} rows")

    # Train model
    log.info("Training RandomForestRegressor...")
    model = RandomForestRegressor(
        n_estimators=200,
        max_depth=12,
        min_samples_split=4,
        min_samples_leaf=2,
        random_state=RANDOM_SEED,
        n_jobs=-1
    )
    model.fit(X_train, y_train)

    # Evaluate
    y_pred = model.predict(X_test)
    r2 = r2_score(y_test, y_pred)
    mae = mean_absolute_error(y_test, y_pred)
    log.info(f"Test R² score: {r2:.4f}")
    log.info(f"Test MAE: {mae:.4f} tonnes/hectare")

    # Save model
    os.makedirs(os.path.dirname(YIELD_MODEL_PATH), exist_ok=True)
    joblib.dump(model, YIELD_MODEL_PATH)
    log.info(f"Model saved to: {YIELD_MODEL_PATH}")

    # Update metadata
    update_metadata(
        model_type="yield_model",
        dataset_size=len(yield_df),
        is_full_dataset=False,  # Always synthetic
        source="synthetic",
        r2_score=r2,
        mae=mae,
        training_time=time.time() - start_time
    )

    log.info(f"Training complete in {time.time() - start_time:.1f}s")
    log.info("=" * 60)
    log.warning("REMINDER: This yield model is trained on SYNTHETIC/ESTIMATED data.")
    log.warning("It should NOT be presented as a field-validated real-world yield predictor.")
    return True


if __name__ == "__main__":
    success = train()
    sys.exit(0 if success else 1)
