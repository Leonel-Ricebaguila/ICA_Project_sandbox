# 🐛 Dashboard Devices Not Updating Issue

## Problem

Your server logs show scans at **12:46:42** and **12:46:52**, but the dashboard shows:
- Last seen: **12:35:34** (11 minutes behind!)

This means the dashboard is not using our new `/api/nfc/devices/active` endpoint, or it's showing **cached data**.

---

## Solutions

### **Option 1: Check if Dashboard Uses Our Endpoint**

The dashboard table shows `IP: 127.0.0.41` which is a **hardcoded value** from the database.

Our API returns actual `device_id: ba899bab96c788b7`.

**Question:** Does the dashboard call `/api/nfc/devices/active`?

Check your browser's **Network tab** (F12) when you load the Access Control page:
- Look for calls to `/api/nfc/devices/active`
- Or look for calls to `/devices_nfc` or similar

**If it's NOT calling our endpoint**, then the dashboard code needs to be updated.

### **Option 2: Force Refresh Dashboard Data**

Try these:
1. Hard refresh: `Ctrl+F5` or `Ctrl+Shift+R`
2. Clear browser cache
3. Logout and login again

### **Option 3: Update Database Manually**

To test if the dashboard reads from the database:

```bash
cd C:\Users\jaque\OneDrive\Escritorio\Cursor\ICA_Project_New\ICA_Project_sandbox\IAM_Backend
sqlite3 iam.db "UPDATE devices_nfc SET last_seen = CURRENT_TIMESTAMP WHERE id=1;"
sqlite3 iam.db "SELECT * FROM devices_nfc;"
```

Then refresh the dashboard to see if it updates.

---

## Why Dashboard Shows Old Data

Looking at your logs:

- Dashboard accessed at **12:46:06** (line 19)
- Your scans happened at **12:46:42** and **12:46:52**

The dashboard **was already loaded** before you scanned the cards!

**Fix:** Refresh the Access Control tab after scanning a card.

---

## Verify Dashboard is Reading Database

Run this to see if dashboard shows updated data:

```bash
sqlite3 iam.db "SELECT id, name, last_seen, device_id FROM devices_nfc;"
```

Check what the dashboard shows vs what's in the database.

---

## Quick Test

1. Open dashboard in browser
2. Go to Access Control tab
3. Run: `python debug_active_devices.py` (to see what API returns)
4. Refresh dashboard - does it update?

**Share the output!**

