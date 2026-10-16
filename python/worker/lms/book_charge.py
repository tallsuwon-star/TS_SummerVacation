"""LMS '교육상품관리 > 교재상품 결제확인' 화면(book_charge_list.php)에서
'준비'(아직 미발송) 상태인 교재 구매 건의 받는사람 이름/전화번호/주소를
읽어온다.

이 페이지는 GET 방식 조회 화면이라, member_search.py와 같은 방식으로
쿼리스트링을 그대로 만들어 바로 그 결과 URL로 이동한다. 쿼리에
purchasePlace=ALL(구매처-전체), order_status=ALL(배송-전체),
classAppVocakingView=Y(보카킹통합신청교재표시)를 포함해, 사람이 화면에서
직접 그 세 조건을 설정한 것과 같은 결과를 보게 한다.

실제 화면 HTML(사용자가 직접 캡처해 전달)을 보면, 각 행의 '배송정보' 칸은
다음과 같은 구조다:

    <td>
        이름: 이소이, 전화: 010-8240-9070<br>
        ( 4714 ) 서울 성동구 행당로 99 101동 1310호
        <span class="label label-default">준비</span>
        <a ...>배송추적</a>
    </td>

상태는 <span class="label label-default">준비</span> /
<span class="label label-info">배송중</span>로 명확히 구분된다. 이름/전화/
주소를 뽑을 때는 그 span(상태)과 배송추적 버튼(<a>)을 먼저 제거한 나머지
텍스트에서 "이름: ..., 전화: ... (주소)" 패턴을 읽는다 — 그래야 상태 글자나
버튼 글자가 주소에 섞여 들어가지 않는다.

이름/전화가 비어있는 행(예: 결제금액 0원인 오래된 네이버 연동 테스트성
데이터)이나 주소가 비어있는("(  )") 행은 실제로 보낼 수 없는 주소라
needsReview=True로 표시해 사람이 직접 확인하게 한다 — 조용히 빈 값으로
엑셀에 들어가지 않도록 하기 위함이다."""

import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from .. import config
from ..utils.progress import emit_log

BOOK_CHARGE_LIST_PATH = "/edu/admin_common/shop_book/book_charge_list.php"
BOOK_CHARGE_LIST_QUERY = (
    "page_count=&find_decision=&arrange_type=reg_date&desc_type=DESC&purchasePlace=ALL"
    "&order_status=ALL&sign_sw=10&classAppVocakingView=Y&sel_text=&sel_search=name"
)

STATUS_READY = "준비"
STATUS_SHIPPING = "배송중"

# "이름: 이소이, 전화: 010-8240-9070 ( 4714 ) 서울 ..." (상태 span/배송추적
# 버튼을 제거한 뒤의 텍스트) 형태에서 이름/전화/주소를 뽑는다. 전화번호가
# 비어있는 행도 있어 phone 그룹은 0자도 허용한다.
_SHIP_INFO_RE = re.compile(
    r"이름\s*[:：]\s*(?P<name>[^,，]*)[,，]\s*전화\s*[:：]\s*(?P<phone>[^()]*)\s*(?P<address>\(.*)"
)


class BookChargeError(Exception):
    pass


def _lms_root() -> str:
    parsed = urlparse(config.LMS_BASE_URL)
    return f"{parsed.scheme}://{parsed.netloc}"


def book_charge_list_url() -> str:
    return f"{_lms_root()}{BOOK_CHARGE_LIST_PATH}?{BOOK_CHARGE_LIST_QUERY}"


def open_book_charge_list(driver) -> None:
    """교재상품 결제확인 화면으로 이동한다. 표가 안 뜨면 BookChargeError."""
    emit_log("교재상품 결제확인 화면 여는 중")
    driver.get(book_charge_list_url())

    try:
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "table")))
    except TimeoutException as exc:
        raise BookChargeError("교재상품 결제확인 화면을 불러오지 못했습니다.") from exc


