import argparse
import json
import sys

from .control import ControlState
from .jobs import morning_special_stats
from .utils.progress import emit_log

# 신규 작업(job) 추가 시 여기에 jobId -> run 함수를 등록한다.
JOBS = {
    "morning_special_stats": morning_special_stats.run,
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--job", required=True, choices=list(JOBS.keys()))
    args = parser.parse_args()

    # 첫 줄: Electron이 보낸 작업 설정 JSON (tutors, consultationAfter, classAfter 등)
    first_line = sys.stdin.readline()
    try:
        job_payload = json.loads(first_line)
    except json.JSONDecodeError:
        emit_log("작업 설정(JSON)을 읽지 못했습니다.", level="error")
        sys.exit(1)

    # 이후 stdin은 pause/resume/stop 제어 메시지용
    control = ControlState()
    control.start()

    run_job = JOBS[args.job]
    run_job(job_payload, control)


if __name__ == "__main__":
    main()
