function renderOverdueReportView(container) {
  container.innerHTML = `
    <div class="view-header">
      <h1>미납자 관리</h1>
      <div class="job-controls">
        <button id="start-btn" class="btn btn-primary">시작</button>
        <button id="pause-btn" class="btn btn-ghost" disabled>일시정지</button>
        <button id="stop-btn" class="btn btn-danger" disabled>중단</button>
        <button id="copy-btn" class="btn btn-ghost" disabled>결과 클립보드 복사</button>
      </div>
    </div>

    <section class="panel">
      <div class="field">
        <label class="field-label" for="as-of-date">기준일 (이 날짜까지의 미납자를 조회, 기본: 어제)</label>
        <input type="date" id="as-of-date" />
      </div>
      <div class="field-hint">
        2023.01.01부터 기준일까지 6개월 단위로 조회해 전체 합계를 내고, 기준일 기준 최근 5개월(이번 달은 1일~기준일)도 별도로 조회합니다.
        각 구간의 미납자 명단에서 이름이 실제 사람 같지 않은 회원과, 이름에 "test"가 포함된 담당강사 계정도 함께 찾아 보고서 하단에 표시합니다.
      </div>
    </section>

    <section class="panel">
      <div class="field-label">진행 현황</div>
      <table class="dashboard-table" id="overdue-progress-table">
        <thead>
          <tr><th>구간</th><th>상태</th><th>미납자 수</th></tr>
        </thead>
        <tbody id="overdue-progress-body">
          <tr><td colspan="3" class="empty">아직 시작하지 않았습니다.</td></tr>
        </tbody>
      </table>
    </section>

    <section class="panel" id="overdue-report-panel" hidden>
      <div class="field-label login-test-label">미납자 보고</div>
      <pre id="overdue-report-text" class="log-output"></pre>
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

  const asOfDateInput = document.getElementById('as-of-date');
  const startBtn = document.getElementById('start-btn');
  const pauseBtn = document.getElementById('pause-btn');
  const stopBtn = document.getElementById('stop-btn');
  const copyBtn = document.getElementById('copy-btn');

  const progressBody = document.getElementById('overdue-progress-body');
  const reportPanel = document.getElementById('overdue-report-panel');
  const reportTextEl = document.getElementById('overdue-report-text');

  const logOutput = document.getElementById('log-output');
  const logSearchInput = document.getElementById('log-search');
  const logSearchCount = document.getElementById('log-search-count');

  function yesterdayIso() {
    const d = new Date();
    d.setDate(d.getDate() - 1);
    return d.toISOString().slice(0, 10);
  }

  asOfDateInput.value = yesterdayIso();

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

  // ---- 진행 현황 표 (구간은 작업이 시작돼야 알 수 있어 실시간으로 행을 추가/갱신) ----
  const progressRows = new Map(); // label -> <tr>

  function resetProgressTable() {
    progressRows.clear();
    progressBody.innerHTML = '<tr><td colspan="3" class="empty">진행 중...</td></tr>';
  }

  function upsertProgressRow(label, status, found, reason) {
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
    row.children[2].textContent = status === 'success' ? `${found}명` : status === 'failed' ? (reason || '-') : '-';
  }

  // ---- 시작/일시정지/중단 ----
  let paused = false;
  let lastDoneSummary = null;

  startBtn.addEventListener('click', async () => {
    if (!asOfDateInput.value) {
      alert('기준일을 선택해주세요.');
      return;
    }

    resetProgressTable();
    reportPanel.hidden = true;
    reportTextEl.textContent = '';
    lastDoneSummary = null;
    paused = false;
    pauseBtn.textContent = '일시정지';

    const result = await window.api.startJob({
      jobId: 'overdue_report',
      asOfDate: asOfDateInput.value,
    });
    if (!result.started) {
      alert('이미 실행 중인 작업이 있습니다.');
      return;
    }

    startBtn.disabled = true;
    pauseBtn.disabled = false;
    stopBtn.disabled = false;
    copyBtn.disabled = true;
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

  copyBtn.addEventListener('click', async () => {
    if (!lastDoneSummary) return;
    const result = await window.api.copySummary(lastDoneSummary.reportText);
    copyBtn.textContent = result.success ? '복사됨!' : '복사 실패';
    setTimeout(() => {
      copyBtn.textContent = '결과 클립보드 복사';
    }, 1500);
  });

  window.api.onJobProgress((data) => {
    upsertProgressRow(data.tutor, data.status, data.found, data.reason);
  });

  window.api.onJobLog((data) => {
    appendLog(data.level || 'info', data.message || '');
  });

  window.api.onJobDone((data) => {
    // python worker의 emit_done(요약 정보)과 프로세스 종료(code 있음) 두 번 올 수 있다.
    if (typeof data.code === 'undefined') {
      if (data.summary) {
        lastDoneSummary = data.summary;
        reportPanel.hidden = false;
        reportTextEl.textContent = data.summary.reportText;
      }
      return;
    }

    appendLog('info', `작업 프로세스 종료 (종료 코드: ${data.code})`);

    startBtn.disabled = false;
    pauseBtn.disabled = true;
    stopBtn.disabled = true;
    copyBtn.disabled = !lastDoneSummary;
  });
}

window.renderOverdueReportView = renderOverdueReportView;
