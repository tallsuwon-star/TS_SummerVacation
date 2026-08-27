// 강사별 처리 현황 표를 그리고, 완료 후 요약 텍스트/실패 목록을 만들어 주는 헬퍼.
function createDashboard(container) {
  const state = new Map(); // tutorName -> { status, found, reason }

  const STATUS_LABEL = {
    pending: '대기중',
    processing: '처리중',
    success: '완료',
    failed: '실패',
  };

  const STATUS_CLASS = {
    대기중: 'pending',
    처리중: 'processing',
    완료: 'success',
    실패: 'failed',
  };

  function reset(tutorNames) {
    state.clear();
    tutorNames.forEach((name) => state.set(name, { status: '대기중', found: null, reason: null }));
    render();
  }

  function setStatus(tutor, status, found, reason) {
    const prev = state.get(tutor) || {};
    state.set(tutor, {
      status: STATUS_LABEL[status] || status,
      found: found ?? prev.found ?? null,
      reason: reason ?? prev.reason ?? null,
    });
    render();
  }

  function render() {
    const rows = Array.from(state.entries())
      .map(([tutor, info]) => {
        const rowClass = info.status === '실패' ? 'row-failed' : '';
        const statusClass = STATUS_CLASS[info.status] || 'pending';
        return `
          <tr class="${rowClass}">
            <td>${escapeHtml(tutor)}</td>
            <td><span class="status-badge status-${statusClass}">${info.status}</span></td>
            <td>${info.found ?? '-'}</td>
          </tr>
        `;
      })
      .join('');

    container.innerHTML = `
      <table class="dashboard-table">
        <thead>
          <tr><th>강사명</th><th>상태</th><th>발견된 보강권 건수</th></tr>
        </thead>
        <tbody>
          ${rows || '<tr><td colspan="3" class="empty">대상 강사를 입력하고 시작 버튼을 눌러주세요.</td></tr>'}
        </tbody>
      </table>
    `;
  }

  function getFailedList() {
    return Array.from(state.entries())
      .filter(([, info]) => info.status === '실패')
      .map(([tutor, info]) => ({ tutor, reason: info.reason }));
  }

  function getSummaryText() {
    const lines = ['[오전특강 통계 결과]'];
    state.forEach((info, tutor) => {
      const foundText = info.found != null ? ` (${info.found}건)` : '';
      lines.push(`${tutor}: ${info.status}${foundText}`);
    });

    const failed = getFailedList();
    if (failed.length > 0) {
      lines.push('', '[실패 목록]');
      failed.forEach(({ tutor, reason }) => lines.push(`${tutor}: ${reason ?? '사유 미상'}`));
    }

    return lines.join('\n');
  }

  function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  render();

  return { reset, setStatus, getFailedList, getSummaryText };
}

window.createDashboard = createDashboard;
