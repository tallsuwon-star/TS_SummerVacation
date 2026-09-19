"""office/* 모듈 전용 디버깅 저장 헬퍼. 크롤링 결과가 이상할 때(예상보다
0건) 실제 페이지가 어떻게 생겼는지 확인할 수 있도록 스크린샷과 HTML 원본을
log/ 폴더에 남긴다."""

from datetime import datetime

from .. import config
from ..utils.progress import emit_log


def save_debug_snapshot(driver, label: str) -> None:
    try:
        config.LOG_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base = config.LOG_DIR / f"office_{timestamp}_{label}"

        screenshot_path = base.with_suffix(".png")
        driver.save_screenshot(str(screenshot_path))

        html_path = base.with_suffix(".html")
        with html_path.open("w", encoding="utf-8") as f:
            f.write(driver.page_source)

        emit_log(f"디버깅용 스크린샷/HTML을 저장했습니다: {screenshot_path.name}, {html_path.name} (log 폴더)")
    except Exception as exc:  # noqa: BLE001
        emit_log(f"디버깅 스냅샷 저장에 실패했습니다: {exc}", level="error")
