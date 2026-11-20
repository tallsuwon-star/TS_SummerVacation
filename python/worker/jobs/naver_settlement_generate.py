"""검수된 네이버 정산 정리 표를 실제 엑셀 파일로 저장하는 job.

naver_settlement_parse.py가 화면에 보여준 행을 다시 읽지 않고 그대로
받아 쓴다 — 화면에서 확인한 내용과 실제로 저장되는 내용이 어긋나지 않게
하기 위함이다. 다운로드 폴더에 바로 저장한다(최근 추가한 교재 발송
기능과 같은 방식 — 날짜별 하위 폴더 없이 파일명에 월 정보를 담음)."""

import re
from datetime import date
from pathlib import Path

from ..control import ControlState
from ..settlement.xlsx_processor import write_settlement_rows
from ..utils.progress import emit_done, emit_log

_YEAR_MONTH_RE = re.compile(r"^(\d{4})\.(\d{1,2})")


def _guess_year_month(rows: list[dict]) -> str:
    """표의 첫 데이터 행 정산완료일에서 "YYYY.MM"을 뽑는다. 못 찾으면
    오늘 날짜 기준으로 대신한다 — 파일명에만 쓰이는 값이라 추측해도
    안전하다."""
    for row in rows:
        if row.get("rowType") != "data":
            continue
        text = str(row.get("settleDate") or "")
        match = _YEAR_MONTH_RE.match(text)
        if match:
            year, month = match.groups()
            return f"{year}.{int(month):02d}"
        break

    today = date.today()
    return f"{today.year}.{today.month:02d}"


def _unique_path(output_dir: Path, filename: str) -> Path:
    candidate = output_dir / filename
    if not candidate.exists():
        return candidate

    stem, suffix = candidate.stem, candidate.suffix
    n = 2
    while True:
        candidate = output_dir / f"{stem}_{n}{suffix}"
        if not candidate.exists():
            return candidate
        n += 1


def run(job_payload: dict, control: ControlState) -> None:
    rows = job_payload.get("rows") or []
    if not rows:
        emit_log("저장할 정산 정리 데이터가 없습니다. 먼저 파일을 업로드해주세요.", level="error")
        emit_done({"success": False, "error": "no-rows"})
        return

    output_dir = Path.home() / "Downloads"
    year_month = _guess_year_month(rows)
    filename = f"네이버정산정리_{year_month}.xlsx"
    output_path = _unique_path(output_dir, filename)

    try:
        write_settlement_rows(rows, output_path)
    except Exception as exc:  # noqa: BLE001 - 파일 생성 오류도 로그로 남기고 종료
        emit_log(f"엑셀 파일 생성 중 오류: {exc}", level="error")
        emit_done({"success": False, "error": str(exc)})
        return

    emit_log(f"다운로드 폴더에 저장 완료: {output_path}")
    emit_done({"success": True, "outputPaths": [str(output_path)]})
