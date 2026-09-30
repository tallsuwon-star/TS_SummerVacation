"""카드취소 처리 전 확인용: 체크된 회원들을 순서대로 검색해 LMS의
'상담관리' 화면을 열고, 구글 시트의 요청자 이름과 같은 사람이 최근(기본
7일 이내) 작성한 상담 내용을 찾아 그 안의 신용카드 매출전표(결제시간/
구매자명/상품정보 등)를 읽어와 화면에 표로 보여준다.

이 작업은 조회만 한다 — LMS 페이지의 삭제/수정 링크는 어디서도 클릭하지
않는다. 매출전표에서 핵심 항목(거래일자/구매자/상품명/승인번호)을 전부
읽어내지 못했거나 조건에 맞는 상담 내용을 아예 못 찾은 경우는 반드시
"확인 필요"로 표시하고, 절대 스스로 "맞다"고 단정하지 않는다 — 사람이
detailUrl을 직접 열어 확인해야 한다.

회원마다 새 창(팝업)에 상담관리 화면을 열어두고 검색용 메인 창으로 돌아와
다음 회원을 검색하는 식으로 진행한다 — 끝나면 모든 회원의 상담관리 창이
각각 열려있어 옆에 시트를 띄워두고 하나씩 대조할 수 있다. '중단' 버튼을
누르기 전까지는 창을 닫지 않는다.
"""

import time

from ..control import ControlState
from ..lms.auth import login, LoginFailedError
from ..lms.driver import build_driver
from ..lms.member_search import MemberSearchError, open_member_consultation_by_email
from ..lms.receipt_check import ReceiptCheckError, check_card_cancel_receipts
from ..utils.progress import emit_done, emit_log, emit_receipt_check_record

JOB_NAME = "card_cancel_open_consult"


def run(job_payload: dict, control: ControlState) -> None:
    targets = [
        {
            "memberEmail": (t.get("memberEmail") or "").strip(),
            "memberName": t.get("memberName") or "",
            "requester": (t.get("requester") or "").strip(),
            "refundAmount": t.get("refundAmount") or "",
        }
        for t in (job_payload.get("targets") or [])
        if (t.get("memberEmail") or "").strip()
    ]
    if not targets:
        emit_log("확인할 회원이 없습니다.", level="error")
        emit_done({"success": False, "error": "missing-target"})
        return

    driver = build_driver()
    opened_count = 0

    try:
        login(driver)
        main_window = driver.current_window_handle

        for i, target in enumerate(targets, start=1):
            email = target["memberEmail"]
            requester = target["requester"]

            if control.should_stop():
                emit_log("사용자 요청으로 확인 작업을 중단합니다.")
                break
            control.wait_if_paused()

            emit_log(f"({i}/{len(targets)}) 상담관리 화면 여는 중: {email}")
            try:
                driver.switch_to.window(main_window)
                open_member_consultation_by_email(driver, email)
                opened_count += 1
            except MemberSearchError as exc:
                emit_log(f"  ⚠ 건너뜀: {exc}", level="error")
                continue

            if not requester:
                emit_log("  ⚠ 요청자 이름이 없어 매출전표 자동 확인은 건너뜁니다. 상담관리 화면을 직접 확인해주세요.", level="warn")
                continue

            try:
                receipts = check_card_cancel_receipts(driver, requester, target["refundAmount"])
            except ReceiptCheckError as exc:
                emit_log(f"  ⚠ 매출전표 확인 중 오류: {exc}", level="error")
                continue

            if not receipts:
                emit_receipt_check_record(
                    {
                        "memberEmail": email,
                        "memberName": target["memberName"],
                        "requester": requester,
                        "found": False,
                        "needsReview": True,
                        "reviewReason": f'최근 7일 이내 "{requester}"님이 작성한 상담 내용을 찾지 못했습니다.',
                    }
                )
                continue

            for receipt in receipts:
                if receipt["needsReview"]:
                    emit_log(f"  ⚠ 확인 필요: {receipt['reviewReason']}", level="warn")
                emit_receipt_check_record(
                    {
                        "memberEmail": email,
                        "memberName": target["memberName"],
                        "requester": requester,
                        "found": True,
                        **receipt,
                    }
                )

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
