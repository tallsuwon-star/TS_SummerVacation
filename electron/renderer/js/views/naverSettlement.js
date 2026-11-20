function renderNaverSettlementView(container) {
  container.innerHTML = `
    <div class="view-header">
      <h1>네이버 정산 정리</h1>
    </div>

    <section class="panel">
      <div class="field-label">
        네이버 스마트스토어 "정산관리 &gt; 항목별 정산 내역"에서 받은 원본
        엑셀을 업로드하면, 제출용 형식으로 정리합니다: 상품명/정산완료일/
        정산기준금액(A)/Npay 수수료(B)/매출연동 수수료 합계(C)/무이자할부
        수수료(D)/정산상태만 남기고 나머지 열은 빼고, '정산예정금액
        (A+B+C+D)' 열을 추가해 건별로 더한 값을 넣습니다. 정산완료일이
        바뀌는 지점마다 그날 합계 행을, 맨 아래에 전체 합계 행을
        추가합니다.
      </div>
      <div class="job-controls">
        <input type="file" id="settlement-file-input" accept=".xlsx" />
        <button id="settlement-parse-btn" class="btn btn-primary" disabled>읽기</button>
      </div>
    </section>

    <section class="panel">
      <div class="log-toolbar">
        <input type="text" id="settlement-search" class="roster-search-input" placeholder="상품명/정산완료일/정산상태 검색..." />
        <span id="settlement-search-count" class="tutor-roster-count"></span>
      </div>
      <div class="table-wrap" style="overflow-x: auto;">
      <table class="dashboard-table" id="settlement-table">
        <thead>
          <tr>
            <th>상품명</th>
            <th>정산완료일</th>
            <th>정산기준금액(A)</th>
            <th>Npay 수수료(B)</th>
            <th>매출연동 수수료 합계(C)</th>
            <th>무이자할부 수수료(D)</th>
            <th>정산예정금액(A+B+C+D)</th>
            <th>정산상태</th>
          </tr>
        </thead>
        <tbody id="settlement-table-body">
          <tr><td colspan="8" class="empty">아직 업로드하지 않았습니다.</td></tr>
        </tbody>
      </table>
      </div>
      <div class="job-controls">
        <button id="settlement-generate-btn" class="btn btn-primary" disabled>엑셀로 저장</button>
      </div>
      <div class="field-label">
        다운로드 폴더에 "네이버정산정리_YYYY.MM.xlsx" 이름으로 바로
        저장됩니다. 저장 전에 거래처 원장과 일자별/전체 합계 금액을
        대조해주세요.
      </div>
    </section>

    <section class="panel">
      <div class="field-label login-test-label">실행 로그</div>
      <div class="log-toolbar">
        <input type="text" id="settlement-log-search" class="roster-search-input" placeholder="로그 검색... (일치하는 줄만 표시)" />
        <span id="settlement-log-search-count" class="tutor-roster-count"></span>
      </div>
      <div id="settlement-log-output" class="log-output"></div>
    </section>
  `;

  const fileInput = container.querySelector('#settlement-file-input');
  const parseBtn = container.querySelector('#settlement-parse-btn');
  const generateBtn = container.querySelector('#settlement-generate-btn');
  const searchInput = container.querySelector('#settlement-search');
  const searchCount = container.querySelector('#settlement-search-count');
  const tableBody = container.querySelector('#settlement-table-body');

  const logOutput = container.querySelector('#settlement-log-output');
  const logSearchInput = container.querySelector('#settlement-log-search');
  const logSearchCount = container.querySelector('#settlement-log-search-count');

  function escapeHtml(text) {
    if (text === null || text === undefined) return '';
    return String(text)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function formatNumber(value) {
    if (value === null || value === undefined || value === '') return '';
    const num = Number(value);
    return Number.isNaN(num) ? String(value) : num.toLocaleString('ko-KR');
  }

  function formatDate(value) {
    return value === null || value === undefined ? '' : String(value);
  }

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

  // ---- 정리된 정산 표 (검색 필터) ----
  let rows = [];
  let searchQuery = '';

  function updateGenerateButtonState() {
    generateBtn.disabled = rows.length === 0;
  }

  function renderTable() {
    const query = searchQuery;
    const filtered = rows.filter((r) => {
      if (!query) return true;
      return `${r.productName || ''} ${formatDate(r.settleDate)} ${r.status || ''}`.toLowerCase().includes(query);
    });

    const dataCount = rows.filter((r) => r.rowType === 'data').length;

    if (rows.length === 0) {
      tableBody.innerHTML = '<tr><td colspan="8" class="empty">아직 업로드하지 않았습니다.</td></tr>';
      searchCount.textContent = '';
      updateGenerateButtonState();
      return;
    }

    if (filtered.length === 0) {
      tableBody.innerHTML = '<tr><td colspan="8" class="empty">검색 결과가 없습니다.</td></tr>';
    } else {
      tableBody.innerHTML = filtered
        .map((r) => {
          const isSummary = r.rowType === 'subtotal' || r.rowType === 'total';
          const rowClass = isSummary ? 'settlement-summary-row' : '';
          return `
            <tr class="${rowClass}">
              <td>${escapeHtml(r.productName) || ''}</td>
              <td>${escapeHtml(formatDate(r.settleDate))}</td>
              <td>${formatNumber(r.amountA)}</td>
              <td>${formatNumber(r.feeB)}</td>
              <td>${formatNumber(r.feeC)}</td>
              <td>${formatNumber(r.feeD)}</td>
              <td>${formatNumber(r.expectedTotal)}</td>
              <td>${escapeHtml(r.status) || ''}</td>
            </tr>
          `;
        })
        .join('');
    }

    if (query) {
      searchCount.textContent = `${filtered.length} / ${rows.length}행 일치`;
    } else {
      searchCount.textContent = `데이터 ${dataCount}건 (소계/합계 포함 총 ${rows.length}행)`;
    }
    updateGenerateButtonState();
  }

  searchInput.addEventListener('input', () => {
    searchQuery = searchInput.value.trim().toLowerCase();
    renderTable();
  });

  // ---- 파일 선택 / 읽기 ----
  let selectedFilePath = null;

  fileInput.addEventListener('change', () => {
    const file = fileInput.files && fileInput.files[0];
    selectedFilePath = file ? window.api.getPathForFile(file) : null;
    parseBtn.disabled = !selectedFilePath;
  });

  parseBtn.addEventListener('click', async () => {
    if (!selectedFilePath) return;
    rows = [];
    renderTable();
    logOutput.innerHTML = '';

    const result = await window.api.startJob({ jobId: 'naver_settlement_parse', filePath: selectedFilePath });
    if (!result.started) {
      alert('이미 실행 중인 작업이 있습니다. 사이드바 하단 \'실행 중인 작업\'에서 종료할 수 있습니다.');
      return;
    }

    parseBtn.disabled = true;
    generateBtn.disabled = true;
  });

  // ---- 확인 완료 → 엑셀로 저장 (화면에 이미 떠 있는 표 내용 그대로 저장) ----
  generateBtn.addEventListener('click', async () => {
    if (rows.length === 0) {
      alert('먼저 정산 내역 파일을 읽어주세요.');
      return;
    }
    if (!confirm(`표에 보이는 내용을 엑셀로 저장할까요? 저장 전에 거래처 원장과 금액을 꼭 대조해주세요.`)) {
      return;
    }

    const result = await window.api.startJob({ jobId: 'naver_settlement_generate', rows });
    if (!result.started) {
      alert('이미 실행 중인 작업이 있습니다. 사이드바 하단 \'실행 중인 작업\'에서 종료할 수 있습니다.');
      return;
    }

    generateBtn.disabled = true;
  });

  function attachListeners() {
    window.api.onJobLog((data) => {
      appendLog(data.level || 'info', data.message || '');
    });

    window.api.onJobRecord((data) => {
      if (data.kind === 'naver_settlement' && data.naverSettlement) {
        rows.push(data.naverSettlement);
        renderTable();
      }
    });

    window.api.onJobDone(async (data) => {
      if (typeof data.code === 'undefined') {
        if (data.outputPaths) {
          for (const outputPath of data.outputPaths) {
            appendLog('info', `다운로드 폴더에 저장됨: ${outputPath}`);
            window.api.revealFile(outputPath).catch(() => {});
          }
        }
        return;
      }

      appendLog('info', `작업 프로세스 종료 (종료 코드: ${data.code})`);
      parseBtn.disabled = !selectedFilePath;
      updateGenerateButtonState();
    });
  }

  attachListeners();
}

window.renderNaverSettlementView = renderNaverSettlementView;
