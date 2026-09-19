"""office.talkstation.co.kr 일일업무보고 작성(/report/write) 자동 채움 + 제출.

사용자가 붙여준 실제 페이지 HTML 기준으로 만든 정확한 선택자를 쓴다:
- 폼: #reportForm (action=/report/process, method=post, multipart/form-data)
- 날짜: input[name="report_date"]
- summernote 필드 6개: textarea[name="{monthly_work|monthly_plan|weekly_work|
  weekly_plan|daily_work|daily_plan}_report"]
- 특이사항: textarea[name="issues"]
- 첨부파일: input[name="upload_files[]"]
- 제출 버튼: #btnSubmit — 실제로 눌러보니 평범한 폼 제출이 아니라, 클릭 시
  "입력하신 내용으로 업무보고를 하시겠습니까?" 확인창(confirm)이 뜨고,
  확인을 눌러야 실제 등록이 진행되는 커스텀 JS 핸들러가 붙어있다. 등록 후
  결과를 알리는 두 번째 알림창이 뜰 수도 있어 아래에서 순서대로 처리한다.

Summernote는 화면에 보이는 편집 영역(.note-editable)과 실제 전송되는
<textarea>를 동기화해주는데, 그 동기화가 정확히 언제 일어나는지(값 변경
시점인지 폼 제출 시점인지) 이 페이지의 커스텀 JS를 보지 못해 확신할 수
없다. 그래서 신뢰할 수 있는 방법인 Summernote 자체 API
($(textarea).summernote('code', html))로 값을 넣는다 — 이 API는 화면
편집 영역과 내부 데이터 모델을 함께 갱신해주므로, 그 이후 폼이 언제
제출되든 값이 올바르게 반영된다.
"""

import time

from selenium.common.exceptions import NoAlertPresentException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from .. import config
from ..utils.progress import emit_log

WRITE_PATH = "/report/write"

SUMMERNOTE_FIELD_NAMES = [
    "monthly_work_report",
    "monthly_plan_report",
    "weekly_work_report",
    "weekly_plan_report",
    "daily_work_report",
    "daily_plan_report",
    "issues",
]

SET_SUMMERNOTE_JS = """
var el = arguments[0];
var html = arguments[1];
if (window.jQuery && jQuery.fn && jQuery.fn.summernote) {
    jQuery(el).summernote('code', html);
    return 'summernote-api';
}
return 'unsupported';
"""

FALLBACK_SET_EDITABLE_JS = """
var el = arguments[0];
var html = arguments[1];
el.value = html;
var editable = el.parentElement ? el.parentElement.querySelector('.note-editable') : null;
if (editable) { editable.innerHTML = html; }
"""


def fill_and_submit(driver, report_data: dict, report_date: str | None, file_paths: list[str] | None) -> dict:
    result: dict = {"success": False, "error": None, "alertText": None, "consoleErrors": [], "finalUrl": None}

    driver.get(f"{config.OFFICE_BASE_URL}{WRITE_PATH}")

    try:
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.ID, "reportForm")))
    except TimeoutException:
        result["error"] = f"작성 화면(#reportForm)을 찾지 못했습니다. 현재 URL: {_safe_current_url(driver)}"
        return result

    if report_date:
        _set_date(driver, report_date)

    for field_name in SUMMERNOTE_FIELD_NAMES:
        html_content = report_data.get(field_name) or ""
        _set_summernote_field(driver, field_name, html_content)

    if file_paths:
        _attach_files(driver, file_paths)

    time.sleep(config.REQUEST_DELAY_SECONDS)

    emit_log("작성 완료, '글쓰기' 버튼을 클릭합니다.")
    try:
        submit_btn = driver.find_element(By.ID, "btnSubmit")
        submit_btn.click()
    except Exception as exc:  # noqa: BLE001
        result["error"] = f"'글쓰기' 버튼을 클릭하지 못했습니다: {exc}"
        return result

    # "글쓰기"를 누르면 "입력하신 내용으로 업무보고를 하시겠습니까?" 같은 확인창이
    # 먼저 뜨고, 확인을 누른 뒤에야 실제 등록이 진행되며 그 결과(성공/실패)를
    # 알리는 두 번째 알림창이 뜰 수 있다. 그래서 알림창이 뜨는 대로 계속
    # 확인을 누르면서(최대 3번) 마지막 알림창의 내용으로 성공/실패를 판단한다.
    alert_texts: list[str] = []
    for i in range(3):
        text = _wait_for_alert(driver, timeout=4 if i == 0 else 6)
        if text is None:
            break
        alert_texts.append(text)
        if _is_confirm_prompt(text):
            emit_log(f"확인창이 떠서 확인을 눌렀습니다: {text}")
        else:
            emit_log(f"결과 알림창: {text}")
            break  # 질문이 아니라 결과 메시지로 보이므로 더 기다리지 않는다

    if alert_texts:
        result["alertText"] = alert_texts[-1]
        if _looks_like_failure(alert_texts[-1]):
            result["error"] = f"제출 실패 알림: {alert_texts[-1]}"
            return result

    time.sleep(2)  # 리다이렉트/렌더링 대기

    result["consoleErrors"] = _collect_console_errors(driver)
    result["finalUrl"] = _safe_current_url(driver)

    if WRITE_PATH in result["finalUrl"]:
        # 제출 후에도 여전히 작성 화면이면 서버 쪽 검증 실패 등으로 실패했을 가능성이 크다.
        result["error"] = "제출 후에도 작성 화면에 그대로 남아있습니다 (서버 검증 실패 가능성)."
        for err in result["consoleErrors"]:
            emit_log(f"[브라우저 콘솔 오류] {err}", level="error")
        return result

    result["success"] = True
    emit_log(f"제출 완료로 보입니다. 이동한 화면: {result['finalUrl']}")
    for err in result["consoleErrors"]:
        emit_log(f"[브라우저 콘솔 오류(참고용)] {err}", level="warn")
    return result


