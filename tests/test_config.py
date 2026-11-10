"""
Unit tests for src/config.py
"""

import os
import json
import tempfile
import unittest
from pathlib import Path
from src.config import (
    load_sources,
    load_settings,
    get_cookies_path,
    get_firebase_key_path,
    get_firestore_collection,
    get_project_root,
)


class TestConfig(unittest.TestCase):
    def test_load_sources_from_repository(self):
        """Verify repository config/sources.json loads and contains valid sources."""
        sources = load_sources()
        self.assertGreater(len(sources), 0)
        for s in sources:
            self.assertIn("id", s)
            self.assertIn("name", s)
            self.assertIn("posts_to_fetch", s)
            self.assertIsInstance(s["posts_to_fetch"], int)
            self.assertGreaterEqual(s["posts_to_fetch"], 1)

    def test_load_sources_handles_missing_file(self):
        missing = Path("/nonexistent/sources.json")
        sources = load_sources(missing)
        self.assertEqual(sources, [])

    def test_load_sources_sanitization(self):
        with tempfile.NamedTemporaryFile("w+", suffix=".json", delete=False) as tf:
            data = {
                "sources": [
                    {"id": "valid_1", "name": "Valid 1", "posts_to_fetch": 8},
                    {"id": "valid_2", "posts_to_fetch": -1},  # Invalid count, should fallback
                    {"name": "missing_id"},                   # Missing ID, should skip
                    "invalid_entry",                          # Non-dict, should skip
                ]
            }
            json.dump(data, tf)
            tf_path = Path(tf.name)

        try:
            sources = load_sources(tf_path)
            self.assertEqual(len(sources), 2)
            self.assertEqual(sources[0]["id"], "valid_1")
            self.assertEqual(sources[0]["posts_to_fetch"], 8)
            self.assertEqual(sources[1]["id"], "valid_2")
            self.assertEqual(sources[1]["posts_to_fetch"], 5)  # Default fallback
            self.assertEqual(sources[1]["name"], "valid_2")    # Name defaults to ID
        finally:
            if tf_path.exists():
                tf_path.unlink()

    def test_load_settings(self):
        settings = load_settings()
        self.assertIsInstance(settings, dict)
        self.assertIn("firebase", settings)

    def test_cookies_path_env_override(self):
        with tempfile.NamedTemporaryFile("w+", delete=False) as tf:
            tf.write("# Test cookie file\n")
            tf_path = Path(tf.name)

        orig_env = os.environ.get("FACEBOOK_COOKIES_PATH")
        try:
            os.environ["FACEBOOK_COOKIES_PATH"] = str(tf_path)
            resolved = get_cookies_path()
            self.assertEqual(resolved, tf_path)
        finally:
            if orig_env is not None:
                os.environ["FACEBOOK_COOKIES_PATH"] = orig_env
            else:
                os.environ.pop("FACEBOOK_COOKIES_PATH", None)
            if tf_path.exists():
                tf_path.unlink()

    def test_firebase_key_path_env_override(self):
        orig_env = os.environ.get("FIREBASE_KEY_PATH")
        try:
            os.environ["FIREBASE_KEY_PATH"] = "custom/path/key.json"
            resolved = get_firebase_key_path()
            self.assertTrue(str(resolved).endswith("custom/path/key.json"))
        finally:
            if orig_env is not None:
                os.environ["FIREBASE_KEY_PATH"] = orig_env
            else:
                os.environ.pop("FIREBASE_KEY_PATH", None)

    def test_firestore_collection_resolution(self):
        orig_env = os.environ.get("FIRESTORE_COLLECTION")
        try:
            # Test default
            os.environ.pop("FIRESTORE_COLLECTION", None)
            col = get_firestore_collection()
            self.assertIn(col, ["posts", "announcements"])

            # Test env override
            os.environ["FIRESTORE_COLLECTION"] = "test_announcements"
            self.assertEqual(get_firestore_collection(), "test_announcements")
        finally:
            if orig_env is not None:
                os.environ["FIRESTORE_COLLECTION"] = orig_env
            else:
                os.environ.pop("FIRESTORE_COLLECTION", None)

    def test_load_env_file(self):
        with tempfile.NamedTemporaryFile("w+", delete=False) as tf:
            tf.write("# Test .env file\n")
            tf.write("CUSTOM_ENV_TEST_VAR=loaded_successfully\n")
            tf.write("QUOTED_VAR=\"value_with_quotes\"\n")
            tf.write("SPACED_VAR = spaced_value \n")
            tf_path = Path(tf.name)

        try:
            from src.config import load_env_file
            res = load_env_file(tf_path, override=True)
            self.assertTrue(res)
            self.assertEqual(os.environ.get("CUSTOM_ENV_TEST_VAR"), "loaded_successfully")
            self.assertEqual(os.environ.get("QUOTED_VAR"), "value_with_quotes")
            self.assertEqual(os.environ.get("SPACED_VAR"), "spaced_value")
        finally:
            os.environ.pop("CUSTOM_ENV_TEST_VAR", None)
            os.environ.pop("QUOTED_VAR", None)
            os.environ.pop("SPACED_VAR", None)
            if tf_path.exists():
                tf_path.unlink()

    def test_get_fixture_path(self):
        from src.config import get_fixture_path
        fixture = get_fixture_path()
        self.assertTrue(fixture.exists())
        self.assertIn("sample_page_text.txt", str(fixture))


if __name__ == "__main__":
    unittest.main()
