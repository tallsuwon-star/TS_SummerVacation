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

GOOGLE_SHEETS_CREDENTIALS_PATH = os.getenv("GOOGLE_SHEETS_CREDENTIALS_PATH", "")
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID", "")

DATA_DIR = ROOT_DIR / "data"
LOG_DIR = ROOT_DIR / "log"

# 요청/클릭 사이 딜레이 (초)
REQUEST_DELAY_SECONDS = 2.5
