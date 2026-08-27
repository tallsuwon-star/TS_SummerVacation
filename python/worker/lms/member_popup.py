import time

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from .. import config
from ..utils.progress import emit_log
from .consultation import ConsultationLoadError
from .driver import switch_to_new_window

# 실제 확인된 선택자:
# <button value="이름" onclick="studentPage(...)">이름</button> 또는
# <input type="button" value="이름" onclick="studentPage(...)">
# 둘 다 studentPage()가 window.open()으로 새 팝업을 연다.
CONSULTATION_LINK_TEXT = "상담관리"


class MemberPopupNotOpenedError(Exception):
    pass


def open_member_popup(driver, member_name: str) -> None:
    """회원 이름 클릭 → 팝업 오픈 (studentPage()가 새 창을 연다)."""
    emit_log(f"회원 팝업 열기: {member_name}")

    try:
        member_btn = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    f"//button[@value='{member_name}'] | //input[@type='button' and @value='{member_name}']",
                )
            )
        )
    except TimeoutException as exc:
        raise MemberPopupNotOpenedError(f"'{member_name}' 버튼을 찾지 못했습니다.") from exc

    windows_before = driver.window_handles
    member_btn.click()

    try:
        switch_to_new_window(driver, windows_before)
    except TimeoutException as exc:
        raise MemberPopupNotOpenedError(f"'{member_name}' 팝업이 열리지 않았습니다.") from exc

    time.sleep(config.REQUEST_DELAY_SECONDS)


def open_consultation_tab(driver) -> None:
    """팝업 상단 '상담관리' 버튼 클릭. 이 링크는 새 창이 아니라 같은 팝업 안에서 페이지가 바뀐다."""
    emit_log("상담관리 탭 열기")

    try:
        consultation_link = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, f"//a[normalize-space(text())='{CONSULTATION_LINK_TEXT}']"))
        )
    except TimeoutException as exc:
        raise ConsultationLoadError("'상담관리' 링크를 찾지 못했습니다.") from exc

    consultation_link.click()
    time.sleep(config.REQUEST_DELAY_SECONDS)


def close_member_popup(driver, schedule_window: str) -> None:
    """회원 팝업(현재 창)을 닫고, 다음 회원 처리를 위해 시간표 팝업 창으로 돌아간다."""
    driver.close()
    driver.switch_to.window(schedule_window)
