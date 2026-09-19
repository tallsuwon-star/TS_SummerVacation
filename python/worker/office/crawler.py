"""office.talkstation.co.kr 업무보고 1회성 크롤링.

/report (검색된 목록) -> 각 /report/view/{id} 페이지를 순회하며, 사용자가
지정한 7개 항목(금일 업무 내용 / 명일 업무 계획 / 지난달 계획 / 이번달 계획 /
지난주 내용 / 다음주 계획 / 특이사항)을 링크·굵게·글자색 등 서식이 살아있는
HTML 그대로 뽑아 JSON으로 저장한다.

/report/view/{id} 페이지의 실제 HTML은 확인하지 못했다 — 사용자가 알려준
/report/write 페이지와 같은 CI4 템플릿(같은 id/name의 summernote 필드들)을
공유한다고 가정하고 작성했다. 만약 view 페이지 구조가 달라 항목이 비어서
저장된다면, view 페이지 HTML을 알려주면 선택자를 맞출 수 있다.
"""

import json
import re
import time
from pathlib import Path
from urllib.parse import quote, urljoin

from bs4 import BeautifulSoup

from .. import config
from ..control import ControlState
from ..utils.progress import emit_log

REPORTS_FILENAME = "reports.json"
MAX_LIST_PAGES = 50

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
    view_links: dict[str, str] = {}  # view URL -> 목록 행에서 뽑은 날짜 힌트

    emit_log(f"'{target_name}' 이름으로 업무보고 목록을 검색합니다.")

    for page in range(1, MAX_LIST_PAGES + 1):
        control.wait_if_paused()
        if control.should_stop():
            emit_log("사용자 요청으로 크롤링을 중단합니다.")
            break

        url = build_list_url(target_name, page)
        driver.get(url)
        time.sleep(config.REQUEST_DELAY_SECONDS)

        soup = BeautifulSoup(driver.page_source, "html.parser")
        page_links = _extract_view_links(soup, driver.current_url)

        new_links = {u: d for u, d in page_links.items() if u not in view_links}
        if not new_links:
            emit_log(f"{page}페이지에 새 항목이 없어 목록 조회를 종료합니다." if page > 1 else "검색 결과가 없습니다.")
            break

        view_links.update(new_links)
        emit_log(f"{page}페이지에서 {len(new_links)}건 발견 (누적 {len(view_links)}건)")

    reports: list[dict] = []
    total = len(view_links)
    for idx, (view_url, date_hint) in enumerate(view_links.items(), start=1):
        control.wait_if_paused()
        if control.should_stop():
            emit_log("사용자 요청으로 크롤링을 중단합니다.")
            break

        emit_log(f"({idx}/{total}) 상세 내용 가져오는 중: {view_url}")
        driver.get(view_url)
        time.sleep(config.REQUEST_DELAY_SECONDS)

        try:
            report = _parse_report_view(BeautifulSoup(driver.page_source, "html.parser"), view_url, date_hint)
            reports.append(report)
        except Exception as exc:  # noqa: BLE001 - 한 건 실패해도 나머지는 계속 진행
            emit_log(f"상세 내용 파싱 실패({view_url}): {exc}", level="error")

    reports.sort(key=lambda r: (r.get("report_date") or "", r.get("report_id") or ""), reverse=True)
    return reports


def _extract_view_links(soup: BeautifulSoup, base_url: str) -> dict[str, str]:
    links: dict[str, str] = {}
    for a in soup.find_all("a", href=True):
        if "/report/view/" not in a["href"]:
            continue
        full_url = urljoin(base_url, a["href"])
        row_text = a.find_parent("tr")
        date_hint = _extract_date(row_text.get_text(" ", strip=True)) if row_text else None
        links[full_url] = date_hint
    return links


def _extract_date(text: str) -> str | None:
    match = DATE_PATTERN.search(text)
    if not match:
        return None
    year, month, day = match.groups()
    return f"{year}-{month}-{day}"


def _report_id_from_url(url: str) -> str | None:
    match = re.search(r"/report/view/(\d+)", url)
    return match.group(1) if match else None


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


def _parse_report_view(soup: BeautifulSoup, url: str, date_hint: str | None) -> dict:
    report: dict = {
        "report_id": _report_id_from_url(url),
        "url": url,
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
