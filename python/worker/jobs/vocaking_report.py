from datetime import date

from selenium.common.exceptions import (
    InvalidSessionIdException,
    NoSuchElementException,
    TimeoutException,
    WebDriverException,
)

from ..control import ControlState
from ..lms.auth import login
from ..lms.driver import build_driver
from ..lms.navigation import go_to_integrated_lms
from ..lms.vocaking import (
    LIST_TYPE_LABEL,
    VocakingListError,
    WEEK_LABEL,
    click_charged_student_list,
    click_vocaking_tab,
    fetch_all_charged_students,
    is_suspicious_name,
)
from ..utils.progress import emit_done, emit_log, emit_progress

JOB_NAME = "vocaking_report"
WEEK_COUNTS = [2, 3, 5]
LIST_TYPES = ["free", "paid"]


def run(job_payload: dict, control: ControlState) -> None:
    """보카킹 보고 작업.

    무료/유료 x 주2/3/5회, 총 6개 조합의 회원 목록을 전부 페이지 순회하며
    수집한다. 이름이 실제 사람 이름처럼 보이지 않는 계정(테스트/가짜 계정
    의심)은 별도로 걸러내 목록으로 보여주고, 최종 인원수에서는 제외한다.

    조회량이 많아(6개 목록 x 여러 페이지) 중간에 브라우저가 죽을 수 있으므로,
    다른 작업들과 동일하게 세션이 끊기면 브라우저를 재시작하고 로그인부터
    다시 해서 같은 목록을 재시도한 뒤 이어서 진행한다.
    """
    class_month = date.today().strftime("%Y-%m")
    driver = build_driver()
    results: dict[tuple[str, int], dict] = {}

    def reauth_to_charged_list() -> None:
        login(driver)
        go_to_integrated_lms(driver)
        click_vocaking_tab(driver)
        click_charged_student_list(driver)

    def combo_label(list_type: str, week_cnt: int) -> str:
        return f"{LIST_TYPE_LABEL.get(list_type, list_type)} {WEEK_LABEL.get(week_cnt, f'주{week_cnt}회')}"

    def process_combo(list_type: str, week_cnt: int):
        nonlocal driver
        label = combo_label(list_type, week_cnt)

        try:
            total, members = fetch_all_charged_students(driver, list_type, week_cnt, class_month)
        except (NoSuchElementException, TimeoutException, VocakingListError) as exc:
            # 셀렉터를 못 찾거나 응답이 늦은 것뿐, 브라우저 자체는 살아있는 평범한 실패.
            emit_log(f"[실패] {label}: {exc}", level="error")
            emit_progress(label, "failed", reason=str(exc))
            return None
        except (InvalidSessionIdException, WebDriverException) as exc:
            emit_log(f"브라우저 세션이 끊어졌습니다. 재시작을 시도합니다: {exc}", level="error")
            try:
                try:
                    driver.quit()
                except Exception:  # noqa: BLE001 - 이미 죽은 드라이버 종료 시도는 무시
                    pass
                driver = build_driver()
                reauth_to_charged_list()
                emit_log("브라우저 재시작 및 재로그인 완료, 같은 목록을 다시 조회합니다.")
                total, members = fetch_all_charged_students(driver, list_type, week_cnt, class_month)
            except Exception as recovery_exc:  # noqa: BLE001
                emit_log(f"[실패] {label}: 브라우저 재시작 후에도 실패했습니다: {recovery_exc}", level="error")
                emit_progress(label, "failed", reason="브라우저 재시작 후에도 실패")
                return None
        except Exception as exc:  # noqa: BLE001 - 조합 단위 오류도 전체 중단 없이 계속 진행해야 함
            emit_log(f"[실패] {label}: {exc}", level="error")
            emit_progress(label, "failed", reason=str(exc))
            return None

        suspicious = [(kr, en) for kr, en in members if is_suspicious_name(kr, en)]
        clean_count = total - len(suspicious)

        emit_log(f"[{label}] 전체 {total}명 / 의심 {len(suspicious)}명 제외 / 실제 {clean_count}명")
        for kr, en in suspicious:
            emit_log(f"  ⚠ 의심 계정: {kr}" + (f" ({en})" if en else ""))

        emit_progress(label, "success", found=clean_count)
        return {"total": total, "suspicious": suspicious, "clean_count": clean_count}

    stopped = False

    try:
        login(driver)
        go_to_integrated_lms(driver)
        click_vocaking_tab(driver)
        click_charged_student_list(driver)

        for list_type in LIST_TYPES:
            if stopped:
                break
            for week_cnt in WEEK_COUNTS:
                control.wait_if_paused()
                if control.should_stop():
                    emit_log("사용자 요청으로 작업을 중단합니다.")
                    stopped = True
                    break

                label = combo_label(list_type, week_cnt)
                emit_progress(label, "processing")
                result = process_combo(list_type, week_cnt)
                if result is not None:
                    results[(list_type, week_cnt)] = result
    finally:
        driver.quit()

    report_text = _format_report(results)

    emit_done(
        {
            "classMonth": class_month,
            "results": {
                f"{list_type}_{week_cnt}": {
                    "total": data["total"],
                    "cleanCount": data["clean_count"],
                    "suspicious": [{"name": kr, "engName": en} for kr, en in data["suspicious"]],
                }
                for (list_type, week_cnt), data in results.items()
            },
            "reportText": report_text,
            "stopped": stopped,
        }
    )


def _format_report(results: dict) -> str:
    lines = [f"<보카킹 보고 - {date.today().strftime('%y.%m.%d')}>"]

    grand_total = 0
    grand_clean = 0

    for list_type in LIST_TYPES:
        section_total = 0
        section_clean = 0
        section_lines = []

        for week_cnt in WEEK_COUNTS:
            data = results.get((list_type, week_cnt))
            if data is None:
                section_lines.append(f"{WEEK_LABEL[week_cnt]} : 실패")
                continue

            section_total += data["total"]
            section_clean += data["clean_count"]

            if data["suspicious"]:
                section_lines.append(
                    f"{WEEK_LABEL[week_cnt]} : {data['clean_count']}명 "
                    f"(전체 {data['total']}명 중 의심 {len(data['suspicious'])}명 제외)"
                )
            else:
                section_lines.append(f"{WEEK_LABEL[week_cnt]} : {data['clean_count']}명")

        lines.append("")
        lines.append(f"{LIST_TYPE_LABEL[list_type]} 수강인원")
        count_line = f"{section_clean}명"
        if section_clean != section_total:
            count_line += f" (전체 {section_total}명)"
        lines.append(count_line)
        lines.extend(section_lines)

        grand_total += section_total
        grand_clean += section_clean

    lines.append("")
    lines.append("총인원")
    total_line = f"{grand_clean}명"
    if grand_clean != grand_total:
        total_line += f" (전체 {grand_total}명)"
    lines.append(total_line)

    suspicious_all = []
    for (list_type, week_cnt), data in results.items():
        label = f"{LIST_TYPE_LABEL[list_type]} {WEEK_LABEL[week_cnt]}"
        for kr, en in data["suspicious"]:
            suspicious_all.append(f"- [{label}] {kr}" + (f" ({en})" if en else ""))

    if suspicious_all:
        lines.append("")
        lines.append("[의심 계정 목록 - 직접 확인 필요]")
        lines.extend(suspicious_all)

    return "\n".join(lines)
