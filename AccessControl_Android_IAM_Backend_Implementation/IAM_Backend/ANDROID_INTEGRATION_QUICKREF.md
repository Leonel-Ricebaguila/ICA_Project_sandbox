# 📱 Android ↔ IAM Backend Quick Reference

**Quick access guide for Android NFC integration**

---

## 🚀 Quick Start

### Backend Setup (5 minutes)

```bash
# 1. Ensure HTTPS is running
python run_https.py

# 2. Create NFC device in backend
python -m app.cli register-nfc-device \
  --name "NFC Reader - Test" \
  --location "Test Location"

# Output: device_id + device_secret + QR code
```

### Android Setup (First Launch)

```kotlin
// 1. Scan QR code from backend OR
// 2. Enter manually in settings:
//    - Device ID: NFC-READER-001
//    - Device Secret: (base64 string)
//    - Server URL: https://your-server:5443

// 3. App authenticates and stores JWT
```

---

## 🔑 Key Endpoints

### Device Authentication
```http
POST /api/nfc_devices/auth
Body: {device_id, device_secret, location}
→ Returns JWT (valid 24h)
```

### NFC Scan
```http
POST /api/nfc/scan
Headers: Authorization: Bearer <JWT>
Body: {nfc_uid, device_id, timestamp, location}
→ Returns {result: "granted/denied", user, message}
```

### Heartbeat
```http
POST /api/nfc_devices/heartbeat  
Headers: Authorization: Bearer <JWT>
Body: {device_id, status, stats}
→ Every 30 seconds
```

---

## 📝 User NFC Card Assignment

### Method 1: CLI (Recommended)
```bash
python -m app.cli assign-nfc --uid EMP-001
# Prompts to tap NFC card
```

### Method 2: API
```http
POST /api/nfc/assign
Headers: Authorization: Bearer <admin_jwt>
Body: {uid: "EMP-001", nfc_uid: "04A3B2C1D4E5F6"}
```

### Method 3: Web UI
- Navigate to: `https://localhost:5443/app.html`
- Go to: Data Base tab → Users table
- Click: "Assign NFC" button
- Enter or scan NFC UID

---

## 🔒 Security Checklist

### Development
- ✅ HTTPS with self-signed cert (port 5443)
- ✅ Trust all certs (debug mode only)
- ✅ Store JWT in Encrypted SharedPreferences
- ✅ Hash NFC UIDs with SHA-256

### Production
- ✅ HTTPS with CA-issued cert (port 443)
- ✅ Certificate pinning enabled
- ✅ Generate new device secrets
- ✅ Enable ProGuard/R8 obfuscation
- ✅ Implement rate limiting
- ✅ Encrypt offline database

---

## 🛠️ Essential Android Code

### Initialize NFC
```kotlin
val nfcAdapter = NfcAdapter.getDefaultAdapter(this)
nfcAdapter?.enableReaderMode(
    this,
    { tag -> 
        val uid = tag.id.toHexString()
        processNfcScan(uid)
    },
    NfcAdapter.FLAG_READER_NFC_A or FLAG_READER_NFC_B,
    null
)
```

### Scan NFC
```kotlin
suspend fun processNfcScan(uid: String) {
    val response = apiService.scanNfc(
        NfcScanRequest(
            nfcUid = uid,
            nfcUidHash = sha256(uid),
            deviceId = getDeviceId(),
            timestamp = Instant.now().toString(),
            location = getLocation()
        )
    )
    
    when (response.result) {
        "granted" -> showSuccess(response.user)
        "denied" -> showDenied(response.message)
    }
}
```

### Offline Queue
```kotlin
@Entity
data class OfflineScan(
    @PrimaryKey(autoGenerate = true) val id: Int = 0,
    val nfcUid: String,
    val timestamp: Long,
    val synced: Boolean = false
)

// Save when offline
if (!isConnected()) {
    database.offlineScanDao().insert(scan)
}

// Sync later (WorkManager)
val unsynced = database.offlineScanDao().getUnsynced()
unsynced.forEach { apiService.scanNfc(it.toRequest()) }
```

