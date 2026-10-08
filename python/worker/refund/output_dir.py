"""환불 처리 결과물(지출결의서 엑셀, 상담관리에서 찾은 캡처 스크린샷)을
저장할 날짜별 다운로드 폴더.

하루에 엑셀 생성과 상담 캡처 저장을 각각 몇 번을 하든 같은 날짜 폴더
(예: "26.10.08")에 모이도록, 폴더 이름 규칙을 한 곳에 모아둔다."""

from datetime import date
from pathlib import Path


def dated_output_dir(for_date: date | None = None, base_dir: Path | None = None) -> Path:
    """Path.home()/Downloads/{YY.MM.DD} 폴더를 만들고(이미 있으면 그대로) 반환한다."""
    for_date = for_date or date.today()
    base_dir = base_dir or (Path.home() / "Downloads")
    output_dir = base_dir / for_date.strftime("%y.%m.%d")
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir
