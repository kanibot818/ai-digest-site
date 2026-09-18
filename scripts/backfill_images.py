#!/usr/bin/env python3
"""Backfill OG images for digests.json entries missing them. Sequential + 429 backoff."""
import sys, os, json, time

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from fetch_digests import fetch_og_image

PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'digests.json')

with open(PATH, 'r', encoding='utf-8') as f:
    data = json.load(f)

todo = [d for d in data if not d.get('image') and d.get('source_url')]
print(f"{len(todo)} images to fetch", flush=True)

t0 = time.time()
ok = 0
for idx, d in enumerate(todo):
    img = ""
    for attempt in range(3):
        try:
            img = fetch_og_image(d['source_url'], d['id'])
            break
        except Exception as e:
            if '429' in str(e):
                wait = 15 * (attempt + 1)
                print(f"  429 backoff {wait}s ({d['id'][:30]})", flush=True)
                time.sleep(wait)
            else:
                break
    if img:
        d['image'] = img
        ok += 1
    if (idx + 1) % 20 == 0:
        with open(PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"  {idx+1}/{len(todo)} ok={ok} ({time.time()-t0:.0f}s)", flush=True)
    time.sleep(1.0)

with open(PATH, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
n = sum(1 for d in data if d.get('image'))
print(f"DONE: {ok}/{len(todo)} this pass, total {n}/{len(data)} in {time.time()-t0:.0f}s", flush=True)
