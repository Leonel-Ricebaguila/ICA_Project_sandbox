# 🚀 Quick Server Setup Guide

**How to connect your Android app to the IAM_Backend server**

---

## 📡 **YOUR SERVER IS RUNNING ON:**

```
✅ https://192.168.1.84:5443
```

This is what you see in your server logs:
```
* Running on https://192.168.1.84:5443
```

---

## 📱 **CONFIGURE ANDROID APP**

### **Method 1: Automatic (Default URL Updated)**

The default URL has been updated to match your server!

```kotlin
// NetworkManager.kt - Already updated!
private const val DEFAULT_BASE_URL = "https://192.168.1.84:5443"
```

**Just rebuild and run the app** - it will automatically use the correct server! ✅

---

### **Method 2: Use Settings Button (If URL Changes)**

If your server IP changes in the future:

1. **Open app** on Android device
2. **Tap ⚙️ button** (top-right of login screen)
3. **Enter:** `https://192.168.1.84:5443`
4. **Tap Save**

---

## 🔍 **UNDERSTANDING THE SERVER ADDRESSES**

Your server logs show:

```
* Running on all addresses (0.0.0.0)        ← Listening on all interfaces
* Running on https://127.0.0.1:5443         ← Localhost (same machine only)
* Running on https://192.168.1.84:5443      ← Network IP (use this!)
```

### **Which to use?**

| Address | When to Use | Works On |
|---------|-------------|----------|
| `127.0.0.1:5443` | Testing on server machine only | ❌ Android device |
| `192.168.1.84:5443` | **Android app on same WiFi** | ✅ Android device |
| `0.0.0.0:5443` | Server binding (not for clients) | ❌ Not a client address |

---

## ✅ **TESTING STEPS**

### **1. Verify Both on Same Network**

Make sure your:
- **PC running IAM_Backend:** Connected to WiFi
- **Android device:** Connected to **SAME WiFi**

Check with:
```bash
# On PC (Windows)
ipconfig

# Look for "Wireless LAN adapter Wi-Fi"
# IPv4 Address: 192.168.1.84  ← Should match server IP
```

---

### **2. Test Server from PC First**

Before testing with Android, verify server works:

```bash
# Open browser or use curl
curl -k https://localhost:5443/health

# Expected: {"status": "ok"} or similar
```

---

### **3. Build and Run Android App**

```bash
# In Android Studio or terminal
./gradlew installDebug

# Then open app on device
```

---

### **4. Test Login**

1. **Open app**
2. **Enter credentials:**
   - Username: (your IAM user)
   - Password: (your IAM password)
3. **Tap LOGIN**

**Expected:** Login successful, redirects to main screen

---

## 🐛 **TROUBLESHOOTING**

### **Issue 1: "Network error: Failed to connect"**

**Possible causes:**

1. **Firewall blocking connection**
   ```bash
   # On PC, allow port 5443
   # Windows Firewall → Allow app → Python
   ```

2. **Different WiFi networks**
   - Check both PC and phone are on **same WiFi**
   - No VPN active on either device

3. **Wrong IP address**
   - Verify server IP: `ipconfig` on PC
   - Check server logs for correct IP

---

### **Issue 2: "SSL/Certificate error"**

**Solution:** App already trusts self-signed certificates! ✅

If you still get errors, check:
- Server is using HTTPS (not HTTP)
- Port is 5443 (not 8443 or other)

---

### **Issue 3: "Server not responding"**

**Check server is running:**
```bash
# Look for this in server logs:
* Running on https://192.168.1.84:5443
Press CTRL+C to quit
```

If server stopped, restart it:
```bash
cd C:\Users\jaque\OneDrive\Escritorio\Cursor\ICA_Project_New\ICA_Project_sandbox\IAM_Backend
python run_https.py
```

---

### **Issue 4: "Cannot connect to 192.168.1.84"**

**Your IP might have changed!**

1. **Check current IP:**
   ```bash
   ipconfig
   # Look for IPv4 Address under "Wireless LAN adapter Wi-Fi"
   ```

2. **If IP changed (e.g., now 192.168.1.100):**
   - Open app
   - Tap ⚙️ button
   - Enter new IP: `https://192.168.1.100:5443`
   - Tap Save

---

## 📊 **NETWORK DIAGRAM**

```
┌─────────────────────────────────────────┐
│  PC (Windows)                           │
│  IP: 192.168.1.84                       │
│                                         │
│  ┌───────────────────────────────────┐ │
│  │ IAM_Backend Server                │ │
│  │ https://192.168.1.84:5443         │ │
│  │ (Python Flask)                    │ │
│  └───────────────────────────────────┘ │
└─────────────────────────────────────────┘
                  │
                  │ WiFi Network
                  │ (192.168.1.x)
                  │
┌─────────────────▼─────────────────────┐
│  Android Device                        │
│  IP: 192.168.1.XXX                     │
│                                        │
│  ┌──────────────────────────────────┐ │
│  │ UPY Sentinel NFC App             │ │
│  │ Server: 192.168.1.84:5443        │ │
│  │ (Kotlin + NFC)                   │ │
│  └──────────────────────────────────┘ │
└────────────────────────────────────────┘
```

---

## 🎯 **QUICK REFERENCE**

### **Your Server Details:**

```
Server IP:   192.168.1.84
Server Port: 5443
Protocol:    HTTPS
Full URL:    https://192.168.1.84:5443
```

### **Android App Configuration:**

```kotlin
// Already configured in NetworkManager.kt
DEFAULT_BASE_URL = "https://192.168.1.84:5443"
```

### **Test Commands:**

```bash
# From PC - Test server
curl -k https://localhost:5443/health

# From another PC on same network
curl -k https://192.168.1.84:5443/health
```

---

## ✅ **VERIFICATION CHECKLIST**

Before testing Android app:

- [ ] Server is running (see "Running on https://192.168.1.84:5443")
- [ ] PC and phone on same WiFi network
- [ ] Firewall allows port 5443
- [ ] Android app default URL is `https://192.168.1.84:5443`
- [ ] App is rebuilt after URL change

---

## 🎉 **READY TO TEST!**

Your configuration:

```
✅ Server running on: https://192.168.1.84:5443
✅ Android app configured: https://192.168.1.84:5443
✅ Both on same WiFi network
✅ Self-signed certificate trusted by app
```

**Next steps:**

1. **Build app:** `./gradlew installDebug`
2. **Open app** on device
3. **Login** with IAM credentials
4. **Test NFC scanning!**

---

## 📞 **NEED HELP?**

### **Check Android App Logs:**

```bash
# In Android Studio, view Logcat
# Filter: "NetworkManager"
# Look for: "Current server: https://..."
```

### **Check Server Logs:**

Look for incoming requests:
```
192.168.1.XXX - - [26/Oct/2025 15:30:00] "POST /api/auth/login HTTP/1.1" 200 -
```

### **Test Network Connectivity:**

From Android device (if you have terminal app):
```bash
ping 192.168.1.84
# Should get responses
```

---

**Created:** October 26, 2025  
**Your Server:** `https://192.168.1.84:5443`  
**Status:** ✅ Ready to connect!


