"""강사 시간표 화면에서 지정한 요일×시간을 블랙/그레이/화이트 타임으로 바꾸는 작업.

로그인 -> 시간표관리 -> 원어민 강사 시간표 -> 강사검색 -> SCH 클릭까지는
tutor_search_test.py와 동일한 기존 경로를 그대로 재사용한다.

절대 "작성완료"(제출) 버튼은 누르지 않는다 — 입력만 해두고 사용자가 화면에서
직접 확인한 뒤 제출한다. 입력이 끝나도 브라우저는 계속 열어두고, 사용자가 확인을
마친 뒤 '중단'을 누르면 그때 닫는다."""

import time

from ..control import ControlState
from ..lms.auth import LoginFailedError, login
from ..lms.driver import build_driver
from ..lms.navigation import NavigationError, go_to_native_tutor_schedule
from ..lms.tutor_schedule import TutorScheduleError, set_hour_state, wait_for_schedule_page
from ..lms.tutor_search import SchButtonNotFoundError, TutorNotFoundError, click_sch_button, search_tutor
from ..utils.progress import emit_done, emit_log

JOB_NAME = "tutor_schedule_set"


def run(job_payload: dict, control: ControlState) -> None:
    tutor_name = (job_payload.get("tutorName") or "").strip()
    weekday = job_payload.get("weekday")
    hour = job_payload.get("hour")
    state = (job_payload.get("state") or "").strip()

    if not tutor_name or weekday is None or hour is None or not state:
        emit_log("강사 이름/요일/시/상태를 모두 입력해주세요.", level="error")
        emit_done({"success": False, "error": "missing-input"})
        return

    driver = build_driver()
    try:
        login(driver)
        go_to_native_tutor_schedule(driver)
        search_tutor(driver, tutor_name)
        click_sch_button(driver, tutor_name)
        wait_for_schedule_page(driver)

        set_hour_state(driver, int(weekday), int(hour), state)

        emit_log("설정을 마쳤습니다. 화면에서 직접 확인 후 '작성완료'를 눌러주세요.")
        emit_log("확인이 끝나면 '중단' 버튼을 눌러 이 작업을 종료해주세요 (브라우저는 그대로 열려 있습니다).")

        while not control.should_stop():
            control.wait_if_paused()
            time.sleep(0.5)
        emit_log("사용자 요청으로 종료합니다.")
    except (LoginFailedError, NavigationError, TutorNotFoundError, SchButtonNotFoundError, TutorScheduleError) as exc:
        emit_log(str(exc), level="error")
        emit_done({"success": False, "error": str(exc)})
        return
    except Exception as exc:  # noqa: BLE001
        emit_log(f"작업 중 오류: {exc}", level="error")
        emit_done({"success": False, "error": str(exc)})
        return
    finally:
        driver.quit()

    emit_done({"success": True})
