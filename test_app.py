#!/usr/bin/env python3
"""
Simple test script to verify gunicorn can import the app
"""

if __name__ == "__main__":
    try:
        print("🔍 Testing app import...")
        from web_app import app
        print("✅ App imported successfully")
        print(f"📍 App name: {app.name}")
        print(f"🔧 Debug mode: {app.debug}")
        
        # Test gunicorn import
        import gunicorn
        print(f"🦄 Gunicorn version: {gunicorn.__version__}")
        
        print("\n🚀 All checks passed!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
