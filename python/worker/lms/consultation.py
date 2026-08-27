from dataclasses import dataclass
from datetime import date

from ..utils.progress import emit_log

VALID_AUTHORS = {"이성규", "양수아"}
TARGET_STATUS = "보강대기"


class ConsultationLoadError(Exception):
    pass


@dataclass
class ConsultationRecord:
    author: str
    written_date: date
    class_date: date
    status: str


def collect_consultation_records(driver) -> list[ConsultationRecord]:
    """상담관리 화면에서 상담 기록 목록을 파싱한다."""
    emit_log("상담 기록 로딩")

    records: list[ConsultationRecord] = []

    # TODO: 상담 기록 리스트/행 선택자 확정 필요
    # row_elements = driver.find_elements(By.CSS_SELECTOR, "TODO")
    # for row in row_elements:
    #     author = row.find_element(By.CSS_SELECTOR, "TODO").text
    #     written_date = _parse_date(row.find_element(By.CSS_SELECTOR, "TODO").text)
    #     class_date = _parse_date(row.find_element(By.CSS_SELECTOR, "TODO").text)
    #     status = row.find_element(By.CSS_SELECTOR, "TODO").text
    #     records.append(ConsultationRecord(author, written_date, class_date, status))

    # TODO: 상담관리 목록 로딩에 실패했을 때 ConsultationLoadError를 발생시켜야 한다.

    return records


def count_makeup_credits(
    records: list[ConsultationRecord],
    consultation_after: date,
    class_after: date,
) -> int:
    """작성자가 '이성규' 또는 '양수아'이고, 작성일이 consultation_after 이후이며,
    수업일자가 class_after 이후이고, 상태가 '보강대기'인 기록만 카운트한다.
    """
    count = 0
    for record in records:
        if record.author not in VALID_AUTHORS:
            continue
        if record.written_date < consultation_after:
            continue
        if record.class_date < class_after:
            continue
        if record.status != TARGET_STATUS:
            continue
        count += 1
    return count


def _parse_date(text: str) -> date:
    """TODO: 실제 날짜 텍스트 포맷(예: '2026.08.18' 또는 '08/18')을 확인한 뒤 구현."""
    raise NotImplementedError("TODO: 실제 날짜 포맷을 확인한 뒤 구현")
