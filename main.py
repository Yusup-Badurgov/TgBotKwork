import sqlite3
import telebot
from telebot import types
import logging
import gspread
from google.oauth2.service_account import Credentials

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger(__name__)

# Данные для Google Sheets
CREDENTIALS_FILE = "quantum-keep-428613-c3-32dc3787140b.json"  # ваш файл с ключами сервисного аккаунта
SPREADSHEET_ID_1 = "1uaHzlpt6A7V3vhJXoa1_EfgSM9CYiN8ViITuAwTyYIk"
SPREADSHEET_ID_2 = "11jihjH1lIJVd7HaHWHjFFzu-jZEB66CYIuDOfJxdcT0"


# ==== Авторизация GSpread ====
scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=scopes)
gc = gspread.authorize(creds)

# Открываем таблицы (листы по умолчанию)
sh1 = gc.open_by_key(SPREADSHEET_ID_1)
worksheet1 = sh1.sheet1  # Лист по умолчанию для таблицы 1

sh2 = gc.open_by_key(SPREADSHEET_ID_2)
worksheet2 = sh2.sheet1  # Лист по умолчанию для таблицы 2

# ==== Настройки ====
TOKEN = "7245958682:AAEczgAtvDYOcvXFtQB1gbyxLdvsVUHyb7s"  # токен бота
DIRECTOR_USERNAME = "yubadurgov"  # username директора без @, например director_username

# id канала, в который принимаем пользователей
CHANNEL_ID = -1002250302799  # пример

bot = telebot.TeleBot(TOKEN, parse_mode='HTML')

# ==== Инициализация БД ====
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

def add_user(user_id, username, first_name, last_name):
    logger.info(f"Добавление пользователя в БД: user_id={user_id}, username={username}, first_name={first_name}, last_name={last_name}")
    cursor.execute("INSERT OR IGNORE INTO users (user_id, username, first_name, last_name) VALUES (?, ?, ?, ?)",
                   (user_id, username, first_name, last_name))
    conn.commit()

    # После добавления в БД получим его запись, чтобы узнать is_privileged (по умолчанию 0)
    cursor.execute("SELECT user_id, username, first_name, last_name, is_privileged FROM users WHERE user_id=?", (user_id,))
    user = cursor.fetchone()
    if user:
        # Записываем в Google Sheets
        # user: (user_id, username, first_name, last_name, is_privileged)
        uid, uname, fname, lname, priv = user

        # Таблица 1: все поля
        # Предполагается, что в таблице 1 столбцы: user_id | username | first_name | last_name | is_privileged
        worksheet1.append_row([uid, uname if uname else '', fname if fname else '', lname if lname else '', priv])

        # Таблица 2: только user_id, first_name, last_name
        # Предполагается, что в таблице 2 столбцы: user_id | first_name | last_name
        worksheet2.append_row([uid, fname if fname else '', lname if lname else ''])

        # Отправляем уведомление сотрудникам
        notify_staff_about_new_user(uid, uname, fname, lname)


def notify_staff_about_new_user(user_id, username, first_name, last_name):
    # Получаем список сотрудников
    staff_members = list_staff()
    # staff_members: [(user_id, username, first_name, last_name), ...]

    # Формируем сообщение
    display_username = f"@{username}" if username else ''
    display_name = f"{first_name or ''} {last_name or ''}".strip()
    text = (
        "<b>Новый пользователь!</b>\n\n"
        f"ID: {user_id}\n"
        f"Username: {display_username or 'нет'}\n"
        f"Имя: {first_name or 'нет'}\n"
        f"Фамилия: {last_name or 'нет'}\n\n"
        "Пользователь был добавлен в БД и Google Sheets."
    )

    for s in staff_members:
        s_uid, s_uname, s_fname, s_lname = s
        try:
            bot.send_message(s_uid, text)
            logger.info(f"Отправлено уведомление сотруднику: user_id={s_uid}")
        except Exception as e:
            logger.error(f"Не удалось отправить сообщение сотруднику user_id={s_uid}: {e}")

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
    logger.info(f"Проверка, является ли пользователь директором: {username}")
    is_dir = username == DIRECTOR_USERNAME
    logger.info(f"Пользователь {'является' if is_dir else 'не является'} директором.")
    return is_dir

def insufficient_rights(message):
    logger.warning(f"Недостаточно прав у пользователя: {message.from_user.username}")
    bot.reply_to(message, "У вас недостаточно прав, обратитесь к директору для получения прав.")


# ==== Хэндлеры ====

