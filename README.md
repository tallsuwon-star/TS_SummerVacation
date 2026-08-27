# LMS 보강권 자동화

LMS 관리자 페이지를 강사별로 순회하며 회원들에게 지급된 보강권 수를 확인해
구글 시트에 자동 기록하는 사내 자동화 도구. 개인용 + 매니저 1명, 총 2명이
각자 PC에서 사용.

## 기술 스택

- Frontend/실행파일: Electron + electron-store
- 자동화: Python 3.x + Selenium 4.6+ (Selenium Manager로 드라이버 자동 관리, headless 금지)
- 결과 저장: Google Sheets (gspread + 서비스 계정 인증)
- Electron ↔ Python 통신: `child_process.spawn`으로 Python 워커 실행,
  Python은 stdout에 진행 상황을 한 줄씩 JSON으로 출력
  (`{"type":"progress","tutor":"김민지","status":"success","found":3}`)
- 클립보드 복사: pyperclip (Python 스크립트를 통해 처리)

## 폴더 구조

```
electron/                 Electron 프론트
  main/                    메인 프로세스 (창 생성, IPC, python 워커 spawn)
  renderer/                렌더러 (사이드바, 대시보드, 각 작업 화면)
python/                   자동화 워커 (Electron과 완전 분리)
  worker/
    main.py                entrypoint (--job, stdin으로 설정 JSON 수신)
    control.py             일시정지/중단 제어
    lms/                   LMS 화면 조작 (로그인, 네비게이션, 강사검색, 시간표, 회원팝업, 상담관리)
    sheets/                구글 시트 연동
    jobs/                  작업 오케스트레이션 (오전특강 통계 등)
    utils/                 progress emit, /data 백업, clipboard(pyperclip)
data/                     작업 결과 백업 (/data/YYYYMMDD/작업명.json, gitignore)
log/                      실행 로그 (gitignore)
```

새 작업을 추가할 때:
1. `python/worker/jobs/`에 새 작업 파일 추가, `worker/main.py`의 `JOBS`에 등록
2. `electron/renderer/js/views/`에 새 뷰 파일 추가, `app.js`의 `VIEW_RENDERERS`에 등록
3. `electron/renderer/js/sidebar.js`의 `JOBS` 배열에 사이드바 항목 추가

## 초기 설정

```bash
npm install

python3 -m venv .venv          # (선택) 가상환경
source .venv/bin/activate
pip install -r python/requirements.txt

cp .env.example .env           # 이미 생성되어 있음. 값만 채우기
```

`.env`에 채워야 하는 값:

- `LMS_ID`, `LMS_PASSWORD`
- `LMS_BASE_URL` (TODO: 실제 로그인 페이지 URL 확정 필요)
- `GOOGLE_SHEETS_CREDENTIALS_PATH` (서비스 계정 JSON 경로)
- `GOOGLE_SHEET_ID`

## 실행

```bash
npm start
```

사이드바 "설치가 필요한 목록"에서 Selenium 미설치가 감지되면 클릭 후
설치 확인 팝업에서 확인을 누르면 `pip install -r python/requirements.txt`가
자동 실행된다.

## 현재 상태 / 다음 단계

`python/worker/lms/*.py`의 각 함수는 구조와 TODO만 잡혀 있고, 실제 LMS 화면의
CSS 선택자는 아직 채워지지 않았다. 다음 단계에서 실제 화면을 보면서
`driver.find_element(...)` 부분을 채워 넣으면 된다.
