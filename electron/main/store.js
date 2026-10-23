const Store = require('electron-store');

const store = new Store({
  name: 'settings',
  defaults: {
    theme: 'light',
    windowBounds: { width: 1280, height: 840 },
    lastTutorList: '',
    checkedTutors: [],
    criteria: {
      consultationAfter: '2026-08-18',
      classAfter: '2026-08-20',
    },
    // LMS 로그인 정보. .env 파일이 있으면(개발용) 그게 기본값으로 쓰이고,
    // 여기 값이 채워져 있으면 이 값이 우선한다 (배포용 exe는 .env가 없으므로
    // 반드시 이 화면에서 입력해야 함).
    lmsCredentials: {
      id: '',
      password: '',
      baseUrl: 'http://talkstation.co.kr/edu/AD_page/',
    },
    // 업무보고 화면의 부서/작성자(고정값)와 날짜별 작성 중인 내용(임시저장).
    reportProfile: {
      department: '',
      author: '',
    },
    // { 'YYYY-MM-DD': { dailyWork, tomorrowPlan, issues, weeklyWork, weeklyPlan,
    //   workItems: [{ title, progress, decreaseReason }] } }
    workReportDrafts: {},
    // office.talkstation.co.kr에서 크롤링할 때 검색할 이름(마지막 입력값 기억).
    officeReportTargetName: '',
    // 업무보고 "정리하기"(Claude API로 메모 다듬기)에 쓰는 API 키.
    anthropicApiKey: '',
    // 환불 지출결의서에 적을 담당자/청구자 이름(마지막 입력값 기억).
    refundPreparerName: '이성규',
    // 교재 관리 화면의 "주소 확인" 버튼이 쓰는 도로명주소(juso.go.kr) 오픈
    // API 승인키. https://www.juso.go.kr 에서 직접 발급받아 입력해야 한다.
    roadAddressApiKey: '',
    // 아이디어 창고: 카테고리에 아이디어가 이 개수 미만이면 "아이디어 필요"로 표시.
    ideaWarehouseThreshold: 3,
    // 메인 화면 상단 배너에 보여주는 "오늘 할 일" 목록. 매일 같은 시각에 반복된다
    // (date가 아니라 time만 저장) — lastFiredDate/lastCompletedDate로 그날 하루에
    // 대해서만 "이미 띄웠음"/"완료함" 상태를 추적하고, 날짜가 바뀌면 자동으로 초기화된다.
    // [{ id, title, time: "HH:MM", lastFiredDate: "YYYY-MM-DD"|null, lastCompletedDate: "YYYY-MM-DD"|null }]
    todayTasks: [],
  },
});

module.exports = store;
