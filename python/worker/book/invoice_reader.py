"""택배사(예: CJ대한통운) '발송처리' 결과로 받은 송장 엑셀을 읽어, 헤더를
뺀 실제 데이터 행만 돌려준다.

사용자가 준 실제 파일(39개 컬럼, 1행 헤더)을 보면 "받는분"/"받는분전화번호"/
"받는분주소"/"운송장번호" 컬럼이 book_charge.py가 읽어온 받는사람 정보와
이름/전화/주소가 정확히 같다 — 이 네 컬럼으로 LMS 주문과 대조(매칭)한다.
단, 택배사마다 컬럼 순서/개수가 다를 수 있어 위치를 하드코딩하지 않고
헤더명으로 찾는다(refund/sheet_reader.py와 같은 방식).

구글 시트에는 사용자가 요청한 대로 헤더를 뺀 나머지 행을 원본 컬럼 순서
그대로 이어붙인다 — 특정 칸만 골라 재구성하지 않는다."""

import openpyxl

NAME_HEADER_CANDIDATES = ["받는분"]
PHONE_HEADER_CANDIDATES = ["받는분전화번호"]
ADDRESS_HEADER_CANDIDATES = ["받는분주소"]
INVOICE_NO_HEADER_CANDIDATES = ["운송장번호"]


class InvoiceReadError(Exception):
    pass


def _normalize_header(value) -> str:
    return (value or "").replace("\r\n", "").replace("\n", "").strip()


def _cell_value(value):
    """구글 시트에 그대로 써도 되는 형태로 정리한다. 수량/운임처럼 정수인데
    float로 읽히는 값(예: 1.0)은 "1.0"으로 적히지 않게 정수로 바꾸고, 빈
    칸은 빈 문자열로 통일한다."""
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def _find_header_index(headers: list[str], candidates: list[str]) -> int | None:
    normalized = [_normalize_header(h) for h in headers]
    for i, header in enumerate(normalized):
        if header in candidates:
            return i
    return None


def read_invoice_rows(file_path: str) -> dict:
    """택배사 송장 엑셀(file_path)을 읽어 헤더 정보 + 데이터 행을 반환한다.

    반환값: {"headers": [...], "rows": [[...], ...],
             "nameIdx", "phoneIdx", "addressIdx", "invoiceNoIdx"}
    rows는 완전히 빈 행을 뺀 데이터 행만, 원본 컬럼 순서 그대로 담는다.
    필요한 헤더(받는분/받는분전화번호/받는분주소/운송장번호)를 하나라도
    못 찾으면 InvoiceReadError를 낸다 — 조용히 엉뚱한 칸을 쓰지 않는다."""
    try:
        workbook = openpyxl.load_workbook(file_path, data_only=True)
    except Exception as exc:  # noqa: BLE001 - 파일이 아예 안 열리는 경우도 사람이 읽을 메시지로
        raise InvoiceReadError(f"엑셀 파일을 열지 못했습니다: {exc}") from exc

    worksheet = workbook.worksheets[0]
    rows_iter = worksheet.iter_rows(values_only=True)

    try:
        header_row = next(rows_iter)
    except StopIteration as exc:
        raise InvoiceReadError("엑셀 파일에 내용이 없습니다.") from exc

    headers = [h if h is not None else "" for h in header_row]

    name_idx = _find_header_index(headers, NAME_HEADER_CANDIDATES)
    phone_idx = _find_header_index(headers, PHONE_HEADER_CANDIDATES)
    address_idx = _find_header_index(headers, ADDRESS_HEADER_CANDIDATES)
    invoice_no_idx = _find_header_index(headers, INVOICE_NO_HEADER_CANDIDATES)

    missing = [
        label
        for label, idx in (
            ("받는분", name_idx),
            ("받는분전화번호", phone_idx),
            ("받는분주소", address_idx),
            ("운송장번호", invoice_no_idx),
        )
        if idx is None
    ]
    if missing:
        raise InvoiceReadError(f"헤더에서 다음 컬럼을 찾지 못했습니다: {', '.join(missing)}")

    data_rows = []
    for row in rows_iter:
        if row is None or not any(v is not None and str(v).strip() for v in row):
            continue  # 완전히 빈 행은 건너뛴다 (시트 끝의 빈 줄 등)
        data_rows.append([_cell_value(v) for v in row])

    return {
        "headers": list(headers),
        "rows": data_rows,
        "nameIdx": name_idx,
        "phoneIdx": phone_idx,
        "addressIdx": address_idx,
        "invoiceNoIdx": invoice_no_idx,
    }
