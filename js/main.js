// AI Digest — Card list + Detail view with hash routing
// Design: Notion-inspired warm minimalism
// v2: dual-source (digest + learning daily reports), month filter

let allDigests = [];
let activeCategory = '全部';
let activeSource = '全部';
let activeMonth = 'all';
let searchTerm = '';
let sortMode = 'newest';

const SOURCE_LABELS = {
  'digest': '每日精選',
  'learning': '學習日報',
};

// === Load ===
async function loadData() {
  try {
    const res = await fetch('data/digests.json');
    allDigests = await res.json();
    initSourceTabs();
    initTabs();
    initMonthSelect();
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

// === Source Tabs ===
function initSourceTabs() {
  const sources = ['全部', ...new Set(allDigests.map(d => d.source || 'digest'))];
  const el = document.getElementById('sourceTabs');
  el.innerHTML = sources.map(src => {
    const label = src === '全部' ? '全部' : (SOURCE_LABELS[src] || src);
    return `<button class="source-tab ${src === activeSource ? 'active' : ''}" data-src="${src}">${label}</button>`;
  }).join('');
  el.querySelectorAll('.source-tab').forEach(t => {
    t.addEventListener('click', () => {
      activeSource = t.dataset.src;
      initSourceTabs();
      initTabs();
      render();
    });
  });
}

// === Month Filter ===
function initMonthSelect() {
  const months = [...new Set(allDigests.map(d => d.date.slice(0, 7)))].sort().reverse();
  const el = document.getElementById('monthSelect');
  el.innerHTML = '<option value="all">全部月份</option>' +
    months.map(m => `<option value="${m}" ${m === activeMonth ? 'selected' : ''}>${m}</option>`).join('');
}
document.getElementById('monthSelect').addEventListener('change', e => {
  activeMonth = e.target.value;
  render();
});

// === Tabs ===
function initTabs() {
  let items = allDigests;
  if (activeSource !== '全部')
    items = items.filter(d => (d.source || 'digest') === activeSource);
  const categories = ['全部', ...new Set(items.map(d => d.category))];
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
  if (!categories.includes(activeCategory)) activeCategory = '全部';
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
  if (activeSource !== '全部')
    items = items.filter(d => (d.source || 'digest') === activeSource);
  if (activeCategory !== '全部')
    items = items.filter(d => d.category === activeCategory);
  if (activeMonth !== 'all')
    items = items.filter(d => d.date.slice(0, 7) === activeMonth);
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

  // Plan A (magazine layout): image is a clean 16:9 visual band, title lives
  // below it as standalone serif headline; category tag sits above the title.
  const heroHTML = d.image
    ? `<figure class="d-hero"><img src="${d.image}" alt="${d.title}"></figure>`
    : '';

  // Meta row: date · category · source domain · read time
  const readingTime = Math.max(1, Math.ceil(
    ((d.summary || []).join('') + (d.editor_note || '')).length / 400));
  const srcDomain = d.source_url ? getDomain(d.source_url) : '';
  const metaHTML = `
      <div class="d-meta">
        <span class="d-meta-item">${d.date}</span>
        <span class="d-meta-dot">·</span>
        <span class="d-meta-item">${d.category}</span>
        ${srcDomain ? `<span class="d-meta-dot">·</span>
          <span class="d-meta-item">${srcDomain}</span>` : ''}
        <span class="d-meta-item d-meta-right">約 ${readingTime} 分鐘</span>
      </div>

      <span class="d-cat-tag">${d.category}</span>
      <h1 class="d-headline">${d.title}</h1>`;

  // Summary: paragraph flow with hairline dividers (Plan A — no numbering)
  const summaryHTML = (d.summary || []).map(s => {
    // Split at first "—" or "：" to bold the lead phrase
    const parts = s.split(/(—|：)/);
    const lead = parts.length > 2 ? parts[0] : '';
    const rest = parts.length > 2 ? parts.slice(1).join('') : s;
    return `<p class="d-para">${lead ? `<strong>${lead}</strong>${rest}` : s}</p>`;
  }).join('');

  // Links: with domain + type icon; X cards with a resolved original article get it first
  let linkList = d.links || [];
  if (d.original_url) {
    linkList = [{ label: '原文出處', url: d.original_url },
                ...linkList.filter(l => l.url !== d.original_url)];
  }
  const allLinks = linkList.map(l => {
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
      ${metaHTML}

      <section class="d-section">
        <h2 class="d-section-title">摘要重點</h2>
        <div class="d-paras">${summaryHTML}</div>
      </section>

      ${d.editor_note ? `
      <aside class="d-editor-note">
        <span class="d-editor-note-label">編輯觀點</span>
        <p>${d.editor_note}</p>
      </aside>` : ''}

      ${allLinks ? `
      <section class="d-section">
        <h2 class="d-section-title">相關連結</h2>
        <div class="d-links">${allLinks}</div>
        ${d.original_url || d.source_url ? `
        <a href="${d.original_url || d.source_url}" target="_blank" rel="noopener" class="d-cta">
          前往原文 <span class="d-cta-arrow">→</span>
        </a>` : ''}
      </section>` : ''}

      <div class="d-actions">
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
