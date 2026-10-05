// 원어민 강사 명단. 'TL '로 시작하는 이름은 직급 강사라 명단에서 아예 뺐고,
// '(WFH)'는 재택근무 표시일 뿐 실제 강사명이 아니라서 이름만 남기고 뗐다.
const TUTOR_ROSTER = [
  'Sadie', 'Chen', 'Tami', 'Angelo', 'Sana', 'Sedona', 'Aida', 'Jerome', 'Fria',
  'Tracy', 'Zarinna', 'Denver', 'Maddie', 'Veera', 'Arlene', 'Agatha', 'Athena',
  'Alodia', 'Lander', 'Melia', 'Rhen', 'Minerva', 'Amber', 'Cassie', 'Avida',
  'Brook', 'Abegail', 'Apple', 'Kinsley', 'Kristine', 'John', 'Tine', 'Lindsay',
  'Lucille', 'Jojo', 'Howie', 'Lydia', 'Mayen', 'Sera', 'Destiny', 'Cyrel', 'Jem',
  'Loki', 'Bam', 'Stella', 'Rio', 'Sophie', 'Kesiah', 'Fawn', 'Emcee', 'Pamela',
  'Goldie', 'Calista', 'Camille', 'Pearl', 'Piper', 'Khim', 'Eco', 'Claire',
  'Janrey', 'Joan', 'Jasper', 'Rick', 'Felin', 'Joice', 'Oscar', 'Olive', 'Wesley',
  'Selena', 'Nicole', 'Sheila', 'Enid', 'Jena', 'Jerrica', 'Mariel', 'Michelle',
  'Missy', 'Karen', 'Zoey', 'Fen', 'Clara', 'Kenny', 'Angie', 'Mary', 'Bea',
  'Zelina', 'Amelie', 'Carmit', 'Pops', 'Wency', 'Cassandra', 'Veron',
];

// 강사 시간표 화면은 09시~23시까지, 각 시간마다 정시(00분)/30분 두 수업 슬롯이 있다.
const TUTOR_SCHEDULE_SLOTS = [];
for (let hour = 9; hour <= 23; hour++) {
  for (const minute of [0, 30]) {
    TUTOR_SCHEDULE_SLOTS.push({
      hour,
      minute,
      label: `${String(hour).padStart(2, '0')}:${String(minute).padStart(2, '0')}`,
    });
  }
}

