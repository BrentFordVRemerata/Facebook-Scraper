# QCU Facebook Announcement Scraper

> **Project Classification:** Academic Proof of Concept / University-Related Project Prototype  
> **Status:** ⚠️ Inactive / Historical Research Prototype (Last developed: February 1, 2026; Recovered & Audited: November 2026)  
> **Target Audience:** Quezon City University (QCU) Project Reviewers, Educational Researchers, and Open-Source Auditors  

---

## 📌 Executive Summary

The **QCU Facebook Announcement Scraper** was initiated as part of a university-related student project aimed at solving announcement fragmentation at Quezon City University (QCU). Official campus announcements are distributed across more than ten distinct Facebook Pages and Groups (e.g., Main Campus, Office of the Registrar, Guidance and Placement Offices, Student Councils, and Campus Journalism outlets), causing students to frequently miss urgent academic advisories.

The backend prototype in this repository explored automated collection of public page announcements using browser automation (Selenium and Playwright) and storage in Google Firebase Firestore to serve a prospective student mobile feed.

**Important Notice:** The student mobile application was never completed, and this repository is **not** a production-ready application. It is preserved for academic review and technical evaluation under strict platform compliance boundaries.

---

## 📊 Implementation Status & Verification Matrix

To ensure transparency and prevent misrepresentation of capabilities, the project features are classified across four verification tiers:

| Component / Feature | Classification | Technical Status & Limitations |
|---------------------|----------------|--------------------------------|
| **Selenium Scraper** (`src/scraper.py`) | **Historically Implemented & Tested** | Verified locally in Feb 2026; collects rendered text blocks via headless Chrome. Requires Chrome & chromedriver. |
| **Playwright Scraper** (`src/scraper_playwright.py`) | **Historically Implemented & Tested** | Verified locally in Feb 2026; alternative browser engine using `domcontentloaded` waits. |
| **Firestore Batch Persistence** (`src/database.py`) | **Historically Implemented & Tested** | Batches writes up to 500 documents with SHA-256 content deduplication into the `posts` collection. |
| **Offline Fixture Pipeline** (`main.py --offline`) | **Tested & Verified (Nov 2026)** | 100% offline pipeline execution using local text fixtures (`tests/fixtures/sample_page_text.txt`) with zero browser launch, zero network access, and zero external credentials. |
| **Automated Unit Test Suite** (`tests/`) | **Tested & Verified (Nov 2026)** | 31 passing offline unit tests covering text extraction, SHA-256 deduplication, legacy post ID migration, config validation, and mock database persistence. |
| **Live Facebook Scraping (Current)** | **Implemented but Not Currently Verified** | Facebook frequently alters its DOM tree, class naming obfuscations, and anti-scraping defenses. Historical scraping routines may encounter login gates, layout shifts, or bot detection. |
| **Cookie Authentication** (`config/facebook_cookies.txt`) | **Implemented but Not Currently Verified** | Netscape cookie injection supported in code, but carries critical session-invalidation and account suspension risks. |
| **Post Permalinks (`post_url`)** | **Incomplete / Non-functional** | **Not extracted.** The scraper collects raw text blocks and does not reliably identify permalink anchor tags. |
| **Publication Timestamps (`posted_at`)** | **Incomplete / Non-functional** | **Not extracted.** The scraper only records the retrieval timestamp (`scraped_at`), not the actual Facebook post creation date. |
| **Image Extraction & Hosting (`images[]`)** | **Incomplete / Non-functional** | **Not extracted.** No media downloading, compression, thumbnailing, or Firebase Storage uploads exist in code. |
| **Automated Scheduler** | **Incomplete / Non-functional** | No cron daemon, background worker, or retry scheduler exists in the repository. Execution is manual via CLI. |
| **Mobile Student Application** | **Planned Only** | Conceptually proposed (`qcu-student-app`), but no mobile frontend code was ever developed. |
| **NLP Keyword Tagging & Urgency Tagger** | **Planned Only** | Defined in `config/keywords.json` and planning documents, but no NLP processing module is hooked into the pipeline. |
| **Multi-Channel Alerts (Discord, Telegram, SMTP)**| **Planned Only** | Stated in architectural concepts and settings templates, but no notification webhooks or mailers are implemented. |

---

## 🏗️ Architecture & Data Flow

```
┌─────────────────────────────────┐
│     Public Facebook Pages       │
│  (QCU Main, Registrar, etc.)    │
└────────────────┬────────────────┘
                 │
                 ▼ Headless Browser Automation (Selenium / Playwright)
┌─────────────────────────────────┐
│       DOM Text Extraction       │
│  - Line chunking & cleanup      │
│  - UI chrome filtering          │
│  - Full text SHA-256 hashing    │
└────────────────┬────────────────┘
                 │
                 ▼ Normalized Post Schema (with legacy ID migration tracking)
┌─────────────────────────────────┐
│    Firebase Admin SDK Batch     │
│  - Per-source deduplication     │
│  - Legacy post ID verification  │
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│   Google Firebase Firestore     │
│   (Collection: "posts")         │
└─────────────────────────────────┘
```

