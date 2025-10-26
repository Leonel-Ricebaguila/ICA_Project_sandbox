"""
Database Migration Script for NFC Support

This script adds NFC fields to the database.

OPTION 1: Alembic Migration (Recommended if Alembic is configured)
OPTION 2: Manual SQL Script (If Alembic is not configured)

Choose the option that works for your IAM_Backend setup.
"""

# ============================================================
# OPTION 1: ALEMBIC MIGRATION
# ============================================================

"""
If using Alembic, save this as:
alembic/versions/xxxx_add_nfc_support.py

Replace xxxx with next revision number (e.g., 0001, 0002, etc.)
"""

"""add nfc support

Revision ID: 0001_nfc_support
Revises: 
Create Date: 2025-10-26

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = '0001_nfc_support'
down_revision = None  # Change this to your last migration revision
branch_labels = None
depends_on = None


def upgrade():
    """Add NFC support to database"""
    
    # ========== ADD NFC COLUMNS TO USUARIOS TABLE ==========
    
    print("Adding NFC columns to usuarios table...")
    
    # Add NFC UID columns
    op.add_column('usuarios', sa.Column('nfc_uid', sa.String(32), nullable=True))
    op.add_column('usuarios', sa.Column('nfc_uid_hash', sa.String(64), nullable=True))
    op.add_column('usuarios', sa.Column('nfc_card_id', sa.String(32), nullable=True))
    op.add_column('usuarios', sa.Column('nfc_status', sa.String(20), nullable=True))
    op.add_column('usuarios', sa.Column('nfc_issued_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('usuarios', sa.Column('nfc_revoked_at', sa.DateTime(timezone=True), nullable=True))
    
    # Create unique index on nfc_uid
    op.create_index('idx_usuarios_nfc_uid', 'usuarios', ['nfc_uid'], unique=True)
    
    print("✅ NFC columns added to usuarios table")
    
    # ========== ADD DEVICE COLUMNS TO DEVICES_NFC TABLE ==========
    
    print("Adding device management columns to devices_nfc table...")
    
    # Add device management columns (nullable for migration)
    op.add_column('devices_nfc', sa.Column('device_id', sa.String(64), nullable=True))
    op.add_column('devices_nfc', sa.Column('device_secret', sa.String, nullable=True))
    op.add_column('devices_nfc', sa.Column('registered_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('devices_nfc', sa.Column('android_version', sa.String, nullable=True))
    op.add_column('devices_nfc', sa.Column('app_version', sa.String, nullable=True))
    op.add_column('devices_nfc', sa.Column('stats_json', sa.JSON, nullable=True))
    
    # ========== POPULATE EXISTING DEVICES ==========
    
    print("Populating device_id and device_secret for existing devices...")
    
    # Get database connection
    bind = op.get_bind()
    
    # Check if there are existing devices
    result = bind.execute(text("SELECT COUNT(*) FROM devices_nfc"))
    count = result.scalar()
    
    if count > 0:
        print(f"Found {count} existing device(s), generating IDs and secrets...")
        
        # Get all existing devices
        result = bind.execute(text("SELECT id FROM devices_nfc"))
        devices = result.fetchall()
        
        # Generate device_id and device_secret for each
        import secrets
        for i, (db_id,) in enumerate(devices):
            device_id = f"NFC-READER-{i+1:03d}"
            device_secret = secrets.token_urlsafe(32)
            
            bind.execute(
                text("""
                    UPDATE devices_nfc 
                    SET device_id = :did, 
                        device_secret = :secret,
                        registered_at = CURRENT_TIMESTAMP
                    WHERE id = :id
                """),
                {"did": device_id, "secret": device_secret, "id": db_id}
            )
            
            print(f"  Device {db_id}: device_id={device_id}")
            print(f"  ⚠️  SAVE THIS SECRET: {device_secret}")
    else:
        print("No existing devices found - skipping ID generation")
    
    # ========== MAKE DEVICE_ID AND DEVICE_SECRET NOT NULL ==========
    
    print("Setting device_id and device_secret as NOT NULL...")
    
    # Now make them NOT NULL (after populating existing rows)
    # Note: Syntax varies by database (PostgreSQL vs SQLite)
    try:
        op.alter_column('devices_nfc', 'device_id', nullable=False)
        op.alter_column('devices_nfc', 'device_secret', nullable=False)
    except Exception as e:
        print(f"⚠️  Warning: Could not set NOT NULL constraint: {e}")
        print("   This is OK for SQLite - the columns are still added")
    
    # Create unique index on device_id
    op.create_index('idx_devices_nfc_device_id', 'devices_nfc', ['device_id'], unique=True)
    
    print("✅ Device columns added to devices_nfc table")
    print("✅ Migration complete!")


def downgrade():
    """Remove NFC support from database"""
    
    print("Removing NFC support...")
    
    # Remove indexes
    op.drop_index('idx_usuarios_nfc_uid', 'usuarios')
    op.drop_index('idx_devices_nfc_device_id', 'devices_nfc')
    
    # Remove columns from usuarios
    op.drop_column('usuarios', 'nfc_uid')
    op.drop_column('usuarios', 'nfc_uid_hash')
    op.drop_column('usuarios', 'nfc_card_id')
    op.drop_column('usuarios', 'nfc_status')
    op.drop_column('usuarios', 'nfc_issued_at')
    op.drop_column('usuarios', 'nfc_revoked_at')
    
    # Remove columns from devices_nfc
    op.drop_column('devices_nfc', 'device_id')
    op.drop_column('devices_nfc', 'device_secret')
    op.drop_column('devices_nfc', 'registered_at')
    op.drop_column('devices_nfc', 'android_version')
    op.drop_column('devices_nfc', 'app_version')
    op.drop_column('devices_nfc', 'stats_json')
    
    print("✅ NFC support removed")


# ============================================================
# OPTION 2: MANUAL SQL SCRIPT
# ============================================================

"""
If NOT using Alembic, run these SQL commands directly.

