"""강사 시간표 화면에서, 사용자가 고른 여러 강사 x 여러 요일 x 여러 수업 슬롯을
한 번에 열거나 닫는 작업.

강사 한 명씩 "원어민 강사 시간표" 검색 화면 -> 강사검색 -> SCH 클릭 -> 체크박스
팝업 순으로 들어가 그 강사의 요일x슬롯 조합을 전부 처리하고 "작성완료"까지
제출한 뒤, 열어뒀던 팝업들을 닫고 다음 강사를 검색하는 식으로 반복한다.

사용자가 실수를 되짚어볼 수 있도록, 슬롯마다 바뀌기 전/후 상태를 로그와
결과표(emit_tutor_schedule_record)로 남긴다."""

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


def _close_popups_except(driver, keep_handle: str) -> None:
    """강사 한 명 처리를 끝낸 뒤, 그 강사의 SCH/체크박스 팝업들을 정리하고
    다음 강사를 검색할 원래 창(keep_handle)으로 돌아간다."""
    for handle in list(driver.window_handles):
        if handle == keep_handle:
            continue
        driver.switch_to.window(handle)
        driver.close()
    driver.switch_to.window(keep_handle)


def run(job_payload: dict, control: ControlState) -> None:
    tutor_names = [name.strip() for name in (job_payload.get("tutorNames") or []) if name and name.strip()]
    weekdays = [int(w) for w in (job_payload.get("weekdays") or [])]
    state = (job_payload.get("state") or "").strip()
    slots = job_payload.get("slots") or []

    if not tutor_names or not weekdays or not state or not slots:
        emit_log("강사/요일/상태/시간 슬롯을 모두 선택해주세요.", level="error")
        emit_done({"success": False, "error": "missing-input"})
        return

    total_count = len(tutor_names) * len(weekdays) * len(slots)
    emit_log(f"강사 {len(tutor_names)}명 x 요일 {len(weekdays)}개 x 시간 {len(slots)}개 = 총 {total_count}건 처리 시작")

    driver = build_driver()
    done_count = 0
    stopped = False
    try:
        login(driver)
        go_to_native_tutor_schedule(driver)
        search_window = driver.current_window_handle

        for tutor_name in tutor_names:
            if control.should_stop():
                stopped = True
                break
            control.wait_if_paused()

            driver.switch_to.window(search_window)
            search_tutor(driver, tutor_name)
            click_sch_button(driver, tutor_name)
            open_schedule_checkboxes(driver)
            wait_for_schedule_page(driver)

            for weekday in weekdays:
                if control.should_stop():
                    stopped = True
                    break
                weekday_name = WEEKDAY_NAMES[weekday]

                for slot in slots:
                    if control.should_stop():
                        stopped = True
                        break
                    control.wait_if_paused()

                    hour = int(slot.get("hour"))
                    start_minute = int(slot.get("startMinute", 0))
                    time_label = f"{hour:02d}:{start_minute:02d}"

                    before_label, after_label = set_hour_state(
                        driver, weekday, hour, state, start_minute=start_minute
                    )
                    done_count += 1
                    emit_log(f"({done_count}/{total_count}) {tutor_name} {weekday_name}요일 {time_label}")
                    emit_tutor_schedule_record(
                        {
                            "tutor": tutor_name,
                            "weekday": weekday_name,
                            "time": time_label,
                            "before": before_label,
                            "after": after_label,
                        }
                    )

                if stopped:
                    break

            if stopped:
                emit_log(f"사용자 요청으로 중단합니다 ({tutor_name}은(는) 제출하지 않았습니다).")
                break

            emit_log(f"{tutor_name} 설정 완료. '작성완료' 제출을 진행합니다.")
            submit_schedule(driver)
            _close_popups_except(driver, search_window)

        if not stopped:
            emit_log("모든 강사 설정과 제출을 완료했습니다. 화면에서 확인 후 '중단'을 눌러주세요.")

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
