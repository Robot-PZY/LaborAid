import sqlite3
conn = sqlite3.connect('laboraid.db')
cur = conn.cursor()

# Check users
cur.execute('SELECT id, email, name FROM users LIMIT 10')
print('=== Users ===')
for r in cur.fetchall():
    print(f'  id={r[0]}, email={r[1]}, name={r[2]}')

# Check documents - first get column names
cur.execute('PRAGMA table_info(documents)')
print('\n=== Document columns ===')
for r in cur.fetchall():
    print(f'  {r[1]} ({r[2]})')

# Now query documents
cur.execute('SELECT id, title, owner_id, LENGTH(content), exported_path FROM documents LIMIT 10')
print('\n=== Documents ===')
for r in cur.fetchall():
    print(f'  id={r[0]}, title={r[1]}, owner={r[2]}, content_len={r[3]}, exported={r[4]}')

conn.close()
