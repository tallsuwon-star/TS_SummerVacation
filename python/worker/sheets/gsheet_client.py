import gspread
from google.oauth2.service_account import Credentials

from .. import config

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.readonly",
]


def get_worksheet(worksheet_name: str = "시트1"):
    """서비스 계정 인증으로 구글 시트를 연다.
    GOOGLE_SHEETS_CREDENTIALS_PATH / GOOGLE_SHEET_ID 는 .env에서 로드된다.
    """
    creds = Credentials.from_service_account_file(
        config.GOOGLE_SHEETS_CREDENTIALS_PATH, scopes=SCOPES
    )
    client = gspread.authorize(creds)
    sheet = client.open_by_key(config.GOOGLE_SHEET_ID)

    return sheet.worksheet(worksheet_name)


def append_credit_row(worksheet, tutor_name: str, member_name: str, credit_count: int) -> None:
    """(강사명, 회원명, 보강권 건수)를 한 행씩 기록한다."""
    worksheet.append_row([tutor_name, member_name, credit_count])
