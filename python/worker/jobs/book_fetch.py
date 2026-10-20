"""교재 관리: LMS '교재상품 결제확인' 화면에서 '준비'(미발송) 상태인 건의
받는사람 이름/전화번호/주소와, 실제로 어떤 교재를 주문했는지(교재명)를
조회해 화면 표로 보여준다. 교재명은 참고용 확인 정보일 뿐 엑셀 파일에는
넣지 않는다 — book/xlsx_writer.py의 출력 컬럼은 기존 그대로 유지한다.

이 작업은 조회만 한다. 조회된 내용을 엑셀로 저장하는 것은 사용자가 화면
표를 직접 확인한 뒤 별도로 실행하는 book_generate.py가 맡는다 — 조회
결과를 바로 파일로 쓰지 않고 반드시 사람이 확인하는 단계를 거치게 하기
위해서다.

tutor_search_test.py/card_cancel_open_consult.py와 같은 흐름으로, 사용자가
직접 LMS 화면과 표를 대조할 수 있도록 '중단' 버튼을 누르기 전까지 브라우저
창을 닫지 않는다."""

import time

from ..control import ControlState
from ..lms.auth import LoginFailedError, login
from ..lms.book_charge import (
    BookChargeError,
    book_charge_list_url,
    fetch_order_book_titles,
    fetch_pending_book_orders,
    open_book_charge_list,
)
from ..lms.driver import build_driver
from ..utils.progress import emit_book_record, emit_done, emit_log

JOB_NAME = "book_fetch"


def run(job_payload: dict, control: ControlState) -> None:
    driver = build_driver()

    try:
        login(driver)
        open_book_charge_list(driver)

        try:
            orders = fetch_pending_book_orders(driver)
        except BookChargeError as exc:
            emit_log(str(exc), level="error")
            emit_done({"success": False, "error": str(exc)})
            return

        if not orders:
            emit_log("'준비' 상태인 교재 구매 건이 없습니다.")
        else:
            emit_log(f"'준비' 상태 {len(orders)}건을 찾았습니다. 주문한 교재 정보를 확인하는 중...")
            for i, order in enumerate(orders, start=1):
                if control.should_stop():
                    emit_log("사용자 요청으로 조회를 중단합니다.")
                    break
                control.wait_if_paused()

                try:
                    order["bookTitles"] = fetch_order_book_titles(driver, order["orderId"])
                except BookChargeError as exc:
                    order["bookTitles"] = []
                    emit_log(f"  ⚠ {exc}", level="warn")

                emit_book_record(order)
                emit_log(f"({i}/{len(orders)}) {order['recipientName']}: {', '.join(order['bookTitles']) or '교재명 확인 필요'}")

            driver.get(book_charge_list_url())

        emit_log("확인이 끝나면 '중단' 버튼을 눌러 이 작업을 종료해주세요.")
        while not control.should_stop():
            control.wait_if_paused()
            time.sleep(0.5)

        emit_log("사용자 요청으로 조회 작업을 종료합니다.")
    except LoginFailedError as exc:
        emit_log(str(exc), level="error")
        emit_done({"success": False, "error": str(exc)})
        return
    finally:
        driver.quit()

    emit_done({"success": True})
