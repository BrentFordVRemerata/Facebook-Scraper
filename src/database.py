"""
=============================================================================
FIREBASE DATABASE MODULE - WHERE YOUR DATA LIVES
=============================================================================

WHAT IS FIREBASE?
-----------------
Firebase is Google's Backend-as-a-Service (BaaS). Instead of setting up your
own server and database, Firebase provides:
- Firestore: NoSQL database (what we use for posts)
- Storage: File storage (for images later)
- Authentication: User login (for mobile app later)

WHY FIREBASE?
-------------
1. FREE TIER: 50,000 reads, 20,000 writes per day
2. REAL-TIME: Mobile app can get instant updates
3. SCALABLE: Google handles all the server stuff
4. EASY: No SQL queries, just save/read Python dictionaries

HOW DATA IS ORGANIZED:
----------------------
Firestore uses: Collections → Documents → Fields

    firestore/
    └── posts/                    ← Collection (like a table)
        ├── abc123/               ← Document (like a row)
        │   ├── post_id: "abc123"
        │   ├── title: "ENROLLMENT ADVISORY"
        │   ├── text: "Please be informed..."
        │   └── ...
        ├── def456/               ← Another document
        │   └── ...
        └── ...

WHERE OUTPUTS GO:
-----------------
When you save a post, it goes to:
    Firebase Console → Your Project → Firestore Database → posts collection

You can view it at: https://console.firebase.google.com/

=============================================================================
SETUP INSTRUCTIONS (DO THIS FIRST!)
=============================================================================

STEP 1: Create Firebase Project
-------------------------------
1. Go to https://console.firebase.google.com/
2. Click "Create a project" (or "Add project")
3. Enter project name: "qcu-unified" (or any name you like)
4. Disable Google Analytics (we don't need it)
5. Click "Create project"
6. Wait for it to finish, then click "Continue"

STEP 2: Enable Firestore Database
---------------------------------
1. In Firebase Console, click "Build" in the left sidebar
2. Click "Firestore Database"
3. Click "Create database"
4. Choose location: "asia-southeast1 (Singapore)" ← IMPORTANT for PHT users
5. Start in "test mode" for now (we'll secure it later)
6. Click "Enable"

STEP 3: Get Service Account Key (for Python access)
---------------------------------------------------
1. Click the gear icon (⚙️) next to "Project Overview"
2. Click "Project settings"
3. Go to "Service accounts" tab
4. Click "Generate new private key"
5. Click "Generate key" - a JSON file will download
6. RENAME the file to: firebase-key.json
7. MOVE it to: c:\\Users\\Marc\\Desktop\\QCU Unified\\Facebook-Scraper\\config\\firebase-key.json
8. IMPORTANT: This file is SECRET! Never commit to git (it's in .gitignore)

STEP 4: Update .env file
------------------------
1. Copy .env.example to .env
2. Set: FIREBASE_KEY_PATH=config/firebase-key.json

=============================================================================
"""

import os
from datetime import datetime, timezone
from typing import Optional
from pathlib import Path

# Firebase Admin SDK - the official Python library for Firebase
try:
    import firebase_admin
    from firebase_admin import credentials, firestore
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False
    print("⚠️  firebase-admin not installed. Run: pip install firebase-admin")


# Global variable to track if Firebase is initialized
_firebase_app = None
_firestore_client = None


