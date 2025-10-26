"""
Database Migration Script for NFC Support
Run this to add NFC columns to existing database
"""

import sqlite3
import secrets
from datetime import datetime

DB_PATH = "iam.db"

def run_migration():
    print("=" * 60)
    print("NFC Support Migration Script")
    print("=" * 60)
    print(f"\nDatabase: {DB_PATH}")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Backup reminder
    print("[!] IMPORTANT: Backup your database before proceeding!")
    response = input("Have you backed up iam.db? (yes/no): ").strip().lower()
    if response != 'yes':
        print("[X] Migration cancelled. Please backup your database first.")
        print("   Run: copy iam.db iam.db.backup")
        return
    
    print("\n" + "=" * 60)
    print("Starting Migration...")
    print("=" * 60)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # ========== ADD NFC COLUMNS TO USUARIOS ==========
        
        print("\n[1/3] Adding NFC columns to usuarios table...")
        
        nfc_columns = [
            ("nfc_uid", "VARCHAR(32)"),
            ("nfc_uid_hash", "VARCHAR(64)"),
            ("nfc_card_id", "VARCHAR(32)"),
            ("nfc_status", "VARCHAR(20)"),
            ("nfc_issued_at", "TIMESTAMP"),
            ("nfc_revoked_at", "TIMESTAMP")
        ]
        
        for col_name, col_type in nfc_columns:
            try:
                cursor.execute(f"ALTER TABLE usuarios ADD COLUMN {col_name} {col_type}")
                print(f"  [OK] Added {col_name}")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e).lower():
                    print(f"  [SKIP] {col_name} already exists")
                else:
                    raise
        
        # Create unique index on nfc_uid
        try:
            cursor.execute("CREATE UNIQUE INDEX idx_usuarios_nfc_uid ON usuarios(nfc_uid)")
            print("  [OK] Created index on nfc_uid")
        except sqlite3.OperationalError as e:
            if "already exists" in str(e).lower():
                print("  [SKIP] Index already exists")
            else:
                raise
        
        # ========== ADD DEVICE COLUMNS TO DEVICES_NFC ==========
        
        print("\n[2/3] Adding device columns to devices_nfc table...")
        
        device_columns = [
            ("device_id", "VARCHAR(64)"),
            ("device_secret", "VARCHAR"),
            ("registered_at", "TIMESTAMP"),
            ("android_version", "VARCHAR"),
            ("app_version", "VARCHAR"),
            ("stats_json", "TEXT")
        ]
        
        for col_name, col_type in device_columns:
            try:
                cursor.execute(f"ALTER TABLE devices_nfc ADD COLUMN {col_name} {col_type}")
                print(f"  [OK] Added {col_name}")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e).lower():
                    print(f"  [SKIP] {col_name} already exists")
                else:
                    raise
        
        # ========== POPULATE EXISTING DEVICES ==========
        
        print("\n[3/3] Populating device IDs and secrets...")
        
        cursor.execute("SELECT id, name FROM devices_nfc WHERE device_id IS NULL")
        devices = cursor.fetchall()
        
        if devices:
            print(f"  Found {len(devices)} device(s) without device_id")
            print()
            
            for i, (device_db_id, device_name) in enumerate(devices):
                device_id = f"NFC-ANDROID-{i+1:03d}"
                device_secret = secrets.token_urlsafe(32)
                
                cursor.execute(
                    """UPDATE devices_nfc 
                       SET device_id = ?, 
                           device_secret = ?,
                           registered_at = CURRENT_TIMESTAMP
                       WHERE id = ?""",
                    (device_id, device_secret, device_db_id)
                )
                
                print(f"  Device: {device_name}")
                print(f"    ID: {device_id}")
                print(f"    Secret: {device_secret}")
                print(f"    [!] SAVE THIS SECRET!")
                print()
        else:
            print("  No existing devices found - all set!")
        
        # Create unique index on device_id
        try:
            cursor.execute("CREATE UNIQUE INDEX idx_devices_nfc_device_id ON devices_nfc(device_id)")
            print("  [OK] Created index on device_id")
        except sqlite3.OperationalError as e:
            if "already exists" in str(e).lower():
                print("  [SKIP] Index already exists")
            else:
                raise
        
        # ========== COMMIT CHANGES ==========
        
        conn.commit()
        
        print("\n" + "=" * 60)
        print("[OK] MIGRATION SUCCESSFUL!")
        print("=" * 60)
        
        # ========== VERIFICATION ==========
        
        print("\nVerifying migration...")
        
        # Check usuarios columns
        cursor.execute("PRAGMA table_info(usuarios)")
        usuarios_cols = [row[1] for row in cursor.fetchall()]
        nfc_cols_found = [col for col, _ in nfc_columns if col in usuarios_cols]
        print(f"\n  usuarios table: {len(nfc_cols_found)}/6 NFC columns found [OK]")
        
        # Check devices_nfc columns
        cursor.execute("PRAGMA table_info(devices_nfc)")
        device_cols = [row[1] for row in cursor.fetchall()]
        dev_cols_found = [col for col, _ in device_columns if col in device_cols]
        print(f"  devices_nfc table: {len(dev_cols_found)}/6 device columns found [OK]")
        
        # Check indexes
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='usuarios'")
        indexes = [row[0] for row in cursor.fetchall()]
        if 'idx_usuarios_nfc_uid' in indexes:
            print("  NFC UID index: found [OK]")
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='devices_nfc'")
        indexes = [row[0] for row in cursor.fetchall()]
        if 'idx_devices_nfc_device_id' in indexes:
            print("  Device ID index: found [OK]")
        
        print("\n" + "=" * 60)
        print("NEXT STEPS:")
        print("=" * 60)
        print("1. [OK] Migration complete")
        print("2. [!] Save any device secrets shown above")
        print("3. [>>] Restart the IAM_Backend server")
        print("4. [>>] Test Android app NFC scanning")
        print("=" * 60)
        
    except Exception as e:
        conn.rollback()
        print(f"\n[X] ERROR during migration: {e}")
        print("   Database rolled back - no changes made")
        raise
    
    finally:
        conn.close()

if __name__ == "__main__":
    run_migration()
