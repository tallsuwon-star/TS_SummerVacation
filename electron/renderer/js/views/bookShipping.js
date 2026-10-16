function renderBookShippingView(container) {
  container.innerHTML = `
    <div class="view-header">
      <div class="job-controls">
        <button id="book-fetch-btn" class="btn btn-primary">조회 시작</button>
        <button id="book-stop-btn" class="btn btn-danger" disabled>조회 종료</button>
        <button id="book-open-lms-btn" class="btn btn-ghost">LMS 페이지 열기</button>
      </div>
    </div>

    <section class="panel">
      <div class="field-label">
        LMS '교육상품관리 &gt; 교재상품 결제확인' 화면에서 '준비'(아직
        미발송) 상태인 건의 받는분 이름/전화번호/주소를 가져와 아래 표로
        보여줍니다. 이미 '배송중'으로 처리된 건은 가져오지 않습니다.
        <b>엑셀로 저장하기 전에 반드시 "LMS 페이지 열기"로 실제 화면을 함께
        띄워 아래 표의 내용과 대조해주세요.</b>
      </div>
      <div class="checkbox-row">
        <label for="book-address-api-key">도로명주소 확인 API 키 (juso.go.kr 승인키)</label>
        <input type="text" id="book-address-api-key" placeholder="juso.go.kr에서 발급받은 승인키" />
      </div>
      <div class="field-label">
        각 행의 "주소 확인" 버튼을 누르면 행정안전부 도로명주소 오픈API로 그
        주소가 실제 존재하는지 대조합니다. 승인키가 없으면
        <a href="https://www.juso.go.kr" target="_blank" rel="noopener">juso.go.kr</a>에서 무료로 발급받아 입력해주세요.
      </div>
      <div class="log-toolbar">
        <input type="text" id="book-search" class="roster-search-input" placeholder="이름/전화번호/주소 검색..." />
        <span id="book-search-count" class="tutor-roster-count"></span>
      </div>
      <table class="dashboard-table" id="book-table">
        <thead>
          <tr>
            <th>받는분성명</th>
            <th>받는분전화번호</th>
            <th>받는분주소(전체, 분할)</th>
            <th>품목명</th>
            <th>주소 확인</th>
          </tr>
        </thead>
        <tbody id="book-table-body">
          <tr><td colspan="5" class="empty">아직 조회하지 않았습니다.</td></tr>
        </tbody>
      </table>
      <div class="job-controls">
        <button id="book-generate-btn" class="btn btn-primary" disabled>확인 완료 → 엑셀로 저장</button>
      </div>
      <div class="field-label">
        '품목명'은 항상 '서적'으로 고정되어 저장됩니다. 저장되는 엑셀 파일은
        내 PC의 "다운로드" 폴더 아래 오늘 날짜 폴더에 바로 저장됩니다.
      </div>
    </section>

    <section class="panel">
      <div class="view-header">
        <div class="job-controls">
          <input type="file" id="book-invoice-file-input" accept=".xlsx" />
          <button id="book-invoice-parse-btn" class="btn btn-primary" disabled>송장 파일 읽기</button>
        </div>
      </div>
      <div class="field-label">
        택배사 사이트에서 "발송처리" 후 내려받은 송장 엑셀 파일을 선택하면,
        첫 줄(헤더)을 뺀 나머지 데이터 행을 읽어 아래 표로 보여줍니다.
        <b>표 내용을 확인한 뒤 "구글 시트에 기록"을 눌러야 실제로
        기록됩니다.</b> 시트의 현재 마지막 데이터 행 바로 다음 줄부터
        원본 컬럼 그대로 이어붙입니다.
      </div>
      <div class="log-toolbar">
        <input type="text" id="book-invoice-search" class="roster-search-input" placeholder="이름/전화번호/주소/운송장번호 검색..." />
        <span id="book-invoice-search-count" class="tutor-roster-count"></span>
      </div>
      <table class="dashboard-table" id="book-invoice-table">
        <thead>
          <tr>
            <th>받는분</th>
            <th>받는분전화번호</th>
            <th>받는분주소</th>
            <th>운송장번호</th>
          </tr>
        </thead>
        <tbody id="book-invoice-table-body">
          <tr><td colspan="4" class="empty">아직 업로드하지 않았습니다.</td></tr>
        </tbody>
      </table>
      <div class="job-controls">
        <button id="book-invoice-write-btn" class="btn btn-primary" disabled>구글 시트에 기록</button>
      </div>
      <div class="field-label">
        구글 시트의 <a href="https://docs.google.com/spreadsheets/d/1brchNvWyrgqaogcGmEvz_7K50AA-otU6kwHmhwDLQwI/edit?gid=760310768#gid=760310768" target="_blank" rel="noopener">환불/카드취소 시트 - 교재 발송 탭</a>에
        기록합니다. 이 시트에 서비스 계정 이메일이 '편집자'로 공유돼 있어야
        기록이 됩니다.
      </div>
      <div class="job-controls">
        <button id="book-mark-shipped-btn" class="btn btn-primary" disabled>LMS에 배송중 처리</button>
      </div>
      <div class="field-label">
        위 표의 전화번호로 LMS의 '준비' 상태 주문을 찾아 배송상태를
        '배송중'으로 바꾸고 송장번호를 입력해 저장합니다.
        <b>LMS 데이터를 실제로 바꾸는 동작입니다.</b> 전화번호가 같은
        '준비' 주문이 여러 건이거나 일치하는 주문을 못 찾으면 자동으로
        처리하지 않고 "확인 필요"로 표시하니, 그 건은 LMS에서 직접
        처리해주세요.
      </div>
      <table class="dashboard-table" id="book-mark-shipped-table" hidden>
        <thead>
          <tr>
            <th>받는분</th>
            <th>받는분전화번호</th>
            <th>운송장번호</th>
            <th>주문번호</th>
            <th>결과</th>
          </tr>
        </thead>
        <tbody id="book-mark-shipped-table-body"></tbody>
      </table>
    </section>

    <section class="panel">
      <div class="field-label login-test-label">실행 로그</div>
      <div class="log-toolbar">
        <input type="text" id="book-log-search" class="roster-search-input" placeholder="로그 검색... (일치하는 줄만 표시)" />
        <span id="book-log-search-count" class="tutor-roster-count"></span>
      </div>
      <div id="book-log-output" class="log-output"></div>
    </section>
  `;

  const fetchBtn = container.querySelector('#book-fetch-btn');
  const stopBtn = container.querySelector('#book-stop-btn');
  const openLmsBtn = container.querySelector('#book-open-lms-btn');
  const generateBtn = container.querySelector('#book-generate-btn');
  const searchInput = container.querySelector('#book-search');
  const searchCount = container.querySelector('#book-search-count');
  const tableBody = container.querySelector('#book-table-body');
  const addressApiKeyInput = container.querySelector('#book-address-api-key');

  const invoiceFileInput = container.querySelector('#book-invoice-file-input');
  const invoiceParseBtn = container.querySelector('#book-invoice-parse-btn');
  const invoiceWriteBtn = container.querySelector('#book-invoice-write-btn');
  const invoiceSearchInput = container.querySelector('#book-invoice-search');
  const invoiceSearchCount = container.querySelector('#book-invoice-search-count');
  const invoiceTableBody = container.querySelector('#book-invoice-table-body');
  const markShippedBtn = container.querySelector('#book-mark-shipped-btn');
  const markShippedTable = container.querySelector('#book-mark-shipped-table');
  const markShippedTableBody = container.querySelector('#book-mark-shipped-table-body');

  const logOutput = container.querySelector('#book-log-output');
  const logSearchInput = container.querySelector('#book-log-search');
  const logSearchCount = container.querySelector('#book-log-search-count');

  (async () => {
    const settings = await window.api.getSettings();
    addressApiKeyInput.value = settings.roadAddressApiKey || '';
  })();

  addressApiKeyInput.addEventListener('change', async () => {
    await window.api.setSettings({ roadAddressApiKey: addressApiKeyInput.value.trim() });
  });

  function escapeHtml(text) {
    if (!text) return '';
    return String(text)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
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

  // ---- 교재 배송 대상 표 (검색 필터) ----
  let orders = [];
  let searchQuery = '';

  function updateGenerateButtonState() {
    generateBtn.disabled = orders.length === 0;
  }

  function renderTable() {
    const query = searchQuery;
    const filtered = orders.filter((o) => {
      if (!query) return true;
      return `${o.recipientName} ${o.recipientPhone} ${o.recipientAddress}`.toLowerCase().includes(query);
    });

    if (orders.length === 0) {
      tableBody.innerHTML = '<tr><td colspan="5" class="empty">아직 조회하지 않았습니다.</td></tr>';
      searchCount.textContent = '';
      updateGenerateButtonState();
      return;
    }

    if (filtered.length === 0) {
      tableBody.innerHTML = '<tr><td colspan="5" class="empty">검색 결과가 없습니다.</td></tr>';
    } else {
      tableBody.innerHTML = filtered
        .map((o, i) => {
          const needsReviewBadge = o.needsReview
            ? ` <span class="status-badge status-failed">확인 필요</span>`
            : '';
          return `
            <tr class="${o.needsReview ? 'row-failed' : ''}">
              <td>${escapeHtml(o.recipientName) || '-'}${needsReviewBadge}</td>
              <td>${escapeHtml(o.recipientPhone) || '-'}</td>
              <td>${escapeHtml(o.recipientAddress) || '-'}</td>
              <td>서적</td>
              <td>
                <button type="button" class="btn btn-ghost book-check-address-btn" data-index="${i}" ${o.recipientAddress ? '' : 'disabled'}>주소 확인</button>
                <div class="field-label book-address-result" data-index="${i}"></div>
              </td>
            </tr>
          `;
        })
        .join('');
    }

    if (query) {
      searchCount.textContent = `${filtered.length} / ${orders.length}건 일치`;
    } else {
      searchCount.textContent = `총 ${orders.length}건`;
    }
    updateGenerateButtonState();

    tableBody.querySelectorAll('.book-check-address-btn').forEach((btn) => {
      btn.addEventListener('click', async () => {
        const order = filtered[Number(btn.dataset.index)];
        if (!order) return;

        const resultEl = tableBody.querySelector(`.book-address-result[data-index="${btn.dataset.index}"]`);
        const apiKey = addressApiKeyInput.value.trim();
        btn.disabled = true;
        btn.textContent = '확인 중...';
        if (resultEl) resultEl.textContent = '';

        const result = await window.api.checkRoadAddress(order.recipientAddress, apiKey);

        btn.disabled = false;
        btn.textContent = '주소 확인';
        if (resultEl) {
          if (!result.success) {
            resultEl.textContent = `⚠ ${result.error}`;
          } else if (result.matched) {
            resultEl.textContent = `✓ 실제 존재하는 주소입니다 (일치 ${result.totalCount}건)`;
          } else {
            resultEl.textContent = '⚠ 일치하는 도로명주소를 찾지 못했습니다. 직접 확인해주세요.';
          }
        }
      });
    });
  }

  searchInput.addEventListener('input', () => {
    searchQuery = searchInput.value.trim().toLowerCase();
    renderTable();
  });

  // ---- 조회 시작 / 중단 (여러 job이 같은 스트림을 공유하므로 currentJobId로
  // 어떤 작업이 진행 중인지 구분한다) ----
  let currentJobId = null;

  fetchBtn.addEventListener('click', async () => {
    orders = [];
    renderTable();
    logOutput.innerHTML = '';

    const result = await window.api.startJob({ jobId: 'book_fetch' });
    if (!result.started) {
      alert('이미 실행 중인 작업이 있습니다.');
      return;
    }

    currentJobId = 'book_fetch';
    fetchBtn.disabled = true;
    generateBtn.disabled = true;
    stopBtn.disabled = false;
  });

  stopBtn.addEventListener('click', async () => {
    await window.api.stopJob();
    stopBtn.disabled = true;
  });

  // ---- LMS 페이지 직접 열어서 대조 확인 ----
  openLmsBtn.addEventListener('click', async () => {
    const result = await window.api.startJob({ jobId: 'book_open_page' });
    if (!result.started) {
      alert('이미 실행 중인 작업이 있습니다.');
      return;
    }
    currentJobId = 'book_open_page';
    fetchBtn.disabled = true;
    generateBtn.disabled = true;
    stopBtn.disabled = false;
  });

  // ---- 확인 완료 → 엑셀로 저장 (화면에 이미 떠 있는 표 내용 그대로 저장) ----
  generateBtn.addEventListener('click', async () => {
    if (orders.length === 0) {
      alert('먼저 조회를 실행해주세요.');
      return;
    }
    if (!confirm(`표에 보이는 ${orders.length}건을 엑셀로 저장할까요? LMS 페이지와 대조해 내용이 맞는지 꼭 확인해주세요.`)) {
      return;
    }

    const result = await window.api.startJob({ jobId: 'book_generate', orders });
    if (!result.started) {
      alert('이미 실행 중인 작업이 있습니다.');
      return;
    }

    currentJobId = 'book_generate';
    generateBtn.disabled = true;
  });

  // ---- 택배사 송장 엑셀 업로드 → 표로 확인 → 구글 시트에 기록 ----
  let invoiceSelectedFilePath = null;
  let invoiceRows = []; // { recipientName, recipientPhone, recipientAddress, invoiceNo, rawRow }
  let invoiceSearchQuery = '';

  invoiceFileInput.addEventListener('change', () => {
    const file = invoiceFileInput.files && invoiceFileInput.files[0];
    invoiceSelectedFilePath = file ? window.api.getPathForFile(file) : null;
    invoiceParseBtn.disabled = !invoiceSelectedFilePath;
  });

  function updateInvoiceWriteButtonState() {
    invoiceWriteBtn.disabled = invoiceRows.length === 0;
    markShippedBtn.disabled = invoiceRows.length === 0;
  }

  function renderInvoiceTable() {
    const query = invoiceSearchQuery;
    const filtered = invoiceRows.filter((r) => {
      if (!query) return true;
      return `${r.recipientName} ${r.recipientPhone} ${r.recipientAddress} ${r.invoiceNo}`
        .toLowerCase()
        .includes(query);
    });

    if (invoiceRows.length === 0) {
      invoiceTableBody.innerHTML = '<tr><td colspan="4" class="empty">아직 업로드하지 않았습니다.</td></tr>';
      invoiceSearchCount.textContent = '';
      updateInvoiceWriteButtonState();
      return;
    }

    if (filtered.length === 0) {
      invoiceTableBody.innerHTML = '<tr><td colspan="4" class="empty">검색 결과가 없습니다.</td></tr>';
    } else {
      invoiceTableBody.innerHTML = filtered
        .map(
          (r) => `
            <tr>
              <td>${escapeHtml(r.recipientName) || '-'}</td>
              <td>${escapeHtml(r.recipientPhone) || '-'}</td>
              <td>${escapeHtml(r.recipientAddress) || '-'}</td>
              <td>${escapeHtml(r.invoiceNo) || '-'}</td>
            </tr>
          `
        )
        .join('');
    }

    if (query) {
      invoiceSearchCount.textContent = `${filtered.length} / ${invoiceRows.length}건 일치`;
    } else {
      invoiceSearchCount.textContent = `총 ${invoiceRows.length}건`;
    }
    updateInvoiceWriteButtonState();
  }

  invoiceSearchInput.addEventListener('input', () => {
    invoiceSearchQuery = invoiceSearchInput.value.trim().toLowerCase();
    renderInvoiceTable();
  });

  invoiceParseBtn.addEventListener('click', async () => {
    if (!invoiceSelectedFilePath) return;
    invoiceRows = [];
    renderInvoiceTable();
    logOutput.innerHTML = '';

    const result = await window.api.startJob({ jobId: 'book_invoice_parse', filePath: invoiceSelectedFilePath });
    if (!result.started) {
      alert('이미 실행 중인 작업이 있습니다.');
      return;
    }

    currentJobId = 'book_invoice_parse';
    invoiceParseBtn.disabled = true;
    invoiceWriteBtn.disabled = true;
  });

  invoiceWriteBtn.addEventListener('click', async () => {
    if (invoiceRows.length === 0) {
      alert('먼저 송장 파일을 읽어주세요.');
      return;
    }
    if (!confirm(`표에 보이는 ${invoiceRows.length}건을 구글 시트에 기록할까요? 되돌리려면 시트에서 직접 지워야 합니다.`)) {
      return;
    }

    const rows = invoiceRows.map((r) => r.rawRow);
    const result = await window.api.startJob({ jobId: 'book_invoice_write', rows });
    if (!result.started) {
      alert('이미 실행 중인 작업이 있습니다.');
      return;
    }

    currentJobId = 'book_invoice_write';
    invoiceWriteBtn.disabled = true;
  });

  // ---- LMS에 배송중 처리 (전화번호로 '준비' 주문 대조 후 상태+송장번호 저장) ----
  let markShippedResults = [];

  function renderMarkShippedTable() {
    if (markShippedResults.length === 0) {
      markShippedTable.hidden = true;
      return;
    }
    markShippedTable.hidden = false;
    markShippedTableBody.innerHTML = markShippedResults
      .map((r) => {
        const resultCell = r.success
          ? '<span class="status-badge status-success">완료</span>'
          : `<span class="status-badge status-failed">확인 필요</span><br><small>${escapeHtml(r.reason)}</small>`;
        return `
          <tr class="${r.success ? '' : 'row-failed'}">
            <td>${escapeHtml(r.recipientName) || '-'}</td>
            <td>${escapeHtml(r.recipientPhone) || '-'}</td>
            <td>${escapeHtml(r.invoiceNo) || '-'}</td>
            <td>${escapeHtml(r.orderId) || '-'}</td>
            <td>${resultCell}</td>
          </tr>
        `;
      })
      .join('');
  }

  markShippedBtn.addEventListener('click', async () => {
    if (invoiceRows.length === 0) {
      alert('먼저 송장 파일을 읽어주세요.');
      return;
    }
    if (
      !confirm(
        `표에 보이는 ${invoiceRows.length}건의 전화번호로 LMS의 '준비' 주문을 찾아 '배송중'으로 바꾸고 송장번호를 저장할까요?\nLMS 데이터를 실제로 바꾸는 동작입니다.`
      )
    ) {
      return;
    }

    markShippedResults = [];
    renderMarkShippedTable();
    logOutput.innerHTML = '';

    const result = await window.api.startJob({ jobId: 'book_mark_shipped', invoiceRows });
    if (!result.started) {
      alert('이미 실행 중인 작업이 있습니다.');
      return;
    }

    currentJobId = 'book_mark_shipped';
    markShippedBtn.disabled = true;
    stopBtn.disabled = false;
  });

  function attachListeners() {
    window.api.onJobLog((data) => {
      appendLog(data.level || 'info', data.message || '');
    });

    window.api.onJobRecord((data) => {
      if (data.kind === 'book' && data.book) {
        orders.push(data.book);
        renderTable();
        return;
      }
      if (data.kind === 'book_invoice' && data.bookInvoice) {
        invoiceRows.push(data.bookInvoice);
        renderInvoiceTable();
        return;
      }
      if (data.kind === 'book_mark_shipped' && data.bookMarkShipped) {
        markShippedResults.push(data.bookMarkShipped);
        renderMarkShippedTable();
      }
    });

    window.api.onJobDone(async (data) => {
      if (typeof data.code === 'undefined') {
        if (currentJobId === 'book_generate' && data.outputPaths) {
          for (const outputPath of data.outputPaths) {
            appendLog('info', `다운로드 폴더에 저장됨: ${outputPath}`);
            window.api.revealFile(outputPath).catch(() => {});
          }
        }
        if (currentJobId === 'book_invoice_write' && data.writtenCount) {
          appendLog('info', `구글 시트 기록 완료: ${data.writtenCount}건`);
        }
        if (currentJobId === 'book_mark_shipped' && typeof data.succeededCount !== 'undefined') {
          appendLog('info', `LMS 배송중 처리 완료: ${data.succeededCount}/${data.processedCount}건`);
        }
        return;
      }

      appendLog('info', `작업 프로세스 종료 (종료 코드: ${data.code})`);
      fetchBtn.disabled = false;
      stopBtn.disabled = true;
      invoiceParseBtn.disabled = !invoiceSelectedFilePath;
      updateGenerateButtonState();
      updateInvoiceWriteButtonState();
      currentJobId = null;
    });
  }

  attachListeners();
}

window.renderBookShippingView = renderBookShippingView;
