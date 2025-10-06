## NFC Access Control 1.0

Simple Python project with:
- SQLite database for NFC card UIDs and role levels
- Flask HTTP server exposing CRUD and lookup
- Interactive CLI to manage UIDs

### Requirements
- Python 3.8+
- Linux bash (for running commands below); works on Windows too (`py` or `python`)

### Setup
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Optional: set a custom database path
```bash
export NFC_DB_PATH=/path/to/data.db
```

### Run the CLI (interactive)
```bash
python3 cli.py
```

### Run the server
```bash
export HOST=0.0.0.0
export PORT=8080
python3 server.py
```

### HTTP API
- GET `/health`
- GET `/cards` → list records
- GET `/cards/<uid>` → get one
- POST `/cards` with JSON `{ "uid": "...", "role": 1, "note": "..." }` → upsert
- DELETE `/cards/<uid>` → delete
- GET `/lookup/<uid>` → `{ uid, allowed, role }`

### Notes
- The database file defaults to `./data.db` in the current working directory.
- You can use the CLI while the server is running; both point to the same SQLite file.
- Ensure Server IP address is 192.168.1.100 due to Android app query to it.

