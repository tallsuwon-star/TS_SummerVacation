"""네이버 스마트스토어 "항목별 정산 내역" 원본 엑셀을 업로드하면, 제출용
형식(필요한 컬럼만 + 정산예정금액 + 날짜별 소계 + 전체 합계)으로 정리한
행을 화면 표로 보여준다.

이 작업은 읽기만 한다 — 실제 엑셀 저장은 사용자가 표를 확인한 뒤 눌러야
하는 naver_settlement_generate.py가 맡는다."""

from ..control import ControlState
from ..settlement.xlsx_processor import SettlementReadError, build_settlement_rows
from ..utils.progress import emit_done, emit_log, emit_naver_settlement_record


def run(job_payload: dict, control: ControlState) -> None:
    file_path = (job_payload.get("filePath") or "").strip()
    if not file_path:
        emit_log("정산 내역 엑셀 파일을 선택해주세요.", level="error")
        emit_done({"success": False, "error": "missing-file"})
        return

    try:
        rows = build_settlement_rows(file_path)
    except SettlementReadError as exc:
        emit_log(str(exc), level="error")
        emit_done({"success": False, "error": str(exc)})
        return

    for row in rows:
        emit_naver_settlement_record(row)

    data_count = sum(1 for r in rows if r["rowType"] == "data")
    subtotal_count = sum(1 for r in rows if r["rowType"] == "subtotal")
    emit_log(f"{data_count}건을 읽었습니다 ({subtotal_count}개 날짜). 아래 표를 확인한 뒤 '엑셀로 저장'을 눌러주세요.")
    emit_done({"success": True, "rowCount": len(rows)})
