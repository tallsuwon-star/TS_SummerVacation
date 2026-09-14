"""스마트스토어 센터 홈 -> 판매관리 > 발주(주문)확인/발송관리 이동.

두 가지 방법을 순서대로 시도한다:
1. 빠른 경로: 세션이 이미 살아있다면 딥링크 해시 URL로 바로 이동을 시도한다.
2. 폴백: 좌측 메뉴를 실제로 클릭한다 (판매관리 -> 발주(주문)확인/발송관리),
   iframe 안까지 탐색한다.

두 방법 모두 마지막에 실제로 URL에 "sale/delivery"가 포함됐는지 확인하고,
가정하지 않는다.

아직은 그 페이지에 도착하는 것까지만 한다 — 실제 주문 목록을 읽거나
엑셀을 다운받는 부분은 다음 단계(TODO).
"""

from __future__ import annotations

import time

from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from ..utils.progress import emit_log
from ._debug import save_debug_screenshot
from .auth import SMARTSTORE_HOME_URL

ORDER_DELIVERY_URL = "https://sell.smartstore.naver.com/#/naverpay/sale/delivery"
DELIVERY_URL_MARKER = "sale/delivery"

# "판매관리"는 좌측 최상위 메뉴 라벨(판매관리N pay, 정산관리N pay, 문의/리뷰관리,
# 스토어관리 ...) 중 유일해서 부분 일치로 충분하다.
SALES_MENU_SELECTORS = (
    (By.XPATH, "//*[self::a or self::button or self::li][contains(normalize-space(.), '판매관리')]"),
)
DELIVERY_LINK_SELECTORS = (
    (By.XPATH, "//a[contains(normalize-space(.), '발주(주문)확인/발송관리')]"),
    (By.XPATH, "//*[contains(normalize-space(.), '발주(주문)확인/발송관리')]"),
)

NOTICE_TITLE_XPATH = "//*[contains(normalize-space(.), '스마트스토어센터 공지')]"
NOTICE_CLOSE_SELECTORS = (
    (By.XPATH, "//*[@aria-label='닫기']"),
    (By.CSS_SELECTOR, "[class*='close' i]"),
    (By.XPATH, "//button[contains(@class, 'close') or contains(@class, 'Close')]"),
)


def go_to_delivery_page(driver: WebDriver) -> bool:
    """스마트스토어 홈에서 발주(주문)확인/발송관리 페이지로 이동한다.
    도착 여부(bool)를 반환한다."""
    if SMARTSTORE_HOME_URL not in driver.current_url:
        emit_log(f"스마트스토어 센터로 이동합니다: {SMARTSTORE_HOME_URL}")
        driver.get(SMARTSTORE_HOME_URL)
    _dismiss_notice_popup(driver)

    if not _try_direct_navigation(driver):
        emit_log("바로 이동이 되지 않아 좌측 메뉴 클릭 방식으로 다시 시도합니다.", level="warn")
        _navigate_via_menu(driver)

    current_url = _safe(lambda: driver.current_url, "(알 수 없음)")
    reached = DELIVERY_URL_MARKER in current_url
    if reached:
        emit_log(f"발주(주문)확인/발송관리 페이지에 진입했습니다: {current_url}")
    else:
        emit_log(f"예상한 페이지에 도달하지 못한 것으로 보입니다. 현재 화면: {current_url}", level="warn")
        save_debug_screenshot(driver, "delivery_nav_check")
    return reached


def _is_window_closed_error(exc: Exception) -> bool:
    text = str(exc)
    return any(marker in text for marker in ("no such window", "target window already closed", "web view not found"))


def _safe(fn, default=None):
    try:
        return fn()
    except Exception:  # noqa: BLE001
        return default


