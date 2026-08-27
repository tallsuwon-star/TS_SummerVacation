const { spawn } = require('child_process');
const path = require('path');
const readline = require('readline');

const PYTHON_BIN = process.platform === 'win32' ? 'python' : 'python3';
const PYTHON_DIR = path.join(__dirname, '..', '..', '..', 'python');

// worker 패키지 내부에서 상대 임포트(from .. import config 등)를 쓰기 때문에
// 반드시 `-m worker.main` 형태로, cwd를 python/ 로 두고 모듈로 실행해야 한다.
const WORKER_MODULE = 'worker.main';

let currentProcess = null;

function start(payload, mainWindow) {
  return new Promise((resolve) => {
    if (currentProcess) {
      resolve({ started: false, reason: 'already-running' });
      return;
    }

    const args = ['-m', WORKER_MODULE, '--job', payload.jobId];
    currentProcess = spawn(PYTHON_BIN, args, {
      cwd: PYTHON_DIR,
      stdio: ['pipe', 'pipe', 'pipe'],
    });

    // 첫 줄로 작업 설정(JSON)을 전달, 이후 stdin은 pause/resume/stop 제어용
    currentProcess.stdin.write(`${JSON.stringify(payload)}\n`);

    const rl = readline.createInterface({ input: currentProcess.stdout });
    rl.on('line', (line) => {
      if (!line.trim()) return;
      try {
        const data = JSON.parse(line);
        if (data.type === 'progress') {
          mainWindow?.webContents.send('job:progress', data);
        } else if (data.type === 'done') {
          mainWindow?.webContents.send('job:done', data);
        } else {
          mainWindow?.webContents.send('job:log', data);
        }
      } catch (err) {
        mainWindow?.webContents.send('job:log', { type: 'log', level: 'raw', message: line });
      }
    });

    currentProcess.stderr.on('data', (chunk) => {
      mainWindow?.webContents.send('job:log', { type: 'log', level: 'error', message: chunk.toString() });
    });

    currentProcess.on('close', (code) => {
      mainWindow?.webContents.send('job:done', { type: 'done', code });
      currentProcess = null;
    });

    resolve({ started: true });
  });
}

function sendControl(action) {
  if (!currentProcess) return { ok: false };
  currentProcess.stdin.write(`${JSON.stringify({ type: 'control', action })}\n`);
  return { ok: true };
}

function pause() {
  return sendControl('pause');
}

function resume() {
  return sendControl('resume');
}

function stop() {
  // TODO: 지정 시간 내에 정상 종료되지 않으면 currentProcess.kill()로 강제 종료하는
  // 타임아웃 로직 추가 (지금은 python worker가 stop 신호를 보고 스스로 종료하는 것에 의존)
  return sendControl('stop');
}

function killCurrent() {
  if (currentProcess) {
    currentProcess.kill();
    currentProcess = null;
  }
}

module.exports = { start, pause, resume, stop, killCurrent };
