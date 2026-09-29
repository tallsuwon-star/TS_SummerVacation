const { app, dialog, shell } = require('electron');
const fs = require('fs');
const path = require('path');

// job이 로컬(data/refund/output/ 등)에 만들어둔 파일을 사용자가 원하는
// 위치에 "다른 이름으로 저장"할 수 있게 네이티브 저장 대화상자를 띄운다.
//
// defaultPath에 파일명만 넘기면(예: "지출결의서_20260929.xlsx") 운영체제가
// 어느 폴더를 기본으로 열지 예측하기 어렵고, 창이 포커스를 못 받으면 대화상자가
// 다른 창 뒤에 숨어 사용자 눈에 안 띌 수 있다 — 그래서 항상 다운로드 폴더를
// 기본 경로로 명시하고, 대화상자를 띄우기 전에 메인 창을 앞으로 가져온다.
async function saveFileAs(mainWindow, sourcePath, suggestedName) {
  const fileName = suggestedName || path.basename(sourcePath);
  const defaultPath = path.join(app.getPath('downloads'), fileName);

  if (mainWindow) {
    mainWindow.show();
    mainWindow.focus();
  }

  const { canceled, filePath } = await dialog.showSaveDialog(mainWindow, {
    title: '지출결의서 저장',
    defaultPath,
    filters: [{ name: 'Excel 파일', extensions: ['xlsx'] }],
  });

  if (canceled || !filePath) {
    return { success: false, canceled: true };
  }

  try {
    fs.copyFileSync(sourcePath, filePath);
    return { success: true, savedPath: filePath };
  } catch (err) {
    return { success: false, error: err.message || String(err) };
  }
}

// 저장 대화상자를 놓쳤거나 못 봤을 때를 대비해, 생성된 파일이 실제로 있는
// 폴더를 탐색기(Finder)로 열어 파일을 선택된 상태로 보여준다. 창 포커스와
// 무관하게 항상 눈에 보이는 OS 동작이라 더 확실하다.
function revealFile(sourcePath) {
  shell.showItemInFolder(sourcePath);
  return { success: true };
}

module.exports = { saveFileAs, revealFile };
