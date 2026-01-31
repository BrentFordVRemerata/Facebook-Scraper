**Version:** 1.0.0
**Lead Architect:** Brent Ford V. Remerata
**Contributors:**

**Objective:** Centralize fragmented university announcements into a single, filterable mobile feed.

---

## 1. The Repository Strategy (Organization)

Do not dump everything into one folder. We will use a **Multi-Repo Strategy** to accommodate different student teams.

- **`qcu-news-scraper`** (Python)
    
    - _The Brain._ Runs on a schedule. Fetches data.
        
    - _Team:_ Platform Technologies Group.
        
- **`qcu-student-app`** (Flutter)
    
    - _The Product._ The mobile interface for students.
        
    - _Team:_ Self-Study / Main Project (formerly Intermediate Prog).
        
- **`qcu-admin-portal`** (Web/HTML/JS)
    
    - _The Backup._ Manual posting tool if automation fails.
        
    - _Team:_ Web Systems Group.
        

---

## 2. System Architecture (The Big Picture)

This flowchart explains how the entire ecosystem connects.

Code snippet

```
graph TD
    subgraph "External World"
        FB[Facebook Pages]
        Web[Official School Website]
    end

    subgraph "The Brain (Python Scraper)"
        Scraper[Python Script]
        Cleaner[Data Sanitizer]
        Tagger[AI Keyword Tagger]
    end

    subgraph "The Cloud (Firebase)"
        DB[(Firestore Database)]
        Auth[Anonymous Auth]
    end

    subgraph "The Client (Mobile App)"
        App[Flutter App]
        Cache[Local Offline Storage]
        UI[Student Feed UI]
    end

    FB -->|Raw HTML/JSON| Scraper
    Scraper -->|Raw Text| Cleaner
    Cleaner -->|Clean Text| Tagger
    Tagger -->|Structured JSON| DB
    DB -->|Realtime Sync| App
    App -->|Read| Cache
    Cache -->|Display| UI
```

---

## 3. Component Deep Dive: "The Listener" (Backend)

**Repository:** `qcu-news-scraper`

**Tech:** Python, `facebook-scraper` or `selenium`, Firebase Admin SDK.

### Logic Flow (How the Robot thinks)

Code snippet

```
flowchart LR
    Start(Start Script) --> Fetch{Fetch FB Page}
    Fetch -- Success --> Loop[Loop through last 10 posts]
    Fetch -- Fail --> Log[Log Error & Sleep]
    
    Loop --> CheckID{Post ID exists in DB?}
    CheckID -- Yes --> Skip[Skip (Duplicate)]
    CheckID -- No --> Process[Process Post]
    
    Process --> Clean[Remove Emojis & 'See More' links]
    Clean --> Tagging{Contains Keywords?}
    
    Tagging -- "Suspension" --> TagUrgent[Tag: URGENT]
    Tagging -- "BSIT" --> TagIT[Tag: BSIT]
    
    TagUrgent --> Push[Upload to Firebase]
    TagIT --> Push
    
    Push --> Sleep(Sleep for 30 mins)
```

### Critical Details for Implementation:

1. **Idempotency:** The script must run every 30 minutes but **never** post the same announcement twice.
    
    - _Solution:_ Use the Facebook Post ID as the Document ID in Firebase. If you try to write a document ID that exists, it just updates it (safe) or ignores it.
        
2. **Sanitization:** Facebook posts are messy.
    
    - _Constraint:_ Remove text like "Click here to sign up" if the link isn't valid.
        
    - _Constraint:_ Convert "2 hrs ago" into a real Timestamp object (`2026-02-01 14:00:00`).
        
3. **Resilience:** If Facebook blocks the scraper, the script must not crash. It should log the error ("Blocked by Zuck") and wait 2 hours before trying again.
    

---

## 4. Component Deep Dive: "The Cloud" (Database)

**Service:** Firebase Firestore

