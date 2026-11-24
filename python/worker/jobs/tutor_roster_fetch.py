"""오전특강 통계 화면의 "전체 강사 조회" 버튼이 실행하는 작업.

로그인 -> 원어민 강사 시간표 페이지 이동까지만 하고, 그 페이지에 실제로 떠
있는 전체 강사를 센터별로 묶어서 한 번에 돌려준다. 여기서 긁어온 이름들은
electron/renderer/js/views/morningSpecialStats.js에서 "강사 블랙/그레이/
화이트 타임 설정" 명단(blackTimeTutorRoster)에 센터 정보와 함께 자동으로
합쳐져, 사용자가 나중에 체크체크로 누구의 블랙/화이트 타임을 설정할지 센터별로
걸러서 고를 수 있게 한다.

화면 구조(사용자가 실제 화면 HTML로 확인):
    <div class="mws-panel ...">                                 <- 팀 하나(=강사 여러 명)
      <div class="mws-panel-header">
        <a ...>
          <span class="i-group" title="Team A1 (Flora) ">...</span>
          <div class="call_center" style="background:#ffcc00">Iloilo (1st)</div>   <- 이 팀의 센터명
        </a>
      </div>
      <div class="mws-panel-body">
        ...
        <a onclick="window.open('/edu/admin_common/tutor_info/index.php?tutor_id=...')">
          <div style="font-weight: bold; color: #000;">강사이름</div>              <- 강사 이름
        </a>
        ...
      </div>
    </div>
즉 "팀(.mws-panel)" 하나마다 센터명(.call_center) 하나와 강사 이름(들)이 같이
들어있어서, 센터명 없는 다른 패널(수업 안 되는 강사 리스트, 센터별 시간표
필터 버튼 등)은 애초에 강사 이름 칸이 없어 자동으로 걸러진다.
"""

from bs4 import BeautifulSoup

from ..control import ControlState
from ..lms.auth import login
from ..lms.driver import build_driver
from ..lms.navigation import go_to_native_tutor_schedule
from ..utils.progress import emit_done, emit_log, emit_tutor_roster_record

JOB_NAME = "tutor_roster_fetch"

UNKNOWN_CENTER = "미분류"


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


def _extract_tutor_roster(html: str) -> list[dict]:
    """팀 패널(.mws-panel)마다 센터명(.call_center)을 먼저 읽고, 그 패널 안의
    강사 이름을 전부 그 센터에 소속시킨다. 반환값은 [{"name": ..., "center": ...}, ...]
    형태이며, 같은 이름이 중복으로 잡히면(이미 같은 이름을 다른 패널에서 찾은 경우)
    처음 찾은 것만 남긴다."""
    soup = BeautifulSoup(html, "html.parser")
    roster: list[dict] = []
    seen_names: set[str] = set()

    for panel in soup.select(".mws-panel"):
        center_div = panel.select_one(".call_center")
        center = center_div.get_text(strip=True) if center_div else None

        name_divs = panel.find_all(_is_tutor_name_div)
        if not name_divs:
            continue
        if not center:
            # 강사 이름 칸은 있는데 센터명 칸이 없는 패널은 지금까지 확인된 화면
            # 구조상 없어야 하지만, 혹시 생기면 조용히 누락시키지 않고 "미분류"로
            # 남겨서 사용자가 확인할 수 있게 한다.
            center = UNKNOWN_CENTER

        for div in name_divs:
            name = div.get_text(strip=True)
            if not name or name in seen_names:
                continue
            seen_names.add(name)
            roster.append({"name": name, "center": center})

    return roster


def run(job_payload: dict, control: ControlState) -> None:
    driver = build_driver()
    roster: list[dict] = []

    try:
        login(driver)
        go_to_native_tutor_schedule(driver)

        emit_log("원어민 강사 시간표 페이지에서 강사 명단을 센터별로 읽는 중...")
        roster = _extract_tutor_roster(driver.page_source)

        if roster:
            center_count = len({entry["center"] for entry in roster})
            emit_log(f"강사 {len(roster)}명을 {center_count}개 센터로 분류해서 찾았습니다.")
            emit_tutor_roster_record(roster)
        else:
            emit_log("강사 이름을 하나도 찾지 못했습니다. 화면 구조가 바뀌었는지 확인해주세요.", level="error")
    finally:
        driver.quit()

    emit_done({"job": JOB_NAME, "tutor_count": len(roster)})
