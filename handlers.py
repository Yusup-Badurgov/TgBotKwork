# handlers.py
import logging
import math

import telebot
from telebot import types

from config import TOKEN
from db import (add_user_to_db, get_user_by_id, get_users_count, get_users_page,
                search_users, list_staff)
from google_sheets import add_user_to_sheets

logger = logging.getLogger(__name__)

bot = telebot.TeleBot(TOKEN, parse_mode='HTML')


def insufficient_rights(message):
    logger.warning(f"Недостаточно прав у пользователя: {message.from_user.username}")
    bot.reply_to(message, "У вас недостаточно прав, обратитесь к директору для получения прав.")


def notify_staff_about_new_user(user_id, username, first_name, last_name):
    staff_members = list_staff()

    display_username = f"@{username}" if username else ''
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


def add_user(user_id, username, first_name, last_name):
    add_user_to_db(user_id, username, first_name, last_name)
    user = get_user_by_id(user_id)
    if user:
        uid, uname, fname, lname, priv = user
        # Записываем в Google Sheets
        add_user_to_sheets(uid, uname, fname, lname, priv)
        # Отправляем уведомление сотрудникам и директору
        notify_staff_about_new_user(uid, uname, fname, lname)


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

    text = f"📄 <b>Список пользователей</b> (Страница {page} из {math.ceil(total_users / per_page)}):\n\n"
    logger.info(f"На странице {page} найдено {len(users)} пользователей из {total_users}")
    keyboard = types.InlineKeyboardMarkup()

    for u in users:
        uid, uname, fname, lname, priv = u
        display_name = f"{fname or ''} {lname or ''}".strip()
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

    if message_id is not None:
        try:
            bot.edit_message_text(text, chat_id, message_id, reply_markup=keyboard, parse_mode='HTML')
        except telebot.apihelper.ApiTelegramException as e:
            if "message is not modified" in str(e):
                logger.warning(
                    f"Попытка отредактировать сообщение без изменений: chat_id={chat_id}, message_id={message_id}")
            else:
                logger.error(f"Ошибка при редактировании сообщения: {e}")
    else:
        bot.send_message(chat_id, text, reply_markup=keyboard, parse_mode='HTML')
        logger.info(f"Сообщение отправлено: page={page}")


def send_search_page(chat_id, query, page=1, per_page=10, message_id=None):
    results = search_users(query)
    total = len(results)

    if total == 0:
        if message_id is not None:
            bot.edit_message_text("❌ Ничего не найдено.", chat_id, message_id)
        else:
            bot.send_message(chat_id, "❌ Ничего не найдено.")
        return

    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    page_results = results[start_idx:end_idx]

    text = f"🔍 <b>Результаты поиска</b> по запросу: <i>{query}</i>\nСтраница {page} из {math.ceil(total / per_page)} (Показано {len(page_results)} из {total})\n\n"
    keyboard = types.InlineKeyboardMarkup()
    enc_query = query.replace(' ', '%20')

    for u in page_results:
        uid, uname, fname, lname, priv = u
        display_name = f"{fname or ''} {lname or ''}".strip()
        if not display_name:
            display_name = str(uid)
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

    # Добавляем HTML-разметку
    if message_id is not None:
        try:
            bot.edit_message_text(text, chat_id, message_id, reply_markup=keyboard, parse_mode='HTML')
        except telebot.apihelper.ApiTelegramException as e:
            if "message is not modified" in str(e):
                logger.warning(
                    f"Попытка отредактировать сообщение без изменений: chat_id={chat_id}, message_id={message_id}")
            else:
                logger.error(f"Ошибка при редактировании сообщения: {e}")
    else:
        bot.send_message(chat_id, text, reply_markup=keyboard, parse_mode='HTML')
