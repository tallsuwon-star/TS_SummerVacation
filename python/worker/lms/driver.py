from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait


def build_driver() -> webdriver.Chrome:
    """항상 화면에 보이는 크롬으로 실행한다 (headless 금지).
    Selenium 4.6+ 의 Selenium Manager가 chromedriver를 자동으로 관리한다.
    """
    options = Options()
    options.add_argument("--start-maximized")
    # TODO: 필요 시 사용자 프로필 경로, 다운로드 경로 등 옵션 추가

    return webdriver.Chrome(options=options)


def switch_to_new_window(driver, windows_before: list[str], timeout: float = 10) -> str:
    """LMS 곳곳의 window.open() 팝업(원어민 강사 시간표, SCH, 회원 클릭 등) 공통 처리.
    클릭 직전의 window_handles 목록을 받아, 새로 열린 창으로 전환하고 그 handle을 반환한다.
    """
    WebDriverWait(driver, timeout).until(lambda d: len(d.window_handles) > len(windows_before))
    new_window = next(w for w in driver.window_handles if w not in windows_before)
    driver.switch_to.window(new_window)
    return new_window
