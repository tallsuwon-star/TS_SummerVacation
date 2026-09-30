"""카드취소 대상 회원의 상담관리 화면에서, 구글 시트의 "요청자"와 이름이
같고 최근(기본 7일 이내) 등록된 "상담 내용 작성" 글을 찾아, 그 글의 상세
페이지에 있는 신용카드 매출전표(결제 시간/구매자명/상품정보 등)를 읽어온다.

이 모듈은 조회만 한다 — student.memo_note.php의 삭제/수정 링크는 어디서도
클릭하지 않고, 오직 읽기 전용 상세보기 링크(view_mode=detail)로만 이동한다.

detail_url로 이동하면 사이드바/카테고리 드롭다운/상담 목록까지 포함된
전체 관리자 페이지가 그대로 로딩되고, 그 안 어딘가에 이 건의 매출전표
내용이 끼어 들어가 있는 구조라, "페이지 전체 텍스트에서 표만 뺀 나머지"
식으로 뽑으면 사이드바 메뉴/카테고리 목록까지 전부 섞여 들어간다. 그래서
매출전표 표(카드종류/카드번호 등이 적힌 표)를 먼저 찾고, 그 표를 포함하되
사이드바·카테고리 드롭다운 같은 "페이지 전체" 요소는 포함하지 않는 가장
작은 조상 태그로 범위를 좁혀서 그 안에서만 메모/금액을 뽑는다.

정확도가 매우 중요한 기능이라 다음 원칙을 지킨다:
- 작성자 이름은 정확히 일치해야만 후보로 본다 (부분일치 금지).
- 매출전표의 핵심 항목(거래일자/구매자/상품명/승인번호/금액)을 전부 읽어낸
  경우에만 needsReview=False로 표시하고, 하나라도 못 찾으면 반드시
  needsReview=True로 표시해 사람이 URL을 직접 열어 확인하게 한다.
- 시트 환불금액과 전표 금액이 다르면 "불일치"로 명확히 표시하고, 절대
  스스로 "맞다"고 얼버무리지 않는다.
- 후보가 여러 건이면 하나를 임의로 고르지 않고 전부 반환한다.
"""

import re
import time
from dataclasses import dataclass
from datetime import date, timedelta

from bs4 import BeautifulSoup
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from .. import config
from ..utils.progress import emit_log

DEFAULT_LOOKBACK_DAYS = 7

# "[구분] - 작성자" 형태에서 구분/작성자를 뽑는다. 구분 텍스트 자체에 "-"가
# 들어있는 경우("정규 - 기타")가 있어, 반드시 닫는 대괄호 "]" 뒤의 "-"부터
# 작성자로 본다.
_CATEGORY_RE = re.compile(r"^\[(.*?)\]")
_AUTHOR_RE = re.compile(r"\]\s*-\s*(.+)$")
_DATE_RE = re.compile(r"(\d{4})\.(\d{2})\.(\d{2})")

RECEIPT_FIELD_LABELS = [
    "카드종류",
    "카드번호",
    "거래일자",
    "취소일자",
    "구매자",
    "상품명",
    "유효기간",
    "거래유형",
    "일반/할부",
    "승인번호",
]
_LABEL_ALTERNATION = "|".join(re.escape(label) for label in RECEIPT_FIELD_LABELS)
# "금액"/"부가세"/"합계"는 콜론 없이(표 칸에 라벨만) 나오는 자릿수별 금액
# 표라서, "승인번호:..." 값이 뒤에 이어지는 금액 표 글자까지 먹어치우지
# 않도록 이 라벨들도(콜론 없이) 값의 끝 경계로 잡아준다.
_AMOUNT_GRID_LABELS = ("금액", "부가세", "합계")
_STOP_LABEL_ALTERNATION = "|".join(re.escape(label) for label in (*RECEIPT_FIELD_LABELS, *_AMOUNT_GRID_LABELS))
_RECEIPT_FIELD_RE = re.compile(
    rf"({_LABEL_ALTERNATION})\s*[:：]\s*(.*?)(?=(?:{_STOP_LABEL_ALTERNATION})(?:\s*[:：])?|$)"
)

# 매출전표를 식별하는 기준이 되는 라벨 (이 중 하나라도 있는 <table>을 찾는다).
_RECEIPT_MARKER_LABELS = ("카드종류", "카드번호", "승인번호")

# detail_url로 이동했을 때 함께 딸려오는 "페이지 전체" 요소들 — 조상 태그를
# 넓혀가다가 이 중 하나라도 텍스트에 섞이면 그 전 단계에서 멈춘다.
_PAGE_FURNITURE_MARKERS = (
    "TALKSTATION LMS",
    "Hidden Menu",
    "- CATEGORY",
    "보강권관리",
    "회원 기본수강 정보",
    "Showing 1 page of",
)
_MAX_ANCESTOR_HOPS = 6

REQUIRED_RECEIPT_FIELDS = ["거래일자", "구매자", "상품명", "승인번호", "금액"]


