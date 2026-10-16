import sqlite3
import sys
sys.stdout.reconfigure(encoding='utf-8')

conn = sqlite3.connect('meeting.db')

print('=== meetings columns ===')
for r in conn.execute('PRAGMA table_info(meetings)').fetchall():
    nullable = 'YES' if r[3] == 0 else 'NO'
    print(f'  {r[1]:25s} {r[2]:20s} nullable={nullable:3s} default={r[4]}')

print()
print('=== FK meetings ===')
for r in conn.execute('PRAGMA foreign_key_list(meetings)').fetchall():
    print(f'  {r[3]} -> {r[2]}.{r[4]} ON DELETE {r[5]}')

print()
print('=== meeting_participants columns ===')
for r in conn.execute('PRAGMA table_info(meeting_participants)').fetchall():
    nullable = 'YES' if r[3] == 0 else 'NO'
    print(f'  {r[1]:25s} {r[2]:20s} nullable={nullable:3s} default={r[4]}')

print()
count = conn.execute('SELECT COUNT(*) FROM meetings').fetchone()[0]
print(f'Total meetings: {count}')

conn.close()
print('\nVerification complete!')
