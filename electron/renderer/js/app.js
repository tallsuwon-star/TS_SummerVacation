// 신규 작업 추가 시 여기에 jobId -> 렌더 함수를 등록한다.
const VIEW_RENDERERS = {
  morning_special_stats: (container) => window.renderMorningSpecialStatsView(container),
  overdue_report: (container) => window.renderOverdueReportView(container),
  vocaking_report: (container) => window.renderVocakingReportView(container),
  naver_store_report: (container) => window.renderNaverStoreReportView(container),
  work_report: (container) => window.renderWorkReportView(container),
};

function renderView(jobId) {
  const container = document.getElementById('main-content');
  const renderFn = VIEW_RENDERERS[jobId];

  if (!renderFn) {
    container.innerHTML = `<div class="empty-view">TODO: '${jobId}' 화면 구현이 필요합니다.</div>`;
    return;
  }

  renderFn(container);
}

window.renderView = renderView;

async function initTheme() {
  const settings = await window.api.getSettings();
  const theme = settings.theme || 'light';
  applyTheme(theme);

  document.getElementById('theme-toggle').addEventListener('click', async () => {
    const current = document.documentElement.getAttribute('data-theme');
    const next = current === 'dark' ? 'light' : 'dark';
    applyTheme(next);
    await window.api.setSettings({ theme: next });
  });
}

function applyTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
  document.getElementById('theme-toggle').textContent = theme === 'dark' ? '☀️' : '🌙';
}

async function initLmsSettingsModal() {
  const modal = document.getElementById('lms-settings-modal');
  const idInput = document.getElementById('lms-settings-id');
  const passwordInput = document.getElementById('lms-settings-password');
  const baseUrlInput = document.getElementById('lms-settings-base-url');

  document.getElementById('lms-settings-btn').addEventListener('click', async () => {
    const settings = await window.api.getSettings();
    const creds = settings.lmsCredentials || {};
    idInput.value = creds.id || '';
    passwordInput.value = creds.password || '';
    baseUrlInput.value = creds.baseUrl || '';
    modal.classList.remove('hidden');
  });

  document.getElementById('lms-settings-cancel-btn').addEventListener('click', () => {
    modal.classList.add('hidden');
  });

  document.getElementById('lms-settings-save-btn').addEventListener('click', async () => {
    await window.api.setSettings({
      lmsCredentials: {
        id: idInput.value.trim(),
        password: passwordInput.value,
        baseUrl: baseUrlInput.value.trim(),
      },
    });
    modal.classList.add('hidden');
  });
}

async function bootstrap() {
  window.appConfig = await window.api.getAppConfig();

  await initTheme();
  initLmsSettingsModal();
  window.sidebar.renderJobNav();
  await window.sidebar.renderInstallNav();
  window.sidebar.wireInstallModal();
  renderView(window.sidebar.getVisibleJobs()[0].id);
}

document.addEventListener('DOMContentLoaded', bootstrap);
