// "오늘 할 일" 알림: 설정해둔 시각이 되면 자동으로 네이버 검색창을 띄워
// "성규야 {업무명} 시작해라"로 검색해준다(사용자가 요청한 그대로의 알림
// 방식 — 별도 알림 UI 없이 그냥 눈에 띄게 브라우저 창이 뜨는 것).
//
// 할 일은 날짜가 아니라 시각(HH:MM)만 저장해 매일 반복된다. 같은 날 같은
// 할 일이 여러 번 뜨지 않도록 lastFiredDate로 "오늘 이미 띄웠는지"를,
// 완료 체크한 할 일은 lastCompletedDate로 "오늘은 띄우지 않을지"를 추적한다.
// 둘 다 날짜 문자열이라 다음 날이 되면 자연히 다시 조건을 만족하게 된다.

const { shell } = require('electron');
const store = require('../store');

const CHECK_INTERVAL_MS = 20000; // 분 경계를 놓치지 않을 정도로 촘촘하게 확인

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

function checkAndFire() {
  const tasks = store.get('todayTasks') || [];
  if (tasks.length === 0) return;

  const today = todayDateStr();
  const nowHHMM = currentHHMM();
  let changed = false;

  const updated = tasks.map((task) => {
    if (task.time !== nowHHMM) return task;
    if (task.lastFiredDate === today) return task; // 이미 오늘 띄움
    if (task.lastCompletedDate === today) return task; // 이미 완료 처리함

    shell.openExternal(naverSearchUrl(task.title));
    changed = true;
    return { ...task, lastFiredDate: today };
  });

  if (changed) store.set('todayTasks', updated);
}

let timer = null;

function startScheduler() {
  if (timer) return;
  checkAndFire(); // 앱을 막 켰는데 마침 그 시각이면 바로 확인
  timer = setInterval(checkAndFire, CHECK_INTERVAL_MS);
}

function stopScheduler() {
  if (timer) clearInterval(timer);
  timer = null;
}

module.exports = { startScheduler, stopScheduler, naverSearchUrl };
