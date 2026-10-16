"""검수된 교재 배송 대상 목록으로 실제 발송 엑셀 파일을 생성하는 job.

LMS를 다시 조회하지 않고, 일렉트론 화면에서 사용자가 이미 확인한(표에
떠 있는) orders 목록을 그대로 받아 파일로 만든다 — 화면에 보인 것과 실제로
생성되는 파일 내용이 어긋나지 않게 하기 위함이다.

사용자 요청에 따라 환불 결과물과 달리 날짜별 하위 폴더를 만들지 않고,
다운로드 폴더에 바로 "YY.MM.DD.HH.MM 교재 발송.xlsx" 파일로 저장한다."""

from pathlib import Path

from ..book.xlsx_writer import generate_book_shipping_form
from ..control import ControlState
from ..utils.progress import emit_done, emit_log


def run(job_payload: dict, control: ControlState) -> None:
    orders = job_payload.get("orders") or []

    if not orders:
        emit_log("생성할 교재 배송 대상이 없습니다. 먼저 조회를 실행해주세요.", level="error")
        emit_done({"success": False, "error": "no-orders"})
        return

    output_dir = Path.home() / "Downloads"

    try:
        output_path = generate_book_shipping_form(orders, output_dir)
    except Exception as exc:  # noqa: BLE001 - 파일 생성 오류도 로그로 남기고 종료
        emit_log(f"엑셀 파일 생성 중 오류: {exc}", level="error")
        emit_done({"success": False, "error": str(exc)})
        return

    emit_log(f"다운로드 폴더에 저장 완료: {output_path}")
    emit_done({"success": True, "outputPaths": [str(output_path)]})
