import time

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from .. import config
from ..utils.progress import emit_log
from .driver import switch_to_new_window

# 실제 확인된 선택자:
# <a href="javascript:void(0)" class="mws-i-24 i-clock">시간표관리</a>
# <a href="/edu/AD_page/schedule/page1_popup.php" target="_blank">원어민 강사 시간표</a>
TIMETABLE_MENU_SELECTOR = "a.i-clock"
NATIVE_TUTOR_SCHEDULE_HREF = "/edu/AD_page/schedule/page1_popup.php"


class NavigationError(Exception):
    pass


def go_to_native_tutor_schedule(driver) -> None:
    """시간표관리 → 원어민 강사 시간표 (하위 메뉴 토글).

    '원어민 강사 시간표' 링크는 target="_blank"라 새 탭으로 열리므로,
    클릭 후 새로 열린 탭으로 전환해야 이후 조작(강사검색, SCH 클릭 등)이 된다.
    """
    emit_log("'시간표관리' 메뉴 열기")

    try:
        timetable_menu = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, TIMETABLE_MENU_SELECTOR))
        )
        timetable_menu.click()
    except TimeoutException as exc:
        raise NavigationError("'시간표관리' 메뉴를 찾지 못했습니다.") from exc

    time.sleep(config.REQUEST_DELAY_SECONDS)

    emit_log("'원어민 강사 시간표' 클릭")

    try:
        native_tutor_submenu = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, f"a[href='{NATIVE_TUTOR_SCHEDULE_HREF}']"))
        )
    except TimeoutException as exc:
        raise NavigationError("'원어민 강사 시간표' 메뉴를 찾지 못했습니다.") from exc

    windows_before = driver.window_handles
    native_tutor_submenu.click()

    try:
        switch_to_new_window(driver, windows_before)
    except TimeoutException as exc:
        raise NavigationError("'원어민 강사 시간표' 새 탭이 열리지 않았습니다.") from exc

    emit_log("원어민 강사 시간표 새 탭으로 전환 완료")

    time.sleep(config.REQUEST_DELAY_SECONDS)
