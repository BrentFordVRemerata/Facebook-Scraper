"""
Firebase Firestore Database Module
==================================
Manages initialization, post persistence, batch writes, and duplicate detection
for the QCU announcement aggregator.
"""

import os
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, List, Set, Tuple

from src.config import get_firebase_key_path, get_firestore_collection, get_project_root

logger = logging.getLogger(__name__)

# Firebase Admin SDK
try:
    import firebase_admin
    from firebase_admin import credentials, firestore
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False
    logger.warning("firebase-admin not installed. Run: pip install firebase-admin")


_firebase_app = None
_firestore_client = None


def initialize_firebase(key_path: Optional[str] = None) -> bool:
    """
    Initialize Firebase Admin connection.
    
    Safe for repeated calls (idempotent).
    """
    global _firebase_app, _firestore_client
    
    if not FIREBASE_AVAILABLE:
        logger.warning("firebase-admin is not installed")
        return False
        
    if _firebase_app is not None and _firestore_client is not None:
        return True
        
    resolved_key: Optional[Path] = None
    if key_path:
        p = Path(key_path)
        resolved_key = p if p.is_absolute() else (get_project_root() / p)
    else:
        resolved_key = get_firebase_key_path()
        
    if not resolved_key or not resolved_key.exists():
        logger.warning("Firebase service account key not found at: %s", resolved_key)
        return False
        
    try:
        cred = credentials.Certificate(str(resolved_key))
        _firebase_app = firebase_admin.initialize_app(cred)
        _firestore_client = firestore.client()
        logger.info("Firebase Firestore initialized successfully")
        return True
    except Exception as e:
        logger.error("Failed to initialize Firebase: %s", e)
        return False


def get_firestore_client():
    """Return active Firestore client instance, or None if not initialized."""
    return _firestore_client


def set_firestore_client(client):
    """Set active Firestore client (useful for unit tests with mocks)."""
    global _firestore_client
    _firestore_client = client


def save_post(post_data: Dict[str, Any], collection: Optional[str] = None) -> Optional[str]:
    """
    Save or update a single post document in Firestore.
    """
    client = get_firestore_client()
    if client is None:
        logger.warning("Firestore client not initialized. Cannot save post.")
        return None
        
    target_collection = collection or get_firestore_collection()
    doc_id = post_data.get('post_id')
    if not doc_id:
        logger.warning("Post record is missing 'post_id'. Skipping.")
        return None
        
    try:
        record = dict(post_data)
        record['updated_at'] = datetime.now(timezone.utc).isoformat()
        client.collection(target_collection).document(doc_id).set(record)
        return doc_id
    except Exception as e:
        logger.error("Error saving post %s: %s", doc_id, e)
        return None


