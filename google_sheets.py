# google_sheets.py
import logging
import gspread
from google.oauth2.service_account import Credentials

from config import CREDENTIALS_FILE, SPREADSHEET_ID_1, SPREADSHEET_ID_2

logger = logging.getLogger(__name__)

scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=scopes)
gc = gspread.authorize(creds)

sh1 = gc.open_by_key(SPREADSHEET_ID_1)
worksheet1 = sh1.sheet1

sh2 = gc.open_by_key(SPREADSHEET_ID_2)
worksheet2 = sh2.sheet1

def add_user_to_sheets(user_id, username, first_name, last_name, is_privileged):
    logger.info(f"Запись данных пользователя в Google Sheets: user_id={user_id}")
    worksheet1.append_row([user_id, username if username else '', first_name if first_name else '', last_name if last_name else '', is_privileged])
    worksheet2.append_row([user_id, first_name if first_name else '', last_name if last_name else ''])
