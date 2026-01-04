#!/usr/bin/env python3
"""
Post-deploy smoke tests for evgenich-gift on Railway.
Checks:
1. Database connectivity (PostgreSQL on Railway)
2. Google Sheets integration
3. User data preservation (existing 1082 rows)
4. Report generation for 03.01 12:00 — 04.01 06:00 (Europe/Moscow)
"""

import os
import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import psycopg2
import gspread
from google.oauth2.service_account import Credentials

# ============================================================================
# Environment Setup
# ============================================================================

# Railway PostgreSQL connection
DATABASE_URL = os.getenv("DATABASE_URL", "")
GOOGLE_CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON", "")
GOOGLE_SHEET_KEY = os.getenv("GOOGLE_SHEET_KEY", "1bp7NwfWe1MCb7S6wkaQtaxJEIDaFcFPwv9V_kzlchXs")

def parse_postgres_url(url):
    """Parse postgres://user:pass@host:port/db to dict"""
    from urllib.parse import urlparse
    parsed = urlparse(url)
    return {
        'host': parsed.hostname,
        'port': parsed.port or 5432,
        'database': parsed.path.lstrip('/'),
        'user': parsed.username,
        'password': parsed.password,
    }

# ============================================================================
# Test 1: Database Connectivity
# ============================================================================

def test_database_connection():
    """Test PostgreSQL connection on Railway"""
    print("\n📦 Test 1: Database Connection")
    print("-" * 50)
    
    if not DATABASE_URL:
        print("❌ DATABASE_URL not set")
        return False
    
    try:
        db_params = parse_postgres_url(DATABASE_URL)
        conn = psycopg2.connect(**db_params)
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print(f"✅ PostgreSQL connected: {version[:50]}...")
        
        # Check users table
        cursor.execute("SELECT COUNT(*) FROM users;")
        user_count = cursor.fetchone()[0]
        print(f"✅ Users in database: {user_count}")
        
        if user_count < 1080:  # At least ~1080 existing + some new test users
            print(f"⚠️  Warning: Expected at least 1080 users, got {user_count}")
        else:
            print(f"✅ Data preservation check: {user_count} users (including test users)")
        
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False

# ============================================================================
# Test 2: Google Sheets Connection
# ============================================================================

def test_google_sheets_connection():
    """Test Google Sheets access"""
    print("\n📊 Test 2: Google Sheets Connection")
    print("-" * 50)
    
    if not GOOGLE_CREDENTIALS_JSON:
        print("❌ GOOGLE_CREDENTIALS_JSON not set")
        return False
    
    try:
        # Parse credentials
        if isinstance(GOOGLE_CREDENTIALS_JSON, str):
            creds_dict = json.loads(GOOGLE_CREDENTIALS_JSON)
        else:
            creds_dict = GOOGLE_CREDENTIALS_JSON
        
        # Authenticate
        credentials = Credentials.from_service_account_info(creds_dict)
        gc = gspread.authorize(credentials)
        
        # Open sheet
        sheet = gc.open_by_key(GOOGLE_SHEET_KEY)
        worksheet = sheet.sheet1
        
        print(f"✅ Connected to Google Sheet: {sheet.title}")
        print(f"✅ Worksheet: {worksheet.title}")
        
        # Check row count
        row_count = len(worksheet.get_all_values())
        print(f"✅ Rows in sheet: {row_count}")
        
        if row_count < 1080:
            print(f"⚠️  Warning: Expected at least 1082 rows (header + 1082 users), got {row_count}")
        else:
            print(f"✅ Data preservation check: {row_count} rows (header + users)")
        
        return True
    except Exception as e:
        print(f"❌ Google Sheets error: {e}")
        return False

# ============================================================================
# Test 3: Report Generation (03.01 12:00 — 04.01 06:00 Moscow time)
# ============================================================================

