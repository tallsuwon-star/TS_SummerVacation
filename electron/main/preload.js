const { contextBridge, ipcRenderer, webUtils } = require('electron');

contextBridge.exposeInMainWorld('api', {
  // 설정 (electron-store)
  getSettings: () => ipcRenderer.invoke('settings:get'),
  setSettings: (partial) => ipcRenderer.invoke('settings:set', partial),

  // 빌드 변형 (전체 앱 vs 미납자 관리 전용 배포용 exe)
  getAppConfig: () => ipcRenderer.invoke('app:getConfig'),

  // Selenium 설치 확인/설치
  checkSelenium: () => ipcRenderer.invoke('setup:checkSelenium'),
  installSelenium: () => ipcRenderer.invoke('setup:installSelenium'),
  onInstallLog: (callback) => {
    ipcRenderer.removeAllListeners('setup:installLog');
    ipcRenderer.on('setup:installLog', (_event, line) => callback(line));
  },

  // 작업(Job) 실행 제어
  startJob: (payload) => ipcRenderer.invoke('job:start', payload),
  pauseJob: () => ipcRenderer.invoke('job:pause'),
  resumeJob: () => ipcRenderer.invoke('job:resume'),
  stopJob: () => ipcRenderer.invoke('job:stop'),
  onJobProgress: (callback) => {
    ipcRenderer.removeAllListeners('job:progress');
    ipcRenderer.on('job:progress', (_event, data) => callback(data));
  },
  onJobLog: (callback) => {
    ipcRenderer.removeAllListeners('job:log');
    ipcRenderer.on('job:log', (_event, data) => callback(data));
  },
  onJobRecord: (callback) => {
    ipcRenderer.removeAllListeners('job:record');
    ipcRenderer.on('job:record', (_event, data) => callback(data));
  },
  onJobDone: (callback) => {
    ipcRenderer.removeAllListeners('job:done');
    ipcRenderer.on('job:done', (_event, data) => callback(data));
  },

  // 결과 요약 클립보드 복사 (pyperclip)
  copySummary: (text) => ipcRenderer.invoke('clipboard:copy', text),

  // 업무보고: 오늘 커밋 내역 불러오기
  getTodayCommits: () => ipcRenderer.invoke('report:getTodayCommits'),

  // 업무보고: office.talkstation.co.kr 크롤링 결과(JSON) 읽기
  getOfficeReports: () => ipcRenderer.invoke('report:getOfficeReports'),

  // 업무보고: Claude API로 메모 정리하기
  tidyText: (rawText) => ipcRenderer.invoke('report:tidyText', rawText),

  // 업무보고: <input type="file">로 고른 파일의 실제 경로 (Electron 32+에서는
  // File.path가 제거되어 webUtils.getPathForFile로만 얻을 수 있다).
  getPathForFile: (file) => webUtils.getPathForFile(file),
});
