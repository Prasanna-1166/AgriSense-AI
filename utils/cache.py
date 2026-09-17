"""
Caching utilities for AgriSense AI
"""
import json
import logging
import os
import time
from typing import Any, Dict, Optional
from datetime import datetime, timezone

log = logging.getLogger(__name__)


class SimpleCache:
    """Simple file-based cache for API responses and predictions."""
    
    def __init__(self, cache_dir: str, ttl_seconds: int = 3600):
        """
        Initialize cache.
        
        Args:
            cache_dir: Directory to store cache files
            ttl_seconds: Time-to-live for cached entries
        """
        self.cache_dir = cache_dir
        self.ttl_seconds = ttl_seconds
        os.makedirs(cache_dir, exist_ok=True)
    
    def _get_cache_path(self, key: str) -> str:
        """Get filesystem path for cache key."""
        # Sanitize key to prevent directory traversal
        safe_key = "".join(c for c in key if c.isalnum() or c in "-_.")
        return os.path.join(self.cache_dir, f"{safe_key}.json")
    
    def get(self, key: str) -> Optional[Any]:
        """
        Retrieve value from cache if it exists and hasn't expired.
        
        Args:
            key: Cache key
        
        Returns:
            Cached value or None if not found or expired
        """
        path = self._get_cache_path(key)
        
        if not os.path.exists(path):
            return None
        
        try:
            with open(path, "r") as f:
                data = json.load(f)
            
            # Check expiration
            timestamp = data.get("timestamp", 0)
            if time.time() - timestamp > self.ttl_seconds:
                os.remove(path)
                return None
            
            return data.get("value")
        
        except Exception as e:
            log.warning(f"Cache read error for key '{key}': {e}")
            return None
    
    def set(self, key: str, value: Any) -> bool:
        """
        Store value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
        
        Returns:
            True if successful, False otherwise
        """
        path = self._get_cache_path(key)
        
        try:
            data = {
                "key": key,
                "value": value,
                "timestamp": time.time(),
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            with open(path, "w") as f:
                json.dump(data, f)
            return True
        except Exception as e:
            log.warning(f"Cache write error for key '{key}': {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete cache entry."""
        path = self._get_cache_path(key)
        if os.path.exists(path):
            try:
                os.remove(path)
                return True
            except Exception as e:
                log.warning(f"Cache delete error for key '{key}': {e}")
                return False
        return False
    
    def clear(self) -> int:
        """Clear all cache entries. Returns count of deleted files."""
        count = 0
        try:
            for filename in os.listdir(self.cache_dir):
                if filename.endswith(".json"):
                    path = os.path.join(self.cache_dir, filename)
                    try:
                        os.remove(path)
                        count += 1
                    except Exception as e:
                        log.warning(f"Error deleting cache file {filename}: {e}")
            return count
        except Exception as e:
            log.error(f"Error clearing cache: {e}")
            return 0
    
    def cleanup_expired(self) -> int:
        """Remove expired cache entries. Returns count of deleted files."""
        count = 0
        try:
            for filename in os.listdir(self.cache_dir):
                if filename.endswith(".json"):
                    path = os.path.join(self.cache_dir, filename)
                    try:
                        with open(path, "r") as f:
                            data = json.load(f)
                        
                        timestamp = data.get("timestamp", 0)
                        if time.time() - timestamp > self.ttl_seconds:
                            os.remove(path)
                            count += 1
                    except Exception as e:
                        log.warning(f"Error processing cache file {filename}: {e}")
            return count
        except Exception as e:
            log.error(f"Error cleaning up cache: {e}")
            return 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        try:
            files = [f for f in os.listdir(self.cache_dir) if f.endswith(".json")]
            total_size = sum(
                os.path.getsize(os.path.join(self.cache_dir, f)) 
                for f in files
            ) / (1024 * 1024)  # MB
            
            return {
                "entries": len(files),
                "size_mb": round(total_size, 2),
                "ttl_seconds": self.ttl_seconds
            }
        except Exception as e:
            log.error(f"Error getting cache stats: {e}")
            return {}


class PredictionHistory:
    """Manage local prediction history."""
    
    def __init__(self, history_file: str):
        """
        Initialize prediction history manager.
        
        Args:
            history_file: Path to history JSON file
        """
        self.history_file = history_file
        self._ensure_file()
    
    def _ensure_file(self):
        """Ensure history file exists."""
        if not os.path.exists(self.history_file):
            try:
                with open(self.history_file, "w") as f:
                    json.dump({"predictions": []}, f)
            except Exception as e:
                log.warning(f"Could not create history file: {e}")
    
    def add(self, prediction: Dict[str, Any]) -> bool:
        """Add prediction to history."""
        try:
            with open(self.history_file, "r") as f:
                data = json.load(f)
            
            # Add timestamp if not present
            if "timestamp" not in prediction:
                prediction["timestamp"] = datetime.now(timezone.utc).isoformat()
            
            # Generate ID if not present
            if "id" not in prediction:
                import hashlib
                content = json.dumps(prediction, sort_keys=True).encode()
                prediction["id"] = hashlib.md5(content).hexdigest()[:12]
            
            data["predictions"].append(prediction)
            
            # Keep only last 100 predictions
            if len(data["predictions"]) > 100:
                data["predictions"] = data["predictions"][-100:]
            
            with open(self.history_file, "w") as f:
                json.dump(data, f, indent=2)
            
            return True
        except Exception as e:
            log.warning(f"Error adding to history: {e}")
            return False
    
    def get_all(self) -> list:
        """Get all predictions from history."""
        try:
            with open(self.history_file, "r") as f:
                data = json.load(f)
            return data.get("predictions", [])
        except Exception as e:
            log.warning(f"Error reading history: {e}")
            return []
    
    def get_recent(self, limit: int = 10) -> list:
        """Get recent predictions."""
        all_predictions = self.get_all()
        return all_predictions[-limit:]
    
    def delete(self, prediction_id: str) -> bool:
        """Delete prediction by ID."""
        try:
            with open(self.history_file, "r") as f:
                data = json.load(f)
            
            original_count = len(data["predictions"])
            data["predictions"] = [
                p for p in data["predictions"]
                if p.get("id") != prediction_id
            ]
            
            if len(data["predictions"]) < original_count:
                with open(self.history_file, "w") as f:
                    json.dump(data, f, indent=2)
                return True
            return False
        except Exception as e:
            log.warning(f"Error deleting from history: {e}")
            return False
    
    def clear(self) -> bool:
        """Clear all history."""
        try:
            with open(self.history_file, "w") as f:
                json.dump({"predictions": []}, f)
            return True
        except Exception as e:
            log.warning(f"Error clearing history: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get history statistics."""
        predictions = self.get_all()
        if not predictions:
            return {"total": 0, "recent_7_days": 0}
        
        # Count predictions from last 7 days
        seven_days_ago = time.time() - (7 * 24 * 3600)
        recent_count = 0
        
        for pred in predictions:
            try:
                timestamp_str = pred.get("timestamp", "")
                if timestamp_str:
                    dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                    if dt.timestamp() > seven_days_ago:
                        recent_count += 1
            except Exception:
                pass
        
        return {
            "total": len(predictions),
            "recent_7_days": recent_count
        }
