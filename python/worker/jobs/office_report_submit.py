"""새 일일업무보고 자동 작성/제출 job. 크롤링해둔 JSON에서 가장 최근 날짜의
항목을 /report/write의 7개 항목에 그대로 채우고 '글쓰기'를 눌러 제출한다."""

from ..control import ControlState
from ..lms.driver import build_driver
from ..office import auth as office_auth
from ..office import crawler
from ..office import writer
from ..utils.progress import emit_done, emit_log


def run(job_payload: dict, control: ControlState) -> None:
    report_date = job_payload.get("reportDate")
    file_paths = job_payload.get("filePaths") or []

    latest = crawler.load_latest_report()
    if latest is None:
        emit_log("크롤링된 데이터가 없습니다. 먼저 '업무보고 크롤링'을 실행해주세요.", level="error")
        emit_done({"success": False, "error": "no-crawled-data"})
        return

    emit_log(f"가장 최근 크롤링 항목(리포트 #{latest.get('report_id')}, {latest.get('report_date')})을 기준으로 채웁니다.")

    # 금일 업무 내용/특이사항은 일렉트론에서 직접 작성 중인 오늘자 초안(진행률 %
    # 포함)이 있으면 크롤링 데이터 대신 그걸 우선 사용한다. 나머지 5개 항목
    # (명일 계획/지난달/이번달/지난주/다음주)은 계속 크롤링 데이터를 그대로 쓴다.
    latest = dict(latest)
    if job_payload.get("dailyWorkOverride"):
        latest["daily_work_report"] = job_payload["dailyWorkOverride"]
    if job_payload.get("issuesOverride"):
        latest["issues"] = job_payload["issuesOverride"]

    driver = build_driver(capture_console_logs=True)
    try:
        office_auth.login(driver)
        result = writer.fill_and_submit(driver, latest, report_date, file_paths)
    except office_auth.LoginFailedError as exc:
        emit_log(str(exc), level="error")
        emit_done({"success": False, "error": str(exc)})
        return
    except Exception as exc:  # noqa: BLE001
        emit_log(f"제출 중 오류: {exc}", level="error")
        emit_done({"success": False, "error": str(exc)})
        return
    finally:
        driver.quit()

    if not result.get("success"):
        emit_log(f"제출 실패: {result.get('error')}", level="error")
    emit_done(result)
