import re
import time as time_module
from dataclasses import dataclass
from datetime import date

from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

from .. import config
from ..utils.progress import emit_log
from .schedule import AM_WINDOW_END_MINUTES, AM_WINDOW_START_MINUTES

PAGE_COUNT_SELECT_SELECTOR = "select[name='page_count']"

VALID_AUTHORS = {"이성규", "양수아"}

# "구분" 라벨이 이 문자열로 "끝나야" 보강대기 상태로 취급한다.
# 예) "정규 - 보강대기신청"        -> 대상 (보강권을 새로 지급한 건)
#     "정규 - 보강대기신청 - 확정" -> 제외 (이미 다른 수업에 보강권을 사용해서 확정된 건이라
#                                      더 이상 "...보강대기신청"으로 끝나지 않음)
TARGET_CATEGORY_SUFFIX = "보강대기신청"

_ROW_XPATH = "//td[@class='list-type-left']/ancestor::tr[1]"
_CATEGORY_AUTHOR_RE = re.compile(r"\[(?P<category>.+?)\]\s*-\s*(?P<author>.+)")
_LEADING_DATE_RE = re.compile(r"(\d{4})\.(\d{2})\.(\d{2})")
_LEADING_DATETIME_RE = re.compile(r"(\d{4})\.(\d{2})\.(\d{2})\s+(\d{1,2}):(\d{2})")


class ConsultationLoadError(Exception):
    pass


@dataclass
class ConsultationRecord:
    category: str
    author: str
    registered_date: date
    detail: str
    class_date: date | None
    class_start_minutes: int | None  # 상세 텍스트에 적힌 실제 수업 시작 시각 (자정 기준 분)


def collect_consultation_records(driver) -> list[ConsultationRecord]:
    """상담관리 화면의 '상담 내용 작성' 목록을 파싱한다.

    실제 확인된 행 구조 (한 행에 class="list-type"인 td가 NO/등록일/관리, 총 3개나 있으므로
    반드시 list-type-left 바로 다음 형제 td를 등록일로 지정해야 한다. 그냥 'td.list-type' 첫
    매치를 쓰면 NO 번호를 등록일로 잘못 읽어 날짜 파싱이 전부 실패하는 버그가 있었다):
      <td class="list-type">{NO}</td>
      <td class="list-type-left">
        <p>[<span style="color:...">{구분}</span>] - {작성자}</p>
        <a ... original-title="{상세 텍스트}">{상세 텍스트 요약}</a>
      </td>
      <td class="list-type">{등록일 예: "2026.08.21"}</td>
      <td class="list-type">{관리 아이콘}</td>

    상세 텍스트 맨 앞의 날짜/시각이 실제 수업일자/수업시각이다.
      예) "2026.08.21 12:30 [Cassandra] 보강대기처리" -> 수업 2026-08-21 12:30 (보강권 지급)
          "2026.08.21 12:30 [Cassandra]을 2026.08.21 16:00 [Alfred]으로 보강권사용 수업 등록함"
          -> 보강권을 실제로 사용해 수업을 잡은 기록. 구분에 "- 확정"이 붙어서
             TARGET_CATEGORY_SUFFIX 필터에서 자동으로 제외된다.
    """
    emit_log("상담 기록 로딩")

    _ensure_max_page_size(driver)

    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "td.list-type-left"))
        )
    except TimeoutException as exc:
        raise ConsultationLoadError("상담 내용 목록을 찾지 못했습니다.") from exc

    rows = driver.find_elements(By.XPATH, _ROW_XPATH)
    records: list[ConsultationRecord] = []

    for row in rows:
        try:
            left_cell = row.find_element(By.CSS_SELECTOR, "td.list-type-left")
            # list-type-left "바로 다음" 형제 td.list-type == 등록일. (NO 번호 td는 그 앞에 있다)
            date_cell = left_cell.find_element(By.XPATH, "following-sibling::td[@class='list-type'][1]")
        except NoSuchElementException:
            continue

        try:
            p_text = left_cell.find_element(By.TAG_NAME, "p").text.strip()
        except NoSuchElementException:
            continue

        match = _CATEGORY_AUTHOR_RE.match(p_text)
        if not match:
            continue
        category = match.group("category").strip()
        author = match.group("author").strip()

        detail = ""
        try:
            detail_el = left_cell.find_element(By.TAG_NAME, "a")
            detail = (
                detail_el.get_attribute("title")
                or detail_el.get_attribute("original-title")
                or detail_el.text
                or ""
            ).strip()
        except NoSuchElementException:
            pass

        registered_date = _parse_date(date_cell.text)
        if registered_date is None:
            continue

        records.append(
            ConsultationRecord(
                category=category,
                author=author,
                registered_date=registered_date,
                detail=detail,
                class_date=_parse_date(detail),
                class_start_minutes=_parse_start_minutes(detail),
            )
        )

    emit_log(f"상담 기록 {len(records)}건 파싱 완료")
    return records