### Standardized Post Schema & Migration Compatibility

Each processed announcement record conforms to the following schema:

```json
{
  "post_id": "qcu1994_a1b2c3d4e5f6",
  "legacy_post_id": "qcu1994_42ef9169",
  "source_id": "qcu1994",
  "source_name": "QCU Main",
  "title": "ADVISORY ON MIDTERM EXAMINATIONS",
  "text": "Full announcement text extracted from rendered DOM blocks...",
  "body": "Full announcement text (alias for text)...",
  "content_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "scraped_at": "2026-11-10T14:00:00.000000+00:00",
  "updated_at": "2026-11-10T14:00:05.000000+00:00"
}
```

#### Migration Note on Post IDs
Original prototype commits generated post IDs using an 8-character MD5 hash of only the first 100 characters (`f"{source_id}_{md5(block[:100])[:8]}"`), which caused collisions when announcements shared university letterheads. The updated parser generates deterministic 12-character SHA-256 IDs over the full normalized text (`f"{source_id}_{sha256(text)[:12]}"`). 

To prevent duplicating existing documents when running against a database populated by the legacy scraper, `src/parser.py` records `legacy_post_id`, and `src/database.py` checks for the presence of the legacy ID before writing.

#### Cross-Source Deduplication
By default (`cross_source_dedup=False`), deduplication is scoped per-source `(source_id, content_hash)`. This ensures each campus unit (e.g. Registrar vs Student Council) retains its announcement in its respective feed even if both post identical text. Setting `cross_source_dedup=True` discards cross-source reshares globally.

---

## ⚠️ Legal, Ethical & Platform Compliance Disclosures

### 1. Meta Terms of Service (ToS)
Section 3.2.3 of Meta's Terms of Service explicitly states that users must not *"access or collect data from our Products using automated means (without our prior permission) or attempt to access data you do not have permission to access."*

Historical documentation in this project suggested that non-commercial educational use or linking back to Facebook provides legal exemption. **This is inaccurate.** While legal precedents (such as *hiQ Labs v. LinkedIn*) recognized that scraping public web data does not violate the US Computer Fraud and Abuse Act (CFAA), platforms enforce contractual Terms of Service and technical anti-bot countermeasures vigorously.

### 2. Account Security & Session Risks
Automating Facebook browsing using personal accounts or session cookies (`c_user`, `xs`) presents severe security and privacy hazards:
- **Account Termination:** Meta's automated abuse detection detects non-human browsing velocity and triggers checkpoints or permanent account bans.
- **Session Hijacking:** Exported browser cookies contain complete account access. Anyone with access to the cookie file can act as the logged-in user.

### 3. Scalability Reality
Early project notes suggested scaling sequential scraping to 50–100 pages. In practice:
- Browser automation consumes significant memory (~300–500 MB RAM per browser process).
- Sequential scraping at 15–25 seconds per page takes 25–40 minutes for 100 pages, easily triggering rate limits or temporary IP blocks from Facebook edge nodes.

---

## 🛠️ Local Environment & Reproducible Setup

Setup and testing can be completed **completely offline without live Facebook accounts, browser drivers, or Firebase credentials**.

### Prerequisites
- Python 3.10, 3.11, or 3.12
- Google Chrome & chromedriver (only required if running live Selenium scraping)

### 1. Clone & Set Up Virtual Environment

```bash
git clone https://github.com/BrentFordVRemerata/Facebook-Scraper.git
cd Facebook-Scraper

python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment Template

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

`src/config.py` automatically detects and parses `.env` on startup (using `python-dotenv` if installed, with a built-in fallback parser if not).

### 3. Run Automated Unit Tests

Run the offline unit test suite (31 tests, completes in ~0.01s with zero network access):

```bash
python3 -m unittest discover -s tests -p "test_*.py" -v
```

### 4. Verify System & Environment Diagnostics

Validate local configuration syntax and dependency presence:

```bash
python3 test_scraper.py
```

### 5. Execute Pipeline Modes

The CLI supports two distinct operational modes:

#### A. Genuine Offline Fixture Mode (Zero Browser, Zero Network)
Ideal for testing parsing, deduplication, and schema validation safely:

```bash
# Parses local announcement fixture without launching browsers or accessing the internet
python3 main.py --offline --dry-run
```

#### B. Live Scraping Mode (Requires Browser & Internet Access)
Runs browser automation against public Facebook pages:

```bash
# Scrape live pages in headless mode without saving to Firebase
python3 main.py --source qcu1994 --name "QCU Main" --max-posts 3 --dry-run