class ReceiptCheckError(Exception):
    pass


@dataclass
class MemoEntry:
    memo_no: str
    author: str
    category: str
    registered_date: date
    detail_url: str


def list_recent_memo_entries(
    driver, requester_name: str, lookback_days: int = DEFAULT_LOOKBACK_DAYS
) -> list[MemoEntry]:
    """현재 열려있는 상담관리 화면의 "상담 내용 작성" 목록에서, 작성자가
    requester_name과 정확히 같고 등록일이 최근 lookback_days일 이내인
    항목만 찾아 반환한다."""
    try:
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "td.list-type-left")))
    except TimeoutException as exc:
        raise ReceiptCheckError('"상담 내용 작성" 목록을 찾지 못했습니다.') from exc

    cutoff = date.today() - timedelta(days=lookback_days)
    entries: list[MemoEntry] = []

    left_cells = driver.find_elements(By.CSS_SELECTOR, "td.list-type-left")
    for cell in left_cells:
        try:
            p_text = cell.find_element(By.TAG_NAME, "p").text.strip()
        except NoSuchElementException:
            continue

        author_match = _AUTHOR_RE.search(p_text)
        if not author_match:
            continue
        author = author_match.group(1).strip()
        if author != requester_name:
            continue

        category_match = _CATEGORY_RE.match(p_text)
        category = category_match.group(1).strip() if category_match else ""

        try:
            link = cell.find_element(By.TAG_NAME, "a")
        except NoSuchElementException:
            continue
        detail_url = link.get_attribute("href") or ""
        memo_no_match = re.search(r"memo_no=(\d+)", detail_url)
        if not memo_no_match:
            continue

        try:
            date_cell = cell.find_element(By.XPATH, "following-sibling::td[@class='list-type'][1]")
        except NoSuchElementException:
            continue
        date_match = _DATE_RE.search(date_cell.text)
        if not date_match:
            continue
        year, month, day = (int(g) for g in date_match.groups())
        registered_date = date(year, month, day)
        if registered_date < cutoff:
            continue

        entries.append(
            MemoEntry(
                memo_no=memo_no_match.group(1),
                author=author,
                category=category,
                registered_date=registered_date,
                detail_url=detail_url,
            )
        )

    return entries


def _find_receipt_container(soup: BeautifulSoup):
    """매출전표 라벨이 있는 <table>을 찾고, 그 표를 포함하되 사이드바/
    카테고리 드롭다운 같은 페이지 전체 요소는 포함하지 않는 가장 작은
    조상을 찾는다. 못 찾으면 None."""
    receipt_table = None
    for table in soup.find_all("table"):
        text = table.get_text(" ", strip=True)
        if any(marker in text for marker in _RECEIPT_MARKER_LABELS):
            receipt_table = table
            break
    if receipt_table is None:
        return None

    best = receipt_table
    node = receipt_table
    for _ in range(_MAX_ANCESTOR_HOPS):
        parent = node.parent
        if parent is None or parent.name in ("body", "html", "[document]") or not hasattr(parent, "get_text"):
            break
        parent_text = parent.get_text(" ", strip=True)
        if any(marker in parent_text for marker in _PAGE_FURNITURE_MARKERS):
            break
        best = parent
        node = parent
    return best


def _extract_amount_from_grid(container) -> dict:
    """매출전표의 금액/부가세/합계는 자릿수별로 칸이 나뉜 표라 일반
    "라벨:값" 패턴으로 못 뽑는다. "금액"/"부가세"/"합계" 글자가 있는 행에서
    그 뒤 셀들의 숫자를 순서대로 이어붙여 실제 금액을 복원한다."""
    amounts: dict[str, str] = {}
    for row in container.find_all("tr"):
        cells = row.find_all("td")
        if not cells:
            continue
        label = cells[0].get_text(strip=True)
        if label not in ("금액", "부가세", "합계"):
            continue
        digits = "".join(cell.get_text(strip=True) for cell in cells[1:] if cell.get_text(strip=True).isdigit())
        if digits:
            amounts[label] = digits
    return amounts


def _extract_receipt_fields(container) -> dict:
    text = container.get_text(" ", strip=True)
    fields: dict[str, str] = {}
    for match in _RECEIPT_FIELD_RE.finditer(text):
        label, value = match.group(1), match.group(2).strip()
        if label not in fields:  # 같은 라벨이 여러 번 매칭되면 첫 값만 쓴다
            fields[label] = value

    amounts = _extract_amount_from_grid(container)
    # "합계"(부가세 포함 최종 금액)를 우선하고, 없으면 "금액"을 쓴다.
    if amounts.get("합계"):
        fields["금액"] = amounts["합계"]
    elif amounts.get("금액"):
        fields["금액"] = amounts["금액"]

    return fields


