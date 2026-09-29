"""환불(계좌 환불) 처리 대상을 구글 시트에서 읽어온다.

시트의 실제 컬럼 순서/개수가 바뀔 수 있어 컬럼 위치를 하드코딩하지 않고,
"계좌 환불 (차액 환불 가능)" 섹션 제목 다음 행을 헤더로 읽어 컬럼명으로
필요한 값을 찾는다. 회원 계좌정보(계좌번호/은행명/예금주)는 개인정보라
헤더명이 통일돼 있지 않을 수 있으므로, 사용자가 설명한 대로 "행에서 가장
오른쪽(마지막)에 값이 있는 칸"을 계좌정보 자유 텍스트로 간주해 파싱한다.

이 모듈이 다루는 값(회원명/이메일/계좌정보)은 개인정보이므로, 여기서 읽은
결과는 화면에 표로 보여주는 용도로만 쓰고 그 외 외부로 전송/기록하지 않는다.
"""

import re

import gspread
from google.oauth2.service_account import Credentials

from .. import config
from .bank_format import format_account_number

SECTION_TITLE = "계좌 환불 (차액 환불 가능)"
STATUS_HEADER_CANDIDATES = ["처리유무", "처리 유무", "처리상태", "처리 상태"]
TARGET_STATUS = "입금확인중"

NAME_HEADER_CANDIDATES = ["회원 이름", "회원명", "이름"]
EMAIL_HEADER_CANDIDATES = ["ID", "이메일", "회원 ID", "회원 이메일"]
AMOUNT_HEADER_CANDIDATES = ["환불금액", "환불 금액"]

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.readonly",
]

# "<메모>, <비고>, <계좌번호> <은행명> <예금주>" 형태 자유 텍스트에서
# 뒤쪽 "계좌번호 은행명 예금주" 부분을 뽑아낸다.
ACCOUNT_INFO_PATTERN = re.compile(r"([\d\-\s]*\d)\s+(\S*은행\S*|\S*뱅크\S*|우체국|새마을금고|신협)\s+(\S.*)")


def _get_worksheet():
    creds = Credentials.from_service_account_file(config.GOOGLE_SHEETS_CREDENTIALS_PATH, scopes=SCOPES)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(config.REFUND_SHEET_ID)
    return sheet.get_worksheet(0)


def _find_header_index(headers: list[str], candidates: list[str]) -> int | None:
    for i, header in enumerate(headers):
        if header.strip() in candidates:
            return i
    return None


def _parse_account_info(raw_text: str) -> dict:
    """자유 텍스트에서 메모/계좌번호/은행명/예금주를 뽑아낸다.
    형식이 예상과 다르면 needs_review=True로 표시하고 원문을 그대로 담아 반환한다."""
    if not raw_text or not raw_text.strip():
        return {
            "memo": "",
            "account_number": "",
            "bank_name": "",
            "account_holder": "",
            "needs_review": True,
        }

    match = ACCOUNT_INFO_PATTERN.search(raw_text)
    if not match:
        return {
            "memo": raw_text.strip(),
            "account_number": "",
            "bank_name": "",
            "account_holder": "",
            "needs_review": True,
        }

    account_part, bank_name, holder = match.groups()
    memo = raw_text[: match.start()].rstrip(", ").strip()

    return {
        "memo": memo,
        "account_number": "".join(ch for ch in account_part if ch.isdigit()),
        "bank_name": bank_name.strip(),
        "account_holder": holder.strip(),
        "needs_review": False,
    }


def fetch_pending_refunds() -> list[dict]:
    """"계좌 환불 (차액 환불 가능)" 섹션에서 처리유무=="입금확인중"인 행만 골라
    회원명/이메일/환불금액/계좌정보(파싱 + 은행별 대시 포맷)로 정리해 반환한다."""
    worksheet = _get_worksheet()
    all_values = worksheet.get_all_values()

    section_row_idx = None
    for i, row in enumerate(all_values):
        if any(cell.strip() == SECTION_TITLE for cell in row):
            section_row_idx = i
            break

    if section_row_idx is None:
        raise ValueError(f'시트에서 "{SECTION_TITLE}" 섹션을 찾지 못했습니다.')

    header_row_idx = section_row_idx + 1
    if header_row_idx >= len(all_values):
        raise ValueError(f'"{SECTION_TITLE}" 섹션 아래에 헤더 행이 없습니다.')

    headers = all_values[header_row_idx]
    status_idx = _find_header_index(headers, STATUS_HEADER_CANDIDATES)
    name_idx = _find_header_index(headers, NAME_HEADER_CANDIDATES)
    email_idx = _find_header_index(headers, EMAIL_HEADER_CANDIDATES)
    amount_idx = _find_header_index(headers, AMOUNT_HEADER_CANDIDATES)

    if status_idx is None:
        raise ValueError(f'헤더에서 "처리유무" 컬럼을 찾지 못했습니다. 헤더: {headers}')

    results: list[dict] = []
    for row in all_values[header_row_idx + 1 :]:
        if not any(cell.strip() for cell in row):
            break  # 빈 행 = 섹션 끝
        if any(cell.strip() == SECTION_TITLE for cell in row):
            break  # 다음 섹션 시작

        status = row[status_idx].strip() if status_idx < len(row) else ""
        if status != TARGET_STATUS:
            continue

        # 계좌정보 칸은 헤더명이 통일돼 있지 않을 수 있어(개인정보라 자유
        # 서식으로 적히는 경우가 많음), 행에서 값이 있는 마지막 칸을
        # 계좌정보로 간주한다 (사용자 설명: "우측에 계좌정보들이 나와있음").
        non_empty_indices = [i for i, cell in enumerate(row) if cell.strip()]
        account_info_idx = non_empty_indices[-1] if non_empty_indices else None
        account_info_raw = row[account_info_idx] if account_info_idx is not None else ""

        parsed = _parse_account_info(account_info_raw)
        if parsed["account_number"] and parsed["bank_name"]:
            dash_result = format_account_number(parsed["account_number"], parsed["bank_name"])
        else:
            dash_result = {"formatted": parsed["account_number"], "verified": False}

        results.append(
            {
                "memberName": row[name_idx].strip() if name_idx is not None and name_idx < len(row) else "",
                "memberEmail": row[email_idx].strip() if email_idx is not None and email_idx < len(row) else "",
                "refundAmount": row[amount_idx].strip() if amount_idx is not None and amount_idx < len(row) else "",
                "bankName": parsed["bank_name"],
                "accountHolder": parsed["account_holder"],
                "accountNumberFormatted": dash_result["formatted"],
                "accountNumberVerified": dash_result["verified"],
                "needsReview": parsed["needs_review"] or not dash_result["verified"],
            }
        )

    return results
