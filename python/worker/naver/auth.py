"""네이버 스마트스토어 로그인.

실제 확인된 흐름: 스마트스토어 홈(SMARTSTORE_HOME_URL)에 로그아웃 상태로
들어가면 "로그인하기" 진입점이 보이고, 이게 네이버 커머스 ID 자체 로그인
페이지(accounts.commerce.naver.com)로 이동하며, 거기서 다시 "네이버 아이디로
로그인"을 눌러야만 익숙한 nid.naver.com 아이디/비밀번호 폼이 뜬다.
nid.naver.com에 곧바로 로그인해도 naver.com 세션은 생기지만 스마트스토어
센터 세션은 생기지 않으므로, 반드시 이 3단계를 그대로 따라가야 한다.

- 이미 스마트스토어 로그인 세션이 남아 있으면 로그인 자체를 건너뛴다.
- .env의 NAVER_ID/NAVER_PASSWORD를 클립보드 붙여넣기 방식으로 입력한다
  (자동입력 패턴으로 인한 캡챠/재인증 유발을 줄이기 위함).
- "네이버 아이디로 로그인" 버튼은 팝업 창을 띄우는 방식이라, 클릭할 때마다
  새 창이 열렸는지 확인해서 그 창으로 전환해야 한다.
- 네이버가 이미지 캡챠를 요구하면 화면을 지켜보는 사람이 직접 풀어야 한다
  (자동으로 풀거나 우회하지 않는다). 캡챠 이후 "다시 로그인해 주세요" 폼이
  다시 뜨면, 이미 갖고 있는 아이디/비밀번호로 자동으로 재입력해 최대
  2번까지 재시도한다.
"""

from __future__ import annotations

import time

import pyperclip
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from .. import config
from ..control import ControlState
from ..utils.progress import emit_log
from ._debug import save_debug_screenshot

SMARTSTORE_HOME_URL = "https://sell.smartstore.naver.com/home"
COMMERCE_LOGIN_HOST = "accounts.commerce.naver.com"
NID_LOGIN_HOST = "nid.naver.com"
CAPTCHA_WAIT_TIMEOUT_SEC = 300
HEARTBEAT_INTERVAL_SEC = 15
MAX_PLAIN_FORM_AUTO_RETRIES = 2

LOGGED_OUT_MARKER_XPATH = "//a[contains(normalize-space(.), '로그인하기')]"
LOGIN_ENTRY_SELECTORS = (
    (By.XPATH, LOGGED_OUT_MARKER_XPATH),
    (By.XPATH, "//button[contains(normalize-space(.), '로그인하기')]"),
    (By.XPATH, "//*[contains(normalize-space(.), '로그인하기')]"),
)
NAVER_ID_LOGIN_SELECTORS = (
    (By.XPATH, "//a[contains(normalize-space(.), '네이버 아이디로 로그인')]"),
    (By.XPATH, "//button[contains(normalize-space(.), '네이버 아이디로 로그인')]"),
    (By.XPATH, "//*[contains(normalize-space(.), '네이버 아이디로 로그인')]"),
)

# nid.naver.com의 "네이버 커머스 ID" OAuth 로그인 템플릿은 화면 너비에 따라
# row/column 두 레이아웃이 같이 존재하고(하나는 CSS로 숨김), 각각 패스키/로그인
# 버튼이 있다. 버튼 자체의 텍스트가 아니라 안의 <span>에 있어서 text() 매치는
# 안 통하므로 정확한 id를 우선으로, normalize-space(.) 매치를 폴백으로 둔다.
LOGIN_BUTTON_SELECTORS = (
    (By.ID, "loginBtn_row"),
    (By.ID, "loginBtn_column"),
    (By.ID, "log.login"),
    (By.CSS_SELECTOR, "button.btn_login"),
    (By.CSS_SELECTOR, "#frmNIDLogin button[type='submit']"),
    (
        By.XPATH,
        "//*[self::button or self::a]"
        "[contains(normalize-space(.), '로그인') and not(contains(normalize-space(.), '패스키'))]",
    ),
)

