import os
from pathlib import Path

from dotenv import load_dotenv

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
