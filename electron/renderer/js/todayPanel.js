// 화면(사이드바 메뉴)이 바뀌어도 항상 떠 있는 오른쪽 "오늘 할 일" 패널.
// (예전엔 상단 배너였는데 본문을 너무 가려서 오른쪽 좁은 패널로 옮김.)
//
// 업무마다 알림 방식이 다르다:
//   - daily(매일 정해진 시간): 그 시각에 하루 한 번, 새 창 팝업으로 네이버에서
//     "성규야 {업무명} 시작해라"를 검색해 보여준다.
//   - interval(시간 미정): 아직 시간을 못 정한 업무를 잊지 않도록 N분(기본
//     30분)마다 반복해서 같은 방식으로 띄운다. 아래 "시간 고정" 입력으로
//     나중에 시간을 정해주면 그때부터는 daily로 바뀌어 그 시각에만 울린다.
//   - todo(알림 없음): 그냥 나중에 보려고 적어두는 목록. 울리지 않는다.
//
// 모든 알림은 기존에 열려있는 브라우저 창을 재사용하지 않고 항상 새 창
// 팝업(일렉트론 BrowserWindow)으로 뜬다 — 메인 프로세스의
// taskScheduler.js가 처리한다.

function _todayDateStr() {
  const d = new Date();
  const pad = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

const MODE_LABEL = { daily: '매일 정해진 시간', interval: '시간 미정 (반복 알림)', todo: '할 일 (알림 없음)' };

function initTodayPanel() {
  const container = document.getElementById('today-panel');

  container.innerHTML = `
    <div class="today-panel-header">
      <strong>오늘 할 일</strong>
      <button id="today-task-toggle-add" class="btn btn-ghost">+ 추가</button>
    </div>

    <div id="today-task-add-form" class="today-task-add-form" hidden>
      <select id="today-task-mode-input">
        <option value="daily">매일 정해진 시간</option>
        <option value="interval">시간 미정 (N분마다 반복 알림)</option>
        <option value="todo">할 일만 등록 (알림 없음)</option>
      </select>
      <input type="text" id="today-task-title-input" placeholder="업무명 (예: 환불처리)" />
      <input type="time" id="today-task-time-input" />
      <input type="number" id="today-task-interval-input" min="5" step="5" value="30" placeholder="몇 분마다" hidden />
      <button id="today-task-add-btn" class="btn btn-primary">추가</button>
    </div>

    <div id="today-task-sections"></div>
  `;

  const toggleAddBtn = container.querySelector('#today-task-toggle-add');
  const addForm = container.querySelector('#today-task-add-form');
  const modeInput = container.querySelector('#today-task-mode-input');
  const titleInput = container.querySelector('#today-task-title-input');
  const timeInput = container.querySelector('#today-task-time-input');
  const intervalInput = container.querySelector('#today-task-interval-input');
  const addBtn = container.querySelector('#today-task-add-btn');
  const sectionsEl = container.querySelector('#today-task-sections');

  function escapeHtml(text) {
    if (!text) return '';
    return String(text)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function syncAddFormFields() {
    const mode = modeInput.value;
    timeInput.hidden = mode !== 'daily';
    intervalInput.hidden = mode !== 'interval';
  }
  modeInput.addEventListener('change', syncAddFormFields);
  syncAddFormFields();

  toggleAddBtn.addEventListener('click', () => {
    addForm.hidden = !addForm.hidden;
    if (!addForm.hidden) titleInput.focus();
  });

  async function getTasks() {
    const settings = await window.api.getSettings();
    return settings.todayTasks || [];
  }

  async function saveTasks(tasks) {
    await window.api.setSettings({ todayTasks: tasks });
  }

  addBtn.addEventListener('click', async () => {
    const mode = modeInput.value;
    const title = titleInput.value.trim();
    if (!title) {
      alert('업무명을 입력해주세요.');
      return;
    }
    if (mode === 'daily' && !timeInput.value) {
      alert('시각을 입력해주세요.');
      return;
    }

    const task = {
      id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      title,
      mode,
      time: mode === 'daily' ? timeInput.value : null,
      intervalMinutes: mode === 'interval' ? Math.max(5, parseInt(intervalInput.value, 10) || 30) : null,
      lastFiredDate: null,
      lastFiredAt: null,
      lastCompletedDate: null,
    };

    const tasks = await getTasks();
    tasks.push(task);
    await saveTasks(tasks);

    titleInput.value = '';
    timeInput.value = '';
    intervalInput.value = '30';
    addForm.hidden = true;
    render();
  });

  function taskItemHtml(task, today) {
    const mode = task.mode || 'daily';
    const completed = task.lastCompletedDate === today;
    const timeLabel =
      mode === 'daily' ? task.time : mode === 'interval' ? `${task.intervalMinutes || 30}분마다` : '-';

    const fixRow =
      mode !== 'daily'
        ? `
          <div class="today-task-fix-row">
            <input type="time" class="today-task-fix-time" data-id="${escapeHtml(task.id)}" style="flex: 1;" />
            <button type="button" class="btn btn-ghost today-task-fix-btn" data-id="${escapeHtml(task.id)}" title="이 시간으로 매일 고정">고정</button>
          </div>
        `
        : '';

    return `
      <div class="today-task-item${completed ? ' completed' : ''}" data-id="${escapeHtml(task.id)}">
        <input type="checkbox" class="today-task-complete-cb" data-id="${escapeHtml(task.id)}" ${completed ? 'checked' : ''} title="오늘 완료" />
        <span class="today-task-time">${escapeHtml(timeLabel)}</span>
        <span class="today-task-title" title="${escapeHtml(task.title)}">${escapeHtml(task.title)}</span>
        <button type="button" class="btn btn-ghost today-task-test-btn" data-id="${escapeHtml(task.id)}" title="지금 바로 알림 테스트 (시작/미루기 팝업)">▶</button>
        <button type="button" class="btn btn-ghost today-task-delete-btn" data-id="${escapeHtml(task.id)}" title="삭제">✕</button>
      </div>
      ${fixRow}
    `;
  }

  async function render() {
    const tasks = await getTasks();
    const today = _todayDateStr();

    if (tasks.length === 0) {
      sectionsEl.innerHTML = '<div class="field-label">등록된 할 일이 없습니다. "+ 추가"로 시작해보세요.</div>';
      return;
    }

    const daily = tasks.filter((t) => (t.mode || 'daily') === 'daily').sort((a, b) => (a.time || '').localeCompare(b.time || ''));
    const interval = tasks.filter((t) => t.mode === 'interval');
    const todo = tasks.filter((t) => t.mode === 'todo');

    const sections = [
      { title: '매일 루틴', items: daily },
      { title: '시간 미정 (반복 알림)', items: interval },
      { title: '할 일 (알림 없음)', items: todo },
    ].filter((s) => s.items.length > 0);

    sectionsEl.innerHTML = sections
      .map(
        (section) => `
          <div class="today-panel-section-title">${escapeHtml(section.title)} (${section.items.length})</div>
          <div class="today-task-list">
            ${section.items.map((t) => taskItemHtml(t, today)).join('')}
          </div>
        `
      )
      .join('');

    sectionsEl.querySelectorAll('.today-task-complete-cb').forEach((cb) => {
      cb.addEventListener('change', async () => {
        const allTasks = await getTasks();
        const updated = allTasks.map((t) =>
          t.id === cb.dataset.id ? { ...t, lastCompletedDate: cb.checked ? today : null } : t
        );
        await saveTasks(updated);
        render();
      });
    });

    sectionsEl.querySelectorAll('.today-task-test-btn').forEach((btn) => {
      btn.addEventListener('click', () => {
        window.api.testTaskPopup(btn.dataset.id);
      });
    });

    sectionsEl.querySelectorAll('.today-task-delete-btn').forEach((btn) => {
      btn.addEventListener('click', async () => {
        const allTasks = await getTasks();
        await saveTasks(allTasks.filter((t) => t.id !== btn.dataset.id));
        render();
      });
    });

    sectionsEl.querySelectorAll('.today-task-fix-btn').forEach((btn) => {
      btn.addEventListener('click', async () => {
        const input = sectionsEl.querySelector(`.today-task-fix-time[data-id="${btn.dataset.id}"]`);
        const time = input?.value;
        if (!time) {
          alert('고정할 시각을 입력해주세요.');
          return;
        }
        const allTasks = await getTasks();
        const updated = allTasks.map((t) =>
          t.id === btn.dataset.id
            ? {
                ...t,
                mode: 'daily',
                time,
                intervalMinutes: null,
                lastFiredAt: null,
                lastFiredDate: null,
                lastCompletedDate: null,
              }
            : t
        );
        await saveTasks(updated);
        render();
      });
    });
  }

  render();
  // 날짜가 바뀌거나(완료 표시 초기화) 다른 화면에서 설정을 바꿨을 수도 있어
  // 주기적으로 다시 그린다.
  setInterval(render, 60000);
}

window.initTodayPanel = initTodayPanel;
