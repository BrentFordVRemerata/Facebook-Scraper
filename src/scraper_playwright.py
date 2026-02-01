"""
Facebook Scraper using Playwright
=================================
Alternative to Selenium with better performance and anti-detection.

Benefits over Selenium:
- ~2x faster (WebSocket vs HTTP)
- Built-in auto-wait (no manual sleeps)
- Better anti-detection by default
- Native parallel support via browser contexts
- Built-in video recording for debugging

Install:
    pip install playwright
    playwright install chromium
"""

import time
import hashlib
import json
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

try:
    from playwright.sync_api import sync_playwright, Page, Browser
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("⚠️  Playwright not installed. Run: pip install playwright && playwright install chromium")


# ==============================================================================
# STATISTICS TRACKING (Same as Selenium version for fair comparison)
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
    
    def to_dict(self):
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
        
        # Scale estimates
        print(f"\n🔮 Scale Estimates (sequential):")
        print(f"   10 pages:  {self.time_total * 10 / 60:>5.1f} minutes")
        print(f"   50 pages:  {self.time_total * 50 / 60:>5.1f} minutes")
        print(f"  100 pages:  {self.time_total * 100 / 60:>5.1f} minutes")


# ==============================================================================
# COOKIE LOADING
# ==============================================================================

def load_cookies_for_playwright():
    """Load cookies from Netscape format file, formatted for Playwright."""
    cookies = []
    path = Path("config/facebook_cookies.txt")
    if not path.exists():
        return cookies
    
    for line in open(path, 'r', encoding='utf-8'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        parts = line.split('\t')
        if len(parts) >= 7:
            # Playwright uses slightly different cookie format
            cookie = {
                'name': parts[5],
                'value': parts[6],
                'domain': parts[0],
                'path': parts[2],
                'secure': parts[3].upper() == 'TRUE',
                'httpOnly': False,  # Default
            }
            # Handle expiry
            try:
                expiry = int(parts[4])
                if expiry > 0:
                    cookie['expires'] = expiry
            except:
                pass
            cookies.append(cookie)
    return cookies


# ==============================================================================
# MAIN SCRAPER (Synchronous version)
# ==============================================================================

def scrape_page(page_id: str, page_name: str = "", max_posts: int = 10,
                headless: bool = True, show_stats: bool = True) -> tuple[list, ScraperStats]:
    """
    Scrape a Facebook page using Playwright.
    
    Args:
        page_id: Facebook page username (e.g., 'qcu1994')
        page_name: Display name for logging
        max_posts: Maximum posts to extract
        headless: Run browser without visible window
        show_stats: Print performance statistics
    
    Returns:
        Tuple of (posts list, statistics object)
    """
    if not PLAYWRIGHT_AVAILABLE:
        print("❌ Playwright not available!")
        return [], ScraperStats(page_id=page_id, error="Playwright not installed")
    
    page_name = page_name or page_id
    stats = ScraperStats(page_id=page_id, tool="playwright")
    posts = []
    
    print(f"\n{'═'*50}")
    print(f"SCRAPING: {page_name} (Playwright)")
    print(f"{'═'*50}")
    
    with sync_playwright() as p:
        # ─────────────────────────────────────────────────
        # Step 1: Initialize browser
        # ─────────────────────────────────────────────────
        t0 = time.time()
        print("\n[1/5] Initializing browser...")
        
        # Playwright has better stealth by default
        browser = p.chromium.launch(
            headless=headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
            ]
        )
        
        # Create context with realistic settings
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='en-US',
            timezone_id='Asia/Manila',
        )
        
        # Remove automation indicators
        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
        
        page = context.new_page()
        stats.time_browser_init = time.time() - t0
        print(f"      Done ({stats.time_browser_init:.2f}s)")
        
        try:
            # ─────────────────────────────────────────────────
            # Step 2: Load Facebook homepage
            # ─────────────────────────────────────────────────
            t0 = time.time()
            print("[2/5] Loading Facebook...")
            page.goto("https://www.facebook.com", wait_until="domcontentloaded")
            stats.time_facebook_load = time.time() - t0
            print(f"      Done ({stats.time_facebook_load:.2f}s)")
            
            # ─────────────────────────────────────────────────
            # Step 3: Add authentication cookies
            # ─────────────────────────────────────────────────
            t0 = time.time()
            print("[3/5] Adding cookies...")
            cookies = load_cookies_for_playwright()
            if cookies:
                context.add_cookies(cookies)
            stats.time_cookies = time.time() - t0
            print(f"      Added {len(cookies)} cookies ({stats.time_cookies:.2f}s)")
            
            # ─────────────────────────────────────────────────
            # Step 4: Navigate to target page
            # ─────────────────────────────────────────────────
            t0 = time.time()
            url = f"https://www.facebook.com/{page_id}"
            print(f"[4/5] Navigating to {page_id}...")
            
            # NOTE: Don't use networkidle - Facebook NEVER becomes idle!
            # Use domcontentloaded + explicit wait instead
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(4000)  # Wait for dynamic content like Selenium
            stats.time_page_navigate = time.time() - t0
            print(f"      Done ({stats.time_page_navigate:.2f}s)")
            
            # ─────────────────────────────────────────────────
            # Step 5: Scroll to load dynamic content
            # ─────────────────────────────────────────────────
            t0 = time.time()
            print("[5/5] Scrolling to load posts...")
            scroll_count = 3
            for i in range(scroll_count):
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                print(f"      Scroll {i+1}/{scroll_count}...")
                page.wait_for_timeout(2000)  # Playwright's timeout (ms)
            
            page.evaluate("window.scrollTo(0, 500)")
            page.wait_for_timeout(1000)
            stats.time_scrolling = time.time() - t0
            print(f"      Done ({stats.time_scrolling:.2f}s)")
            
            # ─────────────────────────────────────────────────
            # Step 6: Extract post content
            # ─────────────────────────────────────────────────
            t0 = time.time()
            print("\n📝 Extracting posts...")
            
            # Get visible text content
            body_text = page.inner_text("body")
            lines = body_text.split('\n')
            stats.text_lines = len(lines)
            
            # Collect text blocks
            current_block = []
            blocks = []
            for line in lines:
                line = line.strip()
                if len(line) > 10:
                    current_block.append(line)
                elif current_block:
                    block_text = '\n'.join(current_block)
                    if len(block_text) > 100:
                        blocks.append(block_text)
                    current_block = []
            stats.text_blocks = len(blocks)
            
            # Filter to real posts
            seen = set()
            skip_words = ['Like', 'Comment', 'Share', 'Follow', 'Message',
                         'See more', 'View more', 'Write a comment', 'Log In']
            
            for block in blocks:
                if len(posts) >= max_posts:
                    break
                if any(block.startswith(w) for w in skip_words):
                    continue
                if len(block) < 50:
                    continue
                
                block_hash = hashlib.md5(block[:100].encode()).hexdigest()[:8]
                if block_hash in seen:
                    continue
                seen.add(block_hash)
                
                post = {
                    "post_id": f"{page_id}_{block_hash}",
                    "source_id": page_id,
                    "source_name": page_name,
                    "title": block.split('\n')[0][:80],
                    "text": block[:2000],
                    "scraped_at": datetime.now(timezone.utc).isoformat(),
                    "content_hash": hashlib.sha256(block.encode()).hexdigest(),
                }
                posts.append(post)
                print(f"   ✅ {post['title'][:60]}...")
            
            stats.time_extraction = time.time() - t0
            stats.posts_found = len(posts)
            
            # Save debug files
            html_content = page.content()
            stats.html_size_kb = len(html_content) / 1024
            
            Path("data").mkdir(exist_ok=True)
            Path("data/debug_page_playwright.html").write_text(html_content, encoding='utf-8')
            Path("data/debug_text_playwright.txt").write_text(body_text, encoding='utf-8')
            
            stats.success = True
            
        except Exception as e:
            stats.error = str(e)
            print(f"\n❌ Error: {e}")
        finally:
            context.close()
            browser.close()
    
    # Calculate total time
    stats.time_total = (stats.time_browser_init + stats.time_facebook_load +
                        stats.time_cookies + stats.time_page_navigate +
                        stats.time_scrolling + stats.time_extraction)
    
    if show_stats:
        stats.print_summary()
    
    return posts, stats


