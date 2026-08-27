function renderMorningSpecialStatsView(container) {
  container.innerHTML = `
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
      <label class="field-label" for="tutor-list">강사 명단 (한 줄에 한 명씩 붙여넣기)</label>
      <textarea id="tutor-list" rows="8" placeholder="김민지&#10;이영희&#10;..."></textarea>
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
  `;

  const dashboard = window.createDashboard(document.getElementById('dashboard-container'));

  const startBtn = document.getElementById('start-btn');
  const pauseBtn = document.getElementById('pause-btn');
  const stopBtn = document.getElementById('stop-btn');
  const copyBtn = document.getElementById('copy-btn');
  const tutorListEl = document.getElementById('tutor-list');
  const consultationInput = document.getElementById('consultation-after');
  const classInput = document.getElementById('class-after');

  window.api.getSettings().then((settings) => {
    consultationInput.value = settings.criteria?.consultationAfter || '2026-08-18';
    classInput.value = settings.criteria?.classAfter || '2026-08-20';
    tutorListEl.value = settings.lastTutorList || '';
  });

  let paused = false;

  startBtn.addEventListener('click', async () => {
    const tutors = tutorListEl.value
      .split('\n')
      .map((name) => name.trim())
      .filter(Boolean);

    if (tutors.length === 0) {
      alert('강사 명단을 입력해주세요.');
      return;
    }

    dashboard.reset(tutors);
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
      criteria: { consultationAfter: payload.consultationAfter, classAfter: payload.classAfter },
    });

    const result = await window.api.startJob(payload);
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
    const text = dashboard.getSummaryText();
    const result = await window.api.copySummary(text);
    copyBtn.textContent = result.success ? '복사됨!' : '복사 실패';
    setTimeout(() => {
      copyBtn.textContent = '결과 클립보드 복사';
    }, 1500);
  });

  window.api.onJobProgress((data) => {
    dashboard.setStatus(data.tutor, data.status, data.found, data.reason);
  });

  window.api.onJobLog((data) => {
    // TODO: 로그 패널 UI가 추가되면 여기서 화면에 출력
    console.log('[job:log]', data);
  });

  window.api.onJobDone(() => {
    startBtn.disabled = false;
    pauseBtn.disabled = true;
    stopBtn.disabled = true;
    copyBtn.disabled = false;
  });
}

window.renderMorningSpecialStatsView = renderMorningSpecialStatsView;
