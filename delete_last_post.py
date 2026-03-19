import sqlite3

# подключаемся к базе
connection = sqlite3.connect("sqlite.db")
cursor = connection.cursor()

# получаем id последнего поста
cursor.execute('SELECT id FROM post ORDER BY id DESC LIMIT 1')
row = cursor.fetchone()

if row:
    last_id = row[0]
    cursor.execute('DELETE FROM post WHERE id = ?', (last_id,))
    connection.commit()
    print(f"Удалён пост с id {last_id}")
else:
    print("Постов нет")

connection.close()
