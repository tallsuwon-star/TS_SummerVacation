"""office.talkstation.co.kr 업무보고 1회성 크롤링.

/report (검색된 목록, 서버 렌더링) -> 각 리포트의 상세 내용을 사용자가
지정한 7개 항목(금일 업무 내용 / 명일 업무 계획 / 지난달 계획 / 이번달 계획 /
지난주 내용 / 다음주 계획 / 특이사항)으로, 링크·굵게·글자색 등 서식이 살아있는
HTML 그대로 뽑아 JSON으로 저장한다.

실제 목록 페이지 HTML을 확인해보니 목록의 각 행은 <a href="javascript:void(0)"
onclick="processReport('view', '17051');"> 형태라 href에 아이디가 없고,
onclick 안에만 리포트 번호가 들어있다. 상세 내용은 /report/view/{id}(읽기 전용,
구조 미확인) 대신, 이미 선택자를 정확히 검증해둔 /report/write/{id}(수정 화면 —
"수정" 버튼이 가는 곳이며 기존 값이 그대로 채워진 같은 작성 템플릿)에서 긁어온다.
"""

import json
import re
import time
from pathlib import Path
from urllib.parse import quote

from bs4 import BeautifulSoup

from .. import config
from ..control import ControlState
from ..utils.progress import emit_log
from ._debug import save_debug_snapshot

REPORTS_FILENAME = "reports.json"
MAX_LIST_PAGES = 50

# 목록 행의 조회 링크는 href가 아니라 onclick="processReport('view', 'ID');"
# 안에 아이디가 들어있다 (실제 페이지 소스로 확인됨).
VIEW_ONCLICK_PATTERN = re.compile(r"processReport\('view',\s*'(\d+)'\)")

# (json 필드 접두어, label id, subject hidden input id) — 라벨/내용이 함께
# 있는 6개 summernote 섹션. "issues"(특이사항)는 라벨에 id가 없어 따로 처리한다.
LABELED_SECTIONS = [
    ("monthly_work", "monthly_work_label", "monthly_work_subject"),
    ("monthly_plan", "monthly_plan_label", "monthly_plan_subject"),
    ("weekly_work", "weekly_work_label", "weekly_work_subject"),
    ("weekly_plan", "weekly_plan_label", "weekly_plan_subject"),
    ("daily_work", "daily_work_label", "daily_work_subject"),
    ("daily_plan", "daily_plan_label", "daily_plan_subject"),
]

DATE_PATTERN = re.compile(r"(\d{4})[.\-](\d{2})[.\-](\d{2})")


def data_dir() -> Path:
    return config.DATA_DIR / "office"


def reports_path() -> Path:
    return data_dir() / REPORTS_FILENAME


def build_list_url(target_name: str, page: int | None = None) -> str:
    url = (
        f"{config.OFFICE_BASE_URL}/report"
        f"?isSearch=Y&work_group=K&searchReport=&searchDivision=&searchMonth="
        f"&searchType=member.name&searchText={quote(target_name)}"
    )
    if page and page > 1:
        url += f"&page={page}"
    return url


def crawl_reports(driver, target_name: str, control: ControlState) -> list[dict]:
    """검색된 리포트 전부를 크롤링해서 리스트로 반환한다 (저장은 별도)."""
    reports_found: dict[str, str] = {}  # report_id -> 목록 행에서 뽑은 날짜 힌트

    emit_log(f"'{target_name}' 이름으로 업무보고 목록을 검색합니다.")

    for page in range(1, MAX_LIST_PAGES + 1):
        control.wait_if_paused()
        if control.should_stop():
            emit_log("사용자 요청으로 크롤링을 중단합니다.")
            break

        url = build_list_url(target_name, page)
        emit_log(f"목록 페이지 요청: {url}")
        driver.get(url)
        time.sleep(config.REQUEST_DELAY_SECONDS)

        soup = BeautifulSoup(driver.page_source, "html.parser")
        page_ids = _extract_report_ids(soup)

        new_ids = {rid: d for rid, d in page_ids.items() if rid not in reports_found}
        if not new_ids:
            if page == 1:
                total_anchors = len(soup.find_all("a"))
                has_table = soup.find(id="dataTable") is not None
                emit_log(
                    f"검색 결과가 없습니다. (참고: 실제 도착한 화면 {driver.current_url}, "
                    f"페이지 내 링크 총 {total_anchors}개, #dataTable 존재 여부: {has_table})"
                )
                save_debug_snapshot(driver, f"no_results_{target_name}")
            else:
                emit_log(f"{page}페이지에 새 항목이 없어 목록 조회를 종료합니다.")
            break

        reports_found.update(new_ids)
        emit_log(f"{page}페이지에서 {len(new_ids)}건 발견 (누적 {len(reports_found)}건)")

    reports: list[dict] = []
    total = len(reports_found)
    for idx, (report_id, date_hint) in enumerate(reports_found.items(), start=1):
        control.wait_if_paused()
        if control.should_stop():
            emit_log("사용자 요청으로 크롤링을 중단합니다.")
            break

        # 상세 내용은 이미 선택자를 검증해둔 /report/write/{id}(수정 화면)에서 긁어온다.
        detail_url = f"{config.OFFICE_BASE_URL}/report/write/{report_id}"
        emit_log(f"({idx}/{total}) 상세 내용 가져오는 중: {detail_url}")
        driver.get(detail_url)
        time.sleep(config.REQUEST_DELAY_SECONDS)

        try:
            report = _parse_report_detail(BeautifulSoup(driver.page_source, "html.parser"), report_id, date_hint)
            reports.append(report)
        except Exception as exc:  # noqa: BLE001 - 한 건 실패해도 나머지는 계속 진행
            emit_log(f"상세 내용 파싱 실패({detail_url}): {exc}", level="error")

    reports.sort(key=lambda r: (r.get("report_date") or "", r.get("report_id") or ""), reverse=True)
    return reports