# Хэндлер на запросы на вступление в канал
@bot.chat_join_request_handler()
def handle_chat_join_request(chat_join_request):
    logger.info(f"Обработка запроса на вступление: user_id={chat_join_request.from_user.id}, username={chat_join_request.from_user.username}")
    bot.approve_chat_join_request(chat_join_request.chat.id, chat_join_request.from_user.id)
    user = chat_join_request.from_user
    add_user(user.id, user.username, user.first_name, user.last_name)
    logger.info(f"Пользователь добавлен: user_id={user.id}, username={user.username}, first_name={user.first_name}, last_name={user.last_name}")



@bot.message_handler(commands=['start'])
def start_cmd(message):
    logger.info(f"Команда /start от пользователя: user_id={message.from_user.id}, username={message.from_user.username}")
    text = ("Привет! 👋\n\n"
            "Это служебный бот, который помогает администрировать закрытый канал. Я автоматически принимаю заявки на вступление от пользователей, сохраняю их данные в базу,"
            "добавляю запись в гугл таблицы, а также отправляю уведомление всем сотрудникам о новом пользователе и позволяю просматривать список участников. "
            "Кроме того, для уполномоченных лиц доступно управление правами пользователей.\n\n"
            "Чтобы узнать о моих возможностях, используй команду /help.")
    bot.reply_to(message, text)


@bot.message_handler(commands=['help'])
def help_cmd(message):
    logger.info(f"Команда /help от пользователя: user_id={message.from_user.id}, username={message.from_user.username}")
    text = (
        "<b>Доступные команды:</b>\n\n"
        "/start - Приветственное сообщение.\n"
        "/help - Список команд и функционала.\n\n"
        "<b>Для директора и привилегированных пользователей:</b>\n"
        "/list_users [номер страницы] - Просмотреть список пользователей по страницам (по 10 записей на странице).\n"
        "/search_users &lt;запрос&gt; - Поиск пользователя по username, имени, фамилии или ID.\n"
        "/list_staff - Показать список сотрудников (пользователей с правами).\n\n"
        "<b>Только для директора:</b>\n"
        "/grant @username - Выдать права пользователю.\n"
        "/revoke @username - Забрать права у пользователя.\n"
    )
    bot.reply_to(message, text)


@bot.message_handler(commands=['list_users'])
def list_users_cmd(message):
    logger.info(f"Команда /list_users от пользователя: user_id={message.from_user.id}, username={message.from_user.username}")
    if not user_has_privileges(message.from_user.username):
        logger.warning(f"У пользователя недостаточно прав: user_id={message.from_user.id}, username={message.from_user.username}")
        insufficient_rights(message)
        return

    # Определяем номер страницы
    parts = message.text.split(maxsplit=1)
    page = 1
    if len(parts) > 1 and parts[1].isdigit():
        page = int(parts[1])
        logger.info(f"Пользователь запросил страницу: {page}")

    send_users_page(message.chat.id, page=page)


def send_users_page(chat_id, page=1, per_page=10, message_id=None):
    logger.info(f"Загрузка страницы пользователей: page={page}, per_page={per_page}")
    total_users = get_users_count()
    users = get_users_page(page, per_page)

    if not users:
        logger.warning(f"Пользователи не найдены на странице: page={page}")
        if message_id is not None:
            bot.edit_message_text(f"Нет пользователей на странице {page}.", chat_id, message_id)
        else:
            bot.send_message(chat_id, f"Нет пользователей на странице {page}.")
        return

    text = f"Страница {page} (Показаны пользователи {len(users)} из {total_users}):\n"
    logger.info(f"На странице {page} найдено {len(users)} пользователей из {total_users}")
    keyboard = types.InlineKeyboardMarkup()

    for u in users:
        uid, uname, fname, lname, priv = u
        display_name = f"@{uname}" if uname else f"{fname or ''} {lname or ''}".strip()
        if not display_name:
            display_name = str(uid)
        logger.debug(f"Добавление пользователя в список: user_id={uid}, display_name={display_name}")
        keyboard.add(types.InlineKeyboardButton(
            text=f"{display_name}",
            callback_data=f"user_details:{uid}:{page}"
        ))

    buttons = []
    if page > 1:
        buttons.append(types.InlineKeyboardButton("⬅️ Назад", callback_data=f"users_page:{page - 1}"))
    if page * per_page < total_users:
        buttons.append(types.InlineKeyboardButton("Вперёд ➡️", callback_data=f"users_page:{page + 1}"))
    if buttons:
        keyboard.add(*buttons)

    # Проверяем, изменилось ли содержимое
    if message_id is not None:
        try:
            bot.edit_message_text(text, chat_id, message_id, reply_markup=keyboard)
        except telebot.apihelper.ApiTelegramException as e:
            if "message is not modified" in str(e):
                logger.warning(f"Попытка отредактировать сообщение без изменений: chat_id={chat_id}, message_id={message_id}")
            else:
                logger.error(f"Ошибка при редактировании сообщения: {e}")
    else:
        bot.send_message(chat_id, text, reply_markup=keyboard)
        logger.info(f"Сообщение отправлено: page={page}")



