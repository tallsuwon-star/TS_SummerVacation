"""검수된 교재 배송 대상 목록으로 실제 발송 엑셀 파일을 만든다.

사용자가 준 참고 파일과 정확히 같은 구조(헤더: 받는분성명/받는분전화번호/
받는분주소(전체, 분할)/품목명, 그 외 서식 없음)로, 매번 새 워크북을 만들어
값만 채운다. '품목명' 칸은 항상 고정 텍스트 '서적'이다.

파일명은 사용자가 요청한 그대로 "YY.MM.DD.HH.MM 교재 발송.xlsx" 형식으로
만든다(예: "26.10.16.10.10 교재 발송.xlsx"). 콜론(:)은 Windows 파일명에
쓸 수 없어 시/분 구분에도 마침표를 쓴다."""

from datetime import datetime
from pathlib import Path

import openpyxl

HEADERS = ["받는분성명", "받는분전화번호", "받는분주소(전체, 분할)", "품목명"]
ITEM_NAME = "서적"


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


def generate_book_shipping_form(orders: list[dict], output_dir: Path) -> Path:
    """orders(각 건 recipientName/recipientPhone/recipientAddress)로 교재
    발송 엑셀을 만들어 output_dir에 저장하고 그 경로를 반환한다."""
    output_dir.mkdir(parents=True, exist_ok=True)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Sheet1"
    ws.append(HEADERS)

    for order in orders:
        ws.append(
            [
                order.get("recipientName", ""),
                order.get("recipientPhone", ""),
                order.get("recipientAddress", ""),
                ITEM_NAME,
            ]
        )

    filename = f"{datetime.now().strftime('%y.%m.%d.%H.%M')} 교재 발송.xlsx"
    output_path = _unique_path(output_dir, filename)
    wb.save(output_path)
    return output_path
