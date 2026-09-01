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
from ..utils.progress import emit_done, emit_log, emit_progress, emit_record

JOB_NAME = "morning_special_stats"


def run(job_payload: dict, control: ControlState) -> None:
    """오전특강 통계 작업 전체 흐름 (동작 원칙 1~9).

    강사 1명 처리 중 오류가 나도 전체를 멈추지 않고 해당 강사만 실패 처리한 뒤 다음 강사로 진행한다.
    구글 시트는 회원 한 명 처리가 끝날 때마다 바로 한 행씩 기록한다 (중간에 중단되어도 그때까지의
    결과는 시트에 이미 남아있도록).
    """
    tutors: list[str] = job_payload.get("tutors", [])
    consultation_after = _parse_iso_date(job_payload["consultationAfter"])
    class_after = _parse_iso_date(job_payload["classAfter"])

    driver = build_driver()
    records: list[dict] = []
    failures: list[dict] = []
    worksheet = _try_get_worksheet()

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
                _process_tutor(driver, tutor_name, consultation_after, class_after, records, worksheet)
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
    worksheet,
) -> None:
    # 강사 목록 탭(원어민 강사 시간표) - 다음 강사를 검색하려면 반드시 이 탭으로 돌아와 있어야 한다.
    tutor_list_window = driver.current_window_handle

    try:
        search_tutor(driver, tutor_name)
        click_sch_button(driver, tutor_name)
        schedule_window = driver.current_window_handle
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
            emit_record(tutor_name, member_name, credit_count)

            if worksheet is not None:
                try:
                    append_credit_row(worksheet, tutor_name, member_name, credit_count)
                except Exception as exc:  # noqa: BLE001 - 시트 기록 실패해도 나머지 처리는 계속
                    emit_log(f"구글 시트 기록 실패 ({tutor_name}/{member_name}): {exc}", level="error")

            close_member_popup(driver, schedule_window)
    finally:
        # 이 강사 처리 중 어디서 실패하든, 열렸던 SCH/회원 팝업을 전부 닫고 반드시 강사 목록
        # 탭으로 돌아간다. 이걸 안 하면 다음 강사 검색이 엉뚱한(이전 강사의) 팝업 화면에서
        # 시도되어 '강사 검색 실패'가 이어서 계속 발생한다.
        _return_to_tutor_list(driver, tutor_list_window)


def _return_to_tutor_list(driver, tutor_list_window: str) -> None:
    for handle in list(driver.window_handles):
        if handle == tutor_list_window:
            continue
        try:
            driver.switch_to.window(handle)
            driver.close()
        except Exception:  # noqa: BLE001 - 이미 닫혔거나 접근 불가한 창은 무시하고 계속 정리
            pass
    driver.switch_to.window(tutor_list_window)


def _fail(failures: list[dict], tutor_name: str, reason: str) -> None:
    failures.append({"tutor": tutor_name, "reason": reason})
    emit_progress(tutor_name, "failed", reason=reason)
    emit_log(f"[실패] {tutor_name}: {reason}", level="error")


def _try_get_worksheet():
    """구글 시트 인증/연결을 미리 한 번 시도한다. 실패하면 None을 반환하고
    이후 모든 시트 기록은 건너뛴다 (작업 자체는 계속 진행).
    """
    try:
        return get_worksheet()
    except Exception as exc:  # noqa: BLE001
        emit_log(f"구글 시트 연결 실패, 이번 실행은 시트 기록 없이 진행합니다: {exc}", level="error")
        return None


def _parse_iso_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()