---

## 🐛 Quick Troubleshooting

| Issue | Solution |
|-------|----------|
| **401 Unauthorized** | Token expired → refresh or re-authenticate |
| **NFC not detected** | Enable NFC in Android settings |
| **Card not registered** | Assign NFC UID to user in backend |
| **Network error** | Check HTTPS cert trust, verify server running |
| **Offline mode not working** | Check WorkManager is enqueued, verify Room DB |

---

## 📊 Data Flow

```
User Taps Card
  → Android reads NFC UID
  → Hash UID (SHA-256)
  → POST /api/nfc/scan with JWT
  → Backend validates & looks up user
  → Returns access decision
  → Android shows result (green/red)
  → Backend logs event (signed, chained)
```

---

## 🔧 Testing Commands

### Test Backend
```bash
# Health check
curl -k https://localhost:5443/health

# Device auth (get JWT)
curl -k -X POST https://localhost:5443/api/nfc_devices/auth \
  -H "Content-Type: application/json" \
  -d '{"device_id":"NFC-READER-001","device_secret":"..."}'

# NFC scan
curl -k -X POST https://localhost:5443/api/nfc/scan \
  -H "Authorization: Bearer <JWT>" \
  -H "Content-Type: application/json" \
  -d '{"nfc_uid":"04A3B2C1D4E5F6","device_id":"NFC-READER-001",...}'
```

### Test Android
```kotlin
// Emulator: Use Android Device Manager to simulate NFC
// Physical: Tap real NFC cards

// Check logs
adb logcat | grep "NFC"
```

---

## 📱 Android Dependencies

```gradle
dependencies {
    // Networking
    implementation 'com.squareup.retrofit2:retrofit:2.9.0'
    implementation 'com.squareup.retrofit2:converter-gson:2.9.0'
    implementation 'com.squareup.okhttp3:logging-interceptor:4.11.0'
    
    // Security
    implementation 'androidx.security:security-crypto:1.1.0-alpha06'
    
    // Offline
    implementation 'androidx.room:room-runtime:2.5.2'
    kapt 'androidx.room:room-compiler:2.5.2'
    
    // Background tasks
    implementation 'androidx.work:work-runtime-ktx:2.8.1'
}
```

---

## 📚 Full Documentation

- **Complete Integration Guide:** `ANDROID_NFC_INTEGRATION.md` (80+ pages)
- **HTTPS Setup:** `HTTPS_SETUP_GUIDE.md`
- **Backend Main:** `README.md`
- **Setup Summary:** `SETUP_COMPLETE.md`

---

## 🎯 Production Deployment

1. **Backend:**
   - Replace self-signed cert with Let's Encrypt
   - Use PostgreSQL instead of SQLite
   - Set HTTPS_PORT=443 in .env
   - Configure firewall rules

2. **Android:**
   - Enable ProGuard/R8 minification
   - Implement certificate pinning
   - Build signed release APK
   - Test on multiple devices/Android versions

3. **Testing:**
   - End-to-end test with real NFC cards
   - Load testing (1000+ scans/hour)
   - Security audit (pen test)
   - User acceptance testing

---

## 💡 Best Practices

✅ **Always validate NFC UIDs** before sending to backend  
✅ **Implement exponential backoff** for failed requests  
✅ **Use encrypted storage** for all sensitive data  
✅ **Log events locally** for debugging, not sensitive data  
✅ **Keep JWT tokens refreshed** (1h before expiry)  
✅ **Implement offline queue** for reliability  
✅ **Monitor heartbeats** on backend dashboard  
✅ **Version your API** for backward compatibility  

---

**Need more details?** See `ANDROID_NFC_INTEGRATION.md` for complete guide.

**Last Updated:** October 25, 2025


