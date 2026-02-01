"""
Facebook Scraper with Performance Statistics
============================================
Tracks timing for optimization decisions.
"""

import time
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from webdriver_manager.chrome import ChromeDriverManager
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False


# ==============================================================================
# STATISTICS TRACKING
# ==============================================================================

@dataclass
class ScraperStats:
    """Tracks performance metrics for each scrape run."""
    page_id: str
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
        print("📊 PERFORMANCE STATISTICS")
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
        
        # Estimate for scale
        print(f"\n🔮 Scale Estimates (sequential):")
        print(f"   10 pages:  {self.time_total * 10 / 60:>5.1f} minutes")
        print(f"   50 pages:  {self.time_total * 50 / 60:>5.1f} minutes")
        print(f"  100 pages:  {self.time_total * 100 / 60:>5.1f} minutes")


# ==============================================================================
# COOKIE LOADING
# ==============================================================================

def load_cookies():
    """Load cookies from Netscape format file."""
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
            cookies.append({
                'domain': parts[0],
                'path': parts[2],
                'secure': parts[3].upper() == 'TRUE',
                'name': parts[5],
                'value': parts[6],
            })
    return cookies


# ==============================================================================
# MAIN SCRAPER
# ==============================================================================

def scrape_page(page_id: str, page_name: str = "", max_posts: int = 10, 
                headless: bool = True, show_stats: bool = True) -> tuple[list, ScraperStats]:
    """
    Scrape a Facebook page for posts.
    
    Args:
        page_id: Facebook page username (e.g., 'qcu1994')
        page_name: Display name for logging
        max_posts: Maximum posts to extract
        headless: Run browser without visible window
        show_stats: Print performance statistics
    
    Returns:
        Tuple of (posts list, statistics object)
    """
    page_name = page_name or page_id
    stats = ScraperStats(page_id=page_id)
    posts = []
    
    print(f"\n{'═'*50}")
    print(f"SCRAPING: {page_name}")
    print(f"{'═'*50}")
    
    # ─────────────────────────────────────────────────
    # Step 1: Initialize browser
    # ─────────────────────────────────────────────────
    t0 = time.time()
    print("\n[1/5] Initializing browser...")
    
    options = Options()
    if headless:
        options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    options.add_experimental_option('excludeSwitches', ['enable-automation'])
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    stats.time_browser_init = time.time() - t0
    print(f"      Done ({stats.time_browser_init:.2f}s)")
    
    try:
        # ─────────────────────────────────────────────────
        # Step 2: Load Facebook homepage
        # ─────────────────────────────────────────────────
        t0 = time.time()
        print("[2/5] Loading Facebook...")
        driver.get("https://www.facebook.com")
        time.sleep(2)
        stats.time_facebook_load = time.time() - t0
        print(f"      Done ({stats.time_facebook_load:.2f}s)")
        
        # ─────────────────────────────────────────────────
        # Step 3: Add authentication cookies
        # ─────────────────────────────────────────────────
        t0 = time.time()
        print("[3/5] Adding cookies...")
        cookies = load_cookies()
        for c in cookies:
            try:
                driver.add_cookie(c)
            except:
                pass
        stats.time_cookies = time.time() - t0
        print(f"      Added {len(cookies)} cookies ({stats.time_cookies:.2f}s)")
        
        # ─────────────────────────────────────────────────
        # Step 4: Navigate to target page
        # ─────────────────────────────────────────────────
        t0 = time.time()
        url = f"https://www.facebook.com/{page_id}"
        print(f"[4/5] Navigating to {page_id}...")
        driver.get(url)
        time.sleep(4)
        stats.time_page_navigate = time.time() - t0
        print(f"      Done ({stats.time_page_navigate:.2f}s)")
        
        # ─────────────────────────────────────────────────
        # Step 5: Scroll to load dynamic content
        # ─────────────────────────────────────────────────
        t0 = time.time()
        print("[5/5] Scrolling to load posts...")
        scroll_count = 3
        for i in range(scroll_count):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            print(f"      Scroll {i+1}/{scroll_count}...")
            time.sleep(2)
        driver.execute_script("window.scrollTo(0, 500);")
        time.sleep(1)
        stats.time_scrolling = time.time() - t0
        print(f"      Done ({stats.time_scrolling:.2f}s)")
        
        # ─────────────────────────────────────────────────
        # Step 6: Extract post content
        # ─────────────────────────────────────────────────
        t0 = time.time()
        print("\n📝 Extracting posts...")
        
        body_text = driver.find_element(By.TAG_NAME, "body").text
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
        html_content = driver.page_source
        stats.html_size_kb = len(html_content) / 1024
        
        Path("data").mkdir(exist_ok=True)
        Path("data/debug_page.html").write_text(html_content, encoding='utf-8')
        Path("data/debug_text.txt").write_text(body_text, encoding='utf-8')
        
        stats.success = True
        
    except Exception as e:
        stats.error = str(e)
        print(f"\n❌ Error: {e}")
    finally:
        driver.quit()
    
    # Calculate total time
    stats.time_total = (stats.time_browser_init + stats.time_facebook_load + 
                        stats.time_cookies + stats.time_page_navigate + 
                        stats.time_scrolling + stats.time_extraction)
    
    # Show statistics
    if show_stats:
        stats.print_summary()
    
    return posts, stats


