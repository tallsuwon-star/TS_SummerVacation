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

# '수강료관리' LNB 메뉴/'일일정산달력' 버튼의 정확한 태그/클래스(아이콘 클래스 등)를
# 아직 확인하지 못해, 위 시간표관리처럼 클래스 기반이 아니라 화면에 보이는 텍스트
# 기준으로 찾는다. 실행해보고 못 찾으면 실제 HTML을 확인해서 선택자를 교체해야 한다.
DAILY_SETTLEMENT_MENU_TEXT = "수강료관리"
DAILY_SETTLEMENT_BUTTON_TEXT = "일일정산달력"


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


def go_to_daily_settlement_calendar(driver) -> None:
    """수강료관리 → 일일정산달력.

    '일일정산달력'이 새 탭으로 열리는지 같은 탭에서 이동하는지 아직 확인되지
    않아, 새 탭 전환을 먼저 시도해보고 새 탭이 안 열리면 같은 탭에서 페이지가
    바뀐 것으로 보고 계속 진행한다 (오류로 처리하지 않음).
    """
    emit_log(f"'{DAILY_SETTLEMENT_MENU_TEXT}' 메뉴 열기")

    try:
        menu = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable(
                (By.XPATH, f"//a[contains(normalize-space(.), '{DAILY_SETTLEMENT_MENU_TEXT}')]")
            )
        )
        menu.click()
    except TimeoutException as exc:
        raise NavigationError(f"'{DAILY_SETTLEMENT_MENU_TEXT}' 메뉴를 찾지 못했습니다.") from exc

    time.sleep(config.REQUEST_DELAY_SECONDS)

    emit_log(f"'{DAILY_SETTLEMENT_BUTTON_TEXT}' 클릭")

    try:
        button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable(
                (By.XPATH, f"//*[contains(normalize-space(.), '{DAILY_SETTLEMENT_BUTTON_TEXT}')]")
            )
        )
    except TimeoutException as exc:
        raise NavigationError(f"'{DAILY_SETTLEMENT_BUTTON_TEXT}' 버튼을 찾지 못했습니다.") from exc

    windows_before = driver.window_handles
    button.click()

    try:
        switch_to_new_window(driver, windows_before)
        emit_log("일일정산달력 새 탭으로 전환 완료")
    except TimeoutException:
        time.sleep(config.REQUEST_DELAY_SECONDS)
        emit_log("일일정산달력 페이지로 이동 완료 (같은 탭)")
