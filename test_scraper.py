"""
Environment and Configuration Health Check Utility
===================================================
Run: python test_scraper.py

Validates local dependencies, configuration syntax, sources schema,
and credential paths without making live network calls or exposing secrets.
"""

import sys
from pathlib import Path
from src.config import load_sources, load_settings, get_cookies_path, get_firebase_key_path


def main() -> int:
    print()
    print("=" * 60)
    print("QCU SCRAPER - ENVIRONMENT & CONFIGURATION CHECK")
    print("=" * 60)
    print(f"Python Runtime: {sys.version.split()[0]} on {sys.platform}")
    print()
    
    issues = []
    warnings = []

    # 1. Dependency checks
    print("📦 DEPENDENCY CHECK")
    print("-" * 40)

    try:
        import selenium
        print(f"  ✅ selenium installed (v{selenium.__version__})")
    except ImportError:
        print("  ❌ selenium NOT installed")
        issues.append("pip install selenium")

    try:
        import webdriver_manager
        print("  ✅ webdriver-manager installed")
    except ImportError:
        print("  ❌ webdriver-manager NOT installed")
        issues.append("pip install webdriver-manager")

    try:
        import firebase_admin
        print("  ✅ firebase-admin installed")
    except ImportError:
        print("  ⚠️  firebase-admin NOT installed (required for Firestore upload)")
        warnings.append("pip install firebase-admin")

    try:
        import playwright
        print("  ✅ playwright installed (optional backup scraper)")
    except ImportError:
        print("  ℹ️  playwright not installed (optional, run: pip install playwright)")

    # 2. Configuration files check
    print()
    print("⚙️  CONFIGURATION CHECK")
    print("-" * 40)

    sources = load_sources()
    if sources:
        enabled = [s for s in sources if s.get('enabled', True)]
        print(f"  ✅ config/sources.json valid: {len(sources)} sources ({len(enabled)} enabled)")
    else:
        print("  ❌ config/sources.json missing or invalid")
        issues.append("Check config/sources.json syntax")

    settings = load_settings()
    if settings:
        print("  ✅ config/settings.json loaded")
    else:
        print("  ⚠️  config/settings.json missing or empty")
        warnings.append("Create or check config/settings.json")

    # 3. Credentials & Session artifacts
    print()
    print("🔒 CREDENTIAL & SESSION PATHS")
    print("-" * 40)

    cookies_path = get_cookies_path()
    if cookies_path and cookies_path.exists():
        print(f"  ℹ️  Facebook cookies found at: {cookies_path.name}")
        print("     ⚠️  Ensure cookies are never committed to Git.")
    else:
        print("  ℹ️  No cookies file detected (public scraping mode).")

    firebase_path = get_firebase_key_path()
    if firebase_path and firebase_path.exists():
        print(f"  ✅ Firebase service account key found at: {firebase_path.name}")
    else:
        print("  ℹ️  Firebase key not found (runs in offline/dry-run mode).")
        print("     To persist posts: place key at config/firebase-key.json")

    # 4. Summary
    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)

    if issues:
        print("❌ Action required to resolve setup issues:")
        for issue in issues:
            print(f"   → {issue}")
        print("=" * 60)
        return 1
    else:
        if warnings:
            print("⚠️  Recommendations:")
            for w in warnings:
                print(f"   → {w}")
        print("✅ Environment is ready for local execution!")
        print("   Run: python main.py --dry-run")
        print("=" * 60)
        return 0


if __name__ == "__main__":
    sys.exit(main())
