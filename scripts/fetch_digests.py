#!/usr/bin/env python3
"""
Fetch digests from Discord 🪜-digest channel, generate AI editorial notes,
fetch OG images, and output digests.json.

Usage:
  python3 scripts/fetch_digests.py [--channel CHANNEL_ID] [--limit 100]

Required environment variables:
  DISCORD_BOT_TOKEN   — Discord bot token
  DISCORD_CHANNEL_ID  — Discord channel to fetch from
  GLM_API_KEY         — z.ai GLM API key for editorial note generation
"""

import json
import os
import re
import sys
import argparse
import hashlib
import urllib.request
import urllib.error
from datetime import datetime, timezone

# Discord channel ID — read from env, not hardcoded
DEFAULT_CHANNEL = os.environ.get("DISCORD_CHANNEL_ID", "")

# LLM config
LLM_BASE_URL = "https://api.z.ai/api/coding/paas/v4/chat/completions"
LLM_MODEL = "glm-4.6"


# ============================================================
# DISCORD API
# ============================================================

def fetch_messages(channel_id, token, limit=100):
    """Fetch messages from Discord channel via REST API."""
    url = f"https://discord.com/api/v10/channels/{channel_id}/messages?limit={limit}"
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bot {token}",
        "Content-Type": "application/json",
        "User-Agent": "AI-Digest-Bot/1.0 (https://github.com/kanibot818/ai-digest-site)",
    })

    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


# ============================================================
# MESSAGE PARSING
# ============================================================

def parse_digest(content, timestamp):
    """Parse a KaniBot digest message into structured data."""
    lines = content.strip().split('\n')

    # Extract title (## Title or first non-empty line)
    title = None
    body_start = 0
    for i, line in enumerate(lines):
        line = line.strip()
        if line.startswith('## '):
            title = line[3:].strip()
            title = re.sub(r'[─—–-]+$', '', title).strip()
            body_start = i + 1
            break
        elif line and not title and not line.startswith(('terminal', '🌐', '💻', '📸', '📎')):
            title = line
            body_start = i + 1
            break

    if not title:
        return None

    # Parse body: extract bullet points and links
    summary = []
    links = []

    body_lines = lines[body_start:]
    for line in body_lines:
        line = line.strip()
        if not line or line in ('──', '─', '—'):
            continue
        if line.startswith(('terminal', '🌐', '💻', '📸', '```')):
            continue

        # Extract links: 📎 [label](url) or [label](url)
        link_matches = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', line)
        for label, url in link_matches:
            links.append({"label": label, "url": url})

        # Clean bullet points
        if line.startswith('- '):
            clean = line[2:]
            clean = re.sub(r'\*\*(.+?)\*\*', r'\1', clean)
            clean = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', clean)
            clean = clean.strip()
            if clean and len(clean) > 10:
                summary.append(clean)
        elif line.startswith('  - '):
            clean = line[4:]
            clean = re.sub(r'\*\*(.+?)\*\*', r'\1', clean)
            clean = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', clean)
            clean = clean.strip()
            if clean and len(clean) > 10:
                if summary:
                    summary[-1] += f" — {clean}"

    if not summary:
        return None

    # Parse date
    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
    date_str = dt.strftime('%Y-%m-%d')

    # Generate ID from title
    digest_id = re.sub(r'[^a-zA-Z0-9\u4e00-\u9fff]', '-', title.lower())[:50]
    digest_id = re.sub(r'-+', '-', digest_id).strip('-')

    # Determine source URL — prefer the most relevant link
    source_url, source_label = pick_source_url(links)

    # Guess category
    category = guess_category(title, summary)

    return {
        "id": digest_id,
        "title": title,
        "date": date_str,
        "category": category,
        "summary": summary[:5],
        "links": links[:5],
        "source_url": source_url,
        "source_label": source_label,
        "raw_content": content,  # kept temporarily for editorial generation
    }


