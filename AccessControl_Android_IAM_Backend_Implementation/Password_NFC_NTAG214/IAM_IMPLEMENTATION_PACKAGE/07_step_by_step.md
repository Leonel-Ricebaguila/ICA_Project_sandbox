# 🚀 Step-by-Step Implementation Guide

**Follow these steps exactly to add NFC support to IAM_Backend**

Estimated time: **60 minutes** (45 min implementation + 15 min testing)

---

## 📋 PRE-FLIGHT CHECKLIST

Before starting, verify:

- [ ] You have IAM_Backend code accessible
- [ ] You know where the IAM_Backend folder is located
- [ ] Database is accessible (SQLite/PostgreSQL)
- [ ] Python environment is activated
- [ ] You have a backup of the database
- [ ] You have admin access to run migrations

**⚠️ IMPORTANT:** Backup your database before proceeding!

```bash
# For SQLite
cp iam.db iam.db.backup.$(date +%Y%m%d)

# For PostgreSQL
pg_dump iam_database > iam_backup_$(date +%Y%m%d).sql
```

---

## 🎯 PHASE 1: DATABASE MODELS (10 minutes)

### Step 1.1: Locate models.py

```bash
cd /path/to/IAM_Backend
ls -la app/models.py
```

**Expected:** You should see `app/models.py` file

---

### Step 1.2: Open models.py

```bash
# Use your preferred editor
code app/models.py
# OR
nano app/models.py
# OR
vim app/models.py
```

---

### Step 1.3: Add NFC fields to Usuario class

**Find this class:**
```python
class Usuario(Base):
    __tablename__ = "usuarios"
    ...
```

**Add these 6 fields** (copy from `02_models_additions.py`):

```python
# NFC Card fields (add after qr_revoked_at field)
nfc_uid = Column(String(32), unique=True, nullable=True)
nfc_uid_hash = Column(String(64), nullable=True)
nfc_card_id = Column(String(32), nullable=True)
nfc_status = Column(String(20), default='inactive', nullable=True)
nfc_issued_at = Column(DateTime(timezone=True), nullable=True)
nfc_revoked_at = Column(DateTime(timezone=True), nullable=True)
```

**Location:** After existing QR fields, before MFA fields

**⚠️ Important:** Match the indentation of surrounding fields!

---

### Step 1.4: Add device fields to NFCDevice class

**Find this class:**
```python
class NFCDevice(Base):
    __tablename__ = "devices_nfc"
    ...
```

**Add these 6 fields:**

```python
# Device authentication and tracking fields
device_id = Column(String(64), unique=True, nullable=False)
device_secret = Column(String, nullable=False)
registered_at = Column(DateTime(timezone=True), default=now_cst, nullable=True)
android_version = Column(String, nullable=True)
app_version = Column(String, nullable=True)
stats_json = Column(JSON, nullable=True)
```

**Location:** After existing fields (last_seen, etc.)

---

### Step 1.5: Check imports

Verify these imports exist at the top of models.py:

```python
from sqlalchemy import Column, String, DateTime, JSON, Boolean, Integer
from .time_utils import now_cst
```

If missing, add them.

---

### Step 1.6: Save models.py

```bash
# In nano: Ctrl+O, Enter, Ctrl+X
# In vim: :wq
# In VS Code: Ctrl+S
```

---

### ✅ Verification Step 1

```bash
# Check for syntax errors
python -c "from app.models import Usuario, NFCDevice; print('✅ Models OK')"
```

**Expected output:** `✅ Models OK`

**If error:** Check indentation and commas

---

## 🗄️ PHASE 2: DATABASE MIGRATION (15 minutes)

### Step 2.1: Choose migration method

**Option A:** Alembic (if configured) - RECOMMENDED  
**Option B:** Manual SQL (if Alembic not set up)

To check if Alembic is set up:
```bash
ls alembic/
```

If you see `alembic` folder → Use Option A  
If not → Use Option B

---

### Step 2.2A: Alembic Migration (RECOMMENDED)

#### Create migration file

```bash
# Create new migration
alembic revision -m "add_nfc_support"
```

This creates: `alembic/versions/xxxx_add_nfc_support.py`

#### Copy migration code

1. Open the newly created file
2. Copy the `upgrade()` and `downgrade()` functions from `03_migration_script.py`
3. Update `down_revision` to match your last migration

#### Run migration

```bash
alembic upgrade head
```

**Expected output:**
```
INFO  [alembic.runtime.migration] Running upgrade -> 0001_nfc_support
Adding NFC columns to usuarios table...
✅ NFC columns added to usuarios table
Adding device management columns to devices_nfc table...
✅ Device columns added to devices_nfc table
✅ Migration complete!
```

**⚠️ SAVE device secrets shown in output!**

---

### Step 2.2B: Manual SQL Migration

