import os
import sys
from pathlib import Path

from dotenv import load_dotenv

if getattr(sys, "frozen", False):
    # PyInstaller로 묶은 배포용 exe로 실행 중. 소스 저장소가 없으므로 실행 파일이
    # 있는 폴더를 기준으로 쓰기 가능한 데이터/로그 경로를 잡는다. 이 경우
    # LMS_ID 등은 .env 파일이 아니라 Electron이 넘겨주는 프로세스 환경변수로
    # 들어오므로 .env를 찾지 않는다.
    ROOT_DIR = Path(sys.executable).resolve().parent
else:
    # python/worker/config.py -> parents[2] == 저장소 루트
    ROOT_DIR = Path(__file__).resolve().parents[2]
    load_dotenv(ROOT_DIR / ".env")

LMS_ID = os.getenv("LMS_ID", "")
LMS_PASSWORD = os.getenv("LMS_PASSWORD", "")

# TODO: 실제 LMS 관리자 페이지 로그인 URL이 확정되면 .env에 채워넣기
LMS_BASE_URL = os.getenv("LMS_BASE_URL", "")

# office.talkstation.co.kr(사내 업무보고 시스템) 자동화. 로그인 계정은 사용자가
# LMS와 같은 것을 쓰기로 해서 별도 입력 없이 LMS_ID/LMS_PASSWORD를 재사용하되,
# Electron이 넘겨주는 환경변수로 OFFICE_ID/OFFICE_PASSWORD가 오면 그걸 우선한다.
OFFICE_ID = os.getenv("OFFICE_ID", "") or LMS_ID
OFFICE_PASSWORD = os.getenv("OFFICE_PASSWORD", "") or LMS_PASSWORD
OFFICE_BASE_URL = os.getenv("OFFICE_BASE_URL", "https://office.talkstation.co.kr")

GOOGLE_SHEETS_CREDENTIALS_PATH = os.getenv("GOOGLE_SHEETS_CREDENTIALS_PATH", "")
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID", "")

# 환불 처리(지출결의서) 자동화가 읽는 "계좌 환불" 기록용 구글 시트.
# 위 GOOGLE_SHEET_ID(보강권 기록용)와는 다른 별도 시트. 이 시트는 링크가
# 있으면 로그인 없이 열람 가능("공개" 상태)이라 서비스 계정/인증 파일 없이
# 공개 다운로드 링크(export?format=xlsx)로 읽으므로 기본값을 넣어두면
# .env에 따로 적지 않아도 동작한다. 필요 시 .env의 REFUND_SHEET_ID로 덮어쓸 수 있다.
REFUND_SHEET_ID = os.getenv("REFUND_SHEET_ID", "1brchNvWyrgqaogcGmEvz_7K50AA-otU6kwHmhwDLQwI")

# 네이버 스마트스토어 자동화 (python/worker/naver/, jobs/naver_store_report.py)
NAVER_ID = os.getenv("NAVER_ID", "")
NAVER_PASSWORD = os.getenv("NAVER_PASSWORD", "")

DATA_DIR = ROOT_DIR / "data"
LOG_DIR = ROOT_DIR / "log"

# 스마트스토어 로그인 세션(쿠키)을 유지하는 영구 크롬 프로필과, 발송처리
# 엑셀을 내려받을 고정 폴더. 둘 다 매 실행 새로 만들지 않고 재사용한다.
NAVER_CHROME_PROFILE_DIR = ROOT_DIR / ".naver-chrome-profile"
NAVER_DOWNLOAD_DIR = ROOT_DIR / "downloads" / "naver_store"

# 요청/클릭 사이 딜레이 (초)
REQUEST_DELAY_SECONDS = 2.5

if not getattr(sys, "frozen", False):
    # .env가 엉뚱한 경로에 있거나(예: 레포 루트가 아닌 하위 폴더), 확장자가
    # 실제로는 ".env.txt"인 경우(메모장으로 저장할 때 흔함) 등을 사용자가
    # 직접 로그로 확인할 수 있게, 매 작업 시작 시 .env 로드 상태를 한 줄 남긴다.
    # 비밀번호 값 자체는 절대 로그에 남기지 않는다.
    from .utils.progress import emit_log as _emit_log

    _env_path = ROOT_DIR / ".env"
    if _env_path.exists():
        _emit_log(
            f".env 로드됨: {_env_path} "
            f"(LMS_ID {'설정됨' if LMS_ID else '비어있음'}, "
            f"LMS_PASSWORD {'설정됨' if LMS_PASSWORD else '비어있음'}, "
            f"LMS_BASE_URL {'설정됨' if LMS_BASE_URL else '비어있음'})"
        )
    else:
        _emit_log(f".env 파일을 찾지 못했습니다. 이 경로에 .env를 만들어주세요: {_env_path}", level="error")
