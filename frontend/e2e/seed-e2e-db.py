"""Seeds the E2E connection row into joi_app.db for Playwright tests."""

import sqlite3
import sys
import uuid
from pathlib import Path

session_id = sys.argv[1]
sales_db_path = sys.argv[2]

app_db = Path(__file__).resolve().parents[2] / "backend" / "joi_app.db"

conn = sqlite3.connect(app_db)
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
conn.commit()
conn.close()
print(f"[seed-e2e-db] seeded session={session_id} with file_path={sales_db_path}")
