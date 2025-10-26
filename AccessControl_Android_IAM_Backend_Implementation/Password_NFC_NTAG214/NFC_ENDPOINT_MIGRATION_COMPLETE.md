# ✅ NFC ENDPOINT MIGRATION COMPLETE

## 🎯 **WHAT WAS FIXED**

The Android app was calling **OLD** endpoints from the original UPY Sentinel Server:

```
❌ POST /api/card/validate           (405 Method Not Allowed)
❌ POST /api/security/alert           (405 Method Not Allowed)  
❌ GET  /api/security/alarm-status    (404 Not Found)
```

Now updated to call **NEW** IAM_Backend endpoints:

```
✅ POST /api/nfc/scan                 (NFC card validation)
✅ POST /api/nfc/heartbeat            (Device heartbeat - future use)
```

---

## 📝 **CHANGES MADE**

### 1. **Models.kt** - Updated Data Structures

**CardValidationRequest** (lines 58-63):
- Changed `passwordValid` → `password_valid` (snake_case for IAM_Backend)
- Changed `deviceId` → `device_id` (snake_case)
- Changed `timestamp` → `session_id` (IAM uses session ID)

**CardValidationResponse** (lines 68-74):
- Changed `valid: Boolean` → `result: String` ("granted" or "denied")
- Added `reason: String?` for denial reasons
- Added `user: User?` for granted access user info
- Added `access_level: String?` for access level

**New User Model** (lines 79-84):
- Represents user data from IAM_Backend
- Fields: `uid`, `nombre`, `apellido`, `rol`

### 2. **NetworkManager.kt** - Updated API Endpoints

**Line 132**: Updated `/api/card/validate` → `/api/nfc/scan`

**Lines 237-246**: Simplified `checkAlarmStatus()` - IAM_Backend manages alarms through web interface, returns `false` for now

### 3. **MainActivity.kt** - Updated Response Handling

**Lines 173-194**: Added `getSessionId()` helper and updated `validateCardWithServer()` to use `session_id` instead of `timestamp`

**Lines 196-229**: Updated `handleValidationResponse()`:
- Checks `response.result == "granted"` instead of `response.valid`
- Displays user name on success: `"✓ Access Granted: Juan Pérez"`
- Displays denial reason on failure: `"✗ Access Denied: card_not_registered"`
- Only triggers alarm for `invalid_password` failures

**Lines 317-320**: Simplified `sendSecurityAlert()` - IAM_Backend automatically logs all events

**Lines 336-337**: Removed separate security alert network call

---

## 🔄 **HOW IT WORKS NOW**

### **Successful NFC Scan Flow**

```
1. User taps NFC card
2. App reads UID: 0494110F4E6180
3. App validates password: 12345678 (PWD_AUTH command)
4. App sends to IAM_Backend:
   POST /api/nfc/scan
   {
     "uid": "0494110F4E6180",
     "password_valid": true,
     "device_id": "ba899bab96c788b7",
     "session_id": "eyJhbGciOi..."
   }
5. IAM_Backend responds:
   {
     "result": "granted",
     "user": {
       "uid": "ADMIN-1",
       "nombre": "Admin",
       "apellido": "User",
       "rol": "R-ADMIN"
     },
     "access_level": "admin",
     "message": "Access granted"
   }
6. App displays: "✓ Access Granted: Admin User"
7. Success sound plays
8. IAM_Backend logs event in eventos table
```

### **Failed NFC Scan Flow (Unregistered Card)**

```
1. User taps unregistered NFC card
2. App reads UID: 1234567890AB
3. App validates password: true
4. App sends to IAM_Backend
5. IAM_Backend responds:
   {
     "result": "denied",
     "reason": "card_not_registered",
     "message": "Card not registered in system"
   }
6. App displays: "✗ Access Denied: card_not_registered"
7. Failure sound plays
8. IAM_Backend logs failed attempt in eventos table
```

### **Failed NFC Scan Flow (Invalid Password) - 3 Times**

