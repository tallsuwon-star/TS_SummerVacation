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

# 상단 정보바(#mws-default-info)의 '통합LMS' 링크. onclick="tsb_login_check(...)"가
# #tsb_login_check 폼을 target="_tsb_311"(새 창)으로 제출하는 SSO 로그인 방식이라,
# 클릭 후 새로 열리는 창으로 전환하고 리다이렉트 체인이 끝날 때까지 기다려야 한다.
INTEGRATED_LMS_LINK_TEXT = "통합LMS"


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
            EC.presence_of_element_located(
                (By.XPATH, f"//a[contains(normalize-space(.), '{DAILY_SETTLEMENT_MENU_TEXT}')]")
            )
        )
        # 반응형 레이아웃 때문에 화면 밖(예: y좌표 음수)에 숨겨진 메뉴 사본이 먼저
        # 잡혀서 일반 click()이 "element not clickable"로 실패하는 경우가 있어,
        # 화면에 실제로 보이는지와 무관하게 onclick을 그대로 실행하는 JS 클릭을 쓴다.
        driver.execute_script("arguments[0].click();", menu)
    except TimeoutException as exc:
        raise NavigationError(f"'{DAILY_SETTLEMENT_MENU_TEXT}' 메뉴를 찾지 못했습니다.") from exc

    time.sleep(config.REQUEST_DELAY_SECONDS)

    emit_log(f"'{DAILY_SETTLEMENT_BUTTON_TEXT}' 클릭")

    try:
        button = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    f"//a[contains(normalize-space(.), '{DAILY_SETTLEMENT_BUTTON_TEXT}')] "
                    f"| //button[contains(normalize-space(.), '{DAILY_SETTLEMENT_BUTTON_TEXT}')]",
                )
            )
        )
    except TimeoutException as exc:
        raise NavigationError(f"'{DAILY_SETTLEMENT_BUTTON_TEXT}' 버튼을 찾지 못했습니다.") from exc

    windows_before = driver.window_handles
    driver.execute_script("arguments[0].click();", button)

    try:
        switch_to_new_window(driver, windows_before)
        emit_log("일일정산달력 새 탭으로 전환 완료")
    except TimeoutException:
        time.sleep(config.REQUEST_DELAY_SECONDS)
        emit_log("일일정산달력 페이지로 이동 완료 (같은 탭)")


def go_to_integrated_lms(driver) -> None:
    """상단 정보바의 '통합LMS' 링크로 이동 (SSO 새 창 로그인).

    아직 이 새 창이 최종적으로 어느 화면에 떨어지는지(보카킹 화면 바로인지,
    별도 홈 화면인지) 확인되지 않아, 이동 후 현재 URL/제목을 로그로 남긴다.
    """
    emit_log(f"'{INTEGRATED_LMS_LINK_TEXT}' 이동")

    try:
        link = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    f"//div[@id='mws-default-info']//a[contains(normalize-space(.), '{INTEGRATED_LMS_LINK_TEXT}')]",
                )
            )
        )
    except TimeoutException as exc:
        raise NavigationError(f"'{INTEGRATED_LMS_LINK_TEXT}' 링크를 찾지 못했습니다.") from exc

    windows_before = driver.window_handles
    driver.execute_script("arguments[0].click();", link)

    try:
        switch_to_new_window(driver, windows_before, timeout=15)
    except TimeoutException as exc:
        raise NavigationError(f"'{INTEGRATED_LMS_LINK_TEXT}' 새 창이 열리지 않았습니다.") from exc

    emit_log(f"'{INTEGRATED_LMS_LINK_TEXT}' 새 창으로 전환 완료, 로그인 리다이렉트 대기 중")
    # SSO 리다이렉트 체인(폼 제출 -> login_check.php -> 최종 목적지)이 끝날 시간을 준다.
    time.sleep(config.REQUEST_DELAY_SECONDS * 2)
    emit_log(f"현재 URL: {driver.current_url}")
    emit_log(f"페이지 제목: {driver.title}")
