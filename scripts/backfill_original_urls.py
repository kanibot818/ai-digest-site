#!/usr/bin/env python3
"""Extract the original article URL behind X card links (via syndication + t.co resolve)."""
import json, os, sys, time, urllib.request, urllib.error

PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'digests.json')
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

with open(PATH, 'r', encoding='utf-8') as f:
    data = json.load(f)

todo = [i for i in data if i.get('source') == 'learning' and not i.get('original_url')
        and 'x.com/' in i.get('source_url', '') and '/status/' in i.get('source_url', '')]
print(f"{len(todo)} X cards to resolve", flush=True)

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None

opener = urllib.request.build_opener(NoRedirect)

def get_original_url(tweet_id):
    su = f"https://cdn.syndication.twimg.com/tweet-result?id={tweet_id}&lang=en&token=x"
    req = urllib.request.Request(su, headers=UA)
    with urllib.request.urlopen(req, timeout=15) as r:
        tj = json.load(r)
    card = tj.get('card') or {}
    bv = card.get('binding_values') or {}
    card_url = (bv.get('card_url') or {}).get('string_value') or card.get('url')
    if not card_url or 't.co' not in card_url:
        return ""
    req2 = urllib.request.Request(card_url, headers=UA, method="HEAD")
    try:
        opener.open(req2, timeout=15)
        return ""
    except urllib.error.HTTPError as e:
        loc = e.headers.get('Location', '')
        return loc if loc.startswith('http') else ""

t0 = time.time()
ok = 0
for idx, item in enumerate(todo):
    tweet_id = item['source_url'].split('/status/')[1].split('?')[0].rstrip('/')
    if not tweet_id.isdigit():
        continue
    orig = ""
    for attempt in range(3):
        try:
            orig = get_original_url(tweet_id)
            break
        except Exception:
            time.sleep(5 * (attempt + 1))
    if orig and 'x.com' not in orig and 'twitter.com' not in orig:
        item['original_url'] = orig
        ok += 1
    if (idx + 1) % 20 == 0:
        with open(PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"  {idx+1}/{len(todo)} ok={ok} ({time.time()-t0:.0f}s)", flush=True)
    time.sleep(0.8)

with open(PATH, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
n = sum(1 for i in data if i.get('original_url'))
print(f"DONE: {ok}/{len(todo)} resolved, total {n} cards with original_url in {time.time()-t0:.0f}s", flush=True)