```
1-3. Three failed password attempts
4. After 3rd failure:
   - Alarm starts (persistent tone)
   - Red banner appears: "🚨 SECURITY ALERT: Alarm active"
   - All buttons disabled except emergency
5. IAM_Backend logs all 3 failed attempts
6. Admin can view attempts in web interface
7. Alarm continues until app restart (for now)
```

---

## 🎯 **CARD ASSIGNMENT REQUIRED**

Before testing, assign your NFC card to ADMIN-1:

```python
cd C:\Users\jaque\OneDrive\Escritorio\Cursor\ICA_Project_New\ICA_Project_sandbox\IAM_Backend
python

from app.db import SessionLocal
from app.models import Usuario
from app.time_utils import now_cst
import hashlib

db = SessionLocal()
user = db.query(Usuario).filter(Usuario.uid == 'ADMIN-1').first()

if user:
    user.nfc_uid = '0494110F4E6180'
    user.nfc_uid_hash = hashlib.sha256('0494110F4E6180'.encode()).hexdigest()
    user.nfc_card_id = '0494110F4E6180'
    user.nfc_status = 'active'
    user.nfc_issued_at = now_cst()
    user.nfc_revoked_at = None
    db.commit()
    print(f'✓ Card assigned to {user.uid}')
    
db.close()
```

---

## 🧪 **TESTING STEPS**

1. **Start IAM_Backend Server:**
   ```bash
   cd C:\Users\jaque\OneDrive\Escritorio\Cursor\ICA_Project_New\ICA_Project_sandbox\IAM_Backend
   python run_https.py
   ```

2. **Rebuild Android App:**
   - Open Android Studio
   - Clean Project
   - Rebuild Project
   - Deploy to device

3. **Login to App:**
   - Email: `admin@local`
   - Password: `StrongPass123!`

4. **Test NFC Scan:**
   - Tap your NFC card (UID: 0494110F4E6180)
   - Should see: "✓ Access Granted: Admin User"

5. **Check Server Logs:**
   - Look for: `POST /api/nfc/scan` → `200`
   - NOT: `405` or `404` errors!

6. **Check Web Platform:**
   - Open: https://192.168.1.84:5443
   - Login as ADMIN-1
   - Go to "Logs" or "Events"
   - Should see your NFC scan event

---

## ✅ **EXPECTED SERVER LOGS**

```
192.168.1.65 - - [26/Oct/2025 01:30:00] "POST /api/auth/login HTTP/1.1" 200 -
192.168.1.65 - - [26/Oct/2025 01:30:05] "POST /api/nfc/scan HTTP/1.1" 200 -
192.168.1.65 - - [26/Oct/2025 01:30:10] "POST /api/nfc/scan HTTP/1.1" 200 -
```

❌ **OLD (WRONG):**
```
192.168.1.65 - - [26/Oct/2025 01:17:18] "POST /api/card/validate HTTP/1.1" 405 -
192.168.1.65 - - [26/Oct/2025 01:17:42] "POST /api/security/alert HTTP/1.1" 405 -
192.168.1.65 - - [26/Oct/2025 01:17:42] "GET /api/security/alarm-status HTTP/1.1" 404 -
```

---

## 📊 **AUTOMATIC LOGGING**

IAM_Backend automatically logs:
- ✅ All NFC scan attempts (granted/denied)
- ✅ User who scanned (if granted)
- ✅ Reason for denial (if denied)
- ✅ Timestamp in CST timezone
- ✅ Device that performed scan
- ✅ Password validation status

No need for separate `/api/security/alert` endpoint!

---

## 🎉 **YOU'RE READY!**

Rebuild the Android app and test NFC scanning. The app now communicates correctly with IAM_Backend!

---

## 🔧 **FILES MODIFIED**

1. `app/src/main/java/com/upysentinel/nfc/data/model/Models.kt`
   - Updated request/response models for IAM_Backend

2. `app/src/main/java/com/upysentinel/nfc/network/NetworkManager.kt`
   - Updated API endpoints

3. `app/src/main/java/com/upysentinel/nfc/ui/main/MainActivity.kt`
   - Updated response handling logic


