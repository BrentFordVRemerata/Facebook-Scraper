"""
Configuration Loader and Path Resolver
======================================
Harmonizes settings, source configurations, credentials, environment variables,
and cookie paths across the application.
"""

import json
import os
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


def get_project_root() -> Path:
    """Return the repository root directory."""
    return Path(__file__).resolve().parent.parent


def load_env_file(dotenv_path: Optional[Path] = None, override: bool = False) -> bool:
    """
    Load environment variables from a .env file.
    
    Tries python-dotenv first if available; otherwise falls back to a clean
    key-value parser for lines formatted as KEY=VALUE or KEY="VALUE".
    
    Returns True if a .env file was located and processed, False otherwise.
    """
    path = dotenv_path or (get_project_root() / ".env")
    if not path.exists():
        return False

    # Attempt loading with python-dotenv
    try:
        from dotenv import load_dotenv
        load_dotenv(path, override=override)
        return True
    except ImportError:
        pass

    # Built-in fallback parser
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip()
                # Strip wrapping single or double quotes
                if len(v) >= 2 and ((v[0] == '"' and v[-1] == '"') or (v[0] == "'" and v[-1] == "'")):
                    v = v[1:-1]
                if k and (override or k not in os.environ):
                    os.environ[k] = v
        return True
    except Exception as e:
        logger.warning("Failed to parse .env file at %s: %s", path, e)
        return False


# Automatically load .env on module import if present
load_env_file()


def load_json_file(file_path: Path) -> Optional[Any]:
    """Safely read and parse a JSON file."""
    if not file_path.exists():
        return None
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.warning("Failed to parse JSON from %s: %s", file_path, e)
        return None


def load_settings(path: Optional[Path] = None) -> Dict[str, Any]:
    """Load settings from config/settings.json or custom path."""
    resolved_path = path or (get_project_root() / "config" / "settings.json")
    data = load_json_file(resolved_path)
    if isinstance(data, dict):
        return data
    return {}


def load_sources(path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """
    Load and validate sources from config/sources.json.
    
    Guarantees that each source has valid 'id', 'name', 'posts_to_fetch', and 'enabled'.
    """
    resolved_path = path or (get_project_root() / "config" / "sources.json")
    data = load_json_file(resolved_path)
    
    raw_sources: List[Any] = []
    if isinstance(data, dict):
        raw_sources = data.get("sources", [])
    elif isinstance(data, list):
        raw_sources = data
        
    validated_sources: List[Dict[str, Any]] = []
    for s in raw_sources:
        if not isinstance(s, dict):
            continue
        source_id = str(s.get("id", "")).strip()
        if not source_id:
            continue
            
        name = str(s.get("name", "")).strip() or source_id
        
        # Validate posts_to_fetch
        try:
            posts_to_fetch = int(s.get("posts_to_fetch", 5))
            if posts_to_fetch <= 0:
                posts_to_fetch = 5
        except (ValueError, TypeError):
            posts_to_fetch = 5
            
        enabled = bool(s.get("enabled", True))
        
        validated_sources.append({
            "id": source_id,
            "name": name,
            "url": str(s.get("url", f"https://www.facebook.com/{source_id}")),
            "type": str(s.get("type", "page")),
            "posts_to_fetch": posts_to_fetch,
            "enabled": enabled,
            "notes": str(s.get("notes", "")),
        })
        
    return validated_sources


def get_cookies_path() -> Optional[Path]:
    """
    Resolve cookies file path with consistent fallback order:
    1. FACEBOOK_COOKIES_PATH environment variable
    2. config/facebook_cookies.txt
    3. config/cookies.txt
    """
    env_path = os.environ.get("FACEBOOK_COOKIES_PATH")
    if env_path:
        p = Path(env_path)
        if not p.is_absolute():
            p = get_project_root() / p
        if p.exists():
            return p
            
    root = get_project_root()
    primary = root / "config" / "facebook_cookies.txt"
    if primary.exists():
        return primary
        
    fallback = root / "config" / "cookies.txt"
    if fallback.exists():
        return fallback
        
    return None


def get_firebase_key_path() -> Optional[Path]:
    """
    Resolve Firebase service account key path with fallback order:
    1. FIREBASE_KEY_PATH environment variable
    2. config/firebase-key.json
    3. config/firebase_config.json
    """
    env_path = os.environ.get("FIREBASE_KEY_PATH")
    if env_path:
        p = Path(env_path)
        if not p.is_absolute():
            p = get_project_root() / p
        return p
        
    root = get_project_root()
    primary = root / "config" / "firebase-key.json"
    if primary.exists():
        return primary
        
    fallback = root / "config" / "firebase_config.json"
    if fallback.exists():
        return fallback
        
    return primary


def get_firestore_collection() -> str:
    """
    Determine Firestore collection name:
    1. FIRESTORE_COLLECTION environment variable
    2. config/settings.json -> firebase.collection_announcements
    3. Defaults to 'posts'
    """
    env_col = os.environ.get("FIRESTORE_COLLECTION")
    if env_col:
        return env_col.strip()
        
    settings = load_settings()
    configured_col = settings.get("firebase", {}).get("collection_announcements")
    if configured_col and isinstance(configured_col, str):
        return configured_col.strip()
        
    return "posts"


def get_fixture_path(filename: Optional[str] = None) -> Path:
    """Return path to default offline fixture file."""
    name = filename or "sample_page_text.txt"
    return get_project_root() / "tests" / "fixtures" / name
