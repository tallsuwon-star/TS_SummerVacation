"""카드취소 대상 회원의 상담관리 화면에서, 구글 시트의 "요청자"와 이름이
같고 최근(기본 7일 이내) 등록된 "상담 내용 작성" 글을 찾아, 그 글의 상세
페이지에 있는 신용카드 매출전표(결제 시간/구매자명/상품정보 등)를 읽어온다.

이 모듈은 조회만 한다 — student.memo_note.php의 삭제/수정 링크는 어디서도
클릭하지 않고, 오직 읽기 전용 상세보기 링크(view_mode=detail)로만 이동한다.

정확도가 매우 중요한 기능이라 다음 원칙을 지킨다:
- 작성자 이름은 정확히 일치해야만 후보로 본다 (부분일치 금지).
- 매출전표의 핵심 항목(거래일자/구매자/상품명/승인번호)을 전부 읽어낸
  경우에만 needsReview=False로 표시하고, 하나라도 못 찾으면 반드시
  needsReview=True로 표시해 사람이 URL을 직접 열어 확인하게 한다.
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
_RECEIPT_FIELD_RE = re.compile(
    rf"({_LABEL_ALTERNATION})\s*[:：]\s*(.*?)(?=(?:{_LABEL_ALTERNATION})\s*[:：]|$)"
)

REQUIRED_RECEIPT_FIELDS = ["거래일자", "구매자", "상품명", "승인번호"]


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


def _extract_receipt_fields(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)
    fields: dict[str, str] = {}
    for match in _RECEIPT_FIELD_RE.finditer(text):
        label, value = match.group(1), match.group(2).strip()
        if label not in fields:  # 같은 라벨이 여러 번 매칭되면 첫 값만 쓴다
            fields[label] = value
    return fields


def _extract_personal_note(html: str) -> str:
    """매출전표 표(<table>)를 전부 제거하고 남는 텍스트 = 담당자가 직접
    적은 메모(예: "전체 카드 취소", "필리핀 > 영미권 수강 변경")."""
    soup = BeautifulSoup(html, "html.parser")
    for table in soup.find_all("table"):
        table.decompose()
    return soup.get_text(" ", strip=True)


def _fetch_receipt_from_current_context(driver) -> dict | None:
    html = driver.page_source
    fields = _extract_receipt_fields(html)
    if not fields:
        return None
    return {"fields": fields, "personalNote": _extract_personal_note(html)}


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


def check_card_cancel_receipts(
    driver, requester_name: str, lookback_days: int = DEFAULT_LOOKBACK_DAYS
) -> list[dict]:
    """현재 열려있는 상담관리 화면에서 요청자 이름 + 최근 등록 조건에 맞는
    "상담 내용 작성" 글을 찾아, 각각의 매출전표 상세 내용을 확인해 반환한다.
    조건에 맞는 글이 없으면 빈 리스트를 반환한다(있어야 하는데 없는 것인지는
    사람이 직접 상담관리 화면에서 확인해야 한다)."""
    entries = list_recent_memo_entries(driver, requester_name, lookback_days)
    if not entries:
        emit_log(f'  ⚠ 최근 {lookback_days}일 이내 "{requester_name}"님이 작성한 상담 내용을 찾지 못했습니다.', level="warn")
        return []

    results = []
    for entry in entries:
        detail = fetch_receipt_detail(driver, entry.detail_url)
        results.append(
            {
                "memoNo": entry.memo_no,
                "detailUrl": entry.detail_url,
                "author": entry.author,
                "category": entry.category,
                "registeredDate": entry.registered_date.isoformat(),
                "personalNote": detail["personalNote"],
                "receiptFields": detail["fields"],
                "needsReview": detail["needsReview"],
                "reviewReason": detail["reviewReason"],
            }
        )

    return results
