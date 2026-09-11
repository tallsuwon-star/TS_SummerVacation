import time
from datetime import date

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from .. import config
from ..utils.progress import emit_log

SEARCH_BUTTON_XPATH = "//button[normalize-space(.)='검색']"
RESULTS_CONTAINER_ID = "jq-today-class-list"


class OverdueSearchError(Exception):
    pass


def search_overdue_count(driver, sdate: date, edate: date) -> int:
    """'미납자기간설정'에 기간을 입력하고 검색해서 해당 기간의 미납자 총 인원 수를 반환한다.

    sdate/edate 입력창은 jQuery UI datepicker가 붙어있어(hasDatepicker) 클릭하면
    달력 팝업이 뜨는데, send_keys로 포커스를 주면 그 팝업이 열려서 이후 '검색'
    버튼 클릭을 팝업이 가로챌 위험이 있다. 그래서 포커스를 주지 않고 JS로 값만
    바로 넣는다 - '검색' 클릭 시 totalClassList()가 그 시점의 .val()을 그대로
    읽어가므로 이렇게 넣어도 동일하게 동작한다.
    """
    emit_log(f"미납자 조회: {sdate.isoformat()} ~ {edate.isoformat()}")

    sdate_input = driver.find_element(By.ID, "sdate")
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
        emit_log(f"  → total_record 필드 없음, 0명으로 처리")
        return 0

    count = int(total_input.get_attribute("value"))
    emit_log(f"  → {count}명")
    return count
