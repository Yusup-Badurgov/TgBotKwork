
### Описание проекта

Данный проект представляет собой Telegram-бота, который:

- Автоматически принимает заявки на вступление в закрытый Telegram-канал.
- Сохраняет данные о пользователях (Telegram ID, username, имя, фамилию) в базу данных SQLite.
- Записывает данные о новых пользователях в две Google Таблицы:
  - В первую таблицу: **user_id, username, first_name, last_name, is_privileged**
  - Во вторую таблицу: **user_id, first_name, last_name**
- Отправляет уведомления о новых пользователях всем сотрудникам.
- Предоставляет функционал для директора и привилегированных пользователей:
  - Просмотр списка пользователей с пагинацией и карточками.
  - Поиск пользователей по разным критериям.
  - Управление правами (grant/revoke).
  - Просмотр списка сотрудников.

Все действия логируются в консоль, что упрощает отладку и мониторинг работы бота.

### Структура проекта

- `main.py`  
  Основной файл для запуска бота. Определяет основные хэндлеры команд и callback-хэндлеры.

- `config.py`  
  Файл с конфигурацией. Здесь указываются:
  - Токен бота (`TOKEN`)
  - Имя директора (`DIRECTOR_USERNAME`)
  - Идентификаторы Google Таблиц (`SPREADSHEET_ID_1`, `SPREADSHEET_ID_2`)
  - Путь к JSON-файлу сервисного аккаунта Google (`CREDENTIALS_FILE`)
  - Другие важные параметры.

- `db.py`  
  Функции для работы с базой данных SQLite (создание таблицы `users`, добавление, выборка и обновление записей).

- `google_sheets.py`  
  Функции для записи данных пользователей в Google Таблицы (используется `gspread` и сервисный аккаунт).

- `handlers.py`  
  Логика обработки запросов, вспомогательные функции:
  - Отправка уведомлений сотрудникам и директору о новых пользователях.
  - Формирование постраничных списков и карточек.
  - Работа с inline-кнопками.

### Подготовка к запуску

1. **Установить зависимости**:
   Убедитесь, что у вас установлен Python 3.8+ и необходимые пакеты:
   ```bash
   pip install -r requirements.txt
   ```

2. **Создание и настройка бота**:
   - Получите токен у [BotFather](https://t.me/BotFather) и вставьте его в `config.py` в переменную `TOKEN`.
   - Укажите `DIRECTOR_USERNAME` — username директора (без `@`).

3. **Настройка базы данных**:
   - При первом запуске бота будет создана база `users.db`.
   - Таблица `users` создаётся автоматически.

4. **Настройка Google Sheets**:
   - Создайте сервисный аккаунт в Google Cloud Console, скачайте `credentials.json`.
   - Укажите путь к `credentials.json` в `CREDENTIALS_FILE` в `config.py`.
   - Создайте две Google Таблицы или используйте существующие. Вставьте их ID в `SPREADSHEET_ID_1` и `SPREADSHEET_ID_2`.
   - Предоставьте сервисному аккаунту права редактирования данных таблиц (через кнопку "Поделиться" в Google Таблице).

5. **Настройка канала**:
   - Добавьте бота в ваш закрытый канал и назначьте его администратором.
   - Убедитесь, что `CHANNEL_ID` в `config.py` соответствует каналу.

6. **Структура таблиц**:
   - Первая таблица (SPREADSHEET_ID_1) должна содержать столбцы:  
     `user_id | username | first_name | last_name | is_privileged`
   - Вторая таблица (SPREADSHEET_ID_2) должна содержать столбцы:  
     `user_id | first_name | last_name`

7. **Запуск бота**:
   Запустите бота командой:
   ```bash
   python main.py
   ```
   
   При успешном запуске в консоли появится информация о старте.

### Проверка прав и ролей

- Директор определяется по `DIRECTOR_USERNAME`.
- Новые пользователи изначально не имеют привилегий (`is_privileged=0`).
- Директор может выдавать права: `/grant @username`
- Директор может забирать права: `/revoke @username`
- Привилегированные пользователи и директор могут просматривать списки и искать пользователей.

### Логирование

Все действия логируются в консоль, включая:
- Запуск бота и инициализация
- Обработка запросов от пользователей
- Действия с базой данных
- Операции с Google Sheets
- Принятие заявок и отправка уведомлений

Логи помогут в отладке и мониторинге работы бота.

### Основные команды:

- `/start` — Приветственное сообщение.
- `/help` — Отображает список доступных команд.
- `/list_users` — Просмотр списка пользователей с пагинацией (по 10 на страницу).
- `/search_users <запрос>` — Поиск пользователей по username, имени, фамилии или ID.
- `/list_staff` — Просмотр списка сотрудников (привилегированных пользователей).
- `/grant @username` — Выдать права пользователю (только директор).
- `/revoke @username` — Забрать права у пользователя (только директор).

Для навигации по страницам и просмотра карточек пользователей используются inline-кнопки.

### Пример рабочего процесса

1. Новый пользователь подаёт заявку на вступление в канал.
2. Бот одобряет заявку, добавляет запись о пользователе в БД, вносит данные в Google Таблицы и уведомляет всех сотрудников и директора.
3. При необходимости привилегированный пользователь или директор может просмотреть список пользователей `/list_users`, найти конкретного `/search_users`, открыть его карточку.
4. Директор может при необходимости выдать права `/grant @username` или отозвать `/revoke @username`.

Таким образом, бот автоматизирует процесс модерации канала, хранение и обработку данных о пользователях, а также облегчает коммуникацию внутри команды сотрудников.