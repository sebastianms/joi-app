"""Deletes all widgets, cache entries, collections, dashboards for given sessions.

Used by Playwright beforeEach hooks to isolate state between E2E runs since
Qdrant persists across test runs. Only touches data for the requested
session_ids; other sessions (demo, prod, other tests) are untouched.
"""

import sqlite3
import sys
from pathlib import Path

if len(sys.argv) < 2:
    print("usage: session-reset.py <session_id> [<session_id> ...]", file=sys.stderr)
    sys.exit(1)

app_db = Path(__file__).resolve().parents[2] / "backend" / "joi_app.db"
conn = sqlite3.connect(app_db)

for session_id in sys.argv[1:]:
    conn.execute("DELETE FROM widget_cache_entries WHERE session_id = ?", (session_id,))
    conn.execute("DELETE FROM dashboard_items WHERE dashboard_id IN (SELECT id FROM dashboards WHERE session_id = ?)", (session_id,))
    conn.execute("DELETE FROM dashboards WHERE session_id = ?", (session_id,))
    conn.execute("DELETE FROM collection_widgets WHERE collection_id IN (SELECT id FROM collections WHERE session_id = ?)", (session_id,))
    conn.execute("DELETE FROM collections WHERE session_id = ?", (session_id,))
    conn.execute("DELETE FROM widgets WHERE session_id = ?", (session_id,))

conn.commit()
conn.close()

# Also wipe Qdrant points for these sessions (SQL reset alone isn't enough
# since the similarity search filter doesn't gate on invalidated_at).
try:
    import urllib.error
    import urllib.request
    import json as _json

    QDRANT = "http://127.0.0.1:6333/collections/widget_cache/points/delete"
    for session_id in sys.argv[1:]:
        body = _json.dumps({
            "filter": {
                "must": [
                    {"key": "metadata.session_id", "match": {"value": session_id}}
                ]
            }
        }).encode()
        req = urllib.request.Request(QDRANT, data=body, method="POST",
                                     headers={"Content-Type": "application/json"})
        try:
            urllib.request.urlopen(req, timeout=2).read()
        except urllib.error.HTTPError:
            pass  # Collection may not exist yet; first run is idempotent.
except Exception:
    pass  # Qdrant offline → SQL-side reset is the most we can do.
