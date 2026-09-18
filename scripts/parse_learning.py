#!/usr/bin/env python3
"""
Parser for 🧠-learning daily reports (KaniBot cronjob output).

A daily report may be split across multiple Discord messages:
  - First message starts with "Cronjob Response: AI Agent 學習日報"
  - Continuations end with "(2/2)", "(3/3)" etc.
Each report contains numbered sections:
  🛠️ **1. Title text**
     - bullet points...
     🏷️ 分類：💼產業
     🔗 https://...
Failure messages ("⚠️ Cron job ... failed") are skipped.

Output items match the digests.json schema plus a "source" field.
"""

import json
import re
from datetime import datetime, timezone

REPORT_HEADER = "Cronjob Response: AI Agent 學習日報"
FAILURE_MARK = "⚠️ Cron job"

# Section header: optional emoji prefix, then "**N. Title**"
SECTION_RE = re.compile(r'^[^\w\s─]{0,3}\s*\*\*(\d+)\.\s*(.+?)\*\*\s*$', re.M)
DATE_RE = re.compile(r'📅\s*(\d{4}-\d{2}-\d{2})')
URL_RE = re.compile(r'(https?://[^\s\)\>]+)')
CATEGORY_RE = re.compile(r'🏷️\s*分類[：:]\s*(\S+)')

# Category emoji mapping used in learning reports → clean category label
CATEGORY_LABELS = {
    '🛠️': '工具',
    '📚': '教程',
    '💼': '產業',
    '📊': '研究',
    '🚨': '安全',
    '🧪': '實驗',
    '🤖': '模型',
    '🌐': '生態',
    '🔧': '基礎設施',
    '📈': '趨勢',
}


def build_reports(messages):
    """Group split Discord messages into complete daily reports.

    messages: list of {content, timestamp, author:{username,bot}} dicts
              in chronological order.
    Returns list of {date_iso, text} for parseable reports.
    """
    reports, cur = [], None
    for m in messages:
        if not m.get('author', {}).get('bot'):
            continue
        c = m.get('content', '')
        if c.startswith(REPORT_HEADER):
            if cur:
                reports.append(cur)
            cur = {'parts': [c], 'ts': m.get('timestamp')}
        elif cur is not None:
            cur['parts'].append(c)
    if cur:
        reports.append(cur)

    out = []
    for r in reports:
        full = '\n'.join(r['parts'])
        if full[:200].find(FAILURE_MARK) != -1:
            continue  # cron failure notice, not a report
        dm = DATE_RE.search(full)
        if not dm:
            continue
        out.append({'date': dm.group(1), 'text': full, 'ts': r['ts']})
    return out


def _slugify(text, max_len=60):
    s = re.sub(r'[^a-zA-Z0-9\u4e00-\u9fff]', '-', text.lower())
    s = re.sub(r'-+', '-', s).strip('-')
    return s[:max_len].rstrip('-')


