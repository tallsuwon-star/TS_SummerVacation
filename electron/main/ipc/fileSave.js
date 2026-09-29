const { dialog } = require('electron');
const fs = require('fs');
const path = require('path');

// job이 로컬(data/refund/output/ 등)에 만들어둔 파일을 사용자가 원하는
// 위치에 "다른 이름으로 저장"할 수 있게 네이티브 저장 대화상자를 띄운다.
async function saveFileAs(mainWindow, sourcePath, suggestedName) {
  const { canceled, filePath } = await dialog.showSaveDialog(mainWindow, {
    defaultPath: suggestedName || path.basename(sourcePath),
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

module.exports = { saveFileAs };
