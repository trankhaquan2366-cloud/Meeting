import sys, sqlite3
sys.stdout.reconfigure(encoding='utf-8')
conn = sqlite3.connect('meeting.db')
tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()]
print('Existing tables:', tables)
conn.close()
