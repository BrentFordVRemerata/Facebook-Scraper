# 📚 QCU Facebook Scraper - Development Guide

> **Purpose:** This document serves as the living context for AI assistants and developers working on this project. It tracks progress, decisions, and implementation details.

**Last Updated:** February 1, 2026  
**Current Phase:** Planning & Architecture (Deep Dive)

---

## 📋 Table of Contents

1. [Project Overview](#project-overview)
2. [Is This Project Worth Building?](#is-this-project-worth-building)
3. [Target Facebook Sources](#target-facebook-sources)
4. [Core Requirements](#core-requirements)
5. [Technical Architecture](#technical-architecture)
6. [Duplicate & Reshare Detection](#duplicate--reshare-detection)
7. [Private Groups Strategy](#private-groups-strategy)
8. [Firebase Setup Guide](#firebase-setup-guide)
9. [Current Progress](#current-progress)
10. [Risk Assessment](#risk-assessment)
11. [Session History](#session-history)

---

## 🎯 Project Overview

### What is this project?
A **flexible, scalable** Python-based scraper that:
- Fetches announcements from multiple QCU Facebook pages/groups
- Supports dynamic addition of new sources
- Filters by date ranges
- Detects and skips duplicate/reshared content
- Tags posts with keywords (URGENT, BSIT, ENTREP, etc.)
- Uploads to Firebase for the QCU Student Mobile App

### Why does it exist?
University announcements are **fragmented across 10+ Facebook pages** (and growing). Students miss important information because they can't follow everything. This centralizes all announcements into one searchable, filterable feed.

### Who maintains it?
- **Lead Architect:** Brent Ford V. Remerata
- **Team:** Platform Technologies Group

---

## 🤔 Is This Project Worth Building?

### ✅ YES - Here's Why:

| Reason | Explanation |
|--------|-------------|
| **Real Problem** | Students genuinely miss announcements scattered across 10+ pages |
| **No Existing Solution** | QCU doesn't have a unified notification system |
| **Scalable Impact** | Benefits thousands of students across all programs |
| **Learning Value** | Teaches web scraping, Firebase, API design, Flutter integration |
| **Portfolio Project** | Demonstrates real-world problem solving |
| **Low Cost** | Firebase free tier is sufficient; no server costs if using GitHub Actions |

### ⚠️ Challenges to Consider:

| Challenge | Severity | Mitigation |
|-----------|----------|------------|
| **facebook-scraper is outdated** | HIGH | Has 438 open issues, last update Aug 2022. May break anytime. |
| **Facebook actively blocks scrapers** | HIGH | Need to use cookies, realistic delays, handle blocks gracefully |
| **Private groups need membership** | MEDIUM | Need dedicated account that's a member |
| **Maintenance burden** | MEDIUM | When FB changes HTML, scraper breaks. Need ongoing fixes. |
| **Terms of Service** | LOW-MEDIUM | Scraping violates FB ToS technically, but for educational/non-commercial use, risk is account suspension not legal action |

### 🎯 My Honest Recommendation:

**BUILD IT, but with a hybrid approach:**

1. **Phase 1:** Build scraper for PUBLIC pages (7 pages you listed) - LOW RISK
2. **Phase 2:** Add private groups with cookies - MEDIUM RISK  
3. **Phase 3:** Build Admin Portal as backup - NO RISK (manual fallback)
4. **Future:** Consider official channels (contact QCU IT for RSS feeds or API access)

**Alternative to Consider:** Have you checked if QCU pages have RSS feeds? Some Facebook pages still expose them at `facebook.com/page/rss` - this would be more reliable than scraping.

---

## 🎯 Target Facebook Sources

### PUBLIC Pages (7 confirmed) - Can scrape without login

| # | Name | URL | Type | Status |
|---|------|-----|------|--------|
| 1 | QCU Main | https://www.facebook.com/qcu1994 | Page | ✅ Public |
| 2 | QCU Guidance | https://www.facebook.com/qcuguidanceunit | Page | ✅ Public |
| 3 | QCU Registrar | https://www.facebook.com/qcuregistrar | Page | ✅ Public |
| 4 | QCU Placement | https://www.facebook.com/QCUPlacement | Page | ✅ Public |
| 5 | QCU Iskolar Council | https://www.facebook.com/qcuiskolarcouncil | Page | ✅ Public |
| 6 | QCU Library | https://www.facebook.com/qculibrary | Page | ✅ Public |
| 7 | QCU Times | https://www.facebook.com/qcutimes | Page | ✅ Public |

### PRIVATE Groups (3 confirmed) - Need cookies + membership

| # | Name | URL | Type | Status |
|---|------|-----|------|--------|
| 8 | Group 1 | https://www.facebook.com/groups/387936581864052/ | Group | 🔒 Private |
| 9 | Group 2 | https://www.facebook.com/groups/391073628062510/ | Group | 🔒 Private |
| 10 | Group 3 | https://www.facebook.com/groups/1257895282002910/ | Group | 🔒 Private |

### Future Sources (To Be Added)
- BSIT-specific pages
- ENTREP-specific pages
- BSCE-specific pages
- Other department pages
- *(System designed to easily add more)*

---

## 📋 Core Requirements

### Flexibility Requirements

| Requirement | Implementation |
|-------------|----------------|
| **Easy to add new URLs** | JSON config file - just add new entry |
| **Date range filtering** | `start_date` and `end_date` parameters |
| **Keyword filtering** | Configurable keyword lists in JSON |
| **Skip reshares** | Content hash comparison + source tracking |
| **Skip duplicates** | Post ID as document ID + text similarity check |
| **Searchable/Filterable** | Firestore indexes + proper data structure |
| **Program-specific tags** | Auto-detect: BSIT, ENTREP, BSCE, etc. |

### Data Model (Flexible Schema)

```json
{
  "post_id": "fb_123456789",
  "content_hash": "sha256_of_text",
  "title": "Classes Suspended",
  "body": "Full post text...",
  "source": {
    "name": "QCU Main",
    "url": "https://facebook.com/qcu1994",
    "type": "page"
  },
  "original_source": {
    "post_id": "fb_987654321",
    "name": "QCU Registrar"
  },
  "is_reshare": false,
  "timestamp": "2026-02-01T08:00:00Z",
  "scraped_at": "2026-02-01T08:05:00Z",
  "images": ["url1", "url2"],
  "links": ["url1"],
  "tags": {
    "urgency": ["URGENT", "SUSPENDED"],
    "programs": ["BSIT", "ALL"],
    "categories": ["Announcement", "Schedule"],
    "custom": []
  },
  "meta": {
    "likes": 150,
    "shares": 45,
    "comments_count": 23,
    "status": "active"
  },
  "search_text": "lowercased concatenated searchable text"
}
```

---

## 🏗️ Technical Architecture

### System Flowchart (Comprehensive)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    QCU NEWS SCRAPER - FULL ARCHITECTURE                      │
└─────────────────────────────────────────────────────────────────────────────┘

                    ┌──────────────────────────────────────┐
                    │          CONFIGURATION               │
                    │  ┌──────────┐  ┌──────────────────┐ │
                    │  │pages.json│  │keywords.json     │ │
                    │  │ - URLs   │  │ - URGENT words   │ │
                    │  │ - Types  │  │ - Program tags   │ │
                    │  │ - Names  │  │ - Categories     │ │
                    │  └──────────┘  └──────────────────┘ │
                    └───────────────┬──────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              SCRAPER ENGINE                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐      │
│   │  PUBLIC PAGES   │     │  PRIVATE GROUPS │     │   DATE FILTER   │      │
│   │  (No auth)      │     │  (With cookies) │     │  (start - end)  │      │
│   └────────┬────────┘     └────────┬────────┘     └────────┬────────┘      │
│            │                       │                       │                │
│            └───────────┬───────────┴───────────────────────┘                │
│                        │                                                     │
│                        ▼                                                     │
│            ┌───────────────────────┐                                        │
│            │    FETCH POSTS        │                                        │
│            │  (facebook-scraper)   │                                        │
│            └───────────┬───────────┘                                        │
│                        │                                                     │
└────────────────────────┼────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           PROCESSING PIPELINE                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐ │
│   │             │    │             │    │             │    │             │ │
│   │  1. CHECK   │───▶│  2. CHECK   │───▶│  3. CLEAN   │───▶│  4. TAG     │ │
│   │  DUPLICATE  │    │  RESHARE    │    │  SANITIZE   │    │  CLASSIFY   │ │
│   │             │    │             │    │             │    │             │ │
│   │ • Post ID   │    │ • Hash text │    │ • Emojis    │    │ • URGENT    │ │
│   │ • In DB?    │    │ • Compare   │    │ • Links     │    │ • BSIT      │ │
│   │             │    │ • Original? │    │ • Dates     │    │ • ENTREP    │ │
│   └──────┬──────┘    └──────┬──────┘    └─────────────┘    └─────────────┘ │
│          │                  │                                               │
│          ▼                  ▼                                               │
│    ┌──────────┐       ┌──────────┐                                         │
│    │  SKIP    │       │  MARK AS │                                         │
│    │(duplicate)│       │  RESHARE │                                         │
│    └──────────┘       │ Link to  │                                         │
│                       │ Original │                                         │
│                       └──────────┘                                         │
│                                                                              │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FIREBASE UPLOAD                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   Collection: announcements/{post_id}                                       │
│                                                                              │
│   ┌─────────────────────────────────────────────────────────────────┐       │
│   │  INDEXES (for fast queries):                                     │       │
│   │  • timestamp (for date range queries)                            │       │
│   │  • tags.programs (for BSIT, ENTREP filters)                      │       │
│   │  • tags.urgency (for URGENT filter)                              │       │
│   │  • source.name (for source filter)                               │       │
│   │  • search_text (for full-text search)                            │       │
│   └─────────────────────────────────────────────────────────────────┘       │
│                                                                              │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                                   ▼
                    ┌──────────────────────────────────┐
                    │         FLUTTER APP              │
                    │  • Realtime sync                 │
                    │  • Offline cache                 │
                    │  • Filter by tag/date/source    │
                    │  • Search functionality          │
                    └──────────────────────────────────┘
```

### Duplicate & Reshare Detection Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    DUPLICATE & RESHARE DETECTION                             │
└─────────────────────────────────────────────────────────────────────────────┘

                         ┌─────────────────┐
                         │  NEW POST FROM  │
                         │  qcuplacement   │
                         └────────┬────────┘
                                  │
                                  ▼
                    ┌─────────────────────────┐
                    │ STEP 1: Check Post ID   │
                    │ Does fb_123 exist in DB?│
                    └────────────┬────────────┘
                                 │
                    ┌────────────┴────────────┐
                    │                         │
                    ▼                         ▼
              ┌──────────┐             ┌──────────┐
              │   YES    │             │    NO    │
              │ (exists) │             │  (new!)  │
              └────┬─────┘             └────┬─────┘
                   │                        │
                   ▼                        ▼
              ┌──────────┐     ┌─────────────────────────┐
              │   SKIP   │     │ STEP 2: Generate Hash   │
              │ Duplicate│     │ hash = sha256(text)     │
              └──────────┘     └────────────┬────────────┘
                                            │
                                            ▼
                               ┌─────────────────────────┐
                               │ STEP 3: Check if hash   │
                               │ exists in DB            │
                               └────────────┬────────────┘
                                            │
                               ┌────────────┴────────────┐
                               │                         │
                               ▼                         ▼
                         ┌──────────┐             ┌──────────┐
                         │   YES    │             │    NO    │
                         │ (reshare)│             │(original)│
                         └────┬─────┘             └────┬─────┘
                              │                        │
                              ▼                        ▼
                    ┌──────────────────┐     ┌──────────────────┐
                    │  SAVE AS RESHARE │     │  SAVE AS NEW     │
                    │  • is_reshare=T  │     │  • is_reshare=F  │
                    │  • Link original │     │  • Calculate hash│
                    │  OR SKIP entirely│     │  • Store hash    │
                    └──────────────────┘     └──────────────────┘

    ┌─────────────────────────────────────────────────────────────────────┐
    │  EXAMPLE:                                                            │
    │                                                                      │
    │  1. QCU Main (qcu1994) posts: "Classes suspended tomorrow"          │
    │     → Saved as NEW, hash = "abc123"                                  │
    │                                                                      │
    │  2. QCU Placement shares the same post                               │
    │     → Same text detected (hash match)                                │
    │     → Option A: Skip entirely (don't save duplicate)                │
    │     → Option B: Save but mark as reshare, link to original          │
    │                                                                      │
    │  USER CONFIG: "skip_reshares": true/false                           │
    └─────────────────────────────────────────────────────────────────────┘
```

---

## 🔒 Private Groups Strategy

### How Private Facebook Groups Work

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    PRIVATE GROUP ACCESS EXPLAINED                            │
└─────────────────────────────────────────────────────────────────────────────┘

    PUBLIC PAGE                           PRIVATE GROUP
    ────────────                          ─────────────
    
    ┌─────────────┐                       ┌─────────────┐
    │  Facebook   │                       │  Facebook   │
    │    Page     │                       │    Group    │
    │             │                       │             │
    │  ◯ Anyone   │                       │  🔒 Members │
    │   can see   │                       │    only     │
    └─────────────┘                       └─────────────┘
          │                                     │
          ▼                                     ▼
    ┌─────────────┐                       ┌─────────────┐
    │  Scraper    │                       │  Scraper    │
    │  (no login) │                       │  needs:     │
    │             │                       │  • Cookies  │
    │   ✅ WORKS  │                       │  • Account  │
    │             │                       │    that is  │
    └─────────────┘                       │    MEMBER   │
                                          └─────────────┘
                                                │
                                                ▼
                                     ┌───────────────────┐
                                     │  COOKIE PROCESS:  │
                                     │                   │
                                     │  1. Login to FB   │
                                     │     in browser    │
                                     │                   │
                                     │  2. Join groups   │
                                     │     manually      │
                                     │                   │
                                     │  3. Export cookies│
                                     │     (extension)   │
                                     │                   │
                                     │  4. Give cookies  │
                                     │     to scraper    │
                                     └───────────────────┘
```

### Private Group Options

| Option | Pros | Cons | Recommendation |
|--------|------|------|----------------|
| **A. Skip private groups** | No risk, simple | Miss some announcements | ✅ Start here |
| **B. Use your personal account** | Easy setup | Risk account suspension | ⚠️ Not recommended |
| **C. Create dedicated "bot" account** | Separates risk | Still might get banned | 🤔 Medium risk |
| **D. Admin Portal manual entry** | Zero risk | Manual work | ✅ Best backup |
| **E. Ask group admins to cross-post to public page** | Sustainable | Requires coordination | ✅ Long-term solution |

### Cookie Setup (If You Choose Option B or C)

```bash
# Step 1: Install browser extension
# Chrome: "Get cookies.txt LOCALLY"
# Firefox: "Cookie Quick Manager"

# Step 2: Login to Facebook with your account

# Step 3: Make sure account is MEMBER of all target groups

# Step 4: Export cookies to: config/cookies.txt

# Step 5: Verify cookies include:
# - c_user (your user ID)
# - xs (session token)
```

---

## 🔥 Firebase Setup Guide

### Step-by-Step Setup

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         FIREBASE SETUP STEPS                                 │
└─────────────────────────────────────────────────────────────────────────────┘

    STEP 1: Create Project
    ──────────────────────
    
    1. Go to: https://console.firebase.google.com/
    2. Click "Create Project" (or select existing)
    3. Name: "qcu-news-app" (or similar)
    4. Disable Google Analytics (optional, not needed)
    5. Click "Create"
    
    
    STEP 2: Enable Firestore
    ────────────────────────
    
    1. In Firebase Console, click "Build" → "Firestore Database"
    2. Click "Create Database"
    3. Choose "Start in TEST MODE" (for development)
       ⚠️ Change to production rules before launch!
    4. Select region: asia-southeast1 (Singapore) for Philippines
    5. Click "Enable"
    
    
    STEP 3: Generate Service Account Key (for Python)
    ─────────────────────────────────────────────────
    
    1. Click ⚙️ gear icon → "Project Settings"
    2. Go to "Service Accounts" tab
    3. Click "Generate New Private Key"
    4. Save as: config/firebase_config.json
    5. ⚠️ NEVER commit this file to Git!
    
    
    STEP 4: Create Firestore Indexes
    ────────────────────────────────
    
    In Firestore Console → Indexes → Add Index:
    
    Index 1: Date Range + Source
    - Collection: announcements
    - Fields: timestamp (Descending), source.name (Ascending)
    
    Index 2: Tag Filtering  
    - Collection: announcements
    - Fields: tags.programs (Array Contains), timestamp (Descending)
    
    Index 3: Urgency Filter
    - Collection: announcements
    - Fields: tags.urgency (Array Contains), timestamp (Descending)
```

### Firestore Security Rules (Production)

```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Announcements collection
    match /announcements/{postId} {
      // Anyone can read (students don't need login)
      allow read: if true;
      
      // Only admin (scraper with service account) can write
      allow write: if request.auth != null && request.auth.token.admin == true;
    }
    
    // Config collection (for app settings)
    match /config/{docId} {
      allow read: if true;
      allow write: if false; // Only via Admin SDK
    }
  }
}
```

---

## 📊 Current Progress

### Phase Status

```
[✓] Phase 1: Initial Research
[✓] Phase 2: Requirements Gathering (THIS SESSION)
[▶] Phase 3: Detailed Planning & Architecture
[ ] Phase 4: Environment Setup
[ ] Phase 5: Core Scraper Development
[ ] Phase 6: Processing Pipeline (Duplicates, Tagging)
[ ] Phase 7: Firebase Integration
[ ] Phase 8: Testing
[ ] Phase 9: Scheduler Setup
[ ] Phase 10: Deployment
```

### Completed This Session
- [x] Identified 7 public pages + 3 private groups
- [x] Defined flexibility requirements
- [x] Designed duplicate/reshare detection system
- [x] Created comprehensive data model
- [x] Documented Firebase setup steps
- [x] Analyzed project viability (YES, worth building)

### Decisions Made
- [x] Start with PUBLIC pages only (Phase 1)
- [x] Private groups as Phase 2 (with cookies)
- [x] Admin Portal as backup (Phase 3 - separate repo)
- [x] Skip reshares by default (configurable)
- [x] Use content hash for duplicate detection

### Pending Decisions
- [ ] Hosting: GitHub Actions (free) vs Cloud Functions vs VPS?
- [ ] Scraping frequency: 30 mins vs 1 hour vs on-demand?
- [ ] Store images locally or just URLs?
- [ ] Include comments or just post content?

---

## ⚠️ Risk Assessment

### Library Health Warning

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  ⚠️  CRITICAL: facebook-scraper LIBRARY STATUS                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Last Update: August 2022 (3.5 years ago!)                                  │
│  Open Issues: 438                                                            │
│  Recent Issues:                                                              │
│    • "Example Scrape does not return any posts" (Oct 2025)                  │
│    • "FB using JS to load content now" (Oct 2024)                           │
│    • "get_posts returns nothing" (May 2024)                                 │
│    • "Login is required" (Oct 2024)                                         │
│                                                                              │
│  RISK: Library may stop working at any time when Facebook changes HTML      │
│                                                                              │
│  MITIGATION:                                                                 │
│    1. Build abstraction layer (can swap scraping method)                    │
│    2. Have Selenium backup ready                                            │
│    3. Admin Portal as manual fallback                                        │
│    4. Monitor for library updates/forks                                      │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Alternative Scraping Methods

| Method | Reliability | Complexity | Cost |
|--------|-------------|------------|------|
| **facebook-scraper** | LOW (may break) | LOW | Free |
| **Selenium + Chrome** | MEDIUM | MEDIUM | Free (but slow) |
| **Playwright** | MEDIUM-HIGH | MEDIUM | Free |
| **Apify Facebook Scraper** | HIGH | LOW | Paid ($49+/mo) |
| **Official Graph API** | HIGH | HIGH | Free (but limited access) |

**Recommendation:** Start with `facebook-scraper`, but design code to easily swap to Selenium/Playwright if needed.

---

## 📅 Session History

### Session 2 - February 1, 2026 (Current)

**Context:** Deep dive into requirements and planning

**User Provided:**
- 7 public Facebook pages
- 3 private Facebook groups
- Requirements for flexibility, date filtering, reshare detection
- Firebase account exists but not configured
- Keywords: URGENT, SUSPENDED, CANCELED, BSIT, ENTREP, BSCE

**Key Discussions:**
1. **Is it worth building?** → YES, with hybrid approach
2. **Private groups** → Need cookies + membership, start with public pages
3. **Reshare detection** → Content hash comparison
4. **Library concerns** → 438 open issues, may break, need backup plan

**Decisions Made:**
- Phased approach (public → private → admin portal)
- Content hashing for duplicate detection
- Flexible JSON config for easy URL additions
- Firebase in asia-southeast1 region

**Next Steps:**
1. ✅ Update GUIDE.md with all requirements (DONE)
2. User to review flowcharts and architecture
3. User to set up Firebase project
4. If approved, proceed to environment setup

---

### Session 1 - February 1, 2026

**Context:** Initial project setup and planning

**What was discussed:**
- Reviewed QCU Unified Network architecture document
- Researched facebook-scraper library capabilities
- Created initial README.md and GUIDE.md

---

## ❓ Questions for User Before Proceeding

1. **Reshare Handling:** Skip reshares entirely, or save them but mark as reshares?

2. **Scraping Frequency:** 
   - Every 30 minutes (more fresh, more risk of blocking)
   - Every 1 hour (balanced)
   - Every 2 hours (safer)
   
3. **Historical Data:** Should we scrape old posts (e.g., last 6 months) or only new posts going forward?

4. **Images:** Store image URLs only, or download and store images in Firebase Storage?

5. **Comments:** Include comments in scraped data, or just main post content?

6. **Hosting Preference:**
   - GitHub Actions (free, runs on schedule)
   - Google Cloud Functions (serverless)
   - Your own PC (local scheduler)

---

## 🔗 Quick Reference

### Target URLs Summary

```
PUBLIC PAGES (scrape first):
├── qcu1994
├── qcuguidanceunit
├── qcuregistrar
├── QCUPlacement
├── qcuiskolarcouncil
├── qculibrary
└── qcutimes

PRIVATE GROUPS (phase 2):
├── groups/387936581864052
├── groups/391073628062510
└── groups/1257895282002910
```

### Keyword Tags

```json
{
  "urgency": ["URGENT", "SUSPENDED", "CANCELED", "CANCELLED", "IMPORTANT", "EMERGENCY"],
  "programs": ["BSIT", "BSCE", "ENTREP", "BSBA", "BEED", "BSED", "ALL"],
  "categories": ["ENROLLMENT", "EXAM", "SCHEDULE", "EVENT", "SCHOLARSHIP", "ANNOUNCEMENT"]
}
```

### Project File Structure (Updated)

```
qcu-news-scraper/
├── README.md
├── GUIDE.md                      # This file
├── QCU Unified Network.md
├── requirements.txt
├── .env.example
├── .gitignore
│
├── src/
│   ├── __init__.py
│   ├── main.py                   # Entry point
│   ├── scraper/
│   │   ├── __init__.py
│   │   ├── facebook_scraper.py   # Primary scraper
│   │   ├── selenium_backup.py    # Backup scraper
│   │   └── base_scraper.py       # Abstract interface
│   ├── processors/
│   │   ├── __init__.py
│   │   ├── duplicate_detector.py
│   │   ├── sanitizer.py
│   │   └── tagger.py
│   ├── storage/
│   │   ├── __init__.py
│   │   └── firebase_client.py
│   └── utils/
│       ├── __init__.py
│       ├── config_loader.py
│       └── logger.py
│
├── config/
│   ├── pages.json                # FB pages/groups to scrape
│   ├── keywords.json             # Tagging keywords
│   ├── settings.json             # App settings
│   └── firebase_config.json      # 🔒 GITIGNORED
│
└── tests/
    ├── test_scraper.py
    ├── test_duplicate_detector.py
    └── test_tagger.py
```
