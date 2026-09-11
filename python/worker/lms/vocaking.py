import re
import time
from urllib.parse import urlencode

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from .. import config
from ..utils.progress import emit_log

# 통합LMS(lms.talkstation.co.kr) 안에서의 이동. 상단 네비게이션의 '보카킹' 탭은
# href="#"라 실제 페이지 이동 없이 JS로 좌측 사이드바를 바꾸는 방식으로 보인다.
# nvalue="4"가 보카킹 고유 값이라 텍스트보다 이 속성으로 찾는 게 더 안전하다.
VOCAKING_TAB_SELECTOR = "a.navbar-option[nvalue='4']"

# '유료 수강생 리스트' 사이드바 링크. 실제 href를 알고 있어 바로 찾을 수 있다.
CHARGED_STUDENT_LIST_HREF = "/admin/admin/vocaking_charged_student/vocaking_charged_student_list.php"
CHARGED_STUDENT_LIST_URL = "https://lms.talkstation.co.kr" + CHARGED_STUDENT_LIST_HREF

# 검색 폼(#searchForm)이 GET 방식이라 select2/라디오 버튼을 클릭하는 대신
# 쿼리 파라미터를 직접 조합해 driver.get()으로 바로 접근한다 (실제 회원 목록
# 화면 HTML에서 확인된 파라미터 이름/값 그대로).
PAGE_SIZE = 30
WEEK_LABEL = {2: "주2회", 3: "주3회", 5: "주5회"}
LIST_TYPE_LABEL = {"free": "무료", "paid": "유료"}

# 실제 사람 이름이 아닌 것으로 의심되는(가짜/테스트) 계정을 걸러내기 위한 키워드.
# 이 판정은 100% 정확하다고 보장하지 않는 '의심 후보' 목록을 만드는 용도이며,
# 최종적으로는 사용자가 이름을 직접 눈으로 확인해야 한다.
FAKE_NAME_KEYWORDS = ["테스트", "test", "보카", "팝업", "샘플", "sample"]
_KOREAN_NAME_RE = re.compile(r"^[가-힣]{2,5}$")


class VocakingNavigationError(Exception):
    pass


class VocakingListError(Exception):
    pass


def click_vocaking_tab(driver) -> None:
    """통합LMS 상단 네비게이션에서 '보카킹' 탭을 클릭해 보카킹 전용 사이드바로 전환한다.

    도착 직후 이미 '보카킹' 탭이 active 상태로 보이는 경우도 있었지만, 항상
    보장되는 것은 아니라서 명시적으로 클릭해 확실히 전환한다.
    """
    emit_log("'보카킹' 탭 클릭")

    try:
        tab = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, VOCAKING_TAB_SELECTOR))
        )
    except TimeoutException as exc:
        raise VocakingNavigationError("'보카킹' 탭을 찾지 못했습니다.") from exc

    driver.execute_script("arguments[0].click();", tab)
    time.sleep(config.REQUEST_DELAY_SECONDS)


def click_charged_student_list(driver) -> None:
    """좌측 사이드바의 '유료 수강생 리스트' 링크를 클릭한다."""
    emit_log("'유료 수강생 리스트' 클릭")

    try:
        link = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, f"a[href='{CHARGED_STUDENT_LIST_HREF}']"))
        )
    except TimeoutException as exc:
        raise VocakingNavigationError("'유료 수강생 리스트' 링크를 찾지 못했습니다.") from exc

    driver.execute_script("arguments[0].click();", link)
    time.sleep(config.REQUEST_DELAY_SECONDS)

    emit_log(f"현재 URL: {driver.current_url}")
    emit_log(f"페이지 제목: {driver.title}")


def build_charged_student_list_url(list_type: str, week_cnt: int, page: int, class_month: str) -> str:
    """무료/유료 x 보카킹 횟수 목록 URL을 직접 조합한다.

    #searchForm이 GET 방식이라 select2/라디오 버튼을 실제로 클릭하지 않고도
    이 파라미터들을 그대로 URL에 넣어 driver.get()으로 접근하면 동일하게 동작한다.
    """
    params = {
        "listType": list_type,
        "vocaking_class_week_cnt": week_cnt,
        "level_id": "",
        "orderValue": "enrollAppliedDateForm",
        "orderSequence": "desc",
        "pageCount": PAGE_SIZE,
        "classMonth": class_month,
        "searchTime": "",
        "classID": "",
        "sel_search": "name",
        "sel_text": "",
        "searchTutorID": "",
        "searchSignSw": "",
        "nowPage": page,
    }
    return f"{CHARGED_STUDENT_LIST_URL}?{urlencode(params)}"


