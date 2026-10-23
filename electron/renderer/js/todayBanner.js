// 화면(사이드바 메뉴)이 바뀌어도 항상 떠 있는 "오늘 할 일" 배너.
//
// 설정한 시각이 되면 일렉트론 메인 프로세스(taskScheduler.js)가 자동으로
// 네이버 검색창을 띄워 "성규야 {업무명} 시작해라"로 검색해준다. 이 배너는
// 그 할 일 목록을 보여주고 추가/완료 체크/삭제를 할 수 있게 한다.
//
// 할 일은 todayTasks라는 이름으로 기존 설정 저장소(electron-store, settings:get/set)에
// 그대로 저장한다 — 매일 반복되는 시각(HH:MM)만 들고 있고, 그날 하루에 대해서만
// "이미 띄웠음"/완료 여부를 추적한다(날짜가 바뀌면 자동으로 초기화됨).

function _pad2(n) {
  return String(n).padStart(2, '0');
}

function _todayDateStr() {
  const d = new Date();
  return `${d.getFullYear()}-${_pad2(d.getMonth() + 1)}-${_pad2(d.getDate())}`;
}

function _naverSearchUrl(title) {
  const query = `성규야 ${title} 시작해라`;
  return `https://search.naver.com/search.naver?query=${encodeURIComponent(query)}`;
}

function initTodayBanner() {
  const container = document.getElementById('today-banner');

  container.innerHTML = `
    <div class="today-banner-header">
      <strong>오늘 할 일</strong>
      <span id="today-task-count" class="field-label"></span>
      <button id="today-task-toggle-add" class="btn btn-ghost" style="margin-left: auto;">+ 할 일 추가</button>
    </div>
    <div id="today-task-list" class="today-task-list"></div>
    <div id="today-task-add-row" class="today-task-add-row" hidden>
      <input type="time" id="today-task-time-input" />
      <input type="text" id="today-task-title-input" placeholder="업무명 (예: 환불처리)" style="flex: 1; min-width: 160px;" />
      <button id="today-task-add-btn" class="btn btn-primary">추가</button>
    </div>
  `;

  const listEl = document.getElementById('today-task-list');
  const countEl = document.getElementById('today-task-count');
  const toggleAddBtn = document.getElementById('today-task-toggle-add');
  const addRow = document.getElementById('today-task-add-row');
  const timeInput = document.getElementById('today-task-time-input');
  const titleInput = document.getElementById('today-task-title-input');
  const addBtn = document.getElementById('today-task-add-btn');

  function escapeHtml(text) {
    if (!text) return '';
    return String(text)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  async function getTasks() {
    const settings = await window.api.getSettings();
    return settings.todayTasks || [];
  }

  async function saveTasks(tasks) {
    await window.api.setSettings({ todayTasks: tasks });
  }

  function sortedTasks(tasks) {
    return [...tasks].sort((a, b) => (a.time || '').localeCompare(b.time || ''));
  }

  async function render() {
    const tasks = sortedTasks(await getTasks());
    const today = _todayDateStr();

    if (tasks.length === 0) {
      listEl.innerHTML = '<span class="field-label">등록된 할 일이 없습니다. "+ 할 일 추가"로 시간을 맞춰보세요.</span>';
      countEl.textContent = '';
      return;
    }

    countEl.textContent = `${tasks.length}건`;

    listEl.innerHTML = tasks
      .map((task) => {
        const completed = task.lastCompletedDate === today;
        return `
          <span class="today-task-item${completed ? ' completed' : ''}" data-id="${escapeHtml(task.id)}">
            <input type="checkbox" class="today-task-complete-cb" data-id="${escapeHtml(task.id)}" ${completed ? 'checked' : ''} title="오늘 완료" />
            <span class="today-task-time">${escapeHtml(task.time)}</span>
            <span>${escapeHtml(task.title)}</span>
            <button type="button" class="btn btn-ghost today-task-test-btn" data-id="${escapeHtml(task.id)}" title="지금 바로 네이버 검색창 테스트">▶</button>
            <button type="button" class="btn btn-ghost today-task-delete-btn" data-id="${escapeHtml(task.id)}" title="삭제">✕</button>
          </span>
        `;
      })
      .join('');

    listEl.querySelectorAll('.today-task-complete-cb').forEach((cb) => {
      cb.addEventListener('change', async () => {
        const allTasks = await getTasks();
        const updated = allTasks.map((t) =>
          t.id === cb.dataset.id ? { ...t, lastCompletedDate: cb.checked ? today : null } : t
        );
        await saveTasks(updated);
        render();
      });
    });

    listEl.querySelectorAll('.today-task-test-btn').forEach((btn) => {
      btn.addEventListener('click', async () => {
        const allTasks = await getTasks();
        const task = allTasks.find((t) => t.id === btn.dataset.id);
        if (task) window.api.openExternal(_naverSearchUrl(task.title));
      });
    });

    listEl.querySelectorAll('.today-task-delete-btn').forEach((btn) => {
      btn.addEventListener('click', async () => {
        const allTasks = await getTasks();
        await saveTasks(allTasks.filter((t) => t.id !== btn.dataset.id));
        render();
      });
    });
  }

  toggleAddBtn.addEventListener('click', () => {
    addRow.hidden = !addRow.hidden;
    if (!addRow.hidden) titleInput.focus();
  });

  addBtn.addEventListener('click', async () => {
    const time = timeInput.value;
    const title = titleInput.value.trim();
    if (!time) {
      alert('시각을 입력해주세요.');
      return;
    }
    if (!title) {
      alert('업무명을 입력해주세요.');
      return;
    }

    const allTasks = await getTasks();
    allTasks.push({
      id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      title,
      time,
      lastFiredDate: null,
      lastCompletedDate: null,
    });
    await saveTasks(allTasks);

    timeInput.value = '';
    titleInput.value = '';
    addRow.hidden = true;
    render();
  });

  render();
  // 날짜가 바뀌거나(완료 표시 초기화) 다른 화면에서 설정을 바꿨을 수도 있어
  // 주기적으로 다시 그린다.
  setInterval(render, 60000);
}

window.initTodayBanner = initTodayBanner;
