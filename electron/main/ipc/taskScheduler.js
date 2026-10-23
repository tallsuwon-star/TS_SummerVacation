// "오늘 할 일" 알림: 업무마다 알림 방식이 다르다.
//   - daily(매일 정해진 시간): 그 시각이 되면 하루에 한 번만 울린다.
//   - interval(시간 미정, N분마다): 시간을 아직 못 정한 업무를 "해야 한다"고
//     계속 알려주려고 N분(기본 30분)마다 반복해서 울린다. 사용자가 나중에
//     패널에서 시각을 정해주면 daily로 바뀌어 그때부터는 그 시각에만 울린다.
//   - todo(알림 없음): 그냥 나중에 보려고 적어두는 목록. 울리지 않는다.
//
// 알림이 뜰 때는 바로 네이버 검색창을 띄우지 않고, 먼저 화면 우측 하단에
// 작은 토스트 알림처럼(틀 없는 작은 창, 항상 위) "지금 시작" / "20분 후
// 다시"를 고르는 결정 팝업을 띄운다. "지금 시작"을 누르면 그제서야
// 네이버에서 "성규야 {업무명} 시작해라"를 검색한 새 창이 뜨고, "20분 후
// 다시"를 누르면 그 순간부터 SNOOZE_MINUTES분 뒤 같은 토스트가 다시
// 뜬다(원래 daily/interval 주기와 무관하게 한 번 더).
//
// 모든 팝업은 기존에 열려있는 브라우저/창을 재사용하지 않고 항상 새
// BrowserWindow로 띄운다 — 사용자가 명시적으로 요청한 "기존에 있던 창 말고".

const { BrowserWindow, ipcMain, screen } = require('electron');
const store = require('../store');

const CHECK_INTERVAL_MS = 20000; // 분 경계를 놓치지 않을 정도로 촘촘하게 확인
const DEFAULT_INTERVAL_MINUTES = 30;
const SNOOZE_MINUTES = 20;

// 결정 팝업(토스트) 크기/화면 우측 하단 여백.
const TOAST_WIDTH = 340;
const TOAST_HEIGHT = 170;
const TOAST_MARGIN = 20;

function pad2(n) {
  return String(n).padStart(2, '0');
}

function todayDateStr(d = new Date()) {
  return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}`;
}

function currentHHMM(d = new Date()) {
  return `${pad2(d.getHours())}:${pad2(d.getMinutes())}`;
}

function naverSearchUrl(title) {
  const query = `성규야 ${title} 시작해라`;
  return `https://search.naver.com/search.naver?query=${encodeURIComponent(query)}`;
}

