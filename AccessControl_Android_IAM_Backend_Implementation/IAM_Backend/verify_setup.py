#!/usr/bin/env python3
"""
Verify HTTPS setup is complete and ready
"""

import os
import sys

def check_file(path, description):
    """Check if a file exists and show status"""
    exists = os.path.exists(path)
    status = "[OK]" if exists else "[MISSING]"
    print(f"  {status} {description}: {path}")
    return exists

def main():
    print("\n" + "="*60)
    print("  HTTPS SETUP VERIFICATION")
    print("="*60 + "\n")
    
    all_ok = True
    
    # Check certificates
    print("[1] SSL/TLS Certificates:")
    all_ok &= check_file("certs/server/server.key", "Private key")
    all_ok &= check_file("certs/server/server.crt", "Certificate")
    all_ok &= check_file("certs/server/server-fullchain.crt", "Full chain")
    
    # Check configuration
    print("\n[2] Configuration:")
    all_ok &= check_file(".env", "Environment config")
    
    # Check scripts
    print("\n[3] Setup Scripts:")
    check_file("generate_certs.py", "Certificate generator")
    check_file("setup_env.py", "Environment generator")
    check_file("run_https.py", "HTTPS server")
    
    # Check documentation
    print("\n[4] Documentation:")
    check_file("HTTPS_SETUP_GUIDE.md", "Setup guide")
    check_file("SETUP_COMPLETE.md", "Completion summary")
    check_file("README.md", "Main README")
    
    # Load and verify .env
    print("\n[5] Configuration Values:")
    if os.path.exists(".env"):
        try:
            from dotenv import load_dotenv
            load_dotenv()
            
            secret_key = os.getenv("SECRET_KEY", "")
            https_port = os.getenv("HTTPS_PORT", "5443")
            db_url = os.getenv("DATABASE_URL", "")
            
            if secret_key and len(secret_key) > 20:
                print(f"  [OK] SECRET_KEY: {secret_key[:20]}... (length: {len(secret_key)})")
            else:
                print(f"  [WARNING] SECRET_KEY may be too short or default")
                all_ok = False
            
            print(f"  [OK] HTTPS_PORT: {https_port}")
            print(f"  [OK] DATABASE_URL: {db_url}")
            
        except ImportError:
            print("  [INFO] python-dotenv not installed (OK if env vars set externally)")
    
    # Summary
    print("\n" + "="*60)
    if all_ok:
        print("  [SUCCESS] SETUP COMPLETE - Ready to start HTTPS server")
        print("="*60)
        print("\n[NEXT STEPS]")
        print("  1. Create admin: python -m app.cli create-admin --uid ADMIN-1 --email admin@local --password Pass123!")
        print("  2. Start server: python run_https.py")
        print("  3. Open browser: https://localhost:5443")
        print("\n[DOCUMENTATION]")
        print("  - Quick start: SETUP_COMPLETE.md")
        print("  - Detailed guide: HTTPS_SETUP_GUIDE.md")
        print("  - Full docs: README.md\n")
        return 0
    else:
        print("  [ERROR] SETUP INCOMPLETE - Some files are missing")
        print("="*60)
        print("\n[TROUBLESHOOTING]")
        print("  - Regenerate certificates: python generate_certs.py")
        print("  - Regenerate .env: python setup_env.py")
        print("  - Check error messages above\n")
        return 1

if __name__ == "__main__":
    sys.exit(main())

