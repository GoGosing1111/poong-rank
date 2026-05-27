# -*- coding: utf-8 -*-
"""
CNINE 공식 게시판 공지 수집기 v1

대상:
- https://www.cnine.kr/board/an

핵심:
- 아이디/비밀번호를 코드에 저장하지 않음
- 회원 전용 페이지면 cnine_cookies.txt의 쿠키를 사용
- 목록에서 제목/날짜/링크를 최대한 안전하게 추출
- notice_status.json 생성
- notice_debug.html / notice_debug.txt 생성

실행:
python update_cnine_notice.py

쿠키가 필요한 경우:
1) 브라우저에서 cnine.kr 로그인
2) 쿠키 확장 프로그램 등으로 cnine.kr 쿠키를 복사
3) 같은 폴더에 cnine_cookies.txt 생성
4) 아래 둘 중 하나 형식으로 저장

[간단 형식]
PHPSESSID=xxxxx; other_cookie=yyyyy

[Netscape cookies.txt 형식]
www.cnine.kr TRUE / FALSE 0 PHPSESSID xxxxx
"""

import json
import re
import time
import html
from html.parser import HTMLParser
from pathlib import Path
from datetime import datetime
from urllib.parse import urljoin
import urllib.request
import urllib.error

BOARD_URL = "https://www.cnine.kr/board/an"
OUTPUT_JSON = "notice_status.json"
DEBUG_HTML = "notice_debug.html"
DEBUG_LOG = "notice_debug.txt"
COOKIE_FILE = "cnine_cookies.txt"
MAX_ITEMS = 12

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
    "Referer": "https://www.cnine.kr/",
}


def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def read_cookie_header():
    p = Path(COOKIE_FILE)
    if not p.exists():
        return ""
    text = p.read_text(encoding="utf-8", errors="ignore").strip()
    if not text:
        return ""

    # 이미 Cookie 헤더 형태면 그대로 사용
    if ";" in text and "\t" not in text and "=" in text:
        return text.replace("\n", "; ").strip("; ")

    # Netscape cookies.txt 형식 지원
    pairs = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) >= 7:
            name = parts[5].strip()
            value = parts[6].strip()
            if name:
                pairs.append(f"{name}={value}")
    return "; ".join(pairs)


def fetch_html(url):
    headers = dict(HEADERS)
    cookie = read_cookie_header()
    if cookie:
        headers["Cookie"] = cookie

    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=15) as res:
        raw = res.read()
        charset = "utf-8"
        ctype = res.headers.get("Content-Type", "")
        m = re.search(r"charset=([\w\-]+)", ctype, re.I)
        if m:
            charset = m.group(1)
        text = raw.decode(charset, errors="ignore")
        return text, res.geturl(), res.status, bool(cookie)


class LinkTextParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack = []
        self.links = []
        self.current = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.stack.append(tag)
        if tag.lower() == "a":
            href = attrs.get("href", "")
            cls = attrs.get("class", "")
            self.current = {"href": href, "class": cls, "text": ""}

    def handle_endtag(self, tag):
        if tag.lower() == "a" and self.current:
            txt = re.sub(r"\s+", " ", self.current["text"]).strip()
            if txt:
                self.current["text"] = html.unescape(txt)
                self.links.append(self.current)
            self.current = None
        if self.stack:
            self.stack.pop()

    def handle_data(self, data):
        if self.current is not None:
            self.current["text"] += data


def clean_title(t):
    t = html.unescape(str(t or ""))
    t = re.sub(r"\s+", " ", t).strip()
    t = re.sub(r"^(공지|notice|new|\[[^\]]+\])\s*", lambda m: m.group(0), t, flags=re.I)
    return t


def is_bad_title(t):
    if not t or len(t) < 2:
        return True
    bad = ["로그인", "회원가입", "검색", "글쓰기", "목록", "이전", "다음", "처음", "마지막", "HOME", "MENU", "TOP"]
    if t.strip() in bad:
        return True
    if len(t) > 120:
        return True
    return False


