const fs = require('fs');
const path = require('path');

// python worker가 크롤링 결과를 저장하는 위치와 반드시 일치해야 한다
// (python/worker/config.py의 DATA_DIR = 저장소 루트/data, office/crawler.py의
// data_dir()/reports_path() 참고 — python/data가 아니라 저장소 루트의 data/다).
const REPORTS_PATH = path.join(__dirname, '..', '..', '..', 'data', 'office', 'reports.json');

function getLatestReports() {
  try {
    const raw = fs.readFileSync(REPORTS_PATH, 'utf-8');
    return JSON.parse(raw);
  } catch (err) {
    return null;
  }
}

module.exports = { getLatestReports };
