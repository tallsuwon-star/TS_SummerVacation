"""네이버 스마트스토어 "항목별 정산 내역" 원본 엑셀을, 사용자가 매달 직접
만들던 "정산정리" 제출용 엑셀과 같은 형식으로 정리한다.

사용자가 매달 하던 일(원본 엑셀을 받아서):
  1. 상품명 / 정산완료일 / 정산기준금액(A) / Npay 수수료(B) / 매출연동 수수료
     합계(C) / 무이자할부 수수료(D) / 정산상태 칸만 남기고 나머지(주문번호,
     상품주문번호, 구분, 구매자명, 정산기준일, 정산예정일, 세금신고기준일,
     계약번호 등)는 전부 지운다.
  2. 그 옆에 '정산예정금액(A+B+C+D)' 열을 추가해 건별로 A~D를 더한다.
  3. 정산완료일이 바뀌는 지점마다 그날 하루치 합계(A~D, 정산예정금액)를
     한 줄 추가해 넣는다.
  4. 맨 아래에 전체 합산 금액 줄('합계')을 추가한다.
를 그대로 자동화한 것. 이 모듈은 파일을 읽어 정리된 행 목록을 만드는
부분만 맡고, 실제 파일 저장은 jobs/naver_settlement_generate.py가 한다 —
화면에서 확인한 내용과 실제로 저장되는 내용이 어긋나지 않도록, 화면에
보여준 행을 그대로 받아 쓴다(이 코드베이스 전반의 원칙과 동일).

원본 파일의 열 순서/개수가 매달 똑같다는 보장이 없어, 열 위치를
하드코딩하지 않고 헤더 이름으로 찾는다."""

import re
from datetime import date, datetime

import openpyxl

REQUIRED_HEADERS = [
    "상품명",
    "정산완료일",
    "정산기준금액(A)",
    "Npay 수수료(B)",
    "매출연동 수수료 합계(C)",
    "무이자할부 수수료(D)",
    "정산상태",
]

OUTPUT_HEADERS = [
    "상품명",
    "정산완료일",
    "정산기준금액(A)",
    "Npay 수수료(B)",
    "매출연동 수수료 합계(C)",
    "무이자할부 수수료(D)",
    "정산예정금액(A+B+C+D)",
    "정산상태",
]

_HEADER_SCAN_ROWS = 10
_DATE_RE = re.compile(r"^(\d{4})\.(\d{1,2})\.(\d{1,2})$")


class SettlementReadError(Exception):
    pass


def _find_header_row(worksheet) -> tuple[int, dict]:
    """REQUIRED_HEADERS가 전부 있는 행을 찾아 (그 행 번호, {헤더명: 0-based
    열 인덱스})를 반환한다. 처음 _HEADER_SCAN_ROWS줄 안에서 못 찾으면
    오류를 낸다."""
    for row_cells in worksheet.iter_rows(min_row=1, max_row=_HEADER_SCAN_ROWS):
        headers = {}
        for cell in row_cells:
            if cell.value is not None:
                headers[str(cell.value).strip()] = cell.column - 1

        if all(h in headers for h in REQUIRED_HEADERS):
            row_num = row_cells[0].row
            return row_num, {h: headers[h] for h in REQUIRED_HEADERS}

    raise SettlementReadError(
        f"헤더에서 다음 컬럼을 찾지 못했습니다: {', '.join(REQUIRED_HEADERS)}"
    )


