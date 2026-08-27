import time

from .. import config
from ..utils.progress import emit_log


class TutorNotFoundError(Exception):
    pass


class SchButtonNotFoundError(Exception):
    pass


def search_tutor(driver, tutor_name: str) -> None:
    """강사검색 입력창에 강사 이름 입력."""
    emit_log(f"강사 검색: {tutor_name}")

    # TODO: 강사검색 입력창 선택자 확정 필요
    # search_input = driver.find_element(By.CSS_SELECTOR, "TODO")
    # search_input.clear()
    # search_input.send_keys(tutor_name)
    # search_input.send_keys(Keys.ENTER)

    time.sleep(config.REQUEST_DELAY_SECONDS)

    # TODO: 검색 결과가 없을 때 TutorNotFoundError를 발생시켜야 한다.
    # if _no_search_results(driver):
    #     raise TutorNotFoundError(tutor_name)


def click_sch_button(driver, tutor_name: str) -> None:
    """검색된 강사의 SCH 버튼 클릭."""
    emit_log(f"{tutor_name} SCH 버튼 클릭")

    # TODO: 강사 행(row) 내에서 SCH 버튼 선택자 확정 필요
    # sch_btn = driver.find_element(By.CSS_SELECTOR, "TODO")
    # sch_btn.click()

    time.sleep(config.REQUEST_DELAY_SECONDS)

    # TODO: SCH 버튼이 없을 때 SchButtonNotFoundError를 발생시켜야 한다.
    # if _sch_button_missing(driver):
    #     raise SchButtonNotFoundError(tutor_name)