# ==============================================================================
# BATCH SCRAPING (Multiple Pages)
# ==============================================================================

def scrape_all_sources(sources: list, max_posts_per_source: int = 10, 
                       headless: bool = True) -> tuple[list, list]:
    """
    Scrape multiple Facebook pages sequentially.
    
    Args:
        sources: List of dicts with 'id' and 'name' keys
        max_posts_per_source: Max posts to get from each source
        headless: Run in headless mode
    
    Returns:
        Tuple of (all_posts, all_stats)
    """
    all_posts = []
    all_stats = []
    
    print(f"\n{'═'*60}")
    print(f"BATCH SCRAPE: {len(sources)} sources")
    print(f"{'═'*60}")
    
    batch_start = time.time()
    
    for i, source in enumerate(sources, 1):
        print(f"\n[{i}/{len(sources)}] Starting {source.get('name', source['id'])}...")
        
        posts, stats = scrape_page(
            page_id=source['id'],
            page_name=source.get('name', source['id']),
            max_posts=max_posts_per_source,
            headless=headless,
            show_stats=False  # Summarize at end
        )
        
        all_posts.extend(posts)
        all_stats.append(stats)
        
        print(f"   Got {len(posts)} posts in {stats.time_total:.1f}s")
    
    batch_time = time.time() - batch_start
    
    # Final summary
    print(f"\n{'═'*60}")
    print("📊 BATCH SUMMARY")
    print(f"{'═'*60}")
    print(f"  Sources scraped: {len(sources)}")
    print(f"  Total posts:     {len(all_posts)}")
    print(f"  Total time:      {batch_time:.1f}s ({batch_time/60:.1f} min)")
    print(f"  Avg per source:  {batch_time/len(sources):.1f}s")
    
    # Breakdown by source
    print(f"\n  Per-Source Breakdown:")
    for stat in all_stats:
        status = "✅" if stat.success else "❌"
        print(f"    {status} {stat.page_id}: {stat.posts_found} posts, {stat.time_total:.1f}s")
    
    # Scale projections
    avg_time = batch_time / len(sources) if sources else 0
    print(f"\n🔮 Scale Projections (at {avg_time:.1f}s/page avg):")
    print(f"   50 pages:  {avg_time * 50 / 60:>5.1f} minutes")
    print(f"  100 pages:  {avg_time * 100 / 60:>5.1f} minutes")
    
    return all_posts, all_stats


# ==============================================================================
# CLI ENTRY POINT
# ==============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Facebook Page Scraper with Statistics")
    parser.add_argument("--page", "-p", help="Single page ID to scrape (e.g., qcu1994)")
    parser.add_argument("--all", "-a", action="store_true", help="Scrape all sources from config")
    parser.add_argument("--headless", action="store_true", help="Run in headless mode (no browser window)")
    parser.add_argument("--max", "-m", type=int, default=10, help="Max posts per source (default: 10)")
    
    args = parser.parse_args()
    
    if args.all:
        # Load sources from config
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
        # Interactive mode - single page test
        print("\n" + "═"*60)
        print("FACEBOOK SCRAPER - DEBUG MODE")
        print("═"*60)
        print("\n⚠️  DON'T TOUCH THE BROWSER WHILE IT RUNS!")
        print("   Just watch and wait ~30 seconds.\n")
        
        input("Press ENTER to start...")
        
        posts, stats = scrape_page("qcu1994", "QCU Main", max_posts=5, headless=False)
        
        if posts:
            print(f"\n{'═'*60}")
            print("FIRST POST FOUND:")
            print(f"{'═'*60}")
            print(json.dumps(posts[0], indent=2, ensure_ascii=False))
        
        # Save stats
        Path("data").mkdir(exist_ok=True)
        Path("data/last_stats.json").write_text(
            json.dumps(stats.to_dict(), indent=2),
            encoding='utf-8'
        )
        print(f"\n📁 Stats saved to data/last_stats.json")