function renderMorningSpecialStatsView(container) {
  container.innerHTML = `
    <section class="panel">
      <div class="field-label login-test-label">LMS 로그인 테스트 (강사 명단 없이 먼저 확인)</div>
      <div class="inline-row">
        <button id="login-test-btn" class="btn btn-primary">로그인 테스트 시작</button>
        <button id="login-test-stop-btn" class="btn btn-danger" disabled>중단</button>
        <span id="login-test-status" class="status-badge status-pending">대기중</span>
      </div>
    </section>

    <section class="panel">
      <div class="field-label login-test-label">강사검색 + 보강권 확인 테스트 (로그인 → 시간표관리 → 검색 → SCH → 오전 전환 → 회원 명단 → 회원별 상담관리 보강권 건수, 위 기준일 사용)</div>
      <div class="inline-row">
        <input type="text" id="tutor-search-test-name" placeholder="강사 이름 (예: Daheetest)" value="Daheetest" />
        <button id="tutor-search-test-btn" class="btn btn-primary">여기까지 테스트</button>
        <button id="tutor-search-test-stop-btn" class="btn btn-danger" disabled>중단</button>
        <span id="tutor-search-test-status" class="status-badge status-pending">대기중</span>
      </div>
    </section>

    <section class="panel">
      <div class="field-label login-test-label">강사 블랙/그레이/화이트 타임 설정 (로그인 → 시간표관리 → 검색 → SCH → 체크박스 설정 → 작성완료 제출까지 자동)</div>
      <div class="tutor-roster-actions">
        <input type="text" id="black-time-roster-input" placeholder="강사 이름 추가 (예: Daheetest)" />
        <button id="black-time-roster-add-btn" type="button" class="btn btn-ghost">추가</button>
      </div>
      <div id="black-time-roster-list" class="black-time-roster-list"></div>
      <div class="inline-row">
        <select id="tutor-time-test-weekday">
          <option value="0">일</option>
          <option value="1">월</option>
          <option value="2">화</option>
          <option value="3">수</option>
          <option value="4">목</option>
          <option value="5">금</option>
          <option value="6">토</option>
        </select>
        <span>요일을</span>
        <select id="tutor-time-test-state">
          <option value="open">열기 (화이트 타임)</option>
          <option value="close">닫기 (블랙+그레이 체크)</option>
        </select>
      </div>

      <div class="field-label">적용할 수업 시간 선택 (체크한 시간에만 적용됩니다)</div>
      <div class="tutor-roster-actions">
        <input type="text" id="tutor-slot-search" class="roster-search-input" placeholder="시간 검색... (예: 10:)" />
        <button id="tutor-slot-select-all-btn" type="button" class="btn btn-ghost">전체 선택</button>
        <button id="tutor-slot-deselect-all-btn" type="button" class="btn btn-ghost">전체 해제</button>
        <select id="tutor-slot-range-start"></select>
        <span>~</span>
        <select id="tutor-slot-range-end"></select>
        <button id="tutor-slot-range-btn" type="button" class="btn btn-ghost">범위 선택</button>
      </div>
      <div id="tutor-slot-grid" class="tutor-roster-grid"></div>
      <div id="tutor-slot-summary" class="field-hint">선택된 시간 없음</div>

      <div class="inline-row">
        <button id="tutor-time-test-btn" class="btn btn-primary">설정 실행 (실제 제출됨)</button>
        <button id="tutor-time-test-stop-btn" class="btn btn-danger" disabled>중단</button>
        <span id="tutor-time-test-status" class="status-badge status-pending">대기중</span>
      </div>

      <div class="field-label login-test-label">설정 결과 (이전 상태 → 변경 후 상태, 실수 확인용 기록)</div>
      <table class="dashboard-table" id="tutor-schedule-results-table">
        <thead>
          <tr><th>강사명</th><th>요일</th><th>시간</th><th>이전 상태</th><th>변경 후 상태</th></tr>
        </thead>
        <tbody id="tutor-schedule-results-body">
          <tr><td colspan="5" class="empty">아직 설정한 내역이 없습니다.</td></tr>
        </tbody>
      </table>
    </section>

    <div class="view-header">
      <h1>오전특강 통계</h1>
      <div class="job-controls">
        <button id="start-btn" class="btn btn-primary">시작</button>
        <button id="pause-btn" class="btn btn-ghost" disabled>일시정지</button>
        <button id="stop-btn" class="btn btn-danger" disabled>중단</button>
        <button id="copy-btn" class="btn btn-ghost" disabled>결과 클립보드 복사</button>
      </div>
    </div>

    <section class="panel">
      <div class="field-label">강사 명단 선택</div>
      <div class="tutor-roster-actions">
        <input type="text" id="tutor-roster-search" class="roster-search-input" placeholder="강사 이름 검색..." />
        <button id="tutor-select-all-btn" type="button" class="btn btn-ghost">전체 선택</button>
        <button id="tutor-deselect-all-btn" type="button" class="btn btn-ghost">전체 해제</button>
        <span id="tutor-roster-count" class="tutor-roster-count">0명 선택됨</span>
      </div>
      <div id="tutor-roster-grid" class="tutor-roster-grid"></div>
    </section>

    <section class="panel">
      <label class="field-label" for="tutor-list">직접 추가 (위 명단에 없는 강사만, 한 줄에 한 명씩)</label>
      <textarea id="tutor-list" rows="3" placeholder="체크박스 명단에 없는 강사만 여기에 추가로 입력"></textarea>
      <div class="field-hint">별도 제출 버튼 없음 — 여기 적어두면 아래 "시작" 버튼을 누를 때 체크된 강사와 함께 자동으로 반영됩니다.</div>
    </section>

    <section class="panel criteria-panel">
      <div class="field">
        <label class="field-label" for="consultation-after">상담 기록 기준일 (이 날짜 이후 작성분)</label>
        <input type="date" id="consultation-after" />
      </div>
      <div class="field">
        <label class="field-label" for="class-after">수업일자 기준일 (이 날짜 이후 수업)</label>
        <input type="date" id="class-after" />
      </div>
    </section>

    <section class="panel">
      <div id="dashboard-container"></div>
    </section>

    <section class="panel">
      <div class="field-label login-test-label">보강권 지급 내역 (강사 / 회원 / 건수) — 아래 복사 버튼으로 엑셀에 바로 붙여넣기 가능</div>
      <table class="dashboard-table" id="records-table">
        <thead>
          <tr><th>강사명</th><th>회원명</th><th>보강권 건수</th></tr>
        </thead>
        <tbody id="records-table-body">
          <tr><td colspan="3" class="empty">아직 수집된 내역이 없습니다.</td></tr>
        </tbody>
      </table>
    </section>

    <section class="panel">
      <div class="field-label login-test-label">실행 로그</div>
      <div class="log-toolbar">
        <input type="text" id="log-search" class="roster-search-input" placeholder="로그 검색... (일치하는 줄만 표시)" />
        <span id="log-search-count" class="tutor-roster-count"></span>
        <button id="log-copy-all-btn" type="button" class="btn btn-ghost">로그 전체 복사</button>
      </div>
      <div id="log-output" class="log-output"></div>
    </section>
  `;

  const dashboard = window.createDashboard(document.getElementById('dashboard-container'));
  const logOutput = document.getElementById('log-output');
  const recordsTableBody = document.getElementById('records-table-body');

  const logSearchInput = document.getElementById('log-search');
  const logSearchCount = document.getElementById('log-search-count');
  const logCopyAllBtn = document.getElementById('log-copy-all-btn');
  let logSearchQuery = '';

  logCopyAllBtn.addEventListener('click', async () => {
    const text = Array.from(logOutput.children)
      .map((line) => line.textContent)
      .join('\n');
    const result = await window.api.copySummary(text);
    logCopyAllBtn.textContent = result.success ? '복사됨!' : '복사 실패';
    setTimeout(() => {
      logCopyAllBtn.textContent = '로그 전체 복사';
    }, 1500);
  });

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

  // python worker가 회원 한 명 처리를 끝낼 때마다 job:record로 보내주는 (강사, 회원, 건수) 목록.
  let collectedRecords = [];

  function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  function renderRecordsTable() {
    if (collectedRecords.length === 0) {
      recordsTableBody.innerHTML = '<tr><td colspan="3" class="empty">아직 수집된 내역이 없습니다.</td></tr>';
      return;
    }

    recordsTableBody.innerHTML = collectedRecords
      .map(
        (r) =>
          `<tr><td>${escapeHtml(r.tutor)}</td><td>${escapeHtml(r.member)}</td><td>${r.creditCount}</td></tr>`
      )
      .join('');
  }

  function buildClipboardText() {
    // 탭으로 구분해야 엑셀/구글시트에 붙여넣을 때 자동으로 열이 나뉜다.
    const lines = ['강사명\t회원명\t보강권 건수'];
    collectedRecords.forEach((r) => {
      lines.push(`${r.tutor}\t${r.member}\t${r.creditCount}`);
    });

    const failed = dashboard.getFailedList();
    if (failed.length > 0) {
      lines.push('', '[실패한 강사]');
      failed.forEach(({ tutor, reason }) => lines.push(`${tutor}\t${reason ?? '사유 미상'}`));
    }

    return lines.join('\n');
  }

  const loginTestBtn = document.getElementById('login-test-btn');
  const loginTestStopBtn = document.getElementById('login-test-stop-btn');
  const loginTestStatus = document.getElementById('login-test-status');

  const tutorSearchTestNameEl = document.getElementById('tutor-search-test-name');
  const tutorSearchTestBtn = document.getElementById('tutor-search-test-btn');
  const tutorSearchTestStopBtn = document.getElementById('tutor-search-test-stop-btn');
  const tutorSearchTestStatus = document.getElementById('tutor-search-test-status');

  const blackTimeRosterInput = document.getElementById('black-time-roster-input');
  const blackTimeRosterAddBtn = document.getElementById('black-time-roster-add-btn');
  const blackTimeRosterListEl = document.getElementById('black-time-roster-list');

  const tutorTimeTestWeekdayEl = document.getElementById('tutor-time-test-weekday');
  const tutorTimeTestStateEl = document.getElementById('tutor-time-test-state');
  const tutorTimeTestBtn = document.getElementById('tutor-time-test-btn');
  const tutorTimeTestStopBtn = document.getElementById('tutor-time-test-stop-btn');
  const tutorTimeTestStatus = document.getElementById('tutor-time-test-status');

  const tutorSlotGrid = document.getElementById('tutor-slot-grid');
  const tutorSlotSummary = document.getElementById('tutor-slot-summary');
  const tutorSlotSearchInput = document.getElementById('tutor-slot-search');
  const tutorSlotSelectAllBtn = document.getElementById('tutor-slot-select-all-btn');
  const tutorSlotDeselectAllBtn = document.getElementById('tutor-slot-deselect-all-btn');
  const tutorSlotRangeStartEl = document.getElementById('tutor-slot-range-start');
  const tutorSlotRangeEndEl = document.getElementById('tutor-slot-range-end');
  const tutorSlotRangeBtn = document.getElementById('tutor-slot-range-btn');
  const tutorScheduleResultsBody = document.getElementById('tutor-schedule-results-body');

  const startBtn = document.getElementById('start-btn');
  const pauseBtn = document.getElementById('pause-btn');
  const stopBtn = document.getElementById('stop-btn');
  const copyBtn = document.getElementById('copy-btn');
  const tutorListEl = document.getElementById('tutor-list');
  const consultationInput = document.getElementById('consultation-after');
  const classInput = document.getElementById('class-after');

  const tutorRosterGrid = document.getElementById('tutor-roster-grid');
  const tutorRosterCount = document.getElementById('tutor-roster-count');
  const tutorSelectAllBtn = document.getElementById('tutor-select-all-btn');
  const tutorDeselectAllBtn = document.getElementById('tutor-deselect-all-btn');
  const tutorRosterSearchInput = document.getElementById('tutor-roster-search');

  tutorRosterGrid.innerHTML = TUTOR_ROSTER.map(
    (name, idx) => `
      <div class="tutor-checkbox">
        <input type="checkbox" id="tutor-chk-${idx}" data-name="${escapeHtml(name)}" />
        <label for="tutor-chk-${idx}">${escapeHtml(name)}</label>
      </div>
    `
  ).join('');

  function getCheckedTutorNames() {
    return Array.from(tutorRosterGrid.querySelectorAll('input[type="checkbox"]:checked')).map(
      (el) => el.dataset.name
    );
  }

  function updateTutorRosterCount() {
    tutorRosterCount.textContent = `${getCheckedTutorNames().length}명 선택됨`;
  }

  tutorRosterGrid.addEventListener('change', updateTutorRosterCount);

  tutorRosterSearchInput.addEventListener('input', () => {
    const query = tutorRosterSearchInput.value.trim().toLowerCase();
    tutorRosterGrid.querySelectorAll('.tutor-checkbox').forEach((row) => {
      const name = row.querySelector('input[type="checkbox"]').dataset.name.toLowerCase();
      row.hidden = query.length > 0 && !name.includes(query);
    });
  });

  tutorSelectAllBtn.addEventListener('click', () => {
    tutorRosterGrid.querySelectorAll('input[type="checkbox"]').forEach((el) => {
      el.checked = true;
    });
    updateTutorRosterCount();
  });

  tutorDeselectAllBtn.addEventListener('click', () => {
    tutorRosterGrid.querySelectorAll('input[type="checkbox"]').forEach((el) => {
      el.checked = false;
    });
    updateTutorRosterCount();
  });

  tutorSlotGrid.innerHTML = TUTOR_SCHEDULE_SLOTS.map(
    (slot, idx) => `
      <div class="tutor-checkbox">
        <input type="checkbox" id="tutor-slot-chk-${idx}" data-hour="${slot.hour}" data-minute="${slot.minute}" data-label="${slot.label}" />
        <label for="tutor-slot-chk-${idx}">${slot.label}</label>
      </div>
    `
  ).join('');

  const slotRangeOptions = TUTOR_SCHEDULE_SLOTS.map((slot) => `<option value="${slot.label}">${slot.label}</option>`).join('');
  tutorSlotRangeStartEl.innerHTML = slotRangeOptions;
  tutorSlotRangeEndEl.innerHTML = slotRangeOptions;
  tutorSlotRangeStartEl.value = '10:00';
  tutorSlotRangeEndEl.value = '23:30';

  function getCheckedSlots() {
    return Array.from(tutorSlotGrid.querySelectorAll('input[type="checkbox"]:checked')).map((el) => ({
      hour: Number(el.dataset.hour),
      startMinute: Number(el.dataset.minute),
      label: el.dataset.label,
    }));
  }

  function updateTutorSlotSummary() {
    const checked = getCheckedSlots();
    tutorSlotSummary.textContent = checked.length
      ? `선택된 시간 (${checked.length}개): ${checked.map((s) => s.label).join(', ')}`
      : '선택된 시간 없음';
  }

  tutorSlotGrid.addEventListener('change', updateTutorSlotSummary);

  tutorSlotSearchInput.addEventListener('input', () => {
    const query = tutorSlotSearchInput.value.trim().toLowerCase();
    tutorSlotGrid.querySelectorAll('.tutor-checkbox').forEach((row) => {
      const label = row.querySelector('input[type="checkbox"]').dataset.label.toLowerCase();
      row.hidden = query.length > 0 && !label.includes(query);
    });
  });

  tutorSlotSelectAllBtn.addEventListener('click', () => {
    tutorSlotGrid.querySelectorAll('input[type="checkbox"]').forEach((el) => {
      el.checked = true;
    });
    updateTutorSlotSummary();
  });

  tutorSlotDeselectAllBtn.addEventListener('click', () => {
    tutorSlotGrid.querySelectorAll('input[type="checkbox"]').forEach((el) => {
      el.checked = false;
    });
    updateTutorSlotSummary();
  });

  tutorSlotRangeBtn.addEventListener('click', () => {
    const startIdx = TUTOR_SCHEDULE_SLOTS.findIndex((s) => s.label === tutorSlotRangeStartEl.value);
    const endIdx = TUTOR_SCHEDULE_SLOTS.findIndex((s) => s.label === tutorSlotRangeEndEl.value);
    if (startIdx === -1 || endIdx === -1 || startIdx > endIdx) {
      alert('범위가 올바르지 않습니다 (시작 시간이 종료 시간보다 늦을 수 없습니다).');
      return;
    }
    for (let i = startIdx; i <= endIdx; i++) {
      const chk = document.getElementById(`tutor-slot-chk-${i}`);
      if (chk) chk.checked = true;
    }
    updateTutorSlotSummary();
  });

  let tutorScheduleResults = [];

  function renderTutorScheduleResults() {
    if (tutorScheduleResults.length === 0) {
      tutorScheduleResultsBody.innerHTML = '<tr><td colspan="5" class="empty">아직 설정한 내역이 없습니다.</td></tr>';
      return;
    }
    tutorScheduleResultsBody.innerHTML = tutorScheduleResults
      .map(
        (r) => `
          <tr>
            <td>${escapeHtml(r.tutor)}</td>
            <td>${escapeHtml(r.weekday)}</td>
            <td>${escapeHtml(r.time)}</td>
            <td>${escapeHtml(r.before)}</td>
            <td>${escapeHtml(r.after)}</td>
          </tr>
        `
      )
      .join('');
  }

  let blackTimeTutorRoster = [];
  let selectedBlackTimeTutor = null;

  function renderBlackTimeRoster() {
    const sorted = [...blackTimeTutorRoster].sort((a, b) => a.localeCompare(b));
    blackTimeRosterListEl.innerHTML = sorted
      .map(
        (name, idx) => `
          <div class="checkbox-row black-time-roster-row">
            <input type="radio" name="black-time-roster-select" id="black-time-roster-${idx}"
              value="${escapeHtml(name)}" ${name === selectedBlackTimeTutor ? 'checked' : ''} />
            <label for="black-time-roster-${idx}">${escapeHtml(name)}</label>
            <button type="button" class="btn btn-ghost black-time-roster-remove-btn" data-name="${escapeHtml(name)}">삭제</button>
          </div>
        `
      )
      .join('');
  }

  function persistBlackTimeTutorRoster() {
    window.api.setSettings({ blackTimeTutorRoster });
  }

  blackTimeRosterAddBtn.addEventListener('click', () => {
    const name = blackTimeRosterInput.value.trim();
    if (!name) return;

    if (blackTimeTutorRoster.some((existing) => existing.toLowerCase() === name.toLowerCase())) {
      alert('이미 명단에 있는 이름입니다.');
      return;
    }

    blackTimeTutorRoster.push(name);
    persistBlackTimeTutorRoster();
    renderBlackTimeRoster();
    blackTimeRosterInput.value = '';
  });

  blackTimeRosterInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') blackTimeRosterAddBtn.click();
  });

  blackTimeRosterListEl.addEventListener('click', (e) => {
    const removeBtn = e.target.closest('.black-time-roster-remove-btn');
    if (!removeBtn) return;

    const name = removeBtn.dataset.name;
    blackTimeTutorRoster = blackTimeTutorRoster.filter((existing) => existing !== name);
    if (selectedBlackTimeTutor === name) selectedBlackTimeTutor = null;
    persistBlackTimeTutorRoster();
    renderBlackTimeRoster();
  });

  blackTimeRosterListEl.addEventListener('change', (e) => {
    if (e.target.name === 'black-time-roster-select') {
      selectedBlackTimeTutor = e.target.value;
    }
  });

  window.api.getSettings().then((settings) => {
    consultationInput.value = settings.criteria?.consultationAfter || '2026-08-18';
    classInput.value = settings.criteria?.classAfter || '2026-08-20';
    tutorListEl.value = settings.lastTutorList || '';

    const checkedSet = new Set(settings.checkedTutors || []);
    tutorRosterGrid.querySelectorAll('input[type="checkbox"]').forEach((el) => {
      el.checked = checkedSet.has(el.dataset.name);
    });
    updateTutorRosterCount();

    blackTimeTutorRoster = settings.blackTimeTutorRoster || [];
    renderBlackTimeRoster();
  });

  // 이 화면의 테스트 버튼들과 오전특강 통계 작업은 python worker 프로세스를 하나만 쓰므로
  // 동시에 실행할 수 없다. 지금 실행 중인 작업이 어느 쪽인지 추적해서 완료 시 해당 UI만 되돌린다.
  let activeJob = null; // 'login_test' | 'tutor_search_test' | 'tutor_schedule_set' | 'morning_special_stats' | null
  let paused = false;

  function setStartButtonsDisabled(disabled) {
    startBtn.disabled = disabled;
    loginTestBtn.disabled = disabled;
    tutorSearchTestBtn.disabled = disabled;
    tutorTimeTestBtn.disabled = disabled;
  }

  function setLoginTestStatus(label, statusClass) {
    loginTestStatus.textContent = label;
    loginTestStatus.className = `status-badge status-${statusClass}`;
  }

  function setTutorSearchTestStatus(label, statusClass) {
    tutorSearchTestStatus.textContent = label;
    tutorSearchTestStatus.className = `status-badge status-${statusClass}`;
  }

  function setTutorTimeTestStatus(label, statusClass) {
    tutorTimeTestStatus.textContent = label;
    tutorTimeTestStatus.className = `status-badge status-${statusClass}`;
  }

  loginTestBtn.addEventListener('click', async () => {
    const result = await window.api.startJob({ jobId: 'login_test' });
    if (!result.started) {
      alert('이미 실행 중인 작업이 있습니다.');
      return;
    }

    activeJob = 'login_test';
    setLoginTestStatus('로그인 시도 중', 'processing');
    setStartButtonsDisabled(true);
    loginTestStopBtn.disabled = false;
  });

  loginTestStopBtn.addEventListener('click', async () => {
    await window.api.stopJob();
    loginTestStopBtn.disabled = true;
  });

  tutorSearchTestBtn.addEventListener('click', async () => {
    const tutorName = tutorSearchTestNameEl.value.trim();
    if (!tutorName) {
      alert('강사 이름을 입력해주세요.');
      return;
    }

    const result = await window.api.startJob({
      jobId: 'tutor_search_test',
      tutorName,
      consultationAfter: consultationInput.value,
      classAfter: classInput.value,
    });
    if (!result.started) {
      alert('이미 실행 중인 작업이 있습니다.');
      return;
    }

    collectedRecords = [];
    renderRecordsTable();

    activeJob = 'tutor_search_test';
    setTutorSearchTestStatus('진행 중', 'processing');
    setStartButtonsDisabled(true);
    tutorSearchTestStopBtn.disabled = false;
  });

  tutorSearchTestStopBtn.addEventListener('click', async () => {
    await window.api.stopJob();
    tutorSearchTestStopBtn.disabled = true;
  });

  tutorTimeTestBtn.addEventListener('click', async () => {
    if (!selectedBlackTimeTutor) {
      alert('강사명단에서 설정할 강사를 선택해주세요.');
      return;
    }

    const slots = getCheckedSlots();
    if (slots.length === 0) {
      alert('적용할 시간을 하나 이상 선택해주세요.');
      return;
    }

    const weekdayLabel = tutorTimeTestWeekdayEl.selectedOptions[0].textContent;
    const stateLabel = tutorTimeTestStateEl.value === 'close' ? '닫기(블랙+그레이 체크)' : '열기(화이트 타임)';
    const confirmed = confirm(
      `${selectedBlackTimeTutor} 강사의 ${weekdayLabel}요일 ${slots.length}개 시간대를 ` +
        `${stateLabel}(으)로 실제 제출합니다. 계속할까요?`
    );
    if (!confirmed) return;

    const result = await window.api.startJob({
      jobId: 'tutor_schedule_set',
      tutorName: selectedBlackTimeTutor,
      weekday: Number(tutorTimeTestWeekdayEl.value),
      state: tutorTimeTestStateEl.value,
      slots: slots.map((s) => ({ hour: s.hour, startMinute: s.startMinute })),
    });
    if (!result.started) {
      alert('이미 실행 중인 작업이 있습니다.');
      return;
    }

    tutorScheduleResults = [];
    renderTutorScheduleResults();

    activeJob = 'tutor_schedule_set';
    setTutorTimeTestStatus('진행 중', 'processing');
    setStartButtonsDisabled(true);
    tutorTimeTestStopBtn.disabled = false;
  });

  tutorTimeTestStopBtn.addEventListener('click', async () => {
    await window.api.stopJob();
    tutorTimeTestStopBtn.disabled = true;
  });

  startBtn.addEventListener('click', async () => {
    const checkedNames = getCheckedTutorNames();
    const extraNames = tutorListEl.value
      .split('\n')
      .map((name) => name.trim())
      .filter(Boolean);
    const tutors = Array.from(new Set([...checkedNames, ...extraNames]));

    if (tutors.length === 0) {
      alert('강사를 체크박스에서 선택하거나 직접 입력해주세요.');
      return;
    }

    dashboard.reset(tutors);
    collectedRecords = [];
    renderRecordsTable();
    paused = false;
    pauseBtn.textContent = '일시정지';

    const payload = {
      jobId: 'morning_special_stats',
      tutors,
      consultationAfter: consultationInput.value,
      classAfter: classInput.value,
    };

    await window.api.setSettings({
      lastTutorList: tutorListEl.value,
      checkedTutors: checkedNames,
      criteria: { consultationAfter: payload.consultationAfter, classAfter: payload.classAfter },
    });

    const result = await window.api.startJob(payload);
    if (!result.started) {
      alert('이미 실행 중인 작업이 있습니다.');
      return;
    }

    activeJob = 'morning_special_stats';
    setStartButtonsDisabled(true);
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
    const text = buildClipboardText();
    const result = await window.api.copySummary(text);
    copyBtn.textContent = result.success ? '복사됨!' : '복사 실패';
    setTimeout(() => {
      copyBtn.textContent = '결과 클립보드 복사';
    }, 1500);
  });

  window.api.onJobProgress((data) => {
    dashboard.setStatus(data.tutor, data.status, data.found, data.reason);
  });

  window.api.onJobRecord((data) => {
    if (data.kind === 'tutor_schedule' && data.tutorSchedule) {
      tutorScheduleResults.push(data.tutorSchedule);
      renderTutorScheduleResults();
      return;
    }
    collectedRecords.push({ tutor: data.tutor, member: data.member, creditCount: data.credit_count });
    renderRecordsTable();
  });

  window.api.onJobLog((data) => {
    appendLog(data.level || 'info', data.message || '');
  });

  window.api.onJobDone((data) => {
    // python worker의 emit_done(요약 정보, code 없음)과 프로세스 종료(code 있음) 두 번 올 수 있다.
    // 실제 성공/실패는 code가 담긴 이벤트가 최종 판단 기준이다.
    if (typeof data.code === 'undefined') return;

    appendLog('info', `작업 프로세스 종료 (종료 코드: ${data.code})`);

    if (activeJob === 'login_test') {
      setLoginTestStatus(
        data.code === 0 ? '완료 (브라우저 창 확인)' : '실패 (로그 확인)',
        data.code === 0 ? 'success' : 'failed'
      );
      loginTestStopBtn.disabled = true;
    } else if (activeJob === 'tutor_search_test') {
      setTutorSearchTestStatus(
        data.code === 0 ? '완료 (브라우저 창 확인)' : '실패 (로그 확인)',
        data.code === 0 ? 'success' : 'failed'
      );
      tutorSearchTestStopBtn.disabled = true;
    } else if (activeJob === 'tutor_schedule_set') {
      setTutorTimeTestStatus(
        data.code === 0 ? '완료 (브라우저 창 확인)' : '실패 (로그 확인)',
        data.code === 0 ? 'success' : 'failed'
      );
      tutorTimeTestStopBtn.disabled = true;
    } else if (activeJob === 'morning_special_stats') {
      pauseBtn.disabled = true;
      stopBtn.disabled = true;
      copyBtn.disabled = false;
    }

    setStartButtonsDisabled(false);
    activeJob = null;
  });
}

window.renderMorningSpecialStatsView = renderMorningSpecialStatsView;
