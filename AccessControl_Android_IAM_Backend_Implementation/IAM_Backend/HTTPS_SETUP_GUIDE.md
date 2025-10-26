# 🔐 HTTPS Setup & Testing Guide

This guide explains how to set up and test the IAM Backend with HTTPS/TLS support.

## ✅ What Has Been Done

1. **✅ SSL/TLS Certificates Generated**
   - Location: `certs/server/`
   - Files:
     - `server.key` - Private key (2048-bit RSA)
     - `server.crt` - Self-signed certificate
     - `server-fullchain.crt` - Full certificate chain
   - Valid for: 365 days
   - SANs: localhost, 127.0.0.1, ::1

2. **✅ Environment Configuration Created**
   - File: `.env`
   - Contains: `SECRET_KEY`, `ED25519_SECRET_HEX`, and all configs
   - TLS settings configured for port 5443

3. **✅ HTTPS Server Updated**
   - File: `run_https.py`
   - Uses port 5443 (no admin rights needed)
   - Reads config from `.env`
   - Enhanced error handling

4. **✅ Dependencies Installed**
   - All packages from `requirements.txt`
   - Includes cryptography for TLS

---

## 🚀 Quick Start (Step-by-Step)

### Step 1: Verify Files

Check that everything is in place:

```bash
# Check certificates
dir certs\server

# Expected output:
# server.key
# server.crt
# server-fullchain.crt

# Check .env exists
dir .env

# Should show .env file
```

### Step 2: Initialize Database & Create Admin

```bash
# Create admin user (first time only)
python -m app.cli create-admin --uid ADMIN-1 --email admin@local --password StrongPass123!

# Expected output:
# [startup] Default admin created: ADMIN-1 admin@local
# [cli] auto-assign QR...
# [OK] QR card saved: cards/ADMIN-1_QR.png
```

### Step 3: (Optional) Load Demo Users

```bash
# Load demo data for all roles
python -m app.cli seed-demo

# Creates users for testing:
# - MON-001 (Monitor): monitor@local / DemoPass123!
# - IM-001 (IAM): im@local / DemoPass123!
# - AC-001 (Access): access@local / DemoPass123!
# - EMP-001 (Employee): empleado@local / DemoPass123!
# - GRD-001 (Guard): guardia@local / DemoPass123!
# - AUD-001 (Auditor): auditor@local / DemoPass123!
```

### Step 4: Start HTTPS Server

```bash
python run_https.py
```

**Expected output:**
```
[*] Starting HTTPS server...
[*] Certificate: certs/server/server-fullchain.crt
[*] Private key: certs/server/server.key
[*] Listening on: https://0.0.0.0:5443
[*] Local access: https://localhost:5443

[WARNING] Using self-signed certificate. Browsers will show security warning.
[INFO] To trust the certificate, add it to your system's certificate store.

 * Running on https://0.0.0.0:5443
```

### Step 5: Access in Browser

1. **Open browser:** `https://localhost:5443`

2. **Accept security warning:**
   - **Chrome:** Click "Advanced" → "Proceed to localhost (unsafe)"
   - **Firefox:** Click "Advanced" → "Accept the Risk and Continue"
   - **Edge:** Click "Details" → "Go on to the webpage"

3. **You should see:** Login page

---

## 🧪 Testing HTTPS

### Test 1: Health Check

```bash
# Windows PowerShell (bypass SSL verification for self-signed cert)
curl.exe -k https://localhost:5443/health

# Expected: {"status":"ok"}
```

### Test 2: Login Flow (API)

```bash
# 1. Login
curl.exe -k -X POST https://localhost:5443/api/auth/login `
  -H "Content-Type: application/json" `
  -d '{\"email\":\"admin@local\",\"password\":\"StrongPass123!\"}'

# Expected: {"session_id":"...","uid":"ADMIN-1","rol":"R-ADM",...}
```

### Test 3: Web UI Test

1. **Navigate to:** `https://localhost:5443/login.html`
2. **Enter credentials:**
   - Email: `admin@local`
   - Password: `StrongPass123!`
3. **Click "Iniciar sesión"**
4. **Result:** Redirected to QR scan page (qr.html)

### Test 4: Certificate Inspection

**Using OpenSSL:**
```bash
openssl s_client -connect localhost:5443 -showcerts
```

**In Browser:**
- Click the padlock icon in address bar
- View certificate details
- Check: Subject = localhost, Validity dates

---

## 🔒 Security Notes

### For Development (Current Setup)

✅ **Acceptable:**
- Self-signed certificates
- Port 5443 (non-privileged)
- Localhost + private IP access
- SQLite database

⚠️ **Browser Warnings:**
- "Your connection is not private" - **This is normal for self-signed certs**
- You must manually accept the risk each time
- Data is still encrypted in transit

### For Production

❌ **NOT Acceptable:**
- Self-signed certificates
- Default SECRET_KEY

