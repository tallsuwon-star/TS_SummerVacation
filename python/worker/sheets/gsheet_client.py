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


def get_worksheet_by_gid(sheet_id: str, gid: int):
    """sheet_id 스프레드시트에서 gid(시트 URL의 "#gid=..." 숫자)에 해당하는
    탭을 연다. get_worksheet()과 달리 탭 이름이 아니라 gid로 찾는다 — 탭
    이름은 사람이 바꿀 수 있지만 gid는 바뀌지 않는다.

    공개 다운로드 링크로 읽기만 하던 기존 방식(refund/sheet_reader.py)과
    달리 이 함수는 "쓰기"가 목적이라, 이 스프레드시트에 서비스 계정
    이메일(credentials JSON의 client_email)이 '편집자'로 공유돼 있어야
    한다 — 안 돼 있으면 gspread가 권한 오류를 낸다."""
    creds = Credentials.from_service_account_file(config.GOOGLE_SHEETS_CREDENTIALS_PATH, scopes=SCOPES)
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(sheet_id)

    for worksheet in spreadsheet.worksheets():
        if worksheet.id == gid:
            return worksheet

    raise ValueError(f"gid={gid}에 해당하는 시트 탭을 찾지 못했습니다.")


def append_rows(worksheet, rows: list[list]) -> None:
    """rows를 시트의 현재 마지막 데이터 행 바로 다음 줄부터 그대로 이어붙인다."""
    worksheet.append_rows(rows, value_input_option="USER_ENTERED")