def _extract_personal_note(container) -> str:
    """매출전표 표(<table>)를 전부 제거하고 남는 텍스트 = 담당자가 직접
    적은 메모(예: "전체 카드 취소", "필리핀 > 영미권 수강 변경")."""
    container_copy = BeautifulSoup(str(container), "html.parser")
    for table in container_copy.find_all("table"):
        table.decompose()
    return container_copy.get_text(" ", strip=True)


def _fetch_receipt_from_current_context(driver) -> dict | None:
    soup = BeautifulSoup(driver.page_source, "html.parser")
    container = _find_receipt_container(soup)
    if container is None:
        return None
    return {"fields": _extract_receipt_fields(container), "personalNote": _extract_personal_note(container)}


def fetch_receipt_detail(driver, detail_url: str) -> dict:
    """상세 페이지(view_mode=detail)로 이동해 매출전표 내용을 읽어온다.
    이 함수는 조회(GET 이동)만 하며, 그 페이지의 삭제/수정 링크는 절대
    클릭하지 않는다."""
    driver.get(detail_url)
    time.sleep(config.REQUEST_DELAY_SECONDS)

    result = _fetch_receipt_from_current_context(driver)

    if result is None:
        # 메인 문서에 없으면 el-rte 편집기 특성상 iframe 안에 렌더링됐을 수
        # 있어 각 iframe을 순서대로 확인한다.
        for iframe in driver.find_elements(By.TAG_NAME, "iframe"):
            try:
                driver.switch_to.frame(iframe)
                result = _fetch_receipt_from_current_context(driver)
            except Exception:  # noqa: BLE001 - iframe 하나가 이상해도 다음 것을 계속 시도
                result = None
            finally:
                driver.switch_to.default_content()
            if result is not None:
                break

    if result is None:
        return {
            "fields": {},
            "personalNote": "",
            "needsReview": True,
            "reviewReason": "매출전표 내용을 찾지 못했습니다. 이 URL을 직접 열어 확인해주세요.",
        }

    missing = [f for f in REQUIRED_RECEIPT_FIELDS if not result["fields"].get(f)]
    return {
        "fields": result["fields"],
        "personalNote": result["personalNote"],
        "needsReview": bool(missing),
        "reviewReason": (f"매출전표에서 다음 항목을 찾지 못했습니다: {', '.join(missing)}" if missing else ""),
    }


def _normalize_amount(text: str) -> str | None:
    digits = re.sub(r"[^\d]", "", text or "")
    return digits or None


def compare_amounts(sheet_refund_amount: str, receipt_fields: dict) -> dict:
    """시트의 환불금액과 전표 금액이 일치하는지 확인한다. 확실하지 않으면
    (둘 중 하나라도 숫자를 못 찾으면) "일치"/"불일치" 둘 다 단정하지 않고
    "확인 필요"로 표시한다."""
    sheet_digits = _normalize_amount(sheet_refund_amount)
    receipt_digits = receipt_fields.get("금액")

    if not sheet_digits or not receipt_digits:
        return {"verdict": "확인 필요", "note": "금액을 비교할 수 없습니다 (시트 또는 전표에서 금액을 찾지 못함)."}
    if sheet_digits == receipt_digits:
        return {"verdict": "일치", "note": f"시트 {sheet_digits}원 = 전표 {receipt_digits}원"}
    return {"verdict": "불일치", "note": f"시트 {sheet_digits}원 ≠ 전표 {receipt_digits}원"}


def check_card_cancel_receipts(
    driver,
    requester_name: str,
    sheet_refund_amount: str = "",
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
) -> list[dict]:
    """현재 열려있는 상담관리 화면에서 요청자 이름 + 최근 등록 조건에 맞는
    "상담 내용 작성" 글을 찾아, 각각의 매출전표 상세 내용을 확인하고 시트
    환불금액과 대조한 결과를 반환한다. 조건에 맞는 글이 없으면 빈 리스트를
    반환한다(있어야 하는데 없는 것인지는 사람이 직접 상담관리 화면에서
    확인해야 한다)."""
    entries = list_recent_memo_entries(driver, requester_name, lookback_days)
    if not entries:
        emit_log(f'  ⚠ 최근 {lookback_days}일 이내 "{requester_name}"님이 작성한 상담 내용을 찾지 못했습니다.', level="warn")
        return []

    results = []
    for entry in entries:
        detail = fetch_receipt_detail(driver, entry.detail_url)
        comparison = compare_amounts(sheet_refund_amount, detail["fields"])
        needs_review = detail["needsReview"] or comparison["verdict"] != "일치"
        review_reason = detail["reviewReason"] or (comparison["note"] if comparison["verdict"] != "일치" else "")

        results.append(
            {
                "memoNo": entry.memo_no,
                "detailUrl": entry.detail_url,
                "author": entry.author,
                "category": entry.category,
                "registeredDate": entry.registered_date.isoformat(),
                "personalNote": detail["personalNote"],
                "receiptFields": detail["fields"],
                "matchVerdict": comparison["verdict"],
                "matchNote": comparison["note"],
                "needsReview": needs_review,
                "reviewReason": review_reason,
            }
        )

    return results