# 실제 보이는 캡챠 이미지/입력창 — 자동입력 감지로 다시 뜨는 빈 로그인 폼과는
# 구별해야 한다 (아래 _on_plain_login_form 참고).
CAPTCHA_ELEMENT_SELECTORS = (
    (By.CSS_SELECTOR, "img[id*='captcha' i]"),
    (By.CSS_SELECTOR, "input[id*='captcha' i]"),
    (By.CSS_SELECTOR, "canvas[id*='captcha' i]"),
)


class LoginFailedError(Exception):
    pass


def _paste_into(driver: WebDriver, element, text: str) -> None:
    """pyperclip으로 값을 클립보드에 넣고 Ctrl+A, Ctrl+V로 붙여넣는다.
    한 글자씩 입력하는 send_keys보다 사람이 붙여넣는 것에 가까워 캡챠 유발을
    줄이는 데 도움이 된다."""
    original = None
    try:
        original = pyperclip.paste()
    except Exception:  # noqa: BLE001
        pass
    try:
        pyperclip.copy(text)
        element.click()
        element.send_keys(Keys.CONTROL, "a")
        element.send_keys(Keys.DELETE)
        ActionChains(driver).key_down(Keys.CONTROL).send_keys("v").key_up(Keys.CONTROL).perform()
    finally:
        if original is not None:
            try:
                pyperclip.copy(original)
            except Exception:  # noqa: BLE001
                pass


def _looks_logged_into_smartstore(driver: WebDriver) -> bool:
    """URL만으로는 부족하다: sell.smartstore.naver.com/home은 로그인 여부와
    무관하게 같은 주소에서 로그아웃 상태면 마케팅 페이지(로그인하기 링크
    있음), 로그인 상태면 진짜 대시보드를 보여준다."""
    _recover_active_window(driver)
    try:
        url = driver.current_url
    except Exception:  # noqa: BLE001
        return False
    if COMMERCE_LOGIN_HOST in url or NID_LOGIN_HOST in url:
        return False
    if "sell.smartstore.naver.com" not in url:
        return False
    if "login" in url.lower():
        return False
    try:
        if driver.find_elements(By.XPATH, LOGGED_OUT_MARKER_XPATH):
            return False
    except Exception:  # noqa: BLE001
        pass
    return True


def has_active_session(driver: WebDriver) -> bool:
    driver.get(SMARTSTORE_HOME_URL)
    _wait_for_redirect_settle(driver)
    time.sleep(1)  # SPA가 로그인/로그아웃 상태를 그려낼 시간을 준다
    return _looks_logged_into_smartstore(driver)


