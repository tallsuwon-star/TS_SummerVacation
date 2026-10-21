// 화면(사이드바 메뉴)이 바뀌어도 항상 떠 있는 "실행 중인 작업" 영역.
//
// 기존에는 각 화면(view)마다 자기 job:done 리스너만 가지고 있어서, 다른
// 화면에서 시작한 작업이 실행 중일 때 지금 보고 있는 화면으로 와도 그
// 작업을 끌 방법이 없었다("이미 실행 중인 작업이 있습니다" 알림만 뜨고
// 끝). 어떤 화면을 보고 있든 지금 실행 중인 작업을 바로 끌 수 있도록,
// 사이드바에 항상 떠 있는 상태 표시 + "작업 종료" 버튼을 둔다.

const JOB_LABELS = {
  login_test: '로그인 테스트',
  tutor_search_test: '강사 검색 테스트',
  morning_special_stats: '오전특강 통계 조회',
  overdue_report: '미납자 보고서 조회',
  vocaking_report: '보카킹 보고 조회',
  naver_store_report: '네이버 스토어 보고',
  office_report_crawl: '업무보고 크롤링',
  office_report_submit: '업무보고 제출',
  refund_fetch: '환불 대상 조회',
  refund_generate: '지출결의서 생성',
  refund_open_consult: '환불 상담 확인',
  card_cancel_fetch: '카드취소 대상 조회',
  card_cancel_open_consult: '카드취소 상담 확인',
  expense_write: '지출결의서 자동입력',
  tutor_schedule_set: '강사 시간표 설정',
  book_fetch: '교재 관리 조회',
  book_open_page: 'LMS 교재 페이지 열기',
  book_generate: '교재 배송 엑셀 생성',
  book_invoice_parse: '송장 파일 읽기',
  book_invoice_write: '구글 시트 기록',
  book_mark_shipped: 'LMS 배송중 처리',
};

function jobLabel(jobId) {
  return JOB_LABELS[jobId] || jobId;
}

function initRunningJobStatus() {
  const statusEl = document.getElementById('running-job-status');
  const stopBtn = document.getElementById('running-job-stop-btn');

  function render({ running, jobId }) {
    if (running) {
      statusEl.innerHTML = `<span class="status-badge status-processing">실행 중</span> ${jobLabel(jobId)}`;
      stopBtn.disabled = false;
    } else {
      statusEl.textContent = '실행 중인 작업이 없습니다.';
      stopBtn.disabled = true;
    }
  }

  stopBtn.addEventListener('click', async () => {
    stopBtn.disabled = true;
    await window.api.stopJob();
    // 파이썬 쪽이 신호를 보고 스스로 종료할 때까지는 시간이 걸릴 수 있어,
    // 실제 종료는 onJobStatusChanged(running:false)로 다시 반영된다.
  });

  window.api.onJobStatusChanged((data) => render(data));

  // 화면(렌더러)이 새로 시작될 때, 혹시 이전에 시작된 작업이 이미 돌고
  // 있을 수도 있어 현재 상태를 한 번 물어본다.
  window.api.getJobStatus().then(render);
}

window.initRunningJobStatus = initRunningJobStatus;
