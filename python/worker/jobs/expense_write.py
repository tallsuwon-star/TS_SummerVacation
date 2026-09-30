"""사용자가 검수를 마친 지출결의서 엑셀(오늘 처리한 환불 건)을 읽어,
office.talkstation.co.kr의 지출결의서 작성 화면에 회원별로 거래처/상세/
거래금액을 자동으로 입력해 넣는다.

절대 "제출하기"는 누르지 않는다 — 사용자가 화면에서 직접 확인하고 제출한다.
입력이 끝나도 브라우저는 계속 열어두고, 사용자가 확인을 마친 뒤 '중단'을
누르면 그때 닫는다."""

import time

from ..control import ControlState
from ..lms.driver import build_driver
from ..office import auth as office_auth
from ..office.expense_writer import fill_expense_rows
from ..refund.expense_reader import ExpenseReadError, read_expense_rows
from ..utils.progress import emit_done, emit_log


def run(job_payload: dict, control: ControlState) -> None:
    file_path = job_payload.get("filePath")
    if not file_path:
        emit_log("엑셀 파일을 선택해주세요.", level="error")
        emit_done({"success": False, "error": "missing-file"})
        return

    try:
        rows = read_expense_rows(file_path)
    except ExpenseReadError as exc:
        emit_log(str(exc), level="error")
        emit_done({"success": False, "error": str(exc)})
        return

    if not rows:
        emit_log("엑셀에서 회원 항목을 찾지 못했습니다. 양식이 예상과 다른 것 같습니다.", level="error")
        emit_done({"success": False, "error": "no-rows"})
        return

    emit_log(f"{len(rows)}건을 읽었습니다. office.talkstation.co.kr 지출결의서 작성 화면에 입력을 시작합니다.")

    driver = build_driver()
    try:
        office_auth.login(driver)
        result = fill_expense_rows(driver, rows, control)

        if result.get("error"):
            emit_log(result["error"], level="error")
            emit_done({"success": False, "error": result["error"]})
            return

        emit_log(f"{result['addedCount']}/{len(rows)}건 입력 완료. 화면에서 직접 확인 후 '제출하기'를 눌러주세요.")
        for failed in result["failedRows"]:
            emit_log(f"⚠ 입력하지 못한 항목: {failed}", level="warn")

        emit_log("확인이 끝나면 '중단' 버튼을 눌러 이 작업을 종료해주세요 (브라우저는 그대로 열려 있습니다).")
        while not control.should_stop():
            control.wait_if_paused()
            time.sleep(0.5)
        emit_log("사용자 요청으로 종료합니다.")
    except office_auth.LoginFailedError as exc:
        emit_log(str(exc), level="error")
        emit_done({"success": False, "error": str(exc)})
        return
    except Exception as exc:  # noqa: BLE001
        emit_log(f"입력 중 오류: {exc}", level="error")
        emit_done({"success": False, "error": str(exc)})
        return
    finally:
        driver.quit()

    emit_done(result)
