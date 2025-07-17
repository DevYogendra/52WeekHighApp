import sqlite3

DB_PATH = "not_interested.db"

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS not_interested (
            nse_code TEXT PRIMARY KEY,
            name TEXT,
            reason TEXT
        )
    """)
    return conn

def get_not_interested():
    conn = get_conn()
    df = conn.execute("SELECT nse_code, name, reason FROM not_interested").fetchall()
    conn.close()
    return df

def get_not_interested_codes():
    conn = get_conn()
    rows = conn.execute("SELECT nse_code FROM not_interested").fetchall()
    conn.close()
    return [r[0] for r in rows]

def save_not_interested_list(entries):
    conn = get_conn()
    conn.execute("DELETE FROM not_interested")  # Clear all
    conn.executemany("INSERT INTO not_interested (nse_code, name, reason) VALUES (?, ?, ?)", entries)
    conn.commit()
    conn.close()

def clear_all_not_interested():
    conn = get_conn()
    conn.execute("DELETE FROM not_interested")
    conn.commit()
    conn.close()
