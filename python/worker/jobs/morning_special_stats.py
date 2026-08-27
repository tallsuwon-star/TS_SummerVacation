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
from ..lms.tutor_search import SchButtonNotFoundError, TutorNotFoundError, click_sch_button, search_tutor
from ..sheets.gsheet_client import append_credit_row, get_worksheet
from ..utils.backup import save_backup
from ..utils.progress import emit_done, emit_log, emit_progress

JOB_NAME = "morning_special_stats"


def run(job_payload: dict, control: ControlState) -> None:
    """오전특강 통계 작업 전체 흐름 (동작 원칙 1~9).

    강사 1명 처리 중 오류가 나도 전체를 멈추지 않고 해당 강사만 실패 처리한 뒤 다음 강사로 진행한다.
    """
    tutors: list[str] = job_payload.get("tutors", [])
    consultation_after = _parse_iso_date(job_payload["consultationAfter"])
    class_after = _parse_iso_date(job_payload["classAfter"])

    driver = build_driver()
    records: list[dict] = []
    failures: list[dict] = []

    try:
        login(driver)
        go_to_native_tutor_schedule(driver)

        for tutor_name in tutors:
            control.wait_if_paused()
            if control.should_stop():
                emit_log("사용자 요청으로 작업을 중단합니다.")
                break

            emit_progress(tutor_name, "processing")

            try:
                _process_tutor(driver, tutor_name, consultation_after, class_after, records)
                found = sum(r["credit_count"] for r in records if r["tutor"] == tutor_name)
                emit_progress(tutor_name, "success", found=found)
            except TutorNotFoundError:
                _fail(failures, tutor_name, "강사 검색 실패")
            except SchButtonNotFoundError:
                _fail(failures, tutor_name, "SCH 없음")
            except MemberPopupNotOpenedError:
                _fail(failures, tutor_name, "회원 팝업 안 열림")
            except ConsultationLoadError:
                _fail(failures, tutor_name, "상담관리 로딩 실패")
            except Exception as exc:  # noqa: BLE001 - 강사 단위 오류도 전체 중단 없이 계속 진행해야 함
                _fail(failures, tutor_name, f"알 수 없는 오류: {exc}")
    finally:
        driver.quit()

    _write_to_sheet(records)

    backup_path = save_backup(JOB_NAME, records)
    emit_log(f"백업 저장 완료: {backup_path}")

    emit_done(
        {
            "total_tutors": len(tutors),
            "success_count": len(tutors) - len(failures),
            "failures": failures,
        }
    )


def _process_tutor(
    driver,
    tutor_name: str,
    consultation_after: date,
    class_after: date,
    records: list[dict],
) -> None:
    search_tutor(driver, tutor_name)
    click_sch_button(driver, tutor_name)
    ensure_am_view(driver)

    member_names = collect_am_class_members(driver)

    for member_name in member_names:
        open_member_popup(driver, member_name)
        open_consultation_tab(driver)

        consultation_records = collect_consultation_records(driver)
        credit_count = count_makeup_credits(consultation_records, consultation_after, class_after)

        records.append(
            {
                "tutor": tutor_name,
                "member": member_name,
                "credit_count": credit_count,
            }
        )

        close_member_popup(driver)


def _fail(failures: list[dict], tutor_name: str, reason: str) -> None:
    failures.append({"tutor": tutor_name, "reason": reason})
    emit_progress(tutor_name, "failed", reason=reason)
    emit_log(f"[실패] {tutor_name}: {reason}", level="error")


def _write_to_sheet(records: list[dict]) -> None:
    if not records:
        return
    try:
        worksheet = get_worksheet()
        for record in records:
            append_credit_row(worksheet, record["tutor"], record["member"], record["credit_count"])
    except Exception as exc:  # noqa: BLE001
        emit_log(f"구글 시트 기록 실패: {exc}", level="error")


def _parse_iso_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()
