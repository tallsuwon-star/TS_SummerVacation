"""오전특강 통계 화면의 "전체 강사 조회" 버튼이 실행하는 작업.

로그인 -> 원어민 강사 시간표 페이지 이동까지만 하고, 그 페이지에 실제로 떠
있는 전체 강사 이름을 긁어서 한 번에 돌려준다. 여기서 긁어온 이름들은
electron/renderer/js/views/morningSpecialStats.js에서 "강사 블랙/그레이/
화이트 타임 설정" 명단(blackTimeTutorRoster)에 자동으로 합쳐져, 사용자가
나중에 체크체크로 누구의 블랙/화이트 타임을 설정할지 고를 수 있게 한다.

강사 이름은 각 강사 칸에서
    <a onclick="window.open('/edu/admin_common/tutor_info/index.php?tutor_id=...')">
        <div style="font-weight: bold; color: #000;">
            (신규 강사면 <img ... new_ico.png ...> 가 붙기도 함)
            강사이름
        </div>
    </a>
형태로만 나온다(사용자가 실제 화면 HTML로 확인). 학습매니저 이름, 직급(TL/CT 등),
Phonics/LAT 등 배지, SCH/TIM 버튼은 전부 다른 태그/스타일이라 이 스타일의
div만 골라도 강사 이름 외의 것이 섞여 들어오지 않는다.
"""

from bs4 import BeautifulSoup

from ..control import ControlState
from ..lms.auth import login
from ..lms.driver import build_driver
from ..lms.navigation import go_to_native_tutor_schedule
from ..utils.progress import emit_done, emit_log, emit_tutor_roster_record

JOB_NAME = "tutor_roster_fetch"


def _is_tutor_name_div(tag) -> bool:
    """강사 이름이 들어있는 칸인지 판별.

    실제 화면 HTML마다 style 속성의 공백/세미콜론 유무가 조금씩 다를 수 있어
    (예: "font-weight: bold; color: #000;" vs "font-weight:bold;color:#000"),
    문자열을 그대로 비교하지 않고 공백을 제거한 뒤 두 선언이 모두 들어있는지만
    확인한다."""
    if tag.name != "div":
        return False
    style = (tag.get("style") or "").lower().replace(" ", "")
    return "font-weight:bold" in style and "color:#000" in style


def _extract_tutor_names(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    names: list[str] = []
    seen: set[str] = set()

    for div in soup.find_all(_is_tutor_name_div):
        name = div.get_text(strip=True)
        if not name or name in seen:
            continue
        seen.add(name)
        names.append(name)

    return names


def run(job_payload: dict, control: ControlState) -> None:
    driver = build_driver()
    names: list[str] = []

    try:
        login(driver)
        go_to_native_tutor_schedule(driver)

        emit_log("원어민 강사 시간표 페이지에서 강사 명단을 읽는 중...")
        names = _extract_tutor_names(driver.page_source)

        if names:
            emit_log(f"강사 {len(names)}명을 찾았습니다.")
            emit_tutor_roster_record(names)
        else:
            emit_log("강사 이름을 하나도 찾지 못했습니다. 화면 구조가 바뀌었는지 확인해주세요.", level="error")
    finally:
        driver.quit()

    emit_done({"job": JOB_NAME, "tutor_count": len(names)})