# Scrape all configured sources and persist to Firebase (requires config/firebase-key.json)
python3 main.py
```

*Note on `--dry-run`: `--dry-run` prevents writing documents to Firestore. When used alone, it still launches browser automation against live web targets. To avoid all network and browser calls, always use `--offline`.*

---

## 🔒 Security Practices

- **Never Commit Secrets:** Service account keys (`config/firebase-key.json`) and exported cookies (`config/facebook_cookies.txt`) are excluded in `.gitignore`.
- **Debug Dumps Disabled:** The scraper does **not** write raw HTML snapshots to disk unless explicitly invoked with `--save-debug`.
- For full security disclosures and vulnerability reporting procedures, review [SECURITY.md](SECURITY.md).

---

## ⚖️ Software Licensing Review

This repository is currently **unlicensed** (all rights reserved by the original authors). 

Before applying an open-source license, the repository owner and Quezon City University project stakeholders should evaluate the following options and intellectual property implications:

| License | Grant & Permissions | Requirements & Obligations | Suitability & Considerations |
|---------|---------------------|----------------------------|-----------------------------|
| **MIT License** | Highly permissive. Anyone can use, copy, modify, merge, publish, distribute, and sublicense. | Retain original copyright notice and disclaimer of liability. | **Recommended for student showcases.** Maximizes educational value and citation while disclaiming all warranties. |
| **Apache 2.0** | Permissive like MIT, but includes explicit patent rights grants and trademark restrictions. | Retain copyright notice, state changes made, and include NOTICE file if applicable. | Standard for enterprise open source. May be more complex than necessary for a small proof of concept. |
| **GPLv3** | Strong copyleft. Any derivative work or modified distribution must also be open-sourced under GPLv3. | Source code of derivative works must be disclosed under the same license. | Suitable if you want to ensure the code remains strictly open source and cannot be incorporated into proprietary closed software. |
| **Unlicensed (Proprietary)** | No open-source permissions granted. Default copyright law applies. | Third parties may view code on GitHub, but cannot reuse, modify, or distribute it without explicit permission. | **Default state.** Retains exclusive intellectual property rights. |

### University Intellectual Property Considerations
At most academic institutions (including Quezon City University), software developed as part of academic coursework or university-related project requirements may be subject to institutional intellectual property policies:
- If university resources, faculty guidance, or institutional logos were used, institutional IP agreements may dictate whether student work can be licensed under permissive open-source licenses.
- Co-authors or team members who contributed code hold joint copyright unless explicitly assigned.
- **Decision:** No license is automatically added in this maintenance update. The repository maintainer should confirm with team members and academic advisers before selecting a license.

---

## 📁 Repository Structure

```
Facebook-Scraper/
├── .github/
│   └── workflows/
│       └── test.yml            # Minimal GitHub Actions CI workflow (offline unit tests)
│
├── main.py                     # Central execution CLI (supports --offline fixture mode)
├── test_scraper.py             # Offline configuration & environment diagnostic check
├── requirements.txt            # Python dependencies (version ranges for Python 3.10-3.12+)
├── .env.example                # Environment variables template (auto-loaded by src/config.py)
├── .gitignore                  # Comprehensive secrets & artifact exclusion rules
├── SECURITY.md                 # Security policy & incident audit disclosures
├── README.md                   # Project documentation & status matrix
├── GUIDE.md                    # Detailed developer handbook & recovery logs
├── QCU Unified Network.md      # Conceptual system architecture specification
│
├── config/
│   ├── sources.json            # Target Facebook pages & groups metadata
│   ├── settings.json           # Application settings
│   └── keywords.json           # Categorization and urgency keywords
│
├── src/
│   ├── __init__.py
│   ├── config.py               # Centralized configuration, .env loader & path resolver
│   ├── parser.py               # Deterministic text block extraction & SHA-256 hashing
│   ├── database.py             # Firebase Firestore batch persistence & deduplication
│   ├── scraper.py              # Selenium-based page scraper
│   └── scraper_playwright.py   # Playwright-based page scraper
│
└── tests/
    ├── __init__.py
    ├── fixtures/
    │   └── sample_page_text.txt # Local announcement fixture for offline pipeline runs
    ├── test_parser.py          # Unit tests for text parsing & collision prevention
    ├── test_config.py          # Unit tests for config loading, .env parsing & paths
    ├── test_database.py        # Unit tests for Firestore batch deduplication & legacy IDs
    └── test_main.py            # Unit tests for CLI pipeline parameter propagation & offline mode
```

---

## 👥 Contributors & Academic Context

- **Platform Technologies Student Project Group**
- **Lead Developer:** Brent Ford V. Remerata
- **Institution:** Quezon City University (QCU), Quezon City, Philippines
