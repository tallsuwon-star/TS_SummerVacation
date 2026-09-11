import time

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from .. import config
from ..utils.progress import emit_log

# 통합LMS(lms.talkstation.co.kr) 안에서의 이동. 상단 네비게이션의 '보카킹' 탭은
# href="#"라 실제 페이지 이동 없이 JS로 좌측 사이드바를 바꾸는 방식으로 보인다.
# nvalue="4"가 보카킹 고유 값이라 텍스트보다 이 속성으로 찾는 게 더 안전하다.
VOCAKING_TAB_SELECTOR = "a.navbar-option[nvalue='4']"

# '유료 수강생 리스트' 사이드바 링크. 실제 href를 알고 있어 바로 찾을 수 있다.
CHARGED_STUDENT_LIST_HREF = "/admin/admin/vocaking_charged_student/vocaking_charged_student_list.php"


class VocakingNavigationError(Exception):
    pass


def click_vocaking_tab(driver) -> None:
    """통합LMS 상단 네비게이션에서 '보카킹' 탭을 클릭해 보카킹 전용 사이드바로 전환한다.

    도착 직후 이미 '보카킹' 탭이 active 상태로 보이는 경우도 있었지만, 항상
    보장되는 것은 아니라서 명시적으로 클릭해 확실히 전환한다.
    """
    emit_log("'보카킹' 탭 클릭")

    try:
        tab = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, VOCAKING_TAB_SELECTOR))
        )
    except TimeoutException as exc:
        raise VocakingNavigationError("'보카킹' 탭을 찾지 못했습니다.") from exc

    driver.execute_script("arguments[0].click();", tab)
    time.sleep(config.REQUEST_DELAY_SECONDS)


def click_charged_student_list(driver) -> None:
    """좌측 사이드바의 '유료 수강생 리스트' 링크를 클릭한다."""
    emit_log("'유료 수강생 리스트' 클릭")

    try:
        link = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, f"a[href='{CHARGED_STUDENT_LIST_HREF}']"))
        )
    except TimeoutException as exc:
        raise VocakingNavigationError("'유료 수강생 리스트' 링크를 찾지 못했습니다.") from exc

    driver.execute_script("arguments[0].click();", link)
    time.sleep(config.REQUEST_DELAY_SECONDS)

    emit_log(f"현재 URL: {driver.current_url}")
    emit_log(f"페이지 제목: {driver.title}")
