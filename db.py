# db.py
import sqlite3
import logging

from config import DIRECTOR_USERNAME

logger = logging.getLogger(__name__)

conn = sqlite3.connect('users.db', check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    last_name TEXT,
    is_privileged INTEGER DEFAULT 0
);
""")
conn.commit()

def add_user_to_db(user_id, username, first_name, last_name):
    logger.info(f"Добавление пользователя в БД: user_id={user_id}, username={username}, first_name={first_name}, last_name={last_name}")
    cursor.execute("INSERT OR IGNORE INTO users (user_id, username, first_name, last_name) VALUES (?, ?, ?, ?)",
                   (user_id, username, first_name, last_name))
    conn.commit()

def get_user_by_id(user_id):
    logger.debug(f"Запрос пользователя по user_id={user_id}")
    cursor.execute("SELECT user_id, username, first_name, last_name, is_privileged FROM users WHERE user_id=?", (user_id,))
    result = cursor.fetchone()
    logger.debug(f"Результат запроса пользователя по id={user_id}: {result}")
    return result


def get_users_count():
    logger.info("Запрос количества пользователей в БД")
    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]
    logger.info(f"Общее количество пользователей: {count}")
    return count

def get_users_page(page=1, per_page=10):
    offset = (page - 1) * per_page
    logger.info(f"Получение пользователей для страницы {page} с {per_page} записями (offset={offset})")
    cursor.execute(
        "SELECT user_id, username, first_name, last_name, is_privileged FROM users ORDER BY user_id LIMIT ? OFFSET ?",
        (per_page, offset))
    users = cursor.fetchall()
    logger.info(f"Получено {len(users)} пользователей на странице {page}")
    return users

def search_users(query):
    logger.info(f"Поиск пользователей с запросом: {query}")
    q = f"%{query}%"
    if query.isdigit():
        cursor.execute(
            "SELECT user_id, username, first_name, last_name, is_privileged FROM users WHERE user_id = ? OR username LIKE ? OR first_name LIKE ? OR last_name LIKE ?",
            (int(query), q, q, q))
    else:
        cursor.execute(
            "SELECT user_id, username, first_name, last_name, is_privileged FROM users WHERE username LIKE ? OR first_name LIKE ? OR last_name LIKE ?",
            (q, q, q))
    results = cursor.fetchall()
    logger.info(f"Найдено {len(results)} пользователей по запросу: {query}")
    return results

def set_privilege(username, value):
    logger.info(f"Установка привилегий: username={username}, is_privileged={value}")
    username = username.lstrip('@')
    cursor.execute("UPDATE users SET is_privileged = ? WHERE username = ?", (value, username))
    conn.commit()
    updated = cursor.rowcount > 0
    logger.info(f"Привилегии обновлены: {updated}")
    return updated

def list_staff():
    logger.info("Запрос списка сотрудников (привилегированных пользователей).")
    cursor.execute("SELECT user_id, username, first_name, last_name FROM users WHERE is_privileged = 1")
    staff = cursor.fetchall()
    logger.info(f"Найдено сотрудников: {len(staff)}")
    return staff

def user_has_privileges(username):
    logger.info(f"Проверка привилегий для пользователя: {username}")
    if username == DIRECTOR_USERNAME:
        logger.info("Пользователь является директором, доступ разрешён.")
        return True
    username = username.lstrip('@')
    cursor.execute("SELECT is_privileged FROM users WHERE username = ?", (username,))
    res = cursor.fetchone()
    has_privileges = res is not None and res[0] == 1
    logger.info(f"Пользователь {'имеет' if has_privileges else 'не имеет'} привилегии.")
    return has_privileges

def is_director(username):
    from config import DIRECTOR_USERNAME
    logger.info(f"Проверка, является ли пользователь директором: {username}")
    is_dir = username == DIRECTOR_USERNAME
    logger.info(f"Пользователь {'является' if is_dir else 'не является'} директором.")
    return is_dir