def pick_source_url(links):
    """Pick the best source URL — prefer GitHub/product over X/Twitter reposts."""
    if not links:
        return "", ""

    # Priority: GitHub > official docs > product site > original article
    priority_domains = [
        ("github.com", "GitHub"),
        ("docs.", "官方文件"),
        ("huggingface.co", "HuggingFace"),
        ("npmjs.com", "npm"),
        ("pypi.org", "PyPI"),
        ("x.com", "原文"),
        ("twitter.com", "原文"),
    ]

    for domain, label in priority_domains:
        for link in links:
            if domain in link["url"]:
                return link["url"], label

    # Fallback: first link
    return links[0]["url"], links[0]["label"]


def guess_category(title, summary):
    """Rough category guessing based on keywords."""
    text = (title + ' ' + ' '.join(summary)).lower()
    rules = [
        (['tts', '語音', 'voice', '音樂', 'audio', 'music'], 'AI 語音'),
        (['圖像', 'image', 'vision', '視覺', 'stable diffusion', 'midjourney'], 'AI 圖像'),
        (['video', '影片', '視頻', 'sora'], 'AI 影片'),
        (['coding', '程式', 'code', '開發', 'framework', '框架', 'ide', 'agent', 'copilot'], '開發工具'),
        (['seo', 'geo', '搜尋', 'search', '行銷', 'marketing'], 'AI 行銷'),
        (['模型', 'model', 'gpt', 'claude', 'llm', 'benchmark', '大模型'], '大模型'),
        (['research', '研究', 'paper', '論文'], '研究'),
    ]
    for keywords, cat in rules:
        if any(k in text for k in keywords):
            return cat
    return '其他'


# ============================================================
# AI EDITORIAL NOTE GENERATION
# ============================================================

def generate_editor_note(digest, api_key):
    """Call LLM to generate a 1-2 sentence editorial note for a digest."""
    if not api_key:
        return ""

    prompt = f"""你是 AI 科技媒體的編輯。用繁體中文寫 1-2 句編輯觀點，說明這則資訊為什麼值得關注。
要有自己的觀點，不要只是重複摘要。語氣專業但親切。

標題：{digest['title']}
分類：{digest['category']}
摘要重點：
{chr(10).join(f'- {s}' for s in digest['summary'][:3])}

直接輸出編輯觀點文字，不要加引號或前綴。最多 80 字。"""

    try:
        data = json.dumps({
            "model": LLM_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 200,
            "temperature": 0.7,
        }).encode()

        req = urllib.request.Request(LLM_BASE_URL, data=data, headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        })

        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())

        note = result["choices"][0]["message"]["content"].strip()
        # Clean up any quotes or prefixes
        note = note.strip('"\'「」""').strip()
        return note

    except Exception as e:
        print(f"  ⚠️  Editorial generation failed for '{digest['title'][:30]}': {e}", file=sys.stderr)
        return ""


# ============================================================
# OG IMAGE FETCHING
# ============================================================

def fetch_og_image(url, digest_id, images_dir="images"):
    """Fetch OG image from a URL and save locally. Returns relative path or empty."""
    if not url:
        return ""

    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (compatible; AI-Digest-Bot/1.0)",
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode('utf-8', errors='ignore')[:50000]

        # Extract og:image
        match = re.search(
            r'<meta\s+[^>]*property=["\']og:image["\']\s+[^>]*content=["\']([^"\']+)["\']',
            html, re.IGNORECASE
        )
        if not match:
            # Try twitter:image
            match = re.search(
                r'<meta\s+[^>]*name=["\']twitter:image["\']\s+[^>]*content=["\']([^"\']+)["\']',
                html, re.IGNORECASE
            )

        if not match:
            return ""

        img_url = match.group(1)

        # Download image
        img_req = urllib.request.Request(img_url, headers={
            "User-Agent": "Mozilla/5.0 (compatible; AI-Digest-Bot/1.0)",
        })
        with urllib.request.urlopen(img_req, timeout=15) as img_resp:
            img_data = img_resp.read()

        # Only save if it's a real image (>1KB)
        if len(img_data) < 1024:
            return ""

        os.makedirs(images_dir, exist_ok=True)
        # Use hash of digest_id for stable filename
        safe_name = re.sub(r'[^a-zA-Z0-9-]', '', digest_id)[:40]
        img_path = os.path.join(images_dir, f"{safe_name}.png")
        with open(img_path, 'wb') as f:
            f.write(img_data)

        return f"{images_dir}/{safe_name}.png"

    except Exception as e:
        print(f"  ⚠️  OG image fetch failed for {url[:50]}: {e}", file=sys.stderr)
        return ""


