# -*- coding: utf-8 -*-
"""
CNINE 일정표 수집기 v2
- 여러 CNINE API 후보 + 페이지 HTML/Next 데이터 후보를 순차 시도
- 실패해도 schedule_status.json 기본 구조 생성
"""
from __future__ import annotations

import json
import re
import urllib.request
from datetime import datetime
from pathlib import Path
from html import unescape

OUT = Path("schedule_status.json")
DEBUG = Path("schedule_debug_body.txt")
COOKIE_FILE = Path("cnine_cookies.txt")
TIMEOUT = 20

URLS = [
    "https://www.cnine.kr/api/v2/p/schedule/all-page?page=1&size=50&order=asc&orderBy=startAt",
    "https://www.cnine.kr/api/v2/p/calendar/all-page?page=1&size=50&order=asc&orderBy=startAt",
    "https://www.cnine.kr/api/v2/p/event/all-page?page=1&size=50&order=asc&orderBy=startAt",
    "https://www.cnine.kr/api/v2/p/post/all-page?page=1&size=50&order=desc&orderBy=sortKey&boardSlug=schedule&viewMode=list",
    "https://www.cnine.kr/api/v2/p/post/all-page?page=1&size=50&order=desc&orderBy=sortKey&boardSlug=sc&viewMode=list",
    "https://www.cnine.kr/schedule",
    "https://www.cnine.kr/timeline",
]


def load_cookie() -> str:
    if COOKIE_FILE.exists():
        return COOKIE_FILE.read_text(encoding="utf-8", errors="ignore").strip()
    return ""


def fetch(url: str) -> str:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/148 Safari/537.36",
        "Accept": "application/json,text/html,*/*",
        "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
        "Referer": "https://www.cnine.kr/",
    }
    ck = load_cookie()
    if ck:
        headers["Cookie"] = ck
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as res:
        return res.read().decode("utf-8", errors="ignore")


def clean_text(s):
    s = re.sub(r"<[^>]+>", " ", str(s or ""))
    s = unescape(s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def find_items(obj):
    found = []
    def walk(x):
        if isinstance(x, list):
            for it in x:
                walk(it)
        elif isinstance(x, dict):
            title = x.get("title") or x.get("name") or x.get("subject") or x.get("content")
            date = x.get("startAt") or x.get("start_at") or x.get("startDate") or x.get("date") or x.get("datetime") or x.get("time")
            if title and (date or any(k in x for k in ("endAt", "popularAt", "createdAt"))):
                found.append(x)
            for v in x.values():
                if isinstance(v, (list, dict)):
                    walk(v)
    walk(obj)
    return found


def normalize(raw):
    items = []
    for x in raw:
        title = x.get("title") or x.get("name") or x.get("subject") or x.get("content") or x.get("description") or ""
        date = x.get("startAt") or x.get("start_at") or x.get("startDate") or x.get("date") or x.get("datetime") or x.get("time") or x.get("popularAt") or x.get("createdAt") or ""
        typ = x.get("type") or x.get("category") or x.get("department") or x.get("part") or "일정"
        title = clean_text(title)
        date = clean_text(date).replace("T", " ")[:19]
        if not title:
            continue
        # 공지 본문 같은 긴 텍스트가 잘못 잡히는 것 방지
        if len(title) > 160:
            title = title[:160] + "..."
        items.append({"title": title, "date": date, "type": clean_text(typ), "raw_id": x.get("id") or x.get("postId") or ""})
    # 중복 제거
    seen = set(); out=[]
    for it in items:
        key=(it["title"], it["date"])
        if key in seen: continue
        seen.add(key); out.append(it)
    return out[:30]


def parse_html_for_json(text):
    # Next.js __NEXT_DATA__ 우선
    m = re.search(r'<script[^>]+id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>', text, re.S)
    if m:
        try:
            return json.loads(unescape(m.group(1)))
        except Exception:
            pass
    # 큰 JSON 조각 후보
    for pat in [r'window\.__INITIAL_STATE__\s*=\s*(\{.*?\})\s*</script>', r'window\.__NUXT__\s*=\s*(\{.*?\})\s*</script>']:
        m = re.search(pat, text, re.S)
        if m:
            try: return json.loads(m.group(1))
            except Exception: pass
    return None


def main():
    logs=[]; all_items=[]; used=""
    for url in URLS:
        logs.append(f"TRY={url}")
        try:
            text=fetch(url)
            logs.append(f"OK bytes={len(text)}")
            obj=None
            if text.lstrip().startswith(("{", "[")):
                obj=json.loads(text)
            else:
                obj=parse_html_for_json(text)
            if obj is not None:
                raw=find_items(obj)
                items=normalize(raw)
                logs.append(f"ITEMS={len(items)}")
                if items:
                    all_items=items; used=url; break
            else:
                logs.append("NO_JSON_FOUND")
        except Exception as e:
            logs.append(f"FAIL={type(e).__name__}: {e}")
    result={"updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "source": used or "none", "items": all_items, "schedules": all_items}
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    logs.append(f"FINAL_ITEMS={len(all_items)}")
    DEBUG.write_text("\n".join(logs), encoding="utf-8")
    print(f"완료: {OUT} 일정 {len(all_items)} 건")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
