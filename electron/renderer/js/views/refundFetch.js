function renderRefundFetchView(container) {
  container.innerHTML = `
    <div class="view-header">
      <h1>환불 지출결의서</h1>
      <div class="job-controls">
        <button id="start-btn" class="btn btn-primary">조회 시작</button>
      </div>
    </div>

    <section class="panel">
      <div class="field-label">
        구글 시트의 "계좌 환불 (차액 환불 가능)" 섹션에서 "처리유무" 칸이 주황색
        (#FF9900)으로 표시된 건만 가져와 아래 표로 보여줍니다. 이 정보는 이 화면에만
        표시되며 어디로도 전송/저장되지 않습니다.
      </div>
      <div class="log-toolbar">
        <input type="text" id="refund-search" class="roster-search-input" placeholder="회원명/이메일 검색..." />
        <span id="refund-search-count" class="tutor-roster-count"></span>
      </div>
      <table class="dashboard-table" id="refund-table">
        <thead>
          <tr>
            <th>회원명</th>
            <th>회원이메일</th>
            <th>환불금액</th>
            <th>환불사유</th>
            <th>계좌정보</th>
          </tr>
        </thead>
        <tbody id="refund-table-body">
          <tr><td colspan="5" class="empty">아직 조회하지 않았습니다.</td></tr>
        </tbody>
      </table>
      <div class="field-label">
        ⚠ 계좌번호의 '-' 구분은 은행별로 흔히 쓰는 형식을 따른 참고값입니다.
        "확인 필요" 표시가 붙은 계좌는 실제 이체 전 반드시 직접 대조해주세요.
      </div>
    </section>

    <section class="panel">
      <div class="field-label">지출결의서 생성</div>
      <div class="checkbox-row">
        <label for="refund-preparer-name">담당자/청구자 이름</label>
        <input type="text" id="refund-preparer-name" placeholder="예: 이성규" />
      </div>
      <div class="job-controls">
        <button id="generate-btn" class="btn btn-primary" disabled>엑셀 다운로드</button>
      </div>
      <div class="field-label">
        기존에 주신 "지출결의서" 양식 그대로(적요/금액/비고, 22건까지 한 장) 채워서
        만듭니다. 22건이 넘으면 여러 장으로 나눠 각각 저장 대화상자가 뜹니다.
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

  const startBtn = document.getElementById('start-btn');
  const generateBtn = document.getElementById('generate-btn');
  const preparerNameInput = document.getElementById('refund-preparer-name');
  const tableBody = document.getElementById('refund-table-body');
  const refundSearchInput = document.getElementById('refund-search');
  const refundSearchCount = document.getElementById('refund-search-count');

  const logOutput = document.getElementById('log-output');
  const logSearchInput = document.getElementById('log-search');
  const logSearchCount = document.getElementById('log-search-count');

  (async () => {
    const settings = await window.api.getSettings();
    preparerNameInput.value = settings.refundPreparerName || '';
  })();

  preparerNameInput.addEventListener('change', async () => {
    await window.api.setSettings({ refundPreparerName: preparerNameInput.value.trim() });
  });

  // ---- 실행 로그 (검색 필터) ----
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

  // ---- 환불 대상 표 (검색 필터 포함) ----
  let refunds = [];
  let refundSearchQuery = '';

  function accountInfoText(refund) {
    if (!refund.bankName && !refund.accountNumberFormatted) return '(계좌정보 확인 필요)';
    const parts = [refund.bankName, refund.accountNumberFormatted, refund.accountHolder].filter(Boolean);
    return parts.join(' ');
  }

  function updateGenerateButtonState() {
    generateBtn.disabled = refunds.length === 0;
  }

  function renderTable() {
    const query = refundSearchQuery;
    const filtered = refunds.filter((r) => {
      if (!query) return true;
      return `${r.memberName} ${r.memberEmail}`.toLowerCase().includes(query);
    });

    if (refunds.length === 0) {
      tableBody.innerHTML = '<tr><td colspan="5" class="empty">아직 조회하지 않았습니다.</td></tr>';
      refundSearchCount.textContent = '';
      updateGenerateButtonState();
      return;
    }

    if (filtered.length === 0) {
      tableBody.innerHTML = '<tr><td colspan="5" class="empty">검색 결과가 없습니다.</td></tr>';
    } else {
      tableBody.innerHTML = filtered
        .map((r) => {
          const needsReviewBadge = r.needsReview
            ? ' <span class="status-badge status-failed">확인 필요</span>'
            : '';
          return `
            <tr class="${r.needsReview ? 'row-failed' : ''}">
              <td>${escapeHtml(r.memberName) || '-'}</td>
              <td>${escapeHtml(r.memberEmail) || '-'}</td>
              <td>${escapeHtml(r.refundAmount) || '-'}</td>
              <td>${escapeHtml(r.memo) || '-'}</td>
              <td>${escapeHtml(accountInfoText(r))}${needsReviewBadge}</td>
            </tr>
          `;
        })
        .join('');
    }

    if (query) {
      refundSearchCount.textContent = `${filtered.length} / ${refunds.length}건 일치`;
    } else {
      refundSearchCount.textContent = `총 ${refunds.length}건`;
    }
    updateGenerateButtonState();
  }

  function escapeHtml(text) {
    if (!text) return '';
    return String(text)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  refundSearchInput.addEventListener('input', () => {
    refundSearchQuery = refundSearchInput.value.trim().toLowerCase();
    renderTable();
  });

  // ---- 조회 시작 / 엑셀 생성 (같은 job 스트림을 공유하므로 어떤 작업이
  // 진행 중인지 currentJobId로 구분한다) ----
  let currentJobId = null;

  startBtn.addEventListener('click', async () => {
    refunds = [];
    renderTable();
    logOutput.innerHTML = '';

    const result = await window.api.startJob({ jobId: 'refund_fetch' });
    if (!result.started) {
      alert('이미 실행 중인 작업이 있습니다.');
      return;
    }

    currentJobId = 'refund_fetch';
    startBtn.disabled = true;
    generateBtn.disabled = true;
  });

  generateBtn.addEventListener('click', async () => {
    const preparerName = preparerNameInput.value.trim();
    if (!preparerName) {
      alert('담당자/청구자 이름을 입력해주세요.');
      return;
    }
    if (refunds.length === 0) {
      alert('먼저 조회를 실행해주세요.');
      return;
    }

    const result = await window.api.startJob({ jobId: 'refund_generate', refunds, preparerName });
    if (!result.started) {
      alert('이미 실행 중인 작업이 있습니다.');
      return;
    }

    currentJobId = 'refund_generate';
    startBtn.disabled = true;
    generateBtn.disabled = true;
  });

  window.api.onJobLog((data) => {
    appendLog(data.level || 'info', data.message || '');
  });

  window.api.onJobRecord((data) => {
    if (data.kind !== 'refund' || !data.refund) return;
    refunds.push(data.refund);
    renderTable();
  });

  window.api.onJobDone(async (data) => {
    if (typeof data.code === 'undefined') {
      if (currentJobId === 'refund_generate' && data.outputPaths) {
        for (const outputPath of data.outputPaths) {
          const fileName = outputPath.split(/[\\/]/).pop();
          const saveResult = await window.api.saveFileAs(outputPath, fileName);
          if (saveResult.success) {
            appendLog('info', `저장 완료: ${saveResult.savedPath}`);
          } else if (!saveResult.canceled) {
            appendLog('error', `저장 실패: ${saveResult.error || '알 수 없는 오류'}`);
          }
        }
      }
      return;
    }

    appendLog('info', `작업 프로세스 종료 (종료 코드: ${data.code})`);
    startBtn.disabled = false;
    updateGenerateButtonState();
    currentJobId = null;
  });
}

window.renderRefundFetchView = renderRefundFetchView;
