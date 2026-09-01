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
        <button id="tutor-select-all-btn" type="button" class="btn btn-ghost">전체 선택</button>
        <button id="tutor-deselect-all-btn" type="button" class="btn btn-ghost">전체 해제</button>
        <span id="tutor-roster-count" class="tutor-roster-count">0명 선택됨</span>
      </div>
      <div id="tutor-roster-grid" class="tutor-roster-grid"></div>
    </section>

    <section class="panel">
      <label class="field-label" for="tutor-list">직접 추가 (위 명단에 없는 강사만, 한 줄에 한 명씩)</label>
      <textarea id="tutor-list" rows="3" placeholder="체크박스 명단에 없는 강사만 여기에 추가로 입력"></textarea>
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
      <div id="log-output" class="log-output"></div>
    </section>
  `;

  const dashboard = window.createDashboard(document.getElementById('dashboard-container'));
  const logOutput = document.getElementById('log-output');
  const recordsTableBody = document.getElementById('records-table-body');

  function appendLog(level, message) {
    const line = document.createElement('div');
    line.className = `log-line log-line-${level}`;
    line.textContent = message;
    logOutput.appendChild(line);
    logOutput.scrollTop = logOutput.scrollHeight;
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

  window.api.getSettings().then((settings) => {
    consultationInput.value = settings.criteria?.consultationAfter || '2026-08-18';
    classInput.value = settings.criteria?.classAfter || '2026-08-20';
    tutorListEl.value = settings.lastTutorList || '';

    const checkedSet = new Set(settings.checkedTutors || []);
    tutorRosterGrid.querySelectorAll('input[type="checkbox"]').forEach((el) => {
      el.checked = checkedSet.has(el.dataset.name);
    });
    updateTutorRosterCount();
  });

  // 이 화면의 테스트 버튼들과 오전특강 통계 작업은 python worker 프로세스를 하나만 쓰므로
  // 동시에 실행할 수 없다. 지금 실행 중인 작업이 어느 쪽인지 추적해서 완료 시 해당 UI만 되돌린다.
  let activeJob = null; // 'login_test' | 'tutor_search_test' | 'morning_special_stats' | null
  let paused = false;

  function setStartButtonsDisabled(disabled) {
    startBtn.disabled = disabled;
    loginTestBtn.disabled = disabled;
    tutorSearchTestBtn.disabled = disabled;
  }

  function setLoginTestStatus(label, statusClass) {
    loginTestStatus.textContent = label;
    loginTestStatus.className = `status-badge status-${statusClass}`;
  }

  function setTutorSearchTestStatus(label, statusClass) {
    tutorSearchTestStatus.textContent = label;
    tutorSearchTestStatus.className = `status-badge status-${statusClass}`;
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
