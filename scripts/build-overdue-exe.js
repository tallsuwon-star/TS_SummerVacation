// 동료 배포용 '미납자 관리' 전용 exe를 만드는 스크립트.
//
// 사전 준비 (반드시 먼저 실행):
//   cd python
//   pip install -r requirements.txt -r requirements-build.txt
//   pyinstaller worker.spec
//   -> python/dist/worker/worker.exe 가 생겨야 함
//
// 그 다음 저장소 루트에서:
//   npm install
//   npm run build:overdue-exe
//
// 결과물은 release/ 폴더에 생성된다 (portable .exe 하나).
//
// variant.js의 APP_VARIANT를 빌드 직전에 'overdue_only'로 바꿔서 electron-builder를
// 돌리고, 끝나면(성공/실패 상관없이) 다시 'full'로 되돌린다. 이렇게 하지 않으면
// 다음에 npm start로 개발할 때도 계속 미납자 관리만 보이게 된다.

const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');

const ROOT_DIR = path.join(__dirname, '..');
const VARIANT_PATH = path.join(ROOT_DIR, 'electron', 'main', 'variant.js');
const BUNDLED_EXE_PATH = path.join(ROOT_DIR, 'python', 'dist', 'worker', 'worker.exe');

function readVariantFile() {
  return fs.readFileSync(VARIANT_PATH, 'utf-8');
}

function writeVariant(content) {
  fs.writeFileSync(VARIANT_PATH, content, 'utf-8');
}

function setVariant(originalContent, variantName) {
  const updated = originalContent.replace(
    /APP_VARIANT:\s*'[^']*'/,
    `APP_VARIANT: '${variantName}'`
  );
  writeVariant(updated);
}

function main() {
  if (!fs.existsSync(BUNDLED_EXE_PATH)) {
    console.error(
      `[build-overdue-exe] python/dist/worker/worker.exe 를 찾을 수 없습니다.\n` +
        `먼저 python/ 폴더에서 다음을 실행하세요:\n` +
        `  pip install -r requirements.txt -r requirements-build.txt\n` +
        `  pyinstaller worker.spec\n`
    );
    process.exit(1);
  }

  const originalVariantContent = readVariantFile();

  try {
    console.log("[build-overdue-exe] variant.js -> 'overdue_only' 로 임시 변경");
    setVariant(originalVariantContent, 'overdue_only');

    console.log('[build-overdue-exe] electron-builder 실행 중...');
    execFileSync('npx', ['electron-builder', '--win', '--config.win.target=portable'], {
      cwd: ROOT_DIR,
      stdio: 'inherit',
      shell: process.platform === 'win32',
    });

    console.log('[build-overdue-exe] 완료. release/ 폴더를 확인하세요.');
  } finally {
    console.log("[build-overdue-exe] variant.js -> 'full' 로 복원");
    writeVariant(originalVariantContent);
  }
}

main();
