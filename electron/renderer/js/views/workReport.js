// 업무보고(office.talkstation.co.kr의 "일일업무보고 작성"과 비슷한 화면) 초안 작성 도구.
//
// office.talkstation.co.kr에 직접 자동 로그인/제출하지는 않는다(사내망 전용
// 사이트라 여기서 직접 테스트해볼 수 없어서 위험 부담이 큼) — 대신 이 화면에서
// 초안을 만들고 다듬은 뒤 "보고서 초안 복사"로 클립보드에 담아 실제 사이트
// 글쓰기 화면에 붙여넣는 방식으로 쓴다.
//
// "오늘 한 일" 초안은 대화 내용이 아니라(일렉트론 앱은 이 대화를 알 수 없음)
// 이 저장소(TS_SummerVacation)의 오늘자 git 커밋 메시지를 불러와서 만든다.
// 실시간 연동은 안 되니, "새로고침" 버튼을 눌러야 그 시점까지의 커밋을 반영한다.
function renderWorkReportView(container) {
  container.innerHTML = `
    <div class="view-header">
      <h1>업무보고</h1>
      <div class="job-controls">
        <button id="report-copy-btn" class="btn btn-primary">보고서 초안 복사</button>
      </div>
    </div>

    <div class="field-hint" style="margin-bottom: 16px;">
      office.talkstation.co.kr에 자동으로 올라가지는 않습니다. 여기서 초안을 만들고 다듬은 뒤,
      "보고서 초안 복사"를 눌러 실제 사이트의 "일일업무보고 작성" 화면에 붙여넣어 주세요.
    </div>

    <section class="panel">
      <div class="criteria-panel">
        <div class="field">
          <label class="field-label" for="report-department">부서</label>
          <input type="text" id="report-department" placeholder="예: 운영팀" />
        </div>
        <div class="field">
          <label class="field-label" for="report-author">작성자</label>
          <input type="text" id="report-author" placeholder="예: 이성규" />
        </div>
        <div class="field">
          <label class="field-label" for="report-date">날짜</label>
          <input type="date" id="report-date" />
        </div>
      </div>
    </section>

    <section class="panel">
      <div class="field-label login-test-label">오늘 깃 커밋 내역</div>
      <div class="log-toolbar">
        <button id="refresh-commits-btn" class="btn btn-ghost">🔄 새로고침</button>
        <button id="apply-commits-btn" class="btn btn-ghost" disabled>→ 금일 업무 내용에 채우기</button>
      </div>
      <div id="commits-output" class="log-output">
        <div class="empty-view">새로고침을 눌러 오늘 이 저장소에 커밋한 내역을 불러오세요.</div>
      </div>
    </section>

    <section class="panel">
      <div class="field">
        <label class="field-label" for="daily-work">금일 업무 내용</label>
        <textarea id="daily-work" rows="8" placeholder="오늘 한 일을 정리해주세요. 위 커밋 내역을 채워 넣은 뒤 자유롭게 다듬을 수 있습니다."></textarea>
      </div>
    </section>

    <section class="panel">
      <div class="field">
        <label class="field-label" for="tomorrow-plan">명일 업무 계획</label>
        <textarea id="tomorrow-plan" rows="4"></textarea>
      </div>
    </section>

    <section class="panel">
      <div class="field">
        <label class="field-label" for="report-issues">특이사항</label>
        <textarea id="report-issues" rows="3"></textarea>
      </div>
    </section>
  `;

  const departmentInput = document.getElementById('report-department');
  const authorInput = document.getElementById('report-author');
  const dateInput = document.getElementById('report-date');
  const refreshCommitsBtn = document.getElementById('refresh-commits-btn');
  const applyCommitsBtn = document.getElementById('apply-commits-btn');
  const commitsOutput = document.getElementById('commits-output');
  const dailyWorkInput = document.getElementById('daily-work');
  const tomorrowPlanInput = document.getElementById('tomorrow-plan');
  const issuesInput = document.getElementById('report-issues');
  const copyBtn = document.getElementById('report-copy-btn');

  let fetchedCommits = [];
  let settings = null;

  function todayIso() {
    const d = new Date();
    d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
    return d.toISOString().slice(0, 10);
  }

  function currentDraft() {
    const drafts = settings.workReportDrafts || {};
    return drafts[dateInput.value] || { dailyWork: '', tomorrowPlan: '', issues: '' };
  }

  function loadDraftForDate() {
    const draft = currentDraft();
    dailyWorkInput.value = draft.dailyWork || '';
    tomorrowPlanInput.value = draft.tomorrowPlan || '';
    issuesInput.value = draft.issues || '';
    fetchedCommits = [];
    applyCommitsBtn.disabled = true;
    commitsOutput.innerHTML = '<div class="empty-view">새로고침을 눌러 오늘 이 저장소에 커밋한 내역을 불러오세요.</div>';
  }

  async function saveDraft() {
    const drafts = { ...(settings.workReportDrafts || {}) };
    drafts[dateInput.value] = {
      dailyWork: dailyWorkInput.value,
      tomorrowPlan: tomorrowPlanInput.value,
      issues: issuesInput.value,
    };
    settings.workReportDrafts = drafts;
    await window.api.setSettings({ workReportDrafts: drafts });
  }

  async function saveProfile() {
    const profile = { department: departmentInput.value, author: authorInput.value };
    settings.reportProfile = profile;
    await window.api.setSettings({ reportProfile: profile });
  }

  async function init() {
    settings = await window.api.getSettings();
    const profile = settings.reportProfile || {};
    departmentInput.value = profile.department || '';
    authorInput.value = profile.author || '';
    dateInput.value = todayIso();
    loadDraftForDate();
  }

  // 입력할 때마다 바로 저장하면 매 키 입력마다 electron-store에 디스크 쓰기가
  // 일어나므로, 타이핑이 잠시 멈췄을 때만 저장하도록 살짝 지연시킨다.
  let saveDraftTimer = null;
  function scheduleSaveDraft() {
    clearTimeout(saveDraftTimer);
    saveDraftTimer = setTimeout(saveDraft, 500);
  }

  dateInput.addEventListener('change', loadDraftForDate);
  departmentInput.addEventListener('change', saveProfile);
  authorInput.addEventListener('change', saveProfile);
  [dailyWorkInput, tomorrowPlanInput, issuesInput].forEach((el) => {
    el.addEventListener('input', scheduleSaveDraft);
  });

  refreshCommitsBtn.addEventListener('click', async () => {
    refreshCommitsBtn.disabled = true;
    refreshCommitsBtn.textContent = '불러오는 중...';
    const result = await window.api.getTodayCommits();
    refreshCommitsBtn.disabled = false;
    refreshCommitsBtn.textContent = '🔄 새로고침';

    if (!result.success) {
      commitsOutput.innerHTML = `<div class="empty-view">커밋 내역을 불러오지 못했습니다: ${result.error || '알 수 없는 오류'}</div>`;
      fetchedCommits = [];
      applyCommitsBtn.disabled = true;
      return;
    }

    fetchedCommits = result.commits;

    if (fetchedCommits.length === 0) {
      commitsOutput.innerHTML = '<div class="empty-view">오늘 이 저장소에 커밋한 내역이 없습니다.</div>';
      applyCommitsBtn.disabled = true;
      return;
    }

    commitsOutput.innerHTML = '';
    fetchedCommits.forEach((subject) => {
      const line = document.createElement('div');
      line.className = 'log-line';
      line.textContent = `- ${subject}`;
      commitsOutput.appendChild(line);
    });
    applyCommitsBtn.disabled = false;
  });

  applyCommitsBtn.addEventListener('click', () => {
    if (fetchedCommits.length === 0) return;
    const commitLines = fetchedCommits.map((subject) => `- ${subject}`).join('\n');
    dailyWorkInput.value = dailyWorkInput.value.trim()
      ? `${dailyWorkInput.value.trim()}\n\n${commitLines}`
      : commitLines;
    saveDraft();
  });

  copyBtn.addEventListener('click', async () => {
    const text = [
      `[일일업무보고 - ${dateInput.value}]`,
      `부서: ${departmentInput.value}`,
      `작성자: ${authorInput.value}`,
      '',
      '<금일 업무 내용>',
      dailyWorkInput.value || '(내용 없음)',
      '',
      '<명일 업무 계획>',
      tomorrowPlanInput.value || '(내용 없음)',
      '',
      '<특이사항>',
      issuesInput.value || '(내용 없음)',
    ].join('\n');

    const result = await window.api.copySummary(text);
    copyBtn.textContent = result.success ? '복사됨!' : '복사 실패';
    setTimeout(() => {
      copyBtn.textContent = '보고서 초안 복사';
    }, 1500);
  });

  init();
}

window.renderWorkReportView = renderWorkReportView;
