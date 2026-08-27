import time

from .. import config
from ..utils.progress import emit_log


class MemberPopupNotOpenedError(Exception):
    pass


def open_member_popup(driver, member_name: str) -> None:
    """회원 이름 클릭 → 팝업 오픈."""
    emit_log(f"회원 팝업 열기: {member_name}")

    # TODO: 회원 이름 클릭 대상 선택자 확정 필요
    # (동일 이름을 가진 회원이 여러 명일 수 있으므로 몇 번째 요소인지 구분 로직 필요할 수 있음)
    # member_link = driver.find_element(By.XPATH, f"//TODO[text()='{member_name}']")
    # member_link.click()

    time.sleep(config.REQUEST_DELAY_SECONDS)

    # TODO: 팝업이 정상적으로 열렸는지 확인하고, 아니면 MemberPopupNotOpenedError를 발생시켜야 한다.
    # if not _popup_is_open(driver):
    #     raise MemberPopupNotOpenedError(member_name)


def open_consultation_tab(driver) -> None:
    """팝업 상단 '상담관리' 버튼 클릭."""
    emit_log("상담관리 탭 열기")

    # TODO: '상담관리' 버튼 선택자 확정 필요
    # consultation_btn = driver.find_element(By.CSS_SELECTOR, "TODO")
    # consultation_btn.click()

    time.sleep(config.REQUEST_DELAY_SECONDS)


def close_member_popup(driver) -> None:
    """다음 회원 처리를 위해 팝업을 닫는다."""
    # TODO: 팝업 닫기 버튼 선택자 확정 필요
    # close_btn = driver.find_element(By.CSS_SELECTOR, "TODO")
    # close_btn.click()
    pass
