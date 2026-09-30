const { shell } = require('electron');

// 파이썬 쪽에서 이미 사용자의 실제 다운로드 폴더에 파일을 저장해두므로,
// 여기서는 그 파일이 있는 폴더를 탐색기(Finder)로 열어 확인시켜주는
// 보조 동작만 한다 (실패해도 파일 자체는 이미 다운로드 폴더에 있다).
function revealFile(sourcePath) {
  shell.showItemInFolder(sourcePath);
  return { success: true };
}

// 매출전표 상세보기 같은 LMS 조회 전용 링크를 사용자의 기본 브라우저로 연다
// (일렉트론 창 안에서 직접 열면 로그인 세션이 없어 접근이 안 된다).
function openExternal(url) {
  if (typeof url !== 'string' || !/^https?:\/\//.test(url)) {
    return { success: false, error: '유효하지 않은 URL입니다.' };
  }
  shell.openExternal(url);
  return { success: true };
}

module.exports = { revealFile, openExternal };
