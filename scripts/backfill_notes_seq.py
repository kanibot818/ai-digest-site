#!/usr/bin/env python3
"""Backfill editorial notes (pass 2) — sequential with rate-limit backoff."""
import sys, os, json, time

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from fetch_digests import generate_editor_note

PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'digests.json')

with open(PATH, 'r', encoding='utf-8') as f:
    data = json.load(f)

todo = [d for d in data if not d.get('editor_note') and d.get('summary')]
print(f"{len(todo)} notes remaining", flush=True)

api_key = os.environ.get('GLM_API_KEY', '')
t0 = time.time()
ok = 0
for idx, d in enumerate(todo):
    note = ""
    for attempt in range(3):
        try:
            note = generate_editor_note(d, api_key)
            if note:
                break
        except Exception as e:
            if '429' in str(e):
                wait = 20 * (attempt + 1)
                print(f"  429 backoff {wait}s ({d['id'][:30]})", flush=True)
                time.sleep(wait)
            else:
                print(f"  err {d['id'][:30]}: {e}", flush=True)
                break
    if note:
        d['editor_note'] = note
        ok += 1
    if (idx + 1) % 20 == 0:
        # checkpoint save
        with open(PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"  {idx+1}/{len(todo)} ok={ok} ({time.time()-t0:.0f}s)", flush=True)
    time.sleep(1.2)  # pace: ~50 req/min stays under limit

with open(PATH, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
n = sum(1 for d in data if d.get('editor_note'))
print(f"DONE: {ok}/{len(todo)} this pass, total {n}/{len(data)} in {time.time()-t0:.0f}s", flush=True)