# ============================================================
# MAIN
# ============================================================

def main():
    parser = argparse.ArgumentParser(description='Fetch Discord digests → JSON')
    parser.add_argument('--channel', default=DEFAULT_CHANNEL, help='Discord channel ID')
    parser.add_argument('--limit', type=int, default=100, help='Max messages to fetch')
    parser.add_argument('--output', default='data/digests.json', help='Output JSON path')
    parser.add_argument('--no-ai', action='store_true', help='Skip AI editorial note generation')
    parser.add_argument('--no-images', action='store_true', help='Skip OG image fetching')
    args = parser.parse_args()

    # Credentials from env only
    token = os.environ.get('DISCORD_BOT_TOKEN')
    channel = args.channel or DEFAULT_CHANNEL
    glm_key = os.environ.get('GLM_API_KEY', '')

    if not token:
        print("❌ Set DISCORD_BOT_TOKEN environment variable", file=sys.stderr)
        sys.exit(1)
    if not channel:
        print("❌ Set DISCORD_CHANNEL_ID environment variable", file=sys.stderr)
        sys.exit(1)

    # Step 1: Fetch messages
    print(f"📡 Fetching up to {args.limit} messages from channel {channel}...")
    try:
        messages = fetch_messages(channel, token, args.limit)
    except Exception as e:
        print(f"❌ Discord API error: {e}", file=sys.stderr)
        print("⚠️ Keeping existing digests.json unchanged.", file=sys.stderr)
        sys.exit(0)

    # Step 2: Parse digests
    digests = []
    seen_ids = set()

    for msg in messages:
        if msg.get('author', {}).get('bot') and '## ' in msg.get('content', ''):
            parsed = parse_digest(msg['content'], msg['timestamp'])
            if parsed and parsed['id'] not in seen_ids:
                digests.append(parsed)
                seen_ids.add(parsed['id'])

    print(f"📋 Parsed {len(digests)} digests")

    # Step 3: Generate AI editorial notes
    if not args.no_ai and glm_key:
        print(f"✍️ Generating editorial notes (model: {LLM_MODEL})...")
        for i, d in enumerate(digests):
            print(f"  [{i+1}/{len(digests)}] {d['title'][:40]}...")
            d['editor_note'] = generate_editor_note(d, glm_key)
    else:
        if not glm_key:
            print("⚠️ No GLM_API_KEY — skipping editorial notes")
        for d in digests:
            d['editor_note'] = d.get('editor_note', '')

    # Step 4: Fetch OG images
    if not args.no_images:
        print("🖼️ Fetching OG images...")
        for i, d in enumerate(digests):
            url = d.get('source_url', '')
            if url:
                print(f"  [{i+1}/{len(digests)}] {url[:50]}...")
                img_path = fetch_og_image(url, d['id'])
                d['image'] = img_path
            else:
                d['image'] = d.get('image', '')

    # Step 5: Clean up temporary fields
    for d in digests:
        d.pop('raw_content', None)

    # Sort by date descending
    digests.sort(key=lambda d: d['date'], reverse=True)

    # Write output
    os.makedirs(os.path.dirname(args.output) or '.', exist_ok=True)
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(digests, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Wrote {len(digests)} digests to {args.output}")
    print(f"   Editorial notes: {sum(1 for d in digests if d.get('editor_note'))}/{len(digests)}")
    print(f"   Images: {sum(1 for d in digests if d.get('image'))}/{len(digests)}")


if __name__ == '__main__':
    main()