def login(driver: WebDriver, control: ControlState) -> bool:
    if not config.NAVER_ID or not config.NAVER_PASSWORD:
        raise LoginFailedError("NAVER_ID / NAVER_PASSWORD가 .env에 설정되지 않았습니다.")

    if has_active_session(driver):
        emit_log("이미 스마트스토어 로그인 세션이 존재합니다. 로그인 절차를 건너뜁니다.")
        return True

    emit_log("로그인 세션이 없어 로그인을 진행합니다.")

    if "sell.smartstore.naver.com" in _safe_current_url(driver):
        emit_log("스마트스토어 홈에서 '로그인하기'를 클릭합니다.")
        if _click_first_match(driver, LOGIN_ENTRY_SELECTORS):
            _wait_for_url_contains(driver, COMMERCE_LOGIN_HOST, timeout=10)
        else:
            emit_log("'로그인하기' 버튼을 찾지 못했습니다. 페이지 구조가 바뀌었을 수 있습니다.", level="error")

    if COMMERCE_LOGIN_HOST in _safe_current_url(driver):
        emit_log("커머스 로그인 화면에서 '네이버 아이디로 로그인'을 클릭합니다.")
        if _click_first_match(driver, NAVER_ID_LOGIN_SELECTORS):
            if _wait_for_url_contains(driver, NID_LOGIN_HOST, timeout=10):
                emit_log(f"로그인 창으로 전환했습니다: {_safe_current_url(driver)}")
        else:
            emit_log("'네이버 아이디로 로그인' 버튼을 찾지 못했습니다.", level="error")
            save_debug_screenshot(driver, "commerce_login_missing")
            return False

    if NID_LOGIN_HOST not in _safe_current_url(driver):
        emit_log(f"예상하지 못한 화면입니다: {_safe_current_url(driver)}", level="error")
        save_debug_screenshot(driver, "unexpected_screen")
        return False

    wait = WebDriverWait(driver, 15)
    id_field = wait.until(EC.presence_of_element_located((By.ID, "id")))
    pw_field = wait.until(EC.presence_of_element_located((By.ID, "pw")))

    emit_log("아이디/비밀번호를 클립보드 붙여넣기 방식으로 입력합니다.")
    _paste_into(driver, id_field, config.NAVER_ID)
    _paste_into(driver, pw_field, config.NAVER_PASSWORD)

    if _click_login_button(driver):
        emit_log("로그인 버튼을 클릭했습니다.")
    else:
        emit_log("로그인 버튼을 찾지 못해 Enter 키로 로그인 폼을 제출합니다.", level="warn")
        pw_field.send_keys(Keys.RETURN)

    time.sleep(2)  # 응답/리다이렉트가 렌더링될 시간을 준다
    return _wait_for_login_completion(driver, control)


def _refill_and_submit(driver: WebDriver) -> None:
    try:
        id_field = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.ID, "id")))
        _paste_into(driver, id_field, config.NAVER_ID)
    except Exception:  # noqa: BLE001
        pass  # 이 화면에서는 아이디가 이미 채워져 있거나 읽기 전용일 수 있다

    try:
        pw_field = driver.find_element(By.ID, "pw")
    except Exception:  # noqa: BLE001
        emit_log("비밀번호 입력창을 찾지 못해 자동 재입력에 실패했습니다.", level="error")
        return

    _paste_into(driver, pw_field, config.NAVER_PASSWORD)
    if _click_login_button(driver):
        emit_log("로그인 버튼을 다시 클릭했습니다.")
    else:
        pw_field.send_keys(Keys.RETURN)


def _click_first_match(driver: WebDriver, selectors, wait_seconds: int = 5) -> bool:
    for by, selector in selectors:
        try:
            el = WebDriverWait(driver, wait_seconds).until(EC.element_to_be_clickable((by, selector)))
            handles_before = driver.window_handles
            el.click()
            _switch_to_new_window_if_opened(driver, handles_before)
            return True
        except Exception:  # noqa: BLE001
            continue
    return False


def _click_login_button(driver: WebDriver) -> bool:
    return _click_first_match(driver, LOGIN_BUTTON_SELECTORS, wait_seconds=3)


def _switch_to_new_window_if_opened(driver: WebDriver, handles_before, timeout: float = 3) -> bool:
    """'네이버 아이디로 로그인' 등 일부 버튼은 다음 단계를 새 창(팝업)으로 연다.
    Selenium은 자동으로 따라가지 않으므로 새 handle을 직접 찾아 전환해야 한다."""
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        try:
            handles_after = driver.window_handles
        except Exception:  # noqa: BLE001
            return False
        new_handles = [h for h in handles_after if h not in handles_before]
        if new_handles:
            try:
                driver.switch_to.window(new_handles[-1])
                return True
            except Exception:  # noqa: BLE001
                return False
        time.sleep(0.2)
    return False


def _recover_active_window(driver: WebDriver) -> bool:
    """팝업이 로그인 완료 후 스스로 닫히는 경우 등, 현재 window handle이
    무효화됐다면 남아 있는 창으로 전환한다."""
    try:
        driver.current_url
        return True
    except Exception:  # noqa: BLE001
        pass
    try:
        handles = driver.window_handles
    except Exception:  # noqa: BLE001
        return False
    for handle in reversed(handles):
        try:
            driver.switch_to.window(handle)
            driver.current_url
            return True
        except Exception:  # noqa: BLE001
            continue
    return False


