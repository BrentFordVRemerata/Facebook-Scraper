"""
QCU Facebook Scraper - Main Entry Point
=======================================

Run: python main.py

What it does:
1. Reads config/sources.json for pages to scrape
2. Scrapes each page using Selenium
3. Saves posts to Firebase
"""

import json
from pathlib import Path
from datetime import datetime

from src.scraper import scrape_page, SELENIUM_AVAILABLE
from src.database import initialize_firebase, save_posts_batch


def load_sources() -> list:
    """Load Facebook pages from config."""
    path = Path("config/sources.json")
    if not path.exists():
        return []
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f).get('sources', [])


def main():
    """Main function."""
    
    print()
    print("=" * 50)
    print("QCU FACEBOOK SCRAPER")
    print("=" * 50)
    print()
    
    # Check requirements
    if not SELENIUM_AVAILABLE:
        print("❌ Selenium not installed!")
        print("   Run: pip install selenium webdriver-manager")
        return
    
    # Initialize Firebase
    print("🔥 Connecting to Firebase...")
    if not initialize_firebase():
        print("❌ Firebase not configured. Continuing without saving.")
        use_firebase = False
    else:
        print("✅ Firebase connected!")
        use_firebase = True
    
    # Load sources
    sources = load_sources()
    enabled = [s for s in sources if s.get('enabled', True)]
    
    if not enabled:
        print("❌ No sources found in config/sources.json")
        return
    
    print(f"📋 Found {len(enabled)} source(s)")
    print()
    
    # Scrape each source
    all_posts = []
    
    for i, source in enumerate(enabled, 1):
        page_id = source.get('id')
        page_name = source.get('name', page_id)
        max_posts = source.get('posts_to_fetch', 5)
        
        print(f"[{i}/{len(enabled)}] {page_name}")
        print("-" * 40)
        
        try:
            posts, stats = scrape_page(
                page_id=page_id,
                headless=True
            )
            
            if stats:
                print(f"   ⏱️  {stats.time_total:.1f}s | 📝 {len(posts)} posts")
            
            all_posts.extend(posts)
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        print()
    
    # Save to Firebase
    if all_posts and use_firebase:
        print("💾 Saving to Firebase...")
        result = save_posts_batch(all_posts)
        print(f"   Saved: {result['saved']}, Skipped: {result['skipped']}")
    
    # Summary
    print()
    print("=" * 50)
    print("COMPLETE")
    print("=" * 50)
    print(f"Total posts: {len(all_posts)}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
