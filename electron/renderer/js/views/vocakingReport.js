function renderVocakingReportView(container) {
  container.innerHTML = `
    <div class="view-header">
      <h1>보카킹 보고</h1>
    </div>

    <section class="panel">
      <div class="field-label login-test-label">
        통합LMS 이동 테스트 (로그인 → 통합LMS 진입까지만 확인. 이후 단계는 화면 구조 확인 후 이어서 구현 예정)
      </div>
      <div class="inline-row">
        <button id="nav-test-btn" class="btn btn-primary">테스트 시작</button>
        <button id="nav-test-stop-btn" class="btn btn-danger" disabled>중단</button>
        <span id="nav-test-status" class="status-badge status-pending">대기중</span>
      </div>
    </section>

    <section class="panel">
      <div class="field-label login-test-label">실행 로그</div>
      <div class="log-toolbar">
        <input type="text" id="log-search" class="roster-search-input" placeholder="로그 검색... (일치하는 줄만 표시)" />
        <span id="log-search-count" class="tutor-roster-count"></span>
      </div>
      <div id="log-output" class="log-output"></div>
    </section>
  `;

  const navTestBtn = document.getElementById('nav-test-btn');
  const navTestStopBtn = document.getElementById('nav-test-stop-btn');
  const navTestStatus = document.getElementById('nav-test-status');

  const logOutput = document.getElementById('log-output');
  const logSearchInput = document.getElementById('log-search');
  const logSearchCount = document.getElementById('log-search-count');

  let logSearchQuery = '';

  function applyLogLineVisibility(line) {
    const matches = !logSearchQuery || line.textContent.toLowerCase().includes(logSearchQuery);
    line.hidden = !matches;
  }

  function updateLogSearchCount() {
    if (!logSearchQuery) {
      logSearchCount.textContent = '';
      return;
    }
    const total = logOutput.children.length;
    const shown = logOutput.querySelectorAll('.log-line:not([hidden])').length;
    logSearchCount.textContent = `${shown} / ${total}줄 일치`;
  }

  logSearchInput.addEventListener('input', () => {
    logSearchQuery = logSearchInput.value.trim().toLowerCase();
    Array.from(logOutput.children).forEach(applyLogLineVisibility);
    updateLogSearchCount();
  });

  function appendLog(level, message) {
    const line = document.createElement('div');
    line.className = `log-line log-line-${level}`;
    line.textContent = message;
    applyLogLineVisibility(line);
    logOutput.appendChild(line);
    if (!line.hidden) {
      logOutput.scrollTop = logOutput.scrollHeight;
    }
    updateLogSearchCount();
  }

  function setNavTestStatus(label, statusClass) {
    navTestStatus.textContent = label;
    navTestStatus.className = `status-badge status-${statusClass}`;
  }

  navTestBtn.addEventListener('click', async () => {
    const result = await window.api.startJob({ jobId: 'vocaking_report' });
    if (!result.started) {
      alert('이미 실행 중인 작업이 있습니다.');
      return;
    }

    setNavTestStatus('진행 중', 'processing');
    navTestBtn.disabled = true;
    navTestStopBtn.disabled = false;
  });

  navTestStopBtn.addEventListener('click', async () => {
    await window.api.stopJob();
    navTestStopBtn.disabled = true;
  });

  window.api.onJobLog((data) => {
    appendLog(data.level || 'info', data.message || '');
  });

  window.api.onJobDone((data) => {
    if (typeof data.code === 'undefined') return;

    appendLog('info', `작업 프로세스 종료 (종료 코드: ${data.code})`);
    setNavTestStatus(
      data.code === 0 ? '완료 (브라우저 창 확인)' : '실패 (로그 확인)',
      data.code === 0 ? 'success' : 'failed'
    );
    navTestBtn.disabled = false;
    navTestStopBtn.disabled = true;
  });
}

window.renderVocakingReportView = renderVocakingReportView;
