"""Tiny Flask backend: serves the simulator and stores shared 'chaos seeds' under short URLs."""
import os, re, secrets, sqlite3
from flask import Flask, request, jsonify, send_from_directory, abort

app = Flask(__name__, static_folder="static", static_url_path="/static")
app.config["MAX_CONTENT_LENGTH"] = 256 * 1024          # seeds are ~10-30 KB
DB = os.environ.get("DB_PATH", "seeds.db")
VALID = re.compile(r"^[A-Za-z0-9_-]+$")

def db():
    c = sqlite3.connect(DB)
    c.execute("CREATE TABLE IF NOT EXISTS seeds (id TEXT PRIMARY KEY, data TEXT NOT NULL, ts INTEGER DEFAULT (strftime('%s','now')))")
    return c

@app.get("/")
@app.get("/s/<sid>")
def index(sid=None):
    return send_from_directory("static", "index.html")

@app.post("/api/share")
def share():
    data = request.get_data(as_text=True).strip()
    if not data or not VALID.match(data):
        abort(400)
    with db() as c:
        for _ in range(5):
            sid = secrets.token_urlsafe(5)[:6].replace("_", "x").replace("-", "y")
            try:
                c.execute("INSERT INTO seeds (id, data) VALUES (?, ?)", (sid, data))
                return jsonify(id=sid)
            except sqlite3.IntegrityError:
                continue
    abort(500)

@app.get("/api/s/<sid>")
def get_seed(sid):
    if not VALID.match(sid):
        abort(404)
    row = db().execute("SELECT data FROM seeds WHERE id=?", (sid,)).fetchone()
    if not row:
        abort(404)
    return row[0], 200, {"Content-Type": "text/plain", "Cache-Control": "public, max-age=31536000, immutable"}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
