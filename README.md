# QCU Facebook Scraper

**Status:** ✅ Working - Saves to Firebase  
**Last Tested:** February 1, 2026  
**Posts Scraped:** 47 from 7 pages

Scrapes announcements from QCU Facebook pages and saves to Firebase.

## What Works Now

| Feature | Status |
|---------|--------|
| Scrape posts | ✅ 47 posts from 7 pages |
| Save to Firebase | ✅ Working |
| Performance stats | ✅ ~20s per page |

## What's Missing (TODO)

| Feature | Status | Priority | Why Needed |
|---------|--------|----------|------------|
| Post URLs | ❌ | 🔴 High | "View on Facebook" button |
| Post dates | ❌ | 🔴 High | Sort by time |
| Images | ❌ | 🔴 High | Rich card display |
| Source names | ⚠️ Uses ID | 🟡 Medium | Show "QCU Main" not "qcu1994" |
| Tags | ❌ | 🟡 Medium | Filter by URGENT, ENROLLMENT |

## Display Strategy

```
┌────────────────────────────────┐
│ 🏛️ QCU Main                   │
│ 📅 Yesterday at 12:33 PM       │
│                                │
│ Today marks a milestone...     │
│                                │
│ [THUMBNAIL IMAGE]              │
│                                │
│     [View on Facebook →]       │  ← Links to post_url
└────────────────────────────────┘
```

Posts displayed as preview cards, clicking redirects to Facebook.

## Current Performance

| Scraper | Time/Page | Posts | Status |
|---------|-----------|-------|--------|
| Selenium | ~21s | 6-10 | ✅ Primary |
| Playwright | ~15s | 5-10 | ✅ Backup (faster) |

## Quick Start

```bash
# 1. Activate virtual environment
.venv\Scripts\activate

# 2. Run scraper (interactive mode)
python src/scraper.py

# 3. Or run specific page
python src/scraper.py --page qcu1994 --headless

# 4. Or run all pages
python src/scraper.py --all --headless
```

## Commands

```bash
# Selenium (recommended - more stable)
python src/scraper.py                     # Interactive test
python src/scraper.py -p qcu1994          # Single page
python src/scraper.py --all --headless    # All sources, no browser window

# Playwright (faster - use if Selenium fails)
python src/scraper_playwright.py          # Interactive test
python src/scraper_playwright.py -p qcu1994  # Single page
```

## Setup

### 1. Facebook Cookies

Export your Facebook login cookies:

1. Install "Get cookies.txt LOCALLY" Chrome extension
2. Go to facebook.com (logged in)
3. Click extension → Export
4. Save as `config/facebook_cookies.txt`

### 2. Firebase

1. Go to [Firebase Console](https://console.firebase.google.com)
2. Create project → Create Firestore Database (asia-southeast1)
3. Project Settings → Service Accounts → Generate Key
4. Save as `config/firebase-key.json`

### 3. Sources

Edit `config/sources.json` to add/remove pages to scrape.

## Project Structure

```
├── main.py                    # Entry point (runs all sources)
├── test_scraper.py            # Check setup works
├── src/
│   ├── scraper.py             # Selenium scraper (PRIMARY)
│   ├── scraper_playwright.py  # Playwright scraper (BACKUP)
│   └── database.py            # Firebase operations
├── config/
│   ├── sources.json           # Pages to scrape
│   ├── facebook_cookies.txt   # Your cookies (SECRET)
│   └── firebase-key.json      # Firebase key (SECRET)
├── data/
│   ├── last_stats.json        # Performance stats (Selenium)
│   └── last_stats_playwright.json  # Performance stats (Playwright)
├── GUIDE.md                   # Development guide (detailed)
└── QCU Unified Network.md     # Architecture document
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| No posts found | Export fresh cookies from browser |
| Timeout error | Increase wait times in scraper |
| Facebook blocking | Wait 1-2 hours, try again |
| Firebase error | Check firebase-key.json exists |

## Scale Estimates

| Pages | Selenium | Playwright |
|-------|----------|------------|
| 7 | 2.5 min | 1.7 min |
| 50 | 18 min | 12 min |
| 100 | 36 min | 24 min |

## Note

⚠️ Scraping Facebook violates their ToS. Use responsibly for educational purposes only.

