import sqlite3

# Создание соединения с SQLite и базы данных
conn = sqlite3.connect('users.db')
cursor = conn.cursor()

# Создание таблицы
cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    last_name TEXT
)
''')

# Данные пользователей
users_data = [
    (7321932241, None, 'Yahaya', 'Isyaku'),
]

# Заполнение таблицы данными
cursor.executemany('''
INSERT OR IGNORE INTO users (user_id, username, first_name, last_name)
VALUES (?, ?, ?, ?)
''', users_data)

# Сохранение изменений и закрытие соединения
conn.commit()
conn.close()

print("Данные успешно добавлены в базу данных SQLite!")
