# 🧪 Testing Guide for NFC Implementation

**Complete testing checklist for IAM_Backend NFC integration**

---

## 📋 PRE-TESTING CHECKLIST

Before testing, verify:

- [ ] Database migration completed successfully
- [ ] Models updated (Usuario and NFCDevice have new fields)
- [ ] nfc_routes.py copied to app/api/
- [ ] Blueprint registered in __init__.py
- [ ] Flask server restarted
- [ ] No errors in server console

---

## 🔧 TESTING SETUP

### Required Tools

```bash
# Install testing tools if not already installed
pip install requests  # For Python testing
# OR use curl (built-in on most systems)
# OR use Postman (GUI tool)
```

### Environment Variables

Make sure these are set in your `.env`:

```bash
JWT_SECRET_KEY=your-secret-key-here
NFC_DEVICE_JWT_EXP_SECONDS=86400
```

---

## 📝 TEST SEQUENCE

### Test 1: Server Health Check ✅

**Purpose:** Verify server is running

```bash
curl -k https://localhost:5443/health

# Expected: 200 OK
# {"status": "ok"} or similar
```

---

### Test 2: NFC Config Endpoint ✅

**Purpose:** Verify NFC routes are registered

```bash
curl -k https://localhost:5443/api/nfc_devices/config

# Expected: 200 OK
# {
#   "heartbeat_interval": 30,
#   "scan_timeout": 5,
#   "offline_queue_max": 1000,
#   "features": {...},
#   "server_time": "2025-10-26T..."
# }
```

✅ **If this works, blueprint registration is successful!**

---

### Test 3: Register NFC Device (CLI) ✅

**Purpose:** Create test device credentials

```bash
python -m app.cli register-nfc-device \
  --name "Test NFC Reader" \
  --location "Test Lab"

# Expected output:
# ✅ NFC Device Registered Successfully!
# Device ID:     NFC-READER-XXX
# Device Secret: <base64_secret>
# 
# ⚠️  SAVE THESE CREDENTIALS!
```

**IMPORTANT:** Copy the Device ID and Device Secret for next tests

---

### Test 4: Device Authentication ✅

**Purpose:** Get JWT token for device

```bash
# Replace with your actual device_id and device_secret from Test 3
curl -k -X POST https://localhost:5443/api/nfc_devices/auth \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "NFC-READER-001",
    "device_secret": "YOUR_DEVICE_SECRET_HERE",
    "location": "Test Lab",
    "android_version": "13",
    "app_version": "1.0.0"
  }'

# Expected: 200 OK
# {
#   "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
#   "expires_at": 1698342000,
#   "device_info": {
#     "id": 1,
#     "name": "Test NFC Reader",
#     "status": "active",
#     "location": "Test Lab",
#     "last_seen": "2025-10-26T..."
#   }
# }
```

**IMPORTANT:** Copy the `token` value for next tests

---

### Test 5: Create Test User with NFC Card ✅

**Purpose:** Assign NFC card to a user

```bash
# First, create a test user if not exists
python -m app.cli create-user \
  --uid TEST-001 \
  --email test@example.com \
  --password Test123! \
  --role R-EMP \
  --nombre "Test" \
  --apellido "User"

# Then assign NFC card
python -m app.cli assign-nfc \
  --uid TEST-001 \
  --nfc-uid 04A3B2C1D4E5F6

# Expected:
# ✅ NFC Card Assigned Successfully!
# User:     TEST-001 (Test User)
# NFC UID:  04A3B2C1D4E5F6
# Status:   active
```

---

### Test 6: NFC Scan - Access Granted ✅

**Purpose:** Test successful card scan

```bash
# Replace YOUR_JWT_TOKEN with token from Test 4
curl -k -X POST https://localhost:5443/api/nfc/scan \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "nfc_uid": "04A3B2C1D4E5F6",
    "nfc_uid_hash": "",
    "device_id": "NFC-READER-001",
    "timestamp": "2025-10-26T15:30:00Z",
    "location": "Test Lab",
    "card_type": "Test Card"
  }'

# Expected: 200 OK
# {
#   "result": "granted",
#   "user": {
#     "uid": "TEST-001",
#     "nombre": "Test",
#     "apellido": "User",
#     "rol": "R-EMP",
#     "foto_url": "/static/avatars/TEST-001.png",
#     "email": "test@example.com"
#   },
#   "access_level": "standard",
#   "message": "Access granted",
#   "event_id": 1,
#   "timestamp": "2025-10-26T..."
# }
```

✅ **Success! Access granted**

---

### Test 7: NFC Scan - Card Not Registered ✅

**Purpose:** Test denial for unregistered card

```bash
curl -k -X POST https://localhost:5443/api/nfc/scan \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "nfc_uid": "FFFFFFFFFFFFFFFF",
    "device_id": "NFC-READER-001",
    "timestamp": "2025-10-26T15:31:00Z",
    "location": "Test Lab"
  }'

# Expected: 200 OK
# {
#   "result": "denied",
#   "reason": "card_not_registered",
#   "message": "NFC card not associated with any user",
#   "timestamp": "2025-10-26T..."
# }
```

✅ **Success! Correctly denied unregistered card**

---

### Test 8: Heartbeat ✅

**Purpose:** Test device heartbeat

```bash
curl -k -X POST https://localhost:5443/api/nfc_devices/heartbeat \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "NFC-READER-001",
    "status": "active",
    "stats": {
      "scans_unsynced": 0,
      "battery_level": 100,
      "nfc_enabled": true
    }
  }'

# Expected: 200 OK
# {
#   "ok": true,
#   "server_time": "2025-10-26T...",
#   "device_status": "active",
#   "commands": []
# }
```

---

### Test 9: Device Info ✅