def is_suspicious_name(korean_name: str, eng_name: str) -> bool:
    """실제 사람 이름이 아닌 것으로 의심되는 이름인지 판별한다 (의심 후보용, 확정 아님)."""
    combined = f"{korean_name} {eng_name}".lower()
    if any(keyword.lower() in combined for keyword in FAKE_NAME_KEYWORDS):
        return True
    if not _KOREAN_NAME_RE.match(korean_name):
        return True
    return False


def fetch_charged_student_page(driver, list_type: str, week_cnt: int, page: int, class_month: str):
    """한 페이지를 조회해 (전체 인원수, 이 페이지의 [(한글이름, 영어이름), ...]) 를 반환한다.

    회원 이름 셀 구조 (실제 확인됨):
      <tr data-student-id="...">
        <td>체크박스</td><td>No</td>
        <td>
          <a onclick="studentPage(...)">양다연(여/12)<br>jenny yang</a>
          <a class="c-btn" data-clipboard-text="이메일">...</a>
        </td>
        ...
      </tr>
    .text로 가져오면 "양다연(여/12)\njenny yang"처럼 나와서 첫 줄에서
    괄호(성별/연령) 부분만 떼면 이름, 둘째 줄이 영어이름/별명이다.
    """
    url = build_charged_student_list_url(list_type, week_cnt, page, class_month)
    driver.get(url)

    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='total_record']"))
        )
    except TimeoutException as exc:
        raise VocakingListError(
            f"목록 로딩 실패 (listType={list_type}, week_cnt={week_cnt}, page={page})"
        ) from exc

    total_record = int(
        driver.find_element(By.CSS_SELECTOR, "input[name='total_record']").get_attribute("value")
    )

    members: list[tuple[str, str]] = []
    for row in driver.find_elements(By.CSS_SELECTOR, "tr[data-student-id]"):
        try:
            name_link = row.find_element(By.CSS_SELECTOR, "td:nth-child(3) a[onclick*='studentPage']")
        except Exception:  # noqa: BLE001 - 이름 셀 구조가 다른 행은 건너뛴다 (집계에서 누락되지 않도록 로그는 호출부에서 남김)
            continue

        lines = [line.strip() for line in name_link.text.split("\n") if line.strip()]
        if not lines:
            continue

        korean_name = re.sub(r"\([^)]*\)\s*$", "", lines[0]).strip()
        eng_name = lines[1] if len(lines) > 1 else ""
        members.append((korean_name, eng_name))

    return total_record, members


def fetch_all_charged_students(driver, list_type: str, week_cnt: int, class_month: str):
    """전체 페이지를 순회해 (전체 인원수, 전체 [(한글이름, 영어이름), ...]) 를 반환한다."""
    label = f"{LIST_TYPE_LABEL.get(list_type, list_type)} {WEEK_LABEL.get(week_cnt, f'주{week_cnt}회')}"
    emit_log(f"[{label}] 목록 조회 시작")

    total_record, members = fetch_charged_student_page(driver, list_type, week_cnt, 1, class_month)
    all_members = list(members)

    total_pages = (total_record + PAGE_SIZE - 1) // PAGE_SIZE
    for page in range(2, total_pages + 1):
        time.sleep(config.REQUEST_DELAY_SECONDS)
        _, page_members = fetch_charged_student_page(driver, list_type, week_cnt, page, class_month)
        all_members.extend(page_members)

    if len(all_members) != total_record:
        emit_log(
            f"[{label}] 경고: 전체 인원수({total_record})와 실제로 파싱된 이름 수({len(all_members)})가 다릅니다.",
            level="error",
        )

    emit_log(f"[{label}] 총 {total_record}명, 파싱된 이름 {len(all_members)}개 ({total_pages}페이지)")
    return total_record, all_members