**Mode:** NoSQL (Document Store)

### The Data Schema (The "Skeleton")

Since we are using NoSQL, we don't use tables. We use JSON Documents. This is exactly how your data must look:

**Collection:** `announcements`

**Document ID:** `fb_123456789` (The actual Facebook Post ID)

JSON

```
{
  "title": "Classes Suspended due to Typhoon",
  "body": "Office of the Mayor declares suspension...",
  "source_url": "https://facebook.com/qcu/posts/12345",
  "image_url": "https://fb-cdn.net/image.jpg",
  "timestamp": "2026-02-01T08:00:00Z",
  "author": "QCU Main Page",
  "tags": ["Urgent", "All Campuses"],
  "meta": {
    "scraped_at": "2026-02-01T08:05:00Z",
    "status": "active"
  }
}
```

### Security Rules (Firestore)

- **Read:** `allow read: if true;` (Public for now, anyone can read news).
    
- **Write:** `allow write: if request.auth.token.admin == true;` (Only your Python script with the private key can post news).
    

---

## 5. Component Deep Dive: "The Interface" (Mobile App)

**Repository:** `qcu-student-app`

**Tech:** Flutter (Dart)

### Logic Flow (The User Experience)

Code snippet

```
sequenceDiagram
    participant User
    participant App
    participant LocalDB as Offline Cache
    participant Cloud as Firebase

    User->>App: Opens App
    App->>LocalDB: Load cached news (Speed)
    App-->>User: Show old news immediately
    App->>Cloud: Listening for updates...
    Cloud-->>App: New data found!
    App->>LocalDB: Save new data
    App-->>User: Update screen with new post
    User->>App: Click Filter "San Bartolome"
    App->>App: Hide posts without tag "San Bartolome"
```

### Critical Details for Implementation:

1. **Offline-First:** The app must load _something_ even if the student has no data.
    
    - _Solution:_ Enable Firestore Persistence (1 line of code).
        
2. **The Filter Logic:** Do not query the database every time a user filters.
    
    - _Strategy:_ Download the last 20 posts. Filter them _locally_ on the phone. It is faster and saves server costs.
        
3. **UI State:**
    
    - _Loading State:_ Show a "Skeleton Loader" (grey bars) while fetching.
        
    - _Error State:_ "Cannot connect to QCU Network" (if offline and no cache).
        

---

## 6. The "Prompt Engineering" Guide

_Copy these prompts into GitHub Copilot/Gemini to get the code you need._

**To Build the Scraper:**

> "Act as a Python Backend Engineer. Create a script using `facebook-scraper`. It needs to fetch the latest post from a specific URL. It should check if the post text contains keywords like 'Suspended' or 'BSIT'. If it does, create a dictionary object with the title, body, and timestamp. Do not write to a database yet, just print the JSON."

**To Build the Firebase Connection:**

> "Now, integrate `firebase-admin` SDK. Take the JSON object we created in the previous step and upload it to a Firestore collection named 'announcements'. Use the Facebook Post ID as the document ID to prevent duplicates."

**To Build the Flutter App:**

> "Act as a Mobile Developer. Create a Flutter widget called `NewsFeed`. It should use a `StreamBuilder` to listen to a Firestore collection named 'announcements'. Display the data in a `Card` widget with the Title bolded and the Timestamp in grey. Handle the 'Loading' and 'Error' states."

---

## 7. Risk Management (The "What Ifs")

|**Scenario**|**Impact**|**Solution**|
|---|---|---|
|**Facebook blocks the scraper**|Critical (No data flow)|**Backup:** Use the "Admin Portal" (Web Systems project) to manually type the announcement.|
|**Student has no Internet**|Medium (Cannot get new info)|**Offline Mode:** App shows the announcements from the last time they were online.|
|**Fake News Scraping**|High (Reputation)|**Allowlist:** The scraper must ONLY listen to the 5 official URLs provided in the config. Never scrape random groups.|