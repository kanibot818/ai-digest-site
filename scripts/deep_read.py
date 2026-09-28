#!/usr/bin/env python3
"""
Deep-read pipeline: fetch full article text for digest items and rewrite
the summary into a rich deep summary, via GLM.

For each item with a resolvable article URL (original_url, else source_url
when it is not an X/Twitter link):
  1. Extract main text with trafilatura (requests-free, stdlib fetch).
  2. If extraction fails or text is too short, mark item `deep_status: "no_source"`
     — keep the original summary, never fabricate.
  3. Otherwise call GLM to rewrite a 200-300 char deep summary covering:
     是什麼 / 怎麼做到 / 為什麼重要 / 適合誰.

Usage:
  python3 scripts/deep_read.py [--limit N] [--dry-run] [--refetch]
Requires: GLM_API_KEY env var. Uses repo-local .venv (trafilatura).
Appends items incrementally to data/deep_read_state.json so progress
survives interruption; digests.json is written only at the end.
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

try:
    import trafilatura
except ImportError:
    print("trafilatura missing — run: uv pip install --python .venv/bin/python trafilatura", file=sys.stderr)
    sys.exit(1)

from fetch_digests import _call_llm  # reuse the same GLM call path

DATA = os.path.join(ROOT, "data", "digests.json")
STATE = os.path.join(ROOT, "data", "deep_read_state.json")
WORKERS = int(os.environ.get("DEEP_WORKERS", "4"))
MIN_TEXT = 400  # chars of extracted article text below which we treat as no-source

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

DEEP_PROMPT = """你是 AI 科技媒體的深度編輯。根據下面的原文，用繁體中文重寫這則摘要。

要求：
- 200-300 字，3-5 段短句（每句一行，不要編號、不要 markdown）
- 講清楚四件事：這是什麼、關鍵做法或數據、為什麼重要、適合誰關注
- 只用原文有的資訊，原文沒有的不要編
- 語氣具體、有細節，不要空話（禁止「值得關注」「不容忽視」這類填充句）

標題：{title}
分類：{category}
既有的粗摘要（僅供參考，不要照抄）：
{old_summary}

原文全文：
{article}
"""

SHORT_EDITOR_PROMPT = """你是 AI 科技媒體的編輯。根據下面的原文與深摘，用繁體中文寫 80-120 字的編輯觀點段落。
要有立場：可以指出局限、給出判斷、或點出跟產業趨勢的關係，不要重複摘要內容，不要總結式收尾。
直接輸出文字，不要引號或前綴。

標題：{title}
深摘：
{deep}
"""


def article_url_for(d):
    """Prefer original_url; accept source_url only if it's a real article page."""
    u = d.get("original_url") or ""
    if u:
        return u
    su = d.get("source_url") or ""
    if su and not re.search(r"(x\.com|twitter\.com)/", su):
        return su
    return ""


def extract_text(url):
    """Download and extract main article text. Returns '' on any failure."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=20) as resp:
            html = resp.read(2_000_000).decode("utf-8", errors="ignore")
        if "<html" not in html.lower():
            return ""  # JSON/PDF/binary — not handled here
        text = trafilatura.extract(html, favor_recall=True, include_comments=False) or ""
        return text.strip()
    except Exception:
        return ""


def load_state():
    if os.path.exists(STATE):
        with open(STATE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_state(state):
    with open(STATE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False)


def deep_summarize(d, article, api_key):
    old = "\n".join(f"- {s}" for s in (d.get("summary") or [])[:4])
    prompt = DEEP_PROMPT.format(title=d["title"], category=d.get("category", ""),
                                old_summary=old, article=article[:12000])
    for attempt in range(2):
        try:
            out = _call_llm(prompt, api_key, max_tokens=8000)
            lines = [l.strip() for l in out.strip().splitlines() if l.strip()]
            lines = [re.sub(r"^[-*•]\s*", "", l) for l in lines]
            if len("".join(lines)) >= 80:
                return lines
        except Exception as e:
            print(f"  llm err: {e}", file=sys.stderr)
        time.sleep(2)
    return []


def rewrite_editor(d, api_key):
    prompt = SHORT_EDITOR_PROMPT.format(title=d["title"], deep="\n".join(d["deep_summary"]))
    try:
        note = _call_llm(prompt, api_key, max_tokens=8000).strip().strip("\"'「」").strip()
        return note if len(note) >= 30 else ""
    except Exception:
        return ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="max items to process this run")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--refetch", action="store_true", help="redo even items already processed")
    args = ap.parse_args()

    api_key = os.environ.get("GLM_API_KEY", "")
    if not args.dry_run and not api_key:
        print("GLM_API_KEY not set", file=sys.stderr)
        sys.exit(1)

    with open(DATA, "r", encoding="utf-8") as f:
        data = json.load(f)
    state = load_state()

    todo = []
    for d in data:
        if not args.refetch and d["id"] in state:
            continue
        url = article_url_for(d)
        if url:
            todo.append(d)
    # newest first so the most visible cards get depth first
    todo.sort(key=lambda d: d.get("date", ""), reverse=True)
    if args.limit:
        todo = todo[:args.limit]

    print(f"{len(todo)} items to deep-read, {WORKERS} workers", flush=True)
    t0 = time.time()
    done = 0
    lock_ok = 0

    def work(d):
        url = article_url_for(d)
        text = extract_text(url)
        if len(text) < MIN_TEXT:
            return d, {"status": "no_source", "url": url}
        if args.dry_run:
            return d, {"status": "would_read", "url": url, "chars": len(text)}
        deep = deep_summarize(d, text, api_key)
        if not deep:
            return d, {"status": "no_source", "url": url}
        return d, {"status": "ok", "url": url, "chars": len(text),
                   "deep_summary": deep}

    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futures = [ex.submit(work, d) for d in todo]
        for fut in as_completed(futures):
            d, result = fut.result()
            state[d["id"]] = {"ts": time.strftime("%Y-%m-%d %H:%M"), **result}
            done += 1
            if result["status"] == "ok":
                lock_ok += 1
            if done % 10 == 0:
                save_state(state)
                print(f"  {done}/{len(todo)} ok={lock_ok} ({time.time()-t0:.0f}s)", flush=True)

    save_state(state)

    # Apply to digests.json only at the end
    if not args.dry_run:
        n_deep = n_editor = 0
        for d in data:
            s = state.get(d["id"])
            if not s:
                continue
            if s.get("status") == "ok":
                d["deep_summary"] = s["deep_summary"]
                d["summary"] = s["deep_summary"]  # cards render summary; deep IS the new summary
                d["deep_source_chars"] = s.get("chars")
                d["deep_status"] = "ok"
                n_deep += 1
                new_note = rewrite_editor(d, api_key)
                if new_note:
                    d["editor_note"] = new_note
                    n_editor += 1
            else:
                d["deep_status"] = s.get("status", "no_source")
        with open(DATA, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"APPLIED: deep={n_deep} editor_rewritten={n_editor} / {len(data)} "
              f"in {time.time()-t0:.0f}s", flush=True)
    else:
        n_ok = sum(1 for s in state.values() if s.get("status") in ("ok", "would_read"))
        print(f"DRY-RUN: {n_ok}/{len(todo)} extractable", flush=True)


if __name__ == "__main__":
    main()
