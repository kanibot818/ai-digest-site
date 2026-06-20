// AI Digest Site — Card list + Detail view with hash routing

let allDigests = [];
let activeCategory = '全部';
let searchTerm = '';
let sortMode = 'newest';

// Category → icon + gradient for placeholder thumbnails
const CATEGORY_THEMES = {
  '開發工具':  { icon: '⚙', grad: ['#A89B86', '#8A7E6B'] },
  'AI 語音':   { icon: '🔊', grad: ['#B5A89A', '#9A8B73'] },
  'AI 圖像':   { icon: '🎨', grad: ['#C4B5A0', '#A89B86'] },
  'AI 影片':   { icon: '🎬', grad: ['#9A8B73', '#827565'] },
  '大模型':    { icon: '🧠', grad: ['#8A7E6B', '#6B6051'] },
  'AI 行銷':   { icon: '📈', grad: ['#B0A293', '#938574'] },
  '研究':      { icon: '🔬', grad: ['#A39585', '#857865'] },
  '其他':      { icon: '✨', grad: ['#BFB3A2', '#A39585'] },
};

function getCategoryTheme(cat) {
  return CATEGORY_THEMES[cat] || CATEGORY_THEMES['其他'];
}

// Generate inline SVG data URI for placeholder thumbnail
function placeholderThumb(title, category) {
  const theme = getCategoryTheme(category);
  const initials = title.replace(/^[—\-·•]+/, '').trim().slice(0, 2);
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="600" height="340" viewBox="0 0 600 340">
    <defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="${theme.grad[0]}"/>
      <stop offset="100%" stop-color="${theme.grad[1]}"/>
    </linearGradient></defs>
    <rect width="600" height="340" fill="url(#g)"/>
    <text x="300" y="140" text-anchor="middle" font-size="72" fill="rgba(255,255,255,0.3)">${theme.icon}</text>
    <text x="300" y="230" text-anchor="middle" font-size="42" font-weight="600" fill="rgba(255,255,255,0.85)" font-family="Noto Serif TC, serif">${initials}</text>
    <text x="300" y="290" text-anchor="middle" font-size="20" fill="rgba(255,255,255,0.5)" font-family="Inter, sans-serif">${category}</text>
  </svg>`;
  return 'data:image/svg+xml,' + encodeURIComponent(svg);
}

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
  // Default: card grid
  showGrid();
  render();
}

function navigateToDetail(id) {
  window.location.hash = `/digest/${id}`;
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
  window.scrollTo(0, 0);
}

function showDetail() {
  document.getElementById('toolbar').style.display = 'none';
  document.querySelector('.card-grid').style.display = 'none';
  document.getElementById('detailView').style.display = '';
  window.scrollTo(0, 0);
}

// === Render Card Grid ===
function render() {
  const items = getFiltered();
  const grid = document.getElementById('cardGrid');

  if (!items.length) {
    grid.innerHTML = '<div class="empty-state"><p>沒有符合條件的內容</p></div>';
    return;
  }

  grid.innerHTML = items.map(d => {
    const thumb = d.image ? d.image : placeholderThumb(d.title, d.category);
    return `
    <article class="card" onclick="navigateToDetail('${d.id}')">
      <div class="card-thumb-wrapper">
        <img class="card-image" src="${thumb}" alt="${d.title}" loading="lazy"
             onerror="this.src='${placeholderThumb(d.title, d.category)}'">
      </div>
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
          ${(d.summary || []).slice(0, 3).map(s => `<li>${s}</li>`).join('')}
        </ul>
      </div>
      <div class="card-footer">
        <span class="card-date">${d.date}</span>
        <span class="card-read-more">閱讀全文 →</span>
      </div>
    </article>`;
  }).join('');
}

// === Render Detail View ===
function renderDetail(d) {
  showDetail();

  const theme = getCategoryTheme(d.category);
  const thumb = d.image ? d.image : placeholderThumb(d.title, d.category);
  const allLinks = (d.links || []).map(l =>
    `<a href="${l.url}" target="_blank" rel="noopener" class="detail-link">
      <span class="detail-link-label">${l.label}</span>
      <span class="detail-link-arrow">↗</span>
    </a>`
  ).join('');

  document.getElementById('detailView').innerHTML = `
    <div class="detail-container">
      <button class="detail-back" onclick="backToGrid()">← 返回列表</button>

      <div class="detail-hero">
        <img class="detail-hero-image" src="${thumb}" alt="${d.title}"
             onerror="this.src='${placeholderThumb(d.title, d.category)}'">
        <div class="detail-hero-overlay"></div>
        <div class="detail-hero-text">
          <span class="card-tag">${d.category}</span>
          <h1 class="detail-title">${d.title}</h1>
          <span class="detail-date">${d.date}</span>
        </div>
      </div>

      ${d.editor_note ? `
      <div class="detail-editor">
        <div class="detail-editor-label">📝 編輯觀點</div>
        <p class="detail-editor-text">${d.editor_note}</p>
      </div>
      ` : ''}

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
      </div>
      ` : ''}

      ${d.source_url ? `
      <div class="detail-source-box">
        <a href="${d.source_url}" target="_blank" rel="noopener" class="detail-source-btn">
          ${d.source_label || '查看原文'} ↗
        </a>
      </div>
      ` : ''}

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
    btn.textContent = '✅ 已複製！';
    setTimeout(() => { btn.textContent = orig; }, 2000);
  });
}

// === Init ===
loadData();
