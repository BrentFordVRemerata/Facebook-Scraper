"""
Facebook Scraper using Playwright (Alternative Implementation)
==============================================================
Provides Playwright-based text announcement collection from public Facebook Pages.
Includes performance tracking, safe cookie loading, and deterministic parsing.
"""

import os
import time
import json
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, List, Tuple, Dict, Any

from src.config import get_cookies_path, load_sources, get_project_root
from src.parser import parse_posts_from_text, extract_text_blocks

logger = logging.getLogger(__name__)

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


# ==============================================================================
# STATISTICS TRACKING
# ==============================================================================

@dataclass
class ScraperStats:
    """Tracks performance metrics for each scrape run."""
    page_id: str
    tool: str = "playwright"
    start_time: float = field(default_factory=time.time)
    
    # Timing breakdowns (in seconds)
    time_browser_init: float = 0.0
    time_facebook_load: float = 0.0
    time_cookies: float = 0.0
    time_page_navigate: float = 0.0
    time_scrolling: float = 0.0
    time_extraction: float = 0.0
    time_total: float = 0.0
    
    # Results
    posts_found: int = 0
    text_lines: int = 0
    text_blocks: int = 0
    html_size_kb: float = 0.0
    
    # Status
    success: bool = False
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "page_id": self.page_id,
            "tool": self.tool,
            "timing": {
                "browser_init": round(self.time_browser_init, 2),
                "facebook_load": round(self.time_facebook_load, 2),
                "cookies": round(self.time_cookies, 2),
                "page_navigate": round(self.time_page_navigate, 2),
                "scrolling": round(self.time_scrolling, 2),
                "extraction": round(self.time_extraction, 2),
                "total": round(self.time_total, 2),
            },
            "results": {
                "posts_found": self.posts_found,
                "text_lines": self.text_lines,
                "text_blocks": self.text_blocks,
                "html_size_kb": round(self.html_size_kb, 1),
            },
            "success": self.success,
            "error": self.error,
        }
    
    def print_summary(self):
        """Print a formatted statistics summary."""
        print(f"\n{'─'*50}")
        print(f"📊 PERFORMANCE STATISTICS ({self.tool.upper()})")
        print(f"{'─'*50}")
        print(f"  Browser init:    {self.time_browser_init:>6.2f}s")
        print(f"  Facebook load:   {self.time_facebook_load:>6.2f}s")
        print(f"  Add cookies:     {self.time_cookies:>6.2f}s")
        print(f"  Navigate page:   {self.time_page_navigate:>6.2f}s")
        print(f"  Scrolling:       {self.time_scrolling:>6.2f}s")
        print(f"  Extraction:      {self.time_extraction:>6.2f}s")
        print(f"  {'─'*28}")
        print(f"  TOTAL:           {self.time_total:>6.2f}s")
        print(f"\n📦 Results: {self.posts_found} posts | {self.text_lines} lines | {self.html_size_kb:.0f}KB HTML")


# ==============================================================================
# COOKIE LOADING
# ==============================================================================

