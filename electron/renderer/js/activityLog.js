// "오늘의 활동 기록" 공용 헬퍼.
//
// 업무보고(workReport.js)에 쓸 "오늘 한 일"을 한 곳에 모아둔다 — 루틴
// 업무를 완료 체크하면(todayPanel.js), 특정 작업이 끝나면(예: 미납자
// 관리 조회), 또는 사용자가 급하게 처리한 업무를 직접 추가하면 전부 이
// 기록에 쌓인다. 실제로 업무보고에 넣을지 말지는 각 항목의 included
// 값으로 사용자가 직접 고른다(workReport.js의 "오늘의 활동 기록" 섹션).
//
// 날짜별(today-panel의 todayTasks와 달리 매일 반복되는 개념이 아니라,
// 그날그날의 실제 활동 로그라서)로 저장하고, 오래된 날짜도 기록이 남아
// 있으면 업무보고 날짜를 바꿔 과거 기록을 다시 볼 수 있게 한다.

function _pad2(n) {
  return String(n).padStart(2, '0');
}

function _dateKey(d = new Date()) {
  return `${d.getFullYear()}-${_pad2(d.getMonth() + 1)}-${_pad2(d.getDate())}`;
}

function _timeNow() {
  const d = new Date();
  return `${_pad2(d.getHours())}:${_pad2(d.getMinutes())}`;
}

async function getActivityLog(dateKey) {
  const settings = await window.api.getSettings();
  const log = settings.activityLog || {};
  return log[dateKey || _dateKey()] || [];
}

async function appendActivityLogEntry({ source, title, detail, url, dateKey }) {
  const settings = await window.api.getSettings();
  const log = { ...(settings.activityLog || {}) };
  const key = dateKey || _dateKey();
  const entries = [...(log[key] || [])];

  entries.push({
    id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    time: _timeNow(),
    source: source || 'adhoc',
    title: title || '',
    detail: detail || '',
    url: url || null,
    included: true,
  });

  log[key] = entries;
  await window.api.setSettings({ activityLog: log });
  return entries[entries.length - 1];
}

async function updateActivityLogEntry(dateKey, id, patch) {
  const settings = await window.api.getSettings();
  const log = { ...(settings.activityLog || {}) };
  const entries = (log[dateKey] || []).map((e) => (e.id === id ? { ...e, ...patch } : e));
  log[dateKey] = entries;
  await window.api.setSettings({ activityLog: log });
}

async function deleteActivityLogEntry(dateKey, id) {
  const settings = await window.api.getSettings();
  const log = { ...(settings.activityLog || {}) };
  log[dateKey] = (log[dateKey] || []).filter((e) => e.id !== id);
  await window.api.setSettings({ activityLog: log });
}

// 업무보고 "금일 업무 내용"에 이어붙일 HTML(<ul><li>...). included인 항목만,
// 시간순으로. url이 있으면 하이퍼링크로(황병권 업무보고처럼).
function buildActivityLogHtml(entries) {
  const included = entries.filter((e) => e.included !== false);
  if (included.length === 0) return '';

  const escapeHtml = (text) =>
    String(text || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');

  const items = included
    .map((e) => {
      const titleHtml = e.url
        ? `<a href="${escapeHtml(e.url)}" target="_blank">${escapeHtml(e.title)}</a>`
        : `<b>${escapeHtml(e.title)}</b>`;
      const detailHtml = e.detail ? `: ${escapeHtml(e.detail)}` : '';
      return `<li>${escapeHtml(e.time)} — ${titleHtml}${detailHtml}</li>`;
    })
    .join('');

  return `<ul>${items}</ul>`;
}

// 특정 작업이 성공적으로 끝나면 화면과 무관하게 자동으로 "오늘의 활동
// 기록"에 남긴다. 지금은 사용자가 직접 요청한 "미납자 관리" 하나만
// 연결돼 있다 — 다른 작업도 자동 기록하고 싶으면 이 표에 jobId와 어떤
// summary 값을 어떻게 요약할지만 추가하면 된다.
const AUTO_LOG_JOBS = {
  overdue_report: {
    title: '미납자 관리 조회',
    detail: (summary) => (typeof summary.total === 'number' ? `총 ${summary.total}명` : ''),
  },
};

function initActivityLogAutoCapture() {
  window.api.onJobCompletedSummary(({ jobId, summary }) => {
    const spec = AUTO_LOG_JOBS[jobId];
    if (!spec || !summary) return;
    appendActivityLogEntry({
      source: 'job',
      title: spec.title,
      detail: spec.detail ? spec.detail(summary) : '',
      url: spec.url ? spec.url(summary) : null,
    });
  });
}

window.activityLog = {
  dateKey: _dateKey,
  get: getActivityLog,
  append: appendActivityLogEntry,
  update: updateActivityLogEntry,
  remove: deleteActivityLogEntry,
  buildHtml: buildActivityLogHtml,
  initAutoCapture: initActivityLogAutoCapture,
};
