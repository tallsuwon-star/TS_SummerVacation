"""검수된 환불 대상 목록으로 실제 "지출결의서" 엑셀 파일을 생성하는 job.

시트를 다시 조회하지 않고, 일렉트론 화면에서 사용자가 이미 확인한(표에
떠 있는) refunds 목록을 그대로 받아 파일로 만든다 — 화면에 보인 것과
실제로 생성되는 파일 내용이 어긋나지 않게 하기 위함이다.

생성된 파일은 곧바로 사용자의 실제 "다운로드" 폴더 아래 오늘 날짜 폴더
(예: Downloads/26.10.08)에 저장한다 — 일렉트론 쪽의 저장 대화상자/탐색기
열기에 의존하지 않고 파이썬이 직접 써서, 그 파일을 바로 찾아 쓸 수 있게
한다. 같은 날 상담관리에서 찾은 회원 요청 캡처 스크린샷(refund_open_consult.py)도
이 폴더에 함께 저장되니, 엑셀과 캡처를 날짜별로 한곳에서 볼 수 있다.
git에는 올라가지 않는다."""

from datetime import date

from ..control import ControlState
from ..refund.output_dir import dated_output_dir
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

    output_dir = dated_output_dir()

    try:
        output_paths = generate_expense_forms(refunds, preparer_name, output_dir, document_date=date.today())
    except Exception as exc:  # noqa: BLE001 - 파일 생성 오류도 로그로 남기고 종료
        emit_log(f"엑셀 파일 생성 중 오류: {exc}", level="error")
        emit_done({"success": False, "error": str(exc)})
        return

    for path in output_paths:
        emit_log(f"다운로드 폴더에 저장 완료: {path}")

    emit_done({"success": True, "outputPaths": [str(p) for p in output_paths]})
