# QUICK START - TEST NFC NOW!

**Status:** READY TO TEST  
**Time Required:** 5 minutes

---

## WHAT WE JUST DID

I successfully implemented the NFC routes in IAM_Backend!

- Added 12 database columns
- Created 4 API endpoints  
- Registered the NFC blueprint
- Tested server startup

**Everything is ready for you to test!**

---

## START TESTING IN 3 STEPS

### STEP 1: Start the Server (1 minute)

```bash
cd C:\Users\jaque\OneDrive\Escritorio\Cursor\ICA_Project_New\ICA_Project_sandbox\IAM_Backend
python run_https.py
```

**Leave this terminal open!** The server needs to stay running.

---

### STEP 2: Assign Your First NFC Card (2 minutes)

**Open a NEW terminal** and run:

```bash
cd C:\Users\jaque\OneDrive\Escritorio\Cursor\ICA_Project_New\ICA_Project_sandbox\IAM_Backend
python -c "from app.db import SessionLocal; from app.models import Usuario; from app.time_utils import now_cst; import hashlib; db = SessionLocal(); user = db.query(Usuario).filter(Usuario.uid == 'ADMIN-1').first(); test_uid = '04A1B2C3D4E5F6'; user.nfc_uid = test_uid if user else None; user.nfc_uid_hash = hashlib.sha256(test_uid.encode()).hexdigest() if user else None; user.nfc_card_id = test_uid if user else None; user.nfc_status = 'active' if user else None; user.nfc_issued_at = now_cst() if user else None; db.commit() if user else None; print(f'[OK] NFC card assigned to ADMIN-1: {test_uid}') if user else print('[X] User not found'); db.close()"
```

This assigns a test NFC UID to your admin user.

[!] **IMPORTANT:** Replace `'04A1B2C3D4E5F6'` with your ACTUAL NFC card UID!

**Don't know your card UID?** Try tapping it in the app first - the server logs will show "card_not_registered" with the last 4 digits.

---

### STEP 3: Test with Android App (2 minutes)

1. **Open the Android app**
2. **Login:**
   - Email: `admin@local`
   - Password: `StrongPass123!`
3. **Tap your NFC card**

---

## WHAT YOU'LL SEE

### Server Terminal (First Terminal)

When you tap the card, you'll see:

```
192.168.1.65 - - [26/Oct/2025 XX:XX:XX] "POST /api/nfc/scan HTTP/1.1" 200 -
```

**200 = SUCCESS!**

### Android App

If the card is registered:
```
ACCESS GRANTED
User: Admin User
Role: R-ADMIN
```

If the card is NOT registered yet:
```
ACCESS DENIED
Reason: Card not registered
```

---

## TROUBLESHOOTING

### Problem: "Card not registered"

**Solution:**
1. Check server logs for the UID
2. Assign it using Step 2 above (with the correct UID)
3. Try tapping again

### Problem: Server won't start

**Check:**
```bash
cd C:\Users\jaque\OneDrive\Escritorio\Cursor\ICA_Project_New\ICA_Project_sandbox\IAM_Backend
python -c "from app import create_app; app = create_app(); print('[OK]')"
```

### Problem: Android app says "Connection failed"

**Check:**
1. Server is running (terminal 1)
2. IP is correct: `https://192.168.1.84:5443`
3. Phone and computer on same network

---

## HOW TO GET YOUR CARD UID

### Method 1: Let the App Tell You

1. Don't assign the card yet
2. Tap the card in the app
3. Look at server logs - they show the last 4 digits
4. Or check Android logcat:
   ```bash
   adb logcat | grep -i "uid"
   ```

### Method 2: Use NFC Tools App

1. Install "NFC Tools" from Play Store
2. Tap your card
3. Look for "Serial number" or "UID"
4. Copy it (format: `04:A1:B2:C3:D4:E5:F6`)
5. Remove colons when assigning: `04A1B2C3D4E5F6`

---

## QUICK COMMAND REFERENCE

### Start Server
```bash
cd C:\Users\jaque\OneDrive\Escritorio\Cursor\ICA_Project_New\ICA_Project_sandbox\IAM_Backend
python run_https.py
```

