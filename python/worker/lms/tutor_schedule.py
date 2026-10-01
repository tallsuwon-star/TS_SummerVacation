"""원어민 강사 시간표(수업 시간표 관리) 화면에서, 특정 요일×시간의 체크박스를
블랙타임(진하게 칠해진 칸) / 그레이타임(휴식시간) / 화이트타임(수업 가능, 체크 없음)
상태로 바꾼다.

이 화면은 SCH 버튼을 눌러 연 "시간표" 팝업(page1_pop.php?tutor_id=...)이며, 체크박스
id는 `time_{시HH}{분MM}{요일0~6}{구분1or2}` 형식이고(예: 09시 00분 일요일 블랙타임 =
"time_090001"), 각 체크박스의 onclick이 그 시간대의 숨은 필드(`{시HH}time`)를
`chkMinute(시HH)`로 다시 계산한다. 그래서 여기서는 체크박스를 실제 클릭(JS click())해서
그 onclick 체인이 그대로 타게 하고, 혹시 모를 경우를 대비해 체크 상태를 바꾼 시(hour)마다
`chkMinute()`를 한 번 더 직접 호출해 숨은 필드가 반드시 갱신되게 한다.

절대 "작성완료" 제출 버튼은 누르지 않는다 — 사용자가 화면에서 직접 확인하고 제출한다."""

from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from ..utils.progress import emit_log

WEEKDAY_NAMES = ["일", "월", "화", "수", "목", "금", "토"]
MINUTE_SLOTS = ("00", "10", "20")

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


def wait_for_schedule_page(driver, timeout: float = 10) -> None:
    """시간표 팝업(체크박스 그리드)이 로딩될 때까지 대기."""
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='checkbox'][id^='time_']"))
        )
    except TimeoutException as exc:
        raise TutorScheduleError("시간표 체크박스 화면을 찾지 못했습니다.") from exc


def set_hour_state(driver, weekday: int, hour: int, state: str, minute_slots: tuple = MINUTE_SLOTS) -> None:
    """지정한 요일(0=일 ... 6=토)의 지정한 시(hour)를, 그 시간에 속한 10분 단위
    칸들(기본: 00/10/20분) 모두에 대해 블랙/그레이/화이트 타임으로 맞춘다.

    - black: type1(블랙) 체크, type2(그레이) 해제
    - gray : type2(그레이) 체크, type1(블랙) 해제
    - white: 둘 다 해제
    """
    if state not in (STATE_BLACK, STATE_GRAY, STATE_WHITE):
        raise ValueError(f"알 수 없는 상태: {state}")
    if not (0 <= weekday <= 6):
        raise ValueError(f"요일 값은 0(일)~6(토) 범위여야 합니다: {weekday}")

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
