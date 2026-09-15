"""Shared debug-screenshot helper for the naver/* modules."""

from datetime import datetime

from .. import config
from ..utils.progress import emit_log


def save_debug_screenshot(driver, label: str) -> None:
    try:
        config.LOG_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = config.LOG_DIR / f"naver_store_{timestamp}_{label}.png"
        driver.save_screenshot(str(path))
        emit_log(f"디버깅용 스크린샷을 저장했습니다: {path}")
    except Exception as exc:  # noqa: BLE001
        emit_log(f"스크린샷 저장에 실패했습니다: {exc}", level="error")
