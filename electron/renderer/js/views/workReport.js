// 업무보고(office.talkstation.co.kr "일일업무보고 작성") 화면.
//
// 세 부분으로 구성된다.
// 1) 초안 작성 - 일일/주간 탭 + 업무 항목별 진행률(%) 입력. 아직은 로컬에만
//    저장되고, "보고서 초안 복사"로 클립보드에 담아 수동으로 붙여넣을 수도 있다.
// 2) 크롤링 - office.talkstation.co.kr에서 지정한 이름으로 검색되는 과거
//    보고서를 1회성으로 모두 가져와 data/office/reports.json에 저장한다
//    (python/worker/office/crawler.py).
// 3) 자동 제출 - 크롤링해둔 가장 최근 보고서의 7개 항목을 그대로
//    /report/write에 채우되, "금일 업무 내용"/"특이사항"은 위 초안(진행률 %
//    포함)이 있으면 그걸 우선 사용해서 실제로 로그인 -> 채움 -> "글쓰기"까지
//    자동으로 수행한다(python/worker/office/writer.py). 오류나 alert가 뜨면
//    실행 로그에 그대로 표시된다.
//
// "오늘 한 일" 초안은 대화 내용이 아니라(일렉트론 앱은 이 대화를 알 수 없음)
// 이 저장소(TS_SummerVacation)의 오늘자 git 커밋 메시지를 불러와서 만든다.
function renderWorkReportView(container) {
  container.innerHTML = `
    <div class="view-header">
      <h1>업무보고</h1>
      <div class="job-controls">
        <button id="report-copy-btn" class="btn btn-primary">보고서 초안 복사</button>
      </div>
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
      <div class="log-toolbar">
        <button id="mode-daily-btn" class="btn btn-primary" data-mode="daily">일일보고서 작성</button>
        <button id="mode-weekly-btn" class="btn btn-ghost" data-mode="weekly">주간보고서 작성</button>
      </div>
    </section>

    <section class="panel">
      <div class="field">
        <label class="field-label" for="anthropic-api-key">Claude API 키 (메모 정리 기능에 사용)</label>
        <input type="password" id="anthropic-api-key" placeholder="sk-ant-..." />
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

    <section class="panel" id="daily-mode-section">
      <div class="field">
        <label class="field-label" for="daily-work">금일 업무 내용</label>
        <textarea id="daily-work" rows="6" placeholder="오늘 한 일을 정리해주세요. 위 커밋 내역을 채워 넣은 뒤 자유롭게 다듬을 수 있습니다."></textarea>
      </div>
      <div class="log-toolbar" style="margin-top: 8px;">
        <button id="tidy-daily-work-btn" class="btn btn-ghost">🪄 정리하기</button>
        <span id="tidy-daily-work-status" class="field-hint" style="margin-top: 0;"></span>
      </div>

      <div class="field-label" style="margin-top: 12px;">업무별 진행률</div>
      <div class="field-hint" style="margin-top: 0;">
        업무 항목마다 진행률(%)을 입력하면 제출 시 "금일 업무 내용"에 자동으로 반영됩니다.
        전날 같은 이름의 업무보다 진행률이 낮아지면 "진행률 감소 사유"를 반드시 입력해야 합니다.
      </div>
      <div id="work-items-list"></div>
      <button id="add-work-item-btn" class="btn btn-ghost" style="margin-top: 8px;">+ 업무 추가</button>

      <div class="field" style="margin-top: 16px;">
        <label class="field-label" for="tomorrow-plan">명일 업무 계획</label>
        <textarea id="tomorrow-plan" rows="4"></textarea>
      </div>
    </section>

    <section class="panel" id="weekly-mode-section" hidden>
      <div class="field">
        <label class="field-label" for="weekly-work">지난주 내용</label>
        <textarea id="weekly-work" rows="6"></textarea>
      </div>
      <div class="field">
        <label class="field-label" for="weekly-plan">다음주 계획</label>
        <textarea id="weekly-plan" rows="6"></textarea>
      </div>
    </section>

    <section class="panel">
      <div class="field">
        <label class="field-label" for="report-issues">특이사항</label>
        <textarea id="report-issues" rows="3"></textarea>
      </div>
    </section>

    <section class="panel">
      <div class="field-label login-test-label">① office.talkstation.co.kr 크롤링 (1회성)</div>
      <div class="field-hint" style="margin-top: 0;">
        지정한 이름으로 검색되는 모든 일일업무보고를 가져와 저장합니다. 새 보고서를 자동 제출할 때
        이 중 가장 최근 날짜의 항목을 기본값으로 사용합니다.
      </div>
      <div class="criteria-panel">
        <div class="field">
          <label class="field-label" for="office-target-name">검색할 이름</label>
          <input type="text" id="office-target-name" placeholder="검색할 이름을 입력하세요" />
        </div>
      </div>
      <div class="log-toolbar">
        <button id="crawl-btn" class="btn btn-primary">크롤링 시작</button>
      </div>
      <div id="crawl-status" class="field-hint" style="margin-top: 8px;">아직 크롤링한 적이 없습니다.</div>
    </section>

    <section class="panel">
      <div class="field-label login-test-label">② 자동으로 채워서 제출 ("글쓰기")</div>
      <div class="field-hint" style="margin-top: 0;">
        이 버튼을 누르면 실제 office.talkstation.co.kr에 자동으로 로그인해서, 새 일일업무보고를
        만들고 등록(글쓰기)까지 전부 자동으로 처리합니다. 채워지는 내용은 이렇습니다:
        <br>· 지난달 계획 / 이번달 계획 / 지난주 내용 / 다음주 계획 / 명일 업무 계획
        → 크롤링해둔 가장 최근 보고서 내용을 그대로 가져와서 채웁니다.
        <br>· 금일 업무 내용 / 특이사항 → 아래 체크박스가 켜져 있으면 지금 이 화면에 쓴 내용을,
        꺼져 있으면 이것도 크롤링 데이터를 그대로 씁니다.
      </div>
      <div class="checkbox-row">
        <input type="checkbox" id="use-local-draft-checkbox" checked />
        <label for="use-local-draft-checkbox">금일 업무 내용/특이사항은 이 화면에서 작성한 내용을 사용</label>
      </div>
      <div class="field">
        <label class="field-label" for="attach-files-input">첨부파일 (선택)</label>
        <div class="file-input-row">
          <input type="file" id="attach-files-input" multiple />
        </div>
      </div>

      <div class="field-label" style="margin-top: 16px;">미리보기 — 실제로 이렇게 올라갑니다</div>
      <div class="field-hint" style="margin-top: 0;" id="preview-empty-hint">
        아직 크롤링한 데이터가 없습니다. 위 ①에서 먼저 크롤링을 실행해주세요.
      </div>
      <div class="preview-grid" id="submit-preview-grid" hidden></div>

      <div class="log-toolbar" style="margin-top: 12px;">
        <button id="submit-btn" class="btn btn-primary">자동 제출</button>
      </div>
      <div id="submit-result" class="result-banner" hidden>
        <span id="submit-result-icon" class="result-banner-icon"></span>
        <span id="submit-result-text"></span>
      </div>
    </section>

    <section class="panel">
      <div class="field-label login-test-label">실행 로그</div>
      <div class="log-toolbar">
        <input type="text" id="job-log-search" class="roster-search-input" placeholder="로그 검색... (일치하는 줄만 표시)" />
        <span id="job-log-search-count" class="tutor-roster-count"></span>
      </div>
      <div id="job-log-output" class="log-output"></div>
    </section>
  `;

  const departmentInput = document.getElementById('report-department');
  const authorInput = document.getElementById('report-author');
  const dateInput = document.getElementById('report-date');
  const anthropicApiKeyInput = document.getElementById('anthropic-api-key');
  const tidyDailyWorkBtn = document.getElementById('tidy-daily-work-btn');
  const tidyDailyWorkStatus = document.getElementById('tidy-daily-work-status');
  const refreshCommitsBtn = document.getElementById('refresh-commits-btn');
  const applyCommitsBtn = document.getElementById('apply-commits-btn');
  const commitsOutput = document.getElementById('commits-output');
  const dailyWorkInput = document.getElementById('daily-work');
  const tomorrowPlanInput = document.getElementById('tomorrow-plan');
  const weeklyWorkInput = document.getElementById('weekly-work');
  const weeklyPlanInput = document.getElementById('weekly-plan');
  const issuesInput = document.getElementById('report-issues');
  const copyBtn = document.getElementById('report-copy-btn');
  const modeDailyBtn = document.getElementById('mode-daily-btn');
  const modeWeeklyBtn = document.getElementById('mode-weekly-btn');
  const dailyModeSection = document.getElementById('daily-mode-section');
  const weeklyModeSection = document.getElementById('weekly-mode-section');
  const workItemsList = document.getElementById('work-items-list');
  const addWorkItemBtn = document.getElementById('add-work-item-btn');
  const officeTargetNameInput = document.getElementById('office-target-name');
  const crawlBtn = document.getElementById('crawl-btn');
  const crawlStatus = document.getElementById('crawl-status');
  const useLocalDraftCheckbox = document.getElementById('use-local-draft-checkbox');
  const attachFilesInput = document.getElementById('attach-files-input');
  const submitBtn = document.getElementById('submit-btn');
  const previewEmptyHint = document.getElementById('preview-empty-hint');
  const submitPreviewGrid = document.getElementById('submit-preview-grid');
  const submitResult = document.getElementById('submit-result');
  const submitResultIcon = document.getElementById('submit-result-icon');
  const submitResultText = document.getElementById('submit-result-text');
  const jobLogOutput = document.getElementById('job-log-output');
  const jobLogSearchInput = document.getElementById('job-log-search');
  const jobLogSearchCount = document.getElementById('job-log-search-count');

  let fetchedCommits = [];
  let settings = null;
  let mode = 'daily'; // 'daily' | 'weekly' — UI 표시 전환용, 데이터는 둘 다 항상 함께 저장
  let workItems = []; // [{ title, progress, decreaseReason }]
  let activeJobKind = null; // 'crawl' | 'submit'
  let latestOfficeData = null; // window.api.getOfficeReports() 결과, 미리보기에 사용

  function todayIso() {
    const d = new Date();
    d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
    return d.toISOString().slice(0, 10);
  }

  function previousIso(iso) {
    const d = new Date(`${iso}T00:00:00`);
    d.setDate(d.getDate() - 1);
    d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
    return d.toISOString().slice(0, 10);
  }

  function emptyDraft() {
    return { dailyWork: '', tomorrowPlan: '', issues: '', weeklyWork: '', weeklyPlan: '', workItems: [] };
  }

  function currentDraft() {
    const drafts = settings.workReportDrafts || {};
    return drafts[dateInput.value] || emptyDraft();
  }

  function previousDraft() {
    const drafts = settings.workReportDrafts || {};
    return drafts[previousIso(dateInput.value)] || emptyDraft();
  }

  function loadDraftForDate() {
    const draft = currentDraft();
    dailyWorkInput.value = draft.dailyWork || '';
    tomorrowPlanInput.value = draft.tomorrowPlan || '';
    weeklyWorkInput.value = draft.weeklyWork || '';
    weeklyPlanInput.value = draft.weeklyPlan || '';
    issuesInput.value = draft.issues || '';
    workItems = (draft.workItems || []).map((item) => ({ ...item }));
    renderWorkItems();
    fetchedCommits = [];
    applyCommitsBtn.disabled = true;
    commitsOutput.innerHTML = '<div class="empty-view">새로고침을 눌러 오늘 이 저장소에 커밋한 내역을 불러오세요.</div>';
    renderSubmitPreview();
  }

  async function saveDraft() {
    renderSubmitPreview();
    const drafts = { ...(settings.workReportDrafts || {}) };
    drafts[dateInput.value] = {
      dailyWork: dailyWorkInput.value,
      tomorrowPlan: tomorrowPlanInput.value,
      weeklyWork: weeklyWorkInput.value,
      weeklyPlan: weeklyPlanInput.value,
      issues: issuesInput.value,
      workItems,
    };
    settings.workReportDrafts = drafts;
    await window.api.setSettings({ workReportDrafts: drafts });
  }

  async function saveProfile() {
    const profile = { department: departmentInput.value, author: authorInput.value };
    settings.reportProfile = profile;
    await window.api.setSettings({ reportProfile: profile });
  }

  function setMode(nextMode) {
    mode = nextMode;
    const isDaily = mode === 'daily';
    dailyModeSection.hidden = !isDaily;
    weeklyModeSection.hidden = isDaily;
    modeDailyBtn.className = isDaily ? 'btn btn-primary' : 'btn btn-ghost';
    modeWeeklyBtn.className = isDaily ? 'btn btn-ghost' : 'btn btn-primary';
  }

  // ---- 업무별 진행률(%) ----
  function findPreviousItem(title) {
    const prev = previousDraft();
    return (prev.workItems || []).find((item) => (item.title || '').trim() === title.trim());
  }

  // 행 DOM은 한 번만 만들고, 타이핑할 때마다 통째로 다시 그리지 않는다 —
  // input을 매번 새로 만들면 한글 조합(IME) 중간에 입력창이 교체돼서
  // 자모가 분리되어 깨지는 문제가 있었다 (예: "ㅁㄴㅇㄴㅁㅁㅇ").
  function refreshRowDerivedState(item, els) {
    const prevItem = item.title ? findPreviousItem(item.title) : null;
    els.progressLabel.textContent = prevItem ? `진행률 % (전날 ${prevItem.progress}%)` : '진행률 %';

    const decreased = prevItem && Number(item.progress) < Number(prevItem.progress);
    els.reasonRow.hidden = !decreased;
    if (!decreased && item.decreaseReason) {
      item.decreaseReason = '';
      els.reasonInput.value = '';
    }
  }

  function renderWorkItems() {
    workItemsList.innerHTML = '';
    workItems.forEach((item, index) => {
      const row = document.createElement('div');
      row.className = 'criteria-panel';
      row.style.marginBottom = '8px';

      const titleField = document.createElement('div');
      titleField.className = 'field';
      titleField.innerHTML = '<label class="field-label">업무명</label>';
      const titleInput = document.createElement('input');
      titleInput.type = 'text';
      titleInput.value = item.title || '';
      titleInput.placeholder = '예: 업무보고 자동화 개발';
      titleField.appendChild(titleInput);

      const progressField = document.createElement('div');
      progressField.className = 'field';
      const progressLabel = document.createElement('label');
      progressLabel.className = 'field-label';
      progressField.appendChild(progressLabel);
      const progressInput = document.createElement('input');
      progressInput.type = 'number';
      progressInput.min = '0';
      progressInput.max = '100';
      progressInput.value = item.progress ?? 0;
      progressField.appendChild(progressInput);

      const removeField = document.createElement('div');
      removeField.className = 'field';
      removeField.innerHTML = '<label class="field-label">&nbsp;</label>';
      const removeBtn = document.createElement('button');
      removeBtn.className = 'btn btn-ghost';
      removeBtn.textContent = '삭제';
      removeBtn.addEventListener('click', () => {
        workItems.splice(index, 1);
        renderWorkItems();
        saveDraft();
      });
      removeField.appendChild(removeBtn);

      row.appendChild(titleField);
      row.appendChild(progressField);
      row.appendChild(removeField);

      const reasonRow = document.createElement('div');
      reasonRow.className = 'field';
      reasonRow.style.marginBottom = '8px';
      reasonRow.innerHTML = '<label class="field-label" style="color: var(--color-danger, #d9534f);">진행률 감소 사유 :</label>';
      const reasonInput = document.createElement('input');
      reasonInput.type = 'text';
      reasonInput.value = item.decreaseReason || '';
      reasonInput.placeholder = '진행률이 줄어든 이유를 입력해주세요 (필수)';
      reasonRow.appendChild(reasonInput);

      const els = { progressLabel, reasonRow, reasonInput };

      titleInput.addEventListener('input', () => {
        item.title = titleInput.value;
        refreshRowDerivedState(item, els);
        scheduleSaveDraft();
      });
      progressInput.addEventListener('input', () => {
        item.progress = Number(progressInput.value);
        refreshRowDerivedState(item, els);
        scheduleSaveDraft();
      });
      reasonInput.addEventListener('input', () => {
        item.decreaseReason = reasonInput.value;
        scheduleSaveDraft();
      });

      workItemsList.appendChild(row);
      workItemsList.appendChild(reasonRow);
      refreshRowDerivedState(item, els);
    });
  }

  function hasBlockingDecreaseReasons() {
    return workItems.some((item) => {
      const prevItem = item.title ? findPreviousItem(item.title) : null;
      const decreased = prevItem && Number(item.progress) < Number(prevItem.progress);
      return decreased && !(item.decreaseReason || '').trim();
    });
  }

  // 금일 업무 내용에 진행률 항목을 반영한 HTML (자동 제출 시 daily_work_report로 사용).
  function buildDailyWorkHtml() {
    const parts = [];
    if (dailyWorkInput.value.trim()) {
      const escaped = dailyWorkInput.value
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .split('\n')
        .join('<br>');
      parts.push(`<p>${escaped}</p>`);
    }
    if (workItems.length > 0) {
      const items = workItems
        .filter((item) => (item.title || '').trim())
        .map((item) => {
          let line = `<b>${item.title}</b>: ${item.progress ?? 0}% 진행`;
          if (item.decreaseReason && item.decreaseReason.trim()) {
            line += ` (진행률 감소 사유 : ${item.decreaseReason})`;
          }
          return `<li>${line}</li>`;
        })
        .join('');
      if (items) parts.push(`<ul>${items}</ul>`);
    }
    return parts.join('');
  }

  function buildIssuesHtml() {
    if (!issuesInput.value.trim()) return '';
    const escaped = issuesInput.value
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .split('\n')
      .join('<br>');
    return `<p>${escaped}</p>`;
  }

  async function init() {
    settings = await window.api.getSettings();
    const profile = settings.reportProfile || {};
    departmentInput.value = profile.department || '';
    authorInput.value = profile.author || '';
    officeTargetNameInput.value = settings.officeReportTargetName || '';
    anthropicApiKeyInput.value = settings.anthropicApiKey || '';
    dateInput.value = todayIso();
    setMode('daily');
    loadDraftForDate();
    await refreshCrawlStatus();
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
  anthropicApiKeyInput.addEventListener('change', async () => {
    settings.anthropicApiKey = anthropicApiKeyInput.value.trim();
    await window.api.setSettings({ anthropicApiKey: settings.anthropicApiKey });
  });
  useLocalDraftCheckbox.addEventListener('change', renderSubmitPreview);

  tidyDailyWorkBtn.addEventListener('click', async () => {
    if (!dailyWorkInput.value.trim()) {
      tidyDailyWorkStatus.textContent = '정리할 내용이 없습니다.';
      return;
    }
    tidyDailyWorkBtn.disabled = true;
    tidyDailyWorkBtn.textContent = '정리 중...';
    tidyDailyWorkStatus.textContent = '';

    const result = await window.api.tidyText(dailyWorkInput.value);

    tidyDailyWorkBtn.disabled = false;
    tidyDailyWorkBtn.textContent = '🪄 정리하기';

    if (!result.success) {
      tidyDailyWorkStatus.textContent = result.error || '정리에 실패했습니다.';
      return;
    }
    dailyWorkInput.value = result.text;
    saveDraft();
  });
  [dailyWorkInput, tomorrowPlanInput, weeklyWorkInput, weeklyPlanInput, issuesInput].forEach((el) => {
    el.addEventListener('input', scheduleSaveDraft);
  });

  modeDailyBtn.addEventListener('click', () => setMode('daily'));
  modeWeeklyBtn.addEventListener('click', () => setMode('weekly'));

  addWorkItemBtn.addEventListener('click', () => {
    workItems.push({ title: '', progress: 0, decreaseReason: '' });
    renderWorkItems();
    saveDraft();
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
    const text =
      mode === 'daily'
        ? [
            `[일일업무보고 - ${dateInput.value}]`,
            `부서: ${departmentInput.value}`,
            `작성자: ${authorInput.value}`,
            '',
            '<금일 업무 내용>',
            dailyWorkInput.value || '(내용 없음)',
            ...(workItems.length
              ? ['', '<업무별 진행률>', ...workItems.map((i) => `- ${i.title}: ${i.progress}%${i.decreaseReason ? ` (진행률 감소 사유: ${i.decreaseReason})` : ''}`)]
              : []),
            '',
            '<명일 업무 계획>',
            tomorrowPlanInput.value || '(내용 없음)',
            '',
            '<특이사항>',
            issuesInput.value || '(내용 없음)',
          ].join('\n')
        : [
            `[주간업무보고 - ${dateInput.value}]`,
            `부서: ${departmentInput.value}`,
            `작성자: ${authorInput.value}`,
            '',
            '<지난주 내용>',
            weeklyWorkInput.value || '(내용 없음)',
            '',
            '<다음주 계획>',
            weeklyPlanInput.value || '(내용 없음)',
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

  // ---- 실행 로그 (크롤링/자동 제출 공용, 검색 필터 포함) ----
  let jobLogSearchQuery = '';

  function applyJobLogLineVisibility(line) {
    const matches = !jobLogSearchQuery || line.textContent.toLowerCase().includes(jobLogSearchQuery);
    line.hidden = !matches;
  }

  function updateJobLogSearchCount() {
    if (!jobLogSearchQuery) {
      jobLogSearchCount.textContent = '';
      return;
    }
    const total = jobLogOutput.children.length;
    const shown = jobLogOutput.querySelectorAll('.log-line:not([hidden])').length;
    jobLogSearchCount.textContent = `${shown} / ${total}줄 일치`;
  }

  jobLogSearchInput.addEventListener('input', () => {
    jobLogSearchQuery = jobLogSearchInput.value.trim().toLowerCase();
    Array.from(jobLogOutput.children).forEach(applyJobLogLineVisibility);
    updateJobLogSearchCount();
  });

  function appendJobLog(level, message) {
    const line = document.createElement('div');
    line.className = `log-line log-line-${level}`;
    line.textContent = message;
    applyJobLogLineVisibility(line);
    jobLogOutput.appendChild(line);
    if (!line.hidden) {
      jobLogOutput.scrollTop = jobLogOutput.scrollHeight;
    }
    updateJobLogSearchCount();
  }

  function showSubmitResult(kind, html) {
    submitResult.hidden = false;
    submitResult.className = `result-banner result-banner-${kind}`;
    submitResultIcon.textContent = kind === 'success' ? '✅' : '⚠️';
    submitResultText.innerHTML = html;
  }

  function hideSubmitResult() {
    submitResult.hidden = true;
    submitResult.className = 'result-banner';
  }

  // ---- ① 크롤링 ----
  async function refreshCrawlStatus() {
    const data = await window.api.getOfficeReports();
    latestOfficeData = data;
    renderSubmitPreview();

    if (!data || !data.reports || data.reports.length === 0) {
      crawlStatus.textContent = '아직 크롤링한 적이 없습니다.';
      return;
    }
    const latest = data.reports[0];
    const crawledAt = data.crawledAt ? new Date(data.crawledAt * 1000).toLocaleString() : '알 수 없음';
    crawlStatus.textContent = `'${data.targetName}' 기준 ${data.reports.length}건 저장됨 (마지막 크롤링: ${crawledAt}, 가장 최근 보고서: ${latest.report_date || '날짜 미상'})`;
  }

  // ---- 자동 제출 미리보기 (실제 /report/write 화면과 같은 7개 항목) ----
  const PREVIEW_FIELDS = [
    { key: 'monthly_work', fallbackLabel: '지난달 계획' },
    { key: 'monthly_plan', fallbackLabel: '이번달 계획' },
    { key: 'weekly_work', fallbackLabel: '지난주 내용' },
    { key: 'weekly_plan', fallbackLabel: '다음주 계획' },
    { key: 'daily_plan', fallbackLabel: '명일 업무 계획' },
  ];

  function renderSubmitPreview() {
    const latest = latestOfficeData && latestOfficeData.reports && latestOfficeData.reports[0];
    if (!latest) {
      submitPreviewGrid.hidden = true;
      previewEmptyHint.hidden = false;
      return;
    }
    previewEmptyHint.hidden = true;
    submitPreviewGrid.hidden = false;
    submitPreviewGrid.innerHTML = '';

    PREVIEW_FIELDS.forEach(({ key, fallbackLabel }) => {
      const label = latest[`${key}_label`] || fallbackLabel;
      const html = latest[`${key}_report`] || '';
      submitPreviewGrid.appendChild(buildPreviewCard(label, html, false));
    });

    const useLocal = useLocalDraftCheckbox.checked;
    const dailyWorkHtml = useLocal ? buildDailyWorkHtml() : latest.daily_work_report || '';
    const issuesHtml = useLocal ? buildIssuesHtml() : latest.issues || '';

    submitPreviewGrid.appendChild(buildPreviewCard('금일 업무 내용', dailyWorkHtml, true));
    submitPreviewGrid.appendChild(buildPreviewCard('특이사항', issuesHtml, true));
  }

  function buildPreviewCard(label, html, isFull) {
    const card = document.createElement('div');
    card.className = isFull ? 'preview-card preview-full' : 'preview-card';

    const labelEl = document.createElement('div');
    labelEl.className = 'preview-card-label';
    labelEl.textContent = label;

    const bodyEl = document.createElement('div');
    bodyEl.className = 'preview-card-body';
    if (html && html.trim()) {
      bodyEl.innerHTML = html;
    } else {
      bodyEl.textContent = '(내용 없음)';
      bodyEl.classList.add('preview-empty');
    }

    card.appendChild(labelEl);
    card.appendChild(bodyEl);
    return card;
  }

  crawlBtn.addEventListener('click', async () => {
    const targetName = officeTargetNameInput.value.trim();
    if (!targetName) {
      alert('크롤링할 대상 이름을 입력해주세요.');
      return;
    }
    settings.officeReportTargetName = targetName;
    await window.api.setSettings({ officeReportTargetName: targetName });

    jobLogOutput.innerHTML = '';
    activeJobKind = 'crawl';
    const result = await window.api.startJob({ jobId: 'office_report_crawl', targetName });
    if (!result.started) {
      alert('이미 실행 중인 작업이 있습니다.');
      activeJobKind = null;
      return;
    }
    crawlBtn.disabled = true;
    submitBtn.disabled = true;
  });

  // ---- ② 자동 제출 ----
  submitBtn.addEventListener('click', async () => {
    if (hasBlockingDecreaseReasons()) {
      alert('전날보다 진행률이 낮아진 업무가 있습니다. "진행률 감소 사유"를 먼저 입력해주세요.');
      return;
    }

    jobLogOutput.innerHTML = '';
    hideSubmitResult();
    activeJobKind = 'submit';

    const filePaths = Array.from(attachFilesInput.files || [])
      .map((f) => window.api.getPathForFile(f))
      .filter(Boolean);

    const payload = {
      jobId: 'office_report_submit',
      reportDate: dateInput.value,
      filePaths,
    };
    if (useLocalDraftCheckbox.checked) {
      const dailyWorkHtml = buildDailyWorkHtml();
      const issuesHtml = buildIssuesHtml();
      if (dailyWorkHtml) payload.dailyWorkOverride = dailyWorkHtml;
      if (issuesHtml) payload.issuesOverride = issuesHtml;
    }

    const result = await window.api.startJob(payload);
    if (!result.started) {
      alert('이미 실행 중인 작업이 있습니다.');
      activeJobKind = null;
      return;
    }
    crawlBtn.disabled = true;
    submitBtn.disabled = true;
  });

  window.api.onJobLog((data) => {
    appendJobLog(data.level || 'info', data.message || '');
  });

  window.api.onJobDone((data) => {
    if (typeof data.code === 'undefined') {
      // emit_done() 요약 정보
      if (activeJobKind === 'crawl' && data.summary) {
        refreshCrawlStatus();
      } else if (activeJobKind === 'submit' && data.summary) {
        const summary = data.summary;
        if (summary.success) {
          showSubmitResult('success', `제출 완료 — <a href="${summary.finalUrl}" target="_blank">${summary.finalUrl || ''}</a>`);
        } else {
          const alertPart = summary.alertText ? ` (알림창: "${summary.alertText}")` : '';
          showSubmitResult('error', `제출 실패 — ${summary.error || '알 수 없는 오류'}${alertPart}`);
        }
      }
      return;
    }

    appendJobLog('info', `작업 프로세스 종료 (종료 코드: ${data.code})`);
    crawlBtn.disabled = false;
    submitBtn.disabled = false;
    activeJobKind = null;
  });

  init();
}

window.renderWorkReportView = renderWorkReportView;