@bot.callback_query_handler(func=lambda call: call.data.startswith('users_page:'))
def callback_users_page(call):
    logger.info(f"Обратный вызов 'users_page': user_id={call.from_user.id}, username={call.from_user.username}, data={call.data}")
    if not user_has_privileges(call.from_user.username):
        logger.warning(f"Недостаточно прав у пользователя: user_id={call.from_user.id}, username={call.from_user.username}")
        bot.answer_callback_query(call.id, "У вас недостаточно прав!")
        return
    page = int(call.data.split(':')[1])
    logger.info(f"Пользователь переключился на страницу: {page}")
    # Редактируем текущее сообщение, а не создаём новое
    send_users_page(call.message.chat.id, page=page, message_id=call.message.message_id)
    bot.answer_callback_query(call.id)



@bot.callback_query_handler(func=lambda call: call.data.startswith('user_details:'))
def callback_user_details(call):
    logger.info(f"Обратный вызов 'user_details': user_id={call.from_user.id}, username={call.from_user.username}, data={call.data}")
    if not user_has_privileges(call.from_user.username):
        logger.warning(f"Недостаточно прав у пользователя: user_id={call.from_user.id}, username={call.from_user.username}")
        bot.answer_callback_query(call.id, "У вас недостаточно прав!")
        return
    _, user_id_str, page_str = call.data.split(':')
    user_id = int(user_id_str)
    page = int(page_str)
    logger.info(f"Запрос деталей пользователя: user_id={user_id}, страница возврата={page}")

    cursor.execute("SELECT user_id, username, first_name, last_name, is_privileged FROM users WHERE user_id=?", (user_id,))
    user = cursor.fetchone()
    if not user:
        logger.warning(f"Пользователь с ID {user_id} не найден в базе данных.")
        bot.answer_callback_query(call.id, "Пользователь не найден.")
        return

    uid, uname, fname, lname, priv = user
    pmark = "✅" if priv == 1 else "❌"
    text = (f"<b>Профиль пользователя</b>\n\n"
            f"ID: {uid}\n"
            f"Username: @{uname if uname else 'нет'}\n"
            f"Имя: {fname or 'нет'}\n"
            f"Фамилия: {lname or 'нет'}\n"
            f"Привилегии: {pmark}\n\n"
            "Вы можете написать этому пользователю, нажав на кнопку ниже.")
    logger.info(f"Профиль пользователя найден: user_id={uid}, username={uname}, privileges={pmark}")

    keyboard = types.InlineKeyboardMarkup()
    if uname:
        keyboard.add(types.InlineKeyboardButton("Написать пользователю", url=f"https://t.me/{uname}"))
    else:
        keyboard.add(types.InlineKeyboardButton("Написать пользователю", url=f"tg://user?id={uid}"))

    # Кнопка Назад возвращается к списку на ту же страницу
    keyboard.add(types.InlineKeyboardButton("🔙 Назад", callback_data=f"users_page:{page}"))

    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=keyboard)
    bot.answer_callback_query(call.id)



# Теперь аналогичная логика для поиска с пагинацией
@bot.message_handler(commands=['search_users'])
def search_users_cmd(message):
    logger.info(f"Команда /search_users от пользователя: user_id={message.from_user.id}, username={message.from_user.username}")
    if not user_has_privileges(message.from_user.username):
        logger.warning(f"Недостаточно прав у пользователя: user_id={message.from_user.id}, username={message.from_user.username}")
        insufficient_rights(message)
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        logger.warning(f"Неправильное использование команды /search_users пользователем: user_id={message.from_user.id}")
        bot.reply_to(message, "Использование: /search_users &lt;запрос&gt")
        return
    query = parts[1].strip()
    logger.info(f"Запрос на поиск: '{query}' от пользователя: user_id={message.from_user.id}, username={message.from_user.username}")
    send_search_page(message.chat.id, query, page=1)


