// 신규 작업(job) 추가 시 여기에 항목을 등록하고,
// electron/renderer/js/views/ 에 뷰 파일을, app.js의 VIEW_RENDERERS에 렌더 함수를 등록한다.
const ALL_JOBS = [
  { id: 'morning_special_stats', label: '오전특강 통계' },
  { id: 'overdue_report', label: '미납자 관리' },
  { id: 'vocaking_report', label: '보카킹 보고' },
];

const INSTALL_CHECKS = [{ id: 'selenium', label: 'Selenium' }];

// 'overdue_only' 배포용 exe(scripts/build-overdue-exe.js 참고)에서는 '미납자
// 관리'만 노출한다. window.appConfig는 app.js의 bootstrap()에서 렌더 전에
// 미리 채워둔다.
function getVisibleJobs() {
  if (window.appConfig?.variant === 'overdue_only') {
    return ALL_JOBS.filter((job) => job.id === 'overdue_report');
  }
  return ALL_JOBS;
}

let activeJobId = null;

function renderJobNav() {
  const jobs = getVisibleJobs();
  if (!activeJobId) activeJobId = jobs[0].id;

  const list = document.getElementById('job-nav-list');
  list.innerHTML = '';

  jobs.forEach((job) => {
    const li = document.createElement('li');
    li.className = `nav-item${job.id === activeJobId ? ' active' : ''}`;
    li.textContent = job.label;
    li.dataset.jobId = job.id;
    li.addEventListener('click', () => {
      if (job.id === activeJobId) return;
      activeJobId = job.id;
      renderJobNav();
      window.renderView(job.id);
    });
    list.appendChild(li);
  });
}

async function renderInstallNav() {
  // 배포용(overdue_only) exe는 PyInstaller가 Python까지 이미 넣어서 배포하므로
  // Selenium 설치 확인 UI 자체가 필요 없다 -> 섹션을 통째로 숨긴다.
  const section = document.getElementById('install-nav-section');
  if (window.appConfig?.variant === 'overdue_only') {
    section.hidden = true;
    return;
  }
  section.hidden = false;

  const list = document.getElementById('install-nav-list');
  list.innerHTML = '';

  for (const item of INSTALL_CHECKS) {
    const li = document.createElement('li');
    li.className = 'nav-item install-item';
    li.dataset.installId = item.id;

    // TODO: item.id 별로 다른 체크 함수를 매핑해야 설치 대상이 늘어나도 확장 가능
    const status = await window.api.checkSelenium();

    li.innerHTML = `
      <span>${item.label}</span>
      <span class="badge ${status.installed ? 'badge-ok' : 'badge-warn'}">
        ${status.installed ? '설치됨' : '설치 필요'}
      </span>
    `;

    if (!status.installed) {
      li.classList.add('needs-install');
      li.addEventListener('click', openInstallModal);
    }

    list.appendChild(li);
  }
}

function openInstallModal() {
  document.getElementById('install-confirm-modal').classList.remove('hidden');
}

function closeInstallModal() {
  document.getElementById('install-confirm-modal').classList.add('hidden');
}

function wireInstallModal() {
  document.getElementById('install-cancel-btn').addEventListener('click', closeInstallModal);

  document.getElementById('install-confirm-btn').addEventListener('click', async () => {
    const logEl = document.getElementById('install-log');
    logEl.classList.remove('hidden');
    logEl.textContent = '';

    window.api.onInstallLog((line) => {
      logEl.textContent += line;
      logEl.scrollTop = logEl.scrollHeight;
    });

    const result = await window.api.installSelenium();
    logEl.textContent += result.success ? '\n설치 완료' : '\n설치 실패';

    await renderInstallNav();
  });
}

window.sidebar = { renderJobNav, renderInstallNav, wireInstallModal, ALL_JOBS, getVisibleJobs };