def initialize_firebase(key_path: str = None) -> bool:
    """
    Initialize Firebase connection.
    
    MUST BE CALLED ONCE before using any other Firebase functions.
    
    PARAMETERS:
    -----------
    key_path : str
        Path to your firebase-key.json file
        If not provided, looks for FIREBASE_KEY_PATH environment variable
        
    RETURNS:
    --------
    bool : True if successful, False if failed
    
    EXAMPLE:
    --------
        if initialize_firebase("config/firebase-key.json"):
            print("Connected to Firebase!")
            save_post(my_post)
        else:
            print("Could not connect")
    """
    global _firebase_app, _firestore_client
    
    if not FIREBASE_AVAILABLE:
        print("❌ firebase-admin not installed")
        return False
    
    # Already initialized? Return existing client
    if _firebase_app is not None:
        return True
    
    # Find the key file
    if key_path is None:
        key_path = os.environ.get('FIREBASE_KEY_PATH', 'config/firebase-key.json')
    
    # Convert to absolute path if relative
    if not os.path.isabs(key_path):
        # Get the project root (parent of src folder)
        project_root = Path(__file__).parent.parent
        key_path = project_root / key_path
    
    key_path = Path(key_path)
    
    # Check if file exists
    if not key_path.exists():
        print(f"❌ Firebase key not found: {key_path}")
        print("\n📋 To fix this:")
        print("   1. Go to Firebase Console → Project Settings → Service Accounts")
        print("   2. Click 'Generate new private key'")
        print("   3. Save the file as: config/firebase-key.json")
        return False
    
    try:
        # Load credentials from the JSON key file
        cred = credentials.Certificate(str(key_path))
        
        # Initialize the Firebase app
        _firebase_app = firebase_admin.initialize_app(cred)
        
        # Get Firestore client
        _firestore_client = firestore.client()
        
        print("✅ Firebase initialized successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Firebase initialization failed: {e}")
        return False


def get_firestore_client():
    """
    Get the Firestore client instance.
    
    Returns None if Firebase is not initialized.
    """
    return _firestore_client


def save_post(post_data: dict, collection: str = "posts") -> Optional[str]:
    """
    Save a post to Firestore.
    
    PARAMETERS:
    -----------
    post_data : dict
        The post data to save (use ScrapedPost.to_dict())
        
    collection : str
        Which collection to save to (default: "posts")
        
    RETURNS:
    --------
    str : The document ID if successful, None if failed
    
    EXAMPLE:
    --------
        from src.scraper import scrape_page
        
        posts = scrape_page("qcu1994", "QCU Main")
        for post in posts:
            doc_id = save_post(post.to_dict())
            print(f"Saved: {doc_id}")
    
    HOW IT WORKS:
    -------------
    1. We use post_id as the document ID (so same post = same document)
    2. If document exists, it gets overwritten (updated)
    3. If new, it gets created
    4. Returns the document ID for reference
    """
    if _firestore_client is None:
        print("❌ Firebase not initialized. Call initialize_firebase() first.")
        return None
    
    try:
        # Get the collection reference
        collection_ref = _firestore_client.collection(collection)
        
        # Use post_id as document ID (ensures no duplicates)
        doc_id = post_data.get('post_id', '')
        if not doc_id:
            print("⚠️  Post has no post_id, skipping")
            return None
        
        # Add metadata
        post_data['updated_at'] = datetime.now(timezone.utc).isoformat()
        
        # Save to Firestore
        # set() creates or overwrites the document
        collection_ref.document(doc_id).set(post_data)
        
        return doc_id
        
    except Exception as e:
        print(f"❌ Error saving post: {e}")
        return None


def get_post(post_id: str, collection: str = "posts") -> Optional[dict]:
    """
    Get a single post from Firestore by ID.
    
    RETURNS:
    --------
    dict : The post data if found, None if not found
    """
    if _firestore_client is None:
        print("❌ Firebase not initialized")
        return None
    
    try:
        doc = _firestore_client.collection(collection).document(post_id).get()
        if doc.exists:
            return doc.to_dict()
        return None
    except Exception as e:
        print(f"❌ Error getting post: {e}")
        return None


def post_exists(post_id: str, collection: str = "posts") -> bool:
    """
    Check if a post already exists in Firestore.
    
    Useful for skipping duplicates without downloading the full document.
    """
    if _firestore_client is None:
        return False
    
    try:
        doc = _firestore_client.collection(collection).document(post_id).get()
        return doc.exists
    except:
        return False


