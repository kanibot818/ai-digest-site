// AI Digest — Card list + Detail view with hash routing
// Design: Notion-inspired warm minimalism

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
    handleRoute();
  } catch (e) {
    document.getElementById('cardGrid').innerHTML =
      '<div class="empty-state"><p>⚠️ 無法載入資料</p></div>';
    console.error(e);
  }
}

// === Hash Routing ===
window.addEventListener('hashchange', handleRoute);

function handleRoute() {
  const hash = window.location.hash;
  const match = hash.match(/^#\/digest\/(.+)$/);
  if (match) {
    const id = decodeURIComponent(match[1]);
    const digest = allDigests.find(d => d.id === id);
    if (digest) {
      renderDetail(digest);
      return;
    }
  }
  showGrid();
  render();
}

function navigateToDetail(id) {
  window.location.hash = '/digest/' + id;
}

function backToGrid() {
  window.location.hash = '';
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

// === View Toggle ===
function showGrid() {
  document.getElementById('toolbar').style.display = '';
  document.querySelector('.card-grid').style.display = '';
  document.getElementById('detailView').style.display = 'none';
}

function showDetail() {
  document.getElementById('toolbar').style.display = 'none';
  document.querySelector('.card-grid').style.display = 'none';
  document.getElementById('detailView').style.display = 'block';
  window.scrollTo(0, 0);
}

// === Card Cover HTML ===
function cardCover(d) {
  if (d.image) {
    return `<div class="card-cover"><img src="${d.image}" alt="${d.title}" loading="lazy"></div>`;
  }
  // Clean typographic cover — no gradients, no emoji, just text on warm background
  return `<div class="card-cover">
    <div class="card-cover-text">
      <div class="cover-cat">${d.category}</div>
      <div class="cover-title">${d.title}</div>
    </div>
  </div>`;
}

// === Render Card Grid ===
function render() {
  const items = getFiltered();
  const grid = document.getElementById('cardGrid');

  if (!items.length) {
    grid.innerHTML = '<div class="empty-state"><p>沒有符合條件的內容</p></div>';
    return;
  }

  grid.innerHTML = items.map(d => `
    <article class="card" data-id="${d.id}">
      ${cardCover(d)}
      <div class="card-body">
        <span class="card-tag">${d.category}</span>
        <h3 class="card-title">${d.title}</h3>
        ${d.editor_note ? `
        <div class="card-editor">
          <div class="card-editor-label">編輯觀點</div>
          <p class="card-editor-text">${d.editor_note}</p>
        </div>` : ''}
        <ul class="card-summary">
          ${(d.summary || []).slice(0, 3).map(s => `<li>${s}</li>`).join('')}
        </ul>
      </div>
      <div class="card-footer">
        <span class="card-date">${d.date}</span>
        <span class="card-read-more">閱讀 →</span>
      </div>
    </article>
  `).join('');

  grid.querySelectorAll('.card').forEach(card => {
    card.addEventListener('click', () => navigateToDetail(card.dataset.id));
  });
}

// === Render Detail ===
function renderDetail(d) {
  showDetail();

  const heroHTML = d.image
    ? `<div class="detail-hero"><img src="${d.image}" alt="${d.title}"></div>`
    : '';

  const allLinks = (d.links || []).map(l =>
    `<a href="${l.url}" target="_blank" rel="noopener" class="detail-link">
      <span class="detail-link-label">${l.label}</span>
      <span class="detail-link-arrow">↗</span>
    </a>`
  ).join('');

  document.getElementById('detailView').innerHTML = `
    <div class="detail-container">
      <button class="detail-back" onclick="backToGrid()">← 返回</button>

      ${heroHTML}

      <div class="detail-hero-text">
        <span class="card-tag">${d.category}</span>
        <h1 class="detail-hero-title">${d.title}</h1>
        <span class="detail-date">${d.date}</span>
      </div>

      ${d.editor_note ? `
      <div class="detail-editor">
        <div class="detail-editor-label">編輯觀點</div>
        <p class="detail-editor-text">${d.editor_note}</p>
      </div>` : ''}

      <div class="detail-section">
        <h2 class="detail-section-title">摘要重點</h2>
        <ul class="detail-summary">
          ${(d.summary || []).map(s => `<li>${s}</li>`).join('')}
        </ul>
      </div>

      ${allLinks ? `
      <div class="detail-section">
        <h2 class="detail-section-title">相關連結</h2>
        <div class="detail-links">${allLinks}</div>
      </div>` : ''}

      ${d.source_url ? `
      <div class="detail-source-box">
        <a href="${d.source_url}" target="_blank" rel="noopener" class="detail-source-btn">
          ${d.source_label || '查看原文'} ↗
        </a>
      </div>` : ''}

      <div class="detail-share">
        <button class="detail-share-btn" onclick="copyShareLink('${d.id}')">複製分享連結</button>
      </div>
    </div>
  `;
}

function copyShareLink(id) {
  const url = window.location.origin + window.location.pathname + '#/digest/' + id;
  navigator.clipboard.writeText(url).then(() => {
    const btn = document.querySelector('.detail-share-btn');
    const orig = btn.textContent;
    btn.textContent = '✅ 已複製';
    setTimeout(() => { btn.textContent = orig; }, 2000);
  });
}

// === Init ===
loadData();
