"""여러 기능의 결과물(환불 처리 엑셀/캡처, 교재 배송 엑셀 등)을 저장할
날짜별 다운로드 폴더.

하루에 같은 기능을 몇 번을 실행하든, 서로 다른 기능이라도 같은 날이면
항상 같은 날짜 폴더(예: "26.10.08")에 모이도록, 폴더 이름 규칙을 한 곳에
모아둔다."""

from datetime import date
from pathlib import Path


def dated_output_dir(for_date: date | None = None, base_dir: Path | None = None) -> Path:
    """Path.home()/Downloads/{YY.MM.DD} 폴더를 만들고(이미 있으면 그대로) 반환한다."""
    for_date = for_date or date.today()
    base_dir = base_dir or (Path.home() / "Downloads")
    output_dir = base_dir / for_date.strftime("%y.%m.%d")
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir
