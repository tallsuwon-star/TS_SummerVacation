const { ipcMain } = require('electron');
const store = require('../store');
const { APP_VARIANT } = require('../variant');
const setupCheck = require('./setupCheck');
const pythonRunner = require('./pythonRunner');
const clipboard = require('./clipboard');
const gitLog = require('./gitLog');
const officeReports = require('./officeReports');
const anthropicClient = require('./anthropic');
const fileSave = require('./fileSave');
const roadAddress = require('./roadAddress');
const ideas = require('./ideas');
const taskScheduler = require('./taskScheduler');

function registerIpcHandlers(mainWindow) {
  ipcMain.handle('settings:get', () => store.store);
  ipcMain.handle('settings:set', (_event, partial) => {
    Object.entries(partial).forEach(([key, value]) => store.set(key, value));
    return store.store;
  });

  ipcMain.handle('app:getConfig', () => ({ variant: APP_VARIANT }));

  ipcMain.handle('setup:checkSelenium', () => setupCheck.checkSelenium());
  ipcMain.handle('setup:installSelenium', () => setupCheck.installSelenium(mainWindow));

  ipcMain.handle('job:start', (_event, payload) => pythonRunner.start(payload, mainWindow));
  ipcMain.handle('job:pause', () => pythonRunner.pause());
  ipcMain.handle('job:resume', () => pythonRunner.resume());
  ipcMain.handle('job:stop', () => pythonRunner.stop());
  ipcMain.handle('job:status', () => pythonRunner.getStatus());

  ipcMain.handle('clipboard:copy', (_event, text) => clipboard.copy(text));

  ipcMain.handle('report:getTodayCommits', () => gitLog.getTodayCommits());
  ipcMain.handle('report:getOfficeReports', () => officeReports.getLatestReports());
  ipcMain.handle('report:tidyText', (_event, rawText) => anthropicClient.tidyText(rawText));

  ipcMain.handle('file:reveal', (_event, sourcePath) => fileSave.revealFile(sourcePath));
  ipcMain.handle('link:openExternal', (_event, url) => fileSave.openExternal(url));

  ipcMain.handle('address:checkRoad', (_event, { address, apiKey }) => roadAddress.checkRoadAddress(address, apiKey));

  ipcMain.handle('ideas:list', () => ideas.listIdeas());
  ipcMain.handle('ideas:create', (_event, payload) => ideas.createIdea(payload));
  ipcMain.handle('ideas:delete', (_event, id) => ideas.deleteIdea(id));

  // "오늘 할 일" 알림을 실제 시각/주기를 기다리지 않고 바로 테스트해보는 용도.
  ipcMain.handle('tasks:testPopup', (_event, taskId) => {
    taskScheduler.testPopup(taskId);
  });
}

module.exports = registerIpcHandlers;