If Alembic is not configured, use SQL directly:

```bash
# For SQLite
sqlite3 iam.db < manual_migration.sql

# For PostgreSQL
psql iam_database < manual_migration.sql
```

Where `manual_migration.sql` contains the SQL from `03_migration_script.py`

---

### ✅ Verification Step 2

Check that columns were added:

```bash
# For SQLite
sqlite3 iam.db "PRAGMA table_info(usuarios);" | grep nfc

# For PostgreSQL
psql iam_database -c "\d usuarios" | grep nfc
```

**Expected:** You should see 6 nfc_* columns

---

## 🌐 PHASE 3: API ROUTES (10 minutes)

### Step 3.1: Create api folder (if not exists)

```bash
mkdir -p app/api
touch app/api/__init__.py
```

---

### Step 3.2: Copy nfc_routes.py

```bash
cp IAM_IMPLEMENTATION_PACKAGE/01_nfc_routes.py app/api/nfc_routes.py
```

---

### Step 3.3: Install PyJWT

```bash
pip install PyJWT
```

**Expected output:** `Successfully installed PyJWT-2.8.0`

---

### Step 3.4: Register blueprint

**Open app/__init__.py** (or wherever Flask app is created):

```bash
code app/__init__.py
```

**Add these TWO lines:**

```python
# At the top with other imports:
from .api import nfc_routes

# In create_app() function with other blueprint registrations:
app.register_blueprint(nfc_routes.bp)
```

See `05_blueprint_registration.txt` for detailed example.

---

### Step 3.5: Set environment variables

Edit `.env` file:

```bash
# Add or update these lines:
JWT_SECRET_KEY=your-secret-key-change-in-production-12345
NFC_DEVICE_JWT_EXP_SECONDS=86400
```

**⚠️ Important:** Use a strong, unique JWT_SECRET_KEY!

Generate one with:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

---

### Step 3.6: Restart Flask server

```bash
# Stop current server (Ctrl+C)
# Start again
python -m flask run --port 5443
# OR
python run.py
```

---

### ✅ Verification Step 3

Test config endpoint:

```bash
curl -k https://localhost:5443/api/nfc_devices/config
```

**Expected output:**
```json
{
  "heartbeat_interval": 30,
  "scan_timeout": 5,
  "offline_queue_max": 1000,
  "features": {...}
}
```

**✅ If you see this, blueprint is registered correctly!**

---

## 🖥️ PHASE 4: CLI COMMANDS (10 minutes)

### Step 4.1: Open cli.py

```bash
code app/cli.py
```

---

### Step 4.2: Add CLI functions

Copy all functions from `04_cli_additions.py` to the end of `app/cli.py`

**Functions to add:**
1. `register_nfc_device()`
2. `assign_nfc_card()`
3. `list_nfc_devices()`
4. `revoke_nfc_card()`
5. `activate_nfc_card()`
6. `list_nfc_users()`

---

### Step 4.3: Register CLI commands

If using Click framework, add command decorators (see `04_cli_additions.py` for examples).

If using argparse or custom CLI, integrate accordingly.

---

### ✅ Verification Step 4

Test CLI help:

```bash
python -m app.cli --help
```

**Expected:** You should see new NFC commands listed

---

## 🧪 PHASE 5: TESTING (20 minutes)

### Step 5.1: Register test device

```bash
python -m app.cli register-nfc-device \
  --name "Test Device" \
  --location "Test Lab"
```

**Expected output:**
```
✅ NFC Device Registered Successfully!
Device ID:     NFC-READER-001
Device Secret: abcd1234...
```

**⚠️ SAVE THESE CREDENTIALS!**

---

### Step 5.2: Test device authentication

```bash
curl -k -X POST https://localhost:5443/api/nfc_devices/auth \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "NFC-READER-001",
    "device_secret": "YOUR_SECRET_HERE"
  }'
```

**Expected:** JWT token in response

**Save the token** for next tests!

---

### Step 5.3: Create test user

```bash
# Create user if not exists
python -m app.cli create-user \
  --uid TEST-001 \
  --email test@test.com \
  --password Test123! \
  --role R-EMP
```

---

### Step 5.4: Assign NFC card

```bash
python -m app.cli assign-nfc \
  --uid TEST-001 \
  --nfc-uid 04A3B2C1D4E5F6
```

**Expected:**
```
✅ NFC Card Assigned Successfully!
```

---

### Step 5.5: Test NFC scan

```bash
curl -k -X POST https://localhost:5443/api/nfc/scan \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "nfc_uid": "04A3B2C1D4E5F6",
    "device_id": "NFC-READER-001"
  }'
```

**Expected:**
```json
{
  "result": "granted",
  "user": {...},
  "access_level": "standard"
}
```

**✅ Success! NFC scanning works!**

