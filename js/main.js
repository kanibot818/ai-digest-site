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
      '<div class="empty-state"><p>無法載入資料</p></div>';
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

// === Helper: extract domain from URL ===
function getDomain(url) {
  try {
    const u = new URL(url);
    return u.hostname.replace('www.', '');
  } catch { return ''; }
}

function linkIcon(url) {
  if (/github\.com/.test(url)) return '⌥';
  if (/x\.com|twitter\.com/.test(url)) return '𝕏';
  if (/huggingface\.co/.test(url)) return 'HF';
  if (/docs\.|documentation/.test(url)) return '☰';
  return '↗';
}

// === Render Detail ===
function renderDetail(d) {
  showDetail();

  // Hero: image with overlay, or clean typographic header
  const heroHTML = d.image
    ? `<div class="d-hero d-hero-img">
        <img src="${d.image}" alt="${d.title}">
        <div class="d-hero-overlay"></div>
        <div class="d-hero-content">
          <span class="d-hero-tag">${d.category}</span>
          <h1 class="d-hero-title">${d.title}</h1>
        </div>
      </div>`
    : `<div class="d-hero d-hero-text">
        <span class="d-hero-tag">${d.category}</span>
        <h1 class="d-hero-title">${d.title}</h1>
      </div>`;

  // Summary: numbered points with bold lead
  const summaryHTML = (d.summary || []).map((s, i) => {
    // Split at first "—" or "：" to bold the lead phrase
    const parts = s.split(/(—|：)/);
    const lead = parts.length > 2 ? parts[0] : '';
    const rest = parts.length > 2 ? parts.slice(1).join('') : s;
    return `
      <div class="d-point">
        <span class="d-point-num">${String(i + 1).padStart(2, '0')}</span>
        <div class="d-point-text">
          ${lead ? `<strong>${lead}</strong>${rest}` : s}
        </div>
      </div>`;
  }).join('');

  // Links: with domain + type icon
  const allLinks = (d.links || []).map(l => {
    const domain = getDomain(l.url);
    const icon = linkIcon(l.url);
    return `
      <a href="${l.url}" target="_blank" rel="noopener" class="d-link">
        <span class="d-link-icon">${icon}</span>
        <span class="d-link-body">
          <span class="d-link-label">${l.label}</span>
          <span class="d-link-domain">${domain}</span>
        </span>
        <span class="d-link-go">↗</span>
      </a>`;
  }).join('');

  document.getElementById('detailView').innerHTML = `
    <div class="d-container">
      <button class="d-back" onclick="backToGrid()">← 返回列表</button>

      ${heroHTML}

      <div class="d-meta">
        <span class="d-meta-item">${d.date}</span>
        ${d.source_url ? `<span class="d-meta-dot">·</span>
          <span class="d-meta-item">來源：${d.source_label || getDomain(d.source_url)}</span>` : ''}
      </div>

      ${d.editor_note ? `
      <blockquote class="d-pullquote">
        <p>${d.editor_note}</p>
        <cite>編輯觀點</cite>
      </blockquote>` : ''}

      <section class="d-section">
        <h2 class="d-section-title">摘要重點</h2>
        <div class="d-points">${summaryHTML}</div>
      </section>

      ${allLinks ? `
      <section class="d-section">
        <h2 class="d-section-title">相關連結</h2>
        <div class="d-links">${allLinks}</div>
      </section>` : ''}

      <div class="d-actions">
        ${d.source_url ? `
        <a href="${d.source_url}" target="_blank" rel="noopener" class="d-btn-primary">
          查看原文 ↗
        </a>` : ''}
        <button class="d-btn-ghost" onclick="copyShareLink('${d.id}')">複製分享連結</button>
      </div>
    </div>
  `;
}

function copyShareLink(id) {
  const url = window.location.origin + window.location.pathname + '#/digest/' + id;
  navigator.clipboard.writeText(url).then(() => {
    const btn = document.querySelector('.detail-share-btn');
    const orig = btn.textContent;
    btn.textContent = '已複製';
    setTimeout(() => { btn.textContent = orig; }, 2000);
  });
}

// === Init ===
loadData();
