# AI Digest Site

自動從 Discord 🪜-digest 頻道抓取 AI 摘要，生成卡片式網站，部署在 GitHub Pages。

## 結構

```
├── index.html          # 主頁面
├── css/style.css       # 莫蘭迪暖灰配色樣式
├── js/main.js          # 卡片渲染 + 搜尋 + 篩選
├── data/digests.json   # 摘要數據（自動更新）
├── images/             # 卡片縮圖
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
```

## 手動更新數據

```bash
export DISCORD_BOT_TOKEN="your_token"
export DISCORD_CHANNEL_ID="your_channel_id"
python3 scripts/fetch_digests.py
```

## 設定（首次部署）

1. Fork / Clone 到你的 GitHub
2. Settings → Pages → Source: GitHub Actions
3. Settings → Secrets → 新增兩個 secret：
   - `DISCORD_BOT_TOKEN` — Discord Bot 的 token
   - `DISCORD_CHANNEL_ID` — 要抓取的 Discord 頻道 ID
4. 自動部署 + 每 6 小時更新