def send_search_page(chat_id, query, page=1, per_page=10, message_id=None):
    logger.info(f"Поиск пользователей: query='{query}', page={page}, per_page={per_page}")
    results = search_users(query)
    total = len(results)
    logger.info(f"Найдено {total} пользователей по запросу: '{query}'")

    if total == 0:
        logger.warning(f"Нет результатов для запроса: '{query}'")
        if message_id is not None:
            bot.edit_message_text("Ничего не найдено.", chat_id, message_id)
        else:
            bot.send_message(chat_id, "Ничего не найдено.")
        return

    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    page_results = results[start_idx:end_idx]

    logger.info(f"Отображение результатов: {len(page_results)} из {total}, страница {page}")
    text = f"Результаты поиска по запросу: {query}\nСтраница {page} (Показано {len(page_results)} из {total})\n"
    keyboard = types.InlineKeyboardMarkup()

    enc_query = query.replace(' ', '%20')

    for u in page_results:
        uid, uname, fname, lname, priv = u
        display_name = f"@{uname}" if uname else f"{fname or ''} {lname or ''}".strip()
        if not display_name:
            display_name = str(uid)
        logger.debug(f"Добавление в список: user_id={uid}, display_name='{display_name}'")
        keyboard.add(
            types.InlineKeyboardButton(
                text=display_name,
                callback_data=f"search_user_details:{uid}:{page}:{enc_query}"
            )
        )

    buttons = []
    if page > 1:
        buttons.append(types.InlineKeyboardButton("⬅️ Назад", callback_data=f"search_page:{page - 1}:{enc_query}"))
    if end_idx < total:
        buttons.append(types.InlineKeyboardButton("Вперёд ➡️", callback_data=f"search_page:{page + 1}:{enc_query}"))

    if buttons:
        keyboard.add(*buttons)

    if message_id is not None:
        try:
            bot.edit_message_text(text, chat_id, message_id, reply_markup=keyboard)
        except telebot.apihelper.ApiTelegramException as e:
            if "message is not modified" in str(e):
                logger.warning(
                    f"Попытка отредактировать сообщение без изменений: chat_id={chat_id}, message_id={message_id}")
            else:
                logger.error(f"Ошибка при редактировании сообщения: {e}")
    else:
        bot.send_message(chat_id, text, reply_markup=keyboard)
        logger.info(f"Сообщение отправлено: page={page}")


@bot.callback_query_handler(func=lambda call: call.data.startswith('search_page:'))
def callback_search_page(call):
    logger.info(f"Обратный вызов 'search_page': user_id={call.from_user.id}, username={call.from_user.username}, data={call.data}")
    if not user_has_privileges(call.from_user.username):
        logger.warning(f"Недостаточно прав у пользователя: user_id={call.from_user.id}, username={call.from_user.username}")
        bot.answer_callback_query(call.id, "У вас недостаточно прав!")
        return
    _, page_str, enc_query = call.data.split(':', 2)
    page = int(page_str)
    query = enc_query.replace('%20', ' ')
    logger.info(f"Переключение на страницу {page} для запроса: '{query}'")
    send_search_page(call.message.chat.id, query, page=page, message_id=call.message.message_id)
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda call: call.data.startswith('search_user_details:'))
def callback_search_user_details(call):
    logger.info(f"Обратный вызов 'search_user_details': user_id={call.from_user.id}, username={call.from_user.username}, data={call.data}")
    if not user_has_privileges(call.from_user.username):
        logger.warning(f"Недостаточно прав у пользователя: user_id={call.from_user.id}, username={call.from_user.username}")
        bot.answer_callback_query(call.id, "У вас недостаточно прав!")
        return
    _, uid_str, page_str, enc_query = call.data.split(':', 3)
    user_id = int(uid_str)
    page = int(page_str)
    query = enc_query.replace('%20', ' ')
    logger.info(f"Запрос деталей пользователя: user_id={user_id}, страница возврата={page}, запрос='{query}'")

    cursor.execute("SELECT user_id, username, first_name, last_name, is_privileged FROM users WHERE user_id=?", (user_id,))
    user = cursor.fetchone()
    if not user:
        logger.warning(f"Пользователь с ID {user_id} не найден в базе данных.")
        bot.answer_callback_query(call.id, "Пользователь не найден.")
        return

    uid, uname, fname, lname, priv = user
    pmark = "✅" if priv == 1 else "❌"
    text = (f"<b>Профиль пользователя</b>\n\n"
            f"ID: {uid}\n"
            f"Username: @{uname if uname else 'нет'}\n"
            f"Имя: {fname or 'нет'}\n"
            f"Фамилия: {lname or 'нет'}\n"
            f"Привилегии: {pmark}\n\n"
            "Вы можете написать этому пользователю, нажав на кнопку ниже.")
    logger.info(f"Детали пользователя: user_id={uid}, username={uname}, privileges={pmark}")

    keyboard = types.InlineKeyboardMarkup()
    if uname:
        keyboard.add(types.InlineKeyboardButton("Написать пользователю", url=f"https://t.me/{uname}"))
    else:
        keyboard.add(types.InlineKeyboardButton("Написать пользователю", url=f"tg://user?id={uid}"))

    enc_query = query.replace(' ', '%20')
    keyboard.add(types.InlineKeyboardButton("🔙 Назад", callback_data=f"search_page:{page}:{enc_query}"))

    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=keyboard)
    bot.answer_callback_query(call.id)



