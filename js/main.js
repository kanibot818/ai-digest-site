// AI Digest Site - Main JS

let allDigests = [];
let activeCategory = '全部';
let searchTerm = '';
let sortMode = 'newest';

// === Load Data ===
async function loadData() {
  try {
    const res = await fetch('data/digests.json');
    allDigests = await res.json();
    initTabs();
    render();
  } catch (e) {
    document.getElementById('cardGrid').innerHTML = '<div class="empty">⚠️ 無法載入資料</div>';
    console.error(e);
  }
}

// === Category Tabs ===
function initTabs() {
  const categories = ['全部', ...new Set(allDigests.map(d => d.category))];
  const container = document.getElementById('categoryTabs');
  container.innerHTML = categories.map(cat =>
    `<button class="tab ${cat === activeCategory ? 'active' : ''}" onclick="setCategory('${cat}')">${cat}</button>`
  ).join('');
}

function setCategory(cat) {
  activeCategory = cat;
  initTabs();
  render();
}

// === Search ===
document.getElementById('searchInput').addEventListener('input', (e) => {
  searchTerm = e.target.value.toLowerCase();
  render();
});

// === Sort ===
document.getElementById('sortSelect').addEventListener('change', (e) => {
  sortMode = e.target.value;
  render();
});

// === Filter & Render ===
function getFiltered() {
  let items = [...allDigests];

  // Category filter
  if (activeCategory !== '全部') {
    items = items.filter(d => d.category === activeCategory);
  }

  // Search filter
  if (searchTerm) {
    items = items.filter(d => {
      const text = (d.title + ' ' + d.summary.join(' ') + ' ' + d.category).toLowerCase();
      return text.includes(searchTerm);
    });
  }

  // Sort
  items.sort((a, b) => {
    const da = new Date(a.date);
    const db = new Date(b.date);
    return sortMode === 'newest' ? db - da : da - db;
  });

  return items;
}

function render() {
  const items = getFiltered();
  const grid = document.getElementById('cardGrid');

  if (items.length === 0) {
    grid.innerHTML = '<div class="empty">沒有符合條件的內容</div>';
    return;
  }

  grid.innerHTML = items.map(d => `
    <article class="card">
      <div class="card-body">
        <span class="card-category">${d.category}</span>
        <h3 class="card-title">${d.title}</h3>
        <ul class="card-summary">
          ${d.summary.slice(0, 3).map(s => `<li>${s}</li>`).join('')}
        </ul>
      </div>
      <div class="card-footer">
        <span class="card-date">${d.date}</span>
        <div class="card-links">
          ${(d.links || []).map(l => `<a href="${l.url}" target="_blank" rel="noopener">${l.label}</a>`).join('')}
        </div>
      </div>
    </article>
  `).join('');
}

// === Init ===
loadData();
