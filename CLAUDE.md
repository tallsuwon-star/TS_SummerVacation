# 개발 규칙

## 목록/로그에는 항상 검색(필터) 기능 넣기

체크박스 명단, 로그 출력, 표 등 항목 수가 많아질 수 있는 UI를 새로 만들 때는
처음부터 검색/필터 입력창을 같이 넣는다. Electron 창은 브라우저 기본 Ctrl+F가
안 먹히므로, 텍스트 입력 후 실시간으로 항목을 필터링하는 자체 검색 기능을
직접 구현해야 한다.

예시: `electron/renderer/js/views/morningSpecialStats.js`의
`tutor-roster-search`(강사 명단 검색), `log-search`(실행 로그 검색) 참고.
