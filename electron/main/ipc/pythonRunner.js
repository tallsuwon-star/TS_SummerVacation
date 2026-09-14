const { app } = require('electron');
const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');
const readline = require('readline');
const store = require('../store');

const PYTHON_BIN = process.platform === 'win32' ? 'python' : 'python3';
const PYTHON_DIR = path.join(__dirname, '..', '..', '..', 'python');

// worker 패키지 내부에서 상대 임포트(from .. import config 등)를 쓰기 때문에
// 반드시 `-m worker.main` 형태로, cwd를 python/ 로 두고 모듈로 실행해야 한다.
const WORKER_MODULE = 'worker.main';

// 배포용 exe는 PyInstaller로 미리 묶어둔 worker.exe를 extraResources로 함께
// 패키징한다 (scripts/build-overdue-exe.js + package.json의 build.extraResources
// 참고). 그 파일이 실제로 존재하면(=패키징된 배포판) Python 설치 없이 이 exe를
// 바로 실행하고, 없으면(개발 중) 기존처럼 시스템 python으로 모듈 실행한다.
function resolveWorkerCommand(jobId) {
  const bundledExePath = path.join(process.resourcesPath || '', 'worker', 'worker.exe');

  if (app.isPackaged && fs.existsSync(bundledExePath)) {
    return {
      command: bundledExePath,
      args: ['--job', jobId],
      cwd: path.dirname(bundledExePath),
    };
  }

  return {
    command: PYTHON_BIN,
    args: ['-m', WORKER_MODULE, '--job', jobId],
    cwd: PYTHON_DIR,
  };
}

// Windows에서 Python이 콘솔 기본 인코딩(cp949 등)으로 stdout/stdin을 열어 한글 로그가
// 깨지는(mojibake) 것을 막기 위해 UTF-8을 강제한다. worker/main.py에서도 동일하게 처리하지만,
// 여기서도 걸어두면 인터프리터 시작 시점부터 확실히 UTF-8로 열린다.
//
// LMS 로그인 정보는 개발 중엔 .env 파일로도 들어오지만, 배포용 exe에는 .env가
// 없으므로 설정 화면(store의 lmsCredentials)에 입력된 값을 매번 최신 상태로
// 읽어와 프로세스 환경변수로 얹어준다 (값이 비어있으면 기존 .env 값을 그대로 둠).
function buildWorkerEnv() {
  const env = { ...process.env, PYTHONIOENCODING: 'utf-8', PYTHONUTF8: '1' };
  const creds = store.get('lmsCredentials') || {};

  if (creds.id) env.LMS_ID = creds.id;
  if (creds.password) env.LMS_PASSWORD = creds.password;
  if (creds.baseUrl) env.LMS_BASE_URL = creds.baseUrl;

  return env;
}

let currentProcess = null;

function start(payload, mainWindow) {
  return new Promise((resolve) => {
    if (currentProcess) {
      resolve({ started: false, reason: 'already-running' });
      return;
    }

    const { command, args, cwd } = resolveWorkerCommand(payload.jobId);
    const child = spawn(command, args, {
      cwd,
      stdio: ['pipe', 'pipe', 'pipe'],
      env: buildWorkerEnv(),
    });
    currentProcess = child;

    // spawn 자체가 실패하면(예: command를 찾을 수 없음) 'error' 이벤트가 발생한다.
    // 리스너가 없으면 Node가 처리되지 않은 예외로 던져서 Electron 프로세스 전체가 죽으므로 반드시 처리해야 한다.
    child.on('error', (err) => {
      mainWindow?.webContents.send('job:log', {
        type: 'log',
        level: 'error',
        message: `작업 프로세스를 실행할 수 없습니다 ("${command}" 명령을 찾을 수 없거나 실행 권한이 없습니다): ${err.message}`,
      });
      mainWindow?.webContents.send('job:done', { type: 'done', code: -1 });
      if (currentProcess === child) currentProcess = null;
    });

    // 첫 줄로 작업 설정(JSON)을 전달, 이후 stdin은 pause/resume/stop 제어용
    child.stdin.write(`${JSON.stringify(payload)}\n`);

    const rl = readline.createInterface({ input: child.stdout });
    rl.on('line', (line) => {
      if (!line.trim()) return;
      try {
        const data = JSON.parse(line);
        if (data.type === 'progress') {
          mainWindow?.webContents.send('job:progress', data);
        } else if (data.type === 'record') {
          mainWindow?.webContents.send('job:record', data);
        } else if (data.type === 'done') {
          mainWindow?.webContents.send('job:done', data);
        } else {
          mainWindow?.webContents.send('job:log', data);
        }
      } catch (err) {
        mainWindow?.webContents.send('job:log', { type: 'log', level: 'raw', message: line });
      }
    });

    child.stderr.on('data', (chunk) => {
      mainWindow?.webContents.send('job:log', { type: 'log', level: 'error', message: chunk.toString() });
    });

    child.on('close', (code) => {
      mainWindow?.webContents.send('job:done', { type: 'done', code });
      if (currentProcess === child) currentProcess = null;
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
