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
    workReportDrafts: {}, // { 'YYYY-MM-DD': { dailyWork, tomorrowPlan, issues } }
  },
});

module.exports = store;
