# AI Digest Site

自動從 Discord 🪜-digest 頻道抓取 AI 摘要，生成卡片式網站，部署在 GitHub Pages。

## 結構

```
├── index.html          # 主頁面
├── css/style.css       # 暗色主題樣式
├── js/main.js          # 卡片渲染 + 搜尋 + 篩選
├── data/digests.json   # 摘要數據（自動更新）
├── scripts/
│   └── fetch_digests.py  # Discord → JSON 轉換腳本
└── .github/workflows/
    ├── deploy.yml          # Push → GitHub Pages
    └── update-digests.yml  # 每 6 小時自動抓新摘要
```

## 本地預覽

```bash
cd ai-digest-site
python3 -m http.server 8080
# 打開 http://localhost:8080
```

## 手動更新數據

```bash
DISCORD_BOT_TOKEN=your_token python3 scripts/fetch_digests.py
```

## 設定

1. Fork / Clone 到你的 GitHub
2. Settings → Pages → Source: GitHub Actions
3. Settings → Secrets → 新增 `DISCORD_BOT_TOKEN`
4. 自動部署 + 每 6 小時更新
