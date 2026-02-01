# QCU Facebook Scraper

**Status:** ✅ Working (Phase 1 Complete)  
**Last Tested:** February 1, 2026  
**Posts Scraped:** 47 from 7 pages in ~2.5 minutes

Scrapes announcements from QCU Facebook pages and saves to Firebase Firestore.

---

## 🚀 Quick Start

```bash
# 1. Activate virtual environment
.venv\Scripts\activate

# 2. Check setup
python test_scraper.py

# 3. Run scraper
python main.py
```

---

## 📊 Current Status

### What Works ✅

| Feature | Status | Notes |
|---------|--------|-------|
| Scrape posts | ✅ | 47 posts from 7 pages |
| Save to Firebase | ✅ | Collection: `posts` |
| Selenium scraper | ✅ | ~20s per page |
| Playwright backup | ✅ | ~15s per page (32% faster) |
| Cookie auth | ✅ | 10 cookies loaded |

### What's Missing ❌

| Feature | Priority | Why Needed |
|---------|----------|------------|
| post_url | 🔴 Critical | "View on Facebook" button |
| posted_at | 🔴 Critical | Sort posts by time |
| images[] | 🔴 Critical | Rich card display |
| source.name | 🟡 High | Show "QCU Main" not "qcu1994" |
| tags | 🟡 Medium | Filter by URGENT, ENROLLMENT |

---

## 📱 Display Strategy

Posts are displayed as preview cards that link to Facebook:

```
┌────────────────────────────────┐
│ 🏛️ QCU Main                   │
│ 📅 Yesterday at 12:33 PM       │
│                                │
│ Today marks a milestone...     │
│                                │
│ [THUMBNAIL IMAGE]              │
│                                │
│     [View on Facebook →]       │
└────────────────────────────────┘
```

---

## ⚡ Performance

| Scraper | Time/Page | Posts | Best For |
|---------|-----------|-------|----------|
| Selenium | ~21s | 6-10 | Daily scraping |
| Playwright | ~15s | 5-10 | Large batches |

### Scale Estimates

| Pages | Selenium | Playwright |
|-------|----------|------------|
| 7 | 2.5 min | 1.7 min |
| 50 | 18 min | 12 min |
| 100 | 36 min | 24 min |

---

## 🔧 Commands

```bash
# Full run (all sources)
python main.py

# Single page test
python src/scraper.py -p qcu1994 --headless

# Playwright (faster)
python src/scraper_playwright.py -p qcu1994

# System check
python test_scraper.py
```

---

## 📁 Project Structure

```
Facebook-Scraper/
├── main.py                 # Entry point - runs all sources
├── test_scraper.py         # System health check
├── requirements.txt        # Dependencies
│
├── src/
│   ├── scraper.py          # Selenium scraper (PRIMARY)
│   ├── scraper_playwright.py # Playwright backup (FASTER)
│   └── database.py         # Firebase operations
│
├── config/
│   ├── sources.json        # Pages to scrape
│   ├── facebook_cookies.txt # Your FB session 🔒
│   └── firebase-key.json   # Firebase credentials 🔒
│
├── data/
│   ├── last_stats.json     # Performance data
│   └── logs/               # (future) Log files
│
├── GUIDE.md                # Development guide (detailed)
└── QCU Unified Network.md  # Architecture document
```

---

## 🔧 Setup

### 1. Python Environment

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Facebook Cookies

1. Install "Get cookies.txt LOCALLY" Chrome extension
2. Go to facebook.com (logged in)
3. Export cookies
4. Save as `config/facebook_cookies.txt`

### 3. Firebase

1. [Firebase Console](https://console.firebase.google.com) → Create project
2. Firestore → Create Database → asia-southeast1
3. Project Settings → Service Accounts → Generate Key
4. Save as `config/firebase-key.json`

---

## 🎯 Target Sources

| # | Page | Status |
|---|------|--------|
| 1 | QCU Main | ✅ 6 posts |
| 2 | QCU Registrar | ✅ 10 posts |
| 3 | QCU Guidance | ✅ 3 posts |
| 4 | QCU Placement | ✅ 10 posts |
| 5 | QCU Iskolar Council | ✅ 8 posts |
| 6 | QCU Library | ✅ 0 posts |
| 7 | QCU Times | ✅ 10 posts |

---

## 🔥 Troubleshooting

| Problem | Solution |
|---------|----------|
| No posts found | Export fresh cookies from browser |
| Timeout error | Increase wait times in scraper |
| Facebook blocking | Wait 1-2 hours, try again |
| Firebase error | Check firebase-key.json exists |

---

## 📚 Documentation

| Document | Purpose |
|----------|---------|
| [GUIDE.md](GUIDE.md) | Detailed development guide |
| [QCU Unified Network.md](QCU%20Unified%20Network.md) | Full architecture |

---

## ⚠️ Legal Notice

Scraping Facebook may violate their ToS. This project is for **educational purposes only**:
- Non-commercial use
- Links back to original posts
- Rate-limited to avoid spam
- No data resale

---

*Phase 1 complete. Next: Extract post URLs, dates, and images.*

