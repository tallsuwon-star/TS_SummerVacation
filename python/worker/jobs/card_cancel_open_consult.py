"""카드취소 처리 전 확인용: 체크된 회원들을 순서대로 검색해 LMS의
'상담관리' 화면을 자동으로 열어준다. 담당자가 구글 시트에 적힌 요청자/
사유와 상담관리에 기록된 내용, 영수증 첨부 여부가 서로 맞는지 눈으로
직접 대조해야 해서, 그 화면까지 가는 반복적인 클릭 과정만 자동화한다.

여러 명을 한 번에 체크해서 넘길 수 있어, 회원마다 새 창(팝업)에 상담관리
화면을 열어두고 검색용 메인 창으로 돌아와 다음 회원을 검색하는 식으로
진행한다 — 끝나면 모든 회원의 상담관리 창이 각각 열려있어 옆에 시트를
띄워두고 하나씩 대조할 수 있다. '중단' 버튼을 누르기 전까지는 창을 닫지
않는다.
"""

import time

from ..control import ControlState
from ..lms.auth import login, LoginFailedError
from ..lms.driver import build_driver
from ..lms.member_search import MemberSearchError, open_member_consultation_by_email
from ..utils.progress import emit_done, emit_log

JOB_NAME = "card_cancel_open_consult"


def run(job_payload: dict, control: ControlState) -> None:
    emails = [e.strip() for e in (job_payload.get("memberEmails") or []) if e and e.strip()]
    if not emails:
        emit_log("확인할 회원 이메일이 없습니다.", level="error")
        emit_done({"success": False, "error": "missing-email"})
        return

    driver = build_driver()
    opened_count = 0

    try:
        login(driver)
        main_window = driver.current_window_handle

        for i, email in enumerate(emails, start=1):
            if control.should_stop():
                emit_log("사용자 요청으로 확인 작업을 중단합니다.")
                break
            control.wait_if_paused()

            emit_log(f"({i}/{len(emails)}) 상담관리 화면 여는 중: {email}")
            try:
                driver.switch_to.window(main_window)
                open_member_consultation_by_email(driver, email)
                opened_count += 1
            except MemberSearchError as exc:
                emit_log(f"  ⚠ 건너뜀: {exc}", level="error")
                continue

        if opened_count:
            emit_log(f"{opened_count}명의 상담관리 화면을 열었습니다. 브라우저에서 각 창을 직접 확인해주세요.")
            emit_log("확인이 끝나면 '중단' 버튼을 눌러 이 작업을 종료해주세요.")

            while not control.should_stop():
                control.wait_if_paused()
                time.sleep(0.5)

            emit_log("사용자 요청으로 확인 작업을 종료합니다.")
    except LoginFailedError as exc:
        emit_log(str(exc), level="error")
        emit_done({"success": False, "error": str(exc)})
        return
    finally:
        driver.quit()

    emit_done({"success": opened_count > 0, "openedCount": opened_count})
