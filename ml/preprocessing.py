"""
ML preprocessing and dataset handling for AgriSense AI
"""
import io
import logging
import pandas as pd
import numpy as np
from typing import Dict, Tuple, Optional
import requests

from config.settings import (
    DATASET_URLS, FALLBACK_DATASET, CROP_FEATURES, CROPS
)

log = logging.getLogger(__name__)


def load_training_dataframe(cache_path: Optional[str] = None, force_online: bool = False) -> Tuple[pd.DataFrame, bool, str]:
    """
    Load the training dataset from online source with fallback.
    
    Args:
        cache_path: Path to cache CSV file
        force_online: Force online fetch even if cache exists
    
    Returns:
        Tuple of (dataframe, is_full_dataset, source_info)
    """
    
    # Try cache first
    if cache_path and not force_online:
        try:
            df = pd.read_csv(cache_path)
            if len(df) > 100:
                log.info(f"Loaded {len(df)} rows from cache: {cache_path}")
                return df, True, "cache"
        except Exception as e:
            log.warning(f"Cache load failed: {e}")
    
    # Try online sources
    for url in DATASET_URLS:
        try:
            log.info(f"Downloading dataset from: {url}")
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            
            df = pd.read_csv(io.StringIO(response.text))
            
            # Validate dataset
            if not validate_dataset(df):
                log.warning(f"Downloaded dataset failed validation: {url}")
                continue
            
            log.info(f"Successfully loaded {len(df)} rows from online source")
            
            # Cache if path provided
            if cache_path:
                try:
                    df.to_csv(cache_path, index=False)
                    log.info(f"Cached dataset to: {cache_path}")
                except Exception as e:
                    log.warning(f"Failed to cache dataset: {e}")
            
            return df, True, "online"
        
        except Exception as e:
            log.warning(f"Failed to load from {url}: {e}")
            continue
    
    # Fallback to bundled dataset
    log.warning("All online sources failed, using bundled fallback dataset")
    try:
        df = pd.read_csv(io.StringIO(FALLBACK_DATASET))
        if validate_dataset(df):
            log.info(f"Loaded fallback dataset with {len(df)} rows")
            return df, False, "fallback"
    except Exception as e:
        log.error(f"Even fallback dataset failed: {e}")
    
    # Return empty dataframe as last resort
    log.error("Could not load any dataset")
    return pd.DataFrame(), False, "error"


def validate_dataset(df: pd.DataFrame) -> bool:
    """Validate dataset structure and content."""
    try:
        required_columns = CROP_FEATURES + ["label"]
        if not all(col in df.columns for col in required_columns):
            log.error(f"Missing required columns. Expected: {required_columns}")
            return False
        
        # Check for reasonable number of rows
        if len(df) < 50:
            log.warning(f"Dataset has only {len(df)} rows")
        
        # Check for missing values
        if df[required_columns].isnull().any().any():
            log.warning("Dataset contains null values")
        
        return True
    except Exception as e:
        log.error(f"Dataset validation error: {e}")
        return False


def clean_dataset(df: pd.DataFrame) -> pd.DataFrame:
    """Clean and prepare dataset for training."""
    try:
        df = df.copy()
        
        # Remove rows with missing values in critical columns
        critical_cols = CROP_FEATURES + ["label"]
        df = df.dropna(subset=critical_cols)
        
        # Remove duplicates
        df = df.drop_duplicates()
        
        # Ensure label is in expected crop list
        df = df[df["label"].isin(CROPS)]
        
        # Handle outliers (simple approach: remove extreme values)
        for col in CROP_FEATURES:
            Q1 = df[col].quantile(0.01)
            Q3 = df[col].quantile(0.99)
            df = df[(df[col] >= Q1) & (df[col] <= Q3)]
        
        log.info(f"Cleaned dataset to {len(df)} rows")
        return df
    
    except Exception as e:
        log.error(f"Error cleaning dataset: {e}")
        return df