def get_post(post_id: str, collection: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Retrieve a single post from Firestore by document ID."""
    client = get_firestore_client()
    if client is None:
        return None
        
    target_collection = collection or get_firestore_collection()
    try:
        doc = client.collection(target_collection).document(post_id).get()
        if doc.exists:
            return doc.to_dict()
        return None
    except Exception as e:
        logger.error("Error retrieving post %s: %s", post_id, e)
        return None


def post_exists(post_id: str, collection: Optional[str] = None) -> bool:
    """Check whether a post document exists by ID."""
    client = get_firestore_client()
    if client is None:
        return False
        
    target_collection = collection or get_firestore_collection()
    try:
        doc = client.collection(target_collection).document(post_id).get()
        return getattr(doc, 'exists', False)
    except Exception:
        return False


def get_post_document(post_id: str, collection: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Retrieve post document data by ID if it exists, else None."""
    client = get_firestore_client()
    if client is None:
        return None
        
    target_collection = collection or get_firestore_collection()
    try:
        doc = client.collection(target_collection).document(post_id).get()
        if getattr(doc, 'exists', False):
            return doc.to_dict() if hasattr(doc, 'to_dict') else {}
        return None
    except Exception:
        return None


def is_content_identical(stored_data: Dict[str, Any], incoming_data: Dict[str, Any]) -> bool:
    """
    Check if the stored Firestore document has identical content to the incoming post.
    Compares content_hash, raw_text, or normalized text.
    """
    # 1. Direct content_hash comparison
    stored_hash = stored_data.get('content_hash')
    incoming_hash = incoming_data.get('content_hash')
    if stored_hash and incoming_hash and stored_hash == incoming_hash:
        return True

    # 2. Compare text / raw_text
    stored_text = stored_data.get('raw_text') or stored_data.get('text') or ''
    incoming_text = incoming_data.get('raw_text') or incoming_data.get('text') or ''
    if stored_text and incoming_text:
        if stored_text.strip() == incoming_text.strip():
            return True
        try:
            from src.parser import generate_content_hash
            if generate_content_hash(stored_text) == generate_content_hash(incoming_text):
                return True
        except ImportError:
            pass

    return False


def check_existing_post(
    post_id: str,
    legacy_post_id: Optional[str] = None,
    post_data: Optional[Dict[str, Any]] = None,
    collection: Optional[str] = None
) -> bool:
    """
    Check if a post already exists under its current SHA-256 ID or historical MD5 ID.
    If matching a legacy ID, verifies stored content before treating as duplicate.
    """
    if post_exists(post_id, collection=collection):
        return True
    if legacy_post_id:
        legacy_data = get_post_document(legacy_post_id, collection=collection)
        if legacy_data is not None:
            if post_data is not None:
                return is_content_identical(legacy_data, post_data)
            return True
    return False


def get_existing_hashes(
    source_id: Optional[str] = None,
    limit: int = 500,
    collection: Optional[str] = None
) -> Set[str]:
    """
    Retrieve known content_hash values from Firestore for duplicate detection.
    
    NOTE ON LIMIT: Firestore bills per document read (free tier: 50,000/day).
    The query limit avoids downloading massive collections on every scrape run while
    inspecting the most recent documents.
    """
    client = get_firestore_client()
    if client is None:
        return set()
        
    target_collection = collection or get_firestore_collection()
    try:
        query = client.collection(target_collection)
        if source_id:
            query = query.where("source_id", "==", source_id)
        if limit and limit > 0:
            query = query.limit(limit)
        
        docs = query.stream()
        hashes: Set[str] = set()
        for doc in docs:
            data = doc.to_dict() if hasattr(doc, 'to_dict') else {}
            h = data.get('content_hash')
            if h:
                hashes.add(h)
        return hashes
    except Exception as e:
        logger.warning("Error fetching existing hashes from Firestore: %s", e)
        return set()


def save_posts_batch(
    posts: List[Any],
    collection: Optional[str] = None,
    cross_source_dedup: bool = False
) -> Dict[str, int]:
    """
    Batch save multiple post records into Firestore with deduplication and migration support.
    
    Args:
        posts: List of post dictionaries or ScrapedPost instances
        collection: Target Firestore collection (defaults to FIRESTORE_COLLECTION or 'posts')
        cross_source_dedup: If True, duplicate content across different sources is discarded.
                            If False (default), each source retains its announcements.
    
    Returns:
        dict: {"saved": int, "skipped": int, "errors": int}
    """
    results = {"saved": 0, "skipped": 0, "errors": 0}
    if not posts:
        return results

    client = get_firestore_client()
    if client is None:
        logger.warning("Firestore client not initialized. Cannot perform batch save.")
        results["skipped"] = len(posts)
        return results
        
    target_collection = collection or get_firestore_collection()
    
    # Avoid unnecessary Firestore reads: only fetch existing hashes when cross-source dedup is active
    existing_hashes: Set[str] = set()
    if cross_source_dedup:
        existing_hashes = get_existing_hashes(collection=target_collection)
    
    seen_in_batch: Set[str] = set()
    seen_source_hashes: Set[Tuple[str, str]] = set()
    
    try:
        batch = client.batch()
        batch_count = 0
        
        for item in posts:
            post_data = item.to_dict() if hasattr(item, 'to_dict') else dict(item)
            
            post_id = post_data.get('post_id')
            legacy_post_id = post_data.get('legacy_post_id')
            source_id = str(post_data.get('source_id', ''))
            content_hash = post_data.get('content_hash')
            
            if not post_id:
                results["skipped"] += 1
                continue
                
            # Deduplicate against current in-flight batch
            if post_id in seen_in_batch:
                results["skipped"] += 1
                continue
                
            if content_hash:
                if cross_source_dedup:
                    if content_hash in existing_hashes:
                        results["skipped"] += 1
                        continue
                else:
                    source_key = (source_id, content_hash)
                    if source_key in seen_source_hashes:
                        results["skipped"] += 1
                        continue
                    seen_source_hashes.add(source_key)

            # Idempotent save check: verify if document already exists under its own SHA-256 post_id
            doc_ref = client.collection(target_collection).document(post_id)
            doc_snap = doc_ref.get()
            if getattr(doc_snap, 'exists', False):
                logger.info("Skipping post %s; already exists in Firestore", post_id)
                results["skipped"] += 1
                continue

            # Migration check: verify if document already exists under legacy post_id with identical content
            if legacy_post_id:
                legacy_doc_ref = client.collection(target_collection).document(legacy_post_id)
                legacy_snap = legacy_doc_ref.get()
                if getattr(legacy_snap, 'exists', False):
                    legacy_data = legacy_snap.to_dict() if hasattr(legacy_snap, 'to_dict') else {}
                    if is_content_identical(legacy_data, post_data):
                        logger.info(
                            "Skipping post %s; identical content already exists under legacy ID %s",
                            post_id, legacy_post_id
                        )
                        results["skipped"] += 1
                        continue
                    else:
                        logger.info(
                            "Legacy ID %s exists in Firestore, but stored content differs from post %s; saving new post",
                            legacy_post_id, post_id
                        )
                
            seen_in_batch.add(post_id)
            if content_hash and cross_source_dedup:
                existing_hashes.add(content_hash)
                
            post_data['updated_at'] = datetime.now(timezone.utc).isoformat()
            batch.set(doc_ref, post_data)
            batch_count += 1
            
            # Firestore limit: 500 operations per batch
            if batch_count >= 500:
                try:
                    batch.commit()
                    results["saved"] += batch_count
                except Exception as commit_err:
                    logger.error("Firestore batch commit failed: %s", commit_err)
                    results["errors"] += batch_count
                batch = client.batch()
                batch_count = 0
                
        if batch_count > 0:
            try:
                batch.commit()
                results["saved"] += batch_count
            except Exception as commit_err:
                logger.error("Firestore batch commit failed: %s", commit_err)
                results["errors"] += batch_count
            
        logger.info("Batch save complete: %d saved, %d skipped, %d errors",
                    results["saved"], results["skipped"], results["errors"])
    except Exception as e:
        logger.error("Unexpected error during Firestore batch operations: %s", e)
        results["errors"] += (len(posts) - results["saved"] - results["skipped"])
        
    return results


if __name__ == "__main__":
    import sys
    print("=" * 60)
    print("FIREBASE DATABASE - DIAGNOSTIC CHECK")
    print("=" * 60)
    
    if not initialize_firebase():
        print("❌ Firebase initialization unsuccessful.")
        print(f"   Key path checked: {get_firebase_key_path()}")
        print("   To configure: Provide valid service account JSON at config/firebase-key.json")
        sys.exit(1)
        
    print("✅ Firebase initialized successfully!")
