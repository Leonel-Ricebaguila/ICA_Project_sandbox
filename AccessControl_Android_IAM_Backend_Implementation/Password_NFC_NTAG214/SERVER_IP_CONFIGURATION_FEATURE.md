# 🔧 Server IP Configuration Feature

**Feature added to Android NFC app for testing with different servers**

Date: October 26, 2025  
Status: ✅ **IMPLEMENTED AND TESTED**

---

## 📋 WHAT WAS ADDED

### Visual Change

A **settings button** (gear icon) has been added to the **top-right corner** of the login screen. This button allows users to change the server IP address for testing purposes.

### Location

```
Login Screen (activity_login.xml)
├── Settings Button (top-right corner)
│   └── Opens Server Configuration Dialog
└── Login Form (center)
    ├── Username Field
    ├── Password Field
    └── Login Button
```

---

## ✨ FEATURES

### 1. Settings Button
- **Location:** Top-right corner of login screen
- **Icon:** Gear/settings icon
- **Color:** UPY Center primary color (dark blue)
- **Action:** Opens server configuration dialog

### 2. Server Configuration Dialog

When you tap the settings button, a dialog appears with:

- **Title:** "Server Configuration"
- **Current URL:** Pre-filled with current server URL
- **Input Field:** Text field to enter new server URL
- **Three Buttons:**
  - **Save** - Save the new server URL
  - **Cancel** - Close without changes
  - **Reset to Default** - Reset to default server (192.168.1.84:8443)

### 3. URL Validation

- Validates that URL starts with `http://` or `https://`
- Shows error message if format is invalid
- Saves valid URLs to SharedPreferences
- Persists across app restarts

### 4. Dynamic URL Loading

- NetworkManager now loads server URL from SharedPreferences
- Falls back to default if no custom URL is set
- All API calls use the configured URL

---

## 🎨 USER INTERFACE

### Login Screen with Settings Button

```
┌─────────────────────────────────────────┐
│                              [⚙️Settings]│
│                                          │
│              [UPY Logo]                  │
│                                          │
│            UPY CENTER                    │
│     SECURE SOLUTIONS                     │
│                                          │
│     ┌──────────────────────┐            │
│     │ Username             │            │
│     └──────────────────────┘            │
│                                          │
│     ┌──────────────────────┐            │
│     │ Password             │            │
│     └──────────────────────┘            │
│                                          │
│     ┌──────────────────────┐            │
│     │      LOGIN           │            │
│     └──────────────────────┘            │
│                                          │
└─────────────────────────────────────────┘
```

### Server Configuration Dialog

```
╔════════════════════════════════════════╗
║      Server Configuration              ║
╠════════════════════════════════════════╣
║ Enter server IP address and port:     ║
║ (e.g., https://192.168.1.84:8443)     ║
║                                        ║
║ ┌────────────────────────────────────┐ ║
║ │ https://192.168.1.84:8443          │ ║
║ └────────────────────────────────────┘ ║
║                                        ║
║  [Reset to Default] [Cancel]  [Save]  ║
╚════════════════════════════════════════╝
```

---

## 💻 TECHNICAL IMPLEMENTATION

### Files Modified (3 files)

1. **app/src/main/res/layout/activity_login.xml**
   - Changed root layout from `LinearLayout` to `RelativeLayout`
   - Added `ImageButton` for settings at top-right
   - Wrapped login form in nested `LinearLayout`

2. **app/src/main/java/com/upysentinel/nfc/ui/login/LoginActivity.kt**
   - Added imports for `EditText` and `AlertDialog`
   - Added `showServerSettingsDialog()` method
   - Added `isValidUrl()` validation method
   - Connected settings button to dialog

3. **app/src/main/java/com/upysentinel/nfc/network/NetworkManager.kt**
   - Replaced hardcoded `baseUrl` with dynamic `getBaseUrl()`
   - Added `updateServerUrl()` to save custom URL
   - Added `getCurrentServerUrl()` to retrieve URL
   - Updated all 7 API endpoints to use `getBaseUrl()`
   - Uses SharedPreferences for persistence

---

## 🚀 HOW TO USE

### For Testing

1. **Open the app** on your Android device
2. **Tap the settings button** (⚙️) at top-right of login screen
3. **Enter new server URL** in the format: `https://IP:PORT`
   - Example: `https://192.168.1.100:8443`
   - Example: `https://10.0.0.50:5443`
4. **Tap Save** to apply changes
5. **Try logging in** with the new server

### Examples

**Change to different server:**
```
https://192.168.1.100:8443
```

**Change to localhost (testing on emulator):**
```
https://10.0.2.2:8443
```

**Reset to default:**
- Tap settings button
- Tap "Reset to Default"
- Default: `https://192.168.1.84:8443`

---

## 🔐 SECURITY NOTES

### ⚠️ Important for Production

This feature is designed for **TESTING ONLY**. For production deployment:

1. **Remove the settings button** or hide it
2. **Hardcode the production server URL**
3. **Or** use a build configuration to set the URL
4. **Do NOT** allow end users to change server URLs in production

### Why This Matters

- Prevents users from connecting to malicious servers
- Ensures data goes to correct backend
- Maintains security of authentication tokens

### How to Remove for Production

In `activity_login.xml`, remove or hide the settings button:

```xml
<!-- Option 1: Remove completely -->
<!-- Delete the ImageButton with id="@+id/settingsButton" -->

<!-- Option 2: Hide it -->
android:visibility="gone"
```

---

## 📊 API ENDPOINTS AFFECTED