def _set_date(driver, report_date: str) -> None:
    try:
        date_input = driver.find_element(By.CSS_SELECTOR, "input[name='report_date']")
    except Exception:  # noqa: BLE001
        emit_log("날짜 입력창(report_date)을 찾지 못했습니다.", level="warn")
        return
    driver.execute_script(
        "arguments[0].value = arguments[1];"
        "arguments[0].dispatchEvent(new Event('change', { bubbles: true }));",
        date_input,
        report_date,
    )


def _set_summernote_field(driver, field_name: str, html_content: str) -> None:
    try:
        textarea = driver.find_element(By.CSS_SELECTOR, f"textarea[name='{field_name}']")
    except Exception:  # noqa: BLE001
        emit_log(f"입력창을 찾지 못했습니다: {field_name}", level="warn")
        return

    mode = driver.execute_script(SET_SUMMERNOTE_JS, textarea, html_content)
    if mode == "unsupported":
        emit_log(
            f"Summernote API를 찾지 못해 대체 방식으로 값을 넣습니다: {field_name} "
            "(제출 시 실제로 반영되는지 확인 필요)",
            level="warn",
        )
        driver.execute_script(FALLBACK_SET_EDITABLE_JS, textarea, html_content)


def _attach_files(driver, file_paths: list[str]) -> None:
    try:
        file_input = driver.find_element(By.CSS_SELECTOR, "input[name='upload_files[]']")
    except Exception:  # noqa: BLE001
        emit_log("파일 첨부 입력창을 찾지 못했습니다.", level="warn")
        return
    file_input.send_keys("\n".join(file_paths))
    emit_log(f"첨부파일 {len(file_paths)}개를 선택했습니다.")


CONFIRM_MARKERS = ("하시겠습니까", "하시겠어요", "할까요", "하시겠어", "하겠습니까")
FAILURE_MARKERS = ("실패", "오류", "에러", "다시 입력", "선택해", "입력해주세요", "필요합니다")


def _is_confirm_prompt(text: str) -> bool:
    return any(marker in text for marker in CONFIRM_MARKERS)


def _looks_like_failure(text: str) -> bool:
    return any(marker in text for marker in FAILURE_MARKERS)


def _wait_for_alert(driver, timeout: float = 4) -> str | None:
    try:
        WebDriverWait(driver, timeout).until(EC.alert_is_present())
        text = driver.switch_to.alert.text
        driver.switch_to.alert.accept()
        return text
    except (TimeoutException, NoAlertPresentException):
        return None


def _collect_console_errors(driver) -> list[str]:
    try:
        logs = driver.get_log("browser")
    except Exception:  # noqa: BLE001
        return []
    return [f"{entry.get('level')}: {entry.get('message')}" for entry in logs if entry.get("level") == "SEVERE"]


def _safe_current_url(driver) -> str:
    try:
        return driver.current_url
    except Exception:  # noqa: BLE001
        return "(알 수 없음)"
