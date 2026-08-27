import time

from .. import config
from ..utils.progress import emit_log


def go_to_native_tutor_schedule(driver) -> None:
    """시간표관리 → 원어민 강사 시간표 (하위 메뉴 토글)."""
    emit_log("시간표관리 > 원어민 강사 시간표 이동")

    # TODO: '시간표관리' 상위 메뉴 선택자 확정 필요
    # timetable_menu = driver.find_element(By.CSS_SELECTOR, "TODO")
    # timetable_menu.click()
    time.sleep(config.REQUEST_DELAY_SECONDS)

    # TODO: '원어민 강사 시간표' 하위 메뉴 선택자 확정 필요 (하위 메뉴 토글 후 노출)
    # native_tutor_submenu = driver.find_element(By.CSS_SELECTOR, "TODO")
    # native_tutor_submenu.click()
    time.sleep(config.REQUEST_DELAY_SECONDS)
