# config.py
# Здесь хранятся все настройки: токены, пароли, пути к файлам

TOKEN = "7245958682:AAEczgAtvDYOcvXFtQB1gbyxLdvsVUHyb7s"  # токен бота
DIRECTOR_USERNAME = "yubadurgov"  # username директора без @ из телеграмм
CHANNEL_ID = -1002250302799 # у каждого телеграмм канала есть свой id

CREDENTIALS_FILE = "quantum-keep-428613-c3-32dc3787140b.json"
# https://console.cloud.google.com/ > credentials > Service Accounts > keys > json

SPREADSHEET_ID_1 = "1uaHzlpt6A7V3vhJXoa1_EfgSM9CYiN8ViITuAwTyYIk" # id таблиц можно взять из адресной строки таблицы
SPREADSHEET_ID_2 = "11jihjH1lIJVd7HaHWHjFFzu-jZEB66CYIuDOfJxdcT0" # он там один большой, не ошибетесь

# Параметры логирования можно также вынести сюда
LOG_LEVEL = "INFO"
# В проекте настроены логи для полного контроля всего происходяшего, можно указать уровень логирования.Абсолютно
# все действия проделываемые в боте логируются.