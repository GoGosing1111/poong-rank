# -*- coding: utf-8 -*-
"""
CNINE 공지 수집기 v2 - API 방식

핵심:
- cnine.kr React HTML 파싱 안 함
- 개발자도구 Network / Fetch-XHR에서 보이는 API JSON을 직접 호출
- 기본 후보 API를 자동 시도
- 정확한 API 주소를 알고 있으면 cnine_notice_api.txt 에 1줄로 넣으면 그 주소 우선 사용
- notice_status.json : 대시보드 최신 출력용
- notice_history.json : 누적 보관용
- notice_api_debug.json / notice_debug.txt : 실패 원인 확인용

실행:
python update_cnine_notice.py
"""

import json
import urllib.request
import urllib.parse
import traceback
from pathlib import Path
from datetime import datetime

BASE = "https://www.cnine.kr"

OUT_STATUS = "notice_status.json"
OUT_HISTORY = "notice_history.json"
DEBUG_TXT = "notice_debug.txt"
DEBUG_JSON = "notice_api_debug.json"
API_TXT = "cnine_notice_api.txt"
COOKIE_TXT = "cnine_cookies.txt"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36",
    "Accept": "application/json,text/plain,*/*",
    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
    "Referer": "https://www.cnine.kr/board/an",
    "Origin": "https://www.cnine.kr",
}

def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def read_text(path):
    p = Path(path)
    if p.exists():
        return p.read_text(encoding="utf-8", errors="ignore").strip()
    return ""

def load_cookies():
    txt = read_text(COOKIE_TXT)
    if not txt:
        return ""
    # 크롬에서 복사한 Cookie 헤더 전체 또는 key=value; key2=value2 형태 둘 다 허용
    if txt.lower().startswith("cookie:"):
        txt = txt.split(":", 1)[1].strip()
    return txt

def fetch_json(url):
    headers = dict(HEADERS)
    ck = load_cookies()
    if ck:
        headers["Cookie"] = ck
    req = urllib.request.Request(url, headers=headers, method="GET")
    with urllib.request.urlopen(req, timeout=15) as res:
        raw = res.read()
        text = raw.decode("utf-8", errors="ignore")
        return json.loads(text), text

def normalize_url(url):
    url = (url or "").strip()
    if not url:
        return ""
    if url.startswith("/"):
        return BASE + url
    return url

def candidate_urls():
    urls = []

    # 사용자가 개발자도구에서 찾은 정확한 Request URL을 여기에 넣으면 최우선 사용
    custom = read_text(API_TXT)
    if custom:
        for line in custom.splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                urls.append(normalize_url(line))

    # 현재 확인된 구조상 가장 유력한 API 후보들
    urls += [
        f"{BASE}/api/main/all-page?page=1&size=20&order=latest",
        f"{BASE}/api/main/all-page?page=1&size=20&order=createdAt,desc",
        f"{BASE}/api/main/all-page?page=1&size=20",
        f"{BASE}/api/boards/an/all-page?page=1&size=20&order=latest",
        f"{BASE}/api/board/an/all-page?page=1&size=20&order=latest",
        f"{BASE}/api/posts/all-page?page=1&size=20&board=an",
    ]

    # 중복 제거
    seen = set()
    out = []
    for u in urls:
        if u and u not in seen:
            seen.add(u)
            out.append(u)
    return out

def get_nested(obj, *keys, default=None):
    cur = obj
    for k in keys:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(k)
    return cur if cur is not None else default

def abs_url(url):
    url = str(url or "").strip()
    if not url:
        return ""
    if url.startswith("//"):
        return "https:" + url
    if url.startswith("/"):
        return BASE + url
    return url

def post_link(item):
    board = item.get("board") or {}
    slug = board.get("slug") or "an"
    pid = item.get("id") or ""
    return f"{BASE}/board/{slug}/{pid}" if pid else f"{BASE}/board/{slug}"

def department_name(item):
    deps = item.get("departments") or []
    if isinstance(deps, list) and deps:
        names = []
        for d in deps:
            if isinstance(d, dict) and d.get("name"):
                names.append(str(d.get("name")))
        return ", ".join(names)
    return ""

def normalize_item(item, source):
    stat = item.get("stat") or {}
    author = item.get("author") or {}
    board = item.get("board") or {}
    return {
        "id": str(item.get("id") or ""),
        "source": source,
        "board_slug": board.get("slug") or "",
        "board_name": board.get("name") or "",
        "title": item.get("title") or "",
        "author": author.get("name") or "",
        "department": department_name(item),
        "createdAt": item.get("createdAt") or "",
        "updatedAt": item.get("updatedAt") or "",
        "popularAt": item.get("popularAt") or "",
        "viewCount": stat.get("viewCount", 0),
        "likeCount": stat.get("likeCount", 0),
        "commentCount": stat.get("commentCount", 0),
        "hasImage": bool(item.get("hasImage")),
        "thumbUrl": abs_url(item.get("thumbUrl") or ""),
        "url": post_link(item),
    }

