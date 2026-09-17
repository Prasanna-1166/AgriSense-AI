"""
AgriSense AI - Soil Report Extraction Service
================================================

Handles soil test report uploads (PDF or image) and attempts structured
value extraction.

IMPORTANT - EXTRACTION IS NEVER AUTO-TRUSTED:
Every value this module extracts is tagged status="DOCUMENT_EXTRACTED"
and the API layer requires the user to confirm or correct each value
before it is used in any recommendation. If extraction fails or no
relevant fields are found, this module returns a clear failure so the
caller can fall back to manual entry - it never fabricates values.
"""
import logging
import os
import re
import uuid
from typing import Dict, Optional

from services.soil_service import SOIL_HEALTH_CARD_PARAMS

log = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg"}
MAX_UPLOAD_SIZE_BYTES = 8 * 1024 * 1024  # 8 MB

# Regex patterns to spot common Soil Health Card style lines, e.g.
# "pH : 6.8", "Available Nitrogen (N) : 245 kg/ha", "EC (dS/m): 0.32"
_FIELD_PATTERNS = {
    "ph": re.compile(r"\bpH\b[^0-9]{0,15}([0-9]+\.?[0-9]*)", re.IGNORECASE),
    "ec": re.compile(r"\bEC\b[^0-9]{0,20}([0-9]+\.?[0-9]*)", re.IGNORECASE),
    "organic_carbon": re.compile(r"organic\s*carbon[^0-9]{0,20}([0-9]+\.?[0-9]*)", re.IGNORECASE),
    "N": re.compile(r"nitrogen\s*\(?N\)?[^0-9]{0,20}([0-9]+\.?[0-9]*)", re.IGNORECASE),
    "P": re.compile(r"phosphor(?:us|ous)\s*\(?P\)?[^0-9]{0,20}([0-9]+\.?[0-9]*)", re.IGNORECASE),
    "K": re.compile(r"potassium\s*\(?K\)?[^0-9]{0,20}([0-9]+\.?[0-9]*)", re.IGNORECASE),
    "sulphur": re.compile(r"sulph?ur\s*\(?S\)?[^0-9]{0,20}([0-9]+\.?[0-9]*)", re.IGNORECASE),
    "zinc": re.compile(r"zinc\s*\(?Zn\)?[^0-9]{0,20}([0-9]+\.?[0-9]*)", re.IGNORECASE),
    "iron": re.compile(r"iron\s*\(?Fe\)?[^0-9]{0,20}([0-9]+\.?[0-9]*)", re.IGNORECASE),
    "manganese": re.compile(r"manganese\s*\(?Mn\)?[^0-9]{0,20}([0-9]+\.?[0-9]*)", re.IGNORECASE),
    "copper": re.compile(r"copper\s*\(?Cu\)?[^0-9]{0,20}([0-9]+\.?[0-9]*)", re.IGNORECASE),
    "boron": re.compile(r"boron\s*\(?B\)?[^0-9]{0,20}([0-9]+\.?[0-9]*)", re.IGNORECASE),
}


def validate_upload(filename: str, size_bytes: int) -> Dict:
    """Validate an uploaded soil report file before processing."""
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return {"valid": False, "error": f"Unsupported file type '{ext}'. Allowed: PDF, PNG, JPG."}
    if size_bytes > MAX_UPLOAD_SIZE_BYTES:
        return {"valid": False, "error": f"File exceeds the {MAX_UPLOAD_SIZE_BYTES // (1024*1024)} MB limit."}
    return {"valid": True, "error": None}


def safe_store_path(upload_dir: str, original_filename: str) -> str:
    """Generate a safe, non-guessable storage path for an uploaded file."""
    ext = os.path.splitext(original_filename)[1].lower()
    safe_name = f"{uuid.uuid4().hex}{ext}"
    os.makedirs(upload_dir, exist_ok=True)
    return os.path.join(upload_dir, safe_name)


def _extract_text_from_pdf(path: str) -> Optional[str]:
    """Extract raw text from a PDF using pypdf, if available."""
    try:
        from pypdf import PdfReader
    except ImportError:
        log.warning("pypdf not installed - PDF text extraction unavailable.")
        return None

    try:
        reader = PdfReader(path)
        text = "\n".join((page.extract_text() or "") for page in reader.pages)
        return text
    except Exception as e:
        log.warning(f"PDF text extraction failed: {e}")
        return None


def _extract_text_from_image(path: str) -> Optional[str]:
    """Extract text from an image using pytesseract, if available."""
    try:
        import pytesseract
        from PIL import Image
    except ImportError:
        log.warning("pytesseract/Pillow not installed - image OCR unavailable.")
        return None

    try:
        return pytesseract.image_to_string(Image.open(path))
    except Exception as e:
        log.warning(f"Image OCR failed: {e}")
        return None


def extract_soil_report(path: str) -> Dict:
    """
    Attempt structured extraction from an uploaded soil report.

    Returns:
        {
            "success": bool,
            "extracted": {field: {"value":..., "status": "DOCUMENT_EXTRACTED", ...}},
            "message": str,
            "requires_confirmation": True   # always True when success
        }
    """
    ext = os.path.splitext(path)[1].lower()

    text = None
    if ext == ".pdf":
        text = _extract_text_from_pdf(path)
    elif ext in (".png", ".jpg", ".jpeg"):
        text = _extract_text_from_image(path)

    if not text:
        return {
            "success": False,
            "extracted": {},
            "message": "Automatic extraction is unavailable or failed for this file. "
                       "Please enter your soil test values manually.",
            "requires_confirmation": False,
        }

    extracted = {}
    for field, pattern in _FIELD_PATTERNS.items():
        match = pattern.search(text)
        if match:
            try:
                value = float(match.group(1))
            except ValueError:
                continue
            spec = SOIL_HEALTH_CARD_PARAMS.get(field, {})
            extracted[field] = {
                "value": value,
                "unit": spec.get("unit", ""),
                "source": "Extracted from uploaded soil report",
                "status": "DOCUMENT_EXTRACTED",
                "confidence": "low",
            }

    if not extracted:
        return {
            "success": False,
            "extracted": {},
            "message": "No recognizable soil test fields were found in this document. "
                       "Please enter your soil test values manually.",
            "requires_confirmation": False,
        }

    return {
        "success": True,
        "extracted": extracted,
        "message": "Values were extracted from your document. Please review and confirm or "
                   "correct each one before it is used - extraction is not automatically trusted.",
        "requires_confirmation": True,
    }
