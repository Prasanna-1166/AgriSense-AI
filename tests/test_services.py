"""Tests for service-layer fallback behavior (never crash on API failure)."""
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services import geocoding_service
from utils.cache import SimpleCache, PredictionHistory
import tempfile
import shutil


def test_geocoding_search_empty_query_does_not_raise():
    result = geocoding_service.search_location("")
    assert result["results"] == []
    assert result["error"] is not None


def test_simple_cache_set_and_get():
    tmpdir = tempfile.mkdtemp()
    try:
        cache = SimpleCache(tmpdir, ttl_seconds=100)
        cache.set("test_key", {"value": 42})
        result = cache.get("test_key")
        assert result == {"value": 42}
    finally:
        shutil.rmtree(tmpdir)


def test_simple_cache_expired_returns_none():
    tmpdir = tempfile.mkdtemp()
    try:
        cache = SimpleCache(tmpdir, ttl_seconds=0)
        cache.set("test_key", {"value": 42})
        import time
        time.sleep(0.1)
        result = cache.get("test_key")
        assert result is None
    finally:
        shutil.rmtree(tmpdir)


def test_simple_cache_missing_key_returns_none():
    tmpdir = tempfile.mkdtemp()
    try:
        cache = SimpleCache(tmpdir, ttl_seconds=100)
        result = cache.get("nonexistent")
        assert result is None
    finally:
        shutil.rmtree(tmpdir)


def test_prediction_history_add_and_retrieve():
    tmpdir = tempfile.mkdtemp()
    try:
        history_file = os.path.join(tmpdir, "history.json")
        history = PredictionHistory(history_file)
        history.add({"crop": "rice", "suitability": 90})
        all_predictions = history.get_all()
        assert len(all_predictions) == 1
        assert all_predictions[0]["crop"] == "rice"
    finally:
        shutil.rmtree(tmpdir)


def test_prediction_history_delete():
    tmpdir = tempfile.mkdtemp()
    try:
        history_file = os.path.join(tmpdir, "history.json")
        history = PredictionHistory(history_file)
        history.add({"id": "abc123", "crop": "maize"})
        success = history.delete("abc123")
        assert success is True
        assert len(history.get_all()) == 0
    finally:
        shutil.rmtree(tmpdir)


def test_prediction_history_clear():
    tmpdir = tempfile.mkdtemp()
    try:
        history_file = os.path.join(tmpdir, "history.json")
        history = PredictionHistory(history_file)
        history.add({"crop": "wheat"})
        history.add({"crop": "cotton"})
        history.clear()
        assert len(history.get_all()) == 0
    finally:
        shutil.rmtree(tmpdir)
