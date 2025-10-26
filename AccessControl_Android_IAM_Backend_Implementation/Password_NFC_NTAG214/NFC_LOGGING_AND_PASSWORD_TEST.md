# 🔧 NFC LOGGING & PASSWORD VALIDATION TEST GUIDE

## 🐛 **BUGS FIXED**

I found and fixed **critical logging bugs** in IAM_Backend:

### **Bug 1: Invalid Password Attempts NOT Logged** ❌ FIXED ✅
- **Problem:** When a card had wrong password, server returned denial but never saved to database
- **Fix:** Added logging + `db.commit()` for invalid_password events
- **Lines:** 86-106 in `nfc_routes.py`

### **Bug 2: Other Denial Events NOT Committed** ❌ FIXED ✅
- **Problem:** Card not registered, user inactive, and card revoked events weren't committed
- **Fix:** Added `db.commit()` after each `db.add(event)`
- **Lines:** 123, 144, 165 in `nfc_routes.py`

---

## 🔄 **RESTART THE SERVER**

The server needs to be restarted to apply the fixes:

**1. Stop the current server:**
- Go to the terminal running IAM_Backend
- Press `Ctrl+C`

**2. Start it again:**
```bash
cd C:\Users\jaque\OneDrive\Escritorio\Cursor\ICA_Project_New\ICA_Project_sandbox\IAM_Backend
python run_https.py
```

**3. Verify it's running:**
```
* Running on https://192.168.1.84:5443
```

---

## 📊 **TEST 1: Check Existing Logs in Database**

Let's see what's currently in the database:

```bash
cd C:\Users\jaque\OneDrive\Escritorio\Cursor\ICA_Project_New\ICA_Project_sandbox\IAM_Backend
sqlite3 iam.db
```

Then run these queries:

### **A. See All Events:**
```sql
SELECT id, tipo, uid, resultado, timestamp 
FROM eventos 
ORDER BY id DESC 
LIMIT 20;
```

### **B. Count Events by Type:**
```sql
SELECT event, COUNT(*) as count 
FROM eventos 
GROUP BY event;
```

### **C. See NFC-Related Events:**
```sql
SELECT id, event, actor_uid, source, context, timestamp 
FROM eventos 
WHERE event LIKE '%nfc%' 
ORDER BY id DESC 
LIMIT 10;
```

**Copy and paste the output here** so I can see what's being logged.

To exit SQLite:
```sql
.quit
```

---

## 🧪 **TEST 2: Invalid Password Detection**

Now let's test if the system properly detects **valid UID but invalid password**.

### **Scenario:**
- UID: `0494110F4E6180` (registered to ADMIN-1) ✅
- Password: **WRONG** (not `12345678`) ❌

### **How to Create This Scenario:**

**Option A: Use a Different Card**
- Find another NTAG214 card
- It will have a different UID AND wrong password
- This tests "card_not_registered"

**Option B: Change Your Card's Password (ADVANCED)**

⚠️ **WARNING:** This will make your card temporarily unusable until you reprogram it!

Use the **Card Programming** screen in your Android app:

1. Open the app
2. Go to "Program Card" (if you have this screen)
3. Set a DIFFERENT password (not `12345678`)
4. Now when you scan it:
   - UID will still be `0494110F4E6180` ✅
   - Password will be WRONG ❌
   - Should trigger `invalid_password` event

**Option C: Manually Test via Python (SIMULATION)**

We can simulate the invalid password scenario:

```python
cd C:\Users\jaque\OneDrive\Escritorio\Cursor\ICA_Project_New\ICA_Project_sandbox\IAM_Backend
python

import requests
import json

# Your test data
url = "https://192.168.1.84:5443/api/nfc/scan"
data = {
    "uid": "0494110F4E6180",
    "password_valid": False,  # ← SIMULATING WRONG PASSWORD
    "device_id": "test_device",
    "session_id": "test_session"
}

# Disable SSL warnings for testing
import urllib3
urllib3.disable_warnings()

# Send request
response = requests.post(url, json=data, verify=False)

print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")
```

Expected output:
```json
{
  "result": "denied",
  "reason": "invalid_password",
  "message": "NFC card password validation failed",
  "timestamp": "2025-10-26T01:45:00-06:00"
}
```

Then check database:
```sql
SELECT * FROM eventos WHERE event='nfc_scan_denied' AND context LIKE '%invalid_password%';
```

---

## 📱 **TEST 3: Android App Test Flow**

### **Test A: Registered Card with Correct Password** ✅✅
```
1. Tap card: 0494110F4E6180
2. Password: 12345678 (correct)
3. Expected: "✓ Access Granted: Admin User"
4. Server log: POST /api/nfc/scan 200
5. Database: event='nfc_scan_granted'
```

### **Test B: Unregistered Card** ❌✅
```
1. Tap different card: XXXXXXXXXXXX
2. Password: (any)
3. Expected: "✗ Access Denied: card_not_registered"
4. Server log: POST /api/nfc/scan 200
5. Database: event='nfc_scan_denied', reason='card_not_registered'
```

### **Test C: Registered Card with WRONG Password** ✅❌
```
1. Tap card: 0494110F4E6180
2. Password: WRONG (not 12345678)
3. Expected: "✗ Access Denied: invalid_password"
4. Server log: POST /api/nfc/scan 200
5. Database: event='nfc_scan_denied', reason='invalid_password'  ← NEW!
```

---

## 🌐 **TEST 4: Check Web Dashboard**

After running tests, check the IAM_Backend web interface:

1. Open browser: `https://192.168.1.84:5443`
2. Login as ADMIN-1
3. Go to **"Logs"** or **"Events"** section
4. You should now see:
   - ✅ All successful scans
   - ✅ All denied scans (with reasons!)
   - ✅ Timestamps
   - ✅ Device IDs

---

## 📋 **WHAT TO REPORT BACK**

Please run these commands and share the output:

### **1. Check Current Events:**
```bash
sqlite3 iam.db "SELECT id, event, actor_uid, context, timestamp FROM eventos ORDER BY id DESC LIMIT 10;"
```

### **2. Test Invalid Password (Python simulation):**
Run the Python script above and share:
- Response status code
- Response JSON
- Database query result

### **3. Scan Cards:**
- Scan your registered card (0494110F4E6180)
- Scan an unregistered card
- Check server logs
- Share what the app displayed

### **4. Web Dashboard:**
- Screenshot or describe what you see in the "Logs" section

---

## 🎯 **EXPECTED RESULTS AFTER FIX**

### **Before Fix:** ❌
- Invalid password attempts: **NOT logged**
- Card not registered: **NOT logged**
- Web dashboard: **EMPTY or incomplete**

### **After Fix:** ✅
- Invalid password attempts: **LOGGED** ✓
- Card not registered: **LOGGED** ✓
- User inactive: **LOGGED** ✓
- Card revoked: **LOGGED** ✓
- Access granted: **LOGGED** ✓
- Web dashboard: **SHOWS EVERYTHING** ✓

---

## 🚀 **LET'S TEST!**

Start with **TEST 1** (check database) and share the output.

Then we'll move to **TEST 2** (invalid password) and **TEST 3** (Android app).

Ready? Let's go! 🎉