✅ **Required:**
1. **Valid TLS Certificate:**
   - Let's Encrypt (free, auto-renew)
   - Commercial CA (DigiCert, Sectigo)
   - Internal PKI (corporate environments)

2. **Update .env:**
   ```bash
   SECRET_KEY=<new-random-key-32-chars>
   DATABASE_URL=postgresql://user:pass@host/db
   ALLOWED_IP_RANGES=<your-network-cidr>
   HTTPS_PORT=443
   CORS_ORIGINS=https://yourdomain.com
   ```

3. **Production Server:**
   - Use Gunicorn/uWSGI instead of Flask dev server
   - Deploy behind nginx/Apache reverse proxy
   - Enable firewall rules
   - Set up automated backups

---

## 🛠️ Troubleshooting

### Issue: "Certificate not found"

**Error:**
```
[ERROR] Certificate not found: certs/server/server-fullchain.crt
```

**Solution:**
```bash
python generate_certs.py
```

### Issue: "Permission denied to bind to port 443"

**Error:**
```
[ERROR] Permission denied to bind to port 443
```

**Solution:**
Update `.env`:
```bash
HTTPS_PORT=5443
```

Or run as administrator (Windows) / sudo (Linux).

### Issue: "Address already in use"

**Error:**
```
[ERROR] [Errno 10048] Only one usage of each socket address...
```

**Solution:**
```bash
# Find process using port 5443
netstat -ano | findstr :5443

# Kill the process (replace PID)
taskkill /PID <PID> /F

# Or change port in .env
HTTPS_PORT=5444
```

### Issue: Browser keeps showing warning

This is **expected behavior** for self-signed certificates.

**Options:**
1. **Accept each time** (easiest for testing)
2. **Add certificate to trust store:**
   - **Windows:** Import `server.crt` to Trusted Root Certification Authorities
   - **Linux:** Copy to `/usr/local/share/ca-certificates/` and run `update-ca-certificates`
   - **Mac:** Add to Keychain Access and trust

### Issue: "Module not found" errors

**Solution:**
```bash
# Install dependencies
pip install -r requirements.txt

# If using virtual environment
venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

---

## 📊 File Structure

```
IAM_Backend/
├── .env                          # Configuration (gitignored)
├── certs/
│   └── server/
│       ├── server.key            # Private key
│       ├── server.crt            # Certificate
│       └── server-fullchain.crt  # Full chain
├── cards/                        # QR card PNGs
│   └── ADMIN-1_QR.png
├── iam.db                        # SQLite database
├── ed25519_secret.hex            # Audit log signing key
├── run_https.py                  # HTTPS server
├── generate_certs.py             # Certificate generator
├── setup_env.py                  # .env generator
└── requirements.txt              # Python dependencies
```

---

## 🎯 Next Steps After Setup

1. **Generate QR cards for all users:**
   ```bash
   python -m app.cli assign-qr-bulk --out cards --size 800
   ```

2. **Print QR cards** from `cards/` folder

3. **Test full authentication flow:**
   - Login with password
   - Scan QR code
   - Access dashboard

4. **Explore features:**
   - Create users (Data Base tab)
   - Monitor logs (Logs tab)
   - Test messaging (Mensajería tab)
   - View cameras (Cámaras tab)

5. **Read full documentation:** `README.md`

---

## 🔐 Certificate Renewal

Self-signed certificates expire after 365 days.

**To renew:**
```bash
# Backup old certificates
copy certs\server\server.key certs\server\server.key.old
copy certs\server\server.crt certs\server\server.crt.old

# Generate new certificates
python generate_certs.py --days 730

# Restart server
python run_https.py
```

**Production:** Use Let's Encrypt with auto-renewal:
```bash
certbot certonly --standalone -d yourdomain.com
# Update TLS_CERT_FILE and TLS_KEY_FILE in .env
```

---

## 📞 Support

- **Documentation:** `README.md`, `README_OFFLINE.md`
- **CLI Help:** `python -m app.cli --help`
- **Certificate Issues:** Re-run `python generate_certs.py`
- **Config Issues:** Re-run `python setup_env.py`

---

## ✅ Verification Checklist

Before going live, verify:

- [ ] .env file exists and has unique SECRET_KEY
- [ ] Certificates exist in `certs/server/`
- [ ] Admin user created successfully
- [ ] HTTPS server starts without errors
- [ ] Can access https://localhost:5443 in browser
- [ ] Can login with admin credentials
- [ ] QR cards generated in `cards/` folder
- [ ] Database file `iam.db` exists
- [ ] Audit log signing key `ed25519_secret.hex` exists
- [ ] All roles tested (if using demo users)

---

**🎉 Your HTTPS-enabled IAM Backend is ready!**

Access the system at: **https://localhost:5443**

Default credentials:
- Email: `admin@local`
- Password: `StrongPass123!`
- QR Card: `cards/ADMIN-1_QR.png` (scan with webcam)