# ==============================================================================
# BATCH SCRAPING WITH BROWSER REUSE (Playwright advantage!)
# ==============================================================================

def scrape_all_sources(sources: list, max_posts_per_source: int = 10,
                       headless: bool = True) -> tuple[list, list]:
    """
    Scrape multiple Facebook pages with browser reuse.
    
    This is where Playwright shines - one browser, many pages!
    """
    if not PLAYWRIGHT_AVAILABLE:
        print("❌ Playwright not available!")
        return [], []
    
    all_posts = []
    all_stats = []
    
    print(f"\n{'═'*60}")
    print(f"BATCH SCRAPE: {len(sources)} sources (Playwright)")
    print(f"{'═'*60}")
    
    batch_start = time.time()
    
    with sync_playwright() as p:
        # Initialize browser ONCE
        print("\n🚀 Starting browser (will reuse for all pages)...")
        t0 = time.time()
        
        browser = p.chromium.launch(
            headless=headless,
            args=['--disable-blink-features=AutomationControlled', '--no-sandbox']
        )
        
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            locale='en-US',
            timezone_id='Asia/Manila',
        )
        
        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
        
        # Add cookies ONCE
        cookies = load_cookies_for_playwright()
        if cookies:
            context.add_cookies(cookies)
            print(f"   Added {len(cookies)} cookies")
        
        browser_init_time = time.time() - t0
        print(f"   Browser ready ({browser_init_time:.2f}s)\n")
        
        page = context.new_page()
        
        # Load Facebook homepage once
        page.goto("https://www.facebook.com", wait_until="domcontentloaded")
        
        # Now scrape each source
        for i, source in enumerate(sources, 1):
            source_id = source['id']
            source_name = source.get('name', source_id)
            
            print(f"[{i}/{len(sources)}] {source_name}...")
            stats = ScraperStats(page_id=source_id, tool="playwright")
            posts = []
            
            try:
                t0 = time.time()
                url = f"https://www.facebook.com/{source_id}"
                page.goto(url, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(4000)  # Wait for dynamic content
                stats.time_page_navigate = time.time() - t0
                
                # Scroll
                t0 = time.time()
                for _ in range(3):
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    page.wait_for_timeout(2000)
                page.evaluate("window.scrollTo(0, 500)")
                page.wait_for_timeout(1000)
                stats.time_scrolling = time.time() - t0
                
                # Extract
                t0 = time.time()
                body_text = page.inner_text("body")
                lines = body_text.split('\n')
                stats.text_lines = len(lines)
                
                current_block = []
                blocks = []
                for line in lines:
                    line = line.strip()
                    if len(line) > 10:
                        current_block.append(line)
                    elif current_block:
                        block_text = '\n'.join(current_block)
                        if len(block_text) > 100:
                            blocks.append(block_text)
                        current_block = []
                stats.text_blocks = len(blocks)
                
                seen = set()
                skip_words = ['Like', 'Comment', 'Share', 'Follow', 'Message',
                             'See more', 'View more', 'Write a comment', 'Log In']
                
                for block in blocks:
                    if len(posts) >= max_posts_per_source:
                        break
                    if any(block.startswith(w) for w in skip_words):
                        continue
                    if len(block) < 50:
                        continue
                    
                    block_hash = hashlib.md5(block[:100].encode()).hexdigest()[:8]
                    if block_hash in seen:
                        continue
                    seen.add(block_hash)
                    
                    post = {
                        "post_id": f"{source_id}_{block_hash}",
                        "source_id": source_id,
                        "source_name": source_name,
                        "title": block.split('\n')[0][:80],
                        "text": block[:2000],
                        "scraped_at": datetime.now(timezone.utc).isoformat(),
                        "content_hash": hashlib.sha256(block.encode()).hexdigest(),
                    }
                    posts.append(post)
                
                stats.time_extraction = time.time() - t0
                stats.posts_found = len(posts)
                stats.time_total = stats.time_page_navigate + stats.time_scrolling + stats.time_extraction
                stats.success = True
                
                print(f"   ✅ {len(posts)} posts in {stats.time_total:.1f}s")
                
            except Exception as e:
                stats.error = str(e)
                print(f"   ❌ Error: {e}")
            
            all_posts.extend(posts)
            all_stats.append(stats)
        
        context.close()
        browser.close()
    
    batch_time = time.time() - batch_start
    
    # Summary
    print(f"\n{'═'*60}")
    print("📊 BATCH SUMMARY (Playwright)")
    print(f"{'═'*60}")
    print(f"  Sources scraped: {len(sources)}")
    print(f"  Total posts:     {len(all_posts)}")
    print(f"  Total time:      {batch_time:.1f}s ({batch_time/60:.1f} min)")
    print(f"  Avg per source:  {batch_time/len(sources):.1f}s")
    
    print(f"\n  Per-Source Breakdown:")
    for stat in all_stats:
        status = "✅" if stat.success else "❌"
        print(f"    {status} {stat.page_id}: {stat.posts_found} posts, {stat.time_total:.1f}s")
    
    avg_time = batch_time / len(sources) if sources else 0
    print(f"\n🔮 Scale Projections (at {avg_time:.1f}s/page avg):")
    print(f"   50 pages:  {avg_time * 50 / 60:>5.1f} minutes")
    print(f"  100 pages:  {avg_time * 100 / 60:>5.1f} minutes")
    
    return all_posts, all_stats


# ==============================================================================
# COMPARISON TOOL
# ==============================================================================

def compare_with_selenium(page_id: str = "qcu1994", page_name: str = "QCU Main"):
    """
    Run both Selenium and Playwright on same page, compare results.
    """
    print("\n" + "═"*60)
    print("🔬 SELENIUM vs PLAYWRIGHT COMPARISON")
    print("═"*60)
    
    results = {}
    
    # Test Playwright
    print("\n" + "─"*40)
    print("Testing PLAYWRIGHT...")
    print("─"*40)
    pw_posts, pw_stats = scrape_page(page_id, page_name, headless=True)
    results['playwright'] = pw_stats.to_dict()
    
    # Test Selenium (import here to avoid dependency issues)
    try:
        from scraper import scrape_page as selenium_scrape_page
        print("\n" + "─"*40)
        print("Testing SELENIUM...")
        print("─"*40)
        se_posts, se_stats = selenium_scrape_page(page_id, page_name, headless=True)
        results['selenium'] = se_stats.to_dict()
    except ImportError:
        print("\n⚠️  Selenium scraper not available for comparison")
        results['selenium'] = None
    
    # Comparison
    print("\n" + "═"*60)
    print("📊 COMPARISON RESULTS")
    print("═"*60)
    
    if results['selenium']:
        pw_time = results['playwright']['timing']['total']
        se_time = results['selenium']['timing']['total']
        
        print(f"\n{'Metric':<25} {'Playwright':>12} {'Selenium':>12} {'Winner':>10}")
        print("─"*60)
        print(f"{'Total Time':<25} {pw_time:>10.2f}s {se_time:>10.2f}s {'PW' if pw_time < se_time else 'SE':>10}")
        print(f"{'Posts Found':<25} {results['playwright']['results']['posts_found']:>12} {results['selenium']['results']['posts_found']:>12}")
        print(f"{'Browser Init':<25} {results['playwright']['timing']['browser_init']:>10.2f}s {results['selenium']['timing']['browser_init']:>10.2f}s")
        print(f"{'Page Navigate':<25} {results['playwright']['timing']['page_navigate']:>10.2f}s {results['selenium']['timing']['page_navigate']:>10.2f}s")
        
        speedup = ((se_time - pw_time) / se_time) * 100
        print(f"\n{'Playwright is ' + str(abs(round(speedup))) + '% ' + ('faster' if speedup > 0 else 'slower')}")
    
    # Save comparison
    Path("data").mkdir(exist_ok=True)
    Path("data/comparison_results.json").write_text(
        json.dumps(results, indent=2),
        encoding='utf-8'
    )
    print(f"\n📁 Results saved to data/comparison_results.json")
    
    return results


# ==============================================================================
# CLI ENTRY POINT
# ==============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Facebook Page Scraper (Playwright)")
    parser.add_argument("--page", "-p", help="Single page ID to scrape")
    parser.add_argument("--all", "-a", action="store_true", help="Scrape all sources from config")
    parser.add_argument("--compare", "-c", action="store_true", help="Compare Playwright vs Selenium")
    parser.add_argument("--headless", action="store_true", help="Run in headless mode")
    parser.add_argument("--max", "-m", type=int, default=10, help="Max posts per source")
    
    args = parser.parse_args()
    
    if args.compare:
        compare_with_selenium()
    
    elif args.all:
        sources_path = Path("config/sources.json")
        if sources_path.exists():
            with open(sources_path) as f:
                data = json.load(f)
                sources = data.get("sources", data) if isinstance(data, dict) else data
            
            posts, stats = scrape_all_sources(
                sources=sources,
                max_posts_per_source=args.max,
                headless=args.headless
            )
        else:
            print("❌ config/sources.json not found!")
    
    elif args.page:
        posts, stats = scrape_page(
            page_id=args.page,
            max_posts=args.max,
            headless=args.headless
        )
        if posts:
            print(f"\n📄 First post:\n{json.dumps(posts[0], indent=2, ensure_ascii=False)}")
    
    else:
        # Interactive mode
        print("\n" + "═"*60)
        print("FACEBOOK SCRAPER - PLAYWRIGHT VERSION")
        print("═"*60)
        print("\n⚠️  DON'T TOUCH THE BROWSER WHILE IT RUNS!\n")
        
        input("Press ENTER to start...")
        
        posts, stats = scrape_page("qcu1994", "QCU Main", max_posts=5, headless=False)
        
        if posts:
            print(f"\n{'═'*60}")
            print("FIRST POST FOUND:")
            print(f"{'═'*60}")
            print(json.dumps(posts[0], indent=2, ensure_ascii=False))
        
        # Save stats
        Path("data").mkdir(exist_ok=True)
        Path("data/last_stats_playwright.json").write_text(
            json.dumps(stats.to_dict(), indent=2),
            encoding='utf-8'
        )
        print(f"\n📁 Stats saved to data/last_stats_playwright.json")
