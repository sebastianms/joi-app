"""Read-only helper for E2E tests: returns the first connection_id for a session as stdout.

Used by specs that need to delete the connection via HTTP DELETE /api/connections/{id}.
"""

import sqlite3
import sys
from pathlib import Path

if len(sys.argv) != 2:
    print("usage: connection-helper.py <session_id>", file=sys.stderr)
    sys.exit(1)

session_id = sys.argv[1]
app_db = Path(__file__).resolve().parents[2] / "backend" / "joi_app.db"

conn = sqlite3.connect(app_db)
row = conn.execute(
    "SELECT id FROM data_source_connections WHERE user_session_id = ? LIMIT 1",
    (session_id,),
).fetchone()
conn.close()

if row is None:
    sys.exit(1)
print(row[0])
