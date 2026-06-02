# -*- coding: utf-8 -*-
"""
CNINE notice collector
- Reads cnine_cookies.txt
- Calls CNINE board API directly, no Chrome/CDP needed
- Writes notice_status.json and notice_debug.txt
"""
from __future__ import annotations

import json
import re
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE = "https://www.cnine.kr"
API_LIST = BASE + "/api/v2/p/post/all-page"
BOARD_SLUG = "an"
ROOT = Path(__file__).resolve().parent
COOKIE_FILE = ROOT / "cnine_cookies.txt"
OUT_FILE = ROOT / "notice_status.json"
DEBUG_FILE = ROOT / "notice_debug.txt"
RAW_DIR = ROOT / "api_raw"
RAW_DIR.mkdir(exist_ok=True)


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def write_debug(lines: List[str]) -> None:
    DEBUG_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def fail(lines: List[str], msg: str, code: int = 1) -> None:
    lines.append("")
    lines.append("ERROR=" + msg)
    write_debug(lines)
    print("[ERROR] " + msg)
    sys.exit(code)


def normalize_cookie_text(text: str) -> str:
    """Accepts either a raw Cookie header or pasted curl snippet, returns cookie header."""
    s = text.strip()
    # If user pasted full curl, extract -b "..." or Cookie: ...
    m = re.search(r"(?:-b|--cookie)\s+\^?\"(.*?)\^?\"", s, re.S)
    if m:
        s = m.group(1)
    else:
        m = re.search(r"cookie:\s*([^\r\n]+)", s, re.I)
        if m:
            s = m.group(1).strip().strip('"')

    # Windows cmd curl escaping cleanup
    s = s.replace("^%", "%").replace("^&", "&").replace("^$", "$")
    s = s.replace('^"', '"').replace("^^", "^")
    s = s.replace("\r", "").replace("\n", " ").strip()

    # Remove accidental leading option text
    s = re.sub(r"^Cookie:\s*", "", s, flags=re.I).strip().strip('"')
    return s


def load_cookie(lines: List[str]) -> str:
    if not COOKIE_FILE.exists():
        fail(lines, "cnine_cookies.txt 파일이 없습니다")
    cookie = normalize_cookie_text(COOKIE_FILE.read_text(encoding="utf-8", errors="ignore"))
    if "CNINE2_S_ID=" not in cookie:
        fail(lines, "cnine_cookies.txt 안에 CNINE2_S_ID가 없습니다. F12 Copy as cURL의 -b 쿠키를 다시 넣으세요.")
    if "CNINE2_REMEMBERME=" not in cookie:
        lines.append("WARN=CNINE2_REMEMBERME 쿠키가 없습니다. 세션 만료가 빨라질 수 있습니다.")
    return cookie


def request_json(url: str, cookie: str, lines: List[str], referer: str = BASE + "/board/an") -> Any:
    headers = {
        "accept": "application/json, text/plain, */*",
        "accept-language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "cache-control": "no-cache",
        "pragma": "no-cache",
        "referer": referer,
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
        "cookie": cookie,
    }
    req = Request(url, headers=headers, method="GET")
    try:
        with urlopen(req, timeout=25) as r:
            body = r.read().decode("utf-8", errors="replace")
            return json.loads(body)
    except HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", errors="replace")[:500]
        except Exception:
            pass
        lines.append(f"FAIL={e.__class__.__name__}: HTTP {e.code} {body}")
        raise
    except (URLError, TimeoutError) as e:
        lines.append(f"FAIL={e.__class__.__name__}: {e}")
        raise


def deep_find_list(obj: Any) -> List[Dict[str, Any]]:
    """Finds the first plausible post list inside unknown API response shape."""
    candidates: List[List[Dict[str, Any]]] = []

    def walk(x: Any) -> None:
        if isinstance(x, list):
            dicts = [v for v in x if isinstance(v, dict)]
            if dicts:
                score = 0
                keys = set().union(*(d.keys() for d in dicts[:5]))
                for k in ("title", "subject", "content", "body", "id", "postId", "createdAt", "createdDate"):
                    if k in keys:
                        score += 1
                if score >= 2:
                    candidates.append(dicts)
            for v in x:
                walk(v)
        elif isinstance(x, dict):
            for v in x.values():
                walk(v)

    walk(obj)
    if not candidates:
        return []
    candidates.sort(key=lambda a: len(a), reverse=True)
    return candidates[0]


def pick(d: Dict[str, Any], *keys: str) -> Any:
    for k in keys:
        if k in d and d[k] not in (None, ""):
            return d[k]
    return ""


def strip_html(s: Any) -> str:
    if s is None:
        return ""
    s = str(s)
    s = re.sub(r"<br\s*/?>", "\n", s, flags=re.I)
    s = re.sub(r"</p\s*>", "\n", s, flags=re.I)
    s = re.sub(r"<[^>]+>", "", s)
    s = (s.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">"))
    return re.sub(r"\n{3,}", "\n\n", s).strip()


