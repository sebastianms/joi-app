"""Seeds E2E connection rows into joi_app.db for Playwright tests.

Usage: seed-e2e-db.py <sales_db_path> <session_id> [<session_id> ...]
All listed sessions get an ACTIVE SQLite connection pointing at sales_db_path.
"""

import sqlite3
import sys
import uuid
from pathlib import Path

if len(sys.argv) < 3:
    print("usage: seed-e2e-db.py <sales_db_path> <session_id> [<session_id> ...]", file=sys.stderr)
    sys.exit(1)

sales_db_path = sys.argv[1]
session_ids = sys.argv[2:]

app_db = Path(__file__).resolve().parents[2] / "backend" / "joi_app.db"

conn = sqlite3.connect(app_db)
for session_id in session_ids:
    conn.execute(
        "DELETE FROM data_source_connections WHERE user_session_id = ?",
        (session_id,),
    )
    conn.execute(
        """
        INSERT INTO data_source_connections
            (id, user_session_id, name, source_type, file_path, connection_string, status)
        VALUES (?, ?, ?, ?, ?, NULL, ?)
        """,
        (str(uuid.uuid4()), session_id, "sales-e2e", "SQLITE", sales_db_path, "ACTIVE"),
    )
    print(f"[seed-e2e-db] seeded session={session_id}")
conn.commit()
conn.close()
