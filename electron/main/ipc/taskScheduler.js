// "오늘 할 일" 알림: 업무마다 알림 방식이 다르다.
//   - daily(매일 정해진 시간): 그 시각이 되면 하루에 한 번만 울린다.
//   - interval(시간 미정, N분마다): 시간을 아직 못 정한 업무를 "해야 한다"고
//     계속 알려주려고 N분(기본 30분)마다 반복해서 울린다. 사용자가 나중에
//     이 업무에 시간을 정해주면(fixTaskTime) daily로 바뀌어 그때부터는 그
//     시각에만 울린다.
//   - todo(알림 없음): 그냥 나중에 보려고 적어두는 목록. 울리지 않는다.
//
// 알림은 사용자가 명시적으로 요청한 대로 "새 창 팝업"으로 띄운다 — 기존에
// 열려있는 브라우저 창의 새 탭이 아니라, 매번 독립된 새 BrowserWindow를
// 만들어 네이버 검색 결과를 그 안에 바로 띄운다.

const { BrowserWindow } = require('electron');
const store = require('../store');

const CHECK_INTERVAL_MS = 20000; // 분 경계를 놓치지 않을 정도로 촘촘하게 확인
const DEFAULT_INTERVAL_MINUTES = 30;

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

// 매번 새 BrowserWindow를 만든다 — 기존 창을 재사용하거나 그 안에 탭으로
// 열리지 않도록(사용자가 명시적으로 요청한 "기존에 있던 창 말고").
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

    if (mode === 'interval') {
      if (!shouldFireInterval(task, now, today)) return task;
      openNaverPopup(task.title);
      changed = true;
      return { ...task, lastFiredAt: now.toISOString() };
    }

    // mode === 'daily'
    if (!shouldFireDaily(task, today, nowHHMM)) return task;
    openNaverPopup(task.title);
    changed = true;
    return { ...task, lastFiredDate: today };
  });

  if (changed) store.set('todayTasks', updated);
}

let timer = null;

function startScheduler() {
  if (timer) return;
  checkAndFire(); // 앱을 막 켰는데 마침 그 시각/주기면 바로 확인
  timer = setInterval(checkAndFire, CHECK_INTERVAL_MS);
}

function stopScheduler() {
  if (timer) clearInterval(timer);
  timer = null;
}

module.exports = { startScheduler, stopScheduler, openNaverPopup, naverSearchUrl };
