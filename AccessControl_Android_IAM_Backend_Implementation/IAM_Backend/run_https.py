# run_https.py — Servidor Flask con TLS "UPY Center"
import os
import sys
from app import create_app

app = create_app()

if __name__ == "__main__":
    # Certificate paths
    cert_file = os.getenv("TLS_CERT_FILE", "certs/server/server-fullchain.crt")
    key_file = os.getenv("TLS_KEY_FILE", "certs/server/server.key")
    
    # Port (5443 for development to avoid admin rights, 443 for production)
    port = int(os.getenv("HTTPS_PORT", "5443"))
    
    # Validate certificates exist
    if not os.path.exists(cert_file):
        print(f"[ERROR] Certificate not found: {cert_file}")
        print("[HINT] Run: python generate_certs.py")
        sys.exit(1)
    
    if not os.path.exists(key_file):
        print(f"[ERROR] Private key not found: {key_file}")
        print("[HINT] Run: python generate_certs.py")
        sys.exit(1)
    
    print(f"\n[*] Starting HTTPS server...")
    print(f"[*] Certificate: {cert_file}")
    print(f"[*] Private key: {key_file}")
    print(f"[*] Listening on: https://0.0.0.0:{port}")
    print(f"[*] Local access: https://localhost:{port}")
    print(f"\n[WARNING] Using self-signed certificate. Browsers will show security warning.")
    print("[INFO] To trust the certificate, add it to your system's certificate store.\n")
    
    try:
        # Habilitar threading para soportar SSE + otras peticiones simultáneas
        app.run(
            host="0.0.0.0",
            port=port,
            ssl_context=(cert_file, key_file),
            threaded=True,
            debug=False
        )
    except PermissionError:
        print(f"\n[ERROR] Permission denied to bind to port {port}")
        if port < 1024:
            print(f"[HINT] Ports < 1024 require admin/root privileges.")
            print(f"[HINT] Either run as admin or use port 5443 (set HTTPS_PORT=5443 in .env)")
        sys.exit(1)
    except OSError as e:
        print(f"\n[ERROR] {e}")
        if "address already in use" in str(e).lower():
            print(f"[HINT] Port {port} is already in use by another process")
            print(f"[HINT] Change HTTPS_PORT in .env or stop the other process")
        sys.exit(1)