---

### Step 5.6: Run full test suite

Follow `06_testing_guide.md` for complete testing checklist (12 tests total)

---

## 🎉 PHASE 6: VERIFICATION (5 minutes)

### Final Checklist

- [ ] Database has 12 new fields (6 in Usuario, 6 in NFCDevice)
- [ ] Flask server starts without errors
- [ ] Config endpoint returns JSON
- [ ] Device can authenticate and get JWT
- [ ] User can be assigned NFC card
- [ ] NFC scan grants/denies access correctly
- [ ] Events are logged to database
- [ ] CLI commands work

---

### Check Audit Trail

```python
python

>>> from app.db import SessionLocal
>>> from app.models import Evento
>>> db = SessionLocal()
>>> events = db.query(Evento).filter(Evento.event.like('nfc_%')).all()
>>> print(f"NFC events logged: {len(events)}")
```

**Expected:** At least 2-3 events logged

---

### Check Web Interface

1. Open web interface in browser
2. Navigate to logs/events page
3. Look for NFC-related events
4. Should see device auth, scan granted/denied events

---

## ✅ IMPLEMENTATION COMPLETE!

Congratulations! You've successfully added NFC support to IAM_Backend!

---

## 📊 WHAT YOU'VE ACCOMPLISHED

✅ **8 new API endpoints** for NFC operations  
✅ **12 new database fields** for users and devices  
✅ **6 new CLI commands** for management  
✅ **JWT authentication** for secure device access  
✅ **Complete audit trail** for all NFC events  
✅ **Production-ready** error handling and validation  

---

## 🔜 NEXT STEPS

### 1. Configure Android App

Update `NetworkManager.kt` in Android app:

```kotlin
private const val BASE_URL = "https://YOUR_SERVER_IP:5443"
```

### 2. Register Android Device

1. Get device credentials from CLI
2. Enter in Android app login screen
3. App will authenticate and get JWT token

### 3. Start Testing

1. Assign NFC cards to test users
2. Scan cards with Android app
3. Verify access granted/denied
4. Check audit trail in web interface

---

## 🆘 TROUBLESHOOTING

### Common Issues

| Problem | Solution |
|---------|----------|
| Import error for PyJWT | `pip install PyJWT` |
| Database error on migration | Check models.py syntax |
| 404 on NFC endpoints | Check blueprint registration |
| 401 on authenticated endpoints | Check JWT_SECRET_KEY matches |
| Device stays "pending" | Authenticate once to activate |

### Getting Help

1. Check server console for errors
2. Review `06_testing_guide.md` troubleshooting section
3. Verify all steps were completed in order
4. Check database columns exist

---

## 📝 ROLLBACK PROCEDURE

If something goes wrong and you need to rollback:

### Alembic Rollback

```bash
alembic downgrade -1
```

### Manual Rollback

```sql
-- Remove indexes
DROP INDEX IF EXISTS idx_usuarios_nfc_uid;
DROP INDEX IF EXISTS idx_devices_nfc_device_id;

-- For SQLite, you'll need to recreate tables without NFC columns
-- (SQLite doesn't support DROP COLUMN easily)

-- For PostgreSQL:
ALTER TABLE usuarios DROP COLUMN nfc_uid;
ALTER TABLE usuarios DROP COLUMN nfc_uid_hash;
-- ... etc
```

**Then restore from backup:**

```bash
cp iam.db.backup iam.db
```

---

## 📚 DOCUMENTATION

- `README.md` - Package overview
- `06_testing_guide.md` - Complete testing checklist  
- `INTEGRATION_GUIDE_UPY_TO_IAM.md` - Full integration plan
- `MINIMAL_IAM_CHANGES_ANALYSIS.md` - Detailed analysis

---

## 🎯 SUCCESS CRITERIA

You're ready to proceed if:

✅ All 12 tests pass  
✅ No errors in server console  
✅ Audit trail shows NFC events  
✅ CLI commands work  
✅ Android app can authenticate  

---

## 🚀 YOU'RE READY!

Your IAM_Backend now has full NFC support!

Next: Configure and test Android app integration

**Happy coding!** 🎉

---

## 📞 REFERENCE CARD

**Quick command reference for daily use:**

```bash
# Register device
python -m app.cli register-nfc-device --name "Device" --location "Location"

# Assign card
python -m app.cli assign-nfc --uid EMP-001 --nfc-uid 04A3B2C1D4E5F6

# List devices
python -m app.cli list-nfc-devices

# List users with cards
python -m app.cli list-nfc-users

# Revoke card
python -m app.cli revoke-nfc --uid EMP-001

# Reactivate card
python -m app.cli activate-nfc --uid EMP-001

# Test endpoint
curl -k https://localhost:5443/api/nfc_devices/config
```

Save this for future reference!


