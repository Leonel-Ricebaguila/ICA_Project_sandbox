# 🎯 DASHBOARD NFC FEATURES IMPLEMENTATION GUIDE

## 📋 **THREE FEATURES TO IMPLEMENT**

1. ✅ **Show NFC login events in dashboard logs** (EASY - Already working, just need formatting)
2. 🔧 **List active NFC devices** (MEDIUM - Need new API endpoint + UI)
3. 🚨 **Stop alarm from dashboard** (MEDIUM - Need alarm management system)

---

## ✅ **FEATURE 1: SHOW NFC LOGIN EVENTS IN DASHBOARD**

### **Current Status:**
Looking at your logs, NFC logins ARE being logged:
```
event ID 93: login_success_pending_qr | ADMIN-1 | {"session_id": "***48b66d", ...}
event ID 95: login_success_pending_qr | ADMIN-1 | {"session_id": "***fd7e5c", ...}
```

### **The Issue:**
The dashboard probably shows these events, but they're not clearly labeled as "NFC Reader Login" vs "Web Dashboard Login".

### **Solution:**
We need to differentiate between:
- Web dashboard logins (from 192.168.1.84)
- NFC reader logins (from 192.168.1.65 - your phone)

**This requires modifying the login event to include the source device type.**

---

## 🔧 **FEATURE 2: LIST ACTIVE NFC DEVICES**

### **What We Need:**

1. **Track NFC devices** in the `devices_nfc` table (already exists!)
2. **Update last_seen** timestamp when device logs in or scans
3. **Create API endpoint** to list active devices
4. **Add UI section** in dashboard to show devices

### **Step 1: Check Current Device Tracking**

Run this to see what's in the devices table:

```bash
cd C:\Users\jaque\OneDrive\Escritorio\Cursor\ICA_Project_New\ICA_Project_sandbox\IAM_Backend
sqlite3 iam.db "SELECT id, nombre, device_id, registered_at, stats_json FROM devices_nfc;"
```

### **Step 2: Create API Endpoint for Active Devices**

We need to add this to `nfc_routes.py`:

```python
@bp.get("/devices/active")
def get_active_devices():
    """
    Get list of active NFC reader devices
    
    Response:
    {
        "devices": [
            {
                "id": 1,
                "nombre": "NFC Reader 1",
                "device_id": "ba899bab96c788b7",
                "last_seen": "2025-10-26T02:16:25-06:00",
                "status": "online",  // online if last_seen < 5 min ago
                "scans_today": 15
            }
        ]
    }
    """
    with DB() as db:
        devices = db.query(NFCDevice).all()
        
        result = []
        for device in devices:
            # Calculate status based on last_seen
            if device.last_seen:
                time_diff = (now_cst() - device.last_seen).total_seconds()
                status = "online" if time_diff < 300 else "offline"  # 5 minutes
            else:
                status = "offline"
            
            # Count today's scans
            today_start = now_cst().replace(hour=0, minute=0, second=0, microsecond=0)
            scans_today = db.query(Evento).filter(
                Evento.source == device.device_id,
                Evento.timestamp >= today_start,
                Evento.event.like('%nfc_scan%')
            ).count()
            
            result.append({
                "id": device.id,
                "nombre": device.nombre,
                "device_id": device.device_id,
                "last_seen": device.last_seen.isoformat() if device.last_seen else None,
                "status": status,
                "scans_today": scans_today
            })
        
        return jsonify({"devices": result})
```

### **Step 3: Update last_seen on Every Scan**

In `nfc_routes.py`, in the `/scan` endpoint, add:

```python
# After successful scan, update device last_seen
device = db.query(NFCDevice).filter(NFCDevice.device_id == device_id).first()
if device:
    device.last_seen = now_cst()
```

### **Step 4: Add UI to Dashboard**

This would require modifying `app.html` or creating a new section to display devices.

---

## 🚨 **FEATURE 3: STOP ALARM FROM DASHBOARD**

### **Current Alarm System:**

From your Android app code:
- Alarm triggers after 3 failed attempts in 1 minute
- Alarm plays persistent sound
- Currently: `checkAlarmStatus()` returns `false` (no remote stop)

### **What We Need:**

1. **Track alarm state** in database (which device has alarm active)
2. **API endpoint** to stop alarm remotely
3. **Dashboard UI** to show devices in alarm state and stop button
4. **Android app update** to actually check and stop alarm

### **Implementation:**

#### **Step 1: Create Alarm Commands Table**

