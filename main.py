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
from pathlib import Path
from typing import List, Dict, Any, Optional

from src.config import load_sources, load_settings, get_fixture_path
from src.database import initialize_firebase, save_posts_batch
from src.parser import parse_posts_from_text

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("main")


def run_offline_fixture_pipeline(
    sources: List[Dict[str, Any]],
    fixture_path: Optional[Path] = None,
    override_max_posts: Optional[int] = None
) -> Optional[List[Dict[str, Any]]]:
    """
    Execute pipeline in genuine offline mode using local text fixtures.
    Zero browser launch, zero network access, zero external credentials.
    Returns None if the fixture file is missing.
    """
    path = fixture_path or get_fixture_path()
    if not path.exists():
        logger.error("Fixture file not found at: %s", path)
        print(f"❌ Fixture file missing: {path}")
        return None

    print(f"📄 Loading offline fixture from: {path.name}")
    raw_text = path.read_text(encoding="utf-8")

    all_posts = []
    for i, source in enumerate(sources, 1):
        source_id = source.get('id', '')
        source_name = source.get('name', source_id)
        limit = override_max_posts if override_max_posts is not None else source.get('posts_to_fetch', 5)

        print(f"\n[{i}/{len(sources)}] Offline Parsing: {source_name} (@{source_id}) | Limit: {limit}")
        print("-" * 50)

        posts = parse_posts_from_text(
            raw_text=raw_text,
            source_id=source_id,
            source_name=source_name,
            max_posts=limit
        )

        for p in posts:
            print(f"   ✅ [Synthetic Sample] {p['title'][:60]}...")
        print(f"   ✨ Extracted {len(posts)} synthetic sample posts from offline fixture.")
        all_posts.extend(posts)

    return all_posts


def run_pipeline(
    sources: List[Dict[str, Any]],
    use_playwright: bool = False,
    headless: bool = True,
    dry_run: bool = False,
    offline: bool = False,
    fixture_path: Optional[Path] = None,
    override_max_posts: Optional[int] = None,
    save_debug: bool = False
) -> int:
    """Execute scraping pipeline across enabled sources."""
    print()
    print("=" * 60)
    print("QCU FACEBOOK ANNOUNCEMENT SCRAPER")
    print("=" * 60)
    if offline:
        print("Mode:        OFFLINE FIXTURE (No network/browser)")
        print("Dry Run:     True (Unconditionally offline: database writes disabled)")
    else:
        print("Mode:        LIVE SCRAPING")
        print(f"Backend:     {'Playwright' if use_playwright else 'Selenium'}")
        print(f"Headless:    {headless}")
        print(f"Dry Run:     {dry_run} (Skip Firestore write: {dry_run})")
    print(f"Sources:     {len(sources)}")
    print("=" * 60)
    print()

    # Determine database persistence
    use_firebase = False
    if offline:
        print("ℹ️  Offline mode active: external network, browser, and database writes are disabled.")
    elif not dry_run:
        print("🔥 Connecting to Firebase Firestore...")
        if initialize_firebase():
            print("✅ Firebase connected successfully.")
            use_firebase = True
        else:
            print("⚠️  Firebase key missing or invalid. Running without saving.")
            use_firebase = False
    else:
        print("ℹ️  Dry-run active: skipping Firestore document writes.")

    all_posts: List[Dict[str, Any]] = []
    failed_sources: List[str] = []

    if offline:
        fixture_posts = run_offline_fixture_pipeline(
            sources=sources,
            fixture_path=fixture_path,
            override_max_posts=override_max_posts
        )
        if fixture_posts is None:
            print("❌ Offline pipeline execution aborted: fixture file missing.")
            return 1
        all_posts = fixture_posts
    else:
        # Load appropriate browser scraper module
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

        for i, source in enumerate(sources, 1):
            page_id = source.get('id')
            page_name = source.get('name', page_id)
            max_posts = override_max_posts if override_max_posts is not None else source.get('posts_to_fetch', 5)

            print(f"\n[{i}/{len(sources)}] Source: {page_name} (@{page_id}) | Limit: {max_posts}")
            print("-" * 50)

            try:
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
    db_errors = 0
    if all_posts and use_firebase:
        print("\n💾 Persisting collected posts to Firestore...")
        result = save_posts_batch(all_posts)
        db_errors = result.get("errors", 0)
        print(f"   ✅ Saved: {result['saved']} | Skipped: {result['skipped']} | Errors: {db_errors}")
        if db_errors > 0:
            print(f"   ❌ Encountered {db_errors} database write error(s).")
    elif all_posts and not use_firebase:
        if offline:
            print(f"\nℹ️  Processed {len(all_posts)} synthetic sample posts from offline fixture (offline mode: external database writes disabled).")
        else:
            print(f"\nℹ️  Collected {len(all_posts)} posts (unsaved due to dry-run or unconfigured Firebase).")

    # Final summary
    print()
    print("=" * 60)
    print("EXECUTION SUMMARY")
    print("=" * 60)
    if offline:
        print(f"Synthetic sample posts parsed: {len(all_posts)}")
        print("Note: Offline fixture counts represent synthetic sample records, not live scraped posts.")
    else:
        print(f"Total posts collected: {len(all_posts)}")
        print(f"Failed sources:        {len(failed_sources)} ({', '.join(failed_sources) if failed_sources else 'None'})")
    print(f"Database write errors: {db_errors}")
    print(f"Completed at:          {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # Exit status reflects scraping and persistence health
    if db_errors > 0:
        return 3
    if failed_sources:
        return 2
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="QCU Facebook Scraper Runner")
    parser.add_argument("--source", "-s", help="Process a single page ID instead of all configured sources")
    parser.add_argument("--name", "-n", default="", help="Display name for single source")
    parser.add_argument("--playwright", action="store_true", help="Use Playwright backend instead of Selenium")
    parser.add_argument("--no-headless", action="store_false", dest="headless", default=True, help="Run browser in visible mode")
    parser.add_argument("--max-posts", "-m", type=int, default=None, help="Override posts_to_fetch limit")
    parser.add_argument("--dry-run", action="store_true", help="Run pipeline without writing documents to Firebase")
    parser.add_argument("--offline", action="store_true", help="Run completely offline using local fixtures (zero browser launch, zero network calls)")
    parser.add_argument("--fixture", type=Path, default=None, help="Custom text fixture file path for offline mode")
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
        offline=args.offline,
        fixture_path=args.fixture,
        override_max_posts=args.max_posts,
        save_debug=args.save_debug
    )


if __name__ == "__main__":
    sys.exit(main())