def _wait_for_url_contains(driver: WebDriver, substring: str, timeout: int = 10) -> bool:
    def _check(d: WebDriver) -> bool:
        _recover_active_window(d)
        try:
            return substring in d.current_url
        except Exception:  # noqa: BLE001
            return False

    try:
        WebDriverWait(driver, timeout).until(_check)
        return True
    except Exception:  # noqa: BLE001
        return False


def _wait_for_redirect_settle(driver: WebDriver, timeout: int = 5) -> None:
    end = time.monotonic() + timeout
    last_url = _safe_current_url(driver)
    while time.monotonic() < end:
        time.sleep(0.5)
        url = _safe_current_url(driver)
        if url == last_url:
            return
        last_url = url


def _wait_for_login_completion(driver: WebDriver, control: ControlState, timeout: int = CAPTCHA_WAIT_TIMEOUT_SEC) -> bool:
    start = time.monotonic()
    warned_captcha = False
    warned_form = False
    plain_form_retries = 0
    last_heartbeat = start

    while time.monotonic() - start < timeout:
        control.wait_if_paused()
        if control.should_stop():
            emit_log("사용자 요청으로 로그인 대기를 중단합니다.")
            return False

        if _looks_logged_into_smartstore(driver):
            emit_log("네이버 로그인 및 스마트스토어 진입에 성공했습니다.")
            return True

        if not warned_captcha and _looks_like_captcha(driver):
            emit_log(
                "네이버가 이미지 캡챠 인증을 요구합니다. "
                "브라우저 창에서 캡챠를 직접 입력하고 확인 버튼을 눌러주세요.",
                level="warn",
            )
            save_debug_screenshot(driver, "captcha")
            warned_captcha = True
        elif _on_plain_login_form(driver):
            if plain_form_retries < MAX_PLAIN_FORM_AUTO_RETRIES:
                plain_form_retries += 1
                emit_log(
                    f"'다시 로그인해 주세요' 화면이 감지되어 아이디/비밀번호를 자동으로 다시 "
                    f"입력합니다. ({plain_form_retries}/{MAX_PLAIN_FORM_AUTO_RETRIES})",
                    level="warn",
                )
                _refill_and_submit(driver)
                time.sleep(2)
                continue
            elif not warned_form:
                emit_log(
                    "자동 재입력으로도 해결되지 않았습니다. 브라우저 창에서 아이디와 비밀번호를 "
                    "직접 입력하시고 '로그인' 버튼을 클릭해 주세요.",
                    level="warn",
                )
                save_debug_screenshot(driver, "reverify")
                warned_form = True

        now = time.monotonic()
        if now - last_heartbeat >= HEARTBEAT_INTERVAL_SEC:
            elapsed = int(now - start)
            emit_log(f"로그인 완료 대기 중... ({elapsed}s 경과, 현재 화면: {_safe_current_url(driver)})")
            last_heartbeat = now

        time.sleep(1)

    save_debug_screenshot(driver, "timeout")
    emit_log("로그인이 제한 시간 내에 완료되지 않았습니다. (인증 미완료 또는 계정 정보 오류 가능)", level="error")
    return False


def _safe_current_url(driver: WebDriver) -> str:
    _recover_active_window(driver)
    try:
        return driver.current_url
    except Exception:  # noqa: BLE001
        return "(알 수 없음)"


def _looks_like_captcha(driver: WebDriver) -> bool:
    for by, selector in CAPTCHA_ELEMENT_SELECTORS:
        try:
            el = driver.find_element(by, selector)
            if el.is_displayed():
                return True
        except Exception:  # noqa: BLE001
            continue
    return False


def _on_plain_login_form(driver: WebDriver) -> bool:
    try:
        id_el = driver.find_element(By.ID, "id")
        pw_el = driver.find_element(By.ID, "pw")
        return id_el.is_displayed() and pw_el.is_displayed()
    except Exception:  # noqa: BLE001
        return False
