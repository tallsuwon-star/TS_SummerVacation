"""검수된 택배사 송장 행들을 구글 시트(환불/카드취소 시트와 같은
스프레드시트, 사용자가 알려준 탭 gid=760310768)의 현재 마지막 데이터 행
바로 다음 줄에 그대로 이어붙인다.

book_invoice_parse.py가 화면에 보여준 표의 행(rawRow)을 그대로 받아
쓴다 — 다시 엑셀을 읽지 않는다. 이 스프레드시트에 서비스 계정 이메일이
'편집자'로 공유돼 있어야 쓰기가 된다 (.env의
GOOGLE_SHEETS_CREDENTIALS_PATH에 적힌 JSON 파일의 client_email)."""

from pathlib import Path

from .. import config
from ..control import ControlState
from ..sheets import gsheet_client
from ..utils.progress import emit_done, emit_log

# 사용자가 알려준 시트 링크(.../edit?gid=760310768)의 탭 번호. 탭 이름이
# 바뀌어도 gid는 바뀌지 않아 이 값으로 정확한 탭을 찾는다.
TARGET_SHEET_GID = 760310768


def run(job_payload: dict, control: ControlState) -> None:
    rows = job_payload.get("rows") or []
    if not rows:
        emit_log("구글 시트에 기록할 데이터가 없습니다. 먼저 송장 파일을 업로드해주세요.", level="error")
        emit_done({"success": False, "error": "no-rows"})
        return

    if not config.GOOGLE_SHEETS_CREDENTIALS_PATH or not Path(config.GOOGLE_SHEETS_CREDENTIALS_PATH).exists():
        emit_log(
            "구글 시트 서비스 계정 인증 파일을 찾지 못했습니다. "
            ".env의 GOOGLE_SHEETS_CREDENTIALS_PATH 경로를 확인해주세요.",
            level="error",
        )
        emit_done({"success": False, "error": "missing-credentials"})
        return

    try:
        worksheet = gsheet_client.get_worksheet_by_gid(config.REFUND_SHEET_ID, TARGET_SHEET_GID)
        gsheet_client.append_rows(worksheet, rows)
    except Exception as exc:  # noqa: BLE001 - 권한/네트워크 오류도 로그로 남기고 종료
        emit_log(
            f"구글 시트 기록 중 오류: {exc} "
            "(이 스프레드시트에 서비스 계정 이메일이 '편집자'로 공유돼 있는지 확인해주세요.)",
            level="error",
        )
        emit_done({"success": False, "error": str(exc)})
        return

    emit_log(f"구글 시트에 {len(rows)}건을 기록했습니다.")
    emit_done({"success": True, "writtenCount": len(rows)})
