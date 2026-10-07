import json
import time
from pathlib import Path

from selenium.common.exceptions import NoAlertPresentException, NoSuchWindowException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from .. import config
from ..utils.progress import emit_log

# 로그인 폼 요소를 실제 id/class 대신 화면에 보이는 placeholder/버튼 텍스트로 찾는다.
# (실제 선택자를 확인하기 전, 우선 눈으로 확인한 텍스트 기준으로 작성)
EMAIL_INPUT_SELECTOR = "input[placeholder='Admin Email']"
PASSWORD_INPUT_SELECTOR = "input[placeholder='Password']"
LOGIN_BUTTON_XPATH = (
    "//button[contains(., 'Login')] | //input[@type='submit' and contains(@value, 'Login')]"
)

# 새로 로그인할 때마다 LMS가 봇으로 의심할 수 있어, 성공한 로그인은 쿠키로 저장해뒀다가
# 다음 실행에서 재사용한다 (아래 세션 저장/복원 로직).
SESSION_DIR_NAME = "session"
COOKIES_FILENAME = "lms_cookies.json"


class LoginFailedError(Exception):
    pass


def login(driver) -> None:
    """LMS 로그인. .env 의 LMS_ID / LMS_PASSWORD 사용.

    저장된 로그인 세션(쿠키)이 아직 유효하면 로그인을 생략하고 그 세션을 그대로 쓴다.
    세션이 없거나 만료된 경우에만 실제로 새로 로그인하고, 성공하면 세션을 다시 저장한다.
    """
    if not config.LMS_BASE_URL:
        raise LoginFailedError("LMS_BASE_URL이 .env에 설정되지 않았습니다.")

    if _try_restore_session(driver):
        return

    emit_log("LMS 로그인 시도")

    driver.get(config.LMS_BASE_URL)

    _dismiss_alert_if_present(driver)

    try:
        email_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, EMAIL_INPUT_SELECTOR))
        )
    except TimeoutException as exc:
        raise LoginFailedError("로그인 폼(아이디 입력창)을 찾을 수 없습니다.") from exc

    password_input = driver.find_element(By.CSS_SELECTOR, PASSWORD_INPUT_SELECTOR)

    email_input.clear()
    email_input.send_keys(config.LMS_ID)
    password_input.clear()
    password_input.send_keys(config.LMS_PASSWORD)

    time.sleep(config.REQUEST_DELAY_SECONDS)

    login_button = driver.find_element(By.XPATH, LOGIN_BUTTON_XPATH)
    login_button.click()

    time.sleep(config.REQUEST_DELAY_SECONDS)

    _dismiss_alert_if_present(driver)

    # TODO: 로그인 성공 여부를 판별하는 요소(예: 대시보드 표시)를 확인하고,
    # 실패 시(아이디/비번 틀림 등) LoginFailedError를 발생시켜야 한다.
    emit_log("LMS 로그인 시도 완료 (TODO: 성공 여부 검증 로직 추가 필요)")

    _save_session(driver)


def _dismiss_alert_if_present(driver, timeout: float = 3) -> bool:
    """페이지 진입 시 뜨는 JS alert('먼저 관리자 로그인 후 이용하세요' 등)를 자동으로 닫는다.

    반환값: alert가 실제로 떠서 닫았으면 True, 안 떴으면 False.
    (세션 복원 후 이 alert가 다시 뜨면 저장해둔 세션이 만료됐다는 뜻이라 판별에 쓴다.)
    """
    try:
        WebDriverWait(driver, timeout).until(EC.alert_is_present())
        alert_text = driver.switch_to.alert.text
        emit_log(f"알림창 감지 후 닫음: {alert_text}")
        driver.switch_to.alert.accept()
        return True
    except (TimeoutException, NoAlertPresentException):
        return False


def _session_dir() -> Path:
    return config.DATA_DIR / SESSION_DIR_NAME


def _cookies_path() -> Path:
    return _session_dir() / COOKIES_FILENAME


def _try_restore_session(driver) -> bool:
    """저장된 쿠키가 있으면 복원을 시도한다. 성공하면 True(로그인 생략 가능).

    테스트 중 브라우저 창을 실수로 닫는 등(크롬 창이 사라짐) NoSuchWindowException이
    나는 경우에도 원인 불명 오류로 작업 전체가 죽지 않도록, 그 경우엔 세션 복원만
    포기하고 아래 login()의 새 로그인 절차로 넘어가게 False를 반환한다.
    """
    cookies = _load_saved_cookies()
    if not cookies:
        return False

    try:
        # 쿠키는 같은 도메인의 페이지가 열려있어야 추가할 수 있어서, 일단 먼저 접속한다.
        # 이 시점엔 아직 쿠키가 없으므로 뜨는 alert는 의미 없는(항상 뜨는) 것이라 그냥 닫는다.
        driver.get(config.LMS_BASE_URL)
        _dismiss_alert_if_present(driver)

        restored_any = False
        for cookie in cookies:
            try:
                driver.add_cookie(_sanitize_cookie_for_selenium(cookie))
                restored_any = True
            except Exception:  # noqa: BLE001 - 쿠키 하나가 깨져 있어도 나머지는 계속 시도
                continue

        if not restored_any:
            return False

        driver.get(config.LMS_BASE_URL)

        if _dismiss_alert_if_present(driver):
            # 쿠키를 실은 채로 다시 열었는데도 로그인 요구 alert가 뜨면 세션이 만료된 것.
            emit_log("저장된 로그인 세션이 만료되어 새로 로그인합니다.")
            _clear_saved_session()
            return False
    except NoSuchWindowException:
        emit_log(
            "브라우저 창을 찾을 수 없어 세션 복원을 건너뜁니다 "
            "(작업 중 창을 직접 닫지는 않으셨는지 확인해주세요). 새로 로그인합니다.",
            level="warn",
        )
        return False

    emit_log("저장된 로그인 세션을 재사용합니다 (로그인 생략).")
    return True


def _sanitize_cookie_for_selenium(cookie: dict) -> dict:
    """driver.get_cookies()로 저장해둔 쿠키를 add_cookie()가 받아들이는 형태로 정리."""
    sanitized = {k: v for k, v in cookie.items() if k in {"name", "value", "path", "domain", "secure", "httpOnly", "expiry", "sameSite"}}
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
