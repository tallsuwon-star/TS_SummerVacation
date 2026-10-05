"""강사 시간표 화면에서, 사용자가 체크박스로 고른 여러 수업 슬롯을 한 번에
열거나 닫는 작업.

로그인 -> 시간표관리 -> 원어민 강사 시간표 -> 강사검색 -> SCH 클릭까지는
tutor_search_test.py와 동일한 기존 경로를 그대로 재사용한다.

사용자가 실수를 되짚어볼 수 있도록, 슬롯마다 바뀌기 전/후 상태를 로그와
결과표(emit_tutor_schedule_record)로 남긴다. 사용자가 명시적으로 요청한 대로
모든 슬롯을 처리한 뒤 "작성완료"까지 눌러 실제로 제출한다."""

import time

from ..control import ControlState
from ..lms.auth import LoginFailedError, login
from ..lms.driver import build_driver
from ..lms.navigation import NavigationError, go_to_native_tutor_schedule
from ..lms.tutor_schedule import (
    WEEKDAY_NAMES,
    TutorScheduleError,
    open_schedule_checkboxes,
    set_hour_state,
    submit_schedule,
    wait_for_schedule_page,
)
from ..lms.tutor_search import SchButtonNotFoundError, TutorNotFoundError, click_sch_button, search_tutor
from ..utils.progress import emit_done, emit_log, emit_tutor_schedule_record

JOB_NAME = "tutor_schedule_set"


def run(job_payload: dict, control: ControlState) -> None:
    tutor_name = (job_payload.get("tutorName") or "").strip()
    weekday = job_payload.get("weekday")
    state = (job_payload.get("state") or "").strip()
    slots = job_payload.get("slots") or []

    if not tutor_name or weekday is None or not state or not slots:
        emit_log("강사 이름/요일/상태/시간 슬롯을 모두 선택해주세요.", level="error")
        emit_done({"success": False, "error": "missing-input"})
        return

    weekday = int(weekday)
    weekday_name = WEEKDAY_NAMES[weekday]

    driver = build_driver()
    try:
        login(driver)
        go_to_native_tutor_schedule(driver)
        search_tutor(driver, tutor_name)
        click_sch_button(driver, tutor_name)
        open_schedule_checkboxes(driver)
        wait_for_schedule_page(driver)

        for i, slot in enumerate(slots, start=1):
            if control.should_stop():
                emit_log("사용자 요청으로 중단합니다 (제출은 하지 않았습니다).")
                break
            control.wait_if_paused()

            hour = int(slot.get("hour"))
            start_minute = int(slot.get("startMinute", 0))
            time_label = f"{hour:02d}:{start_minute:02d}"

            before_label, after_label = set_hour_state(driver, weekday, hour, state, start_minute=start_minute)
            emit_log(f"({i}/{len(slots)}) {weekday_name}요일 {time_label}")
            emit_tutor_schedule_record(
                {
                    "tutor": tutor_name,
                    "weekday": weekday_name,
                    "time": time_label,
                    "before": before_label,
                    "after": after_label,
                }
            )
        else:
            emit_log("모든 슬롯 설정 완료. '작성완료' 제출을 진행합니다.")
            submit_schedule(driver)
            emit_log("제출까지 완료했습니다. 화면에서 확인 후 '중단'을 눌러주세요.")

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
