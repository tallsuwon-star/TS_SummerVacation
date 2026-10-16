"""택배사 '발송처리' 결과(송장) 엑셀을 업로드하면, 헤더를 뺀 데이터 행을
화면 표로 보여준다.

이 작업은 파일을 읽기만 한다 — 실제 구글 시트 기록은 사용자가 표를
확인하고 "구글 시트에 기록"을 눌러야 진행되는 book_invoice_write.py가
맡는다. 화면에 보인 행(rawRow)을 그 작업이 다시 엑셀을 읽지 않고 그대로
받아 써야, 표에 보인 내용과 실제로 시트에 들어가는 내용이 어긋나지
않는다."""

from ..book.invoice_reader import InvoiceReadError, read_invoice_rows
from ..control import ControlState
from ..utils.progress import emit_book_invoice_record, emit_done, emit_log


def run(job_payload: dict, control: ControlState) -> None:
    file_path = (job_payload.get("filePath") or "").strip()
    if not file_path:
        emit_log("업로드할 송장 엑셀 파일을 선택해주세요.", level="error")
        emit_done({"success": False, "error": "missing-file"})
        return

    try:
        parsed = read_invoice_rows(file_path)
    except InvoiceReadError as exc:
        emit_log(str(exc), level="error")
        emit_done({"success": False, "error": str(exc)})
        return

    rows = parsed["rows"]
    if not rows:
        emit_log("엑셀 파일에 기록할 데이터 행이 없습니다 (헤더만 있음).", level="error")
        emit_done({"success": False, "error": "no-data-rows"})
        return

    for row in rows:
        emit_book_invoice_record(
            {
                "recipientName": str(row[parsed["nameIdx"]] or ""),
                "recipientPhone": str(row[parsed["phoneIdx"]] or ""),
                "recipientAddress": str(row[parsed["addressIdx"]] or ""),
                "invoiceNo": str(row[parsed["invoiceNoIdx"]] or ""),
                "rawRow": row,
            }
        )

    emit_log(f"{len(rows)}건을 읽었습니다. 아래 표를 확인한 뒤 '구글 시트에 기록'을 눌러주세요.")
    emit_done({"success": True, "rowCount": len(rows)})