@bot.message_handler(commands=['grant'])
def grant_cmd(message):
    logger.info(f"Команда /grant от пользователя: user_id={message.from_user.id}, username={message.from_user.username}")
    if not is_director(message.from_user.username):
        logger.warning(f"Недостаточно прав для выполнения команды /grant: user_id={message.from_user.id}, username={message.from_user.username}")
        insufficient_rights(message)
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        logger.warning(f"Неправильное использование команды /grant: user_id={message.from_user.id}")
        bot.reply_to(message, "Использование: /grant @username")
        return
    username = parts[1].strip()
    logger.info(f"Попытка выдать права пользователю: username={username}")
    if set_privilege(username, 1):
        logger.info(f"Права успешно выданы пользователю: username={username}")
        bot.reply_to(message, f"Права выданы пользователю {username}.")
    else:
        logger.warning(f"Не удалось выдать права пользователю: username={username}")
        bot.reply_to(message, f"Не удалось выдать права пользователю {username}. Убедитесь, что пользователь является "
                              f"участником закрытого канала. Или такого пользователя вовсе не существует.")



@bot.message_handler(commands=['revoke'])
def revoke_cmd(message):
    logger.info(f"Команда /revoke от пользователя: user_id={message.from_user.id}, username={message.from_user.username}")
    if not is_director(message.from_user.username):
        logger.warning(f"Недостаточно прав для выполнения команды /revoke: user_id={message.from_user.id}, username={message.from_user.username}")
        insufficient_rights(message)
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        logger.warning(f"Неправильное использование команды /revoke: user_id={message.from_user.id}")
        bot.reply_to(message, "Использование: /revoke @username")
        return
    username = parts[1].strip()
    logger.info(f"Попытка забрать права у пользователя: username={username}")
    if set_privilege(username, 0):
        logger.info(f"Права успешно отозваны у пользователя: username={username}")
        bot.reply_to(message, f"Права забраны у пользователя {username}.")
    else:
        logger.warning(f"Не удалось забрать права у пользователя: username={username}")
        bot.reply_to(message, f"Не удалось забрать права у {username}. Возможно, пользователь не найден.")



@bot.message_handler(commands=['list_staff'])
def list_staff_cmd(message):
    logger.info(f"Команда /list_staff от пользователя: user_id={message.from_user.id}, username={message.from_user.username}")
    if not is_director(message.from_user.username):
        logger.warning(f"Недостаточно прав для выполнения команды /list_staff: user_id={message.from_user.id}, username={message.from_user.username}")
        insufficient_rights(message)
        return
    staff = list_staff()
    if not staff:
        logger.info("Запрос списка сотрудников: список пуст.")
        bot.reply_to(message, "Нет сотрудников.")
        return
    logger.info(f"Список сотрудников запрошен. Найдено: {len(staff)} сотрудников.")
    text = "Сотрудники:\n"
    for u in staff:
        uid, uname, fname, lname = u
        logger.debug(f"Сотрудник: ID={uid}, username={uname}, first_name={fname}, last_name={lname}")
        text += f"ID: {uid}, @{uname if uname else ''}, {fname or ''} {lname or ''}\n"
    bot.reply_to(message, text)



@bot.message_handler(func=lambda m: True)
def default_handler(message):
    logger.warning(f"Неизвестная команда от пользователя: user_id={message.from_user.id}, username={message.from_user.username}, text={message.text}")
    bot.reply_to(message,
                 "Я не знаю такой команды. Попробуй /help, чтобы увидеть список доступных команд и функционал.")



if __name__ == "__main__":
    logger.info("Инициализация бота...")
    try:
        logger.info("Бот успешно запущен. Ожидаем входящие команды...")
        bot.infinity_polling()
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
