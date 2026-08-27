import time

from ..control import ControlState
from ..lms.auth import login
from ..lms.driver import build_driver
from ..lms.navigation import go_to_native_tutor_schedule
from ..lms.tutor_search import click_sch_button, search_tutor
from ..utils.progress import emit_done, emit_log

JOB_NAME = "tutor_search_test"


def run(job_payload: dict, control: ControlState) -> None:
    """로그인 -> 시간표관리 이동 -> 강사검색 -> SCH 클릭까지만 확인하는 테스트 작업.
    성공하면 브라우저를 열어둔 채 '중단'을 누를 때까지 대기한다.
    """
    tutor_name = (job_payload.get("tutorName") or "").strip()
    if not tutor_name:
        emit_log("테스트할 강사 이름이 비어 있습니다.", level="error")
        emit_done({"job": JOB_NAME})
        return

    driver = build_driver()

    try:
        login(driver)
        go_to_native_tutor_schedule(driver)
        search_tutor(driver, tutor_name)
        click_sch_button(driver, tutor_name)

        emit_log(f"'{tutor_name}' 검색 -> SCH 클릭까지 완료. 브라우저 창을 직접 확인해주세요.")
        emit_log("'중단' 버튼을 누르기 전까지 브라우저가 열린 상태로 유지됩니다.")

        while not control.should_stop():
            control.wait_if_paused()
            time.sleep(0.5)

        emit_log("사용자 요청으로 테스트를 종료합니다.")
    finally:
        driver.quit()

    emit_done({"job": JOB_NAME})
