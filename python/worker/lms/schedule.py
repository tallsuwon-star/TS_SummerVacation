import re
import time

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

from .. import config
from ..utils.progress import emit_log

# 실제 확인된 선택자: <select name="a_divide">...<option value="am">오전</option>...
AM_PM_SELECT_SELECTOR = "select[name='a_divide']"
AM_OPTION_VALUE = "am"

# 시간표 표: <table class="mws-table"> 안, 각 행(tr)의 2번째 td가 시간("10:00" 등),
# 이후 td.list-type-left 안에 회원 버튼들이 들어있다.
# 회원 버튼은 <button value="이름">이름</button> 또는 <input type="button" value="이름"> 두 형태 모두 나온다.
MEMBER_BUTTON_SELECTOR = (
    "td.list-type-left button.mws-button[value], td.list-type-left input[type='button'].mws-button[value]"
)

AM_WINDOW_START_MINUTES = 10 * 60  # 10:00
AM_WINDOW_END_MINUTES = 12 * 60 + 30  # 12:30


class ScheduleViewError(Exception):
    pass


def ensure_am_view(driver) -> None:
    """기본 화면이 '오후'로 표시되어 있으면 '오전'으로 토글 전환한다.
    실제로는 버튼이 아니라 select[name='a_divide'] 드롭다운이며, onchange 시 폼이 자동 제출되어
    페이지가 새로 로딩된다.
    """
    emit_log("오전/오후 화면 확인")

    try:
        select_el = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, AM_PM_SELECT_SELECTOR))
        )
    except TimeoutException as exc:
        raise ScheduleViewError("오전/오후 선택 드롭다운을 찾지 못했습니다.") from exc

    select = Select(select_el)
    current_value = select.first_selected_option.get_attribute("value")

    if current_value != AM_OPTION_VALUE:
        emit_log(f"현재 '{current_value}' 상태 -> '오전'으로 전환")
        select.select_by_value(AM_OPTION_VALUE)
        time.sleep(config.REQUEST_DELAY_SECONDS)
    else:
        emit_log("이미 '오전' 화면임")


def collect_am_class_members(driver) -> list[str]:
    """10:00~13:00 수업을 확인하고, 그중 10:00~12:30 시작 수업들에서 회원 이름 전체를 수집한다.
    같은 회원이 여러 요일/시간에 걸쳐 여러 번 나올 수 있는데, '상담관리'는 회원(수강권) 단위라
    같은 회원을 중복 처리하지 않도록 처음 등장한 순서를 유지하며 중복 제거한다.
    """
    emit_log("오전 수업(10:00~12:30 시작) 회원 명단 수집")

    member_names: list[str] = []

    rows = driver.find_elements(By.CSS_SELECTOR, "table.mws-table tbody tr")
    for row in rows:
        cells = row.find_elements(By.TAG_NAME, "td")
        if len(cells) < 2:
            continue

        time_text = cells[1].text.strip()
        if not _starts_between_10_and_1230(time_text):
            continue

        name_buttons = row.find_elements(By.CSS_SELECTOR, MEMBER_BUTTON_SELECTOR)
        for btn in name_buttons:
            name = (btn.get_attribute("value") or "").strip()
            if name:
                member_names.append(name)

    return list(dict.fromkeys(member_names))


def _starts_between_10_and_1230(class_time_text: str) -> bool:
    """수업 시작 시각이 10:00~12:30 사이인지 판정. 시간 셀 텍스트는 'HH:MM' 형식(예: '10:30')."""
    match = re.match(r"^(\d{1,2}):(\d{2})$", class_time_text)
    if not match:
        return False

    hour, minute = int(match.group(1)), int(match.group(2))
    total_minutes = hour * 60 + minute
    return AM_WINDOW_START_MINUTES <= total_minutes <= AM_WINDOW_END_MINUTES
