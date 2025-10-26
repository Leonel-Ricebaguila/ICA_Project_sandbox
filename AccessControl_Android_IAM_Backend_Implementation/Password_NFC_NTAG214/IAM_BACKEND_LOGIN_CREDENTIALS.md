# 🔐 IAM_Backend Login Credentials Guide

**How to access IAM_Backend from your Android NFC app**

---

## ✅ **DEFAULT CREDENTIALS (AUTO-CREATED)**

When the IAM_Backend server starts for the first time, it **automatically creates** a default admin user:

### **Default Admin Account**

```
Username: ADMIN-1
Email:    admin@local
Password: StrongPass123!
Role:     R-ADM (Administrator)
```

---

## 📱 **HOW TO LOGIN FROM ANDROID APP**

### **Step 1: Open the Android App**

The app will show the login screen.

### **Step 2: Enter Credentials**

```
Username Field: ADMIN-1
Password Field: StrongPass123!
```

### **Step 3: Tap LOGIN**

The app will:
1. Send credentials to server: `https://192.168.1.84:5443/api/auth/login`
2. Receive authentication token
3. Activate device automatically
4. Redirect to main screen

---

## 🎯 **QUICK REFERENCE CARD**

```
╔════════════════════════════════════════╗
║     IAM_BACKEND LOGIN CREDENTIALS      ║
╠════════════════════════════════════════╣
║ Username: ADMIN-1                      ║
║ Password: StrongPass123!               ║
║ Role:     Administrator                ║
╚════════════════════════════════════════╝
```

**Copy & paste into app:**
- Username: `ADMIN-1`
- Password: `StrongPass123!`

---

## 👥 **CREATING ADDITIONAL USERS**

### **Option 1: Using CLI (Recommended)**

From the IAM_Backend directory:

```bash
# Create another admin
python -m app.cli create-admin \
  --uid ADMIN-2 \
  --email admin2@local \
  --password YourPassword123!

# Create regular user (employee)
python -m app.cli create-user \
  --uid EMP-001 \
  --email employee1@local \
  --password Pass123! \
  --role R-EMP

# Create monitor user
python -m app.cli create-user \
  --uid MON-001 \
  --email monitor@local \
  --password Pass123! \
  --role R-MON
```

### **Option 2: Using Web Interface**

1. Login with `ADMIN-1` credentials
2. Navigate to Users section
3. Click "Add User"
4. Fill in details and save

---

## 🔑 **USER ROLES AVAILABLE**

| Role Code | Role Name | Description |
|-----------|-----------|-------------|
| `R-ADM` | Administrator | Full system access |
| `R-MON` | Monitor | View-only access |
| `R-IM` | Manager | Manage users and permissions |
| `R-AC` | Access Control | Manage access cards |
| `R-EMP` | Employee | Standard employee access |
| `R-GRD` | Guard | Security guard access |
| `R-AUD` | Auditor | Audit log access |

---

## 🔐 **PASSWORD REQUIREMENTS**

When creating new users, passwords must have:

