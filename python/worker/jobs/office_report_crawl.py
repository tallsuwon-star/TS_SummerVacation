"""업무보고 1회성 크롤링 job. office.talkstation.co.kr에서 지정한 이름으로
검색되는 모든 일일업무보고를 가져와 data/office/reports.json에 저장한다."""

from ..control import ControlState
from ..lms.driver import build_driver
from ..office import auth as office_auth
from ..office import crawler
from ..utils.progress import emit_done, emit_log


def run(job_payload: dict, control: ControlState) -> None:
    target_name = (job_payload.get("targetName") or "").strip()
    if not target_name:
        emit_log("검색할 이름(targetName)이 없습니다.", level="error")
        emit_done({"success": False, "error": "missing-target-name"})
        return

    driver = build_driver(capture_console_logs=True)
    reports: list[dict] = []
    try:
        office_auth.login(driver)
        reports = crawler.crawl_reports(driver, target_name, control)
    except office_auth.LoginFailedError as exc:
        emit_log(str(exc), level="error")
        emit_done({"success": False, "error": str(exc)})
        return
    except Exception as exc:  # noqa: BLE001 - 크롤링 중 예상 못한 오류도 로그로 남기고 종료
        emit_log(f"크롤링 중 오류: {exc}", level="error")
        emit_done({"success": False, "error": str(exc)})
        return
    finally:
        driver.quit()

    path = crawler.save_reports(target_name, reports)
    emit_log(f"{len(reports)}건 저장 완료: {path}")
    emit_done({"success": True, "targetName": target_name, "count": len(reports)})
