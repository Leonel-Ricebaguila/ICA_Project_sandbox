# UPY Sentinel - NFC Access Control System

Android application for managing NTAG214 NFC card access control with enhanced security features.

## Features

✅ **Secure Card Authentication**
- Hash + Salt password protection (SHA-256)
- UID reading (unique card identifier)
- Clone detection capability

✅ **Audio Feedback**
- Success sound (1.5 seconds)
- Failure sound (1.5 seconds)
- Persistent alarm after 3 failures in 1 minute

✅ **HTTPS Communication**
- Self-signed certificate support for LAN/WLAN
- No internet required
- Server communication at 192.168.10.100:8443 (configurable)

✅ **User Authentication**
- Login system with device activation
- Device registration on server
- Session management

✅ **Card Management**
- Read existing cards
- Program new cards
- Register cards with server

## Technical Requirements

- **Android SDK**: Minimum Android 7.0 (API 24)
- **NFC**: Required hardware
- **Permissions**: NFC, Internet, Network State, Audio

## Project Structure

```
app/
├── src/main/
│   ├── java/com/upysentinel/nfc/
│   │   ├── audio/
│   │   │   └── AudioFeedbackManager.kt     # Audio handling
│   │   ├── data/model/
│   │   │   └── Models.kt                    # Data models & security
│   │   ├── nfc/
│   │   │   └── NFCManager.kt                # NTAG214 operations
│   │   ├── network/
│   │   │   └── NetworkManager.kt            # HTTPS communication
│   │   └── ui/
│   │       ├── login/
│   │       │   └── LoginActivity.kt         # Login screen
│   │       ├── main/
│   │       │   └── MainActivity.kt          # Main NFC reading
│   │       └── programming/
│   │           └── CardProgrammingActivity.kt # Card programming
│   └── res/
│       ├── layout/                          # UI layouts
│       ├── values/                          # Strings, colors, themes
│       └── drawable/                        # Icons and backgrounds
```

## Security Implementation

### Hash + Salt Method
Instead of storing passwords directly on NFC tags, the app:

1. Generates a unique salt for each card
2. Creates hash: `SHA256(password + salt + UID)`
3. Stores only hash + salt on the card (not the password)
4. Server validates by comparing hashes

**Benefits:**
- Password never stored on card
- Each card has unique hash (includes UID)
- Cloned UIDs won't have correct hash
- Resistant to rainbow table attacks

### Clone Detection
The system detects cloned cards by:
- Matching UID + Hash + Salt combination
- Server-side validation
- Alert after 3 failed attempts in 1 minute

## Server API Endpoints

The app expects these endpoints on your server:

```
POST /api/auth/login
- Body: { username, password, deviceId }
- Response: { success, token, message }

POST /api/device/activate
- Body: { deviceId, authToken, deviceInfo }
- Response: { success }

POST /api/card/validate
- Body: { uid, hash, salt, deviceId, timestamp }
- Response: { valid, message, isCloned, securityAlert }

POST /api/card/register
- Body: { card: { uid, hash, salt }, authToken }
- Response: { success }

POST /api/security/alert
- Body: { deviceId, uid, alertType, timestamp, failureCount }
- Response: { success }

POST /api/security/stop-alarm
- Body: { deviceId, authToken }
- Response: { success }
```

## Setup Instructions

### 1. Open in Android Studio
1. Open Android Studio
2. Select "Open Existing Project"
3. Navigate to the project folder
4. Wait for Gradle sync to complete

### 2. Configure Server URL
Edit `NetworkManager.kt`:
```kotlin
private val baseUrl = "https://192.168.10.100:8443" // Change to your server IP
```

### 3. Server SSL Certificate
The app accepts self-signed certificates for LAN operation.

On your server:
```bash
# Generate self-signed certificate
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes

# Configure your server (Apache/Nginx) to use HTTPS with this certificate
```

### 4. Build and Run
1. Connect Android device with NFC
2. Enable Developer Mode and USB Debugging
3. Click "Run" in Android Studio

## Usage Flow

### First Time Setup
1. **Login**: Enter username/password
2. **Device Activation**: App registers with server
3. **Main Screen**: Ready to scan cards

### Programming New Cards
1. Click "Program New Card"
2. Enter password for the card
3. Tap "Program Card"
4. Tap NTAG214 card to NFC reader
5. Card is programmed and registered with server

### Validating Cards
1. From main screen, tap any NFC card
2. App reads UID + Hash + Salt
3. Sends to server for validation
4. Plays success/failure sound
5. After 3 failures in 1 minute: persistent alarm

### Stopping Alarm
1. Click "Stop Alarm" button
2. Sends command to server
3. Alarm stops

## NTAG214 Memory Layout

The app uses NTAG214 memory as follows:

```
Pages 4-11:  Hash (32 bytes, SHA-256)
Pages 12-15: Salt (16 bytes, random)
Pages 16+:   Available for future use
```

## Testing Without Server

For testing, you can modify `NetworkManager.kt` to use mock responses:

```kotlin
suspend fun validateCard(request: CardValidationRequest): Result<CardValidationResponse> {
    // Mock response for testing
    return Result.success(CardValidationResponse(
        valid = true,
        message = "Test mode - access granted",
        isCloned = false,
        securityAlert = false
    ))
}
```

## Troubleshooting

**NFC not detected:**
- Check Settings → Connected devices → NFC is enabled
- Ensure device has NFC hardware

**Server connection failed:**
- Verify server is running on LAN
- Check firewall allows port 8443
- Confirm IP address is correct

**Card programming fails:**
- Ensure using genuine NTAG214 chips
- Hold card steady during writing (2-3 seconds)
- Check NFC antenna position on your device

## Dependencies

- Kotlin 1.9.10
- AndroidX Core KTX 1.12.0
- Material Design Components 1.11.0
- OkHttp 4.12.0 (HTTPS)
- Gson 2.10.1 (JSON)
- Android Security Crypto 1.1.0

## License

This project is for educational and internal use.

## Author

Built for UPY access control system with Android 7+ compatibility.


