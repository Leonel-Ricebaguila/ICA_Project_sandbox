# run_https.py — Servidor Flask con TLS "UPY Center"
from app import create_app

app = create_app()

if __name__ == "__main__":
    cert_file = "certs/server/server-fullchain.crt"
    key_file  = "certs/server/server.key"
    # Habilitar threading para soportar SSE + otras peticiones simultáneas
    app.run(host="0.0.0.0", port=443, ssl_context=(cert_file, key_file), threaded=True)
