from ..control import ControlState
from ..naver.auth import LoginFailedError, login
from ..naver.driver import build_driver
from ..naver.smartstore import go_to_delivery_page
from ..utils.backup import save_backup
from ..utils.progress import emit_done, emit_log, emit_progress

JOB_NAME = "naver_store_report"


def run(job_payload: dict, control: ControlState) -> None:
    """네이버 스마트스토어 발주(주문)확인/발송관리 페이지 진입 작업.

    아직은 로그인 + 페이지 진입까지만 확인하는 단계다 (테스트 단계).
    엑셀 다운로드 -> 파싱 -> 구글 시트 기록은 다음 단계에서 추가한다.
    """
    driver = build_driver()
    logged_in = False
    reached = False

    try:
        control.wait_if_paused()
        if control.should_stop():
            emit_log("사용자 요청으로 작업을 시작하기 전에 중단합니다.")
            emit_done({"stopped": True, "loggedIn": False, "reachedDeliveryPage": False})
            return

        emit_progress("로그인", "processing")
        try:
            logged_in = login(driver, control)
        except LoginFailedError as exc:
            emit_log(f"로그인 실패: {exc}", level="error")
            emit_progress("로그인", "failed", reason=str(exc))
            emit_done({"stopped": False, "loggedIn": False, "reachedDeliveryPage": False})
            return

        if not logged_in:
            emit_progress("로그인", "failed", reason="로그인이 완료되지 않았습니다.")
            emit_done({"stopped": False, "loggedIn": False, "reachedDeliveryPage": False})
            return
        emit_progress("로그인", "success")

        control.wait_if_paused()
        if control.should_stop():
            emit_log("사용자 요청으로 작업을 중단합니다.")
            emit_done({"stopped": True, "loggedIn": True, "reachedDeliveryPage": False})
            return

        emit_progress("발주(주문)확인/발송관리", "processing")
        reached = go_to_delivery_page(driver)
        emit_progress("발주(주문)확인/발송관리", "success" if reached else "failed")
    finally:
        driver.quit()

    result = {
        "stopped": False,
        "loggedIn": logged_in,
        "reachedDeliveryPage": reached,
        # TODO: 엑셀 다운로드 -> 파싱 -> 구글 시트 기록
        # (발송처리 화면의 "엑셀 다운로드" 버튼 실제 HTML을 받은 뒤 구현)
    }
    save_backup(JOB_NAME, [result])
    emit_done(result)