def _find_ship_info_cell(row):
    """행(<tr>)에서 상태 라벨(<span class="label ...">)이 들어있는 칸(= 배송정보
    칸)을 찾는다. 없으면 None (헤더 행 등)."""
    for td in row.find_all("td"):
        if td.find("span", class_="label"):
            return td
    return None


def _row_status(ship_cell) -> str | None:
    label = ship_cell.find("span", class_="label")
    if label is None:
        return None
    text = label.get_text(strip=True)
    return text if text in (STATUS_READY, STATUS_SHIPPING) else None


def _parse_ship_info(ship_cell) -> dict:
    """배송정보 칸에서 상태 span과 배송추적 버튼을 제거한 나머지 텍스트로
    이름/전화/주소를 뽑는다. 패턴이 안 맞거나 핵심 값이 비어있으면
    needsReview=True로 표시하고 원문(rawText)을 그대로 남긴다 — 절대 추측해서
    값을 지어내지 않는다."""
    cell_copy = BeautifulSoup(str(ship_cell), "html.parser")
    for tag in cell_copy.find_all(["span", "a"]):
        tag.decompose()
    raw_text = cell_copy.get_text(" ", strip=True)

    match = _SHIP_INFO_RE.search(raw_text)
    if not match:
        return {
            "recipientName": "",
            "recipientPhone": "",
            "recipientAddress": "",
            "needsReview": True,
            "reviewReason": "배송정보(이름/전화/주소)를 찾지 못했습니다. 직접 확인해주세요.",
            "rawText": raw_text,
        }

    name = match.group("name").strip()
    phone = re.sub(r"\s+", "", match.group("phone")).strip()
    address = re.sub(r"\s+", " ", match.group("address")).strip()
    # "(  )"처럼 우편번호/주소가 비어있는 경우까지 "주소가 있다"고 보지 않는다.
    address_has_content = bool(re.search(r"\d|[가-힣]", address.strip("( )")))

    missing = []
    if not name:
        missing.append("이름")
    if not phone:
        missing.append("전화번호")
    if not address_has_content:
        missing.append("주소")

    return {
        "recipientName": name,
        "recipientPhone": phone,
        "recipientAddress": address if address_has_content else "",
        "needsReview": bool(missing),
        "reviewReason": (f"다음 정보가 비어있습니다: {', '.join(missing)}" if missing else ""),
        "rawText": raw_text,
    }


def fetch_pending_book_orders(driver) -> list[dict]:
    """현재 열려있는 교재상품 결제확인 화면에서 '준비' 상태인 행만 찾아
    받는사람 이름/전화번호/주소를 추출해 반환한다.

    행을 스캔했는데(표는 있는데) 상태 라벨을 단 하나도 식별하지 못했다면,
    실제 원인이 '준비 상태인 건이 없음'이 아니라 '화면 구조가 바뀜'일
    가능성이 높으므로 조용히 빈 목록을 반환하지 않고 BookChargeError를
    낸다."""
    soup = BeautifulSoup(driver.page_source, "html.parser")
    rows = soup.select("table tr")
    data_rows = [r for r in rows if r.find("td")]

    if not data_rows:
        raise BookChargeError("교재상품 결제확인 표에서 행을 찾지 못했습니다.")

    any_status_detected = False
    orders: list[dict] = []

    for row in data_rows:
        ship_cell = _find_ship_info_cell(row)
        if ship_cell is None:
            continue

        status = _row_status(ship_cell)
        if status is None:
            continue
        any_status_detected = True

        if status != STATUS_READY:
            continue

        ship_info = _parse_ship_info(ship_cell)
        if ship_info["needsReview"]:
            emit_log(f"  ⚠ {ship_info['reviewReason']} (원문: {ship_info['rawText'][:80]})", level="warn")

        orders.append(ship_info)

    if not any_status_detected:
        raise BookChargeError(
            "표의 어떤 행에서도 '준비'/'배송중' 상태 라벨을 찾지 못했습니다. "
            "화면 구조가 예상과 달라졌을 수 있어 개발자 확인이 필요합니다."
        )

    return orders
