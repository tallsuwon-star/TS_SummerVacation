"""택배사 송장 엑셀(이미 업로드해 화면에 떠 있는 행)과 LMS의 '준비' 상태
교재 주문을 전화번호로 대조해, 일치하는 주문의 배송상태를 '배송중'으로
바꾸고 송장번호를 입력해 저장한다.

사용자가 직접 확인해준 절차(주문 상세 화면에서 배송상태 드롭다운을
'배송중'으로, 송장번호 입력, 저장하기 클릭) 그대로 자동화한다. 전화번호가
같은 '준비' 주문이 둘 이상이거나 아예 없으면 자동으로 어떤 걸 고를지
단정하지 않고 "확인 필요"로 남겨 사람이 LMS에서 직접 처리하게 한다 —
엉뚱한 주문을 잘못 배송중 처리하는 사고를 막기 위해서다."""

import re
import time

from ..control import ControlState
from ..lms.auth import LoginFailedError, login
from ..lms.book_charge import (
    BookChargeError,
    book_charge_list_url,
    fetch_pending_book_orders,
    open_book_charge_list,
    set_order_shipped,
)
from ..lms.driver import build_driver
from ..utils.progress import emit_book_mark_shipped_record, emit_done, emit_log


def _normalize_phone(phone: str) -> str:
    return re.sub(r"\D", "", phone or "")


def run(job_payload: dict, control: ControlState) -> None:
    invoice_rows = [
        {
            "recipientName": r.get("recipientName") or "",
            "recipientPhone": r.get("recipientPhone") or "",
            "invoiceNo": (r.get("invoiceNo") or "").strip(),
        }
        for r in (job_payload.get("invoiceRows") or [])
    ]
    if not invoice_rows:
        emit_log("처리할 송장 데이터가 없습니다. 먼저 송장 파일을 업로드해주세요.", level="error")
        emit_done({"success": False, "error": "no-invoice-rows"})
        return

    driver = build_driver()
    processed = 0
    succeeded = 0

    try:
        login(driver)
        open_book_charge_list(driver)

        try:
            pending_orders = fetch_pending_book_orders(driver)
        except BookChargeError as exc:
            emit_log(str(exc), level="error")
            emit_done({"success": False, "error": str(exc)})
            return

        phone_to_orders: dict[str, list[dict]] = {}
        for order in pending_orders:
            phone_to_orders.setdefault(_normalize_phone(order["recipientPhone"]), []).append(order)

        for row in invoice_rows:
            if control.should_stop():
                emit_log("사용자 요청으로 처리를 중단합니다.")
                break
            control.wait_if_paused()

            processed += 1
            phone = _normalize_phone(row["recipientPhone"])
            label = f"{row['recipientName']} ({row['recipientPhone']})"

            if not row["invoiceNo"]:
                emit_book_mark_shipped_record(
                    {**row, "success": False, "reason": "송장번호가 없습니다."}
                )
                emit_log(f"  ⚠ 건너뜀: {label} - 송장번호가 없습니다.", level="warn")
                continue

            candidates = phone_to_orders.get(phone, [])
            if not candidates:
                emit_book_mark_shipped_record(
                    {**row, "success": False, "reason": "전화번호와 일치하는 '준비' 상태 주문을 찾지 못했습니다."}
                )
                emit_log(f"  ⚠ 건너뜀: {label} - 일치하는 '준비' 주문 없음.", level="warn")
                continue
            if len(candidates) > 1:
                emit_book_mark_shipped_record(
                    {
                        **row,
                        "success": False,
                        "reason": f"전화번호가 같은 '준비' 주문이 {len(candidates)}건이라 자동 처리를 건너뜁니다. 직접 확인해주세요.",
                    }
                )
                emit_log(f"  ⚠ 건너뜀: {label} - 전화번호 중복 주문 {len(candidates)}건.", level="warn")
                continue

            order = candidates[0]
            emit_log(f"({processed}/{len(invoice_rows)}) {label} → 주문번호 {order['orderId']} 배송중 처리 중...")
            try:
                set_order_shipped(driver, order["orderId"], row["invoiceNo"])
            except BookChargeError as exc:
                emit_book_mark_shipped_record(
                    {**row, "orderId": order["orderId"], "success": False, "reason": str(exc)}
                )
                emit_log(f"  ⚠ 실패: {label} - {exc}", level="error")
                continue

            succeeded += 1
            emit_book_mark_shipped_record(
                {**row, "orderId": order["orderId"], "success": True, "reason": ""}
            )
            emit_log(f"  ✓ 완료: {label} → 주문번호 {order['orderId']}")

        emit_log(f"{succeeded}/{processed}건을 '배송중'으로 처리했습니다.")

        driver.get(book_charge_list_url())
        emit_log("LMS 교재상품 결제확인 화면에서 결과를 확인해주세요.")
        emit_log("확인이 끝나면 '중단' 버튼을 눌러 이 작업을 종료해주세요.")

        while not control.should_stop():
            control.wait_if_paused()
            time.sleep(0.5)

        emit_log("사용자 요청으로 작업을 종료합니다.")
    except LoginFailedError as exc:
        emit_log(str(exc), level="error")
        emit_done({"success": False, "error": str(exc)})
        return
    finally:
        driver.quit()

    emit_done({"success": True, "processedCount": processed, "succeededCount": succeeded})
