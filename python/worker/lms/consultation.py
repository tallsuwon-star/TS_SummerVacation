import re
from dataclasses import dataclass
from datetime import date

from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from ..utils.progress import emit_log

VALID_AUTHORS = {"이성규", "양수아"}

# "구분" 라벨이 이 문자열로 "끝나야" 보강대기 상태로 취급한다.
# 예) "정규 - 보강대기신청"        -> 대상 (보강권을 새로 지급한 건)
#     "정규 - 보강대기신청 - 확정" -> 제외 (이미 다른 수업에 보강권을 사용해서 확정된 건이라
#                                      더 이상 "...보강대기신청"으로 끝나지 않음)
TARGET_CATEGORY_SUFFIX = "보강대기신청"

_ROW_XPATH = "//td[@class='list-type-left']/ancestor::tr[1]"
_CATEGORY_AUTHOR_RE = re.compile(r"\[(?P<category>.+?)\]\s*-\s*(?P<author>.+)")
_LEADING_DATE_RE = re.compile(r"(\d{4})\.(\d{2})\.(\d{2})")


class ConsultationLoadError(Exception):
    pass


@dataclass
class ConsultationRecord:
    category: str
    author: str
    registered_date: date
    detail: str
    class_date: date | None


def collect_consultation_records(driver) -> list[ConsultationRecord]:
    """상담관리 화면의 '상담 내용 작성' 목록을 파싱한다.

    실제 확인된 행 구조:
      <td class="list-type-left">
        <p>[<span style="color:...">{구분}</span>] - {작성자}</p>
        <a ... title="{상세 텍스트}">{상세 텍스트 요약}</a>
      </td>
      <td class="list-type">{등록일 예: "2026.08.21"}</td>

    상세 텍스트 맨 앞의 날짜가 실제 수업일자다.
      예) "2026.08.21 12:30 [Cassandra] 보강대기처리" -> 수업일자 2026-08-21 (보강권 지급)
          "2026.08.21 12:30 [Cassandra]을 2026.08.21 16:00 [Alfred]으로 보강권사용 수업 등록함"
          -> 보강권을 실제로 사용해 수업을 잡은 기록. 구분에 "- 확정"이 붙어서
             TARGET_CATEGORY_SUFFIX 필터에서 자동으로 제외된다.
    """
    emit_log("상담 기록 로딩")

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
            date_cell = row.find_element(By.CSS_SELECTOR, "td.list-type")
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
            )
        )

    emit_log(f"상담 기록 {len(records)}건 파싱 완료")
    return records


def count_makeup_credits(
    records: list[ConsultationRecord],
    consultation_after: date,
    class_after: date,
) -> int:
    """작성자가 이성규/양수아이고, 등록일이 consultation_after 이후이며,
    수업일자가 class_after 이후이고, 구분이 '...보강대기신청'으로 끝나는(확정 제외) 기록만 카운트한다.
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
        count += 1
    return count


def _parse_date(text: str) -> date | None:
    """텍스트 어디에서든 첫 번째 'YYYY.MM.DD' 패턴을 찾아 날짜로 변환한다."""
    match = _LEADING_DATE_RE.search(text)
    if not match:
        return None
    year, month, day = (int(g) for g in match.groups())
    return date(year, month, day)
