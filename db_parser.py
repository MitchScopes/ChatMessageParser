import sqlite3

DEFAULT_CONFIG = {
    "max_emoticon_length": "15",
    "max_title_length": "200"
}

class ParserDB:
    def __init__(self, db_path="parser.db"):
        self.conn = sqlite3.connect(db_path)
        self.create_table()
        
    def create_table(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS stats (
                category TEXT,
                value TEXT,
                count INTEGER,
                PRIMARY KEY (category, value)
            )
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS links (
                url TEXT PRIMARY KEY,
                title TEXT,
                fetch_time REAL,
                last_accessed INTEGER
            )
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS config (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
        self.conn.commit()

    # Stats
    def add(self, category, value):
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO stats (category, value, count)
            VALUES (?, ?, 1)
            ON CONFLICT(category, value) DO UPDATE SET count = count + 1
        """, (category, value))

    def get_top(self, category, limit=3):
        cur = self.conn.cursor()
        cur.execute("""
            SELECT value, count FROM stats
            WHERE category = ?
            ORDER BY count DESC
            LIMIT ?
        """, (category, limit))
        return cur.fetchall()

    # Links
    def add_link(self, url, title, fetch_time, last_accessed):
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO links (url, title, fetch_time, last_accessed)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(url) DO UPDATE SET title=excluded.title, fetch_time=excluded.fetch_time, last_accessed=excluded.last_accessed
        """, (url, title, fetch_time, last_accessed))

    def get_links(self, limit=3):
        cur = self.conn.cursor()
        cur.execute("""
            SELECT url, title, fetch_time FROM links
            ORDER BY fetch_time DESC
            LIMIT ?
        """, (limit,))
        return cur.fetchall()
    
    # Configuration
    def set_config(self, key, value):
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO config (key, value)
            VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value=excluded.value
        """, (key, str(value)))
        self.conn.commit()

    def get_all_config(self):
        cur = self.conn.cursor()
        cur.execute("SELECT key, value FROM config")
        rows = cur.fetchall()
        config = {key: value for key, value in rows}
        for k, v in DEFAULT_CONFIG.items():
            config.setdefault(k, v)
        return config

    def reset_config(self):
        cur = self.conn.cursor()
        cur.execute("DELETE FROM config")
        for k, v in DEFAULT_CONFIG.items():
            cur.execute("INSERT INTO config (key, value) VALUES (?, ?)", (k, v))
        self.conn.commit()

    def close(self):
        self.conn.close()