def count_makeup_credits(
    records: list[ConsultationRecord],
    consultation_after: date,
    class_after: date,
) -> int:
    """작성자가 이성규/양수아이고, 등록일이 consultation_after 이후이며, 수업일자가 class_after
    이후이고, 수업 시작 시각이 10:00~12:30 사이이며, 구분이 '...보강대기신청'으로 끝나는
    (확정 제외) 기록만 카운트한다.
    """
    count = 0
    for record in records:
        if record.author not in VALID_AUTHORS:
            continue
        if not record.category.endswith(TARGET_CATEGORY_SUFFIX):
            continue
        if record.registered_date < consultation_after:
            continue
        if record.class_date is None or record.class_date < class_after:
            continue
        if record.class_start_minutes is None:
            continue
        if not (AM_WINDOW_START_MINUTES <= record.class_start_minutes <= AM_WINDOW_END_MINUTES):
            continue
        count += 1
    return count


def _ensure_max_page_size(driver) -> None:
    """목록이 30개씩 페이지네이션되어 있어 최근 등록분이 뒤 페이지로 밀릴 수 있으므로,
    'Show' 드롭다운을 각 목록에서 고를 수 있는 가장 큰 값으로 올려서 한 페이지에서 최대한
    많이 확인한다. (완전한 페이지네이션 순회는 아니지만, 대상 기간이 보통 최근 1~2주 내인
    점을 감안하면 대부분의 경우 이걸로 충분하다.)

    이 페이지에는 '정규 수강상담 리스트'와 '상담 내용 작성' 두 목록이 각자 자신의
    page_count 드롭다운을 갖고 있을 수 있어 select[name='page_count']가 여러 개 잡힐 수
    있다. 옵션 값을 120으로 하드코딩하면 그 값이 없는 드롭다운에서 예외가 나서 작업
    전체가 죽으므로, 각 드롭다운에서 실제로 제공하는 옵션 중 가장 큰 값을 골라 선택하고,
    이건 어디까지나 부가 기능이라 하나라도 실패해도(드롭다운이 없거나, 클릭 후 페이지가
    새로고침되어 다음 드롭다운 참조가 stale해지는 경우 등) 작업 자체는 계속 진행한다.
    """
    try:
        select_elements = driver.find_elements(By.CSS_SELECTOR, PAGE_COUNT_SELECT_SELECTOR)
    except Exception:  # noqa: BLE001 - 부가 기능, 실패해도 작업을 막으면 안 됨
        return

    for select_el in select_elements:
        try:
            select = Select(select_el)
            options = select.options
            if not options:
                continue
            largest_value = options[-1].get_attribute("value")
            if select.first_selected_option.get_attribute("value") != largest_value:
                select.select_by_value(largest_value)
                time_module.sleep(config.REQUEST_DELAY_SECONDS)
        except Exception as exc:  # noqa: BLE001 - 부가 기능, 실패해도 작업 자체는 계속 진행
            emit_log(f"상담 목록 페이지 크기 확장 중 일부 실패 (무시하고 계속 진행): {exc}", level="error")


def _parse_date(text: str) -> date | None:
    """텍스트 어디에서든 첫 번째 'YYYY.MM.DD' 패턴을 찾아 날짜로 변환한다."""
    match = _LEADING_DATE_RE.search(text)
    if not match:
        return None
    year, month, day = (int(g) for g in match.groups())
    return date(year, month, day)


def _parse_start_minutes(detail: str) -> int | None:
    """상세 텍스트 맨 앞의 'YYYY.MM.DD HH:MM'에서 시각을 분 단위로 변환한다.
    예: "2026.08.21 12:30 [Cassandra] 보강대기처리" -> 750 (12*60+30)
    """
    match = _LEADING_DATETIME_RE.search(detail)
    if not match:
        return None
    hour, minute = int(match.group(4)), int(match.group(5))
    return hour * 60 + minute
