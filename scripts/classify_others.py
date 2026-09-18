#!/usr/bin/env python3
"""Batch-classify learning cards stuck in 其他 using GLM (flash, cheap)."""
import json, os, sys, time, urllib.request

PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'digests.json')
API = "https://api.z.ai/api/coding/paas/v4/chat/completions"
MODEL = "glm-4.5-flash"
CATS = ["工具", "教程", "產業", "研究", "安全", "實驗", "模型", "生態", "基礎設施", "趨勢"]

with open(PATH, 'r', encoding='utf-8') as f:
    data = json.load(f)

todo = [i for i in data if i.get('source') == 'learning' and i['category'] == '其他']
print(f"{len(todo)} cards to classify with {MODEL}", flush=True)

key = os.environ['GLM_API_KEY']

def classify(items):
    lines = [f"{n}. {i['title']}｜{' '.join((i.get('summary') or [])[:2])[:80]}" for n, i in enumerate(items, 1)]
    prompt = (
        "把以下 AI 新聞條目各分到一個分類。只能從這些選："
        + "、".join(CATS)
        + "。\n只輸出 JSON 陣列（如 [\"工具\",\"研究\",...]），順序對應條目，不要其他文字。\n\n"
        + "\n".join(lines)
    )
    body = json.dumps({
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
        "max_tokens": 2000,
    }).encode()
    req = urllib.request.Request(API, data=body, headers={
        "Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        resp = json.load(r)
    text = resp['choices'][0]['message']['content'].strip()
    # strip markdown fences if present
    if text.startswith('```'):
        text = text.split('```')[1].lstrip('json').strip()
    arr = json.loads(text)
    assert isinstance(arr, list) and len(arr) == len(items), f"len mismatch {len(arr)} vs {len(items)}"
    return arr

BATCH = 15
done = 0
t0 = time.time()
for start in range(0, len(todo), BATCH):
    batch = todo[start:start+BATCH]
    cats = None
    for attempt in range(3):
        try:
            cats = classify(batch)
            break
        except Exception as e:
            print(f"  retry {attempt+1}: {str(e)[:100]}", flush=True)
            time.sleep(10 * (attempt + 1))
    if not cats:
        print(f"  batch {start} FAILED, keeping 其他", flush=True)
        continue
    for item, cat in zip(batch, cats):
        if cat in CATS:
            item['category'] = cat
            done += 1
    print(f"  {min(start+BATCH, len(todo))}/{len(todo)} ({time.time()-t0:.0f}s)", flush=True)
    time.sleep(2)

with open(PATH, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

from collections import Counter
print("DONE:", done, "reclassified")
print(Counter(i['category'] for i in data if i.get('source') == 'learning').most_common())
