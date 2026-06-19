// AI Digest Site — Editorial card rendering

let allDigests = [];
let activeCategory = '全部';
let searchTerm = '';
let sortMode = 'newest';

// === Load ===
async function loadData() {
  try {
    const res = await fetch('data/digests.json');
    allDigests = await res.json();
    initTabs();
    render();
  } catch (e) {
    document.getElementById('cardGrid').innerHTML =
      '<div class="empty-state"><p>⚠️ 無法載入資料</p></div>';
    console.error(e);
  }
}

// === Tabs ===
function initTabs() {
  const categories = ['全部', ...new Set(allDigests.map(d => d.category))];
  document.getElementById('categoryTabs').innerHTML = categories.map(cat =>
    `<button class="tab ${cat === activeCategory ? 'active' : ''}" data-cat="${cat}">${cat}</button>`
  ).join('');

  document.querySelectorAll('.tab').forEach(t => {
    t.addEventListener('click', () => {
      activeCategory = t.dataset.cat;
      initTabs();
      render();
    });
  });
}

// === Search & Sort ===
document.getElementById('searchInput').addEventListener('input', e => {
  searchTerm = e.target.value.toLowerCase();
  render();
});
document.getElementById('sortSelect').addEventListener('change', e => {
  sortMode = e.target.value;
  render();
});

// === Filter ===
function getFiltered() {
  let items = [...allDigests];

  if (activeCategory !== '全部')
    items = items.filter(d => d.category === activeCategory);

  if (searchTerm) {
    items = items.filter(d => {
      const text = (d.title + ' ' + (d.editor_note || '') + ' ' + (d.summary || []).join(' ') + ' ' + d.category).toLowerCase();
      return text.includes(searchTerm);
    });
  }

  items.sort((a, b) => {
    const cmp = new Date(b.date) - new Date(a.date);
    return sortMode === 'newest' ? cmp : -cmp;
  });

  return items;
}

// === Render ===
function render() {
  const items = getFiltered();
  const grid = document.getElementById('cardGrid');

  if (!items.length) {
    grid.innerHTML = '<div class="empty-state"><p>沒有符合條件的內容</p></div>';
    return;
  }

  grid.innerHTML = items.map(d => `
    <article class="card">
      <div class="card-body">
        <span class="card-tag">${d.category}</span>
        <h3 class="card-title">${d.title}</h3>

        ${d.editor_note ? `
        <div class="card-editor">
          <div class="card-editor-label">編輯觀點</div>
          <p class="card-editor-text">${d.editor_note}</p>
        </div>
        ` : ''}

        <ul class="card-summary">
          ${(d.summary || []).slice(0, 4).map(s => `<li>${s}</li>`).join('')}
        </ul>
      </div>

      <div class="card-footer">
        <span class="card-date">${d.date}</span>
        ${d.source_url ? `<a class="card-source" href="${d.source_url}" target="_blank" rel="noopener">${d.source_label || '查看原文'} ↗</a>` : ''}
      </div>
    </article>
  `).join('');
}

// === Init ===
loadData();
