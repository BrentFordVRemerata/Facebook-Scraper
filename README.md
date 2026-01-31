# 🎓 QCU News Scraper

> **Automated Facebook scraper for Quezon City University announcements**

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![Firebase](https://img.shields.io/badge/Firebase-Firestore-orange.svg)](https://firebase.google.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## 📋 Table of Contents

- [Overview](#overview)
- [System Architecture](#system-architecture)
- [How It Works](#how-it-works)
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [Limitations](#limitations)
- [Contributing](#contributing)

---

## 🎯 Overview

The QCU News Scraper is a Python-based automation tool that:
- **Fetches** announcements from official QCU Facebook pages
- **Processes** and sanitizes the data
- **Tags** content with relevant keywords (Urgent, BSIT, Enrollment, etc.)
- **Uploads** to Firebase Firestore for the QCU Student App

### Part of the QCU Unified Network

```
┌─────────────────────────────────────────────────────────────────────┐
│                     QCU UNIFIED NETWORK                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────────┐    │
│  │   Facebook   │     │   Firebase   │     │  QCU Student     │    │
│  │    Pages     │────▶│   Firestore  │────▶│  Mobile App      │    │
│  └──────────────┘     └──────────────┘     └──────────────────┘    │
│         │                    ▲                                       │
│         ▼                    │                                       │
│  ┌──────────────────────────────────┐                               │
│  │   THIS REPO: qcu-news-scraper    │                               │
│  │   • Fetches posts from FB        │                               │
│  │   • Cleans & sanitizes data      │                               │
│  │   • Tags with keywords           │                               │
│  │   • Uploads to Firestore         │                               │
│  └──────────────────────────────────┘                               │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 🏗️ System Architecture

### High-Level Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           DATA FLOW                                      │
└─────────────────────────────────────────────────────────────────────────┘

    ┌─────────────┐
    │  FACEBOOK   │
    │   PAGES     │
    │  (Public)   │
    └──────┬──────┘
           │
           │ 1. Fetch HTML/JSON
           ▼
    ┌─────────────┐
    │  SCRAPER    │──────────────────────────────┐
    │  MODULE     │                              │
    └──────┬──────┘                              │
           │                                     │
           │ 2. Raw Post Data                    │
           ▼                                     │
    ┌─────────────┐                              │
    │  SANITIZER  │                              │
    │  • Remove emojis                           │
    │  • Fix timestamps                          │
    │  • Clean URLs                              │
    └──────┬──────┘                              │
           │                                     │
           │ 3. Clean Data                       │
           ▼                                     │
    ┌─────────────┐                              │
    │  TAGGER     │                              │
    │  • Detect keywords                         │
    │  • Add tags: [Urgent, BSIT, etc.]         │
    └──────┬──────┘                              │
           │                                     │
           │ 4. Tagged JSON                      │
           ▼                                     │
    ┌─────────────┐                              │
    │  FIREBASE   │◀─────────────────────────────┘
    │  UPLOADER   │   5. Uses Post ID as Doc ID
    │             │      (Prevents duplicates)
    └──────┬──────┘
           │
           │ 6. Realtime Sync
           ▼
    ┌─────────────┐
    │  FIRESTORE  │──────────▶ Flutter App
    │  DATABASE   │
    └─────────────┘
```

### Detailed Process Flowchart

```
                              ┌─────────┐
                              │  START  │
                              └────┬────┘
                                   │
                                   ▼
                        ┌──────────────────────┐
                        │  Load Configuration  │
                        │  • FB Page URLs      │
                        │  • Keywords list     │
                        │  • Firebase creds    │
                        └──────────┬───────────┘
                                   │
                                   ▼
                    ┌──────────────────────────────┐
                    │  For each Facebook Page URL  │◀────────────┐
                    └──────────────┬───────────────┘             │
                                   │                             │
                                   ▼                             │
                        ┌──────────────────┐                     │
                        │  Fetch last 10   │                     │
                        │  posts from page │                     │
                        └────────┬─────────┘                     │
                                 │                               │
                    ┌────────────┴────────────┐                  │
                    │                         │                  │
                    ▼                         ▼                  │
              ┌──────────┐             ┌──────────┐              │
              │ SUCCESS  │             │  FAILED  │              │
              └────┬─────┘             └────┬─────┘              │
                   │                        │                    │
                   │                        ▼                    │
                   │               ┌─────────────────┐           │
                   │               │  Log Error      │           │
                   │               │  "Blocked by    │           │
                   │               │   Facebook"     │           │
                   │               └────────┬────────┘           │
                   │                        │                    │
                   │                        ▼                    │
                   │               ┌─────────────────┐           │
                   │               │  Sleep 2 hours │           │
                   │               │  then retry    │           │
                   │               └────────┬────────┘           │
                   │                        │                    │
                   │◀───────────────────────┘                    │
                   │                                             │
                   ▼                                             │
        ┌──────────────────────┐                                 │
        │  For each post       │◀───────────────────┐            │
        └──────────┬───────────┘                    │            │
                   │                                │            │
                   ▼                                │            │
        ┌──────────────────────┐                    │            │
        │  Check: Post ID      │                    │            │
        │  exists in Firebase? │                    │            │
        └──────────┬───────────┘                    │            │
                   │                                │            │
          ┌───────┴───────┐                        │            │
          │               │                        │            │
          ▼               ▼                        │            │
    ┌──────────┐   ┌──────────┐                    │            │
    │   YES    │   │    NO    │                    │            │
    │ (exists) │   │  (new!)  │                    │            │
    └────┬─────┘   └────┬─────┘                    │            │
         │              │                          │            │
         │              ▼                          │            │
         │     ┌─────────────────┐                 │            │
         │     │  SANITIZE       │                 │            │
         │     │  • Remove junk  │                 │            │
         │     │  • Fix dates    │                 │            │
         │     └────────┬────────┘                 │            │
         │              │                          │            │
         │              ▼                          │            │
         │     ┌─────────────────┐                 │            │
         │     │  TAG POST       │                 │            │
         │     │  • Check for    │                 │            │
         │     │    keywords     │                 │            │
         │     └────────┬────────┘                 │            │
         │              │                          │            │
         │              ▼                          │            │
         │     ┌─────────────────┐                 │            │
         │     │  Upload to      │                 │            │
         │     │  Firebase       │                 │            │
         │     └────────┬────────┘                 │            │
         │              │                          │            │
         │◀─────────────┘                          │            │
         │                                         │            │
         │  SKIP (duplicate)                       │            │
         │                                         │            │
         └────────────────────────────────────────▶│            │
                   │                               │            │
                   │  Next post                    │            │
                   └───────────────────────────────┘            │
                                                                │
                   │  All posts processed                       │
                   ▼                                            │
        ┌──────────────────────┐                                │
        │  Next page           │────────────────────────────────┘
        └──────────────────────┘
                   │
                   │  All pages done
                   ▼
        ┌──────────────────────┐
        │  Sleep 30 minutes    │
        └──────────┬───────────┘
                   │
                   │  Repeat forever
                   └───────────────▶ (back to start)
```

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🔄 **Automated Scraping** | Runs on schedule to fetch new posts |
| 🚫 **Duplicate Prevention** | Uses FB Post ID as Firestore Document ID |
| 🔁 **Reshare Detection** | Content hash comparison to skip cross-posted content |
| 🏷️ **Smart Tagging** | Auto-tags: URGENT, BSIT, ENTREP, BSCE, etc. |
| 📅 **Date Range Filtering** | Scrape from specific date to specific date |
| ➕ **Easy URL Addition** | JSON config - just add new entries |
| 🧹 **Data Sanitization** | Cleans emojis, invalid links, relative timestamps |
| 🛡️ **Error Resilience** | Handles Facebook blocks gracefully |
| 📴 **Offline Fallback** | Admin Portal backup for manual posting |

---

## 🔁 Reshare / Duplicate Detection

One of your key requirements - detecting when `qcu1994` posts something that gets reshared by `qcuplacement`:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    RESHARE DETECTION LOGIC                                   │
└─────────────────────────────────────────────────────────────────────────────┘

    NEW POST ARRIVES
          │
          ▼
    ┌─────────────────────┐
    │ 1. Check Post ID    │──── EXISTS? ───▶ SKIP (exact duplicate)
    │    in Database      │
    └──────────┬──────────┘
               │ NOT FOUND
               ▼
    ┌─────────────────────┐
    │ 2. Generate Hash    │
    │    SHA256(text)     │
    └──────────┬──────────┘
               │
               ▼
    ┌─────────────────────┐
    │ 3. Check Hash       │──── EXISTS? ───▶ RESHARE DETECTED!
    │    in Database      │                        │
    └──────────┬──────────┘                        ▼
               │ NOT FOUND               ┌─────────────────┐
               ▼                         │ Option A: SKIP  │
    ┌─────────────────────┐              │ (don't save)    │
    │ 4. SAVE AS NEW      │              ├─────────────────┤
    │    • Store hash     │              │ Option B: SAVE  │
    │    • is_reshare=F   │              │ but mark as     │
    └─────────────────────┘              │ reshare & link  │
                                         │ to original     │
                                         └─────────────────┘

    EXAMPLE:
    ────────
    08:00 - qcu1994 posts "Classes suspended tomorrow"
            → Saved as NEW, hash="abc123"
    
    08:30 - qcuplacement shares the SAME post
            → Hash "abc123" found in DB
            → SKIPPED (or marked as reshare)
```

---

## 📦 Prerequisites

- **Python 3.8+**
- **pip** (Python package manager)
- **Firebase Project** with Firestore enabled
- **Facebook Cookies** (for private groups only)

---

## 🚀 Installation

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/qcu-news-scraper.git
cd qcu-news-scraper
```

### 2. Create Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Set Up Firebase

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Create a new project or use existing
3. Enable Firestore Database
4. Generate a service account key:
   - Project Settings → Service Accounts → Generate New Private Key
5. Save as `config/firebase_config.json`

---

## ⚙️ Configuration

### Environment Variables

Create a `.env` file:

```env
# Firebase
FIREBASE_PROJECT_ID=your-project-id
GOOGLE_APPLICATION_CREDENTIALS=./config/firebase_config.json

# Scraper Settings
SCRAPE_INTERVAL_MINUTES=30
MAX_POSTS_PER_PAGE=10
RETRY_DELAY_HOURS=2

# Optional: For private groups
FB_COOKIES_PATH=./config/cookies.txt
```

### Facebook Pages Configuration

Create `config/pages.json`:

```json
{
  "settings": {
    "skip_reshares": true,
    "scrape_interval_minutes": 60,
    "max_posts_per_source": 10
  },
  "public_pages": [
    {
      "id": "qcu1994",
      "name": "QCU Main",
      "url": "https://www.facebook.com/qcu1994",
      "enabled": true,
      "priority": 1
    },
    {
      "id": "qcuguidanceunit",
      "name": "QCU Guidance",
      "url": "https://www.facebook.com/qcuguidanceunit",
      "enabled": true,
      "priority": 2
    },
    {
      "id": "qcuregistrar",
      "name": "QCU Registrar",
      "url": "https://www.facebook.com/qcuregistrar",
      "enabled": true,
      "priority": 2
    },
    {
      "id": "QCUPlacement",
      "name": "QCU Placement",
      "url": "https://www.facebook.com/QCUPlacement",
      "enabled": true,
      "priority": 3
    },
    {
      "id": "qcuiskolarcouncil",
      "name": "QCU Iskolar Council",
      "url": "https://www.facebook.com/qcuiskolarcouncil",
      "enabled": true,
      "priority": 3
    },
    {
      "id": "qculibrary",
      "name": "QCU Library",
      "url": "https://www.facebook.com/qculibrary",
      "enabled": true,
      "priority": 3
    },
    {
      "id": "qcutimes",
      "name": "QCU Times",
      "url": "https://www.facebook.com/qcutimes",
      "enabled": true,
      "priority": 3
    }
  ],
  "private_groups": [
    {
      "id": "387936581864052",
      "name": "QCU Group 1",
      "url": "https://www.facebook.com/groups/387936581864052/",
      "enabled": false,
      "requires_cookies": true,
      "notes": "Need to be member to access"
    },
    {
      "id": "391073628062510",
      "name": "QCU Group 2",
      "url": "https://www.facebook.com/groups/391073628062510/",
      "enabled": false,
      "requires_cookies": true
    },
    {
      "id": "1257895282002910",
      "name": "QCU Group 3",
      "url": "https://www.facebook.com/groups/1257895282002910/",
      "enabled": false,
      "requires_cookies": true
    }
  ]
}
```

**To add a new page:** Just add a new entry to the array! Set `enabled: true` when ready.

### Keywords Configuration

Create `config/keywords.json`:

```json
{
  "urgency": {
    "URGENT": ["urgent", "immediately", "asap", "important notice"],
    "SUSPENDED": ["suspended", "suspension", "no classes"],
    "CANCELED": ["canceled", "cancelled", "postponed"]
  },
  "programs": {
    "BSIT": ["BSIT", "BS Information Technology", "IT students", "DCIT"],
    "BSCE": ["BSCE", "Civil Engineering", "CE students"],
    "ENTREP": ["ENTREP", "Entrepreneurship", "business students"],
    "BSBA": ["BSBA", "Business Administration"],
    "BEED": ["BEED", "Elementary Education"],
    "BSED": ["BSED", "Secondary Education"],
    "ALL": ["all students", "all programs", "university-wide"]
  },
  "categories": {
    "ENROLLMENT": ["enrollment", "enroll now", "registration", "admission"],
    "EXAM": ["examination", "midterm", "finals", "quiz", "test"],
    "SCHEDULE": ["schedule", "calendar", "timeline", "deadline"],
    "EVENT": ["event", "seminar", "webinar", "orientation"],
    "SCHOLARSHIP": ["scholarship", "financial aid", "stipend", "allowance"]
  }
}
```

---

## 🎮 Usage

### Run the Scraper

```bash
# Single run
python src/scraper.py

# With scheduler (continuous)
python src/scheduler.py
```

### Test Mode

```bash
# Test scrape without uploading
python src/scraper.py --dry-run
```

---

## 📁 Project Structure

```
qcu-news-scraper/
│
├── 📄 README.md                  # You are here
├── 📄 GUIDE.md                   # AI context & progress tracking
├── 📄 QCU Unified Network.md     # Architecture document
├── 📄 requirements.txt           # Python dependencies
├── 📄 .env.example               # Environment template
├── 📄 .gitignore
│
├── 📂 src/
│   ├── __init__.py
│   ├── main.py                   # Entry point
│   │
│   ├── 📂 scraper/               # Scraping modules
│   │   ├── __init__.py
│   │   ├── base_scraper.py       # Abstract interface
│   │   ├── facebook_scraper.py   # Primary (facebook-scraper lib)
│   │   └── selenium_backup.py    # Backup (if primary fails)
│   │
│   ├── 📂 processors/            # Data processing
│   │   ├── __init__.py
│   │   ├── duplicate_detector.py # Hash-based duplicate check
│   │   ├── sanitizer.py          # Text cleaning
│   │   └── tagger.py             # Keyword detection
│   │
│   ├── 📂 storage/               # Database operations
│   │   ├── __init__.py
│   │   └── firebase_client.py    # Firestore CRUD
│   │
│   └── 📂 utils/                 # Utilities
│       ├── __init__.py
│       ├── config_loader.py      # Load JSON configs
│       └── logger.py             # Logging setup
│
├── 📂 config/
│   ├── pages.json                # FB pages/groups (easy to edit!)
│   ├── keywords.json             # Tagging keywords
│   ├── settings.json             # App settings
│   └── firebase_config.json      # 🔒 GITIGNORED - Firebase creds
│
└── 📂 tests/
    ├── test_scraper.py
    ├── test_duplicate_detector.py
    └── test_tagger.py
```

---

## 📊 Data Schema

Each scraped post is stored in Firebase with this structure:

```json
{
  "post_id": "fb_123456789",
  "content_hash": "sha256_abc123...",
  "title": "Classes Suspended Due to Weather",
  "body": "Full post text here...",
  "source": {
    "id": "qcu1994",
    "name": "QCU Main",
    "url": "https://facebook.com/qcu1994"
  },
  "is_reshare": false,
  "original_post_id": null,
  "timestamp": "2026-02-01T08:00:00Z",
  "scraped_at": "2026-02-01T08:05:00Z",
  "images": ["https://..."],
  "links": ["https://..."],
  "tags": {
    "urgency": ["URGENT", "SUSPENDED"],
    "programs": ["ALL"],
    "categories": ["ANNOUNCEMENT"]
  },
  "meta": {
    "likes": 150,
    "shares": 45,
    "comments_count": 23
  },
  "search_text": "classes suspended due to weather..."
}
```

---

## ⚠️ Limitations & Risks

### Library Health Warning ⚠️

```
┌────────────────────────────────────────────────────────────────────┐
│  facebook-scraper library status:                                  │
│                                                                    │
│  Last Update:    August 2022 (3+ years ago!)                      │
│  Open Issues:    438                                               │
│  Status:         May break when Facebook changes HTML              │
│                                                                    │
│  MITIGATION: Code designed with abstraction layer to swap          │
│              to Selenium/Playwright backup if needed               │
└────────────────────────────────────────────────────────────────────┘
```

### Facebook Scraping Limitations

| Limitation | Impact | Workaround |
|------------|--------|------------|
| **Private Groups** | Cannot access without auth | Use cookies + membership |
| **Rate Limiting** | IP may get blocked | Add delays (1+ hour recommended) |
| **HTML Changes** | Scraper may break | Selenium backup + Admin Portal |
| **Missing Data** | Some fields may be `None` | Handle gracefully in code |
| **Reshares** | Same content appears multiple times | Content hash detection |

### Private Groups Requirement

If scraping **private Facebook groups/communities**:

1. You need a Facebook account that is a **member** of the group
2. Export cookies from browser using:
   - Chrome: [Get cookies.txt LOCALLY](https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc)
   - Firefox: [Cookie Quick Manager](https://addons.mozilla.org/en-US/firefox/addon/cookie-quick-manager/)
3. Save as `config/cookies.txt`
4. Include both `c_user` and `xs` cookies

**⚠️ Warning:** Using automation on private groups may violate Facebook ToS and risk account suspension.

---

## 🔒 Security Notes

- **Never commit** `firebase_config.json` or `cookies.txt`
- Use environment variables for sensitive data
- The scraper only reads from Facebook, never posts
- Firestore rules restrict writes to admin only

---

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 📞 Contact

**Platform Technologies Group - QCU**

For issues and questions, please open a GitHub issue.

---

## 📚 Related Documentation

- [QCU Unified Network Architecture](QCU%20Unified%20Network.md)
- [Development Guide (GUIDE.md)](GUIDE.md)
- [facebook-scraper Documentation](https://github.com/kevinzg/facebook-scraper)
- [Firebase Firestore Docs](https://firebase.google.com/docs/firestore)