def get_existing_hashes(source_id: str = None, limit: int = 100) -> set:
    """
    Get content hashes of existing posts.
    
    Used for duplicate detection - if a post's hash matches an existing one,
    we know the content hasn't changed and can skip it.
    
    PARAMETERS:
    -----------
    source_id : str
        Optional - only get hashes from this source
        
    limit : int
        Maximum number of hashes to retrieve
        
    RETURNS:
    --------
    set : Set of content_hash strings
    """
    if _firestore_client is None:
        return set()
    
    try:
        query = _firestore_client.collection("posts")
        
        if source_id:
            query = query.where("source_id", "==", source_id)
        
        query = query.limit(limit)
        docs = query.stream()
        
        hashes = set()
        for doc in docs:
            data = doc.to_dict()
            if 'content_hash' in data:
                hashes.add(data['content_hash'])
        
        return hashes
        
    except Exception as e:
        print(f"⚠️  Error getting hashes: {e}")
        return set()


def save_posts_batch(posts: list, collection: str = "posts") -> dict:
    """
    Save multiple posts efficiently using batch write.
    
    Firestore allows up to 500 operations per batch, making this
    much faster than saving one by one.
    
    RETURNS:
    --------
    dict with keys:
        - saved: int (number successfully saved)
        - skipped: int (number skipped - duplicates or no ID)
        - errors: int (number that failed)
    """
    if _firestore_client is None:
        print("❌ Firebase not initialized")
        return {"saved": 0, "skipped": 0, "errors": 0}
    
    results = {"saved": 0, "skipped": 0, "errors": 0}
    
    # Get existing hashes for duplicate detection
    existing_hashes = get_existing_hashes()
    
    try:
        batch = _firestore_client.batch()
        batch_count = 0
        
        for post in posts:
            # Convert ScrapedPost to dict if needed
            if hasattr(post, 'to_dict'):
                post_data = post.to_dict()
            else:
                post_data = post
            
            post_id = post_data.get('post_id')
            content_hash = post_data.get('content_hash')
            
            # Skip if no ID
            if not post_id:
                results["skipped"] += 1
                continue
            
            # Skip if same content exists
            if content_hash and content_hash in existing_hashes:
                results["skipped"] += 1
                continue
            
            # Add to batch
            doc_ref = _firestore_client.collection(collection).document(post_id)
            post_data['updated_at'] = datetime.now(timezone.utc).isoformat()
            batch.set(doc_ref, post_data)
            batch_count += 1
            
            # Firestore limit: 500 per batch
            if batch_count >= 500:
                batch.commit()
                results["saved"] += batch_count
                batch = _firestore_client.batch()
                batch_count = 0
        
        # Commit remaining
        if batch_count > 0:
            batch.commit()
            results["saved"] += batch_count
        
        print(f"✅ Batch save complete: {results['saved']} saved, {results['skipped']} skipped")
        
    except Exception as e:
        print(f"❌ Batch save error: {e}")
        results["errors"] += 1
    
    return results


# =============================================================================
# QUICK TEST
# =============================================================================

if __name__ == "__main__":
    """
    HOW TO TEST FIREBASE:
    ---------------------
    1. Complete the setup instructions at the top of this file
    2. Run: python src/database.py
    
    This will:
    - Connect to Firebase
    - Save a test post
    - Read it back
    - Delete the test post
    """
    
    print("=" * 60)
    print("FIREBASE DATABASE - TEST MODE")
    print("=" * 60)
    print()
    
    # Try to initialize
    if not initialize_firebase():
        print("\n⚠️  Firebase setup incomplete. Follow the instructions at the top of this file.")
        exit(1)
    
    # Create a test post
    test_post = {
        "post_id": "test_123",
        "source_id": "test",
        "source_name": "Test Source",
        "title": "Test Post",
        "text": "This is a test post to verify Firebase connection.",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "content_hash": "test_hash_abc",
    }
    
    print("\n📝 Saving test post...")
    doc_id = save_post(test_post)
    
    if doc_id:
        print(f"✅ Saved with ID: {doc_id}")
        
        print("\n📖 Reading it back...")
        retrieved = get_post(doc_id)
        if retrieved:
            print(f"✅ Retrieved: {retrieved['title']}")
        
        # Clean up - delete test post
        print("\n🗑️  Cleaning up test post...")
        _firestore_client.collection("posts").document(doc_id).delete()
        print("✅ Test post deleted")
        
        print("\n✅ Firebase is working correctly!")
    else:
        print("❌ Failed to save test post")
