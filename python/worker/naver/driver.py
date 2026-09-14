"""Naver Smart Store 전용 Chrome 드라이버.

다른 LMS 작업들과 달리, 매번 새로 캡챠를 받지 않으려면 로그인 세션(쿠키)을
디스크에 유지해야 하고, 이후 발송처리 엑셀도 내려받아야 하므로
영구 user-data-dir + 고정 다운로드 폴더를 사용한다. headless는 여기서도 금지
(자동 제어 중인 크롬 창을 사람이 보고 캡챠 등을 직접 처리해야 한다).
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from .. import config


def build_driver() -> webdriver.Chrome:
    config.NAVER_CHROME_PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    config.NAVER_DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

    options = Options()
    options.add_argument(f"--user-data-dir={config.NAVER_CHROME_PROFILE_DIR}")
    options.add_argument("--start-maximized")
    options.add_argument("--lang=ko-KR")
    options.add_experimental_option("excludeSwitches", ["enable-logging"])
    options.add_experimental_option(
        "prefs",
        {
            "download.default_directory": str(config.NAVER_DOWNLOAD_DIR),
            "download.prompt_for_download": False,
            "safebrowsing.enabled": True,
        },
    )

    # Selenium 4.6+ 의 Selenium Manager가 chromedriver를 자동으로 관리한다.
    return webdriver.Chrome(options=options)
