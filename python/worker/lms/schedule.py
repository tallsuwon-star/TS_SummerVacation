import time

from .. import config
from ..utils.progress import emit_log


def ensure_am_view(driver) -> None:
    """기본 화면이 '오후'로 표시되어 있으면 '오전'으로 토글 전환한다."""
    emit_log("오전/오후 화면 확인")

    # TODO: 오전/오후 토글 현재 상태를 읽는 선택자 확정 필요
    # current_view = driver.find_element(By.CSS_SELECTOR, "TODO").text

    # TODO: '오후'로 표시되어 있으면 '오전' 토글 버튼 클릭
    # if current_view == "오후":
    #     am_toggle_btn = driver.find_element(By.CSS_SELECTOR, "TODO")
    #     am_toggle_btn.click()
    #     time.sleep(config.REQUEST_DELAY_SECONDS)


def collect_am_class_members(driver) -> list[str]:
    """10:00~13:00 수업을 확인하고, 그중 10:00~12:30 시작 수업들에서 회원 이름 전체를 수집한다."""
    emit_log("오전 수업(10:00~12:30 시작) 회원 명단 수집")

    member_names: list[str] = []

    # TODO: 10:00~13:00 시간대 수업 블록 목록 선택자 확정 필요
    # class_blocks = driver.find_elements(By.CSS_SELECTOR, "TODO")
    # for block in class_blocks:
    #     class_time_text = block.find_element(By.CSS_SELECTOR, "TODO").text
    #     if not _starts_between_10_and_1230(class_time_text):
    #         continue
    #     name_elements = block.find_elements(By.CSS_SELECTOR, "TODO")
    #     member_names.extend(el.text for el in name_elements)

    return member_names


def _starts_between_10_and_1230(class_time_text: str) -> bool:
    """수업 시작 시각이 10:00~12:30 사이인지 판정.
    TODO: 실제 화면의 시간 텍스트 포맷(예: '10:30~11:00')을 확인한 뒤 파싱 로직 구현.
    """
    raise NotImplementedError("TODO: 실제 시간 텍스트 포맷을 확인한 뒤 구현")