```bash
sqlite3 iam.db
```

```sql
CREATE TABLE IF NOT EXISTS alarm_commands (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id TEXT NOT NULL,
    command TEXT NOT NULL,  -- 'stop_alarm' or 'start_alarm'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed BOOLEAN DEFAULT 0,
    processed_at TIMESTAMP
);

CREATE INDEX idx_alarm_commands_device ON alarm_commands(device_id, processed);
```

#### **Step 2: Add Alarm Stop Endpoint**

In `nfc_routes.py`:

```python
@bp.post("/alarm/stop")
def stop_device_alarm():
    """
    Send command to stop alarm on specific device
    
    Request:
    {
        "device_id": "ba899bab96c788b7"
    }
    """
    data = request.get_json() or {}
    device_id = data.get("device_id")
    
    if not device_id:
        return jsonify({"error": "device_id required"}), 400
    
    with DB() as db:
        # Create stop alarm command
        from app.models import text
        db.execute(text("""
            INSERT INTO alarm_commands (device_id, command, processed)
            VALUES (:device_id, 'stop_alarm', 0)
        """), {"device_id": device_id})
        db.commit()
        
        # Log admin action
        admin_uid = request.args.get('uid', 'system')
        event = Evento(
            event="alarm_stop_command",
            actor_uid=admin_uid,
            source="web_dashboard",
            context={
                "target_device": device_id,
                "action": "stop_alarm"
            }
        )
        db.add(event)
        db.commit()
        
        return jsonify({"success": True, "message": "Stop alarm command sent"})
```

#### **Step 3: Check Alarm Status Endpoint**

Update the existing `checkAlarmStatus()` to actually query the database:

```python
@bp.get("/alarm/status/<device_id>")
def check_alarm_status(device_id):
    """
    Check if device should stop alarm
    
    Response:
    {
        "should_stop": true/false
    }
    """
    with DB() as db:
        # Check for unprocessed stop commands
        from app.models import text
        result = db.execute(text("""
            SELECT id FROM alarm_commands
            WHERE device_id = :device_id
            AND command = 'stop_alarm'
            AND processed = 0
            ORDER BY created_at DESC
            LIMIT 1
        """), {"device_id": device_id}).fetchone()
        
        if result:
            # Mark as processed
            db.execute(text("""
                UPDATE alarm_commands
                SET processed = 1, processed_at = CURRENT_TIMESTAMP
                WHERE id = :id
            """), {"id": result[0]})
            db.commit()
            
            return jsonify({"should_stop": True})
        
        return jsonify({"should_stop": False})
```

#### **Step 4: Update Android App**

Update `NetworkManager.kt`:

```kotlin
suspend fun checkAlarmStatus(): Result<Boolean> = withContext(Dispatchers.IO) {
    try {
        val deviceId = getAndroidDeviceId()
        val request = Request.Builder()
            .url("${getBaseUrl()}/api/nfc/alarm/status/$deviceId")
            .get()
            .build()
        
        val response = client.newCall(request).execute()
        
        if (response.isSuccessful) {
            val responseBody = response.body?.string()
            val jsonResponse = gson.fromJson(responseBody, Map::class.java)
            val shouldStop = jsonResponse["should_stop"] as? Boolean ?: false
            Result.success(shouldStop)
        } else {
            Result.failure(Exception("Server error: ${response.code}"))
        }
    } catch (e: Exception) {
        Result.failure(e)
    }
}
```

---

## 🎯 **QUICK WIN: SIMPLEST IMPLEMENTATION**

If you want to start with the EASIEST feature:

### **Show Current Devices in Database**

```bash
sqlite3 iam.db "SELECT id, nombre, device_id, last_seen FROM devices_nfc;"
```

This will show if your Android device is already tracked!

---

## 📝 **WHAT DO YOU WANT TO IMPLEMENT FIRST?**

Choose one:

**A) Show active NFC devices** (easier - just add API + view data)
**B) Stop alarm from dashboard** (needs alarm tracking system)
**C) Both** (full implementation)

Let me know which one you want, and I'll implement it step by step!

---

## 🔍 **CURRENT STATUS CHECK**

First, let's see what devices are currently in the database:

```bash
cd C:\Users\jaque\OneDrive\Escritorio\Cursor\ICA_Project_New\ICA_Project_sandbox\IAM_Backend
sqlite3 iam.db "SELECT * FROM devices_nfc;"
```

**Run this and share the output!** This will tell us if your Android device is already being tracked. 📱


