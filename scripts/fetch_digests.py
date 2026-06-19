#!/usr/bin/env python3
"""
Fetch digests from Discord 🪜-digest channel and convert to digests.json.
Run locally or via GitHub Actions (with DISCORD_BOT_TOKEN secret).

Usage:
  python3 scripts/fetch_digests.py [--channel CHANNEL_ID] [--limit 100]
"""

import json
import os
import re
import sys
import argparse
from datetime import datetime, timezone

# Discord channel ID — read from env, not hardcoded
DEFAULT_CHANNEL = os.environ.get("DISCORD_CHANNEL_ID", "")


def fetch_messages(channel_id, token, limit=100):
    """Fetch messages from Discord channel via REST API."""
    import urllib.request
    import urllib.parse

    url = f"https://discord.com/api/v10/channels/{channel_id}/messages?limit={limit}"
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bot {token}",
        "Content-Type": "application/json",
        "User-Agent": "AI-Digest-Bot/1.0 (https://github.com/kanibot818/ai-digest-site)",
    })

    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())



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
            # Remove trailing separator like ──
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

    # Skip separator lines
    body_lines = lines[body_start:]
    for line in body_lines:
        line = line.strip()
        if not line or line in ('──', '─', '—'):
            continue
        # Skip tool output markers
        if line.startswith(('terminal', '🌐', '💻', '📸', '```')):
            continue

        # Extract links: 📎 [label](url) or [label](url)
        link_matches = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', line)
        for label, url in link_matches:
            links.append({"label": label, "url": url})

        # Clean bullet points: remove - ** prefix, clean markdown
        if line.startswith('- '):
            clean = line[2:]
            # Remove bold markers for summary but keep text
            clean = re.sub(r'\*\*(.+?)\*\*', r'\1', clean)
            # If line has links, extract just the text part
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
                # Append to previous summary item as sub-point
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

    # Guess category (can be refined)
    category = guess_category(title, summary)

    return {
        "id": digest_id,
        "title": title,
        "date": date_str,
        "category": category,
        "summary": summary[:5],
        "links": links[:5],
    }


def guess_category(title, summary):
    """Rough category guessing based on keywords."""
    text = (title + ' ' + ' '.join(summary)).lower()
    rules = [
        (['tts', '語音', 'voice', '音樂', 'audio', 'music'], 'AI 語音/音樂'),
        (['圖像', 'image', 'vision', '視覺', 'stable diffusion', 'midjourney'], 'AI 圖像'),
        (['video', '影片', '視頻', 'sora'], 'AI 影片'),
        (['coding', '程式', 'code', '開發', 'framework', '框架', 'ide', 'agent'], '開發工具'),
        (['seo', 'geo', '搜尋', 'search', '行銷', 'marketing'], 'SEO/行銷'),
        (['模型', 'model', 'gpt', 'claude', 'llm', 'benchmark', '大模型'], '大模型'),
        (['research', '研究', 'paper', '論文'], '研究'),
        (['開源', 'open source', 'github', 'repo'], '開源專案'),
    ]
    for keywords, cat in rules:
        if any(k in text for k in keywords):
            return cat
    return '其他'


def main():
    parser = argparse.ArgumentParser(description='Fetch Discord digests → JSON')
    parser.add_argument('--channel', default=DEFAULT_CHANNEL, help='Discord channel ID (or set DISCORD_CHANNEL_ID env)')
    parser.add_argument('--limit', type=int, default=100, help='Max messages to fetch')
    parser.add_argument('--output', default='data/digests.json', help='Output JSON path')
    args = parser.parse_args()

    # Token must come from env only — never accept via CLI to avoid process list leak
    token = os.environ.get('DISCORD_BOT_TOKEN')
    channel = args.channel or DEFAULT_CHANNEL

    if not token:
        print("❌ Set DISCORD_BOT_TOKEN environment variable", file=sys.stderr)
        sys.exit(1)
    if not channel:
        print("❌ Set DISCORD_CHANNEL_ID environment variable (or use --channel)", file=sys.stderr)
        sys.exit(1)

    print(f"Fetching up to {args.limit} messages from channel {channel}...")
    try:
        messages = fetch_messages(channel, token, args.limit)
    except Exception as e:
        print(f"❌ Discord API error: {e}", file=sys.stderr)
        # Don't fail the workflow — keep existing data
        print("⚠️ Keeping existing digests.json unchanged.", file=sys.stderr)
        sys.exit(0)

    digests = []
    seen_ids = set()

    for msg in messages:
        # Only process KaniBot's digest summaries (have ## header)
        if msg.get('author', {}).get('bot') and '## ' in msg.get('content', ''):
            parsed = parse_digest(msg['content'], msg['timestamp'])
            if parsed and parsed['id'] not in seen_ids:
                digests.append(parsed)
                seen_ids.add(parsed['id'])

    # Sort by date descending
    digests.sort(key=lambda d: d['date'], reverse=True)

    # Write output
    os.makedirs(os.path.dirname(args.output) or '.', exist_ok=True)
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(digests, f, ensure_ascii=False, indent=2)

    print(f"✅ Wrote {len(digests)} digests to {args.output}")


if __name__ == '__main__':
    main()
