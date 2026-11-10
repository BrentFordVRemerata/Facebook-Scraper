# Security Policy

## Overview

The **QCU Facebook Scraper** was developed as an educational research prototype and student capstone proof-of-concept exploring centralized announcement feeds for Quezon City University. 

This repository is **not** deployed in production and is not maintained as an active service.

---

## Reporting a Vulnerability

If you discover a security vulnerability or sensitive data exposure in this repository, please report it responsibly:

1. **GitHub Private Vulnerability Reporting:** Use the "Report a vulnerability" button under the **Security** tab of the GitHub repository.
2. **Direct Contact:** Email the project maintainer at `remerata.brentford.vergeldedios@gmail.com`.

Please include:
- A description of the issue and potential impact
- Affected commit hashes or file paths
- Steps to reproduce or verify
- Any proposed remediation

We ask that you do not open public GitHub issues for unresolved sensitive data exposures.

---

## Historical Security Findings & Remediation

During a repository audit conducted in November 2026, the following historical exposures were identified in the Git commit history:

### 1. Authenticated Session HTML Dump (Commit `58cfe30f5557d95c1b5299e96871896099d05931`)
- **Impact:** An active personal Facebook session dump (`data/debug_page.html`, ~4.54 MB and `data/debug_text.txt`, ~5.3 KB) was committed on February 1, 2026 and removed in commit `50fb423b30fb08726c66706e068c76b47585ad67`.
- **Exposed Data:** The raw DOM snapshot contained Facebook User/Account IDs, account holder personal name, anti-CSRF tokens (`DTSGInitialData`), notification state, and session metadata.
- **Remediation Required:**
  1. **Account Session Termination:** The account holder must invalidate active sessions by visiting Facebook **Settings & Privacy → Password and Security → Where You're Logged In → Log out of all sessions** and updating their password.
  2. **History Purge (Requires Owner Approval):** Although the files were removed from the working tree in commit `50fb423`, the Git pack files still retain the objects. Permanent removal requires rewriting Git history (e.g. via `git-filter-repo` or BFG Repo-Cleaner) followed by a force-push to `main`.

### 2. Code Safeguards Implemented (2026 Recovery)
- Debug file writing (`data/debug_page.html`, `data/debug_text.txt`) in `src/scraper.py` and `src/scraper_playwright.py` is now **disabled by default**. It can only be enabled explicitly via `--save-debug` or `SAVE_DEBUG_DUMPS=true`.
- `.gitignore` was expanded to prevent any accidental tracking of `data/*.html`, `data/*.txt`, `data/debug*`, `cookies.txt`, or service account keys.

---

## Secrets & Credential Management

### 1. Firebase Service Account Keys
- **Location:** `config/firebase-key.json` or path specified in `FIREBASE_KEY_PATH`.
- **Status:** **Must NEVER be committed to Git.**
- **Permissions:** If configuring Firebase, adhere to the principle of least privilege. Do not use project Owner/Editor credentials; generate a dedicated service account restricted to Firestore Read/Write only.
- **Firestore Rules:** Never leave Firestore security rules in open "test mode" (`allow read, write: if true;`) in any shared or production environment.

### 2. Facebook Session Cookies
- **Location:** `config/facebook_cookies.txt` or `config/cookies.txt`.
- **Status:** **Must NEVER be committed to Git.**
- **Risk:** Cookies such as `c_user` and `xs` represent full session authentication tokens. Anyone possessing them can impersonate the account holder and access private messages, personal details, and connected pages.

---

## Platform Terms of Service & Legal Boundaries

- **Meta Terms of Service:** Section 3.2.3 of Meta's Terms of Service prohibits accessing or collecting data from Facebook products using automated means without prior written permission.
- **Account Suspension Risk:** Automated scraping using personal credentials carries a high probability of account checkpointing, temporary restriction, or permanent account termination.
- **Private Groups:** Scraping private groups requires authenticated group membership. This violates platform access boundaries and is disabled by default in this repository.
