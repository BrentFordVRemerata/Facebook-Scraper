"""
Quick Test Script
=================
Run: python test_scraper.py
"""

from pathlib import Path


def main():
    print()
    print("=" * 50)
    print("QCU SCRAPER - SYSTEM CHECK")
    print("=" * 50)
    print()
    
    errors = []
    
    # 1. Check Selenium
    try:
        from selenium import webdriver
        print("✅ Selenium installed")
    except ImportError:
        print("❌ Selenium NOT installed")
        errors.append("pip install selenium")
    
    # 2. Check webdriver-manager
    try:
        from webdriver_manager.chrome import ChromeDriverManager
        print("✅ webdriver-manager installed")
    except ImportError:
        print("❌ webdriver-manager NOT installed")
        errors.append("pip install webdriver-manager")
    
    # 3. Check Firebase
    try:
        import firebase_admin
        print("✅ firebase-admin installed")
    except ImportError:
        print("❌ firebase-admin NOT installed")
        errors.append("pip install firebase-admin")
    
    # 4. Check config files
    print()
    
    cookie_path = Path("config/facebook_cookies.txt")
    if cookie_path.exists():
        print("✅ Facebook cookies found")
    else:
        print("⚠️  No cookies (config/facebook_cookies.txt)")
    
    firebase_path = Path("config/firebase-key.json")
    if firebase_path.exists():
        print("✅ Firebase key found")
    else:
        print("❌ Firebase key missing (config/firebase-key.json)")
        errors.append("Add Firebase service account key")
    
    sources_path = Path("config/sources.json")
    if sources_path.exists():
        print("✅ Sources config found")
    else:
        print("❌ Sources config missing (config/sources.json)")
    
    # 5. Test Firebase connection
    print()
    if firebase_path.exists():
        try:
            from src.database import initialize_firebase
            if initialize_firebase():
                print("✅ Firebase connection OK")
            else:
                print("❌ Firebase connection failed")
        except Exception as e:
            print(f"❌ Firebase error: {e}")
    
    # Summary
    print()
    print("=" * 50)
    
    if errors:
        print("FIX THESE ISSUES:")
        for err in errors:
            print(f"   → {err}")
    else:
        print("✅ All checks passed! Run: python main.py")
    
    print("=" * 50)


if __name__ == "__main__":
    main()