- ✅ Minimum 8 characters
- ✅ At least 1 uppercase letter
- ✅ At least 1 lowercase letter
- ✅ At least 1 number
- ✅ At least 1 special character (!@#$%^&*)

**Example valid passwords:**
- `StrongPass123!`
- `MyPassword1!`
- `Secure@Pass99`

---

## 🧪 **TESTING THE LOGIN**

### **Test 1: Login with Default Admin**

```bash
# Using curl (from PC)
curl -k -X POST https://localhost:5443/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "ADMIN-1",
    "password": "StrongPass123!",
    "deviceId": "test-device"
  }'
```

**Expected Response:**
```json
{
  "success": true,
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "message": "Login successful"
}
```

### **Test 2: Login from Android App**

1. **Open app**
2. **Enter:**
   - Username: `ADMIN-1`
   - Password: `StrongPass123!`
3. **Tap LOGIN**
4. **Expected:** Redirects to main screen ✅

---

## ⚠️ **TROUBLESHOOTING**

### **Issue 1: "Invalid username or password"**

**Solutions:**
1. **Check username is exactly:** `ADMIN-1` (case-sensitive)
2. **Check password is exactly:** `StrongPass123!` (with exclamation mark)
3. **Verify server is running** (check server console logs)
4. **Check database:** Admin user might not have been created

### **Issue 2: "Admin user not found"**

**Solution:** Check if admin was created by server startup:

```bash
# Check server logs for:
[startup] Default admin created: ADMIN-1 admin@local
```

If not found, create manually:
```bash
python -m app.cli create-admin \
  --uid ADMIN-1 \
  --email admin@local \
  --password StrongPass123!
```

### **Issue 3: "Network error: Failed to connect"**

**Solutions:**
1. **Verify server is running:**
   ```
   * Running on https://192.168.1.84:5443
   ```

2. **Check Android app server URL:**
   - Tap ⚙️ button
   - Verify: `https://192.168.1.84:5443`

3. **Verify both on same WiFi**

### **Issue 4: "Device activation failed"**

**Solution:** This happens after successful login. Check:
1. Server received device activation request
2. Device ID is being sent correctly
3. Server logs show the activation

---

## 📊 **USER DATABASE STRUCTURE**

Default admin user in database:

```sql
-- Check if admin exists
SELECT uid, email, rol, estado 
FROM usuarios 
WHERE uid = 'ADMIN-1';

-- Expected result:
-- uid: ADMIN-1
-- email: admin@local
-- rol: R-ADM
-- estado: active
```

---

## 🔄 **CHANGING DEFAULT PASSWORD**

### **For Security: Change default password!**

**Option 1: Using CLI**
```bash
python -m app.cli reset-password \
  --uid ADMIN-1 \
  --new-password YourNewPassword123!
```

**Option 2: Using Web Interface**
1. Login as ADMIN-1
2. Go to Profile → Change Password
3. Enter new password
4. Save

**Option 3: Direct SQL (not recommended)**
```sql
-- Hash your password first, then update
UPDATE usuarios 
SET password_hash = '...' 
WHERE uid = 'ADMIN-1';
```

---

## 📝 **CREATE TEST USERS FOR ANDROID TESTING**

### **Create a test employee for NFC card testing:**

```bash
# Create employee user
python -m app.cli create-user \
  --uid TEST-EMP-001 \
  --email test@local \
  --password Test123! \
  --role R-EMP \
  --nombre "Test" \
  --apellido "Employee"

# Assign NFC card to test user
python -m app.cli assign-nfc \
  --uid TEST-EMP-001 \
  --nfc-uid 04A3B2C1D4E5F6
```

Now you can:
1. Login to app with `ADMIN-1`
2. Scan NFC card with UID `04A3B2C1D4E5F6`
3. System will recognize it as TEST-EMP-001

---

## 🎯 **ANDROID APP LOGIN FLOW**

```
┌─────────────────────────────────────────┐
│ 1. User enters credentials             │
│    Username: ADMIN-1                    │
│    Password: StrongPass123!             │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│ 2. App sends POST to /api/auth/login   │
│    {                                    │
│      "username": "ADMIN-1",             │
│      "password": "StrongPass123!",      │
│      "deviceId": "android-device-id"    │
│    }                                    │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│ 3. Server validates credentials        │
│    ✓ Username exists                    │
│    ✓ Password matches hash              │
│    ✓ User status is active              │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│ 4. Server returns JWT token             │
│    {                                    │
│      "success": true,                   │
│      "token": "eyJ...",                 │
│      "message": "Login successful"      │
│    }                                    │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│ 5. App stores token in SharedPrefs     │
│    Key: "auth_token"                    │
│    Value: JWT token                     │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│ 6. App sends POST to /api/device/activate│
│    {                                    │
│      "deviceId": "...",                 │
│      "authToken": "...",                │
│      "deviceInfo": {...}                │
│    }                                    │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│ 7. Device activated successfully       │
│    Navigate to main screen              │
│    Ready to scan NFC cards!             │
└─────────────────────────────────────────┘
```

---

## 🔍 **CHECKING LOGIN IN SERVER LOGS**

When you login successfully, you should see in server logs:

```
[2025-10-26 15:30:00] INFO: Login attempt for user: ADMIN-1
[2025-10-26 15:30:00] INFO: Login successful for ADMIN-1
192.168.1.XXX - - [26/Oct/2025 15:30:00] "POST /api/auth/login HTTP/1.1" 200 -
192.168.1.XXX - - [26/Oct/2025 15:30:01] "POST /api/device/activate HTTP/1.1" 200 -
```

---

## 📋 **QUICK TEST CHECKLIST**

Before testing Android app login:

- [ ] IAM_Backend server is running
- [ ] Server shows: `Running on https://192.168.1.84:5443`
- [ ] Default admin user exists (check server startup logs)
- [ ] Android app server URL is `https://192.168.1.84:5443`
- [ ] Both PC and phone on same WiFi
- [ ] You know the credentials: `ADMIN-1` / `StrongPass123!`

---

## 🎉 **READY TO LOGIN!**

### **Your Credentials:**

```
╔════════════════════════════════════════╗
║  Username: ADMIN-1                     ║
║  Password: StrongPass123!              ║
║  Server:   https://192.168.1.84:5443   ║
╚════════════════════════════════════════╝
```

### **Steps:**

1. ✅ Open Android app
2. ✅ Enter username: `ADMIN-1`
3. ✅ Enter password: `StrongPass123!`
4. ✅ Tap LOGIN
5. ✅ Should redirect to main screen!

---

## 📞 **SUPPORT**

### **Check if admin user exists:**

```bash
# In Python console
from app.db import SessionLocal
from app.models import Usuario

db = SessionLocal()
admin = db.query(Usuario).filter(Usuario.uid == 'ADMIN-1').first()

if admin:
    print(f"✅ Admin exists: {admin.email}")
    print(f"   Role: {admin.rol}")
    print(f"   Status: {admin.estado}")
else:
    print("❌ Admin user not found!")
    print("   Create with: python -m app.cli create-admin ...")
```

### **Create admin if missing:**

```bash
python -m app.cli create-admin \
  --uid ADMIN-1 \
  --email admin@local \
  --password StrongPass123!
```

---

**Created:** October 26, 2025  
**Default Username:** `ADMIN-1`  
**Default Password:** `StrongPass123!`  
**Server URL:** `https://192.168.1.84:5443`  
**Status:** ✅ Ready to login!