def _parse_date(value):
    """'YYYY.MM.DD' 텍스트 형식의 정산완료일을 날짜로 바꾼다. 이미 날짜/
    시각 값이면 그대로 date로, 그 외(형식이 다르거나 비어있음)는 원본
    값을 그대로 둔다 — 추측해서 바꾸지 않는다."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value

    text = str(value or "").strip()
    match = _DATE_RE.match(text)
    if not match:
        return value

    year, month, day = (int(g) for g in match.groups())
    try:
        return date(year, month, day)
    except ValueError:
        return value


def _stringify_date(value):
    """정산완료일 값을 JSON으로 안전하게 보낼 수 있는 "YYYY.MM.DD" 텍스트로
    바꾼다. 원본 엑셀의 날짜 칸이 실제 날짜/시각 타입으로 들어오는 경우도
    있어(텍스트가 아니라), 이 함수를 거쳐야 job이 datetime.date 객체를
    그대로 JSON으로 내보내려다 죽는 사고를 막을 수 있다. 이미 문자열이거나
    형식을 모르면 그대로 둔다."""
    if isinstance(value, datetime):
        value = value.date()
    if isinstance(value, date):
        return f"{value.year}.{value.month:02d}.{value.day:02d}"
    return value


def _to_number(value) -> int:
    if value is None:
        return 0
    if isinstance(value, (int, float)):
        return int(value)
    try:
        return int(str(value).replace(",", "").strip() or 0)
    except ValueError:
        return 0


def build_settlement_rows(file_path: str) -> list[dict]:
    """네이버 정산 내역 원본 엑셀(file_path)을 읽어, 필요한 컬럼만 남기고
    정산완료일별 소계 + 전체 합계 행을 끼워 넣은 행 목록을 반환한다.

    각 행은 {"rowType": "data"|"subtotal"|"total", "productName",
    "settleDate", "amountA", "feeB", "feeC", "feeD", "expectedTotal",
    "status"} 형태다. 원본 순서(이미 정산완료일 기준 오름차순으로 돼
    있다고 봄)를 그대로 유지하며, 정산완료일 값이 바뀌는 지점마다 소계를
    끼워 넣는다 — 재정렬하지 않는다(원본 순서를 임의로 바꾸면 사람이
    원본과 대조하기 어려워지기 때문)."""
    try:
        workbook = openpyxl.load_workbook(file_path, data_only=True)
    except Exception as exc:  # noqa: BLE001
        raise SettlementReadError(f"엑셀 파일을 열지 못했습니다: {exc}") from exc

    worksheet = workbook.worksheets[0]
    header_row_num, col = _find_header_row(worksheet)

    data_rows = []
    for row in worksheet.iter_rows(min_row=header_row_num + 1, values_only=True):
        if row is None or not any(v is not None and str(v).strip() for v in row):
            continue  # 완전히 빈 행은 건너뛴다

        data_rows.append(
            {
                "productName": row[col["상품명"]],
                "settleDate": _stringify_date(row[col["정산완료일"]]),
                "amountA": _to_number(row[col["정산기준금액(A)"]]),
                "feeB": _to_number(row[col["Npay 수수료(B)"]]),
                "feeC": _to_number(row[col["매출연동 수수료 합계(C)"]]),
                "feeD": _to_number(row[col["무이자할부 수수료(D)"]]),
                "status": row[col["정산상태"]],
            }
        )

    if not data_rows:
        raise SettlementReadError("정산 내역 데이터 행을 찾지 못했습니다.")

    for row in data_rows:
        row["expectedTotal"] = row["amountA"] + row["feeB"] + row["feeC"] + row["feeD"]

    _SENTINEL = object()

    output_rows: list[dict] = []
    grand = {"amountA": 0, "feeB": 0, "feeC": 0, "feeD": 0, "expectedTotal": 0}
    group = {"amountA": 0, "feeB": 0, "feeC": 0, "feeD": 0, "expectedTotal": 0}
    current_date = _SENTINEL

    def flush_group():
        if current_date is _SENTINEL:
            return  # 아직 첫 그룹도 시작 안 함
        output_rows.append(
            {
                "rowType": "subtotal",
                "productName": None,
                "settleDate": current_date,  # 이미 _stringify_date를 거친 JSON-safe 문자열
                **group,
                "status": None,
            }
        )

    for row in data_rows:
        if row["settleDate"] != current_date:
            flush_group()
            group = {"amountA": 0, "feeB": 0, "feeC": 0, "feeD": 0, "expectedTotal": 0}
            current_date = row["settleDate"]

        output_rows.append({**row, "rowType": "data"})

        for key in group:
            group[key] += row[key]
            grand[key] += row[key]

    flush_group()

    output_rows.append(
        {
            "rowType": "total",
            "productName": None,
            "settleDate": "합계",
            **grand,
            "status": None,
        }
    )

    return output_rows


def write_settlement_rows(rows: list[dict], output_path) -> None:
    """build_settlement_rows()가 만든(그리고 화면에서 확인된) 행을 그대로
    새 엑셀로 저장한다. 소계/합계 행은 굵게 표시해 한눈에 구분되게 한다.

    일렉트론을 거쳐 JSON으로 왕복한 rows라 정산완료일은 전부 문자열이다.
    소계 행("YYYY.MM.DD" 형식)만 실제 날짜 타입으로 되돌려 써서, 기존에
    사람이 직접 만들던 파일처럼 소계 줄의 날짜가 엑셀에서 진짜 날짜로
    인식되게 한다 — 전체 합계 행의 "합계" 라벨은 날짜가 아니므로 그대로
    문자열로 둔다."""
    workbook = openpyxl.Workbook()
    worksheet = workbook.active
    worksheet.title = "결제정산 - 일별상세"
    worksheet.append(OUTPUT_HEADERS)

    bold_font = openpyxl.styles.Font(bold=True)

    for row in rows:
        row_type = row.get("rowType")
        settle_date = row.get("settleDate")
        if row_type == "subtotal":
            settle_date = _parse_date(settle_date)

        worksheet.append(
            [
                row.get("productName"),
                settle_date,
                row.get("amountA"),
                row.get("feeB"),
                row.get("feeC"),
                row.get("feeD"),
                row.get("expectedTotal"),
                row.get("status"),
            ]
        )
        if row_type in ("subtotal", "total"):
            for cell in worksheet[worksheet.max_row]:
                cell.font = bold_font

    workbook.save(output_path)
