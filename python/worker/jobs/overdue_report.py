from calendar import monthrange
from datetime import date, datetime, timedelta

from selenium.common.exceptions import (
    InvalidSessionIdException,
    NoSuchElementException,
    TimeoutException,
    WebDriverException,
)

from ..control import ControlState
from ..lms.auth import login
from ..lms.driver import build_driver
from ..lms.navigation import go_to_daily_settlement_calendar
from ..lms.overdue import search_overdue_count
from ..utils.progress import emit_done, emit_log, emit_progress

JOB_NAME = "overdue_report"
TOTAL_RANGE_START = date(2023, 1, 1)
RECENT_MONTHS_COUNT = 5


def run(job_payload: dict, control: ControlState) -> None:
    """미납자 관리 보고 작업.

    기준일(기본: 어제)까지 최근 5개월(이번 달은 1일~기준일, 이전 4개월은 1일~말일)과,
    2023-01-01부터 기준일까지를 6개월 단위로 쪼갠 구간 각각에 대해 LMS
    '수강료관리 > 일일정산달력' 화면에서 미납자 수를 조회한다.

    조회 구간이 13개 안팎으로 많아 중간에 브라우저가 죽을 수 있으므로,
    morning_special_stats와 동일하게 세션이 끊기면 브라우저를 재시작하고
    같은 구간을 한 번 더 시도한 뒤 이어서 진행한다.
    """
    as_of = _parse_iso_date(job_payload["asOfDate"])

    driver = build_driver()
    monthly_results: list[dict] = []
    semiannual_results: list[dict] = []

    def process_window(start: date, end: date, label: str) -> int | None:
        nonlocal driver
        try:
            count = search_overdue_count(driver, start, end)
            emit_progress(label, "success", found=count)
            return count
        except (NoSuchElementException, TimeoutException) as exc:
            # 셀렉터를 못 찾거나 응답이 늦은 것뿐 브라우저 자체는 살아있는, 평범한
            # 실패 케이스다. NoSuchElementException/TimeoutException은 아래
            # WebDriverException의 하위 클래스라 먼저 잡아주지 않으면 "브라우저
            # 세션이 끊어졌다"로 오진단해서 불필요하게 브라우저를 재시작하게 된다.
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
                login(driver)
                go_to_daily_settlement_calendar(driver)
                emit_log("브라우저 재시작 및 재로그인 완료, 같은 구간을 다시 조회합니다.")
                count = search_overdue_count(driver, start, end)
                emit_progress(label, "success", found=count)
                return count
            except Exception as recovery_exc:  # noqa: BLE001
                emit_log(f"[실패] {label}: 브라우저 재시작 후에도 실패했습니다: {recovery_exc}", level="error")
                emit_progress(label, "failed", reason="브라우저 재시작 후에도 실패")
                return None
        except Exception as exc:  # noqa: BLE001 - 구간 단위 오류도 전체 중단 없이 계속 진행해야 함
            emit_log(f"[실패] {label}: {exc}", level="error")
            emit_progress(label, "failed", reason=str(exc))
            return None

    stopped = False

    try:
        login(driver)
        go_to_daily_settlement_calendar(driver)

        for start, end, label in _recent_monthly_windows(as_of, RECENT_MONTHS_COUNT):
            control.wait_if_paused()
            if control.should_stop():
                emit_log("사용자 요청으로 작업을 중단합니다.")
                stopped = True
                break
            emit_progress(label, "processing")
            count = process_window(start, end, label)
            monthly_results.append({"label": label, "start": start.isoformat(), "end": end.isoformat(), "count": count})

        if not stopped:
            for start, end in _semiannual_windows(TOTAL_RANGE_START, as_of):
                control.wait_if_paused()
                if control.should_stop():
                    emit_log("사용자 요청으로 작업을 중단합니다.")
                    stopped = True
                    break
                label = f"{start.isoformat()}~{end.isoformat()}"
                emit_progress(label, "processing")
                count = process_window(start, end, label)
                semiannual_results.append({"start": start.isoformat(), "end": end.isoformat(), "count": count})
    finally:
        driver.quit()

    total = sum(r["count"] for r in semiannual_results if r["count"] is not None)
    report_text = _format_report(as_of, monthly_results, semiannual_results, total)

    emit_done(
        {
            "asOfDate": as_of.isoformat(),
            "totalRangeStart": TOTAL_RANGE_START.isoformat(),
            "monthly": monthly_results,
            "semiannual": semiannual_results,
            "total": total,
            "reportText": report_text,
            "stopped": stopped,
        }
    )


def _recent_monthly_windows(as_of: date, count: int) -> list[tuple[date, date, str]]:
    """최근 `count`개월 구간을 최신순으로 반환한다.

    이번 달(첫 번째)만 1일~as_of, 이전 달들은 각각 1일~말일 전체.
    예) as_of=2026-09-11 이면
      (2026-09-01, 2026-09-11, "9월"), (2026-08-01, 2026-08-31, "8월"), ...
    """
    windows: list[tuple[date, date, str]] = []
    month_start = date(as_of.year, as_of.month, 1)
    window_end = as_of

    for _ in range(count):
        windows.append((month_start, window_end, f"{month_start.month}월"))
        prev_month_last_day = month_start - timedelta(days=1)
        month_start = date(prev_month_last_day.year, prev_month_last_day.month, 1)
        window_end = prev_month_last_day

    return windows


def _semiannual_windows(start: date, as_of: date) -> list[tuple[date, date]]:
    """start부터 as_of까지를 1~6월/7~12월 단위로 쪼갠 구간 목록 (마지막 구간은 as_of로 자름)."""
    windows: list[tuple[date, date]] = []
    cur_start = start

    while cur_start <= as_of:
        if cur_start.month <= 6:
            cur_end = date(cur_start.year, 6, 30)
        else:
            cur_end = date(cur_start.year, 12, monthrange(cur_start.year, 12)[1])

        if cur_end > as_of:
            cur_end = as_of

        windows.append((cur_start, cur_end))

        if cur_end >= as_of:
            break
        cur_start = cur_end + timedelta(days=1)

    return windows


def _format_report(as_of: date, monthly: list[dict], semiannual: list[dict], total: int) -> str:
    lines = [f"<미납자 보고 - {as_of.strftime('%y.%m.%d')}>"]

    for r in monthly:
        count_str = f"{r['count']}명" if r["count"] is not None else "실패"
        lines.append(f"-{r['label']} : {count_str}")

    total_end = as_of.strftime("%Y.%m.%d")
    total_start = TOTAL_RANGE_START.strftime("%Y.%m.%d")
    lines.append(f"-전체 ({total_start} ~ {total_end}) : {total}명")

    lines.append("")
    lines.append("[6개월 단위 상세]")
    for r in semiannual:
        count_str = f"{r['count']}명" if r["count"] is not None else "실패"
        s = date.fromisoformat(r["start"]).strftime("%Y.%m.%d")
        e = date.fromisoformat(r["end"]).strftime("%Y.%m.%d")
        lines.append(f"-{s}~{e} : {count_str}")

    return "\n".join(lines)


def _parse_iso_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()