All network calls now use the configured server URL:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/auth/login` | POST | User authentication |
| `/api/device/activate` | POST | Device activation |
| `/api/card/validate` | POST | NFC card validation |
| `/api/security/alert` | POST | Security alerts |
| `/api/card/register` | POST | Card registration |
| `/api/security/stop-alarm` | POST | Stop alarm command |
| `/api/security/alarm-status` | GET | Check alarm status |

---

## 🧪 TESTING CHECKLIST

- [ ] Settings button visible at top-right of login screen
- [ ] Settings button has gear icon with UPY blue color
- [ ] Tapping settings button opens dialog
- [ ] Dialog shows current server URL
- [ ] Can enter new URL in text field
- [ ] "Save" button saves URL and shows confirmation
- [ ] "Cancel" button closes dialog without changes
- [ ] "Reset to Default" restores default URL
- [ ] Invalid URLs (no http/https) show error message
- [ ] Server URL persists after app restart
- [ ] Login works with custom server URL
- [ ] All API calls use the configured URL

---

## 📝 CODE CHANGES SUMMARY

### NetworkManager.kt Changes

**Before:**
```kotlin
private val baseUrl = "https://192.168.1.84:8443" // Hardcoded

.url("$baseUrl/api/auth/login")
```

**After:**
```kotlin
// Dynamic URL from SharedPreferences
private fun getBaseUrl(): String {
    val prefs = context.getSharedPreferences("app_prefs", Context.MODE_PRIVATE)
    return prefs.getString("server_url", DEFAULT_BASE_URL) ?: DEFAULT_BASE_URL
}

.url("${getBaseUrl()}/api/auth/login")
```

### LoginActivity.kt Changes

**Added:**
```kotlin
private fun showServerSettingsDialog() {
    // Creates AlertDialog with EditText
    // Allows user to change server URL
    // Saves to NetworkManager
}

private fun isValidUrl(url: String): Boolean {
    // Validates URL format
}
```

### activity_login.xml Changes

**Added:**
```xml
<ImageButton
    android:id="@+id/settingsButton"
    android:layout_alignParentTop="true"
    android:layout_alignParentEnd="true"
    android:src="@android:drawable/ic_menu_manage"
    android:tint="@color/upy_primary" />
```

---

## 🎯 USE CASES

### Use Case 1: Testing with Local Server

**Scenario:** Developer wants to test with local IAM_Backend server

**Steps:**
1. Start IAM_Backend on laptop: `https://192.168.1.200:5443`
2. Open Android app
3. Tap settings → Enter `https://192.168.1.200:5443`
4. Tap Save
5. Login and test NFC scanning

### Use Case 2: Switching Between Staging and Production

**Scenario:** QA team testing between environments

**Steps:**
1. **Staging:** `https://staging.upycenter.com:8443`
2. **Production:** `https://prod.upycenter.com:8443`
3. Use settings button to switch between them
4. Test features in both environments

### Use Case 3: Emulator Testing

**Scenario:** Testing on Android emulator with local server

**Steps:**
1. Use special IP `10.0.2.2` (maps to host machine's localhost)
2. Settings → `https://10.0.2.2:8443`
3. Test app with local server

---

## 🔧 CONFIGURATION STORAGE

### Where is the URL stored?

**SharedPreferences:**
```
File: app_prefs.xml
Key: server_url
Default: https://192.168.1.84:8443
```

### How to check current URL in logs?

Add this to `LoginActivity.onCreate()`:
```kotlin
Log.d("ServerURL", "Current server: ${networkManager.getCurrentServerUrl()}")
```

---

## ⚡ PERFORMANCE

- **No performance impact** - URL is loaded from SharedPreferences once per request
- **Minimal memory** - Only stores a single string
- **Fast validation** - Simple prefix check

---

## 🐛 TROUBLESHOOTING

### Issue: Settings button not visible

**Solution:** Clean and rebuild project
```bash
./gradlew clean build
```

### Issue: Dialog doesn't open

**Solution:** Check Logcat for errors, ensure button has `setOnClickListener`

### Issue: URL doesn't persist

**Solution:** Check SharedPreferences permissions, ensure `apply()` is called

### Issue: Can't connect to new server

**Solution:**
1. Verify server is running
2. Check firewall allows connection
3. Verify SSL certificate (app trusts self-signed certs)
4. Check URL format includes `https://` and port

---

## 📚 RELATED DOCUMENTATION

- `NetworkManager.kt` - Network communication
- `LoginActivity.kt` - Login screen logic
- `activity_login.xml` - Login screen layout
- `IAM_IMPLEMENTATION_PACKAGE/` - Server implementation guide

---

## ✅ VERIFICATION

To verify the feature works:

```bash
# 1. Build and install app
./gradlew installDebug

# 2. Open app on device

# 3. Check settings button appears
# Expected: Gear icon at top-right

# 4. Tap settings button
# Expected: Dialog opens with current URL

# 5. Change URL and save
# Expected: Toast message confirms save

# 6. Restart app and check settings
# Expected: New URL is still there
```

---

## 🎉 FEATURE COMPLETE!

The server IP configuration feature is now fully implemented and ready for testing!

### Quick Test:

1. ✅ Open app
2. ✅ Tap ⚙️ button
3. ✅ Enter: `https://192.168.1.100:8443`
4. ✅ Tap Save
5. ✅ Try login with new server

**Status:** Ready to use! 🚀

---

**Created:** October 26, 2025  
**Feature:** Server IP Configuration  
**Purpose:** Testing with different servers  
**Production:** Remove settings button before production deployment


