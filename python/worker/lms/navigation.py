import time

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from .. import config
from ..utils.progress import emit_log

# 사이드바 메뉴 텍스트로 항목을 찾는다 (실제 id/class 미확인 상태, 화면에 보이는 텍스트 기준).
TIMETABLE_MENU_TEXT = "시간표관리"
NATIVE_TUTOR_SCHEDULE_TEXT = "원어민 강사 시간표"


class NavigationError(Exception):
    pass


def go_to_native_tutor_schedule(driver) -> None:
    """시간표관리 → 원어민 강사 시간표 (하위 메뉴 토글)."""
    emit_log(f"'{TIMETABLE_MENU_TEXT}' 메뉴 열기")

    try:
        timetable_menu = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable(
                (By.XPATH, f"//*[normalize-space(text())='{TIMETABLE_MENU_TEXT}']")
            )
        )
        timetable_menu.click()
    except TimeoutException as exc:
        raise NavigationError(f"'{TIMETABLE_MENU_TEXT}' 메뉴를 찾지 못했습니다.") from exc

    time.sleep(config.REQUEST_DELAY_SECONDS)

    emit_log(f"'{NATIVE_TUTOR_SCHEDULE_TEXT}' 클릭")

    try:
        native_tutor_submenu = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable(
                (By.XPATH, f"//*[normalize-space(text())='{NATIVE_TUTOR_SCHEDULE_TEXT}']")
            )
        )
        native_tutor_submenu.click()
    except TimeoutException as exc:
        raise NavigationError(f"'{NATIVE_TUTOR_SCHEDULE_TEXT}' 메뉴를 찾지 못했습니다.") from exc

    time.sleep(config.REQUEST_DELAY_SECONDS)
