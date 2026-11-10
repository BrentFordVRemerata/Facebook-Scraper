"""
QCU Facebook Scraper - Main Entry Point
=======================================
Reads sources from config/sources.json, scrapes announcement posts,
and persists results to Firebase Firestore.
"""

import sys
import argparse
import logging
from datetime import datetime
from typing import List, Dict, Any

from src.config import load_sources, load_settings
from src.database import initialize_firebase, save_posts_batch

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("main")


def run_pipeline(
    sources: List[Dict[str, Any]],
    use_playwright: bool = False,
    headless: bool = True,
    dry_run: bool = False,
    override_max_posts: int = None,
    save_debug: bool = False
) -> int:
    """Execute scraping pipeline across enabled sources."""
    print()
    print("=" * 60)
    print("QCU FACEBOOK ANNOUNCEMENT SCRAPER")
    print("=" * 60)
    print(f"Backend:     {'Playwright' if use_playwright else 'Selenium'}")
    print(f"Headless:    {headless}")
    print(f"Dry Run:     {dry_run}")
    print(f"Sources:     {len(sources)}")
    print("=" * 60)
    print()

    # Load appropriate scraper module
    if use_playwright:
        from src.scraper_playwright import scrape_page, PLAYWRIGHT_AVAILABLE
        if not PLAYWRIGHT_AVAILABLE:
            print("❌ Playwright is not installed.")
            print("   Install: pip install playwright && playwright install chromium")
            return 1
    else:
        from src.scraper import scrape_page, SELENIUM_AVAILABLE
        if not SELENIUM_AVAILABLE:
            print("❌ Selenium is not installed.")
            print("   Install: pip install selenium webdriver-manager")
            return 1

    # Connect to Firebase if not dry run
    use_firebase = False
    if not dry_run:
        print("🔥 Connecting to Firebase Firestore...")
        if initialize_firebase():
            print("✅ Firebase connected successfully.")
            use_firebase = True
        else:
            print("⚠️  Firebase key missing or invalid. Running in local dry-run mode (no save).")
            use_firebase = False
    else:
        print("ℹ️  Dry-run mode enabled: skipping Firebase connection.")

    all_posts: List[Dict[str, Any]] = []
    failed_sources: List[str] = []

    for i, source in enumerate(sources, 1):
        page_id = source.get('id')
        page_name = source.get('name', page_id)
        max_posts = override_max_posts if override_max_posts is not None else source.get('posts_to_fetch', 5)

        print(f"\n[{i}/{len(sources)}] Source: {page_name} (@{page_id}) | Limit: {max_posts}")
        print("-" * 50)

        try:
            # FIX: Properly pass max_posts, page_name, headless, and save_debug
            posts, stats = scrape_page(
                page_id=page_id,
                page_name=page_name,
                max_posts=max_posts,
                headless=headless,
                show_stats=True,
                save_debug=save_debug
            )

            if stats and stats.success:
                all_posts.extend(posts)
                print(f"   ✨ Extracted {len(posts)} posts in {stats.time_total:.1f}s")
            else:
                err_msg = stats.error if stats else "Unknown error"
                print(f"   ⚠️  Failed to scrape @{page_id}: {err_msg}")
                failed_sources.append(page_id)

        except Exception as e:
            logger.exception("Unexpected error processing source %s: %s", page_id, e)
            print(f"   ❌ Error: {e}")
            failed_sources.append(page_id)

    # Save to Firestore
    if all_posts and use_firebase:
        print("\n💾 Persisting collected posts to Firestore...")
        result = save_posts_batch(all_posts)
        print(f"   ✅ Saved: {result['saved']} | Skipped: {result['skipped']} | Errors: {result['errors']}")
    elif all_posts and not use_firebase:
        print(f"\nℹ️  Collected {len(all_posts)} posts (unsaved due to dry-run or unconfigured Firebase).")

    # Final summary
    print()
    print("=" * 60)
    print("EXECUTION SUMMARY")
    print("=" * 60)
    print(f"Total posts collected: {len(all_posts)}")
    print(f"Failed sources:        {len(failed_sources)} ({', '.join(failed_sources) if failed_sources else 'None'})")
    print(f"Completed at:          {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    return 0 if not failed_sources else 2


def main() -> int:
    parser = argparse.ArgumentParser(description="QCU Facebook Scraper Runner")
    parser.add_argument("--source", "-s", help="Scrape a single page ID instead of all configured sources")
    parser.add_argument("--name", "-n", default="", help="Display name for single source")
    parser.add_argument("--playwright", action="store_true", help="Use Playwright backend instead of Selenium")
    parser.add_argument("--no-headless", action="store_false", dest="headless", default=True, help="Run browser in visible mode")
    parser.add_argument("--max-posts", "-m", type=int, default=None, help="Override posts_to_fetch limit")
    parser.add_argument("--dry-run", action="store_true", help="Scrape without persisting to Firebase")
    parser.add_argument("--save-debug", action="store_true", help="Save raw HTML and text dumps to data/ (may include session data)")

    args = parser.parse_args()

    if args.source:
        sources = [{
            "id": args.source,
            "name": args.name or args.source,
            "posts_to_fetch": args.max_posts or 5,
            "enabled": True
        }]
    else:
        all_sources = load_sources()
        sources = [s for s in all_sources if s.get('enabled', True)]
        if not sources:
            print("❌ No enabled sources found in config/sources.json")
            return 1

    return run_pipeline(
        sources=sources,
        use_playwright=args.playwright,
        headless=args.headless,
        dry_run=args.dry_run,
        override_max_posts=args.max_posts,
        save_debug=args.save_debug
    )


if __name__ == "__main__":
    sys.exit(main())
