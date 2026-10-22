function renderIdeaWarehouseView(container) {
  container.innerHTML = `
    <div class="view-header">
      <h1>이성규의 아이디어 창고</h1>
    </div>

    <section class="panel">
      <div class="field-label">
        생각날 때마다 아이디어를 적어두면 카테고리별로 묶어서 보여줍니다.
        옵시디언처럼 이 레포(<code>ideas/</code> 폴더)에 마크다운 파일로
        그대로 저장되니, 깃에 커밋/푸시하면 깃허브에서도 history로 남습니다.
      </div>

      <div class="checkbox-row">
        <label for="idea-title-input">제목</label>
        <input type="text" id="idea-title-input" placeholder="예: 보카킹 보고 자동화 개선안" />
      </div>
      <div class="checkbox-row">
        <label for="idea-category-input">카테고리</label>
        <input type="text" id="idea-category-input" list="idea-category-options" placeholder="예: 수업운영, 마케팅, 자동화..." />
        <datalist id="idea-category-options"></datalist>
      </div>
      <div class="checkbox-row">
        <label for="idea-tags-input">태그 (쉼표로 구분, 생략 가능)</label>
        <input type="text" id="idea-tags-input" placeholder="예: 보카킹, 자동화" />
      </div>
      <div class="field" style="margin-bottom: 10px;">
        <label class="field-label" for="idea-body-input">내용</label>
        <textarea id="idea-body-input" rows="5" style="width: 100%;" placeholder="떠오른 생각을 자유롭게 적어주세요."></textarea>
      </div>
      <div class="job-controls">
        <button id="idea-add-btn" class="btn btn-primary">아이디어 추가</button>
      </div>
    </section>

    <section class="panel">
      <div class="field-label">
        카테고리별 아이디어 개수가
        <input type="number" id="idea-threshold-input" min="1" style="width: 50px; display: inline-block;" />
        개 미만이면 "아이디어 필요"로 표시합니다.
      </div>
      <div class="log-toolbar">
        <input type="text" id="idea-search" class="roster-search-input" placeholder="제목/내용/카테고리/태그 검색..." />
        <span id="idea-search-count" class="tutor-roster-count"></span>
      </div>
      <div id="idea-groups"></div>
    </section>
  `;

  const titleInput = container.querySelector('#idea-title-input');
  const categoryInput = container.querySelector('#idea-category-input');
  const categoryOptions = container.querySelector('#idea-category-options');
  const tagsInput = container.querySelector('#idea-tags-input');
  const bodyInput = container.querySelector('#idea-body-input');
  const addBtn = container.querySelector('#idea-add-btn');
  const thresholdInput = container.querySelector('#idea-threshold-input');
  const searchInput = container.querySelector('#idea-search');
  const searchCount = container.querySelector('#idea-search-count');
  const groupsEl = container.querySelector('#idea-groups');

  let ideas = [];
  let threshold = 3;
  let searchQuery = '';

  function escapeHtml(text) {
    if (!text) return '';
    return String(text)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function formatDate(iso) {
    if (!iso) return '';
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return iso;
    const pad = (n) => String(n).padStart(2, '0');
    return `${d.getFullYear()}.${pad(d.getMonth() + 1)}.${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
  }

  function updateCategoryOptions() {
    const categories = [...new Set(ideas.map((i) => i.category).filter(Boolean))].sort();
    categoryOptions.innerHTML = categories.map((c) => `<option value="${escapeHtml(c)}"></option>`).join('');
  }

  function matchesSearch(idea) {
    if (!searchQuery) return true;
    const haystack = `${idea.title} ${idea.body} ${idea.category} ${(idea.tags || []).join(' ')}`.toLowerCase();
    return haystack.includes(searchQuery);
  }

  function renderGroups() {
    const filtered = ideas.filter(matchesSearch);

    if (ideas.length === 0) {
      groupsEl.innerHTML = '<div class="empty">아직 등록된 아이디어가 없습니다.</div>';
      searchCount.textContent = '';
      return;
    }
    if (filtered.length === 0) {
      groupsEl.innerHTML = '<div class="empty">검색 결과가 없습니다.</div>';
      searchCount.textContent = `0 / ${ideas.length}건 일치`;
      return;
    }

    // 전체 아이디어 개수 기준으로 "아이디어 필요" 여부를 판단한다 (검색으로
    // 걸러진 개수가 아니라 — 검색 중에도 카테고리 상태가 바뀌어 보이면 혼란스럽다).
    const countByCategory = {};
    ideas.forEach((i) => {
      countByCategory[i.category] = (countByCategory[i.category] || 0) + 1;
    });

    const grouped = {};
    filtered.forEach((idea) => {
      if (!grouped[idea.category]) grouped[idea.category] = [];
      grouped[idea.category].push(idea);
    });

    const categories = Object.keys(grouped).sort((a, b) => a.localeCompare(b, 'ko'));

    groupsEl.innerHTML = categories
      .map((category) => {
        const items = grouped[category];
        const total = countByCategory[category] || items.length;
        const needsMore = total < threshold;
        const badge = needsMore
          ? ` <span class="status-badge status-failed">아이디어 필요 (${total}/${threshold})</span>`
          : ` <span class="status-badge status-success">${total}개</span>`;

        const itemsHtml = items
          .map((idea) => {
            const tagsHtml = (idea.tags || []).length
              ? `<div class="field-label">태그: ${idea.tags.map(escapeHtml).join(', ')}</div>`
              : '';
            return `
              <div class="idea-card" data-id="${escapeHtml(idea.id)}">
                <div class="idea-card-header">
                  <strong>${escapeHtml(idea.title) || '(제목 없음)'}</strong>
                  <span class="field-label">${formatDate(idea.createdAt)}</span>
                  <button type="button" class="btn btn-ghost idea-delete-btn" data-id="${escapeHtml(idea.id)}">삭제</button>
                </div>
                <div class="idea-card-body">${escapeHtml(idea.body).replace(/\n/g, '<br>')}</div>
                ${tagsHtml}
              </div>
            `;
          })
          .join('');

        return `
          <section class="panel">
            <div class="field-label"><strong>${escapeHtml(category)}</strong>${badge}</div>
            ${itemsHtml}
          </section>
        `;
      })
      .join('');

    if (searchQuery) {
      searchCount.textContent = `${filtered.length} / ${ideas.length}건 일치`;
    } else {
      searchCount.textContent = `총 ${ideas.length}건`;
    }

    groupsEl.querySelectorAll('.idea-delete-btn').forEach((btn) => {
      btn.addEventListener('click', async () => {
        if (!confirm('이 아이디어를 삭제할까요? (ideas/ 폴더의 파일이 지워집니다)')) return;
        const result = await window.api.deleteIdea(btn.dataset.id);
        if (!result.success) {
          alert(result.error || '삭제하지 못했습니다.');
          return;
        }
        await loadIdeas();
      });
    });
  }

  searchInput.addEventListener('input', () => {
    searchQuery = searchInput.value.trim().toLowerCase();
    renderGroups();
  });

  thresholdInput.addEventListener('change', async () => {
    const value = Math.max(1, parseInt(thresholdInput.value, 10) || 1);
    threshold = value;
    thresholdInput.value = value;
    await window.api.setSettings({ ideaWarehouseThreshold: value });
    renderGroups();
  });

  addBtn.addEventListener('click', async () => {
    const title = titleInput.value.trim();
    const category = categoryInput.value.trim();
    const body = bodyInput.value.trim();

    if (!category) {
      alert('카테고리를 입력해주세요. 비슷한 아이디어끼리 묶는 기준이 됩니다.');
      return;
    }
    if (!title && !body) {
      alert('제목이나 내용 중 하나는 입력해주세요.');
      return;
    }

    const tags = tagsInput.value
      .split(',')
      .map((t) => t.trim())
      .filter(Boolean);

    await window.api.createIdea({ title, category, tags, body });

    titleInput.value = '';
    tagsInput.value = '';
    bodyInput.value = '';
    // 카테고리는 같은 주제로 연달아 적는 경우가 많아 일부러 지우지 않는다.

    await loadIdeas();
  });

  async function loadIdeas() {
    ideas = await window.api.listIdeas();
    updateCategoryOptions();
    renderGroups();
  }

  (async () => {
    const settings = await window.api.getSettings();
    threshold = settings.ideaWarehouseThreshold || 3;
    thresholdInput.value = threshold;
    await loadIdeas();
  })();
}

window.renderIdeaWarehouseView = renderIdeaWarehouseView;
