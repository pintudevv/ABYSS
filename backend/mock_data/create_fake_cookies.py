"""Create a fake cookies SQLite database for honeypot deception."""
import sqlite3
from pathlib import Path

db_path = Path(__file__).parent / "fake_cookies.db"

conn = sqlite3.connect(str(db_path))
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS cookies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    host TEXT NOT NULL,
    name TEXT NOT NULL,
    value TEXT NOT NULL,
    path TEXT DEFAULT '/',
    expires INTEGER,
    secure INTEGER DEFAULT 0,
    httponly INTEGER DEFAULT 0,
    samesite TEXT DEFAULT 'Lax'
)
""")

fake_cookies = [
    ("accounts.fakegoogle.com", "SID", "FAKE_SESSION_TOKEN_abcdef123456", "/", 1893456000, 1, 1, "None"),
    ("accounts.fakegoogle.com", "HSID", "FAKE_HSID_xyz789", "/", 1893456000, 1, 1, "None"),
    ("fakegoogle.com", "NID", "FAKE_NID_cookie_data_here", "/", 1719273600, 0, 1, "Lax"),
    ("www.fakepaypal.com", "cookie_prefs", "T%3D1%26M%3D0", "/", 1893456000, 1, 1, "None"),
    ("www.fakepaypal.com", "ts", "vreXpYHY3OfakeTokenData789xyz", "/", 1893456000, 1, 1, "None"),
    ("fake-bank.com", "session_id", "FAKE_BANK_SESSION_abc123def456", "/", 0, 1, 1, "Strict"),
    ("fake-bank.com", "auth_token", "FAKE_AUTH_eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9", "/", 0, 1, 1, "Strict"),
    ("www.fakeamazon.com", "session-id", "263-FAKE-SESSION-ID", "/", 1893456000, 0, 0, "Lax"),
    ("www.fakeamazon.com", "ubid-main", "130-FAKE-UBID-MAIN", "/", 1893456000, 0, 0, "Lax"),
    (".faketwitter.com", "auth_token", "FAKE_TWITTER_AUTH_TOKEN_abc123", "/", 1893456000, 1, 1, "None"),
    (".faketwitter.com", "ct0", "FAKE_CSRF_TOKEN_xyz789abc123", "/", 1893456000, 0, 0, "Lax"),
    ("fakegithub.com", "user_session", "FAKE_GH_SESSION_abc123xyz789", "/", 0, 1, 1, "Lax"),
    ("fakegithub.com", "__Host-user_session_same_site", "FAKE_SAME_SITE_SESSION", "/", 0, 1, 1, "Strict"),
]

cur.executemany(
    "INSERT INTO cookies (host, name, value, path, expires, secure, httponly, samesite) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
    fake_cookies,
)
conn.commit()
conn.close()
print(f"Created fake cookies database: {db_path}")