def load_cookies_for_playwright(cookies_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Load cookies from Netscape format file, formatted for Playwright."""
    cookies = []
    path = cookies_path or get_cookies_path()
    if not path or not path.exists():
        return cookies
    
    try:
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                parts = line.split('\t')
                if len(parts) >= 7:
                    cookie: Dict[str, Any] = {
                        'name': parts[5],
                        'value': parts[6],
                        'domain': parts[0],
                        'path': parts[2],
                        'secure': parts[3].upper() == 'TRUE',
                        'httpOnly': False,
                    }
                    try:
                        expiry = int(parts[4])
                        if expiry > 0:
                            cookie['expires'] = expiry
                    except (ValueError, TypeError):
                        pass
                    cookies.append(cookie)
    except Exception as e:
        logger.warning("Error reading cookie file for Playwright at %s: %s", path, e)
    return cookies


# ==============================================================================
# MAIN SCRAPER (Synchronous version)
# ==============================================================================

def scrape_page(
    page_id: str,
    page_name: str = "",
    max_posts: int = 10,
    headless: bool = True,
    show_stats: bool = True,
    save_debug: bool = False
) -> Tuple[List[Dict[str, Any]], ScraperStats]:
    """
    Scrape a Facebook page using Playwright.
    
    Args:
        page_id: Facebook page username (e.g., 'qcu1994')
        page_name: Display name for logging
        max_posts: Maximum posts to extract
        headless: Run browser without visible window
        show_stats: Print performance statistics
        save_debug: Whether to save raw HTML and text dumps to data/ (default: False)
    
    Returns:
        Tuple of (posts list, statistics object)
    """
    if not PLAYWRIGHT_AVAILABLE:
        stats = ScraperStats(page_id=page_id, error="Playwright not installed")
        return [], stats
    
    page_name = page_name or page_id
    stats = ScraperStats(page_id=page_id, tool="playwright")
    posts: List[Dict[str, Any]] = []
    
    save_debug = save_debug or os.environ.get("SAVE_DEBUG_DUMPS", "").lower() in ("1", "true")
    
    print(f"\n{'═'*50}")
    print(f"SCRAPING: {page_name} (Playwright, max: {max_posts})")
    print(f"{'═'*50}")
    
    try:
        with sync_playwright() as p:
            t0 = time.time()
            print("\n[1/5] Initializing browser...")
            
            browser = p.chromium.launch(
                headless=headless,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',
                ]
            )
            
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                locale='en-US',
                timezone_id='Asia/Manila',
            )
            
            page = context.new_page()
            stats.time_browser_init = time.time() - t0
            print(f"      Done ({stats.time_browser_init:.2f}s)")
            
            try:
                # Step 2: Load Facebook homepage
                t0 = time.time()
                print("[2/5] Loading Facebook...")
                page.goto("https://www.facebook.com", wait_until="domcontentloaded", timeout=30000)
                stats.time_facebook_load = time.time() - t0
                print(f"      Done ({stats.time_facebook_load:.2f}s)")
                
                # Step 3: Add cookies
                t0 = time.time()
                print("[3/5] Adding cookies (if available)...")
                cookies = load_cookies_for_playwright()
                if cookies:
                    context.add_cookies(cookies)
                    print(f"      Added {len(cookies)} cookies")
                else:
                    print("      No cookies provided (public mode)")
                stats.time_cookies = time.time() - t0
                print(f"      Done ({stats.time_cookies:.2f}s)")
                
                # Step 4: Navigate to target page
                t0 = time.time()
                url = f"https://www.facebook.com/{page_id}"
                print(f"[4/5] Navigating to {url}...")
                page.goto(url, wait_until="domcontentloaded", timeout=45000)
                page.wait_for_timeout(4000)
                stats.time_page_navigate = time.time() - t0
                print(f"      Done ({stats.time_page_navigate:.2f}s)")
                
                # Step 5: Scroll to load posts
                t0 = time.time()
                print("[5/5] Scrolling to load posts...")
                scroll_count = 3
                for i in range(scroll_count):
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    print(f"      Scroll {i+1}/{scroll_count}...")
                    page.wait_for_timeout(2000)
                
                page.evaluate("window.scrollTo(0, 500)")
                page.wait_for_timeout(1000)
                stats.time_scrolling = time.time() - t0
                print(f"      Done ({stats.time_scrolling:.2f}s)")
                
                # Step 6: Extract posts
                t0 = time.time()
                print("\n📝 Extracting posts...")
                
                body_text = page.inner_text("body")
                lines = body_text.split('\n')
                stats.text_lines = len(lines)
                
                blocks = extract_text_blocks(body_text)
                stats.text_blocks = len(blocks)
                
                posts = parse_posts_from_text(
                    raw_text=body_text,
                    source_id=page_id,
                    source_name=page_name,
                    max_posts=max_posts
                )
                
                for post in posts:
                    print(f"   ✅ {post['title'][:60]}...")
                
                stats.time_extraction = time.time() - t0
                stats.posts_found = len(posts)
                
                html_content = page.content()
                stats.html_size_kb = len(html_content) / 1024
                
                if save_debug:
                    data_dir = get_project_root() / "data"
                    data_dir.mkdir(exist_ok=True)
                    (data_dir / "debug_page_playwright.html").write_text(html_content, encoding='utf-8')
                    (data_dir / "debug_text_playwright.txt").write_text(body_text, encoding='utf-8')
                    print("   ⚠️  Debug dumps written to data/debug_page_playwright.html")
                
                stats.success = True
                
            finally:
                context.close()
                browser.close()
                
    except Exception as e:
        stats.error = str(e)
        logger.exception("Playwright error on page %s: %s", page_id, e)
        print(f"\n❌ Error: {e}")
        
    stats.time_total = (stats.time_browser_init + stats.time_facebook_load +
                        stats.time_cookies + stats.time_page_navigate +
                        stats.time_scrolling + stats.time_extraction)
    
    if show_stats:
        stats.print_summary()
        
    return posts, stats


def scrape_all_sources(
    sources: List[Dict[str, Any]],
    max_posts_per_source: Optional[int] = None,
    headless: bool = True
) -> Tuple[List[Dict[str, Any]], List[ScraperStats]]:
    """Scrape multiple Facebook pages sequentially using Playwright."""
    all_posts: List[Dict[str, Any]] = []
    all_stats: List[ScraperStats] = []
    
    print(f"\n{'═'*60}")
    print(f"BATCH SCRAPE (Playwright): {len(sources)} sources")
    print(f"{'═'*60}")
    
    batch_start = time.time()
    
    for i, source in enumerate(sources, 1):
        source_id = source.get('id', '')
        source_name = source.get('name', source_id)
        limit = max_posts_per_source if max_posts_per_source is not None else source.get('posts_to_fetch', 10)
        
        print(f"\n[{i}/{len(sources)}] Starting {source_name} (max {limit} posts)...")
        
        posts, stats = scrape_page(
            page_id=source_id,
            page_name=source_name,
            max_posts=limit,
            headless=headless,
            show_stats=False
        )
        
        all_posts.extend(posts)
        all_stats.append(stats)
        
        print(f"   Got {len(posts)} posts in {stats.time_total:.1f}s")
        
    batch_time = time.time() - batch_start
    print(f"\n{'═'*60}")
    print("📊 BATCH SUMMARY (Playwright)")
    print(f"{'═'*60}")
    print(f"  Sources scraped: {len(sources)}")
    print(f"  Total posts:     {len(all_posts)}")
    print(f"  Total time:      {batch_time:.1f}s ({batch_time/60:.1f} min)")
    
    return all_posts, all_stats


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Facebook Page Scraper with Statistics (Playwright)")
    parser.add_argument("--page", "-p", help="Single page ID to scrape (e.g., qcu1994)")
    parser.add_argument("--name", "-n", default="", help="Display name of the page")
    parser.add_argument("--all", "-a", action="store_true", help="Scrape all sources from config")
    parser.add_argument("--headless", action="store_true", default=True, help="Run in headless mode (default: True)")
    parser.add_argument("--no-headless", action="store_false", dest="headless", help="Run with browser window visible")
    parser.add_argument("--max", "-m", type=int, default=10, help="Max posts per source (default: 10)")
    parser.add_argument("--save-debug", action="store_true", help="Save raw HTML/text dumps to data/")
    
    args = parser.parse_args()
    
    if args.all:
        sources = load_sources()
        enabled = [s for s in sources if s.get('enabled', True)]
        posts, stats = scrape_all_sources(
            sources=enabled,
            max_posts_per_source=args.max,
            headless=args.headless
        )
    elif args.page:
        posts, stats = scrape_page(
            page_id=args.page,
            page_name=args.name or args.page,
            max_posts=args.max,
            headless=args.headless,
            save_debug=args.save_debug
        )
        if posts:
            print(f"\n📄 First post:\n{json.dumps(posts[0], indent=2, ensure_ascii=False)}")
    else:
        parser.print_help()
