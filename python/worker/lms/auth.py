import time

from .. import config
from ..utils.progress import emit_log


class LoginFailedError(Exception):
    pass


def login(driver) -> None:
    """LMS 로그인. .env 의 LMS_ID / LMS_PASSWORD 사용."""
    emit_log("LMS 로그인 시도")

    if not config.LMS_BASE_URL:
        raise LoginFailedError("LMS_BASE_URL이 .env에 설정되지 않았습니다.")

    driver.get(config.LMS_BASE_URL)

    # TODO: 아이디/비밀번호 입력창 선택자 확정 필요
    # id_input = driver.find_element(By.CSS_SELECTOR, "TODO")
    # pw_input = driver.find_element(By.CSS_SELECTOR, "TODO")
    # id_input.send_keys(config.LMS_ID)
    # pw_input.send_keys(config.LMS_PASSWORD)

    # TODO: 로그인 버튼 선택자 확정 필요
    # login_btn = driver.find_element(By.CSS_SELECTOR, "TODO")
    # login_btn.click()

    time.sleep(config.REQUEST_DELAY_SECONDS)

    # TODO: 로그인 성공 여부를 판별하는 요소(예: 대시보드 표시)를 확인하고,
    # 실패 시 LoginFailedError를 발생시켜야 한다.
    emit_log("LMS 로그인 완료 (TODO: 성공 여부 검증 로직 추가 필요)")
