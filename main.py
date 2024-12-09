# main.py
import logging
from config import LOG_LEVEL, TOKEN
from handlers import bot, add_user, send_users_page, send_search_page, insufficient_rights
from db import user_has_privileges, is_director, set_privilege, list_staff
from telebot import types
from telebot import apihelper

# Настройка логирования
logging.basicConfig(level=LOG_LEVEL, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@bot.chat_join_request_handler()
def handle_chat_join_request(chat_join_request):
    logger.info(
        f"Обработка запроса на вступление: user_id={chat_join_request.from_user.id}, username={chat_join_request.from_user.username}")
    bot.approve_chat_join_request(chat_join_request.chat.id, chat_join_request.from_user.id)
    user = chat_join_request.from_user
    add_user(user.id, user.username, user.first_name, user.last_name)
    logger.info(
        f"Пользователь добавлен: user_id={user.id}, username={user.username}, first_name={user.first_name}, last_name={user.last_name}")


@bot.message_handler(commands=['start'])
def start_cmd(message):
    logger.info(
        f"Команда /start от пользователя: user_id={message.from_user.id}, username={message.from_user.username}")
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
    logger.info(
        f"Команда /list_users от пользователя: user_id={message.from_user.id}, username={message.from_user.username}")
    if not user_has_privileges(message.from_user.username):
        logger.warning(
            f"У пользователя недостаточно прав: user_id={message.from_user.id}, username={message.from_user.username}")
        insufficient_rights(message)
        return

    # Определяем номер страницы
    parts = message.text.split(maxsplit=1)
    page = 1
    if len(parts) > 1 and parts[1].isdigit():
        page = int(parts[1])
        logger.info(f"Пользователь запросил страницу: {page}")

    send_users_page(message.chat.id, page=page)


@bot.callback_query_handler(func=lambda call: call.data.startswith('users_page:'))
def callback_users_page(call):
    logger.info(
        f"Обратный вызов 'users_page': user_id={call.from_user.id}, username={call.from_user.username}, data={call.data}")
    if not user_has_privileges(call.from_user.username):
        logger.warning(
            f"Недостаточно прав у пользователя: user_id={call.from_user.id}, username={call.from_user.username}")
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
    logger.info(f"Получение деталей пользователя: user_id={user_id}, страница возврата={page}")

    from db import get_user_by_id
    user = get_user_by_id(user_id)
    if not user:
        logger.warning(f"Пользователь с ID {user_id} не найден в БД.")
        bot.answer_callback_query(call.id, "Пользователь не найден.")
        return

    uid, uname, fname, lname, priv = user
    pmark = "✅" if priv == 1 else "❌"
    logger.info(f"Детали пользователя получены: user_id={uid}, username={uname}, имя={fname}, фамилия={lname}, привилегии={pmark}")

    text = (f"<b>Профиль пользователя</b>\n\n"
            f"ID: {uid}\n"
            f"Username: @{uname if uname else 'нет'}\n"
            f"Имя: {fname or 'нет'}\n"
            f"Фамилия: {lname or 'нет'}\n"
            f"Привилегии: {pmark}\n\n"
            "Вы можете написать этому пользователю, нажав на кнопку ниже.")

    keyboard = types.InlineKeyboardMarkup()
    if uname:
        logger.debug("Формируем кнопку для отправки сообщения по username.")
        keyboard.add(types.InlineKeyboardButton("Написать пользователю", url=f"https://t.me/{uname}"))
    else:
        logger.debug("Формируем кнопку для отправки сообщения по user_id.")
        keyboard.add(types.InlineKeyboardButton("Написать пользователю", url=f"tg://user?id={uid}"))

    keyboard.add(types.InlineKeyboardButton("🔙 Назад", callback_data=f"users_page:{page}"))

    try:
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=keyboard)
        logger.info("Сообщение с деталями пользователя успешно отредактировано.")
    except Exception as e:
        logger.error(f"Ошибка при редактировании сообщения с деталями пользователя: {e}")

    bot.answer_callback_query(call.id)

