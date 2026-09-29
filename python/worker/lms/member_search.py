"""이메일로 회원을 검색해 회원 정보 팝업을 거쳐 '상담관리' 화면까지 이동한다.

카드취소 처리 전, 담당자가 구글 시트에 적힌 내용과 회원의 실제 상담관리
기록(요청자, 영수증 첨부 여부 등)이 서로 맞는지 눈으로 대조해야 해서 만든
기능이다. 사용자가 실제로 클릭해서 확인해준 경로를 그대로 자동화한다:

  회원관리 > 회원리스트 (검색조건: 이메일) 검색
    -> 검색결과 행의 이메일 링크 클릭 (studentPage('mail_send', ismember) 팝업)
    -> 팝업 안의 '상담관리' 링크 클릭 (같은 창에서 페이지 전환)

검색폼 자체가 GET 방식이라, UI(드롭다운 등)를 조작하는 대신 쿼리스트링을
직접 만들어 바로 그 결과 URL로 이동한다 — select2/multiselect 같은 커스텀
드롭다운 위젯을 Selenium으로 조작하는 것보다 훨씬 안정적이다.
"""

import time
from urllib.parse import urlencode, urlparse

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from .. import config
from ..utils.progress import emit_log
from .driver import switch_to_new_window
from .member_popup import open_consultation_tab

MEMBER_LIST_PATH = "/edu/admin_common/member/member_list.php"

# studentPage('mail_send', '120871') 형태의 onclick에서 회원 고유번호(ismember)를 뽑는다.
MEMBER_LINK_SELECTOR = "a[onclick*=\"studentPage('mail_send'\"]"


class MemberSearchError(Exception):
    pass


def _lms_root() -> str:
    parsed = urlparse(config.LMS_BASE_URL)
    return f"{parsed.scheme}://{parsed.netloc}"


def _member_list_search_url(email: str) -> str:
    params = {
        "search_go": "Y",
        "page_count": "30",
        "level_search": "",
        "find_member_mode": "",
        "find_recommend": "",
        "arrange_type": "reg_date",
        "desc_type": "DESC",
        "search_class_type": "",
        "datetype": "reg_date",
        "fr_date": "",
        "to_date": "",
        "search_word": email,
        "search_key": "email",
    }
    return f"{_lms_root()}{MEMBER_LIST_PATH}?{urlencode(params)}"


def open_member_consultation_by_email(driver, email: str) -> None:
    """이메일로 회원을 검색해 상담관리 화면까지 자동으로 이동한다.

    검색 결과가 없거나 회원 링크를 찾지 못하면 MemberSearchError를 낸다 —
    이런 경우는 이메일 오타/미가입 등일 수 있어 사람이 직접 확인해야 한다.
    """
    emit_log(f"회원 검색 (이메일: {email})")
    driver.get(_member_list_search_url(email))

    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "table.table-performance-data"))
        )
    except TimeoutException as exc:
        raise MemberSearchError(f"검색 결과 화면을 불러오지 못했습니다 (이메일: {email}).") from exc

    if driver.find_elements(By.CSS_SELECTOR, "td.no-data"):
        raise MemberSearchError(f"'{email}'로 검색된 회원이 없습니다.")

    links = driver.find_elements(By.CSS_SELECTOR, MEMBER_LINK_SELECTOR)
    if not links:
        raise MemberSearchError(f"'{email}' 검색 결과에서 회원 링크를 찾지 못했습니다.")
    if len(links) > 1:
        emit_log(f"'{email}'로 검색된 회원이 {len(links)}명입니다. 첫 번째 결과로 진행합니다.", level="warn")

    emit_log("회원 정보 팝업 열기")
    windows_before = driver.window_handles
    driver.execute_script("arguments[0].click();", links[0])

    try:
        switch_to_new_window(driver, windows_before)
    except TimeoutException as exc:
        raise MemberSearchError("회원 정보 팝업이 열리지 않았습니다.") from exc

    time.sleep(config.REQUEST_DELAY_SECONDS)

    open_consultation_tab(driver)
    emit_log("상담관리 화면으로 이동 완료")
