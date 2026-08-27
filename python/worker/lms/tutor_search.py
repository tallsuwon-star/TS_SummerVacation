import time

from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from .. import config
from ..utils.progress import emit_log

# 필터 바의 '강사검색' 라벨 바로 다음에 오는 입력창을 찾는다 (실제 id/class 미확인 상태).
SEARCH_LABEL_TEXT = "강사검색"
FIND_BUTTON_TEXT = "Find"


class TutorNotFoundError(Exception):
    pass


class SchButtonNotFoundError(Exception):
    pass


def search_tutor(driver, tutor_name: str) -> None:
    """강사검색 입력창에 강사 이름 입력 후 검색."""
    emit_log(f"강사 검색: {tutor_name}")

    # 로그인 폼과 마찬가지로 '강사검색'이 라벨 텍스트가 아니라 입력창의 placeholder
    # 속성일 가능성이 높아 그것부터 시도하고, 안 되면 라벨 텍스트 뒤의 input으로 대체 시도.
    try:
        search_input = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, f"input[placeholder='{SEARCH_LABEL_TEXT}']"))
        )
    except TimeoutException:
        try:
            search_input = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located(
                    (By.XPATH, f"//*[contains(normalize-space(text()), '{SEARCH_LABEL_TEXT}')]/following::input[1]")
                )
            )
        except TimeoutException as exc:
            raise TutorNotFoundError(f"'{SEARCH_LABEL_TEXT}' 입력창을 찾지 못했습니다.") from exc

    search_input.clear()
    search_input.send_keys(tutor_name)

    try:
        find_btn = driver.find_element(
            By.XPATH, f"//button[normalize-space(text())='{FIND_BUTTON_TEXT}'] | //input[@value='{FIND_BUTTON_TEXT}']"
        )
        find_btn.click()
    except NoSuchElementException:
        # 'Find' 버튼 선택자를 못 찾으면 입력창에서 Enter로 대체 시도
        search_input.send_keys(Keys.ENTER)

    time.sleep(config.REQUEST_DELAY_SECONDS)


def click_sch_button(driver, tutor_name: str) -> None:
    """검색된 강사의 SCH 버튼 클릭.

    시간표 화면은 강사 카드 배경색이 흰색/초록색 등으로 번갈아 나오는데, 색상과 무관하게
    강사 이름과 '같은 카드(컨테이너)' 안에 있는 SCH 버튼만 클릭해야 다른 강사의 SCH를
    잘못 누르지 않는다. 그래서 이름 요소의 가장 가까운 조상 중 SCH 텍스트를 포함하는
    조상을 찾아 그 안에서만 SCH를 찾는다.
    """
    emit_log(f"{tutor_name} SCH 버튼 클릭")

    try:
        name_el = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, f"//*[normalize-space(text())='{tutor_name}']"))
        )
    except TimeoutException as exc:
        raise TutorNotFoundError(f"검색 결과에서 '{tutor_name}'을(를) 찾지 못했습니다.") from exc

    try:
        sch_btn = name_el.find_element(
            By.XPATH,
            "./ancestor::*[.//*[normalize-space(text())='SCH']][1]//*[normalize-space(text())='SCH']",
        )
    except NoSuchElementException as exc:
        raise SchButtonNotFoundError(f"{tutor_name}의 SCH 버튼을 찾지 못했습니다.") from exc

    sch_btn.click()
    time.sleep(config.REQUEST_DELAY_SECONDS)
