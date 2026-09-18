#!/usr/bin/env python3
"""Backfill editorial notes for digests.json via GLM, with ThreadPool concurrency."""
import sys, os, json, time
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from fetch_digests import generate_editor_note

PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'digests.json')
WORKERS = int(os.environ.get('NOTE_WORKERS', '6'))

with open(PATH, 'r', encoding='utf-8') as f:
    data = json.load(f)

todo = [d for d in data if not d.get('editor_note') and d.get('summary')]
print(f"{len(todo)} notes to generate, {WORKERS} workers", flush=True)

api_key = os.environ.get('GLM_API_KEY', '')
done = 0
t0 = time.time()

def work(d):
    try:
        return d, generate_editor_note(d, api_key)
    except Exception as e:
        print(f"  err {d['id'][:40]}: {e}", flush=True)
        return d, ""

with ThreadPoolExecutor(max_workers=WORKERS) as ex:
    futures = [ex.submit(work, d) for d in todo]
    for fut in as_completed(futures):
        d, note = fut.result()
        if note:
            d['editor_note'] = note
        done += 1
        if done % 25 == 0:
            print(f"  {done}/{len(todo)} ({time.time()-t0:.0f}s)", flush=True)

with open(PATH, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

n = sum(1 for d in data if d.get('editor_note'))
print(f"DONE: {n}/{len(data)} notes in {time.time()-t0:.0f}s", flush=True)
