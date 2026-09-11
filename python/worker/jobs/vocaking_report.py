import time

from ..control import ControlState
from ..lms.auth import login
from ..lms.driver import build_driver
from ..lms.navigation import go_to_integrated_lms
from ..lms.vocaking import click_charged_student_list, click_vocaking_tab
from ..utils.progress import emit_done, emit_log

JOB_NAME = "vocaking_report"


def run(job_payload: dict, control: ControlState) -> None:
    """보카킹 보고 작업.

    아직 '유료 수강생 리스트' 화면 안의 무료/유료 토글, 보카킹 횟수별 회원
    목록 테이블의 실제 구조를 확인하는 단계라, 지금은 로그인 → 통합LMS →
    보카킹 탭 → 유료 수강생 리스트까지 이동해 브라우저를 열어둔 채 대기한다.
    사용자가 화면을 직접 보고 회원 목록 HTML을 확인해주면 이어서 구현한다.
    """
    driver = build_driver()

    try:
        login(driver)
        go_to_integrated_lms(driver)
        click_vocaking_tab(driver)
        click_charged_student_list(driver)
        emit_log("브라우저 창을 직접 확인해주세요. '중단' 버튼을 누르기 전까지 열린 상태로 유지됩니다.")

        while not control.should_stop():
            control.wait_if_paused()
            time.sleep(0.5)

        emit_log("사용자 요청으로 테스트를 종료합니다.")
    finally:
        driver.quit()

    emit_done({"job": JOB_NAME})
