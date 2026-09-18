const { execFile } = require('child_process');
const path = require('path');

// 업무보고 화면의 "오늘 커밋 내역 불러오기"용. 이 저장소(TS_SummerVacation) 자체의
// 오늘자 커밋 메시지 제목줄만 모아서 돌려준다. 패키징된 배포용 exe(미납자 관리
// 전용)에는 이 작업 자체가 노출되지 않으므로(sidebar.js가 job 목록을 필터링),
// 여기서는 개발 중 소스 저장소 경로(__dirname 기준)가 항상 유효하다고 가정한다.
const REPO_DIR = path.join(__dirname, '..', '..', '..');

function getTodayCommits() {
  return new Promise((resolve) => {
    execFile(
      'git',
      ['log', '--since=midnight', '--pretty=format:%s', '--no-merges'],
      { cwd: REPO_DIR },
      (err, stdout) => {
        if (err) {
          resolve({ success: false, commits: [], error: err.message });
          return;
        }
        const commits = stdout
          .split('\n')
          .map((line) => line.trim())
          .filter(Boolean);
        resolve({ success: true, commits });
      },
    );
  });
}

module.exports = { getTodayCommits };
