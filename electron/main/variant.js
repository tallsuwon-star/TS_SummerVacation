// 배포용 exe 빌드 스크립트(scripts/build-overdue-exe.js)가 electron-builder를
// 실행하기 직전에 이 파일의 값을 'overdue_only'로 임시로 바꿔서 빌드하고,
// 빌드가 끝나면 다시 'full'로 되돌려놓는다. 이 파일 자체가 그대로 패키징되므로
// 빌드 시점의 값이 그 실행 파일에 고정된다 (런타임 환경변수에 의존하지 않음).
//
// 'full'         : 지금까지 만든 모든 작업(오전특강 통계/미납자 관리/보카킹 보고 등) 노출
// 'overdue_only' : 동료 배포용 - '미납자 관리'만 노출, Selenium 설치 확인도 숨김
//                  (PyInstaller로 Python까지 exe 안에 다 넣기 때문에 불필요)
module.exports = {
  APP_VARIANT: 'full',
};
