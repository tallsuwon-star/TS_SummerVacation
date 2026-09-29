"""카드취소 처리 전 확인용: 이메일로 회원을 검색해 LMS의 '상담관리' 화면을
자동으로 열어준다. 담당자가 구글 시트에 적힌 요청자/사유와 상담관리에
기록된 내용, 영수증 첨부 여부가 서로 맞는지 눈으로 직접 대조해야 해서,
그 화면까지 가는 반복적인 클릭 과정만 자동화하고 브라우저는 열어둔 채로
둔다. '중단' 버튼을 누르기 전까지는 창을 닫지 않는다.
"""

import time

from ..control import ControlState
from ..lms.auth import login, LoginFailedError
from ..lms.driver import build_driver
from ..lms.member_search import MemberSearchError, open_member_consultation_by_email
from ..utils.progress import emit_done, emit_log

JOB_NAME = "card_cancel_open_consult"


def run(job_payload: dict, control: ControlState) -> None:
    email = (job_payload.get("memberEmail") or "").strip()
    if not email:
        emit_log("확인할 회원 이메일이 없습니다.", level="error")
        emit_done({"success": False, "error": "missing-email"})
        return

    driver = build_driver()
    opened = False

    try:
        login(driver)
        open_member_consultation_by_email(driver, email)
        opened = True

        emit_log("상담관리 화면을 열었습니다. 브라우저에서 직접 확인해주세요.")
        emit_log("확인이 끝나면 '중단' 버튼을 눌러 이 작업을 종료해주세요.")

        while not control.should_stop():
            control.wait_if_paused()
            time.sleep(0.5)

        emit_log("사용자 요청으로 확인 작업을 종료합니다.")
    except LoginFailedError as exc:
        emit_log(str(exc), level="error")
        emit_done({"success": False, "error": str(exc)})
        return
    except MemberSearchError as exc:
        emit_log(str(exc), level="error")
        emit_done({"success": False, "error": str(exc)})
        return
    finally:
        driver.quit()

    emit_done({"success": opened})
