# file: Scripts/edit_database.py
import sqlite3
from werkzeug.security import generate_password_hash

connection = sqlite3.connect("sqlite.db", check_same_thread=False)
cursor = connection.cursor()

# -------------------- USER --------------------
cursor.execute('''
CREATE TABLE IF NOT EXISTS user (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL
);
''')

# -------------------- POST --------------------
cursor.execute('''
CREATE TABLE IF NOT EXISTS post (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    author_id INTEGER,
    edited INTEGER DEFAULT 0
);
''')

# -------------------- LIKE --------------------
cursor.execute('''
CREATE TABLE IF NOT EXISTS like (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL
);
''')

# -------------------- CHECK COLUMNS --------------------
cursor.execute("PRAGMA table_info(post)")
columns = [col[1] for col in cursor.fetchall()]

# author_id
if "author_id" not in columns:
    cursor.execute("ALTER TABLE post ADD COLUMN author_id INTEGER")

# edited
if "edited" not in columns:
    cursor.execute("ALTER TABLE post ADD COLUMN edited INTEGER DEFAULT 0")

# -------------------- DEFAULT USER --------------------
cursor.execute("SELECT id FROM user WHERE username = ?", ('Rocket',))
user = cursor.fetchone()

if not user:
    password = "12345"
    cursor.execute(
        'INSERT INTO user (username, password_hash) VALUES (?, ?)',
        ('Rocket', generate_password_hash(password))
    )
    user_id = cursor.lastrowid
else:
    user_id = user[0]

# -------------------- FIX OLD POSTS --------------------
cursor.execute(
    'UPDATE post SET author_id = ? WHERE author_id IS NULL',
    (user_id,)
)

connection.commit()
connection.close()

print("База данных успешно обновлена")
