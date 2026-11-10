"""
Unit tests for src/database.py using offline mocks
"""

import unittest
from unittest.mock import MagicMock
from src.database import (
    initialize_firebase,
    save_post,
    save_posts_batch,
    get_existing_hashes,
    set_firestore_client,
)


class MockDocumentRef:
    def __init__(self, doc_id: str, store: dict):
        self.doc_id = doc_id
        self.store = store

    def set(self, data: dict):
        self.store[self.doc_id] = data

    def get(self):
        doc = MagicMock()
        if self.doc_id in self.store:
            doc.exists = True
            doc.to_dict.return_value = self.store[self.doc_id]
        else:
            doc.exists = False
        return doc


class MockBatch:
    def __init__(self, store: dict):
        self.store = store
        self.pending = []

    def set(self, doc_ref, data):
        self.pending.append((doc_ref, data))

    def commit(self):
        for doc_ref, data in self.pending:
            doc_ref.set(data)
        self.pending.clear()


class MockCollection:
    def __init__(self):
        self.documents = {}

    def document(self, doc_id: str):
        return MockDocumentRef(doc_id, self.documents)

    def where(self, field, op, value):
        return self

    def limit(self, n):
        return self

    def stream(self):
        docs = []
        for doc_id, data in self.documents.items():
            doc = MagicMock()
            doc.to_dict.return_value = data
            docs.append(doc)
        return docs


class MockFirestoreClient:
    def __init__(self):
        self.collections = {}

    def collection(self, name: str):
        if name not in self.collections:
            self.collections[name] = MockCollection()
        return self.collections[name]

    def batch(self):
        return MockBatch(self.collections.setdefault("posts", MockCollection()).documents)


class TestDatabase(unittest.TestCase):
    def tearDown(self):
        set_firestore_client(None)

    def test_initialize_firebase_missing_key(self):
        result = initialize_firebase("/nonexistent/firebase-key.json")
        self.assertFalse(result)

    def test_save_post_uninitialized_client(self):
        set_firestore_client(None)
        res = save_post({"post_id": "test_1", "text": "sample"})
        self.assertIsNone(res)

    def test_save_post_missing_id(self):
        mock_client = MockFirestoreClient()
        set_firestore_client(mock_client)
        res = save_post({"text": "no id"})
        self.assertIsNone(res)

    def test_save_post_success(self):
        mock_client = MockFirestoreClient()
        set_firestore_client(mock_client)
        
        post_data = {
            "post_id": "qcu_101",
            "title": "Advisory",
            "text": "Classes resumed.",
            "content_hash": "hash123",
        }
        res = save_post(post_data, collection="posts")
        self.assertEqual(res, "qcu_101")
        
        saved = mock_client.collection("posts").documents.get("qcu_101")
        self.assertIsNotNone(saved)
        self.assertEqual(saved["title"], "Advisory")
        self.assertIn("updated_at", saved)

    def test_save_posts_batch_with_deduplication(self):
        mock_client = MockFirestoreClient()
        set_firestore_client(mock_client)

        posts = [
            {"post_id": "p1", "text": "Post 1", "content_hash": "hash_1"},
            {"post_id": "p2", "text": "Post 2", "content_hash": "hash_2"},
            {"post_id": "p1", "text": "Post 1 duplicate id", "content_hash": "hash_diff"},
            {"post_id": "p3", "text": "Post 3 duplicate hash", "content_hash": "hash_1"},
            {"text": "Post with missing id", "content_hash": "hash_4"},
        ]

        result = save_posts_batch(posts, collection="posts")
        self.assertEqual(result["saved"], 2, "Only 2 unique posts should be saved")
        self.assertEqual(result["skipped"], 3, "3 duplicates/invalid should be skipped")
        self.assertEqual(result["errors"], 0)

        # Verify saved documents
        docs = mock_client.collection("posts").documents
        self.assertIn("p1", docs)
        self.assertIn("p2", docs)
        self.assertNotIn("p3", docs)

    def test_get_existing_hashes(self):
        mock_client = MockFirestoreClient()
        set_firestore_client(mock_client)

        mock_client.collection("posts").documents["p1"] = {"content_hash": "alpha"}
        mock_client.collection("posts").documents["p2"] = {"content_hash": "beta"}

        hashes = get_existing_hashes(collection="posts")
        self.assertIn("alpha", hashes)
        self.assertIn("beta", hashes)
        self.assertEqual(len(hashes), 2)


if __name__ == "__main__":
    unittest.main()