def get_post_id(post: Dict[str, Any]) -> str:
    v = pick(post, "id", "postId", "post_id", "idx", "postNo", "no", "seq")
    return str(v) if v != "" else ""


def detail_urls(post: Dict[str, Any]) -> List[str]:
    pid = get_post_id(post)
    if not pid:
        return []
    # Try several common CNINE/Spring-style detail endpoints.
    return [
        f"{BASE}/api/v2/p/post/{pid}",
        f"{BASE}/api/v2/p/post/detail/{pid}",
        f"{BASE}/api/v2/p/post?postId={pid}",
        f"{BASE}/api/v2/p/post/view/{pid}",
    ]


def normalize_post(post: Dict[str, Any], cookie: str, lines: List[str]) -> Dict[str, Any]:
    title = strip_html(pick(post, "title", "subject", "name"))
    content_raw = pick(post, "content", "body", "contents", "text", "description")
    content = strip_html(content_raw)

    detail_ok = False
    if not content or len(content) < 3:
        for url in detail_urls(post):
            try:
                lines.append("DETAIL_TRY=" + url)
                detail = request_json(url, cookie, lines)
                (RAW_DIR / f"notice_detail_{get_post_id(post)}.json").write_text(json.dumps(detail, ensure_ascii=False, indent=2), encoding="utf-8")
                # detail may wrap post in data/item/post
                if isinstance(detail, dict):
                    candidates = []
                    for key in ("data", "result", "post", "item"):
                        if isinstance(detail.get(key), dict):
                            candidates.append(detail[key])
                    candidates.append(detail)
                    for c in candidates:
                        c_content = strip_html(pick(c, "content", "body", "contents", "text", "description"))
                        c_title = strip_html(pick(c, "title", "subject", "name"))
                        if c_content:
                            content = c_content
                            if c_title:
                                title = c_title
                            detail_ok = True
                            break
                if detail_ok:
                    break
            except Exception:
                continue

    pid = get_post_id(post)
    url = pick(post, "url", "link")
    if not url and pid:
        url = f"{BASE}/board/{BOARD_SLUG}/{pid}"
    elif isinstance(url, str) and url.startswith("/"):
        url = BASE + url

    return {
        "id": pid,
        "title": title or "제목 없음",
        "content": content or "본문 수집 대기 또는 원문에서 확인",
        "author": strip_html(pick(post, "author", "writer", "nickname", "userName", "createdBy")),
        "created_at": str(pick(post, "createdAt", "createdDate", "regDate", "writeDate", "created_at", "date")),
        "updated_at": str(pick(post, "updatedAt", "modifiedAt", "updatedDate", "updated_at")),
        "url": url,
        "has_content": bool(content),
        "raw_keys": sorted([str(k) for k in post.keys()]),
    }


def main() -> None:
    lines: List[str] = [
        "UPDATED_AT=" + now_str(),
        "MODE=cnine_api_cookie_headers_v2",
    ]
    try:
        cookie = load_cookie(lines)
        lines.append("COOKIE_HAS_CNINE2_S_ID=" + str("CNINE2_S_ID=" in cookie))
        lines.append("COOKIE_HAS_REMEMBERME=" + str("CNINE2_REMEMBERME=" in cookie))

        params = {
            "page": 1,
            "size": 20,
            "order": "desc",
            "orderBy": "sortKey",
            "boardSlug": BOARD_SLUG,
            "viewMode": "list",
        }
        url = API_LIST + "?" + urlencode(params)
        lines.append("TRY=" + url)
        data = request_json(url, cookie, lines)
        (RAW_DIR / "notice_list.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

        posts = deep_find_list(data)
        lines.append("POST_COUNT=" + str(len(posts)))
        if not posts:
            fail(lines, "공지 목록은 받았지만 게시글 배열을 찾지 못했습니다. api_raw/notice_list.json 확인 필요")

        items = [normalize_post(p, cookie, lines) for p in posts[:10]]
        ok_count = sum(1 for x in items if x.get("has_content"))
        lines.append("CONTENT_OK_COUNT=" + str(ok_count))

        out = {
            "updated_at": now_str(),
            "source": "cnine_api",
            "board_slug": BOARD_SLUG,
            "count": len(items),
            "content_ok_count": ok_count,
            "items": items,
        }
        OUT_FILE.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        lines.append("OUTPUT=notice_status.json")
        write_debug(lines)
        print(f"완료: notice_status.json 생성 / 공지 {len(items)}개 / 본문 {ok_count}개")
    except Exception as e:
        lines.append("LAST_ERROR=" + repr(e))
        lines.append(traceback.format_exc())
        write_debug(lines)
        print("[ERROR] 공지 API 수집 실패. notice_debug.txt 확인")
        sys.exit(1)


if __name__ == "__main__":
    main()
