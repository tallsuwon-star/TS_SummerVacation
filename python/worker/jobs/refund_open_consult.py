"""환불(계좌 환불) 처리 전 확인용: 체크된 회원들을 순서대로 검색해 LMS의
'상담관리' 화면을 열고, 구글 시트의 요청자 이름과 같은 사람이 (시트에 날짜가
있으면 그 날짜와 비슷한 시기에, 없으면 최근에) 작성한 상담 내용 중 "환불"
관련 언급이 있는 글을 찾아 화면에 표로 보여준다.

카드취소 확인(card_cancel_open_consult.py)과 같은 흐름이지만, 환불은 대조할
매출전표가 없어서 금액 일치 여부 대신 키워드 매칭으로 후보를 좁힌다 — 그래서
항상 사람이 detailUrl을 직접 열어 확인해야 한다.

찾은 글에 회원 요청을 캡처한 스크린샷이 있으면, 그 이미지를 다운로드
폴더의 오늘 날짜 폴더(예: Downloads/26.10.08, refund_generate.py가 엑셀을
저장하는 곳과 같은 폴더)에 회원 이름 파일명으로 함께 저장한다. 하루에 같은
회원 이름으로 여러 번 저장되면 "회원명2"처럼 번호를 붙여 겹치지 않게 한다.

이 작업은 조회만 한다 — LMS 페이지의 삭제/수정 링크는 어디서도 클릭하지
않는다. 회원마다 새 창(팝업)에 상담관리 화면을 열어두고 검색용 메인 창으로
돌아와 다음 회원을 검색하는 식으로 진행한다. '중단' 버튼을 누르기 전까지는
창을 닫지 않는다."""

import time
from datetime import date

from ..control import ControlState
from ..lms.auth import LoginFailedError, login
from ..lms.consult_capture import save_consult_capture
from ..lms.driver import build_driver
from ..lms.member_search import MemberSearchError, open_member_consultation_by_email
from ..lms.receipt_check import ReceiptCheckError, find_refund_related_entries
from ..refund.output_dir import dated_output_dir
from ..utils.progress import emit_done, emit_log, emit_refund_consult_record

JOB_NAME = "refund_open_consult"


def _parse_iso_date(text: str) -> date | None:
    if not text:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def run(job_payload: dict, control: ControlState) -> None:
    targets = [
        {
            "memberEmail": (t.get("memberEmail") or "").strip(),
            "memberName": t.get("memberName") or "",
            "requester": (t.get("requester") or "").strip(),
            "requestDate": t.get("requestDate") or "",
        }
        for t in (job_payload.get("targets") or [])
        if (t.get("memberEmail") or "").strip()
    ]
    if not targets:
        emit_log("확인할 회원이 없습니다.", level="error")
        emit_done({"success": False, "error": "missing-target"})
        return

    output_dir = dated_output_dir()
    emit_log(f"캡처 이미지는 {output_dir} 폴더에 저장됩니다.")
    driver = build_driver()
    opened_count = 0

    try:
        login(driver)
        main_window = driver.current_window_handle

        for i, target in enumerate(targets, start=1):
            email = target["memberEmail"]
            requester = target["requester"]
            anchor_date = _parse_iso_date(target["requestDate"])

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
                emit_log("  ⚠ 요청자 이름이 없어 상담 내용 자동 확인은 건너뜁니다. 상담관리 화면을 직접 확인해주세요.", level="warn")
                continue

            try:
                entries = find_refund_related_entries(driver, requester, anchor_date=anchor_date)
            except ReceiptCheckError as exc:
                emit_log(f"  ⚠ 상담 내용 확인 중 오류: {exc}", level="error")
                continue

            if not entries:
                emit_refund_consult_record(
                    {
                        "memberEmail": email,
                        "memberName": target["memberName"],
                        "requester": requester,
                        "found": False,
                        "needsReview": True,
                        "reviewReason": f'"{requester}"님이 작성한 상담 내용 중 날짜가 맞는 글을 찾지 못했습니다.',
                    }
                )
                continue

            member_label = target["memberName"] or email
            for entry in entries:
                if entry["needsReview"]:
                    emit_log(f"  ⚠ 확인 필요: {entry['reviewReason']}", level="warn")

                saved_path = save_consult_capture(driver, entry["detailUrl"], member_label, output_dir)

                emit_refund_consult_record(
                    {
                        "memberEmail": email,
                        "memberName": target["memberName"],
                        "requester": requester,
                        "found": True,
                        "capturePath": str(saved_path) if saved_path else "",
                        **entry,
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
