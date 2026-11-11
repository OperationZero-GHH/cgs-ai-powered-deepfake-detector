import sqlite3
import os
import sys
from urllib.parse import quote
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

def main():
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    load_dotenv(os.path.join(root_dir, ".env"))

    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("DATABASE_URL is not set in environment or .env file.")
        sys.exit(1)

    sqlite_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "cgs_deepfake_shield.db"))
    if not os.path.exists(sqlite_path):
        sqlite_path = os.path.abspath(os.path.join(root_dir, "data", "cgs_deepfake_shield.db"))

    print(f"Reading from SQLite: {sqlite_path}")
    sconn = sqlite3.connect(sqlite_path)
    sconn.row_factory = sqlite3.Row
    scur = sconn.cursor()

    engine = create_engine(db_url)

    tables_in_order = [
        "users",
        "guest_sessions",
        "sessions",
        "ip_enforcement_guards",
        "ip_account_links",
        "audit_events",
        "access_audit_events",
        "user_activity_events",
        "worker_heartbeats",
    ]

    with engine.begin() as conn:
        conn.execute(text("SELECT set_config('cgs.actor', 'admin', true), set_config('cgs.user_id', '', true)"))
        
        for tbl in tables_in_order:
            scur.execute(f"SELECT * FROM [{tbl}]")
            rows = [dict(r) for r in scur.fetchall()]
            if not rows:
                print(f"Skipping {tbl} (0 rows in SQLite)")
                continue
            
            cols = list(rows[0].keys())
            for r in rows:
                if "active" in r:
                    r["active"] = bool(r["active"])
            
            placeholders = ", ".join([f":{col}" for col in cols])
            cols_str = ", ".join([f'"{col}"' for col in cols])
            
            pk_sql = f'INSERT INTO "{tbl}" ({cols_str}) VALUES ({placeholders}) ON CONFLICT DO NOTHING'
            conn.execute(text(pk_sql), rows)
            print(f"Seeded {len(rows)} rows into {tbl}")

    print("\n--- Verifying Row Counts in Supabase ---")
    with engine.connect() as conn:
        for tbl in tables_in_order:
            cnt = conn.execute(text(f'SELECT count(*) FROM "{tbl}"')).scalar()
            print(f"  {tbl}: {cnt} rows")

if __name__ == "__main__":
    main()