def _parse_section(block):
    """Parse one numbered section into a digest item (or None)."""
    # find the header line inside the block (block may start with '---' etc.)
    header = None
    for line in block.split('\n'):
        if re.match(r'^[^\w\s─]{0,3}\s*\*\*\d+\.', line.strip()):
            header = line
            break
    if not header:
        return None
    m = re.match(r'^[^\w\s─]{0,3}\s*\*\*\d+\.\s*(.+?)\*\*\s*$', header.strip())
    if not m:
        return None
    title = m.group(1).strip()

    summary = []
    category = ''
    links = []
    source_url = ''

    for line in block.split('\n'):
        line = line.strip()
        if not line or line in ('---', '──', '─'):
            continue
        if re.match(r'^[^\w\s─]{0,3}\s*\*\*\d+\.', line):
            continue  # header line itself
        if line.startswith(('🏷️', '**分類')):
            cm = CATEGORY_RE.search(line)
            if cm:
                # strip emoji + parenthetical/slash qualifiers: "💼產業" → "產業",
                # "工具（重大更新）" → "工具", "研究／產業" → take first part
                cat = cm.group(1)
                for emoji in CATEGORY_LABELS:
                    cat = cat.replace(emoji, '')
                cat = re.split(r'[（(／/]', cat)[0]
                category = cat.strip()
            continue
        if line.startswith(('- 🔗', '🔗')):
            urls = URL_RE.findall(line)
            if urls:
                links.append({'label': '來源', 'url': urls[0]})
                if not source_url:
                    source_url = urls[0]
            continue
        # plain URLs in body (older format)
        for u in URL_RE.findall(line):
            if 'http' in line and not line.startswith('- '):
                links.append({'label': '來源', 'url': u})
                if not source_url:
                    source_url = u
        if line.startswith('- '):
            clean = line[2:]
            clean = re.sub(r'\*\*(.+?)\*\*', r'\1', clean)
            clean = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', clean)
            clean = re.sub(r'\(1/\d+\)|\(2/\d+\)|\(3/\d+\)', '', clean)
            clean = clean.strip()
            # skip bare link bullets (URL already captured above)
            if clean.startswith('http'):
                continue
            if len(clean) > 10:
                summary.append(clean)

    if not summary:
        # Prose format (some reports use paragraphs instead of bullets):
        # fall back to first substantial non-tag paragraph as summary.
        for line in block.split('\n'):
            line = line.strip()
            if (not line or line in ('---', '──', '─') or line.startswith(('🏷️', '🔗', '- 🔗'))
                    or re.match(r'^[^\w\s─]{0,3}\s*\*\*\d+\.', line)
                    or line.startswith(('>', '📅', 'To stop', '(1/', '(2/', '(3/'))):
                continue
            clean = re.sub(r'\*\*(.+?)\*\*', r'\1', line)
            clean = re.sub(r'\(1/\d+\)|\(2/\d+\)|\(3/\d+\)', '', clean).strip()
            if len(clean) > 30 and not clean.startswith('http'):
                summary.append(clean)
                break

    if not summary or not title:
        return None

    return {
        'title': title,
        'category': category or '其他',
        'summary': summary[:5],
        'links': links[:3],
        'source_url': source_url,
        'source_label': '來源' if source_url else '',
    }


def resolve_original_url(source_url):
    """For X status links, resolve the attached link-card's landing URL (the
    original article). Returns '' when the tweet has no card or links to X itself."""
    if not source_url or 'x.com/' not in source_url or '/status/' not in source_url:
        return ''
    import urllib.request, urllib.error
    tweet_id = source_url.split('/status/')[1].split('?')[0].rstrip('/')
    if not tweet_id.isdigit():
        return ''
    ua = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    class _NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs):
            return None

    opener = urllib.request.build_opener(_NoRedirect)
    try:
        su = f"https://cdn.syndication.twimg.com/tweet-result?id={tweet_id}&lang=en&token=x"
        with urllib.request.urlopen(urllib.request.Request(su, headers=ua), timeout=15) as r:
            tj = json.load(r)
        card = tj.get('card') or {}
        bv = card.get('binding_values') or {}
        card_url = (bv.get('card_url') or {}).get('string_value') or card.get('url') or ''
        if 't.co' not in card_url:
            return ''
        req2 = urllib.request.Request(card_url, headers=ua, method="HEAD")
        try:
            opener.open(req2, timeout=15)
            return ''
        except urllib.error.HTTPError as e:
            loc = e.headers.get('Location', '')
            return loc if loc.startswith('http') and 'x.com' not in loc and 'twitter.com' not in loc else ''
    except Exception:
        return ''


def parse_report(report, limit_per_report=10):
    """Parse one report into a list of digest items with ids/dates/source set."""
    text = report['text']
    date = report['date']
    matches = list(SECTION_RE.finditer(text))
    items = []
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        block = text[m.start():end]
        parsed = _parse_section(block)
        if not parsed:
            continue
        item_id = 'lrn-' + date + '-' + _slugify(parsed['title'])[:40]
        parsed.update({
            'id': item_id,
            'date': date,
            'source': 'learning',
        })
        items.append(parsed)
        if len(items) >= limit_per_report:
            break
    return items


def parse_all_reports(messages):
    """Convenience: messages → flat list of digest items."""
    items = []
    for report in build_reports(messages):
        items.extend(parse_report(report))
    return items
