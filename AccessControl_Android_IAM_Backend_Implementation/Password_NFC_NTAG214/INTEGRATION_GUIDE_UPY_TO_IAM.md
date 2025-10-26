# 🔄 UPY Sentinel NFC App → IAM Backend Integration Guide

**Complete Migration Documentation for Cursor AI Assistant**

**Version:** 1.0  
**Date:** October 26, 2025  
**Status:** Migration Planning Phase

---

## 📋 Table of Contents

1. [Executive Summary](#executive-summary)
2. [Current System Overview](#current-system-overview)
3. [Target System Overview](#target-system-overview)
4. [Architecture Comparison](#architecture-comparison)
5. [Integration Strategy](#integration-strategy)
6. [Phase-by-Phase Migration Plan](#phase-by-phase-migration-plan)
7. [API Endpoint Mapping](#api-endpoint-mapping)
8. [Security Protocol Changes](#security-protocol-changes)
9. [Data Model Changes](#data-model-changes)
10. [Code Changes Required](#code-changes-required)
11. [Testing Strategy](#testing-strategy)
12. [Rollback Plan](#rollback-plan)
13. [Post-Migration Checklist](#post-migration-checklist)

---

## 📊 Executive Summary

### Current State
- **App Name:** UPY Sentinel NFC Reader
- **Package:** `com.upysentinel.nfc`
- **Purpose:** Standalone NFC password validation system
- **Server:** Simple Flask server with SQLite database
- **Authentication:** Device activation + user login
- **NFC Protocol:** NTAG214 password validation (PWD_AUTH 0x1B command)
- **Security:** HTTPS with self-signed certificates, JWT tokens

### Target State
- **App Name:** UPY Sentinel NFC Reader (updated)
- **Package:** `com.upysentinel.nfc` (same)
- **Purpose:** IAM-integrated NFC device for access control
- **Server:** IAM_Backend platform (comprehensive IAM system)
- **Authentication:** IAM device registration + JWT management
- **NFC Protocol:** UID-based user mapping (no password on card)
- **Security:** IAM-compliant HTTPS, JWT with refresh, heartbeat monitoring

### Migration Goals
✅ Integrate with IAM_Backend without breaking existing functionality  
✅ Maintain security standards and improve monitoring  
✅ Add offline support with sync capabilities  
✅ Enable multi-device management from IAM dashboard  
✅ Support role-based access control (RBAC)  
✅ Provide audit trail integration  

---

## 🏗️ Current System Overview

### Current App Structure

```
Password_NFC_NTAG214/
├── app/src/main/
│   ├── java/com/upysentinel/nfc/
│   │   ├── audio/
│   │   │   └── AudioFeedbackManager.kt      # Success/failure sounds + alarm
│   │   ├── data/model/
│   │   │   └── Models.kt                     # Data classes + SecurityUtils
│   │   ├── network/
│   │   │   └── NetworkManager.kt             # Retrofit API client
│   │   ├── nfc/
│   │   │   └── NFCManager.kt                 # NFC operations (UID, PWD_AUTH)
│   │   └── ui/
│   │       ├── login/
│   │       │   └── LoginActivity.kt          # User login + device activation
│   │       ├── main/
│   │       │   └── MainActivity.kt           # NFC scanning interface
│   │       └── programming/
│   │           └── CardProgrammingActivity.kt # Card enrollment
│   └── res/
│       ├── layout/                           # Activity layouts
│       ├── values/                           # Strings, colors, themes
│       └── drawable*/                        # Icons, logos
└── build.gradle.kts                          # Dependencies & configuration
```

### Current Server Structure

```
UPY_Sentinel_Server/
├── server.py                # Flask server with API endpoints
├── db.py                    # SQLite database utilities
├── cli.py                   # Command-line interface
├── cert.pem                 # SSL certificate
├── key.pem                  # SSL private key
└── upy_sentinel.db          # SQLite database
```

### Current Data Models

**Android App (Models.kt):**
```kotlin
data class NFCCard(
    val uid: String,
    val hash: String,      // Not used anymore (changed to password)
    val salt: String,      // Not used anymore
    val timestamp: Long
)

data class LoginRequest(
    val username: String,
    val password: String,
    val deviceId: String
)

data class CardValidationRequest(
    val uid: String,
    val passwordValid: Boolean,  // Result of PWD_AUTH
    val deviceId: String,
    val timestamp: Long
)

data class CardValidationResponse(
    val valid: Boolean,
    val message: String,
    val isCloned: Boolean,
    val securityAlert: Boolean
)

data class SecurityAlert(
    val deviceId: String,
    val uid: String?,
    val alertType: AlertType,
    val timestamp: Long,
    val failureCount: Int
)
```

**Current Server Database Schema:**
```sql
-- users table
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    username TEXT UNIQUE,
    password_hash TEXT,
    salt TEXT,
    created_at TIMESTAMP
);

-- devices table
CREATE TABLE devices (
    id INTEGER PRIMARY KEY,
    device_id TEXT UNIQUE,
    activated BOOLEAN,
    last_seen TIMESTAMP
);

-- cards table
CREATE TABLE cards (
    id INTEGER PRIMARY KEY,
    uid TEXT UNIQUE,
    password TEXT,
    created_at TIMESTAMP
);

-- access_logs table
CREATE TABLE access_logs (
    id INTEGER PRIMARY KEY,
    uid TEXT,
    device_id TEXT,
    success BOOLEAN,
    timestamp TIMESTAMP
);

-- security_alerts table
CREATE TABLE security_alerts (
    id INTEGER PRIMARY KEY,
    device_id TEXT,
    alert_type TEXT,
    timestamp TIMESTAMP,
    processed BOOLEAN
);
```

### Current API Endpoints

| Endpoint | Method | Purpose | Request | Response |
|----------|--------|---------|---------|----------|
| `/api/auth/login` | POST | User login | `{username, password, deviceId}` | `{success, token}` |
| `/api/device/activate` | POST | Device activation | `{deviceId, authToken, deviceInfo}` | `{success}` |
| `/api/card/validate` | POST | Validate NFC card | `{uid, passwordValid, deviceId, timestamp}` | `{valid, message}` |
| `/api/card/register` | POST | Register new card | `{card: {uid}, authToken}` | `{success}` |
| `/api/security/alert` | POST | Report security alert | `{deviceId, uid, alertType, timestamp, failureCount}` | `{success}` |
| `/api/security/alarm-status` | GET | Check alarm stop command | Header: `X-Device-ID` | `{stop_alarm, message}` |

### Current NFC Protocol

**Card Reading (MainActivity.kt):**
1. User taps NTAG214 card
2. Read UID from card
3. Execute PWD_AUTH command (0x1B + password bytes)
4. Send UID + passwordValid to server
5. Display result (granted/denied)
6. Trigger audio feedback

**Card Programming (CardProgrammingActivity.kt):**
1. Admin enters programming mode
2. User taps blank NTAG214 card
3. Write password (12345678) to pages 0xE5-0xE6
4. Register UID with server
5. Card ready for use

### Current Security Features

**Transport Security:**
- HTTPS with self-signed certificates (port 8443)
- TLS 1.2+ enforcement
- Certificate validation (trust all in dev mode)

**Authentication:**
- User login with password (hashed + salted)
- Device activation with unique device ID
- JWT tokens (stored in SharedPreferences)
- Session management (basic)

**Authorization:**
- User-level authentication
- Device activation required
- Card validation against database

**Alarm System:**
- 3 failures in 1 minute → alarm mode
- Persistent alarm sound
- Stop only from server CLI
- Device locks during alarm

---

## 🎯 Target System Overview

### IAM_Backend Architecture

```
IAM_Backend/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI/Flask app
│   ├── models.py                  # SQLAlchemy models
│   ├── database.py                # Database connection
│   ├── auth.py                    # Authentication logic
│   ├── cli.py                     # CLI commands
│   ├── api/
│   │   ├── __init__.py
│   │   ├── auth.py                # Auth endpoints
│   │   ├── nfc.py                 # NFC device endpoints
│   │   ├── users.py               # User management
│   │   └── devices.py             # Device management
│   ├── core/
│   │   ├── security.py            # Security utilities
│   │   ├── jwt.py                 # JWT token management
│   │   └── audit.py               # Audit trail (Ed25519 signed)
│   └── utils/
│       ├── hash.py                # Hashing utilities
│       └── validators.py          # Input validation
├── alembic/                       # Database migrations
├── certs/                         # SSL certificates
├── logs/                          # Application logs
├── .env                           # Environment configuration
├── requirements.txt               # Python dependencies
└── run_https.py                   # HTTPS server startup
```

### IAM_Backend Data Models

**Database Schema:**
```sql
-- usuarios (users) table
CREATE TABLE usuarios (
    id INTEGER PRIMARY KEY,
    uid VARCHAR(32) UNIQUE NOT NULL,
    email VARCHAR UNIQUE NOT NULL,
    nombre VARCHAR NOT NULL,
    apellido VARCHAR NOT NULL,
    password_hash VARCHAR NOT NULL,
    salt VARCHAR NOT NULL,
    rol VARCHAR NOT NULL,              -- R-ADMIN, R-IAM, R-EMP, etc.
    activo BOOLEAN DEFAULT TRUE,
    qr_secret VARCHAR,                 -- For 2FA
    nfc_uid VARCHAR(32) UNIQUE,        -- NFC card UID
    nfc_uid_hash VARCHAR(64),          -- SHA-256 of UID
    nfc_card_id VARCHAR(32),           -- Physical card ID
    nfc_status VARCHAR(20) DEFAULT 'inactive',
    nfc_issued_at TIMESTAMP,
    nfc_revoked_at TIMESTAMP,
    created_at TIMESTAMP,
    last_login TIMESTAMP
);

-- devices_nfc table
CREATE TABLE devices_nfc (
    id INTEGER PRIMARY KEY,
    device_id VARCHAR(64) UNIQUE NOT NULL,
    name VARCHAR NOT NULL,
    device_secret VARCHAR NOT NULL,
    ip VARCHAR,
    port INTEGER,
    status VARCHAR NOT NULL DEFAULT 'pending',
    location VARCHAR,
    last_seen TIMESTAMP,
    registered_at TIMESTAMP,
    android_version VARCHAR,
    app_version VARCHAR,
    stats_json JSON
);

-- eventos (events/audit trail) table
CREATE TABLE eventos (
    id INTEGER PRIMARY KEY,
    tipo VARCHAR NOT NULL,
    descripcion TEXT,
    uid VARCHAR,                       -- User who triggered event
    device_id VARCHAR,                 -- Device that recorded event
    timestamp TIMESTAMP NOT NULL,
    signature VARCHAR,                 -- Ed25519 signature
    prev_hash VARCHAR,                 -- Previous event hash (blockchain-like)
    metadata JSON
);

-- sesiones (sessions) table
CREATE TABLE sesiones (
    id INTEGER PRIMARY KEY,
    token VARCHAR UNIQUE NOT NULL,
    uid VARCHAR NOT NULL,
    device_type VARCHAR,               -- 'nfc_device', 'web', 'mobile'
    created_at TIMESTAMP,
    expires_at TIMESTAMP,
    last_activity TIMESTAMP,
    ip VARCHAR
);
```

### IAM_Backend API Endpoints

**Device Management:**
```http
POST   /api/nfc_devices/auth        # Device authentication
POST   /api/nfc_devices/heartbeat   # Device heartbeat (every 30s)
GET    /api/nfc_devices/me          # Get device info
PUT    /api/nfc_devices/me          # Update device info
GET    /api/nfc_devices/config      # Get server configuration
```

**NFC Operations:**
```http
POST   /api/nfc/scan                # Scan NFC card
POST   /api/nfc/scan/batch          # Batch scan (offline sync)
POST   /api/nfc/assign              # Assign NFC card to user (admin)
POST   /api/nfc/self-enroll         # Self-enrollment (optional)
GET    /api/nfc/user/:uid           # Get user by NFC UID
```

**User Management:**
```http
GET    /api/users                   # List all users
GET    /api/users/:uid              # Get specific user
POST   /api/users                   # Create user (admin)
PUT    /api/users/:uid              # Update user
DELETE /api/users/:uid              # Delete user (admin)
```

**Authentication:**
```http
POST   /api/auth/login              # User login (web/admin)
POST   /api/auth/logout             # User logout
POST   /api/auth/refresh            # Refresh JWT token
GET    /api/auth/verify             # Verify token validity
```

**Audit & Monitoring:**
```http
GET    /api/events                  # Get audit events
GET    /api/events/stream           # SSE stream (real-time)
GET    /api/devices/status          # Get all device statuses
GET    /api/dashboard/stats         # Dashboard statistics
```

### IAM_Backend Security Features

**Transport Security:**
- HTTPS with proper certificate management
- TLS 1.2+ enforcement
- Certificate pinning support for production
- Port 5443 (dev) or 443 (prod)

**Authentication:**
- Multi-factor authentication (Password + QR code)
- JWT tokens with proper expiration
- Device-specific authentication
- Session management with refresh
- Rate limiting (3 attempts, 10 min lockout)

**Authorization:**
- Role-Based Access Control (7 roles):
  - R-ADMIN (System Administrator)
  - R-IAM (IAM Administrator)
  - R-AUD (Auditor)
  - R-SEC (Security Officer)
  - R-EMP (Employee)
  - R-CEO (Executive)
  - R-VIS (Visitor)
- Permission-based access control
- Time-based access rules (optional)

**Audit Trail:**
- Ed25519-signed event chain
- Tamper-evident blockchain-like structure
- Real-time SSE streaming
- Complete access history

**Device Management:**
- Device registration with secrets
- Heartbeat monitoring (30s interval)
- Status tracking (active/inactive/error)
- Remote device management
- Multi-device support

---

## 🔄 Architecture Comparison

### Authentication Flow Comparison

**Current System (UPY Sentinel):**
```
┌─────────────┐
│   Android   │
│     App     │
└──────┬──────┘
       │ 1. Login (username, password, deviceId)
       ▼
┌─────────────┐
│   Server    │
│  (Flask)    │
└──────┬──────┘
       │ 2. Validate credentials
       │ 3. Generate JWT
       ▼
┌─────────────┐
│   SQLite    │
│  Database   │
└─────────────┘
```

**IAM_Backend System:**
```
┌─────────────┐
│   Android   │
│  NFC Device │
└──────┬──────┘
       │ 1. Device auth (device_id, device_secret)
       ▼
┌─────────────┐
│ IAM Backend │
│  (Flask +   │
│ SQLAlchemy) │
└──────┬──────┘
       │ 2. Validate device credentials
       │ 3. Check device status (active?)
       │ 4. Generate device JWT (24h validity)
       │ 5. Log authentication event (signed)
       ▼
┌─────────────┐
│ PostgreSQL/ │
│   SQLite    │
└─────────────┘
```

### NFC Scan Flow Comparison

**Current System:**
```
Card Tap → Read UID → PWD_AUTH (0x1B) → Validate Password
                                              ↓
                                        Send to Server
                                              ↓
                                     Check UID in DB
                                              ↓
                                      Grant/Deny Access
```

**IAM_Backend System:**
```
Card Tap → Read UID only → Hash UID (SHA-256)
                                ↓
                          Send to Server
                                ↓
                     Lookup user by nfc_uid
                                ↓
                     Validate user status
                                ↓
                      Check access rules
                                ↓
                       Grant/Deny Access
                                ↓
                    Log event (Ed25519 signed)
                                ↓
                   SSE broadcast to monitors
```

### Data Flow Comparison

**Current System (Simple):**
```
Android App ←─ HTTPS ─→ Flask Server ←─→ SQLite DB
                 ↑
                JWT
```

**IAM_Backend System (Comprehensive):**
```
┌──────────────┐
│  Android App │
│ (NFC Device) │
└──────┬───────┘
       │
       │ HTTPS/TLS (Device JWT)
       │ • Scan NFC
       │ • Heartbeat (30s)
       │ • Offline sync
       │
       ▼
┌──────────────────────────────┐
│      IAM Backend             │
│  • Device authentication     │
│  • User validation           │
│  • RBAC enforcement          │
│  • Event logging (signed)    │
│  • Real-time monitoring      │
└──────┬───────────────────────┘
       │
       ├─→ Database (PostgreSQL/SQLite)
       │   • Users with NFC UIDs
       │   • Devices registration
       │   • Events (audit trail)
       │   • Sessions
       │
       ├─→ SSE Stream (Real-time)
       │   • Event broadcast
       │   • Device status
       │
       └─→ Web Dashboard
           • User management
           • Device monitoring
           • Audit trail viewer
           • Access control
```

---

## 🚀 Integration Strategy

### Migration Philosophy

**Incremental Migration Approach:**
1. ✅ Keep existing app structure
2. ✅ Replace server backend with IAM_Backend
3. ✅ Update API endpoints and models
4. ✅ Add new features (offline, heartbeat, etc.)
5. ✅ Test thoroughly at each phase
6. ✅ Maintain backward compatibility where possible

**Key Principles:**
- **Non-Disruptive:** Maintain app functionality throughout migration
- **Security-First:** Enhance security at every step
- **Feature-Additive:** Add IAM features without removing existing ones
- **Test-Driven:** Comprehensive testing at each phase
- **Rollback-Ready:** Ability to revert changes if needed

### Migration Phases

```
Phase 0: Preparation (Current)
  └─→ Documentation
  └─→ Code analysis
  └─→ Testing environment setup

Phase 1: Server Setup (Week 1)
  └─→ Install IAM_Backend
  └─→ Configure database
  └─→ Create initial users
  └─→ Register NFC device

Phase 2: Authentication Migration (Week 1-2)
  └─→ Update NetworkManager for IAM endpoints
  └─→ Implement device authentication
  └─→ Update JWT token management
  └─→ Add token refresh logic

Phase 3: NFC Protocol Migration (Week 2)
  └─→ Remove password validation logic
  └─→ Implement UID-only scanning
  └─→ Update card validation endpoint
  └─→ Test with registered cards

Phase 4: New Features (Week 3)
  └─→ Implement offline queue (Room DB)
  └─→ Add heartbeat worker
  └─→ Implement sync worker
  └─→ Add device status monitoring

Phase 5: UI/UX Updates (Week 3-4)
  └─→ Update layouts for new features
  └─→ Add offline mode indicator
  └─→ Add device status display
  └─→ Improve error messages

Phase 6: Testing & Refinement (Week 4)
  └─→ Unit tests
  └─→ Integration tests
  └─→ End-to-end tests
  └─→ Performance testing
  └─→ Security audit

Phase 7: Deployment (Week 5)
  └─→ Production server setup
  └─→ Certificate configuration
  └─→ App deployment
  └─→ User training
  └─→ Monitoring setup
```

---

## 📋 Phase-by-Phase Migration Plan

### Phase 0: Preparation (Current Phase)

**Objectives:**
- ✅ Complete documentation
- ✅ Set up IAM_Backend test environment
- ✅ Create test users and devices
- ✅ Verify both systems work independently

**Tasks:**

1. **Install IAM_Backend:**
   ```bash
   cd C:\Users\jaque\OneDrive\Escritorio\Cursor\ICA_Project_New\ICA_Project_sandbox\IAM_Backend
   
   # Create virtual environment
   python -m venv venv
   venv\Scripts\activate
   
   # Install dependencies
   pip install -r requirements.txt
   
   # Generate SSL certificates
   python generate_certs.py --cn localhost --days 365
   
   # Setup environment
   python setup_env.py
   
   # Initialize database
   python -m app.cli init-db
   
   # Start HTTPS server
   python run_https.py
   ```

2. **Create Test Users:**
   ```bash
   # Create admin user
   python -m app.cli create-admin --uid ADMIN-001 --email admin@upy.local --password Admin123!
   
   # Create test employee
   python -m app.cli create-user --uid EMP-001 --email emp1@upy.local --password Emp123! --role R-EMP --nombre John --apellido Doe
   ```

3. **Register NFC Device:**
   ```bash
   python -m app.cli register-nfc-device --name "UPY Sentinel NFC Reader" --location "Main Entrance"
   
   # Note the output:
   # Device ID: NFC-READER-001
   # Device Secret: <base64_secret>
   ```

4. **Assign NFC Cards:**
   ```bash
   # Assign NFC card to test employee
   python -m app.cli assign-nfc --uid EMP-001
   # Tap card when prompted
   ```

5. **Test IAM_Backend:**
   ```bash
   # Health check
   curl -k https://localhost:5443/health
   
   # Test device auth
   curl -k -X POST https://localhost:5443/api/nfc_devices/auth \
     -H "Content-Type: application/json" \
     -d '{"device_id":"NFC-READER-001","device_secret":"<secret>","location":"Test"}'
   ```

**Deliverables:**
- ✅ Working IAM_Backend instance
- ✅ Test users created
- ✅ NFC device registered
- ✅ Test cards assigned
- ✅ This documentation complete

---

### Phase 1: Server Setup & Configuration

**Objectives:**
- Configure IAM_Backend for production use
- Set up proper certificates
- Configure database properly
- Test all IAM endpoints

**Tasks:**

1. **Configure .env file:**
   ```bash
   # C:\Users\jaque\OneDrive\Escritorio\Cursor\ICA_Project_New\ICA_Project_sandbox\IAM_Backend\.env
   
   # Server Configuration
   HTTPS_PORT=5443
   FLASK_ENV=development
   SECRET_KEY=<generated_secret_key>
   
   # Database
   DATABASE_URL=sqlite:///./iam_upy.db
   
   # JWT Configuration
   JWT_SECRET_KEY=<generated_jwt_secret>
   JWT_ALGORITHM=HS256
   NFC_DEVICE_JWT_EXP_SECONDS=86400  # 24 hours
   
   # NFC Configuration
   NFC_UID_HASH_ALGORITHM=sha256
   NFC_HEARTBEAT_INTERVAL=30
   NFC_HEARTBEAT_TIMEOUT=120
   
   # Security
   RATE_LIMIT_ENABLED=true
   RATE_LIMIT_MAX_ATTEMPTS=3
   RATE_LIMIT_WINDOW_MINUTES=10
   ```

2. **Database Schema Verification:**
   ```bash
   # Verify all tables exist
   python -m app.cli verify-db
   
   # Expected tables:
   # - usuarios
   # - devices_nfc
   # - eventos
   # - sesiones
   ```

3. **Create Device Credentials Document:**
   ```
   Document the following for Android app:
   - Server URL: https://<server_ip>:5443
   - Device ID: NFC-READER-001
   - Device Secret: <base64_secret>
   - Location: Main Entrance
   ```

**Deliverables:**
- ✅ IAM_Backend fully configured
- ✅ Database schema verified
- ✅ Device credentials documented
- ✅ Server accessible from Android device network

---

### Phase 2: Authentication Migration

**Objectives:**
- Update Android app to authenticate with IAM_Backend
- Implement proper JWT token management
- Add token refresh logic
- Remove old login system

**Code Changes Required:**

**1. Update NetworkManager.kt:**

```kotlin
// File: app/src/main/java/com/upysentinel/nfc/network/NetworkManager.kt

class NetworkManager(private val context: Context) {
    
    companion object {
        // CHANGE: Update server URL to IAM_Backend
        private const val BASE_URL = "https://192.168.1.84:5443/"  // Update with actual IAM server IP
        private const val TIMEOUT_SECONDS = 30L
    }
    
    // NEW: Device authentication request/response models
    data class DeviceAuthRequest(
        @SerializedName("device_id") val deviceId: String,
        @SerializedName("device_secret") val deviceSecret: String,
        val location: String,
        @SerializedName("android_version") val androidVersion: String,
        @SerializedName("app_version") val appVersion: String
    )
    
    data class DeviceAuthResponse(
        val token: String,
        @SerializedName("expires_at") val expiresAt: Long,
        @SerializedName("device_info") val deviceInfo: DeviceInfo
    )
    
    data class DeviceInfo(
        val id: Int,
        val name: String,
        val status: String,
        val location: String,
        @SerializedName("last_seen") val lastSeen: String
    )
    
    // NEW: Device authentication method
    suspend fun authenticateDevice(
        deviceId: String,
        deviceSecret: String,
        location: String
    ): Result<DeviceAuthResponse> = withContext(Dispatchers.IO) {
        try {
            val request = DeviceAuthRequest(
                deviceId = deviceId,
                deviceSecret = deviceSecret,
                location = location,
                androidVersion = Build.VERSION.RELEASE,
                appVersion = getAppVersion()
            )
            
            val response = client.newCall(
                Request.Builder()
                    .url("${BASE_URL}api/nfc_devices/auth")
                    .post(gson.toJson(request).toRequestBody("application/json".toMediaType()))
                    .build()
            ).execute()
            
            if (response.isSuccessful) {
                val authResponse = gson.fromJson(
                    response.body?.string(),
                    DeviceAuthResponse::class.java
                )
                Result.success(authResponse)
            } else {
                Result.failure(Exception("Authentication failed: ${response.code}"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
    
    // REMOVE: Old login method
    // suspend fun login(...) { ... }
    
    // REMOVE: Old device activation method
    // suspend fun activateDevice(...) { ... }
    
    private fun getAppVersion(): String {
        return try {
            val packageInfo = context.packageManager.getPackageInfo(context.packageName, 0)
            packageInfo.versionName
        } catch (e: Exception) {
            "1.0.0"
        }
    }
}
```

**2. Create TokenManager.kt:**

```kotlin
// File: app/src/main/java/com/upysentinel/nfc/auth/TokenManager.kt

package com.upysentinel.nfc.auth

import android.content.Context
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

class TokenManager(private val context: Context) {
    
    private val masterKey = MasterKey.Builder(context)
        .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
        .build()
    
    private val securePrefs = EncryptedSharedPreferences.create(
        context,
        "device_auth_prefs",
        masterKey,
        EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
        EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
    )
    
    companion object {
        private const val KEY_DEVICE_TOKEN = "device_jwt"
        private const val KEY_TOKEN_EXPIRES_AT = "jwt_expires_at"
        private const val KEY_DEVICE_ID = "device_id"
        private const val KEY_DEVICE_SECRET = "device_secret"
        private const val KEY_LOCATION = "device_location"
        
        // Refresh token 1 hour before expiry
        private const val REFRESH_THRESHOLD_SECONDS = 3600
    }
    
    private var cachedToken: String? = null
    private var expiresAt: Long = 0
    
    suspend fun getToken(): String? = withContext(Dispatchers.IO) {
        // Return cached if valid
        if (cachedToken != null && !isExpired() && !needsRefresh()) {
            return@withContext cachedToken
        }
        
        // Load from storage
        cachedToken = securePrefs.getString(KEY_DEVICE_TOKEN, null)
        expiresAt = securePrefs.getLong(KEY_TOKEN_EXPIRES_AT, 0)
        
        // Refresh if needed
        if (needsRefresh()) {
            refreshToken()
        }
        
        cachedToken
    }
    
    suspend fun refreshToken(): Boolean = withContext(Dispatchers.IO) {
        val deviceId = securePrefs.getString(KEY_DEVICE_ID, null) ?: return@withContext false
        val deviceSecret = securePrefs.getString(KEY_DEVICE_SECRET, null) ?: return@withContext false
        val location = securePrefs.getString(KEY_LOCATION, null) ?: ""
        
        try {
            val networkManager = NetworkManager(context)
            val result = networkManager.authenticateDevice(deviceId, deviceSecret, location)
            
            result.fold(
                onSuccess = { response ->
                    saveToken(response.token, response.expiresAt)
                    true
                },
                onFailure = {
                    false
                }
            )
        } catch (e: Exception) {
            false
        }
    }
    
    fun saveToken(token: String, expiresAt: Long) {
        cachedToken = token
        this.expiresAt = expiresAt
        
        securePrefs.edit().apply {
            putString(KEY_DEVICE_TOKEN, token)
            putLong(KEY_TOKEN_EXPIRES_AT, expiresAt)
            apply()
        }
    }
    
    fun saveDeviceCredentials(deviceId: String, deviceSecret: String, location: String) {
        securePrefs.edit().apply {
            putString(KEY_DEVICE_ID, deviceId)
            putString(KEY_DEVICE_SECRET, deviceSecret)
            putString(KEY_LOCATION, location)
            apply()
        }
    }
    
    fun getDeviceId(): String? = securePrefs.getString(KEY_DEVICE_ID, null)
    
    fun getLocation(): String? = securePrefs.getString(KEY_LOCATION, null)
    
    fun clearCredentials() {
        cachedToken = null
        expiresAt = 0
        securePrefs.edit().clear().apply()
    }
    
    private fun isExpired(): Boolean {
        return System.currentTimeMillis() / 1000 > expiresAt
    }
    
    fun needsRefresh(): Boolean {
        return System.currentTimeMillis() / 1000 > (expiresAt - REFRESH_THRESHOLD_SECONDS)
    }
    
    fun isAuthenticated(): Boolean {
        return cachedToken != null && !isExpired()
    }
}
```

**3. Update LoginActivity.kt:**

```kotlin
// File: app/src/main/java/com/upysentinel/nfc/ui/login/LoginActivity.kt

class LoginActivity : AppCompatActivity() {
    
    private lateinit var tokenManager: TokenManager
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityLoginBinding.inflate(layoutInflater)
        setContentView(binding.root)
        
        tokenManager = TokenManager(this)
        
        // Check if device is already authenticated
        if (tokenManager.isAuthenticated()) {
            navigateToMain()
            return
        }
        
        // CHANGE: Show device setup screen instead of login
        setupDeviceAuthentication()
    }
    
    private fun setupDeviceAuthentication() {
        binding.apply {
            // Update UI to show device credentials input
            usernameInput.hint = "Device ID"
            passwordInput.hint = "Device Secret"
            loginButton.text = "Activate Device"
            
            loginButton.setOnClickListener {
                val deviceId = usernameInput.text.toString()
                val deviceSecret = passwordInput.text.toString()
                val location = "Main Entrance"  // Or from input
                
                if (deviceId.isNotEmpty() && deviceSecret.isNotEmpty()) {
                    authenticateDevice(deviceId, deviceSecret, location)
                } else {
                    showError("Please enter device credentials")
                }
            }
        }
    }
    
    private fun authenticateDevice(deviceId: String, deviceSecret: String, location: String) {
        binding.loginButton.isEnabled = false
        binding.progressBar.visibility = View.VISIBLE
        
        lifecycleScope.launch {
            try {
                val networkManager = NetworkManager(this@LoginActivity)
                val result = networkManager.authenticateDevice(deviceId, deviceSecret, location)
                
                result.fold(
                    onSuccess = { response ->
                        // Save credentials and token
                        tokenManager.saveDeviceCredentials(deviceId, deviceSecret, location)
                        tokenManager.saveToken(response.token, response.expiresAt)
                        
                        withContext(Dispatchers.Main) {
                            showSuccess("Device activated successfully")
                            navigateToMain()
                        }
                    },
                    onFailure = { exception ->
                        withContext(Dispatchers.Main) {
                            showError("Authentication failed: ${exception.message}")
                            binding.loginButton.isEnabled = true
                            binding.progressBar.visibility = View.GONE
                        }
                    }
                )
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    showError("Error: ${e.message}")
                    binding.loginButton.isEnabled = true
                    binding.progressBar.visibility = View.GONE
                }
            }
        }
    }
    
    private fun navigateToMain() {
        startActivity(Intent(this, MainActivity::class.java))
        finish()
    }
    
    // REMOVE: Old login logic
    // private fun performLogin(...) { ... }
    // private fun activateDevice(...) { ... }
}
```

**4. Add AuthInterceptor.kt:**

```kotlin
// File: app/src/main/java/com/upysentinel/nfc/network/AuthInterceptor.kt

package com.upysentinel.nfc.network

import android.content.Context
import com.upysentinel.nfc.auth.TokenManager
import kotlinx.coroutines.runBlocking
import okhttp3.Interceptor
import okhttp3.Response

class AuthInterceptor(private val context: Context) : Interceptor {
    
    private val tokenManager = TokenManager(context)
    
    override fun intercept(chain: Interceptor.Chain): Response {
        val original = chain.request()
        
        // Skip auth for authentication endpoint
        if (original.url.encodedPath.contains("/api/nfc_devices/auth")) {
            return chain.proceed(original)
        }
        
        // Get token (with refresh if needed)
        val token = runBlocking {
            tokenManager.getToken()
        }
        
        // Add Authorization header
        val request = original.newBuilder().apply {
            if (token != null) {
                header("Authorization", "Bearer $token")
            }
        }.build()
        
        val response = chain.proceed(request)
        
        // Handle 401 Unauthorized (token expired or invalid)
        if (response.code == 401) {
            response.close()
            
            // Try to refresh token
            val refreshed = runBlocking {
                tokenManager.refreshToken()
            }
            
            if (refreshed) {
                // Retry request with new token
                val newToken = runBlocking { tokenManager.getToken() }
                val newRequest = original.newBuilder().apply {
                    if (newToken != null) {
                        header("Authorization", "Bearer $newToken")
                    }
                }.build()
                
                return chain.proceed(newRequest)
            } else {
                // Refresh failed, clear credentials
                tokenManager.clearCredentials()
                // Redirect to login (handled by app logic)
            }
        }
        
        return response
    }
}
```

**5. Update NetworkManager to use AuthInterceptor:**

```kotlin
// In NetworkManager.kt constructor:

private val client: OkHttpClient = OkHttpClient.Builder()
    .connectTimeout(TIMEOUT_SECONDS, TimeUnit.SECONDS)
    .readTimeout(TIMEOUT_SECONDS, TimeUnit.SECONDS)
    .writeTimeout(TIMEOUT_SECONDS, TimeUnit.SECONDS)
    .addInterceptor(AuthInterceptor(context))  // ADD THIS
    .addInterceptor(HttpLoggingInterceptor().apply {
        level = if (BuildConfig.DEBUG) {
            HttpLoggingInterceptor.Level.BODY
        } else {
            HttpLoggingInterceptor.Level.NONE
        }
    })
    // ... SSL configuration ...
    .build()
```

**Testing Phase 2:**

1. **Test device authentication:**
   - Enter device credentials in app
   - Verify JWT token is received and stored
   - Check token expiration handling

2. **Test token refresh:**
   - Wait for token to near expiration
   - Make API call
   - Verify token is automatically refreshed

3. **Test error handling:**
   - Try invalid credentials
   - Test with server offline
   - Verify proper error messages

**Deliverables:**
- ✅ Device authentication working
- ✅ JWT token management implemented
- ✅ Token refresh working
- ✅ Encrypted storage for credentials
- ✅ Error handling complete

---

### Phase 3: NFC Protocol Migration

**Objectives:**
- Remove password validation logic
- Implement UID-only scanning
- Update card validation to use IAM endpoint
- Test with IAM-registered cards

**Code Changes Required:**

**1. Update Models.kt:**

```kotlin
// File: app/src/main/java/com/upysentinel/nfc/data/model/Models.kt

// CHANGE: Update CardValidationRequest
data class CardValidationRequest(
    @SerializedName("nfc_uid") val nfcUid: String,
    @SerializedName("nfc_uid_hash") val nfcUidHash: String,
    @SerializedName("device_id") val deviceId: String,
    val timestamp: String,
    val location: String,
    @SerializedName("card_type") val cardType: String? = null
)

// CHANGE: Update CardValidationResponse
data class CardValidationResponse(
    val result: String,  // "granted" or "denied"
    val user: UserInfo? = null,
    val reason: String? = null,
    val message: String,
    @SerializedName("access_level") val accessLevel: String? = null,
    @SerializedName("event_id") val eventId: Int? = null,
    val timestamp: String
)

// NEW: User info from IAM
data class UserInfo(
    val uid: String,
    val nombre: String,
    val apellido: String,
    val rol: String,
    @SerializedName("foto_url") val fotoUrl: String?,
    val email: String
)

// REMOVE: NFCCard data class (no longer storing hash/salt)
// data class NFCCard(...) { ... }

// KEEP: SecurityAlert (still needed for alarm system)
data class SecurityAlert(
    val deviceId: String,
    val uid: String?,
    val alertType: AlertType,
    val timestamp: Long,
    val failureCount: Int
)
```

**2. Update NFCManager.kt:**

```kotlin
// File: app/src/main/java/com/upysentinel/nfc/nfc/NFCManager.kt

class NFCManager {
    
    companion object {
        private const val PAGE_SIZE = 4
        private const val READ_COMMAND = 0x30.toByte()
        // REMOVE: PWD_AUTH_COMMAND and DEFAULT_PASSWORD constants
    }
    
    /**
     * Read UID from NFC tag
     */
    fun readUID(tag: Tag): String {
        return SecurityUtils.bytesToHex(tag.id)
    }
    
    // REMOVE: validatePassword() method - no longer needed
    // REMOVE: setPassword() method - no longer needed
    // REMOVE: readHash() and readSalt() methods - no longer needed
    // REMOVE: writeCardData() method - no longer needed
    
    /**
     * Check if tag is NTAG214 compatible
     */
    fun isNTAG214(tag: Tag): Boolean {
        val techList = tag.techList
        return techList.contains("android.nfc.tech.NfcA")
    }
    
    /**
     * Get tag information
     */
    fun getTagInfo(tag: Tag): TagInfo {
        val uid = readUID(tag)
        val techList = tag.techList.toList()
        val isCompatible = isNTAG214(tag)
        
        return TagInfo(
            uid = uid,
            techList = techList,
            isNTAG214 = isCompatible
        )
    }
    
    /**
     * Get card type for logging
     */
    fun getCardType(tag: Tag): String {
        return when {
            tag.techList.contains("android.nfc.tech.MifareClassic") -> "Mifare Classic"
            tag.techList.contains("android.nfc.tech.MifareUltralight") -> "Mifare Ultralight"
            tag.techList.contains("android.nfc.tech.NfcA") -> "NFC-A"
            tag.techList.contains("android.nfc.tech.NfcB") -> "NFC-B"
            else -> "Unknown"
        }
    }
}
```

**3. Update MainActivity.kt:**

```kotlin
// File: app/src/main/java/com/upysentinel/nfc/ui/main/MainActivity.kt

class MainActivity : AppCompatActivity() {
    
    private lateinit var tokenManager: TokenManager
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)
        
        tokenManager = TokenManager(this)
        
        // Check authentication
        if (!tokenManager.isAuthenticated()) {
            navigateToLogin()
            return
        }
        
        // ... rest of initialization ...
    }
    
    private fun processNFCTag(tag: Tag) {
        lifecycleScope.launch {
            try {
                binding.statusText.text = getString(R.string.processing_card)
                binding.statusText.visibility = View.VISIBLE
                
                // 1. Read UID only
                val uid = nfcManager.readUID(tag)
                val cardType = nfcManager.getCardType(tag)
                
                // 2. Validate card with IAM server
                validateCardWithIAM(uid, cardType)
                
            } catch (e: Exception) {
                handleCardError("Error processing card: ${e.message}")
            }
        }
    }
    
    private suspend fun validateCardWithIAM(uid: String, cardType: String) {
        val deviceId = tokenManager.getDeviceId() ?: return
        val location = tokenManager.getLocation() ?: ""
        
        val validationRequest = CardValidationRequest(
            nfcUid = uid,
            nfcUidHash = SecurityUtils.sha256(uid),
            deviceId = deviceId,
            timestamp = Instant.now().toString(),
            location = location,
            cardType = cardType
        )
        
        val result = networkManager.validateCard(validationRequest)
        
        result.fold(
            onSuccess = { response ->
                handleValidationResponse(response, uid)
            },
            onFailure = { exception ->
                handleCardError("Server validation failed: ${exception.message}")
            }
        )
    }
    
    private fun handleValidationResponse(response: CardValidationResponse, uid: String) {
        when (response.result) {
            "granted" -> {
                // Valid access
                binding.statusText.text = getString(R.string.access_granted)
                binding.statusText.setTextColor(getColor(R.color.success_color))
                
                // Display user info
                response.user?.let { user ->
                    binding.userNameText.text = "${user.nombre} ${user.apellido}"
                    binding.userRoleText.text = user.rol
                    binding.userEmailText.text = user.email
                    
                    // Load user photo if available
                    user.fotoUrl?.let { photoUrl ->
                        loadUserPhoto(photoUrl)
                    }
                }
                
                // Play success sound
                audioManager.handleAccessAttempt(true) {
                    // Success callback
                }
                
                // Auto-clear display after 3 seconds
                Handler(Looper.getMainLooper()).postDelayed({
                    clearDisplay()
                }, 3000)
            }
            "denied" -> {
                // Invalid access
                binding.statusText.text = getString(R.string.access_denied)
                binding.statusText.setTextColor(getColor(R.color.error_color))
                
                // Display reason
                binding.userNameText.text = response.reason?.replace("_", " ") ?: "Unknown"
                binding.userRoleText.text = response.message
                
                // Handle failure attempt
                audioManager.handleAccessAttempt(false) {
                    // Check if should send security alert
                    if (it) {
                        lifecycleScope.launch {
                            sendSecurityAlert(uid)
                        }
                    }
                }
                
                // Auto-clear display after 3 seconds
                Handler(Looper.getMainLooper()).postDelayed({
                    clearDisplay()
                }, 3000)
            }
        }
    }
    
    private fun loadUserPhoto(photoUrl: String) {
        // Use Glide or Coil to load user photo
        // Glide.with(this).load("${BASE_URL}${photoUrl}").into(binding.userPhotoImage)
    }
    
    // REMOVE: Old validateCardWithServer() method that used passwordValid
}
```

**4. Update NetworkManager.kt for IAM validation:**

```kotlin
// File: app/src/main/java/com/upysentinel/nfc/network/NetworkManager.kt

suspend fun validateCard(request: CardValidationRequest): Result<CardValidationResponse> = 
    withContext(Dispatchers.IO) {
        try {
            val response = client.newCall(
                Request.Builder()
                    .url("${BASE_URL}api/nfc/scan")  // Changed from /api/card/validate
                    .post(gson.toJson(request).toRequestBody("application/json".toMediaType()))
                    .build()
            ).execute()
            
            if (response.isSuccessful) {
                val validationResponse = gson.fromJson(
                    response.body?.string(),
                    CardValidationResponse::class.java
                )
                Result.success(validationResponse)
            } else {
                Result.failure(Exception("Validation failed: ${response.code}"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
```

**5. Update CardProgrammingActivity.kt:**

```kotlin
// File: app/src/main/java/com/upysentinel/nfc/ui/programming/CardProgrammingActivity.kt

class CardProgrammingActivity : AppCompatActivity() {
    
    // CHANGE: Card programming now just registers UID with IAM
    private fun handleNFCTag(tag: Tag) {
        if (!isProgramming) return
        
        if (!nfcManager.isNTAG214(tag)) {
            showError("Unsupported NFC tag type. Please use NTAG214")
            resetProgramming()
            return
        }
        
        binding.statusText.text = "Registering card..."
        
        lifecycleScope.launch {
            try {
                // Just read UID - no password programming
                val uid = nfcManager.readUID(tag)
                
                // Show assignment UI or admin must assign via IAM web UI
                showCardRegistrationDialog(uid)
                
            } catch (e: Exception) {
                showError("Error reading card: ${e.message}")
                audioManager.playFailureSound()
            }
            
            resetProgramming()
        }
    }
    
    private fun showCardRegistrationDialog(uid: String) {
        AlertDialog.Builder(this)
            .setTitle("NFC Card Detected")
            .setMessage("Card UID: $uid\n\nPlease assign this card to a user in the IAM web dashboard.")
            .setPositiveButton("Copy UID") { _, _ ->
                val clipboard = getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
                val clip = ClipData.newPlainText("NFC UID", uid)
                clipboard.setPrimaryClip(clip)
                Toast.makeText(this, "UID copied to clipboard", Toast.LENGTH_SHORT).show()
            }
            .setNegativeButton("OK", null)
            .show()
    }
    
    // REMOVE: Old card programming logic with password writing
    // REMOVE: Server registration call (done via IAM web UI instead)
}
```

**Testing Phase 3:**

1. **Test UID reading:**
   - Tap various NFC cards
   - Verify UID is correctly extracted
   - Check different card types are detected

2. **Test IAM validation:**
   - Tap registered card → Access granted
   - Tap unregistered card → Access denied
   - Verify user info is displayed correctly

3. **Test card registration flow:**
   - Tap new card in programming mode
   - Copy UID
   - Assign via IAM web UI
   - Test card access

**Deliverables:**
- ✅ UID-only scanning implemented
- ✅ IAM validation endpoint integrated
- ✅ User info display working
- ✅ Card registration flow updated
- ✅ Password logic removed

---

### Phase 4: New Features (Offline & Heartbeat)

**Objectives:**
- Implement offline queue using Room database
- Add heartbeat worker for device monitoring
- Implement sync worker for offline data
- Add network status monitoring

**Code Changes Required:**

**1. Add Room Database dependencies:**

```kotlin
// File: app/build.gradle.kts

dependencies {
    // ... existing dependencies ...
    
    // Room database
    implementation("androidx.room:room-runtime:2.5.2")
    implementation("androidx.room:room-ktx:2.5.2")
    kapt("androidx.room:room-compiler:2.5.2")
    
    // WorkManager
    implementation("androidx.work:work-runtime-ktx:2.8.1")
    
    // Network monitoring
    implementation("androidx.lifecycle:lifecycle-livedata-ktx:2.6.2")
}
```

**2. Create OfflineScan Entity:**

```kotlin
// File: app/src/main/java/com/upysentinel/nfc/db/entities/OfflineScan.kt

package com.upysentinel.nfc.db.entities

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "offline_scans")
data class OfflineScan(
    @PrimaryKey(autoGenerate = true)
    val id: Int = 0,
    
    @ColumnInfo(name = "nfc_uid")
    val nfcUid: String,
    
    @ColumnInfo(name = "nfc_uid_hash")
    val nfcUidHash: String,
    
    @ColumnInfo(name = "device_id")
    val deviceId: String,
    
    @ColumnInfo(name = "timestamp")
    val timestamp: Long,
    
    @ColumnInfo(name = "location")
    val location: String,
    
    @ColumnInfo(name = "card_type")
    val cardType: String?,
    
    @ColumnInfo(name = "synced")
    val synced: Boolean = false,
    
    @ColumnInfo(name = "sync_attempts")
    val syncAttempts: Int = 0,
    
    @ColumnInfo(name = "last_sync_attempt")
    val lastSyncAttempt: Long? = null,
    
    @ColumnInfo(name = "created_at")
    val createdAt: Long = System.currentTimeMillis()
) {
    fun toRequest(): CardValidationRequest {
        return CardValidationRequest(
            nfcUid = nfcUid,
            nfcUidHash = nfcUidHash,
            deviceId = deviceId,
            timestamp = Instant.ofEpochMilli(timestamp).toString(),
            location = location,
            cardType = cardType
        )
    }
}
```

**3. Create OfflineScanDao:**

```kotlin
// File: app/src/main/java/com/upysentinel/nfc/db/OfflineScanDao.kt

package com.upysentinel.nfc.db

import androidx.room.*
import com.upysentinel.nfc.db.entities.OfflineScan
import kotlinx.coroutines.flow.Flow

@Dao
interface OfflineScanDao {
    
    @Insert
    suspend fun insert(scan: OfflineScan): Long
    
    @Query("SELECT * FROM offline_scans WHERE synced = 0 ORDER BY timestamp ASC LIMIT :limit")
    suspend fun getUnsynced(limit: Int = 100): List<OfflineScan>
    
    @Query("SELECT COUNT(*) FROM offline_scans WHERE synced = 0")
    suspend fun getUnsyncedCount(): Int
    
    @Query("SELECT COUNT(*) FROM offline_scans WHERE synced = 0")
    fun getUnsyncedCountFlow(): Flow<Int>
    
    @Query("UPDATE offline_scans SET synced = 1 WHERE id = :id")
    suspend fun markSynced(id: Int)
    
    @Query("UPDATE offline_scans SET sync_attempts = sync_attempts + 1, last_sync_attempt = :timestamp WHERE id = :id")
    suspend fun incrementSyncAttempts(id: Int, timestamp: Long)
    
    @Query("DELETE FROM offline_scans WHERE synced = 1 AND created_at < :cutoffTime")
    suspend fun deleteOldSynced(cutoffTime: Long)
    
    @Query("DELETE FROM offline_scans WHERE sync_attempts > :maxAttempts AND last_sync_attempt < :cutoffTime")
    suspend fun deleteFailedScans(maxAttempts: Int, cutoffTime: Long)
    
    @Query("SELECT * FROM offline_scans ORDER BY timestamp DESC LIMIT :limit")
    suspend fun getRecentScans(limit: Int = 50): List<OfflineScan>
}
```

**4. Create AppDatabase:**

```kotlin
// File: app/src/main/java/com/upysentinel/nfc/db/AppDatabase.kt

package com.upysentinel.nfc.db

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase
import com.upysentinel.nfc.db.entities.OfflineScan

@Database(
    entities = [OfflineScan::class],
    version = 1,
    exportSchema = true
)
abstract class AppDatabase : RoomDatabase() {
    
    abstract fun offlineScanDao(): OfflineScanDao
    
    companion object {
        @Volatile
        private var INSTANCE: AppDatabase? = null
        
        fun getInstance(context: Context): AppDatabase {
            return INSTANCE ?: synchronized(this) {
                val instance = Room.databaseBuilder(
                    context.applicationContext,
                    AppDatabase::class.java,
                    "upy_sentinel_db"
                )
                    .fallbackToDestructiveMigration()
                    .build()
                
                INSTANCE = instance
                instance
            }
        }
    }
}
```

**5. Create HeartbeatWorker:**

```kotlin
// File: app/src/main/java/com/upysentinel/nfc/workers/HeartbeatWorker.kt

package com.upysentinel.nfc.workers

import android.content.Context
import android.os.BatteryManager
import androidx.work.*
import com.upysentinel.nfc.auth.TokenManager
import com.upysentinel.nfc.db.AppDatabase
import com.upysentinel.nfc.network.NetworkManager
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.util.concurrent.TimeUnit

class HeartbeatWorker(
    context: Context,
    params: WorkerParameters
) : CoroutineWorker(context, params) {
    
    private val tokenManager = TokenManager(applicationContext)
    private val networkManager = NetworkManager(applicationContext)
    private val database = AppDatabase.getInstance(applicationContext)
    
    override suspend fun doWork(): Result = withContext(Dispatchers.IO) {
        try {
            // Check if authenticated
            if (!tokenManager.isAuthenticated()) {
                return@withContext Result.failure()
            }
            
            val deviceId = tokenManager.getDeviceId() ?: return@withContext Result.failure()
            val location = tokenManager.getLocation() ?: ""
            
            // Gather stats
            val unsyncedCount = database.offlineScanDao().getUnsyncedCount()
            val batteryLevel = getBatteryLevel()
            
            // Send heartbeat
            val result = networkManager.sendHeartbeat(
                deviceId = deviceId,
                status = "active",
                stats = mapOf(
                    "scans_unsynced" to unsyncedCount,
                    "battery_level" to batteryLevel,
                    "nfc_enabled" to true
                )
            )
            
            result.fold(
                onSuccess = {
                    Result.success()
                },
                onFailure = {
                    Result.retry()
                }
            )
        } catch (e: Exception) {
            Result.retry()
        }
    }
    
    private fun getBatteryLevel(): Int {
        val batteryManager = applicationContext.getSystemService(Context.BATTERY_SERVICE) as BatteryManager
        return batteryManager.getIntProperty(BatteryManager.BATTERY_PROPERTY_CAPACITY)
    }
    
    companion object {
        const val WORK_NAME = "heartbeat_worker"
        
        fun enqueue(context: Context) {
            val heartbeatRequest = PeriodicWorkRequestBuilder<HeartbeatWorker>(
                30, TimeUnit.SECONDS,  // Repeat every 30 seconds
                10, TimeUnit.SECONDS   // Flex interval
            )
                .setConstraints(
                    Constraints.Builder()
                        .setRequiredNetworkType(NetworkType.CONNECTED)
                        .build()
                )
                .build()
            
            WorkManager.getInstance(context)
                .enqueueUniquePeriodicWork(
                    WORK_NAME,
                    ExistingPeriodicWorkPolicy.KEEP,
                    heartbeatRequest
                )
        }
        
        fun cancel(context: Context) {
            WorkManager.getInstance(context).cancelUniqueWork(WORK_NAME)
        }
    }
}
```

**6. Create SyncWorker:**

```kotlin
// File: app/src/main/java/com/upysentinel/nfc/workers/SyncWorker.kt

package com.upysentinel.nfc.workers

import android.content.Context
import androidx.work.*
import com.upysentinel.nfc.auth.TokenManager
import com.upysentinel.nfc.db.AppDatabase
import com.upysentinel.nfc.network.NetworkManager
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.util.concurrent.TimeUnit

class SyncWorker(
    context: Context,
    params: WorkerParameters
) : CoroutineWorker(context, params) {
    
    private val tokenManager = TokenManager(applicationContext)
    private val networkManager = NetworkManager(applicationContext)
    private val database = AppDatabase.getInstance(applicationContext)
    
    override suspend fun doWork(): Result = withContext(Dispatchers.IO) {
        try {
            // Check if authenticated
            if (!tokenManager.isAuthenticated()) {
                return@withContext Result.failure()
            }
            
            // Get unsynced scans (max 100 at a time)
            val unsyncedScans = database.offlineScanDao().getUnsynced(100)
            
            if (unsyncedScans.isEmpty()) {
                return@withContext Result.success()
            }
            
            // Try to sync each scan
            var successCount = 0
            var failureCount = 0
            
            for (scan in unsyncedScans) {
                try {
                    val result = networkManager.validateCard(scan.toRequest())
                    
                    result.fold(
                        onSuccess = {
                            // Mark as synced
                            database.offlineScanDao().markSynced(scan.id)
                            successCount++
                        },
                        onFailure = {
                            // Increment sync attempts
                            database.offlineScanDao().incrementSyncAttempts(
                                scan.id,
                                System.currentTimeMillis()
                            )
                            failureCount++
                        }
                    )
                } catch (e: Exception) {
                    // Increment sync attempts
                    database.offlineScanDao().incrementSyncAttempts(
                        scan.id,
                        System.currentTimeMillis()
                    )
                    failureCount++
                }
            }
            
            // Clean up old synced scans (older than 7 days)
            val sevenDaysAgo = System.currentTimeMillis() - (7 * 24 * 60 * 60 * 1000)
            database.offlineScanDao().deleteOldSynced(sevenDaysAgo)
            
            // Clean up failed scans (more than 10 attempts, older than 24h)
            val oneDayAgo = System.currentTimeMillis() - (24 * 60 * 60 * 1000)
            database.offlineScanDao().deleteFailedScans(10, oneDayAgo)
            
            // Return success if at least one scan was synced
            if (successCount > 0) {
                Result.success()
            } else if (failureCount > 0) {
                Result.retry()
            } else {
                Result.success()
            }
        } catch (e: Exception) {
            Result.retry()
        }
    }
    
    companion object {
        const val WORK_NAME = "sync_worker"
        
        fun enqueue(context: Context) {
            val syncRequest = PeriodicWorkRequestBuilder<SyncWorker>(
                15, TimeUnit.MINUTES,  // Repeat every 15 minutes
                5, TimeUnit.MINUTES    // Flex interval
            )
                .setConstraints(
                    Constraints.Builder()
                        .setRequiredNetworkType(NetworkType.CONNECTED)
                        .build()
                )
                .setBackoffCriteria(
                    BackoffPolicy.EXPONENTIAL,
                    WorkRequest.MIN_BACKOFF_MILLIS,
                    TimeUnit.MILLISECONDS
                )
                .build()
            
            WorkManager.getInstance(context)
                .enqueueUniquePeriodicWork(
                    WORK_NAME,
                    ExistingPeriodicWorkPolicy.KEEP,
                    syncRequest
                )
        }
        
        fun cancel(context: Context) {
            WorkManager.getInstance(context).cancelUniqueWork(WORK_NAME)
        }
    }
}
```

**7. Update MainActivity.kt for offline support:**

```kotlin
// File: app/src/main/java/com/upysentinel/nfc/ui/main/MainActivity.kt

class MainActivity : AppCompatActivity() {
    
    private lateinit var database: AppDatabase
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        // ... existing code ...
        
        database = AppDatabase.getInstance(this)
        
        // Start workers
        HeartbeatWorker.enqueue(this)
        SyncWorker.enqueue(this)
        
        // Observe offline queue count
        observeOfflineQueue()
    }
    
    private fun observeOfflineQueue() {
        lifecycleScope.launch {
            database.offlineScanDao().getUnsyncedCountFlow().collect { count ->
                withContext(Dispatchers.Main) {
                    if (count > 0) {
                        binding.offlineIndicator.visibility = View.VISIBLE
                        binding.offlineCountText.text = "$count pending"
                    } else {
                        binding.offlineIndicator.visibility = View.GONE
                    }
                }
            }
        }
    }
    
    private suspend fun validateCardWithIAM(uid: String, cardType: String) {
        val deviceId = tokenManager.getDeviceId() ?: return
        val location = tokenManager.getLocation() ?: ""
        
        val validationRequest = CardValidationRequest(
            nfcUid = uid,
            nfcUidHash = SecurityUtils.sha256(uid),
            deviceId = deviceId,
            timestamp = Instant.now().toString(),
            location = location,
            cardType = cardType
        )
        
        // Check network connectivity
        if (!isNetworkAvailable()) {
            // Save to offline queue
            saveToOfflineQueue(validationRequest)
            
            withContext(Dispatchers.Main) {
                binding.statusText.text = "Offline - Saved to queue"
                binding.statusText.setTextColor(getColor(R.color.warning_color))
                audioManager.playFailureSound()
            }
            return
        }
        
        // Try online validation
        val result = networkManager.validateCard(validationRequest)
        
        result.fold(
            onSuccess = { response ->
                handleValidationResponse(response, uid)
            },
            onFailure = { exception ->
                // Network error - save to offline queue
                saveToOfflineQueue(validationRequest)
                
                withContext(Dispatchers.Main) {
                    binding.statusText.text = "Network error - Saved to queue"
                    binding.statusText.setTextColor(getColor(R.color.warning_color))
                    audioManager.playFailureSound()
                }
            }
        )
    }
    
    private suspend fun saveToOfflineQueue(request: CardValidationRequest) {
        val offlineScan = OfflineScan(
            nfcUid = request.nfcUid,
            nfcUidHash = request.nfcUidHash,
            deviceId = request.deviceId,
            timestamp = System.currentTimeMillis(),
            location = request.location,
            cardType = request.cardType
        )
        
        database.offlineScanDao().insert(offlineScan)
    }
    
    private fun isNetworkAvailable(): Boolean {
        val connectivityManager = getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager
        val network = connectivityManager.activeNetwork ?: return false
        val capabilities = connectivityManager.getNetworkCapabilities(network) ?: return false
        
        return capabilities.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET) &&
               capabilities.hasCapability(NetworkCapabilities.NET_CAPABILITY_VALIDATED)
    }
    
    override fun onDestroy() {
        super.onDestroy()
        // Don't cancel workers - they should continue in background
    }
}
```

**8. Add NetworkManager methods for heartbeat:**

```kotlin
// File: app/src/main/java/com/upysentinel/nfc/network/NetworkManager.kt

data class HeartbeatRequest(
    @SerializedName("device_id") val deviceId: String,
    val status: String,
    val stats: Map<String, Any>
)

data class HeartbeatResponse(
    val ok: Boolean,
    @SerializedName("server_time") val serverTime: String,
    @SerializedName("device_status") val deviceStatus: String,
    val commands: List<String>
)

suspend fun sendHeartbeat(
    deviceId: String,
    status: String,
    stats: Map<String, Any>
): Result<HeartbeatResponse> = withContext(Dispatchers.IO) {
    try {
        val request = HeartbeatRequest(deviceId, status, stats)
        
        val response = client.newCall(
            Request.Builder()
                .url("${BASE_URL}api/nfc_devices/heartbeat")
                .post(gson.toJson(request).toRequestBody("application/json".toMediaType()))
                .build()
        ).execute()
        
        if (response.isSuccessful) {
            val heartbeatResponse = gson.fromJson(
                response.body?.string(),
                HeartbeatResponse::class.java
            )
            Result.success(heartbeatResponse)
        } else {
            Result.failure(Exception("Heartbeat failed: ${response.code}"))
        }
    } catch (e: Exception) {
        Result.failure(e)
    }
}
```

**Testing Phase 4:**

1. **Test offline queue:**
   - Turn off Wi-Fi/Data
   - Tap several cards
   - Verify scans are saved to queue
   - Turn on network
   - Verify scans are synced

2. **Test heartbeat:**
   - Monitor IAM dashboard
   - Verify device shows "active" status
   - Check "last_seen" timestamp updates every 30s

3. **Test sync worker:**
   - Create offline scans
   - Wait for sync (max 15 min)
   - Verify scans appear in IAM events log

**Deliverables:**
- ✅ Offline queue implemented
- ✅ Heartbeat worker running
- ✅ Sync worker functioning
- ✅ Network status monitoring
- ✅ UI indicators for offline mode

---

### Phase 5: UI/UX Updates & Testing

**Objectives:**
- Update layouts for new features
- Add user photo display
- Improve error messages
- Add device status indicators
- Comprehensive testing

**Tasks:**

1. **Update activity_main.xml:**
   - Add offline indicator
   - Add user photo ImageView
   - Add device status indicator
   - Improve layout for user info display

2. **Update activity_login.xml:**
   - Change to device activation UI
   - Add QR code scanner option (optional)
   - Update branding

3. **Add string resources:**
   - Update all user-facing messages
   - Add IAM-specific messages
   - Add offline mode messages

4. **Update themes:**
   - Ensure consistent branding
   - Add IAM color scheme if needed

5. **Testing:**
   - Unit tests for core logic
   - Integration tests for API calls
   - End-to-end tests with real devices
   - Load testing
   - Security audit

**Deliverables:**
- ✅ Updated UI layouts
- ✅ Improved user experience
- ✅ All tests passing
- ✅ Documentation updated

---

## 🔒 Security Protocol Changes

### TLS/HTTPS Configuration

**Current System:**
- Self-signed certificate
- Port 8443
- Trust all certificates in debug mode

**IAM_Backend:**
- Proper certificate management
- Port 5443 (dev) / 443 (prod)
- Certificate pinning (production)

**Android Changes:**

```kotlin
// Development mode (trust self-signed cert)
if (BuildConfig.DEBUG) {
    val trustManager = object : X509TrustManager {
        override fun checkClientTrusted(chain: Array<X509Certificate>, authType: String) {}
        override fun checkServerTrusted(chain: Array<X509Certificate>, authType: String) {}
        override fun getAcceptedIssuers() = arrayOf<X509Certificate>()
    }
    
    val sslContext = SSLContext.getInstance("TLS")
    sslContext.init(null, arrayOf(trustManager), SecureRandom())
    
    builder.sslSocketFactory(sslContext.socketFactory, trustManager)
    builder.hostnameVerifier { _, _ -> true }
}

// Production mode (certificate pinning)
else {
    builder.certificatePinner(
        CertificatePinner.Builder()
            .add("your-domain.com", "sha256/AAAA...=")
            .build()
    )
}
```

### Authentication Flow Changes

**Current:**
1. User login (username/password)
2. Device activation
3. JWT token (simple)

**IAM:**
1. Device authentication (device_id/device_secret)
2. JWT token (24h validity)
3. Automatic refresh
4. Heartbeat monitoring

### Data Privacy

**NFC UID Handling:**
- Always hash UIDs (SHA-256)
- Send both raw and hashed to server
- Never log full UIDs
- Store hashed UIDs in offline queue

---

## 📊 API Endpoint Mapping

| Current Endpoint | IAM Endpoint | Status | Notes |
|------------------|--------------|--------|-------|
| `/api/auth/login` | `/api/nfc_devices/auth` | ✅ Mapped | Changed to device auth |
| `/api/device/activate` | `/api/nfc_devices/auth` | ✅ Merged | Combined with auth |
| `/api/card/validate` | `/api/nfc/scan` | ✅ Mapped | Different request format |
| `/api/card/register` | Web UI / CLI | ⚠️ Changed | Admin only via IAM |
| `/api/security/alert` | Included in `/api/nfc/scan` | ✅ Integrated | Part of scan response |
| `/api/security/alarm-status` | TBD | ⚠️ Needs implementation | May need custom endpoint |
| N/A | `/api/nfc_devices/heartbeat` | ✅ New | Device monitoring |
| N/A | `/api/nfc/scan/batch` | ✅ New | Offline sync |
| N/A | `/api/nfc_devices/me` | ✅ New | Device info |
| N/A | `/api/nfc_devices/config` | ✅ New | Server config |

---

## ✅ Testing Strategy

### Unit Tests

**Authentication:**
- TokenManager token refresh
- Token expiration detection
- Credential storage/retrieval

**NFC:**
- UID extraction
- Card type detection
- Data validation

**Offline Queue:**
- Insert operations
- Sync logic
- Cleanup operations

### Integration Tests

**API Communication:**
- Device authentication
- Card validation
- Heartbeat sending
- Batch sync

**Database:**
- Offline scan CRUD
- Query performance
- Migration handling

### End-to-End Tests

**User Flows:**
1. First-time device setup
2. Card scanning (online)
3. Card scanning (offline → sync)
4. Token refresh
5. Alarm system
6. Device recovery after network loss

**Performance:**
- Scan latency (<500ms)
- Offline queue performance
- Heartbeat reliability
- Battery impact

**Security:**
- Certificate validation
- Token security
- Data encryption
- Network security

---

## 🔄 Rollback Plan

### If Migration Fails

**Immediate Rollback:**
1. Revert Android app to previous version
2. Restore UPY_Sentinel_Server
3. Restore database backup
4. Test basic functionality

**Gradual Rollback:**
1. Keep IAM_Backend running
2. Run both systems in parallel
3. Gradually migrate devices
4. Monitor for issues

### Backup Strategy

**Before Migration:**
- ✅ Full code backup (Git commit)
- ✅ Database export (UPY_Sentinel_Server)
- ✅ Configuration files backup
- ✅ Certificate backup

**During Migration:**
- ✅ Incremental Git commits
- ✅ Database snapshots at each phase
- ✅ Configuration version control

---

## 📝 Post-Migration Checklist

### Functionality Verification

- [ ] Device authentication works
- [ ] Card scanning works (online)
- [ ] Card scanning works (offline)
- [ ] Offline sync works
- [ ] Heartbeat shows device active
- [ ] User info displays correctly
- [ ] Alarm system works
- [ ] Token refresh works
- [ ] Error handling works

### Performance Verification

- [ ] Scan latency <500ms
- [ ] Offline queue performs well
- [ ] Battery usage acceptable
- [ ] Network usage reasonable
- [ ] App startup time <2s

### Security Verification

- [ ] HTTPS working correctly
- [ ] Certificates valid
- [ ] Tokens stored securely
- [ ] Data encrypted at rest
- [ ] No secrets in logs

### IAM Dashboard Verification

- [ ] Device appears in dashboard
- [ ] Device status updates
- [ ] Scan events logged
- [ ] Audit trail working
- [ ] User cards assigned correctly

### Documentation

- [ ] Update README
- [ ] Document new configuration
- [ ] Update user guide
- [ ] Document troubleshooting
- [ ] Create admin guide

---

## 📞 Support & Resources

### IAM_Backend Resources

**Documentation:**
- Main guide: `C:\Users\jaque\OneDrive\Escritorio\Cursor\ICA_Project_New\ICA_Project_sandbox\IAM_Backend\ANDROID_NFC_INTEGRATION.md`
- Quick reference: `C:\Users\jaque\OneDrive\Escritorio\Cursor\ICA_Project_New\ICA_Project_sandbox\IAM_Backend\ANDROID_INTEGRATION_QUICKREF.md`
- HTTPS setup: `C:\Users\jaque\OneDrive\Escritorio\Cursor\ICA_Project_New\ICA_Project_sandbox\IAM_Backend\HTTPS_SETUP_GUIDE.md`

**CLI Commands:**
```bash
# Register device
python -m app.cli register-nfc-device --name "..." --location "..."

# Assign NFC card
python -m app.cli assign-nfc --uid EMP-001

# View logs
python -m app.cli view-events --device-id NFC-READER-001

# Test NFC UID
python -m app.cli test-nfc --uid 04A3B2C1D4E5F6
```

### Android App Resources

**Current App:**
- Path: `C:\Users\jaque\AndroidStudioProjects\Password_NFC_NTAG214`
- Package: `com.upysentinel.nfc`
- Build: `app/build.gradle.kts`

**Key Files:**
- NetworkManager: `app/src/main/java/com/upysentinel/nfc/network/NetworkManager.kt`
- NFCManager: `app/src/main/java/com/upysentinel/nfc/nfc/NFCManager.kt`
- MainActivity: `app/src/main/java/com/upysentinel/nfc/ui/main/MainActivity.kt`

### Testing Resources

**IAM Server:**
- URL: `https://192.168.1.84:5443` (update with actual IP)
- Health check: `curl -k https://192.168.1.84:5443/health`
- Web UI: `https://192.168.1.84:5443/app.html`

**Test Credentials:**
- Admin: Created during Phase 0
- Device ID: From Phase 0 registration
- Device Secret: From Phase 0 registration

---

## 🎯 Migration Timeline

**Total Estimated Time:** 4-5 weeks

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| Phase 0: Preparation | 1-2 days | None |
| Phase 1: Server Setup | 2-3 days | Phase 0 |
| Phase 2: Authentication | 3-5 days | Phase 1 |
| Phase 3: NFC Protocol | 3-5 days | Phase 2 |
| Phase 4: New Features | 5-7 days | Phase 3 |
| Phase 5: UI/UX & Testing | 5-7 days | Phase 4 |
| Phase 6: Deployment | 2-3 days | Phase 5 |
| **Total** | **4-5 weeks** | |

---

## 🎉 Success Criteria

Migration is considered successful when:

✅ **Functionality:**
- All existing features work
- New IAM features implemented
- No critical bugs

✅ **Performance:**
- Scan latency <500ms
- Offline mode works reliably
- Battery usage acceptable

✅ **Security:**
- HTTPS properly configured
- Tokens managed securely
- Audit trail working

✅ **Monitoring:**
- Device appears in IAM dashboard
- Heartbeat updates regularly
- Events logged correctly

✅ **User Experience:**
- Intuitive interface
- Clear error messages
- Offline mode transparent

✅ **Documentation:**
- Complete and up-to-date
- Admin guide available
- Troubleshooting documented

---

## 📌 Important Notes for Cursor AI

### Context Preservation

This document provides complete context for the migration. When working on any phase:

1. **Always reference this document** for current state and target state
2. **Maintain security standards** throughout migration
3. **Test incrementally** - don't skip testing phases
4. **Keep backups** before major changes
5. **Document any deviations** from this plan

### Code Quality Standards

- Follow Kotlin best practices
- Use coroutines for async operations
- Implement proper error handling
- Add comments for complex logic
- Use meaningful variable names

### Security Reminders

- Never log sensitive data (tokens, passwords, full UIDs)
- Always use HTTPS
- Validate all inputs
- Store credentials in encrypted storage
- Implement proper token refresh

### IAM Integration Points

1. **Authentication:** Device-based, not user-based
2. **Authorization:** Handled by IAM server
3. **Audit Trail:** Automatic via IAM events
4. **Device Management:** Via IAM dashboard
5. **User Management:** Via IAM web UI

---

**This document is the complete integration guide for migrating UPY Sentinel NFC App to IAM_Backend. Keep this document updated as the migration progresses.**

**Last Updated:** October 26, 2025  
**Version:** 1.0  
**Status:** Migration Planning Phase Complete ✅

---

**Ready to begin Phase 0: Preparation** 🚀