def _extract_report_ids(soup: BeautifulSoup) -> dict[str, str]:
    """목록 행의 onclick="processReport('view', 'ID');"에서 리포트 아이디를 뽑는다."""
    ids: dict[str, str] = {}
    for el in soup.find_all(attrs={"onclick": True}):
        match = VIEW_ONCLICK_PATTERN.search(el["onclick"])
        if not match:
            continue
        report_id = match.group(1)
        if report_id in ids:
            continue
        row_text = el.find_parent("tr")
        ids[report_id] = _extract_date(row_text.get_text(" ", strip=True)) if row_text else None
    return ids


def _extract_date(text: str) -> str | None:
    match = DATE_PATTERN.search(text)
    if not match:
        return None
    year, month, day = match.groups()
    return f"{year}-{month}-{day}"


def _extract_section_html(soup: BeautifulSoup, name_attr: str) -> str:
    """name="{name_attr}_report" summernote 텍스트에어리어를 감싼 form-group 안의
    실제 렌더링된 내용(.note-editable)을 HTML 그대로 반환한다."""
    textarea = soup.find(attrs={"name": f"{name_attr}_report"})
    scope = textarea.find_parent(class_="form-group") if textarea else None
    if scope is None:
        # 혹시 form-group 클래스가 없는 변형이면 상위 div 아무거나로 폴백
        scope = textarea.parent if textarea else soup
    editable = scope.find(class_="note-editable") if scope else None
    if editable is None:
        return ""
    return editable.decode_contents().strip()


def _parse_report_detail(soup: BeautifulSoup, report_id: str, date_hint: str | None) -> dict:
    report: dict = {
        "report_id": report_id,
        "url": f"{config.OFFICE_BASE_URL}/report/view/{report_id}",
    }

    date_input = soup.find(attrs={"name": "report_date"})
    report_date = None
    if date_input is not None:
        report_date = date_input.get("value") or None
    report["report_date"] = report_date or date_hint

    for prefix, label_id, subject_id in LABELED_SECTIONS:
        label = soup.find(id=label_id)
        label_text = label.get_text(strip=True) if label else None
        subject_input = soup.find(id=subject_id)
        subject_value = subject_input.get("value") if subject_input else None
        report[f"{prefix}_label"] = label_text
        report[f"{prefix}_subject"] = subject_value or label_text
        report[f"{prefix}_report"] = _extract_section_html(soup, prefix)

    # "특이사항"(issues)은 name이 "issues_report"가 아니라 "issues" 그대로라서
    # _extract_section_html과 같은 로직을 여기서 직접 반복한다.
    report["issues"] = ""
    issues_textarea = soup.find(attrs={"name": "issues"})
    if issues_textarea is not None:
        scope = issues_textarea.find_parent(class_="form-group") or issues_textarea.parent
        editable = scope.find(class_="note-editable") if scope else None
        report["issues"] = editable.decode_contents().strip() if editable else ""

    return report


def save_reports(target_name: str, reports: list[dict]) -> Path:
    path = reports_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "targetName": target_name,
        "crawledAt": time.time(),
        "reports": reports,
    }
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return path


def load_reports() -> dict | None:
    path = reports_path()
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def load_latest_report() -> dict | None:
    payload = load_reports()
    if not payload:
        return None
    reports = payload.get("reports") or []
    return reports[0] if reports else None
