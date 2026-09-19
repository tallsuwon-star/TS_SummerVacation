"""office.talkstation.co.kr(사내 업무공유센터, Task Sharing Center) 로그인.

이 사이트는 사내망 전용이라 개발 중에는 로그인 화면 HTML을 직접 확인할 수
없었다. 사용자가 알려준 로그인 후 화면(사이드바에 "Task Sharing Center",
/main 대시보드, 우측 상단 로그아웃 모달 등)만 근거로, CI4 + sb-admin-2
템플릿에서 흔한 로그인 폼 패턴(아이디/비밀번호 input + "로그인" 버튼)을
여러 후보 선택자로 순서대로 시도한다.

실제 로그인 화면 구조가 아래 후보와 다르면 로그인 폼을 못 찾았다는 로그가
찍힐 것이다 — 그 경우 사용자가 로그인 화면 HTML을 알려주면 선택자를 정확히
맞출 수 있다.
"""

import json
import time
from pathlib import Path

from selenium.common.exceptions import NoAlertPresentException, NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from .. import config
from ..utils.progress import emit_log

SESSION_DIR_NAME = "session"
COOKIES_FILENAME = "office_cookies.json"

LOGOUT_MODAL_ID = "logoutModal"  # 로그인된 페이지에만 존재하는 요소 (사용자가 알려준 HTML 기준)

# 로그인 폼 후보 선택자들. 위에서부터 순서대로 시도한다.
ID_INPUT_SELECTORS = [
    (By.CSS_SELECTOR, "input[name='member_id']"),
    (By.CSS_SELECTOR, "input[name='userid']"),
    (By.CSS_SELECTOR, "input[name='username']"),
    (By.CSS_SELECTOR, "input[name='id']"),
    (By.CSS_SELECTOR, "input[name='email']"),
    (By.ID, "member_id"),
    (By.ID, "userid"),
    (By.ID, "username"),
    (By.ID, "id"),
    (By.ID, "email"),
]
PASSWORD_INPUT_SELECTORS = [
    (By.CSS_SELECTOR, "input[type='password']"),
]
LOGIN_BUTTON_XPATH = (
    "//button[contains(., '로그인') or contains(., 'Login') or contains(., 'LOGIN')] "
    "| //input[@type='submit' and (contains(@value, '로그인') or contains(@value, 'Login'))]"
)


class LoginFailedError(Exception):
    pass


def login(driver) -> None:
    """office.talkstation.co.kr 로그인.

    저장된 세션(쿠키)이 아직 유효하면 로그인 없이 그대로 재사용한다.
    """
    if not config.OFFICE_ID or not config.OFFICE_PASSWORD:
        raise LoginFailedError(
            "office.talkstation.co.kr 로그인 정보가 없습니다. "
            "⚙ LMS 로그인 설정에 아이디/비밀번호를 입력해주세요(같은 계정을 재사용합니다)."
        )

    if _try_restore_session(driver):
        return

    emit_log("office.talkstation.co.kr 로그인 시도")

    driver.get(config.OFFICE_BASE_URL)

    if _is_logged_in(driver):
        emit_log("이미 로그인된 상태입니다 (로그인 절차 생략).")
        _save_session(driver)
        return

    id_input = _find_first(driver, ID_INPUT_SELECTORS)
    password_input = _find_first(driver, PASSWORD_INPUT_SELECTORS)

    if id_input is None or password_input is None:
        raise LoginFailedError(
            "로그인 폼(아이디/비밀번호 입력창)을 찾을 수 없습니다. "
            "로그인 화면 구조가 예상과 달라 선택자를 맞춰야 합니다. "
            "현재 화면 URL: " + _safe_current_url(driver)
        )

    id_input.clear()
    id_input.send_keys(config.OFFICE_ID)
    password_input.clear()
    password_input.send_keys(config.OFFICE_PASSWORD)

    time.sleep(config.REQUEST_DELAY_SECONDS)

    try:
        login_button = driver.find_element(By.XPATH, LOGIN_BUTTON_XPATH)
        login_button.click()
    except NoSuchElementException:
        emit_log("로그인 버튼을 찾지 못해 Enter 키로 로그인 폼을 제출합니다.", level="warn")
        password_input.send_keys(Keys.RETURN)

    time.sleep(config.REQUEST_DELAY_SECONDS)

    alert_text = _dismiss_alert_if_present(driver)
    if alert_text:
        raise LoginFailedError(f"로그인 중 알림창이 떴습니다: {alert_text}")

    if not _is_logged_in(driver):
        raise LoginFailedError(
            "로그인에 실패한 것으로 보입니다 (아이디/비밀번호를 다시 확인해주세요). "
            "현재 화면 URL: " + _safe_current_url(driver)
        )

    emit_log("office.talkstation.co.kr 로그인 성공")
    _save_session(driver)


def _find_first(driver, selectors, timeout: float = 8):
    for by, selector in selectors:
        try:
            return WebDriverWait(driver, timeout).until(EC.presence_of_element_located((by, selector)))
        except TimeoutException:
            continue
    return None


def _is_logged_in(driver) -> bool:
    """로그인 후 페이지에만 있는 요소(로그아웃 모달, 사이드바 브랜드 등)로 판별."""
    try:
        if driver.find_elements(By.ID, LOGOUT_MODAL_ID):
            return True
        if driver.find_elements(By.CSS_SELECTOR, "a.sidebar-brand"):
            return True
    except Exception:  # noqa: BLE001
        pass
    return False


def _dismiss_alert_if_present(driver, timeout: float = 2) -> str | None:
    try:
        WebDriverWait(driver, timeout).until(EC.alert_is_present())
        alert_text = driver.switch_to.alert.text
        driver.switch_to.alert.accept()
        return alert_text
    except (TimeoutException, NoAlertPresentException):
        return None


def _safe_current_url(driver) -> str:
    try:
        return driver.current_url
    except Exception:  # noqa: BLE001
        return "(알 수 없음)"


def _session_dir() -> Path:
    return config.DATA_DIR / SESSION_DIR_NAME


def _cookies_path() -> Path:
    return _session_dir() / COOKIES_FILENAME


def _try_restore_session(driver) -> bool:
    cookies = _load_saved_cookies()
    if not cookies:
        return False

    driver.get(config.OFFICE_BASE_URL)

    restored_any = False
    for cookie in cookies:
        try:
            driver.add_cookie(_sanitize_cookie_for_selenium(cookie))
            restored_any = True
        except Exception:  # noqa: BLE001
            continue

    if not restored_any:
        return False

    driver.get(config.OFFICE_BASE_URL)

    if not _is_logged_in(driver):
        emit_log("저장된 office 로그인 세션이 만료되어 새로 로그인합니다.")
        _clear_saved_session()
        return False

    emit_log("저장된 office 로그인 세션을 재사용합니다 (로그인 생략).")
    return True


def _sanitize_cookie_for_selenium(cookie: dict) -> dict:
    sanitized = {
        k: v
        for k, v in cookie.items()
        if k in {"name", "value", "path", "domain", "secure", "httpOnly", "expiry", "sameSite"}
    }
    if "expiry" in sanitized and sanitized["expiry"] is not None:
        sanitized["expiry"] = int(sanitized["expiry"])
    return sanitized


def _load_saved_cookies() -> list[dict] | None:
    path = _cookies_path()
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("cookies") or None
    except (json.JSONDecodeError, OSError):
        return None


def _save_session(driver) -> None:
    path = _cookies_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"savedAt": time.time(), "cookies": driver.get_cookies()}
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)


def _clear_saved_session() -> None:
    try:
        _cookies_path().unlink()
    except FileNotFoundError:
        pass