### Assign Card (replace UID!)
```bash
cd C:\Users\jaque\OneDrive\Escritorio\Cursor\ICA_Project_New\ICA_Project_sandbox\IAM_Backend
python
```
Then paste:
```python
from app.db import SessionLocal
from app.models import Usuario
from app.time_utils import now_cst
import hashlib

db = SessionLocal()
user = db.query(Usuario).filter(Usuario.uid == 'ADMIN-1').first()

if user:
    card_uid = '04A1B2C3D4E5F6'  # CHANGE THIS!
    user.nfc_uid = card_uid
    user.nfc_uid_hash = hashlib.sha256(card_uid.encode()).hexdigest()
    user.nfc_card_id = card_uid
    user.nfc_status = 'active'
    user.nfc_issued_at = now_cst()
    db.commit()
    print(f'[OK] Card {card_uid} assigned to {user.uid}')
else:
    print('[X] User not found')

db.close()
```

### Check Database
```bash
cd C:\Users\jaque\OneDrive\Escritorio\Cursor\ICA_Project_New\ICA_Project_sandbox\IAM_Backend
sqlite3 iam.db "SELECT uid, nfc_uid, nfc_status FROM usuarios WHERE nfc_uid IS NOT NULL;"
```

### Check Devices
```bash
sqlite3 iam.db "SELECT device_id, name, last_seen FROM devices_nfc;"
```

### Check Event Logs
```bash
sqlite3 iam.db "SELECT id, ts, event, actor_uid FROM eventos WHERE event LIKE '%nfc%' ORDER BY id DESC LIMIT 5;"
```

---

## YOUR SETUP

**Server Location:**
```
C:\Users\jaque\OneDrive\Escritorio\Cursor\ICA_Project_New\ICA_Project_sandbox\IAM_Backend
```

**Server URL:**
```
https://192.168.1.84:5443
```

**Login:**
```
Email:    admin@local
Password: StrongPass123!
```

**Android App:**
```
C:\Users\jaque\AndroidStudioProjects\Password_NFC_NTAG214
```

---

## API ENDPOINTS WORKING NOW

```
POST /api/nfc/scan        - Validates NFC cards
POST /api/nfc/heartbeat   - Device status updates
POST /api/nfc/assign      - Assign cards to users
GET  /api/nfc/devices     - List all devices
```

---

## TESTING CHECKLIST

- [ ] Server started successfully
- [ ] Assigned NFC card to ADMIN-1
- [ ] Android app installed and open
- [ ] Logged into app
- [ ] Tapped NFC card
- [ ] Saw "Access Granted" or "Access Denied"
- [ ] Checked server logs (200 response)

---

## WHAT TO EXPECT

### First Card Tap (Card not assigned yet)

**Android App:**
```
ACCESS DENIED
Card not registered
```

**Server Log:**
```
192.168.1.65 - - [...] "POST /api/nfc/scan HTTP/1.1" 200 -
```

**Event logged:**
```json
{
  "event": "nfc_scan_denied",
  "reason": "card_not_registered"
}
```

### After Assigning Card

**Android App:**
```
ACCESS GRANTED
Name: Admin User
Role: R-ADMIN
```

**Server Log:**
```
192.168.1.65 - - [...] "POST /api/nfc/scan HTTP/1.1" 200 -
```

**Event logged:**
```json
{
  "event": "nfc_scan_granted",
  "actor_uid": "ADMIN-1",
  "user_rol": "R-ADMIN"
}
```

---

## IF SOMETHING DOESN'T WORK

1. **Check server is running** (terminal 1 should be active)
2. **Check server logs** (any errors?)
3. **Check Android logcat:**
   ```bash
   adb logcat | grep -i "network\|nfc\|main"
   ```
4. **Verify database:**
   ```bash
   sqlite3 iam.db "SELECT * FROM usuarios WHERE uid='ADMIN-1';"
   ```

---

## READY?

1. Open terminal → Start server
2. Open another terminal → Assign card
3. Open Android app → Login
4. Tap card → See result!

**GO TEST IT NOW!**

---

**Created:** October 26, 2025, 01:00  
**Status:** READY FOR TESTING  
**Estimated test time:** 5 minutes


