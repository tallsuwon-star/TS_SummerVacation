"""환불(계좌 환불) 처리 대상을 구글 시트에서 읽어온다.

시트의 실제 컬럼 순서/개수가 바뀔 수 있어 컬럼 위치를 하드코딩하지 않고,
"계좌 환불 (차액 환불 가능)" 섹션 제목 다음 행을 헤더로 읽어 컬럼명으로
필요한 값을 찾는다. 회원 계좌정보(계좌번호/은행명/예금주)는 개인정보라
헤더명이 통일돼 있지 않을 수 있으므로, 사용자가 설명한 대로 "행에서 가장
오른쪽(마지막)에 값이 있는 칸"을 계좌정보 자유 텍스트로 간주해 파싱한다.

처리 대상 판단은 "처리유무" 칸의 텍스트가 아니라 셀 배경색이 주황색
(#FF9900)인지로 한다 — 사용자가 확인해준 실제 기준. 텍스트는 그대로
"입금확인중"일 수 있지만, 색이 곧 처리 대상 표시이므로 색만 본다.

이 모듈이 다루는 값(회원명/이메일/계좌정보)은 개인정보이므로, 여기서 읽은
결과는 화면에 표로 보여주는 용도로만 쓰고 그 외 외부로 전송/기록하지 않는다.
"""

import re

import gspread
from google.oauth2.service_account import Credentials
from gspread.utils import rowcol_to_a1

from .. import config
from .bank_format import format_account_number

SECTION_TITLE = "계좌 환불 (차액 환불 가능)"
STATUS_HEADER_CANDIDATES = ["처리유무", "처리 유무", "처리상태", "처리 상태"]

# 처리 대상 표시 색(#FF9900)과 셀 실제 배경색을 대조할 때 허용할 오차.
# 구글시트가 값을 0~1 사이 실수로 저장/반환하면서 미세한 반올림 차이가
# 생길 수 있어 약간의 허용 범위를 둔다.
TARGET_COLOR_HEX = "FF9900"
COLOR_TOLERANCE = 0.05

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


def _hex_to_rgb01(hex_color: str) -> tuple[float, float, float]:
    hex_color = hex_color.lstrip("#")
    return (
        int(hex_color[0:2], 16) / 255,
        int(hex_color[2:4], 16) / 255,
        int(hex_color[4:6], 16) / 255,
    )


def _is_target_color(color: dict | None) -> bool:
    if not color:
        return False
    target_r, target_g, target_b = _hex_to_rgb01(TARGET_COLOR_HEX)
    return (
        abs(color.get("red", 0) - target_r) <= COLOR_TOLERANCE
        and abs(color.get("green", 0) - target_g) <= COLOR_TOLERANCE
        and abs(color.get("blue", 0) - target_b) <= COLOR_TOLERANCE
    )


def _fetch_background_colors(worksheet, num_rows: int, num_cols: int) -> list[list[dict | None]]:
    """all_values와 같은 범위(A1부터)의 셀 배경색을, all_values와 같은 행/열
    인덱스로 대응되는 2차원 리스트로 가져온다. 값이 없는 셀은 API가 응답에서
    아예 생략하기도 해서 행/칸별로 길이가 짧을 수 있다 (호출부에서 bounds
    체크 필요)."""
    if num_rows == 0 or num_cols == 0:
        return []

    end_a1 = rowcol_to_a1(num_rows, num_cols)
    a1_range = f"'{worksheet.title}'!A1:{end_a1}"
    metadata = worksheet.spreadsheet.fetch_sheet_metadata(
        params={
            "ranges": a1_range,
            "fields": (
                "sheets.data.rowData.values.effectiveFormat.backgroundColor,"
                "sheets.data.rowData.values.userEnteredFormat.backgroundColor"
            ),
        }
    )

    sheets_data = metadata.get("sheets") or []
    if not sheets_data:
        return []
    data_blocks = sheets_data[0].get("data") or []
    if not data_blocks:
        return []
    row_data = data_blocks[0].get("rowData") or []

    colors: list[list[dict | None]] = []
    for row in row_data:
        row_colors = []
        for cell in row.get("values", []):
            effective = cell.get("effectiveFormat", {}).get("backgroundColor")
            entered = cell.get("userEnteredFormat", {}).get("backgroundColor")
            row_colors.append(effective or entered)
        colors.append(row_colors)
    return colors


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
    """"계좌 환불 (차액 환불 가능)" 섹션에서 "처리유무" 칸이 주황색(#FF9900)인
    행만 골라 회원명/이메일/환불금액/계좌정보(파싱 + 은행별 대시 포맷)로
    정리해 반환한다."""
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

    num_cols = max((len(row) for row in all_values), default=0)
    colors = _fetch_background_colors(worksheet, len(all_values), num_cols)

    results: list[dict] = []
    for row_idx, row in enumerate(all_values[header_row_idx + 1 :], start=header_row_idx + 1):
        if not any(cell.strip() for cell in row):
            break  # 빈 행 = 섹션 끝
        if any(cell.strip() == SECTION_TITLE for cell in row):
            break  # 다음 섹션 시작

        row_colors = colors[row_idx] if row_idx < len(colors) else []
        status_color = row_colors[status_idx] if status_idx < len(row_colors) else None
        if not _is_target_color(status_color):
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
