"""검수된 환불 대상 목록으로 실제 "지출결의서" 엑셀 파일을 생성하는 job.

시트를 다시 조회하지 않고, 일렉트론 화면에서 사용자가 이미 확인한(표에
떠 있는) refunds 목록을 그대로 받아 파일로 만든다 — 화면에 보인 것과
실제로 생성되는 파일 내용이 어긋나지 않게 하기 위함이다.

생성된 파일은 로컬(data/refund/output/)에만 저장하고 git에는 올리지 않는다.
"""

from datetime import date

from .. import config
from ..control import ControlState
from ..refund.xlsx_writer import generate_expense_forms
from ..utils.progress import emit_done, emit_log


def run(job_payload: dict, control: ControlState) -> None:
    refunds = job_payload.get("refunds") or []
    preparer_name = (job_payload.get("preparerName") or "").strip()

    if not refunds:
        emit_log("생성할 환불 대상이 없습니다. 먼저 조회를 실행해주세요.", level="error")
        emit_done({"success": False, "error": "no-refunds"})
        return

    if not preparer_name:
        emit_log("담당자 이름이 없습니다.", level="error")
        emit_done({"success": False, "error": "missing-preparer-name"})
        return

    output_dir = config.DATA_DIR / "refund" / "output"

    try:
        output_paths = generate_expense_forms(refunds, preparer_name, output_dir, document_date=date.today())
    except Exception as exc:  # noqa: BLE001 - 파일 생성 오류도 로그로 남기고 종료
        emit_log(f"엑셀 파일 생성 중 오류: {exc}", level="error")
        emit_done({"success": False, "error": str(exc)})
        return

    for path in output_paths:
        emit_log(f"생성 완료: {path.name}")

    emit_done({"success": True, "outputPaths": [str(p) for p in output_paths]})