def test_report_generation():
    """Test report queries for the interval 03.01 12:00 — 04.01 06:00 (Europe/Moscow)"""
    print("\n📈 Test 3: Report Generation (03.01 12:00 — 04.01 06:00 Moscow)")
    print("-" * 50)
    
    if not DATABASE_URL:
        print("❌ DATABASE_URL not set")
        return False
    
    try:
        db_params = parse_postgres_url(DATABASE_URL)
        conn = psycopg2.connect(**db_params)
        cursor = conn.cursor()
        
        # Define the interval in Europe/Moscow timezone
        moscow_tz = ZoneInfo("Europe/Moscow")
        start_dt = datetime(2026, 1, 3, 12, 0, 0, tzinfo=moscow_tz)
        end_dt = datetime(2026, 1, 4, 6, 0, 0, tzinfo=moscow_tz)
        
        # Convert to UTC for database query (PostgreSQL stores in UTC)
        start_utc = start_dt.astimezone(ZoneInfo("UTC")).strftime('%Y-%m-%d %H:%M:%S')
        end_utc = end_dt.astimezone(ZoneInfo("UTC")).strftime('%Y-%m-%d %H:%M:%S')
        
        print(f"Report interval (Moscow): {start_dt.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        print(f"Query interval (UTC): {start_utc} to {end_utc}")
        
        # Test new user registrations in this interval
        cursor.execute("""
            SELECT COUNT(*) FROM users 
            WHERE created_at >= %s AND created_at <= %s
        """, (start_utc, end_utc))
        new_users = cursor.fetchone()[0]
        print(f"✅ New users registered: {new_users}")
        
        # Test contact shares in this interval
        cursor.execute("""
            SELECT COUNT(*) FROM user_contacts 
            WHERE created_at >= %s AND created_at <= %s
        """, (start_utc, end_utc))
        contacts_shared = cursor.fetchone()[0]
        print(f"✅ Contacts shared: {contacts_shared}")
        
        # Test social bookings in this interval
        cursor.execute("""
            SELECT COUNT(*) FROM social_bookings 
            WHERE created_at >= %s AND created_at <= %s
        """, (start_utc, end_utc))
        social_bookings = cursor.fetchone()[0]
        print(f"✅ Social bookings: {social_bookings}")
        
        # Test redeemed vouchers in this interval
        cursor.execute("""
            SELECT COUNT(*) FROM users 
            WHERE status = 'Купон погашен' AND updated_at >= %s AND updated_at <= %s
        """, (start_utc, end_utc))
        redeemed = cursor.fetchone()[0]
        print(f"✅ Redeemed vouchers: {redeemed}")
        
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Report generation error: {e}")
        return False

# ============================================================================
# Test 4: Data Export to Google Sheets
# ============================================================================

def test_sheets_export():
    """Test exporting users to Google Sheets (append mode)"""
    print("\n💾 Test 4: Google Sheets Export (Append Mode)")
    print("-" * 50)
    
    if not DATABASE_URL or not GOOGLE_CREDENTIALS_JSON or not GOOGLE_SHEET_KEY:
        print("❌ Missing env vars for export")
        return False
    
    try:
        # Parse credentials
        if isinstance(GOOGLE_CREDENTIALS_JSON, str):
            creds_dict = json.loads(GOOGLE_CREDENTIALS_JSON)
        else:
            creds_dict = GOOGLE_CREDENTIALS_JSON
        
        # Get current sheet row count
        credentials = Credentials.from_service_account_info(creds_dict)
        gc = gspread.authorize(credentials)
        sheet = gc.open_by_key(GOOGLE_SHEET_KEY)
        worksheet = sheet.sheet1
        
        rows_before = len(worksheet.get_all_values())
        print(f"Rows before export: {rows_before}")
        
        # Get users from database
        db_params = parse_postgres_url(DATABASE_URL)
        conn = psycopg2.connect(**db_params)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, telegram_id, contact, name, birth_date, status, created_at 
            FROM users 
            ORDER BY created_at DESC 
            LIMIT 10
        """)
        recent_users = cursor.fetchall()
        
        print(f"✅ Retrieved {len(recent_users)} recent users from database")
        if recent_users:
            print(f"   Latest user ID: {recent_users[0][0]}, TG ID: {recent_users[0][1]}")
        
        # Get existing user IDs from sheet
        all_rows = worksheet.get_all_values()
        existing_ids = set()
        if len(all_rows) > 1:  # Skip header
            for row in all_rows[1:]:
                if row:
                    try:
                        existing_ids.add(int(row[0]))
                    except (ValueError, IndexError):
                        pass
        
        print(f"✅ Existing user IDs in sheet: {len(existing_ids)}")
        
        # Find new users (not in sheet)
        new_users = [u for u in recent_users if u[0] not in existing_ids]
        print(f"✅ New users to append: {len(new_users)}")
        
        if new_users:
            # Append new users
            for user in new_users:
                row = [
                    str(user[0]),  # id
                    str(user[1]),  # telegram_id
                    user[2] or "",  # contact
                    user[3] or "",  # name
                    user[4] or "",  # birth_date
                    user[5] or "",  # status
                    str(user[6]) if user[6] else "",  # created_at
                ]
                worksheet.append_row(row)
            print(f"✅ Appended {len(new_users)} new users to sheet")
        else:
            print(f"ℹ️  No new users to append (all recent users already in sheet)")
        
        rows_after = len(worksheet.get_all_values())
        print(f"Rows after export: {rows_after}")
        
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Export error: {e}")
        import traceback
        traceback.print_exc()
        return False

# ============================================================================
# Main
# ============================================================================

def main():
    print("\n" + "=" * 60)
    print("🚀 PRODUCTION SMOKE TESTS - evgenich-gift on Railway")
    print("=" * 60)
    
    results = {
        "Database Connection": test_database_connection(),
        "Google Sheets Connection": test_google_sheets_connection(),
        "Report Generation": test_report_generation(),
        "Sheets Export": test_sheets_export(),
    }
    
    print("\n" + "=" * 60)
    print("📋 TEST SUMMARY")
    print("=" * 60)
    
    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name}: {status}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n🎉 ALL TESTS PASSED! Production deployment successful.")
    else:
        print("\n⚠️  SOME TESTS FAILED. Check logs above.")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    exit(main())
