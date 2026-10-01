function renderRefundFetchView(container) {
  container.innerHTML = `
    <div class="view-header">
      <h1>환불/카드취소</h1>
    </div>

    <div class="job-controls" style="margin-bottom: 12px;">
      <button id="tab-refund-btn" class="btn btn-primary">환불</button>
      <button id="tab-card-cancel-btn" class="btn btn-ghost">카드취소</button>
      <button id="tab-expense-write-btn" class="btn btn-ghost">지출결의서 자동입력</button>
    </div>

    <div id="refund-tab-panel"></div>
    <div id="card-cancel-tab-panel" hidden></div>
    <div id="expense-write-tab-panel" hidden></div>
  `;

  const refundTabBtn = document.getElementById('tab-refund-btn');
  const cardCancelTabBtn = document.getElementById('tab-card-cancel-btn');
  const expenseWriteTabBtn = document.getElementById('tab-expense-write-btn');
  const refundPanelEl = document.getElementById('refund-tab-panel');
  const cardCancelPanelEl = document.getElementById('card-cancel-tab-panel');
  const expenseWritePanelEl = document.getElementById('expense-write-tab-panel');

  const refundPanel = buildRefundPanel(refundPanelEl);
  const cardCancelPanel = buildCardCancelPanel(cardCancelPanelEl);
  const expenseWritePanel = buildExpenseWritePanel(expenseWritePanelEl);

  function activateTab(tab) {
    refundTabBtn.className = `btn ${tab === 'refund' ? 'btn-primary' : 'btn-ghost'}`;
    cardCancelTabBtn.className = `btn ${tab === 'card-cancel' ? 'btn-primary' : 'btn-ghost'}`;
    expenseWriteTabBtn.className = `btn ${tab === 'expense-write' ? 'btn-primary' : 'btn-ghost'}`;
    refundPanelEl.hidden = tab !== 'refund';
    cardCancelPanelEl.hidden = tab !== 'card-cancel';
    expenseWritePanelEl.hidden = tab !== 'expense-write';
    // job:log/record/done 리스너는 프리로드에서 채널당 하나만 유지되므로,
    // 현재 보이는 탭의 콜백으로 매번 다시 등록해준다.
    if (tab === 'refund') refundPanel.attachListeners();
    else if (tab === 'card-cancel') cardCancelPanel.attachListeners();
    else expenseWritePanel.attachListeners();
  }

  refundTabBtn.addEventListener('click', () => activateTab('refund'));
  cardCancelTabBtn.addEventListener('click', () => activateTab('card-cancel'));
  expenseWriteTabBtn.addEventListener('click', () => activateTab('expense-write'));

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
          const copyBtn = r.accountNumberFormatted
            ? `<button type="button" class="btn btn-ghost copy-account-btn" data-copy="${escapeHtml(r.accountNumberFormatted)}">복사</button>`
            : '';
          return `
            <tr class="${r.needsReview ? 'row-failed' : ''}">
              <td>${escapeHtml(r.memberName) || '-'}</td>
              <td>${escapeHtml(r.memberEmail) || '-'}</td>
              <td>${escapeHtml(r.refundAmount) || '-'}</td>
              <td>${escapeHtml(r.memo) || '-'}</td>
              <td>${escapeHtml(accountInfoText(r))}${needsReviewBadge} ${copyBtn}</td>
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

  // 표 전체에 한 번만 위임해서 등록 — renderTable이 다시 그려도 버튼 클릭이
  // 계속 동작한다. 계좌번호만 복사해서 뱅킹 앱의 "계좌번호" 입력창에 바로
  // 붙여넣을 수 있게 한다 (직접 옮겨 적다가 숫자를 틀리는 실수 방지용).
  tableBody.addEventListener('click', async (event) => {
    const btn = event.target.closest('.copy-account-btn');
    if (!btn) return;
    const result = await window.api.copySummary(btn.dataset.copy);
    const original = btn.textContent;
    btn.textContent = result.success ? '복사됨!' : '복사 실패';
    setTimeout(() => {
      btn.textContent = original;
    }, 1200);
  });

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

// ---- 카드취소 탭 (구글 시트 "카드 환불" 섹션 조회 -> 체크한 회원들의
// LMS 상담관리 화면을 자동으로 열어 대조 확인) ----
function buildCardCancelPanel(container) {
  container.innerHTML = `
    <div class="view-header">
      <div class="job-controls">
        <button id="cc-fetch-btn" class="btn btn-primary">조회 시작</button>
      </div>
    </div>

    <section class="panel">
      <div class="field-label">
        구글 시트의 "카드 환불" 섹션에서 "처리유무" 칸이 주황색(#FF9900)으로
        표시된 건만 가져와 아래 표로 보여줍니다. 카드 전액취소 전, 시트에
        적힌 내용과 회원의 실제 상담관리 기록(요청자 일치 여부, 영수증 첨부
        여부, 처리 사유)이 서로 맞는지 확인이 필요한 회원을 체크한 뒤
        "선택한 회원 상담관리 열기"를 누르면 LMS에 로그인해서 각 회원의
        상담관리 화면을 열고, 요청자 이름이 같고 최근 7일 이내 작성된 상담
        내용을 찾아 그 안의 신용카드 매출전표(결제시간/구매자명/상품정보)를
        아래에 표로 정리해줍니다. 자동으로 확인이 안 된 건은 반드시 "확인
        필요"로 표시되니, 그 경우는 링크를 열어 직접 대조해주세요.
      </div>
      <div class="log-toolbar">
        <input type="text" id="cc-search" class="roster-search-input" placeholder="회원명/이메일 검색..." />
        <span id="cc-search-count" class="tutor-roster-count"></span>
      </div>
      <table class="dashboard-table" id="cc-table">
        <thead>
          <tr>
            <th><input type="checkbox" id="cc-select-all" /></th>
            <th>회원명</th>
            <th>이메일</th>
            <th>요청자</th>
            <th>환불금액</th>
            <th>사유</th>
            <th>내용</th>
          </tr>
        </thead>
        <tbody id="cc-table-body">
          <tr><td colspan="7" class="empty">아직 조회하지 않았습니다.</td></tr>
        </tbody>
      </table>
      <div class="job-controls">
        <button id="cc-open-consult-btn" class="btn btn-primary" disabled>선택한 회원 상담관리 열기</button>
        <button id="cc-stop-btn" class="btn btn-danger" disabled>확인 종료</button>
      </div>
      <div class="field-label">
        누르면 크롬 창이 열리고 LMS 로그인 후 체크한 회원마다 새 창으로
        상담관리 화면을 하나씩 열어줍니다. 확인이 다 끝나면 "확인 종료"를
        눌러 브라우저를 닫아주세요.
      </div>
    </section>

    <section class="panel" id="cc-receipt-panel" hidden>
      <div class="field-label">
        체크한 회원의 상담관리 화면에서, 요청자 이름이 같고 최근 7일 이내
        작성된 상담 내용을 찾아 그 안의 신용카드 매출전표를 읽어온 결과입니다.
        <b>"확인 필요"로 표시된 건은 자동으로 확인이 안 된 것이니 URL을 직접
        열어 반드시 눈으로 대조해주세요.</b>
      </div>
      <table class="dashboard-table" id="cc-receipt-table">
        <thead>
          <tr>
            <th>회원명</th>
            <th>이메일</th>
            <th>요청자</th>
            <th>결제시간(거래일)</th>
            <th>상품정보</th>
            <th>메모</th>
            <th>비고</th>
            <th>링크</th>
          </tr>
        </thead>
        <tbody id="cc-receipt-table-body"></tbody>
      </table>
    </section>

    <section class="panel">
      <div class="field-label">직접 이메일로 확인</div>
      <div class="checkbox-row">
        <label for="cc-manual-email">회원 이메일(ID)</label>
        <input type="text" id="cc-manual-email" placeholder="예: xiaoguai@naver.com" />
      </div>
      <div class="checkbox-row">
        <label for="cc-manual-requester">요청자 이름 (시트의 요청자, 매출전표 대조용, 생략 가능)</label>
        <input type="text" id="cc-manual-requester" placeholder="예: 김지윤" />
      </div>
      <div class="job-controls">
        <button id="cc-manual-open-btn" class="btn btn-ghost">상담관리 화면 열기</button>
      </div>
      <div class="field-label">
        위 표에 없는 회원을 이메일로 바로 확인하고 싶을 때 사용하세요.
      </div>
    </section>

    <section class="panel">
      <div class="field-label login-test-label">실행 로그</div>
      <div class="log-toolbar">
        <input type="text" id="cc-log-search" class="roster-search-input" placeholder="로그 검색... (일치하는 줄만 표시)" />
        <span id="cc-log-search-count" class="tutor-roster-count"></span>
      </div>
      <div id="cc-log-output" class="log-output"></div>
    </section>
  `;

  const fetchBtn = container.querySelector('#cc-fetch-btn');
  const searchInput = container.querySelector('#cc-search');
  const searchCount = container.querySelector('#cc-search-count');
  const tableBody = container.querySelector('#cc-table-body');
  const selectAllCheckbox = container.querySelector('#cc-select-all');
  const openConsultBtn = container.querySelector('#cc-open-consult-btn');
  const stopBtn = container.querySelector('#cc-stop-btn');
  const manualEmailInput = container.querySelector('#cc-manual-email');
  const manualRequesterInput = container.querySelector('#cc-manual-requester');
  const manualOpenBtn = container.querySelector('#cc-manual-open-btn');
  const receiptPanel = container.querySelector('#cc-receipt-panel');
  const receiptTableBody = container.querySelector('#cc-receipt-table-body');

  const logOutput = container.querySelector('#cc-log-output');
  const logSearchInput = container.querySelector('#cc-log-search');
  const logSearchCount = container.querySelector('#cc-log-search-count');

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

  function escapeHtml(text) {
    if (!text) return '';
    return String(text)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  // ---- 카드취소 대상 표 (체크박스 + 검색 필터) ----
  let cardCancels = []; // { memberName, memberEmail, requester, refundAmount, reasonType, detail }
  let checkedEmails = new Set();
  let searchQuery = '';

  function updateActionButtonsState() {
    openConsultBtn.disabled = checkedEmails.size === 0;
  }

  function renderTable() {
    const query = searchQuery;
    const filtered = cardCancels.filter((c) => {
      if (!query) return true;
      return `${c.memberName} ${c.memberEmail}`.toLowerCase().includes(query);
    });

    if (cardCancels.length === 0) {
      tableBody.innerHTML = '<tr><td colspan="7" class="empty">아직 조회하지 않았습니다.</td></tr>';
      searchCount.textContent = '';
      updateActionButtonsState();
      return;
    }

    if (filtered.length === 0) {
      tableBody.innerHTML = '<tr><td colspan="7" class="empty">검색 결과가 없습니다.</td></tr>';
    } else {
      tableBody.innerHTML = filtered
        .map((c, i) => {
          const checked = checkedEmails.has(c.memberEmail) ? 'checked' : '';
          return `
            <tr>
              <td><input type="checkbox" class="cc-row-check" data-email="${escapeHtml(c.memberEmail)}" ${checked} /></td>
              <td>${escapeHtml(c.memberName) || '-'}</td>
              <td>${escapeHtml(c.memberEmail) || '-'}</td>
              <td>${escapeHtml(c.requester) || '-'}</td>
              <td>${escapeHtml(c.refundAmount) || '-'}</td>
              <td>${escapeHtml(c.reasonType) || '-'}</td>
              <td>${escapeHtml(c.detail) || '-'}</td>
            </tr>
          `;
        })
        .join('');
    }

    tableBody.querySelectorAll('.cc-row-check').forEach((checkbox) => {
      checkbox.addEventListener('change', () => {
        const email = checkbox.dataset.email;
        if (checkbox.checked) checkedEmails.add(email);
        else checkedEmails.delete(email);
        updateActionButtonsState();
      });
    });

    if (query) {
      searchCount.textContent = `${filtered.length} / ${cardCancels.length}건 일치`;
    } else {
      searchCount.textContent = `총 ${cardCancels.length}건`;
    }
    updateActionButtonsState();
  }

  searchInput.addEventListener('input', () => {
    searchQuery = searchInput.value.trim().toLowerCase();
    renderTable();
  });

  selectAllCheckbox.addEventListener('change', () => {
    if (selectAllCheckbox.checked) {
      cardCancels.forEach((c) => checkedEmails.add(c.memberEmail));
    } else {
      checkedEmails.clear();
    }
    renderTable();
  });

  // ---- 매출전표 대조 결과 (회원별로 묶어서 표시) ----
  let receiptChecks = []; // { memberName, memberEmail, requester, found, needsReview, reviewReason, ... }

  function renderReceiptTable() {
    if (receiptChecks.length === 0) {
      receiptPanel.hidden = true;
      return;
    }
    receiptPanel.hidden = false;

    const sorted = [...receiptChecks].sort((a, b) => (a.memberEmail || '').localeCompare(b.memberEmail || ''));

    receiptTableBody.innerHTML = sorted
      .map((r) => {
        const fields = r.receiptFields || {};
        const verdict = r.matchVerdict || (r.needsReview ? '확인 필요' : '-');
        const verdictClass =
          verdict === '일치' ? 'status-success' : verdict === '불일치' ? 'status-failed' : 'status-processing';
        const verdictNote = r.matchNote ? `<br><small>${escapeHtml(r.matchNote)}</small>` : '';
        const reviewReason =
          r.needsReview && r.reviewReason ? `<br><small>${escapeHtml(r.reviewReason)}</small>` : '';
        const remarks = `<span class="status-badge ${verdictClass}">${escapeHtml(verdict)}</span>${verdictNote}${reviewReason}`;
        const link = r.detailUrl
          ? `<button type="button" class="btn btn-ghost cc-open-link" data-url="${escapeHtml(r.detailUrl)}">열기</button>`
          : '-';
        return `
          <tr class="${r.needsReview ? 'row-failed' : ''}">
            <td>${escapeHtml(r.memberName) || '-'}</td>
            <td>${escapeHtml(r.memberEmail) || '-'}</td>
            <td>${escapeHtml(r.requester) || '-'}</td>
            <td>${escapeHtml(fields['거래일자']) || '-'}</td>
            <td>${escapeHtml(fields['상품명']) || '-'}</td>
            <td>${escapeHtml(r.personalNote) || '-'}</td>
            <td>${remarks}</td>
            <td>${link}</td>
          </tr>
        `;
      })
      .join('');

    receiptTableBody.querySelectorAll('.cc-open-link').forEach((btn) => {
      btn.addEventListener('click', () => {
        window.api.openExternal(btn.dataset.url);
      });
    });
  }

  // ---- 조회 시작 / 선택 회원 상담관리 열기 ----
  fetchBtn.addEventListener('click', async () => {
    cardCancels = [];
    checkedEmails.clear();
    selectAllCheckbox.checked = false;
    receiptChecks = [];
    renderTable();
    renderReceiptTable();
    logOutput.innerHTML = '';

    const result = await window.api.startJob({ jobId: 'card_cancel_fetch' });
    if (!result.started) {
      alert('이미 실행 중인 작업이 있습니다.');
      return;
    }

    fetchBtn.disabled = true;
  });

  async function startConsultJob(targets) {
    logOutput.innerHTML = '';
    receiptChecks = [];
    renderReceiptTable();

    const result = await window.api.startJob({ jobId: 'card_cancel_open_consult', targets });
    if (!result.started) {
      alert('이미 실행 중인 작업이 있습니다.');
      return;
    }
    fetchBtn.disabled = true;
    openConsultBtn.disabled = true;
    manualOpenBtn.disabled = true;
    stopBtn.disabled = false;
  }

  openConsultBtn.addEventListener('click', () => {
    if (checkedEmails.size === 0) {
      alert('먼저 확인할 회원을 체크해주세요.');
      return;
    }
    const targets = cardCancels
      .filter((c) => checkedEmails.has(c.memberEmail))
      .map((c) => ({
        memberEmail: c.memberEmail,
        memberName: c.memberName,
        requester: c.requester,
        refundAmount: c.refundAmount,
      }));
    startConsultJob(targets);
  });

  manualOpenBtn.addEventListener('click', () => {
    const email = manualEmailInput.value.trim();
    if (!email) {
      alert('회원 이메일(ID)을 입력해주세요.');
      return;
    }
    const requester = manualRequesterInput.value.trim();
    startConsultJob([{ memberEmail: email, memberName: '', requester }]);
  });

  stopBtn.addEventListener('click', async () => {
    await window.api.stopJob();
    stopBtn.disabled = true;
  });

  function attachListeners() {
    window.api.onJobLog((data) => {
      appendLog(data.level || 'info', data.message || '');
    });

    window.api.onJobRecord((data) => {
      if (data.kind === 'card_cancel' && data.cardCancel) {
        cardCancels.push(data.cardCancel);
        renderTable();
        return;
      }
      if (data.kind === 'receipt_check' && data.receiptCheck) {
        receiptChecks.push(data.receiptCheck);
        renderReceiptTable();
      }
    });

    window.api.onJobDone((data) => {
      if (typeof data.code === 'undefined') return;
      appendLog('info', `작업 프로세스 종료 (종료 코드: ${data.code})`);
      fetchBtn.disabled = false;
      manualOpenBtn.disabled = false;
      stopBtn.disabled = true;
      updateActionButtonsState();
    });
  }

  return { attachListeners };
}

// ---- 지출결의서 자동입력 탭 (사용자가 검수한 지출결의서 엑셀을 읽어
// office.talkstation.co.kr 지출결의서 작성 화면에 거래처/상세/거래금액을
// 자동으로 입력. "제출하기"는 절대 누르지 않고 사용자가 직접 확인 후 제출) ----
function buildExpenseWritePanel(container) {
  container.innerHTML = `
    <div class="view-header">
      <div class="job-controls">
        <input type="file" id="ew-file-input" accept=".xlsx" />
        <button id="ew-start-btn" class="btn btn-primary" disabled>작성 시작</button>
        <button id="ew-stop-btn" class="btn btn-danger" disabled>중단</button>
      </div>
    </div>

    <section class="panel">
      <div class="field-label">
        오늘 처리한 환불 건을 정리해둔 지출결의서 엑셀 파일을 선택하면, 크롬
        창을 열어 office.talkstation.co.kr의 "지출결의서 작성" 화면에
        회원별로 거래처(회원명)/상세(사유 및 계좌정보)/거래금액을 순서대로
        입력해줍니다. 날짜는 오늘 날짜로 채워집니다.
        <b>"제출하기"는 절대 누르지 않으니, 화면에서 직접 내용을 확인한 뒤
        본인이 눌러 제출해주세요.</b> 입력이 끝나도 브라우저는 그대로
        열려있으니, 확인이 끝나면 "중단"을 눌러 종료해주세요.
      </div>
    </section>

    <section class="panel">
      <div class="field-label login-test-label">실행 로그</div>
      <div id="ew-log-output" class="log-output"></div>
    </section>
  `;

  const fileInput = container.querySelector('#ew-file-input');
  const startBtn = container.querySelector('#ew-start-btn');
  const stopBtn = container.querySelector('#ew-stop-btn');
  const logOutput = container.querySelector('#ew-log-output');

  let selectedFilePath = null;

  fileInput.addEventListener('change', () => {
    const file = fileInput.files && fileInput.files[0];
    selectedFilePath = file ? window.api.getPathForFile(file) : null;
    startBtn.disabled = !selectedFilePath;
  });

  function appendLog(level, message) {
    const line = document.createElement('div');
    line.className = `log-line log-line-${level}`;
    line.textContent = message;
    logOutput.appendChild(line);
    logOutput.scrollTop = logOutput.scrollHeight;
  }

  startBtn.addEventListener('click', async () => {
    if (!selectedFilePath) return;
    logOutput.innerHTML = '';

    const result = await window.api.startJob({ jobId: 'expense_write', filePath: selectedFilePath });
    if (!result.started) {
      alert('이미 실행 중인 작업이 있습니다.');
      return;
    }

    startBtn.disabled = true;
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
      startBtn.disabled = !selectedFilePath;
      stopBtn.disabled = true;
    });
  }

  return { attachListeners };
}

window.renderRefundFetchView = renderRefundFetchView;