def compute_crop_stats(df: pd.DataFrame) -> Dict[str, Dict[str, float]]:
    """
    Compute statistics (mean, std) for each crop and feature.
    Used for explanations and synthetic yield data generation.
    """
    stats = {}
    
    for crop in CROPS:
        crop_data = df[df["label"] == crop]
        if len(crop_data) > 0:
            crop_stats = {}
            for feature in CROP_FEATURES:
                crop_stats[feature] = {
                    "mean": float(crop_data[feature].mean()),
                    "std": float(crop_data[feature].std()),
                    "min": float(crop_data[feature].min()),
                    "max": float(crop_data[feature].max()),
                }
            stats[crop] = crop_stats
        else:
            # Use defaults if crop not in dataset
            stats[crop] = {
                feature: {"mean": 50, "std": 20, "min": 10, "max": 100}
                for feature in CROP_FEATURES
            }
    
    return stats


def build_synthetic_yield_dataset(
    crop_stats: Dict[str, Dict[str, float]],
    samples_per_crop: int = 160
) -> pd.DataFrame:
    """
    Build synthetic yield training data based on crop statistics.
    
    The synthetic target is computed as:
    - Base yield for crop
    - Scaled by how well input conditions match crop's comfort zone
    - Adjusted by irrigation level
    
    This creates a defensible, documented synthetic dataset that allows
    the yield regressor to learn general patterns without claiming real-world
    field validation.
    """
    from config.settings import BASE_YIELD_TONNES_PER_HA
    
    rows = []
    
    np.random.seed(42)
    
    for crop in CROPS:
        crop_base_yield = BASE_YIELD_TONNES_PER_HA.get(crop, 5.0)
        crop_stat = crop_stats.get(crop, {})
        
        for _ in range(samples_per_crop):
            # Generate feature values centered around crop's typical range
            sample = {}
            for feature in CROP_FEATURES:
                stat = crop_stat.get(feature, {})
                mean = stat.get("mean", 50)
                std = max(stat.get("std", 20), 1)
                # Add noise to diversify samples
                sample[feature] = np.clip(
                    np.random.normal(mean, std * 0.7),
                    stat.get("min", 0),
                    stat.get("max", 300)
                )
            
            # Compute synthetic yield
            # Calculate how well conditions match crop's preferences
            z_scores = []
            for feature in CROP_FEATURES:
                stat = crop_stat.get(feature, {})
                mean = stat.get("mean", 50)
                std = max(stat.get("std", 20), 1)
                if std > 0:
                    z = abs((sample[feature] - mean) / std)
                else:
                    z = 0
                z_scores.append(z)
            
            # Calculate suitability (lower z-score = better match)
            avg_z = np.mean(z_scores)
            suitability = max(0, 1 - (avg_z * 0.15))  # Non-linear decay
            
            # Irrigation adjustment
            irrigation_val = np.random.choice([0, 1, 2])  # 0=none, 1=partial, 2=full
            irrigation_bonus = irrigation_val * 0.1
            
            # Final synthetic yield
            synthetic_yield = crop_base_yield * (0.7 + 0.3 * suitability) * (1 + irrigation_bonus)
            synthetic_yield = max(0.1, min(synthetic_yield, crop_base_yield * 2))  # Bounds
            
            row = sample.copy()
            row["crop_index"] = CROPS.index(crop)
            row["irrigation"] = irrigation_val
            row["yield_t_per_ha"] = synthetic_yield
            rows.append(row)
    
    df_synthetic = pd.DataFrame(rows)
    log.info(f"Generated {len(df_synthetic)} synthetic yield samples")
    return df_synthetic


def prepare_prediction_features(
    data: Dict[str, float],
    feature_names: list,
    crop_index: Optional[int] = None,
    irrigation: Optional[int] = None
) -> Tuple[np.ndarray, bool]:
    """
    Prepare feature vector for prediction.
    
    Returns:
        Tuple of (feature_array, success_bool)
    """
    try:
        X = []
        for feature in feature_names:
            if feature == "crop_index":
                X.append(crop_index if crop_index is not None else 0)
            elif feature == "irrigation":
                # Convert string to numeric: 0=none, 1=partial, 2=full
                irr_str = data.get(feature, "partial")
                irr_map = {"none": 0, "partial": 1, "full": 2}
                X.append(irr_map.get(str(irr_str).lower(), 1))
            else:
                X.append(float(data.get(feature, 0)))
        
        return np.array([X]), True
    except Exception as e:
        log.error(f"Error preparing features: {e}")
        return np.array([[]]), False
