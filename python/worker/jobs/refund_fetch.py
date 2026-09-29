"""환불(계좌 환불) 지출결의서 대상 조회 job.

구글 시트의 "계좌 환불 (차액 환불 가능)" 섹션에서 "처리유무" 칸이 주황색
(#FF9900)인 행만 읽어와 회원명/이메일/환불금액/계좌정보(은행별 '-' 포맷)로
화면에 표로 보여준다. 셀레니움 없이 구글 시트 API만 호출하므로 빠르게 끝난다.
"""

from .. import config
from ..control import ControlState
from ..refund.sheet_reader import fetch_pending_refunds
from ..utils.progress import emit_done, emit_log, emit_refund_record


def run(job_payload: dict, control: ControlState) -> None:
    if not config.REFUND_SHEET_ID or not config.GOOGLE_SHEETS_CREDENTIALS_PATH:
        emit_log(
            "환불 시트 연결 정보(REFUND_SHEET_ID / GOOGLE_SHEETS_CREDENTIALS_PATH)가 "
            ".env에 설정되지 않았습니다.",
            level="error",
        )
        emit_done({"success": False, "error": "missing-config"})
        return

    try:
        refunds = fetch_pending_refunds()
    except Exception as exc:  # noqa: BLE001 - 시트 접근/파싱 오류도 로그로 남기고 종료
        emit_log(f"환불 대상 조회 중 오류: {exc}", level="error")
        emit_done({"success": False, "error": str(exc)})
        return

    emit_log(f'"처리유무"가 주황색으로 표시된 환불 대상 {len(refunds)}건을 찾았습니다.')
    for refund in refunds:
        if refund["needsReview"]:
            emit_log(
                f"  ⚠ 확인 필요: {refund['memberName'] or '(이름 미확인)'} - "
                "계좌정보 형식이 예상과 다르거나 은행별 자릿수 구분 규칙을 확인하지 못했습니다.",
                level="warn",
            )
        emit_refund_record(refund)

    emit_done({"success": True, "count": len(refunds)})
