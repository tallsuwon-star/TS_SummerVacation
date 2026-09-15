function renderNaverStoreReportView(container) {
  container.innerHTML = `
    <div class="view-header">
      <h1>네이버 스토어</h1>
      <div class="job-controls">
        <button id="start-btn" class="btn btn-primary">시작</button>
        <button id="pause-btn" class="btn btn-ghost" disabled>일시정지</button>
        <button id="stop-btn" class="btn btn-danger" disabled>중단</button>
      </div>
    </div>

    <section class="panel">
      <p class="field-hint" style="margin-top: 0;">
        .env의 NAVER_ID / NAVER_PASSWORD로 로그인합니다 (이미 로그인 세션이 있으면 건너뜁니다).
        실행되는 동안 자동 제어 중인 크롬 창이 화면에 표시되며, 캡챠 등 추가 인증이 뜨면
        해당 창에서 직접 완료해 주세요. 완료되면 자동으로 이어서 진행됩니다.
        (테스트 단계: 아직 발주(주문)확인/발송관리 페이지 진입까지만 확인합니다.)
      </p>
      <table class="dashboard-table" id="naver-progress-table">
        <thead>
          <tr><th>단계</th><th>상태</th><th>비고</th></tr>
        </thead>
        <tbody id="naver-progress-body">
          <tr><td colspan="3" class="empty">아직 시작하지 않았습니다.</td></tr>
        </tbody>
      </table>
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

  const startBtn = document.getElementById('start-btn');
  const pauseBtn = document.getElementById('pause-btn');
  const stopBtn = document.getElementById('stop-btn');

  const progressBody = document.getElementById('naver-progress-body');
  const logOutput = document.getElementById('log-output');
  const logSearchInput = document.getElementById('log-search');
  const logSearchCount = document.getElementById('log-search-count');

  // ---- 실행 로그 (검색 필터 포함) ----
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

  // ---- 진행 현황 표 (로그인 / 발주(주문)확인/발송관리, 두 단계) ----
  const progressRows = new Map();

  function resetProgressTable() {
    progressRows.clear();
    progressBody.innerHTML = '<tr><td colspan="3" class="empty">진행 중...</td></tr>';
  }

  function upsertProgressRow(label, status, reason) {
    if (progressRows.size === 0) {
      progressBody.innerHTML = '';
    }

    let row = progressRows.get(label);
    if (!row) {
      row = document.createElement('tr');
      row.innerHTML = '<td></td><td></td><td></td>';
      progressBody.appendChild(row);
      progressRows.set(label, row);
    }

    const statusLabel = { processing: '진행중', success: '완료', failed: '실패' }[status] || status;
    row.className = status === 'failed' ? 'row-failed' : '';
    row.children[0].textContent = label;
    row.children[1].innerHTML = `<span class="status-badge status-${status}">${statusLabel}</span>`;
    row.children[2].textContent = status === 'failed' ? reason || '-' : '-';
  }

  // ---- 시작/일시정지/중단 ----
  let paused = false;

  startBtn.addEventListener('click', async () => {
    resetProgressTable();
    paused = false;
    pauseBtn.textContent = '일시정지';

    const result = await window.api.startJob({ jobId: 'naver_store_report' });
    if (!result.started) {
      alert('이미 실행 중인 작업이 있습니다.');
      return;
    }

    startBtn.disabled = true;
    pauseBtn.disabled = false;
    stopBtn.disabled = false;
  });

  pauseBtn.addEventListener('click', async () => {
    if (!paused) {
      await window.api.pauseJob();
      paused = true;
      pauseBtn.textContent = '재개';
    } else {
      await window.api.resumeJob();
      paused = false;
      pauseBtn.textContent = '일시정지';
    }
  });

  stopBtn.addEventListener('click', async () => {
    await window.api.stopJob();
    stopBtn.disabled = true;
    pauseBtn.disabled = true;
  });

  window.api.onJobProgress((data) => {
    upsertProgressRow(data.tutor, data.status, data.reason);
  });

  window.api.onJobLog((data) => {
    appendLog(data.level || 'info', data.message || '');
  });

  window.api.onJobDone((data) => {
    // python worker의 emit_done(요약 정보)과 프로세스 종료(code 있음) 두 번 올 수 있다.
    if (typeof data.code === 'undefined') {
      if (data.summary) {
        const s = data.summary;
        appendLog(
          'info',
          `결과: 로그인 ${s.loggedIn ? '성공' : '실패'} / 발주(주문)확인·발송관리 진입 ${
            s.reachedDeliveryPage ? '성공' : '실패'
          }${s.stopped ? ' (사용자 중단)' : ''}`
        );
      }
      return;
    }

    appendLog('info', `작업 프로세스 종료 (종료 코드: ${data.code})`);

    startBtn.disabled = false;
    pauseBtn.disabled = true;
    stopBtn.disabled = true;
  });
}

window.renderNaverStoreReportView = renderNaverStoreReportView;
