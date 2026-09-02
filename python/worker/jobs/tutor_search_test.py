import time
from datetime import date, datetime

from ..control import ControlState
from ..lms.auth import login
from ..lms.consultation import ConsultationLoadError, collect_consultation_records, count_makeup_credits
from ..lms.driver import build_driver
from ..lms.member_popup import (
    MemberPopupNotOpenedError,
    close_member_popup,
    open_consultation_tab,
    open_member_popup,
)
from ..lms.navigation import go_to_native_tutor_schedule
from ..lms.schedule import collect_am_class_members, ensure_am_view
from ..lms.tutor_search import click_sch_button, search_tutor
from ..utils.progress import emit_done, emit_log, emit_record

JOB_NAME = "tutor_search_test"

_DEFAULT_CONSULTATION_AFTER = "2026-08-18"
_DEFAULT_CLASS_AFTER = "2026-08-20"


def run(job_payload: dict, control: ControlState) -> None:
    """로그인 -> 시간표관리 이동 -> 강사검색 -> SCH 클릭 -> 오전 전환 -> 회원 명단 수집
    -> 회원별 상담관리에서 보강권 지급 건수 확인까지 한 번에 확인하는 테스트 작업.
    성공하면 브라우저를 열어둔 채 '중단'을 누를 때까지 대기한다.
    """
    tutor_name = (job_payload.get("tutorName") or "").strip()
    if not tutor_name:
        emit_log("테스트할 강사 이름이 비어 있습니다.", level="error")
        emit_done({"job": JOB_NAME})
        return

    consultation_after = _parse_iso_date(job_payload.get("consultationAfter") or _DEFAULT_CONSULTATION_AFTER)
    class_after = _parse_iso_date(job_payload.get("classAfter") or _DEFAULT_CLASS_AFTER)

    driver = build_driver()

    try:
        login(driver)
        go_to_native_tutor_schedule(driver)
        search_tutor(driver, tutor_name)
        click_sch_button(driver, tutor_name)
        schedule_window = driver.current_window_handle
        ensure_am_view(driver)

        member_names = collect_am_class_members(driver)
        emit_log(f"오전(10:00~12:30 시작) 회원 명단 ({len(member_names)}명): {member_names}")

        for member_name in member_names:
            control.wait_if_paused()
            if control.should_stop():
                emit_log("사용자 요청으로 테스트를 중단합니다.")
                break

            popup_opened = False
            try:
                open_member_popup(driver, member_name)
                popup_opened = True
                open_consultation_tab(driver)

                records = collect_consultation_records(driver)
                credit_count = count_makeup_credits(records, consultation_after, class_after, tutor_name, member_name)

                emit_log(f"[{tutor_name} / {member_name}] 보강권 지급 건수: {credit_count}")
                emit_record(tutor_name, member_name, credit_count)
            except MemberPopupNotOpenedError as exc:
                emit_log(f"[{tutor_name} / {member_name}] 회원 팝업 열기 실패: {exc}", level="error")
            except ConsultationLoadError as exc:
                emit_log(f"[{tutor_name} / {member_name}] 상담관리 로딩 실패: {exc}", level="error")
            finally:
                if popup_opened:
                    close_member_popup(driver, schedule_window)

        emit_log(f"'{tutor_name}' 회원별 보강권 확인까지 완료. 브라우저 창을 직접 확인해주세요.")
        emit_log("'중단' 버튼을 누르기 전까지 브라우저가 열린 상태로 유지됩니다.")

        while not control.should_stop():
            control.wait_if_paused()
            time.sleep(0.5)

        emit_log("사용자 요청으로 테스트를 종료합니다.")
    finally:
        driver.quit()

    emit_done({"job": JOB_NAME})


def _parse_iso_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()