Save this section as: migrations/add_nfc_support.sql

Then run: 
  sqlite3 iam.db < migrations/add_nfc_support.sql
  (or equivalent for PostgreSQL/MySQL)
"""

SQL_MIGRATION = """
-- ============================================================
-- Add NFC Support to IAM_Backend Database
-- Date: 2025-10-26
-- ============================================================

BEGIN TRANSACTION;

-- ========== ADD NFC COLUMNS TO USUARIOS ==========

ALTER TABLE usuarios ADD COLUMN nfc_uid VARCHAR(32);
ALTER TABLE usuarios ADD COLUMN nfc_uid_hash VARCHAR(64);
ALTER TABLE usuarios ADD COLUMN nfc_card_id VARCHAR(32);
ALTER TABLE usuarios ADD COLUMN nfc_status VARCHAR(20);
ALTER TABLE usuarios ADD COLUMN nfc_issued_at TIMESTAMP;
ALTER TABLE usuarios ADD COLUMN nfc_revoked_at TIMESTAMP;

-- Create unique index on nfc_uid
CREATE UNIQUE INDEX idx_usuarios_nfc_uid ON usuarios(nfc_uid);

-- ========== ADD DEVICE COLUMNS TO DEVICES_NFC ==========

ALTER TABLE devices_nfc ADD COLUMN device_id VARCHAR(64);
ALTER TABLE devices_nfc ADD COLUMN device_secret VARCHAR;
ALTER TABLE devices_nfc ADD COLUMN registered_at TIMESTAMP;
ALTER TABLE devices_nfc ADD COLUMN android_version VARCHAR;
ALTER TABLE devices_nfc ADD COLUMN app_version VARCHAR;
ALTER TABLE devices_nfc ADD COLUMN stats_json JSON;

-- ========== POPULATE EXISTING DEVICES (if any) ==========

-- Note: You'll need to manually generate device_id and device_secret for existing devices
-- Example for first device:
-- UPDATE devices_nfc 
-- SET device_id = 'NFC-READER-001', 
--     device_secret = 'YOUR_GENERATED_SECRET_HERE',
--     registered_at = CURRENT_TIMESTAMP
-- WHERE id = 1;

-- ========== CREATE UNIQUE INDEX ==========

CREATE UNIQUE INDEX idx_devices_nfc_device_id ON devices_nfc(device_id);

-- ========== COMMIT CHANGES ==========

COMMIT;

-- ============================================================
-- Verify migration
-- ============================================================

-- Check usuarios columns
SELECT sql FROM sqlite_master WHERE type='table' AND name='usuarios';

-- Check devices_nfc columns
SELECT sql FROM sqlite_master WHERE type='table' AND name='devices_nfc';

-- ============================================================
-- Migration complete!
-- ============================================================
"""


# ============================================================
# INSTRUCTIONS
# ============================================================

"""
HOW TO USE THIS MIGRATION:

OPTION 1 - Alembic (Recommended):
  1. Copy the Alembic code above to: alembic/versions/0001_add_nfc_support.py
  2. Update the 'down_revision' to your last migration
  3. Run: alembic upgrade head
  4. Check output for device secrets (SAVE THEM!)

OPTION 2 - Manual SQL:
  1. Copy the SQL_MIGRATION string above to: migrations/add_nfc_support.sql
  2. Backup your database: cp iam.db iam.db.backup
  3. Run: sqlite3 iam.db < migrations/add_nfc_support.sql
  4. For existing devices, manually generate and update device_id/device_secret

VERIFICATION:
  After migration, verify with:
  
  Python:
    from app.models import Usuario, NFCDevice
    from app.db import SessionLocal
    
    db = SessionLocal()
    
    # Check Usuario has NFC fields
    user = db.query(Usuario).first()
    print(hasattr(user, 'nfc_uid'))  # Should be True
    
    # Check NFCDevice has device_id
    device = db.query(NFCDevice).first()
    print(hasattr(device, 'device_id'))  # Should be True
  
  SQL:
    SELECT nfc_uid, nfc_status FROM usuarios LIMIT 1;
    SELECT device_id, device_secret FROM devices_nfc LIMIT 1;

ROLLBACK (if needed):
  Alembic:
    alembic downgrade -1
  
  Manual SQL:
    -- Drop indexes
    DROP INDEX IF EXISTS idx_usuarios_nfc_uid;
    DROP INDEX IF EXISTS idx_devices_nfc_device_id;
    
    -- Drop columns (SQLite requires table recreation for this)
    -- Backup first, then recreate tables without NFC columns

IMPORTANT NOTES:
  1. BACKUP YOUR DATABASE before running migration!
  2. Save device secrets generated for existing devices
  3. Migration is safe - all new fields are nullable
  4. No data loss - only adding columns
  5. Can be reversed with downgrade() function
"""


# ============================================================
# POST-MIGRATION TASKS
# ============================================================

"""
After successful migration:

1. ✅ Verify tables have new columns
2. ✅ Test user and device models in Python
3. ✅ Register a test NFC device:
   python -m app.cli register-nfc-device --name "Test Device" --location "Test"
4. ✅ Assign test NFC card to user:
   python -m app.cli assign-nfc --uid EMP-001 --nfc-uid TEST123456
5. ✅ Test NFC scan endpoint with Postman
6. ✅ Check eventos table for logged events
"""


