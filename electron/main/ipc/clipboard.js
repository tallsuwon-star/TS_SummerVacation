const { spawn } = require('child_process');
const path = require('path');

const PYTHON_BIN = process.platform === 'win32' ? 'python' : 'python3';
const CLIPBOARD_SCRIPT = path.join(__dirname, '..', '..', '..', 'python', 'worker', 'utils', 'clipboard.py');

// 클립보드 복사는 pyperclip(Python)을 통해 처리한다 (기술 스택 지정 사항).
function copy(text) {
  return new Promise((resolve) => {
    const proc = spawn(PYTHON_BIN, [CLIPBOARD_SCRIPT]);

    proc.stdin.write(text);
    proc.stdin.end();

    proc.on('close', (code) => resolve({ success: code === 0 }));
    proc.on('error', () => resolve({ success: false }));
  });
}

module.exports = { copy };
