import time

from ..control import ControlState
from ..lms.auth import login
from ..lms.driver import build_driver
from ..lms.navigation import go_to_integrated_lms
from ..utils.progress import emit_done, emit_log

JOB_NAME = "vocaking_report"


def run(job_payload: dict, control: ControlState) -> None:
    """보카킹 보고 작업.

    아직 '통합LMS' 진입 이후의 화면 구조(보카킹 회원 목록 등)를 확인하는
    단계라, 지금은 로그인 후 통합LMS로 이동해 현재 URL/제목을 로그로 남기고
    브라우저를 열어둔 채 대기한다. 사용자가 화면을 직접 보고 다음 단계(유료
    수강생 리스트 진입, 무료/유료 및 보카킹 횟수별 회원 목록 파싱)에 필요한
    실제 HTML을 확인해주면 이어서 구현한다.
    """
    driver = build_driver()

    try:
        login(driver)
        go_to_integrated_lms(driver)
        emit_log("브라우저 창을 직접 확인해주세요. '중단' 버튼을 누르기 전까지 열린 상태로 유지됩니다.")

        while not control.should_stop():
            control.wait_if_paused()
            time.sleep(0.5)

        emit_log("사용자 요청으로 테스트를 종료합니다.")
    finally:
        driver.quit()

    emit_done({"job": JOB_NAME})
