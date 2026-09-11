import time
from datetime import date

from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from .. import config
from ..utils.progress import emit_log

SEARCH_BUTTON_XPATH = "//button[normalize-space(.)='검색']"
RESULTS_CONTAINER_ID = "jq-today-class-list"
PAGE_LINK_XPATH = f"//div[@id='{RESULTS_CONTAINER_ID}']//a[contains(@onclick, 'jqPageLIst')]"


class OverdueSearchError(Exception):
    pass


def _run_search(driver, sdate: date, edate: date) -> int:
    """'미납자기간설정'에 기간을 입력하고 검색해서 해당 기간의 미납자 총 인원 수를 반환한다.

    sdate/edate 입력창은 jQuery UI datepicker가 붙어있어(hasDatepicker) 클릭하면
    달력 팝업이 뜨는데, send_keys로 포커스를 주면 그 팝업이 열려서 이후 '검색'
    버튼 클릭을 팝업이 가로챌 위험이 있다. 그래서 포커스를 주지 않고 JS로 값만
    바로 넣는다 - '검색' 클릭 시 totalClassList()가 그 시점의 .val()을 그대로
    읽어가므로 이렇게 넣어도 동일하게 동작한다.
    """
    emit_log(f"미납자 조회: {sdate.isoformat()} ~ {edate.isoformat()}")

    try:
        sdate_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "sdate"))
        )
    except TimeoutException as exc:
        raise OverdueSearchError("'미납자기간설정' 입력창(시작일)을 찾지 못했습니다.") from exc

    edate_input = driver.find_element(By.ID, "edate")
    driver.execute_script("arguments[0].value = arguments[1];", sdate_input, sdate.isoformat())
    driver.execute_script("arguments[0].value = arguments[1];", edate_input, edate.isoformat())

    try:
        search_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, SEARCH_BUTTON_XPATH))
        )
    except TimeoutException as exc:
        raise OverdueSearchError("'검색' 버튼을 찾지 못했습니다.") from exc

    search_btn.click()
    time.sleep(config.REQUEST_DELAY_SECONDS)

    try:
        total_input = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, f"#{RESULTS_CONTAINER_ID} input[name='total_record']")
            )
        )
    except TimeoutException:
        # 결과가 0명이면 total_record 필드 자체가 안 생길 수 있다. 그 경우 로딩
        # 표시가 이미 사라졌는지(=응답은 왔는지)로 진짜 오류와 구분한다.
        results_html = driver.find_element(By.ID, RESULTS_CONTAINER_ID).get_attribute("innerHTML")
        if "loading..." in results_html:
            raise OverdueSearchError("검색 결과 로딩이 끝나지 않았습니다.")
        emit_log("  → total_record 필드 없음, 0명으로 처리")
        return 0

    count = int(total_input.get_attribute("value"))
    emit_log(f"  → {count}명")
    return count


def search_overdue_count(driver, sdate: date, edate: date) -> int:
    """기간을 검색해 해당 기간의 미납자 총 인원 수만 반환한다."""
    return _run_search(driver, sdate, edate)


def _get_total_pages(driver) -> int:
    """페이지네이션 링크(jqPageLIst) 중 가장 큰 숫자를 총 페이지 수로 추정한다.
    링크가 하나도 없으면(=결과가 1페이지뿐이거나 0명) 1을 반환한다.
    """
    max_page = 1
    for link in driver.find_elements(By.XPATH, PAGE_LINK_XPATH):
        text = link.text.strip()
        if text.isdigit():
            max_page = max(max_page, int(text))
    return max_page


def _parse_overdue_rows(driver) -> list[tuple[str, str]]:
    """현재 화면(#jq-today-class-list)의 미납자 표에서 (회원명, 담당강사명)을 뽑는다.

    합계(Total) 행처럼 이름 셀이 없는 행은 자연스럽게 건너뛴다.
    """
    rows: list[tuple[str, str]] = []
    for tr in driver.find_elements(By.CSS_SELECTOR, f"#{RESULTS_CONTAINER_ID} table tbody tr"):
        try:
            student_name = tr.find_element(
                By.CSS_SELECTOR, "td:nth-child(2) span.text-blue.strong"
            ).text.strip()
        except NoSuchElementException:
            continue

        try:
            tutor_name = tr.find_element(
                By.CSS_SELECTOR, "td:nth-child(3) span.text-orange.strong"
            ).text.strip()
        except NoSuchElementException:
            tutor_name = ""

        rows.append((student_name, tutor_name))
    return rows


def fetch_overdue_members(driver, sdate: date, edate: date) -> tuple[int, list[tuple[str, str]]]:
    """search_overdue_count와 동일하게 검색하되, 총 인원수뿐 아니라 페이지를
    전부 순회하며 (회원명, 담당강사명) 전체 목록도 함께 수집한다.

    페이지 이동은 실제 페이지네이션 링크의 onclick="jqPageLIst('N')"을 그대로
    실행한다 (이 함수는 서버가 응답에 현재 검색 조건의 sdate/edate를 다시
    박아서 내려주므로, 우리가 따로 날짜를 넘길 필요 없이 그대로 재사용 가능).
    """
    count = _run_search(driver, sdate, edate)

    members = _parse_overdue_rows(driver)
    total_pages = _get_total_pages(driver)

    for page in range(2, total_pages + 1):
        driver.execute_script("jqPageLIst(arguments[0]);", str(page))
        time.sleep(config.REQUEST_DELAY_SECONDS)
        members.extend(_parse_overdue_rows(driver))

    if len(members) != count:
        emit_log(
            f"  경고: 전체 인원수({count})와 실제로 파싱된 이름 수({len(members)})가 다릅니다.",
            level="error",
        )

    return count, members
