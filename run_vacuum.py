import sqlite3
conn = sqlite3.connect("highs.db")
conn.execute("VACUUM")
conn.close()
