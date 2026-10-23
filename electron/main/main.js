const { app, BrowserWindow } = require('electron');
const { createMainWindow } = require('./windows');
const registerIpcHandlers = require('./ipc');
const pythonRunner = require('./ipc/pythonRunner');
const taskScheduler = require('./ipc/taskScheduler');

let mainWindow;

function bootstrap() {
  mainWindow = createMainWindow();
  registerIpcHandlers(mainWindow);
  taskScheduler.startScheduler();
}

app.whenReady().then(bootstrap);

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) bootstrap();
});

app.on('before-quit', () => {
  pythonRunner.killCurrent();
  taskScheduler.stopScheduler();
});