def parse_notices(page_html, base_url):
    parser = LinkTextParser()
    parser.feed(page_html)

    items = []
    seen = set()

    # board/an 게시글 링크 후보 위주로 수집
    for a in parser.links:
        href = a.get("href", "")
        title = clean_title(a.get("text", ""))
        if is_bad_title(title):
            continue
        full = urljoin(base_url, href)

        # 게시글 링크로 보이는 것만 우선 통과
        href_l = href.lower()
        full_l = full.lower()
        looks_post = (
            "/board/an" in full_l
            or "bo_table=an" in full_l
            or "wr_id=" in full_l
            or re.search(r"/board/an/\d+", full_l)
        )
        if not looks_post:
            continue

        key = (title, full)
        if key in seen:
            continue
        seen.add(key)

        items.append({
            "title": title,
            "url": full,
            "date": "",
            "category": "씨나인 공지"
        })

    # 날짜는 HTML 구조가 사이트별로 다르므로 주변 텍스트에서 보조 추출
    text_flat = re.sub(r"<[^>]+>", " ", page_html)
    text_flat = html.unescape(re.sub(r"\s+", " ", text_flat))
    dates = re.findall(r"20\d{2}[.\-/]\d{1,2}[.\-/]\d{1,2}|\d{2}[.\-/]\d{1,2}[.\-/]\d{1,2}", text_flat)
    for i, d in enumerate(dates[:len(items)]):
        items[i]["date"] = d

    return items[:MAX_ITEMS]


def make_result(ok, message, items, fetched_url="", status=0, used_cookie=False):
    return {
        "updated_at": now_str(),
        "source": BOARD_URL,
        "fetched_url": fetched_url,
        "http_status": status,
        "used_cookie": used_cookie,
        "ok": ok,
        "message": message,
        "count": len(items),
        "items": items,
    }


def main():
    logs = []
    logs.append(f"UPDATED_AT={now_str()}")
    logs.append(f"SOURCE={BOARD_URL}")
    logs.append(f"COOKIE_FILE_EXISTS={Path(COOKIE_FILE).exists()}")

    try:
        text, final_url, status, used_cookie = fetch_html(BOARD_URL)
        Path(DEBUG_HTML).write_text(text, encoding="utf-8", errors="ignore")
        logs.append(f"HTTP_STATUS={status}")
        logs.append(f"FINAL_URL={final_url}")
        logs.append(f"USED_COOKIE={used_cookie}")
        logs.append(f"HTML_LENGTH={len(text)}")

        lower = text.lower()
        if any(x in lower for x in ["login", "로그인", "권한", "회원만", "permission"]):
            logs.append("LOGIN_HINT=페이지에 로그인/권한 관련 문구가 감지됨. 쿠키가 필요할 수 있음.")

        items = parse_notices(text, final_url or BOARD_URL)
        if items:
            result = make_result(True, "공지 수집 완료", items, final_url, status, used_cookie)
        else:
            result = make_result(False, "공지 항목을 찾지 못했습니다. notice_debug.html 구조 확인 필요", [], final_url, status, used_cookie)

    except urllib.error.HTTPError as e:
        msg = f"HTTP 오류: {e.code} {e.reason}"
        logs.append("ERROR=" + msg)
        result = make_result(False, msg, [], BOARD_URL, e.code, bool(read_cookie_header()))
    except Exception as e:
        msg = f"수집 실패: {e}"
        logs.append("ERROR=" + msg)
        result = make_result(False, msg, [], BOARD_URL, 0, bool(read_cookie_header()))

    Path(OUTPUT_JSON).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    Path(DEBUG_LOG).write_text("\n".join(logs), encoding="utf-8")

    print("=" * 60)
    print("완료:", OUTPUT_JSON)
    print("상태:", result.get("message"))
    print("수집:", result.get("count"), "개")
    print("디버그:", DEBUG_HTML, "/", DEBUG_LOG)
    print("=" * 60)

    if not result.get("ok"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
