import sqlite3
from pathlib import Path

class AccessCounter:
    def __init__(self, filepath: str = str(Path.cwd().joinpath("databases", "access_counter.db"))):
        self.filepath = filepath

    def get(self) -> int:
        if Path(self.filepath).is_file():
            conn = sqlite3.connect(self.filepath)
            try:
                cur = conn.cursor()
                cur.execute("SELECT value FROM access_counter WHERE rowid = 1")
                row = cur.fetchone()
                if row is None:
                    conn.execute("""
                    CREATE TABLE IF NOT EXISTS access_counter (
                        value INTEGER NOT NULL
                    )
                    """)
                    conn.execute("INSERT OR IGNORE INTO access_counter (rowid, value) VALUES (1, 0)")
                    conn.commit()
                    return 0
                return row[0]
            finally:
                conn.close()
        else:
            conn = sqlite3.connect(self.filepath)
            conn.execute("""
            CREATE TABLE IF NOT EXISTS access_counter (
                value INTEGER NOT NULL
            )
            """)
            conn.execute("INSERT OR IGNORE INTO access_counter (rowid, value) VALUES (1, 0)")
            conn.commit()
            conn.close()
            return 0

    def increase(self):
        if Path(self.filepath).is_file():
            conn = sqlite3.connect(self.filepath)
            try:
                cur = conn.cursor()
                conn.execute("BEGIN IMMEDIATE")
                cur.execute(
                    "UPDATE access_counter SET value = value + 1 WHERE rowid = 1"
                )
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()
        else:
            conn = sqlite3.connect(self.filepath)
            conn.execute("""
            CREATE TABLE IF NOT EXISTS access_counter (
                value INTEGER NOT NULL
            )
            """)
            conn.execute("INSERT OR IGNORE INTO access_counter (rowid, value) VALUES (1, 1)")
            conn.commit()
            conn.close()
