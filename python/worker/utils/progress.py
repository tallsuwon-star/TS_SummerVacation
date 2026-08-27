import json
import sys


def emit(payload: dict) -> None:
    """Electron 메인 프로세스가 한 줄씩 파싱할 수 있도록 JSON을 stdout에 출력하고 즉시 flush한다."""
    sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def emit_progress(tutor: str, status: str, found: int | None = None, reason: str | None = None) -> None:
    """status: pending | processing | success | failed"""
    payload = {"type": "progress", "tutor": tutor, "status": status}
    if found is not None:
        payload["found"] = found
    if reason is not None:
        payload["reason"] = reason
    emit(payload)


def emit_log(message: str, level: str = "info") -> None:
    emit({"type": "log", "level": level, "message": message})


def emit_done(summary: dict) -> None:
    emit({"type": "done", "summary": summary})