function escapeHtml(text) {
  return String(text ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// 매번 새 BrowserWindow를 만든다 — 기존 창을 재사용하거나 그 안에 탭으로
// 열리지 않도록.
function openNaverPopup(title) {
  const popup = new BrowserWindow({
    width: 960,
    height: 720,
    title: `성규야 ${title} 시작해라`,
    webPreferences: { sandbox: true },
  });
  popup.loadURL(naverSearchUrl(title));
  return popup;
}

// 동시에 여러 알림이 뜰 때 토스트끼리 겹치지 않도록, 지금 떠 있는 토스트
// 개수만큼 위로 쌓아 올린다. 창이 닫히면(결정 또는 사용자가 직접 닫음) 자리에서 뺀다.
const openToasts = [];

function toastPosition(index) {
  const display = screen.getPrimaryDisplay();
  const { x: areaX, y: areaY, width, height } = display.workArea;
  const x = areaX + width - TOAST_WIDTH - TOAST_MARGIN;
  const y = areaY + height - TOAST_HEIGHT - TOAST_MARGIN - index * (TOAST_HEIGHT + 12);
  return { x, y };
}

// "지금 시작" / "20분 후 다시"를 고르는 결정 팝업. 일반 창이 아니라 화면
// 우측 하단에 뜨는 작은 토스트 알림처럼 보이도록 틀 없이(frameless) 그
// 자리에 띄운다. 외부 URL을 전혀 불러오지 않고 우리가 직접 만든 로컬
// HTML만 보여주므로, nodeIntegration을 켜서 ipcRenderer로 바로 메인
// 프로세스에 선택 결과를 보낸다.
function openDecisionPopup(task) {
  const { x, y } = toastPosition(openToasts.length);

  const popup = new BrowserWindow({
    width: TOAST_WIDTH,
    height: TOAST_HEIGHT,
    x,
    y,
    frame: false,
    resizable: false,
    alwaysOnTop: true,
    skipTaskbar: true,
    title: `성규야 ${task.title} 시작해라`,
    webPreferences: { nodeIntegration: true, contextIsolation: false },
  });

  openToasts.push(popup);
  popup.on('closed', () => {
    const idx = openToasts.indexOf(popup);
    if (idx !== -1) openToasts.splice(idx, 1);

    // "지금 시작"/"20분 후 다시"를 누르지 않고 ✕로 그냥 닫은 경우, pendingDecision이
    // 그대로 남아 다시는 안 울리게 되는 걸 막기 위해 미루기로 처리한다.
    const tasks = store.get('todayTasks') || [];
    const current = tasks.find((t) => t.id === task.id);
    if (current && current.pendingDecision) {
      handleDecision(task.id, 'snooze');
    }
  });

  const html = `<!DOCTYPE html>
<html><head><meta charset="utf-8" />
<style>
  * { box-sizing: border-box; }
  html, body { margin: 0; height: 100%; }
  body {
    position: relative;
    font-family: -apple-system, "Malgun Gothic", "Apple SD Gothic Neo", sans-serif;
    display: flex;
    flex-direction: column;
    justify-content: center;
    padding: 18px 20px;
    background: #1f2430;
    color: #fff;
    border: 1px solid #39405a;
    border-radius: 10px;
  }
  h2 { margin: 0 0 6px; font-size: 15px; }
  p { color: #aab0c6; margin: 0 0 16px; font-size: 12px; }
  .btn-row { display: flex; gap: 8px; }
  button { flex: 1; font-size: 13px; padding: 9px 0; border: none; border-radius: 6px; cursor: pointer; }
  .start { background: #2d6cdf; color: #fff; }
  .snooze { background: #39405a; color: #e4e6f0; }
  #close-btn { position: absolute; top: 8px; right: 10px; background: none; color: #888; font-size: 14px; padding: 0; flex: none; }
</style>
</head>
<body>
  <button id="close-btn" title="닫기">✕</button>
  <h2>성규야 ${escapeHtml(task.title)} 시작해라</h2>
  <p>지금 시작할까요, ${SNOOZE_MINUTES}분 뒤에 다시 알려드릴까요?</p>
  <div class="btn-row">
    <button id="start-btn" class="start">지금 시작</button>
    <button id="snooze-btn" class="snooze">${SNOOZE_MINUTES}분 후 다시</button>
  </div>
  <script>
    const { ipcRenderer } = require('electron');
    const taskId = ${JSON.stringify(task.id)};
    document.getElementById('start-btn').addEventListener('click', () => {
      ipcRenderer.send('task-decision', { taskId, action: 'start' });
      window.close();
    });
    document.getElementById('snooze-btn').addEventListener('click', () => {
      ipcRenderer.send('task-decision', { taskId, action: 'snooze' });
      window.close();
    });
    document.getElementById('close-btn').addEventListener('click', () => window.close());
  </script>
</body></html>`;

  popup.loadURL(`data:text/html;charset=utf-8,${encodeURIComponent(html)}`);
  return popup;
}

function shouldFireDaily(task, today, nowHHMM) {
  if (task.time !== nowHHMM) return false;
  if (task.lastFiredDate === today) return false; // 오늘 이미 울림
  if (task.lastCompletedDate === today) return false; // 오늘 완료 처리함
  return true;
}

function shouldFireInterval(task, now, today) {
  if (task.lastCompletedDate === today) return false; // 오늘 완료 처리함
  const intervalMs = (task.intervalMinutes || DEFAULT_INTERVAL_MINUTES) * 60000;
  if (!task.lastFiredAt) return true; // 등록 후 아직 한 번도 안 울렸으면 바로
  return now.getTime() - new Date(task.lastFiredAt).getTime() >= intervalMs;
}

function checkAndFire() {
  const tasks = store.get('todayTasks') || [];
  if (tasks.length === 0) return;

  const now = new Date();
  const today = todayDateStr(now);
  const nowHHMM = currentHHMM(now);
  let changed = false;

  const updated = tasks.map((task) => {
    const mode = task.mode || 'daily'; // 예전 데이터(모드 필드 없음) 호환

    if (mode === 'todo') return task; // 알림 없음
    if (task.pendingDecision) return task; // 결정 팝업에 아직 응답 안 함 — 중복으로 또 띄우지 않는다

    // "20분 후 다시" 선택한 지 SNOOZE_MINUTES분이 지났으면, 원래 daily/interval
    // 주기와 상관없이 결정 팝업을 한 번 더 띄운다.
    if (task.snoozeUntil) {
      if (now.getTime() < new Date(task.snoozeUntil).getTime()) return task;
      openDecisionPopup(task);
      changed = true;
      return { ...task, pendingDecision: true, snoozeUntil: null };
    }

    if (mode === 'interval') {
      if (!shouldFireInterval(task, now, today)) return task;
      openDecisionPopup(task);
      changed = true;
      return { ...task, pendingDecision: true };
    }

    // mode === 'daily'
    if (!shouldFireDaily(task, today, nowHHMM)) return task;
    openDecisionPopup(task);
    changed = true;
    return { ...task, pendingDecision: true };
  });

  if (changed) store.set('todayTasks', updated);
}

// 결정 팝업에서 "지금 시작"/"20분 후 다시"를 눌렀을 때 호출된다.
function handleDecision(taskId, action) {
  const tasks = store.get('todayTasks') || [];
  const now = new Date();
  const today = todayDateStr(now);

  const updated = tasks.map((task) => {
    if (task.id !== taskId) return task;

    if (action === 'start') {
      openNaverPopup(task.title);
      const base = { ...task, pendingDecision: false, snoozeUntil: null };
      return (task.mode || 'daily') === 'interval'
        ? { ...base, lastFiredAt: now.toISOString() }
        : { ...base, lastFiredDate: today };
    }

    if (action === 'snooze') {
      const snoozeUntil = new Date(now.getTime() + SNOOZE_MINUTES * 60000).toISOString();
      return { ...task, pendingDecision: false, snoozeUntil };
    }

    return task;
  });

  store.set('todayTasks', updated);
}

// 실제 시각/주기를 기다리지 않고 결정 팝업을 바로 테스트해보는 용도.
function testPopup(taskId) {
  const tasks = store.get('todayTasks') || [];
  const task = tasks.find((t) => t.id === taskId);
  if (task) openDecisionPopup(task);
}

let timer = null;
let decisionHandlerRegistered = false;

function startScheduler() {
  if (!decisionHandlerRegistered) {
    ipcMain.on('task-decision', (_event, { taskId, action }) => handleDecision(taskId, action));
    decisionHandlerRegistered = true;
  }

  if (timer) return;
  checkAndFire(); // 앱을 막 켰는데 마침 그 시각/주기면 바로 확인
  timer = setInterval(checkAndFire, CHECK_INTERVAL_MS);
}

function stopScheduler() {
  if (timer) clearInterval(timer);
  timer = null;
}

module.exports = { startScheduler, stopScheduler, testPopup, naverSearchUrl };
