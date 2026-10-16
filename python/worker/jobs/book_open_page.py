"""교재 관리 화면 표에 나온 내용이 맞는지, 사용자가 LMS의 실제
'교재상품 결제확인' 페이지를 직접 띄워 눈으로 대조할 수 있게 하는 전용
작업. 조회(book_fetch)와 달리 아무 것도 읽어오지 않고, 그냥 그 페이지를
열어둔다 — '중단'을 누르기 전까지 창을 닫지 않는다."""

import time

from ..control import ControlState
from ..lms.auth import LoginFailedError, login
from ..lms.book_charge import open_book_charge_list
from ..lms.driver import build_driver
from ..utils.progress import emit_done, emit_log

JOB_NAME = "book_open_page"


def run(job_payload: dict, control: ControlState) -> None:
    driver = build_driver()

    try:
        login(driver)
        open_book_charge_list(driver)

        emit_log("LMS 교재상품 결제확인 화면을 열었습니다. 표의 내용과 대조해주세요.")
        emit_log("확인이 끝나면 '중단' 버튼을 눌러 이 작업을 종료해주세요.")

        while not control.should_stop():
            control.wait_if_paused()
            time.sleep(0.5)

        emit_log("사용자 요청으로 작업을 종료합니다.")
    except LoginFailedError as exc:
        emit_log(str(exc), level="error")
        emit_done({"success": False, "error": str(exc)})
        return
    finally:
        driver.quit()

    emit_done({"success": True})