**Purpose:** Get device information

```bash
curl -k -X GET https://localhost:5443/api/nfc_devices/me \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Expected: 200 OK
# {
#   "id": 1,
#   "device_id": "NFC-READER-001",
#   "name": "Test NFC Reader",
#   "status": "active",
#   "location": "Test Lab",
#   "ip": "127.0.0.1",
#   "last_seen": "2025-10-26T...",
#   "registered_at": "2025-10-26T...",
#   "stats": {
#     "total_scans": 2,
#     "granted_scans": 1,
#     "denied_scans": 1,
#     ...
#   }
# }
```

---

### Test 10: Revoke NFC Card ✅

**Purpose:** Test card revocation

```bash
python -m app.cli revoke-nfc --uid TEST-001

# Then try to scan again
curl -k -X POST https://localhost:5443/api/nfc/scan \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "nfc_uid": "04A3B2C1D4E5F6",
    "device_id": "NFC-READER-001",
    "timestamp": "2025-10-26T15:32:00Z",
    "location": "Test Lab"
  }'

# Expected: 200 OK
# {
#   "result": "denied",
#   "reason": "card_revoked",
#   "message": "NFC card status: revoked",
#   "timestamp": "2025-10-26T..."
# }
```

✅ **Success! Revoked card correctly denied**

---

### Test 11: Batch Scan (Offline Sync) ✅

**Purpose:** Test batch scanning endpoint

```bash
curl -k -X POST https://localhost:5443/api/nfc/scan/batch \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "NFC-READER-001",
    "scans": [
      {
        "nfc_uid": "04A3B2C1D4E5F6",
        "timestamp": "2025-10-26T15:25:00Z",
        "location": "Test Lab"
      },
      {
        "nfc_uid": "FFFFFFFFFFFFFFFF",
        "timestamp": "2025-10-26T15:26:00Z",
        "location": "Test Lab"
      }
    ]
  }'

# Expected: 200 OK
# {
#   "processed": 2,
#   "results": [
#     {
#       "nfc_uid": "04A3B2C1D4E5F6",
#       "result": "denied",
#       "reason": "card_revoked"
#     },
#     {
#       "nfc_uid": "FFFFFFFFFFFFFFFF",
#       "result": "denied",
#       "reason": "card_not_registered"
#     }
#   ]
# }
```

---

### Test 12: Check Audit Trail ✅

**Purpose:** Verify events are being logged

```bash
# In Python console
python

>>> from app.db import SessionLocal
>>> from app.models import Evento
>>> db = SessionLocal()
>>> events = db.query(Evento).filter(Evento.event.like('nfc_%')).all()
>>> for e in events:
...     print(f"{e.event} | {e.actor_uid} | {e.source} | {e.ts}")
>>> 

# Expected output:
# nfc_device_authenticated | None | NFC-READER-001 | 2025-10-26...
# nfc_scan_granted | TEST-001 | NFC-READER-001 | 2025-10-26...
# nfc_scan_denied | None | NFC-READER-001 | 2025-10-26...
# ...
```

✅ **Success! Events are being logged**

---

## ✅ COMPLETE TEST CHECKLIST

- [ ] Server health check passes
- [ ] NFC config endpoint returns configuration
- [ ] Device registration creates device with credentials
- [ ] Device authentication returns JWT token
- [ ] User can be assigned NFC card via CLI
- [ ] NFC scan grants access for valid card
- [ ] NFC scan denies access for unregistered card
- [ ] Heartbeat updates device last_seen
- [ ] Device info returns correct statistics
- [ ] Card revocation prevents access
- [ ] Batch scan processes multiple scans
- [ ] Events are logged to database

---

## 🐛 TROUBLESHOOTING

### Issue: "ImportError: No module named 'jwt'"

**Solution:**
```bash
pip install PyJWT
```

### Issue: "401 Unauthorized" on all authenticated endpoints

**Solution:**
- Check JWT_SECRET_KEY in .env matches what's in nfc_routes.py
- Verify token hasn't expired (24h default)
- Re-authenticate to get new token

### Issue: "500 Internal Server Error" on scan endpoint

**Solution:**
- Check server console for full error
- Verify database has NFC columns (run migration)
- Check that Usuario and NFCDevice models have new fields

### Issue: Device status stays "pending"

**Solution:**
- Device changes to "active" after first successful authentication
- Try authenticating again with correct credentials

### Issue: Events not appearing in database

**Solution:**
- Check that Evento model exists
- Verify database write permissions
- Check server logs for database errors

---

## 📊 TEST RESULTS TEMPLATE

```
IAM_Backend NFC Testing Results
================================
Date: _______________
Tester: _____________

✅ = Pass | ❌ = Fail | ⚠️ = Warning

Test 1:  Server Health Check         [ ]
Test 2:  NFC Config Endpoint          [ ]
Test 3:  Register NFC Device          [ ]
Test 4:  Device Authentication        [ ]
Test 5:  Create Test User             [ ]
Test 6:  NFC Scan - Granted           [ ]
Test 7:  NFC Scan - Denied            [ ]
Test 8:  Heartbeat                    [ ]
Test 9:  Device Info                  [ ]
Test 10: Revoke NFC Card              [ ]
Test 11: Batch Scan                   [ ]
Test 12: Check Audit Trail            [ ]

Notes:
_________________________________
_________________________________
_________________________________

Overall Status: ________________
Ready for Android Integration: [ ]
```

---

## 🎉 SUCCESS CRITERIA

All tests should pass before proceeding to Android app integration!

If all 12 tests pass:
- ✅ IAM_Backend is ready for Android NFC app
- ✅ Proceed to Android integration (Phase 2+)
- ✅ Start testing with real Android device

---

**Testing Complete!** 🚀


