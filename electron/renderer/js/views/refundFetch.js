function renderRefundFetchView(container) {
  container.innerHTML = `
    <div class="view-header">
      <h1>환불/카드취소</h1>
    </div>

    <div class="job-controls" style="margin-bottom: 12px;">
      <button id="tab-refund-btn" class="btn btn-primary">환불</button>
      <button id="tab-card-cancel-btn" class="btn btn-ghost">카드취소</button>
    </div>

    <div id="refund-tab-panel"></div>
    <div id="card-cancel-tab-panel" hidden></div>
  `;

  const refundTabBtn = document.getElementById('tab-refund-btn');
  const cardCancelTabBtn = document.getElementById('tab-card-cancel-btn');
  const refundPanelEl = document.getElementById('refund-tab-panel');
  const cardCancelPanelEl = document.getElementById('card-cancel-tab-panel');

  const refundPanel = buildRefundPanel(refundPanelEl);
  const cardCancelPanel = buildCardCancelPanel(cardCancelPanelEl);

  function activateTab(tab) {
    const isRefund = tab === 'refund';
    refundTabBtn.className = `btn ${isRefund ? 'btn-primary' : 'btn-ghost'}`;
    cardCancelTabBtn.className = `btn ${!isRefund ? 'btn-primary' : 'btn-ghost'}`;
    refundPanelEl.hidden = !isRefund;
    cardCancelPanelEl.hidden = isRefund;
    // job:log/record/done 리스너는 프리로드에서 채널당 하나만 유지되므로,
    // 현재 보이는 탭의 콜백으로 매번 다시 등록해준다.
    if (isRefund) refundPanel.attachListeners();
    else cardCancelPanel.attachListeners();
  }

  refundTabBtn.addEventListener('click', () => activateTab('refund'));
  cardCancelTabBtn.addEventListener('click', () => activateTab('card-cancel'));

  activateTab('refund');
}

// ---- 환불 탭 (기존 지출결의서 조회/생성 기능 그대로) ----
function buildRefundPanel(container) {
  container.innerHTML = `
    <div class="view-header">
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
        내 PC의 "다운로드" 폴더에 바로 저장합니다. 22건이 넘으면 여러 장으로
        나눠 각각 저장됩니다.
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

  const startBtn = container.querySelector('#start-btn');
  const generateBtn = container.querySelector('#generate-btn');
  const preparerNameInput = container.querySelector('#refund-preparer-name');
  const tableBody = container.querySelector('#refund-table-body');
  const refundSearchInput = container.querySelector('#refund-search');
  const refundSearchCount = container.querySelector('#refund-search-count');

  const logOutput = container.querySelector('#log-output');
  const logSearchInput = container.querySelector('#log-search');
  const logSearchCount = container.querySelector('#log-search-count');

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

  function attachListeners() {
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
            appendLog('info', `다운로드 폴더에 저장됨: ${outputPath}`);
            // 파이썬이 이미 다운로드 폴더에 파일을 직접 저장했으니, 탐색기로
            // 위치를 열어주는 것은 확인 차원의 보조 동작일 뿐이다 (실패해도
            // 파일 자체는 이미 다운로드 폴더에 있다).
            window.api.revealFile(outputPath).catch(() => {});
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

  return { attachListeners };
}

// ---- 카드취소 탭 (이메일로 회원 검색 -> LMS 상담관리 화면 자동으로 열기) ----
function buildCardCancelPanel(container) {
  container.innerHTML = `
    <section class="panel">
      <div class="field-label">
        카드 전액취소 전, 구글 시트에 적힌 내용과 회원의 실제 상담관리 기록
        (요청자 일치 여부, 영수증 첨부 여부, 처리 사유)이 서로 맞는지 눈으로
        대조해야 합니다. 아래에 시트의 D열(회원 이메일/ID)을 입력하면 LMS에
        로그인해서 해당 회원의 상담관리 화면까지 자동으로 열어줍니다.
      </div>
      <div class="checkbox-row">
        <label for="card-cancel-email">회원 이메일(ID)</label>
        <input type="text" id="card-cancel-email" placeholder="예: xiaoguai@naver.com" />
      </div>
      <div class="job-controls">
        <button id="card-cancel-open-btn" class="btn btn-primary">상담관리 화면 열기</button>
        <button id="card-cancel-stop-btn" class="btn btn-danger" disabled>확인 종료</button>
      </div>
      <div class="field-label">
        버튼을 누르면 크롬 창이 열리고 LMS 로그인 후 해당 회원의 상담관리
        화면까지 자동으로 이동합니다. 확인이 끝나면 "확인 종료"를 눌러
        브라우저를 닫아주세요.
      </div>
    </section>

    <section class="panel">
      <div class="field-label login-test-label">실행 로그</div>
      <div class="log-toolbar">
        <input type="text" id="card-cancel-log-search" class="roster-search-input" placeholder="로그 검색... (일치하는 줄만 표시)" />
        <span id="card-cancel-log-search-count" class="tutor-roster-count"></span>
      </div>
      <div id="card-cancel-log-output" class="log-output"></div>
    </section>
  `;

  const emailInput = container.querySelector('#card-cancel-email');
  const openBtn = container.querySelector('#card-cancel-open-btn');
  const stopBtn = container.querySelector('#card-cancel-stop-btn');

  const logOutput = container.querySelector('#card-cancel-log-output');
  const logSearchInput = container.querySelector('#card-cancel-log-search');
  const logSearchCount = container.querySelector('#card-cancel-log-search-count');

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

  openBtn.addEventListener('click', async () => {
    const memberEmail = emailInput.value.trim();
    if (!memberEmail) {
      alert('회원 이메일(ID)을 입력해주세요.');
      return;
    }

    logOutput.innerHTML = '';

    const result = await window.api.startJob({ jobId: 'card_cancel_open_consult', memberEmail });
    if (!result.started) {
      alert('이미 실행 중인 작업이 있습니다.');
      return;
    }

    openBtn.disabled = true;
    stopBtn.disabled = false;
  });

  stopBtn.addEventListener('click', async () => {
    await window.api.stopJob();
    stopBtn.disabled = true;
  });

  function attachListeners() {
    window.api.onJobLog((data) => {
      appendLog(data.level || 'info', data.message || '');
    });

    window.api.onJobRecord(() => {});

    window.api.onJobDone((data) => {
      if (typeof data.code === 'undefined') return;
      appendLog('info', `작업 프로세스 종료 (종료 코드: ${data.code})`);
      openBtn.disabled = false;
      stopBtn.disabled = true;
    });
  }

  return { attachListeners };
}

window.renderRefundFetchView = renderRefundFetchView;
