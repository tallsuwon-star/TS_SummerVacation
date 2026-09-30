"""office.talkstation.co.kr 지출결의서 작성(/approval/documents/expenseWrite)
화면에, 회원별 환불 내역을 "지출 내역" 표의 입력 행(#workNewRow)에 채워
"추가"(#btnAddWork) 버튼으로 하나씩 등록한다.

사용자가 명시적으로 요청한 대로, 이 모듈은 절대 "제출하기"(#btnSave)를
누르지 않는다 — 입력만 해두고 사용자가 화면에서 직접 확인한 뒤 제출한다."""

import time
from datetime import date

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from .. import config
from ..utils.progress import emit_log

WRITE_PATH = "/approval/documents/expenseWrite"

NEW_ROW_ID = "workNewRow"
LIST_BODY_ID = "workListBody"
ADD_BUTTON_ID = "btnAddWork"

SET_DATE_JS = "arguments[0].value = arguments[1]; arguments[0].dispatchEvent(new Event('change', { bubbles: true }));"


def fill_expense_rows(driver, rows: list[dict], control) -> dict:
    """rows: [{memberName, reason, amount, accountLine}, ...]. 각 항목을
    "거래처=회원명 / 상세=사유 // 계좌정보 / 거래금액=amount"로 입력 행에
    채우고 추가 버튼을 누른다. control이 중단을 요청하면 그 시점까지 처리한
    결과를 그대로 반환한다."""
    result: dict = {"success": False, "addedCount": 0, "failedRows": [], "finalUrl": None}

    driver.get(f"{config.OFFICE_BASE_URL}{WRITE_PATH}")

    try:
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.ID, NEW_ROW_ID)))
    except TimeoutException:
        result["error"] = f"지출결의서 작성 화면(#{NEW_ROW_ID})을 찾지 못했습니다. 현재 URL: {_safe_current_url(driver)}"
        return result

    today_iso = date.today().isoformat()

    for i, row in enumerate(rows, start=1):
        if control.should_stop():
            emit_log("사용자 요청으로 입력을 중단합니다.")
            break
        control.wait_if_paused()

        name = row.get("memberName") or ""
        reason = row.get("reason") or ""
        amount = row.get("amount") or ""
        account_line = row.get("accountLine") or ""
        content = f"{reason} // {account_line}".strip(" /")

        emit_log(f"({i}/{len(rows)}) 입력 중: {name} / {content} / {amount}원")

        if not name or not amount:
            emit_log(f"  ⚠ 건너뜀: 회원명 또는 금액을 확인할 수 없습니다 ({row}).", level="warn")
            result["failedRows"].append(row)
            continue

        try:
            before_count = len(driver.find_elements(By.CSS_SELECTOR, f"#{LIST_BODY_ID} tr"))

            _set_date(driver, today_iso)
            _set_text(driver, "work-vendor", name)
            _set_text(driver, "work-content", content)
            _set_text(driver, "work-amount", amount)

            driver.find_element(By.ID, ADD_BUTTON_ID).click()

            added = _wait_for_row_count_increase(driver, before_count)
            if not added:
                emit_log(f"  ⚠ 표에 추가되지 않은 것 같습니다 (필수 입력 확인 필요): {name}", level="warn")
                result["failedRows"].append(row)
                continue

            result["addedCount"] += 1
        except Exception as exc:  # noqa: BLE001
            emit_log(f"  ⚠ 입력 중 오류: {exc}", level="error")
            result["failedRows"].append(row)

        time.sleep(0.3)

    result["success"] = result["addedCount"] > 0
    result["finalUrl"] = _safe_current_url(driver)
    return result


def _set_date(driver, iso_date: str) -> None:
    date_input = driver.find_element(By.CSS_SELECTOR, f"#{NEW_ROW_ID} .work-date")
    driver.execute_script(SET_DATE_JS, date_input, iso_date)


def _set_text(driver, class_name: str, value: str) -> None:
    field = driver.find_element(By.CSS_SELECTOR, f"#{NEW_ROW_ID} .{class_name}")
    field.clear()
    field.send_keys(value)


def _wait_for_row_count_increase(driver, before_count: int, timeout: float = 5) -> bool:
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: len(d.find_elements(By.CSS_SELECTOR, f"#{LIST_BODY_ID} tr")) > before_count
        )
        return True
    except TimeoutException:
        return False


def _safe_current_url(driver) -> str:
    try:
        return driver.current_url
    except Exception:  # noqa: BLE001
        return "(알 수 없음)"
