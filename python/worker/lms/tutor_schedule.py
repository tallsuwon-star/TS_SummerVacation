"""원어민 강사 시간표(수업 시간표 관리) 화면에서, 특정 요일×시간의 체크박스를
블랙타임(진하게 칠해진 칸) / 그레이타임(휴식시간) / 화이트타임(수업 가능, 체크 없음)
상태로 바꾼다.

이 화면은 SCH 버튼을 눌러 연 "원어민 강사 시간표" 팝업에서 "수업시간표관리" 버튼을
또 눌러야 새 팝업 창으로 열리는 실제 체크박스 표(/edu/AD_page/tutor/tutor_schedule.php
?tutor_id=...)이다. 체크박스 id는 `time_{시HH}{분MM}{요일0~6}{구분1~3}` 형식이고
(예: 09시 00분 일요일 블랙타임 = "time_090001"), 각 체크박스의 onclick이 그 시간대의
숨은 필드(`{시HH}time`)를 `chkMinute(시HH)`로 다시 계산한다. 그래서 여기서는 체크박스를
실제 클릭(JS click())해서 그 onclick 체인이 그대로 타게 하고, 혹시 모를 경우를 대비해
체크 상태를 바꾼 시(hour)마다 `chkMinute()`를 한 번 더 직접 호출해 숨은 필드가 반드시
갱신되게 한다.

한 "시(hour)" 행에는 00/10/20/30/40/50분, 총 6개의 10분 단위 칸이 있고 이는 정시 수업
(00/10/20분)과 30분 수업(30/40/50분) 두 수업 슬롯에 해당한다. 그래서 "몇 시 수업을 연다"는
그 수업이 시작하는 분(0 또는 30)부터 10분 단위로 3칸만 묶어서 처리해야 한다.

절대 "작성완료" 제출 버튼은 누르지 않는다 — 사용자가 화면에서 직접 확인하고 제출한다."""

from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from ..utils.progress import emit_log
from .driver import switch_to_new_window

WEEKDAY_NAMES = ["일", "월", "화", "수", "목", "금", "토"]

# SCH 팝업("원어민 강사 시간표")에서 이 버튼을 눌러야 실제 체크박스 표가 담긴
# 새 팝업 창(tutor_schedule.php)이 열린다.
# <input type="button" onclick="tutor_schedule('Daheetest11')" value="수업시간표관리" ...>
SCHEDULE_BUTTON_VALUE = "수업시간표관리"

BLACK_TYPE = "1"
GRAY_TYPE = "2"
# 아직 정확한 용도는 설명되지 않은 세 번째 체크박스("M"). 사용자 확인 결과, 블랙/그레이와
# 마찬가지로 이것도 꺼져 있어야 화이트 타임이 정상적으로 적용된다.
EXTRA_TYPE = "3"

STATE_BLACK = "black"
STATE_GRAY = "gray"
STATE_WHITE = "white"


class TutorScheduleError(Exception):
    pass


def open_schedule_checkboxes(driver, timeout: float = 10) -> None:
    """"수업시간표관리" 버튼을 눌러 체크박스 표를 연다.

    이 버튼은 새 팝업 창(tutor_schedule.php)을 여는 방식이라, 클릭 후 그 새 창으로
    전환해야 이후 체크박스 조작이 된다. 혹시 같은 창에서 페이지가 바뀌는 경우를
    대비해, 새 창이 안 열려도 오류로 처리하지 않고 계속 진행한다.
    """
    try:
        button = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable(
                (By.XPATH, f"//input[@type='button' and @value='{SCHEDULE_BUTTON_VALUE}']")
            )
        )
    except TimeoutException as exc:
        raise TutorScheduleError(f"'{SCHEDULE_BUTTON_VALUE}' 버튼을 찾지 못했습니다.") from exc

    emit_log(f"'{SCHEDULE_BUTTON_VALUE}' 버튼 클릭")
    windows_before = driver.window_handles
    button.click()

    try:
        switch_to_new_window(driver, windows_before, timeout=5)
        emit_log("시간표 체크박스 팝업으로 전환 완료")
    except TimeoutException:
        pass


def wait_for_schedule_page(driver, timeout: float = 10) -> None:
    """체크박스 표가 로딩될 때까지 대기."""
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='checkbox'][id^='time_']"))
        )
    except TimeoutException as exc:
        raise TutorScheduleError("시간표 체크박스 화면을 찾지 못했습니다.") from exc


def set_hour_state(driver, weekday: int, hour: int, state: str, start_minute: int = 0) -> None:
    """지정한 요일(0=일 ... 6=토)의 지정한 수업(hour시 start_minute분 시작, 10분 단위
    3칸: start_minute/+10/+20)을 블랙/그레이/화이트 타임으로 맞춘다. start_minute은
    0(정시 수업) 또는 30(30분 수업)만 유효하다.

    - black: type1(블랙) 체크, type2(그레이) 해제
    - gray : type2(그레이) 체크, type1(블랙) 해제
    - white: 둘 다 해제
    """
    if state not in (STATE_BLACK, STATE_GRAY, STATE_WHITE):
        raise ValueError(f"알 수 없는 상태: {state}")
    if not (0 <= weekday <= 6):
        raise ValueError(f"요일 값은 0(일)~6(토) 범위여야 합니다: {weekday}")
    if start_minute not in (0, 30):
        raise ValueError(f"시작 분은 0 또는 30이어야 합니다: {start_minute}")

    minute_slots = tuple(f"{start_minute + offset:02d}" for offset in (0, 10, 20))

    hour_str = f"{hour:02d}"
    weekday_str = str(weekday)
    weekday_name = WEEKDAY_NAMES[weekday]

    want_checked = {
        BLACK_TYPE: state == STATE_BLACK,
        GRAY_TYPE: state == STATE_GRAY,
    }
    if state == STATE_WHITE:
        # 화이트 타임은 블랙/그레이뿐 아니라 세 번째 체크("M")까지 모두 꺼져 있어야 한다.
        want_checked[EXTRA_TYPE] = False

    emit_log(f"{weekday_name}요일 {hour}시({'/'.join(minute_slots)}분)를 "
             f"{'블랙' if state == STATE_BLACK else '그레이' if state == STATE_GRAY else '화이트'} 타임으로 설정")

    changed = False
    for minute in minute_slots:
        for type_digit, should_be_checked in want_checked.items():
            checkbox_id = f"time_{hour_str}{minute}{weekday_str}{type_digit}"
            try:
                checkbox = driver.find_element(By.ID, checkbox_id)
            except NoSuchElementException:
                emit_log(f"  ⚠ 체크박스를 찾지 못함: {checkbox_id}", level="warn")
                continue

            if checkbox.is_selected() != should_be_checked:
                driver.execute_script("arguments[0].click();", checkbox)
                changed = True
                emit_log(f"  {checkbox_id} -> {'체크' if should_be_checked else '해제'}")

    if changed:
        driver.execute_script(
            "if (typeof chkMinute === 'function') { chkMinute(arguments[0]); }", hour_str
        )