def pick_items(data):
    """
    씨나인 숲 공지(boardSlug=an)만 수집한다.
    홈페이지 공지(notice), 일반 page 보조 데이터는 절대 포함하지 않는다.
    """
    result = []

    # API 응답 구조상 씨나인 숲 공지는 popular.data 쪽에 들어온다.
    popular = get_nested(data, "popular", "data", default=[])
    if isinstance(popular, list):
        for item in popular:
            if not isinstance(item, dict):
                continue

            board = item.get("board") or {}
            board_slug = str(board.get("slug") or "").strip()

            # 씨나인 숲 공지(an) 외에는 전부 제외
            if board_slug != "an":
                continue

            result.append(normalize_item(item, "popular"))

    # id 중복 제거
    seen = set()
    unique = []
    for it in result:
        key = it.get("id") or (it.get("title"), it.get("createdAt"))
        if key in seen:
            continue
        seen.add(key)
        unique.append(it)

    # 최신순 정렬. popularAt > updatedAt > createdAt
    unique.sort(key=lambda x: x.get("popularAt") or x.get("updatedAt") or x.get("createdAt") or "", reverse=True)
    return unique


def load_history():
    p = Path(OUT_HISTORY)
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data.get("items", []) or []
        if isinstance(data, list):
            return data
    except Exception:
        pass
    return []

def save_history(new_items, max_keep=500):
    old = load_history()
    merged = []
    seen = set()

    for it in new_items + old:
        key = it.get("id") or (it.get("title"), it.get("createdAt"))
        if not key or key in seen:
            continue
        seen.add(key)
        merged.append(it)

    merged.sort(key=lambda x: x.get("popularAt") or x.get("updatedAt") or x.get("createdAt") or "", reverse=True)
    merged = merged[:max_keep]

    Path(OUT_HISTORY).write_text(json.dumps({
        "updated_at": now_str(),
        "total": len(merged),
        "items": merged
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    return merged

def main():
    logs = []
    logs.append(f"UPDATED_AT={now_str()}")
    logs.append("MODE=cnine_api")
    logs.append("")

    last_error = ""
    used_url = ""
    raw_data = None

    for url in candidate_urls():
        try:
            logs.append(f"TRY={url}")
            data, raw_text = fetch_json(url)
            Path(DEBUG_JSON).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            items = pick_items(data)

            logs.append(f"OK_URL={url}")
            logs.append(f"FOUND_ITEMS={len(items)}")

            if items:
                raw_data = data
                used_url = url
                break

            last_error = "API 응답은 받았지만 공지 item을 찾지 못했습니다."

        except Exception as e:
            last_error = f"{type(e).__name__}: {e}"
            logs.append(f"FAIL={last_error}")

    if raw_data is None or not used_url:
        logs.append("")
        logs.append("ERROR=공지 API 수집 실패")
        logs.append(f"LAST_ERROR={last_error}")
        logs.append("")
        logs.append("해결방법:")
        logs.append("1) 크롬 F12 > Network > Fetch/XHR > all-page 클릭")
        logs.append("2) Headers의 Request URL 전체를 복사")
        logs.append("3) cnine_notice_api.txt 파일에 1줄로 붙여넣기")
        logs.append("4) 다시 python update_cnine_notice.py 실행")
        Path(DEBUG_TXT).write_text("\n".join(logs), encoding="utf-8")
        print("[ERROR] 공지 수집 실패. notice_debug.txt 확인")
        return 1

    items = pick_items(raw_data)
    history = save_history(items)

    status = {
        "updated_at": now_str(),
        "api_url": used_url,
        "latest_count": len(items),
        "history_count": len(history),
        "items": items[:20],
        "popular": [x for x in items if x.get("source") == "popular"][:10],
        "notice": [],
    }

    Path(OUT_STATUS).write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")

    logs.append("")
    logs.append("DONE")
    logs.append(f"USED_URL={used_url}")
    logs.append(f"LATEST_COUNT={len(items)}")
    logs.append(f"HISTORY_COUNT={len(history)}")
    Path(DEBUG_TXT).write_text("\n".join(logs), encoding="utf-8")

    print("=" * 60)
    print("완료:", OUT_STATUS)
    print("누적:", OUT_HISTORY)
    print("최신 공지:", len(items))
    print("누적 공지:", len(history))
    print("API:", used_url)
    print("=" * 60)
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        Path(DEBUG_TXT).write_text(traceback.format_exc(), encoding="utf-8")
        print("[ERROR] 예외 발생. notice_debug.txt 확인")
        raise