@bot.message_handler(commands=['search_users'])
def search_users_cmd(message):
    logger.info(
        f"Команда /search_users от пользователя: user_id={message.from_user.id}, username={message.from_user.username}")
    if not user_has_privileges(message.from_user.username):
        logger.warning(
            f"Недостаточно прав у пользователя: user_id={message.from_user.id}, username={message.from_user.username}")
        insufficient_rights(message)
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        logger.warning(
            f"Неправильное использование команды /search_users пользователем: user_id={message.from_user.id}")
        bot.reply_to(message, "Использование: /search_users &lt;запрос&gt")
        return
    query = parts[1].strip()
    logger.info(
        f"Запрос на поиск: '{query}' от пользователя: user_id={message.from_user.id}, username={message.from_user.username}")
    send_search_page(message.chat.id, query, page=1)


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
    logger.info(f"Получение деталей пользователя: user_id={user_id}, страница возврата={page}, запрос='{query}'")

    from db import get_user_by_id
    user = get_user_by_id(user_id)
    if not user:
        logger.warning(f"Пользователь с ID {user_id} не найден в БД.")
        bot.answer_callback_query(call.id, "Пользователь не найден.")
        return

    uid, uname, fname, lname, priv = user
    pmark = "✅" if priv == 1 else "❌"
    logger.info(f"Детали пользователя получены: user_id={uid}, username={uname}, имя={fname}, фамилия={lname}, привилегии={pmark}")

    text = (f"<b>Профиль пользователя</b>\n\n"
            f"ID: {uid}\n"
            f"Username: @{uname if uname else 'нет'}\n"
            f"Имя: {fname or 'нет'}\n"
            f"Фамилия: {lname or 'нет'}\n"
            f"Привилегии: {pmark}\n\n"
            "Вы можете написать этому пользователю, нажав на кнопку ниже.")

    keyboard = types.InlineKeyboardMarkup()
    if uname:
        logger.debug("Формируем кнопку для отправки сообщения по username.")
        keyboard.add(types.InlineKeyboardButton("Написать пользователю", url=f"https://t.me/{uname}"))
    else:
        logger.debug("Формируем кнопку для отправки сообщения по user_id.")
        keyboard.add(types.InlineKeyboardButton("Написать пользователю", url=f"tg://user?id={uid}"))

    enc_query = query.replace(' ', '%20')
    keyboard.add(types.InlineKeyboardButton("🔙 Назад", callback_data=f"search_page:{page}:{enc_query}"))

    try:
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=keyboard)
        logger.info("Сообщение с деталями пользователя успешно отредактировано.")
    except Exception as e:
        logger.error(f"Ошибка при редактировании сообщения с деталями пользователя: {e}")

    bot.answer_callback_query(call.id)


@bot.message_handler(commands=['grant'])
def grant_cmd(message):
    logger.info(
        f"Команда /grant от пользователя: user_id={message.from_user.id}, username={message.from_user.username}")
    if not is_director(message.from_user.username):
        logger.warning(
            f"Недостаточно прав для выполнения команды /grant: user_id={message.from_user.id}, username={message.from_user.username}")
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
    logger.info(
        f"Команда /revoke от пользователя: user_id={message.from_user.id}, username={message.from_user.username}")
    if not is_director(message.from_user.username):
        logger.warning(
            f"Недостаточно прав для выполнения команды /revoke: user_id={message.from_user.id}, username={message.from_user.username}")
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
    logger.info(
        f"Команда /list_staff от пользователя: user_id={message.from_user.id}, username={message.from_user.username}")
    if not is_director(message.from_user.username):
        logger.warning(
            f"Недостаточно прав для выполнения команды /list_staff: user_id={message.from_user.id}, username={message.from_user.username}")
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
    logger.warning(
        f"Неизвестная команда от пользователя: user_id={message.from_user.id}, username={message.from_user.username}, text={message.text}")
    bot.reply_to(message,
                 "Я не знаю такой команды. Попробуй /help, чтобы увидеть список доступных команд и функционал.")


if __name__ == "__main__":
    logger.info("Инициализация бота...")
    try:
        logger.info("Бот успешно запущен. Ожидаем входящие команды...")
        bot.infinity_polling()
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
