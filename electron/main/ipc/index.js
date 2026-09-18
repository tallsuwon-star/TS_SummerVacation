const { ipcMain } = require('electron');
const store = require('../store');
const { APP_VARIANT } = require('../variant');
const setupCheck = require('./setupCheck');
const pythonRunner = require('./pythonRunner');
const clipboard = require('./clipboard');
const gitLog = require('./gitLog');

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

  ipcMain.handle('clipboard:copy', (_event, text) => clipboard.copy(text));

  ipcMain.handle('report:getTodayCommits', () => gitLog.getTodayCommits());
}

module.exports = registerIpcHandlers;
