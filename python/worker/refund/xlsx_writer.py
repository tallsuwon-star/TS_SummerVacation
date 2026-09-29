"""검수된 환불 대상 목록으로 실제 "지출결의서" 엑셀 파일을 만든다.

사용자가 준 실제 양식 파일(python/worker/refund/template/refund_expense_form.xlsx,
예시로 채워져 있던 개인정보는 전부 지우고 서식만 남긴 클린 버전)을 그대로
열어 값만 채운 뒤 다른 이름으로 저장한다 — 폰트/정렬/병합/숫자서식 등은
템플릿에 이미 들어있는 것을 그대로 쓰고 건드리지 않는다.

양식은 22건까지 한 장에 들어가는 구조(8~51행, 2행씩 22칸)라 그보다 많으면
여러 장으로 나눠 만든다.
"""

import re
from datetime import date
from pathlib import Path

import openpyxl

TEMPLATE_PATH = Path(__file__).resolve().parent / "template" / "refund_expense_form.xlsx"
SHEET_NAME = "운영팀 수강료 환불 지출결의서"

FIRST_SLOT_ROW = 8
SLOT_ROW_SPAN = 2
MAX_SLOTS_PER_SHEET = 22

TOTAL_ROW = 52
DATE_ROW = 55
CLAIMANT_ROW = 56
PREPARER_ROW = 6


def _parse_amount(raw: str) -> int:
    digits = re.sub(r"[^\d]", "", raw or "")
    return int(digits) if digits else 0


def _format_korean_date(d: date) -> str:
    return f"{d.year}년  {d.month}월  {d.day}일"


def _member_line(refund: dict) -> str:
    reason = (refund.get("memo") or "").strip()
    name = refund.get("memberName") or ""
    email = refund.get("memberEmail") or ""
    line = f"{name}  ( {email} )"
    if reason:
        line += f" / {reason}"
    return line


def _account_line(refund: dict) -> str:
    bank = refund.get("bankName") or ""
    account_number = refund.get("accountNumberFormatted") or ""
    holder = refund.get("accountHolder") or ""
    return f"{bank} {account_number} / 예금주 : {holder}".strip()


def generate_expense_forms(
    refunds: list[dict],
    preparer_name: str,
    output_dir: Path,
    document_date: date | None = None,
) -> list[Path]:
    """refunds를 MAX_SLOTS_PER_SHEET건씩 나눠 지출결의서 엑셀 파일(들)을 만들고
    저장된 경로 목록을 반환한다."""
    document_date = document_date or date.today()
    output_dir.mkdir(parents=True, exist_ok=True)

    chunks = [
        refunds[i : i + MAX_SLOTS_PER_SHEET] for i in range(0, len(refunds), MAX_SLOTS_PER_SHEET)
    ] or [[]]

    output_paths: list[Path] = []
    for chunk_idx, chunk in enumerate(chunks, start=1):
        suffix = f"_{chunk_idx}" if len(chunks) > 1 else ""
        filename = f"지출결의서_{document_date.strftime('%Y%m%d')}{suffix}.xlsx"
        output_path = output_dir / filename
        _write_single_form(chunk, preparer_name, document_date, output_path)
        output_paths.append(output_path)

    return output_paths


def _write_single_form(chunk: list[dict], preparer_name: str, document_date: date, output_path: Path) -> None:
    wb = openpyxl.load_workbook(TEMPLATE_PATH)
    ws = wb[SHEET_NAME]

    ws[f"D{PREPARER_ROW}"] = f"담당 : {preparer_name}"

    total = 0
    for i, refund in enumerate(chunk):
        top_row = FIRST_SLOT_ROW + i * SLOT_ROW_SPAN
        bottom_row = top_row + 1

        ws[f"C{top_row}"] = _member_line(refund)
        ws[f"C{bottom_row}"] = _account_line(refund)

        amount = _parse_amount(refund.get("refundAmount", ""))
        ws[f"D{top_row}"] = amount
        total += amount

    ws[f"D{TOTAL_ROW}"] = total
    ws[f"C{DATE_ROW}"] = _format_korean_date(document_date)
    ws[f"D{CLAIMANT_ROW}"] = f"청구자 :   {preparer_name}"

    wb.save(output_path)