def _dismiss_notice_popup(driver: WebDriver) -> None:
    """스마트스토어 홈에 "스마트스토어센터 공지" 모달이 대시보드 위를 덮고
    뜰 때가 있는데, 그러면 뒤에 있는 좌측 메뉴 클릭이 막힌다."""
    try:
        if not driver.find_elements(By.XPATH, NOTICE_TITLE_XPATH):
            return
        emit_log("'스마트스토어센터 공지' 팝업이 감지되어 닫습니다.")
        try:
            ActionChains(driver).send_keys(Keys.ESCAPE).perform()
            time.sleep(0.3)
        except Exception:  # noqa: BLE001
            pass
        if driver.find_elements(By.XPATH, NOTICE_TITLE_XPATH):
            for by, selector in NOTICE_CLOSE_SELECTORS:
                try:
                    el = driver.find_element(by, selector)
                    if el.is_displayed():
                        el.click()
                        time.sleep(0.3)
                        break
                except Exception:  # noqa: BLE001
                    continue
    except Exception:  # noqa: BLE001
        pass


def _click_first_match(driver: WebDriver, selectors, wait_seconds: int) -> bool:
    for by, selector in selectors:
        try:
            el = WebDriverWait(driver, wait_seconds).until(EC.element_to_be_clickable((by, selector)))
            el.click()
            return True
        except Exception:  # noqa: BLE001
            continue
    return False


def _click_first_match_anywhere(driver: WebDriver, selectors, label: str, wait_seconds: int = 15) -> bool:
    """메인 문서에서 먼저 시도하고, 없으면 iframe 안까지 찾아본다."""
    if _click_first_match(driver, selectors, wait_seconds):
        return True

    try:
        frames = driver.find_elements(By.TAG_NAME, "iframe")
    except Exception as exc:  # noqa: BLE001
        if _is_window_closed_error(exc):
            raise RuntimeError(
                "자동화 중이던 크롬 창이 닫혀서 작업을 계속할 수 없습니다. "
                "실행 중에는 크롬 창을 직접 닫지 말고 완료/실패 로그가 뜰 때까지 기다려 주세요."
            ) from exc
        frames = []

    for frame in frames:
        try:
            driver.switch_to.frame(frame)
            if _click_first_match(driver, selectors, wait_seconds=3):
                return True
        except Exception:  # noqa: BLE001
            continue
        finally:
            driver.switch_to.default_content()

    present_count = 0
    for by, selector in selectors:
        try:
            present_count += len(driver.find_elements(by, selector))
        except Exception:  # noqa: BLE001
            pass
    emit_log(
        f"'{label}' 메뉴를 클릭하지 못했습니다 (iframe {len(frames)}개 포함 탐색, "
        f"DOM에 존재하는(클릭 가능 여부 무관) 후보 {present_count}개).",
        level="warn",
    )
    return False


def _try_direct_navigation(driver: WebDriver) -> bool:
    emit_log(f"이미 로그인된 세션이므로 발주(주문)확인/발송관리로 바로 이동을 시도합니다: {ORDER_DELIVERY_URL}")
    driver.get(ORDER_DELIVERY_URL)
    time.sleep(2)
    _dismiss_notice_popup(driver)
    return DELIVERY_URL_MARKER in driver.current_url


def _navigate_via_menu(driver: WebDriver) -> None:
    driver.get(SMARTSTORE_HOME_URL)
    _dismiss_notice_popup(driver)

    emit_log("좌측 메뉴에서 '판매관리'를 클릭합니다.")
    if not _click_first_match_anywhere(driver, SALES_MENU_SELECTORS, "판매관리"):
        emit_log("하위 메뉴가 이미 펼쳐져 있을 수 있어 계속 진행합니다.", level="warn")

    emit_log("좌측 메뉴에서 '발주(주문)확인/발송관리'를 클릭합니다.")
    if _click_first_match_anywhere(driver, DELIVERY_LINK_SELECTORS, "발주(주문)확인/발송관리"):
        time.sleep(1.5)  # SPA 라우트가 렌더링될 시간을 준다
