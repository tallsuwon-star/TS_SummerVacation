"""카드취소 대상 조회 job.

구글 시트의 "카드 환불" 섹션에서 "처리유무" 칸이 주황색(#FF9900)인 행만
읽어와 회원명/이메일/요청자/환불금액/사유/내용으로 화면에 표로 보여준다.
계좌이체가 필요 없는 건이라 계좌정보는 다루지 않고, 대신 이 표에서 바로
회원의 상담관리 화면을 열어 시트 기록과 실제 상담 기록을 대조할 수 있게
한다(카드취소 탭의 "상담관리 열기" 버튼, card_cancel_open_consult job).
"""

from ..control import ControlState
from ..refund.sheet_reader import fetch_pending_card_cancellations
from ..utils.progress import emit_card_cancel_record, emit_done, emit_log


def run(job_payload: dict, control: ControlState) -> None:
    try:
        card_cancels = fetch_pending_card_cancellations()
    except Exception as exc:  # noqa: BLE001 - 시트 접근/파싱 오류도 로그로 남기고 종료
        emit_log(f"카드취소 대상 조회 중 오류: {exc}", level="error")
        emit_done({"success": False, "error": str(exc)})
        return

    emit_log(f'"처리유무"가 주황색으로 표시된 카드취소 대상 {len(card_cancels)}건을 찾았습니다.')
    for card_cancel in card_cancels:
        emit_card_cancel_record(card_cancel)

    emit_done({"success": True, "count": len(card_cancels)})
