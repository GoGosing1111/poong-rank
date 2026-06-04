# -*- coding: utf-8 -*-
"""
CNINE Dashboard schedule updater
- 기존 cnine_timeline_bot 방식 기반
- Playwright로 https://www.cnine.kr/timeline 렌더링 후 body 텍스트 파싱
- schedule_status.json 생성
- 자동화용: 실패해도 빈 JSON 생성 후 정상 종료(전체 자동화 중단 방지)
"""

import re
import json
import html
import traceback
from pathlib import Path
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Tuple

URL = "https://www.cnine.kr/timeline"
OUT_JSON = Path("schedule_status.json")
DEBUG_BODY = Path("schedule_debug_body.txt")
DEBUG_RENDERED = Path("schedule_debug_rendered.html")
DEBUG_LOG = Path("schedule_debug_log.txt")

MAX_DAYS = 45
MAX_ITEMS = 30
KST_WEEK = ["월", "화", "수", "목", "금", "토", "일"]


def now_kst_naive() -> datetime:
    return datetime.now()


def clean_space(s: str) -> str:
    s = html.unescape(str(s or ""))
    s = re.sub(r"[\u200b\xa0]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


DATE_RE = re.compile(
    r"(?P<year>20\d{2})\s*년\s*(?P<month>\d{1,2})\s*월\s*(?P<day>\d{1,2})\s*일"
    r"(?:\s*\((?P<w>[월화수목금토일])\))?"
)
TIME_RANGE_RE = re.compile(
    r"(?P<h1>\d{1,2})\s*:\s*(?P<m1>\d{2})(?:\s*~\s*(?P<h2>\d{1,2})\s*:\s*(?P<m2>\d{2}))?"
)
DATE_ONLY_RE = re.compile(r"^(?:오늘|내일|모레)?\s*(?:\([월화수목금토일]\))?\s*(?:~\s*(?:\([월화수목금토일]\))?)?\s*$")
BAD_TITLE_RE = re.compile(r"^(?:오늘|내일|모레|\([월화수목금토일]\)|~|\([월화수목금토일]\)\s*~|\([월화수목금토일]\)\s*~\s*\([월화수목금토일]\))$")
DDAY_ONLY_RE = re.compile(r"^D\s*-\s*\d+$", re.I)
BAD_UI_WORDS = {
    "TODAY", "D-DAY", "D DAY", "일정", "스케줄", "타임라인",
    "오늘 0개", "오늘 1개", "오늘 2개", "오늘 3개",
}


def parse_date_from_text(text: str) -> Optional[date]:
    m = DATE_RE.search(text)
    if not m:
        return None
    try:
        return date(int(m.group("year")), int(m.group("month")), int(m.group("day")))
    except ValueError:
        return None


def parse_time_from_text(text: str) -> Optional[str]:
    m = TIME_RANGE_RE.search(text)
    if not m:
        return None
    h, mi = int(m.group("h1")), int(m.group("m1"))
    if 0 <= h <= 23 and 0 <= mi <= 59:
        return f"{h:02d}:{mi:02d}"
    return None


def trim_repeated_phrase(s: str) -> str:
    s = clean_space(s)
    if not s:
        return s
    for sep in [" 스타부 :", " 엑셀<", " 김택용 :", " 혜루찡 :", " 쁠리 "]:
        idx = s.find(sep, max(1, len(s)//3))
        if idx > 0:
            s = s[:idx].strip()
            break
    m = re.search(r"(<feat\.\s*[^>]+>)", s)
    if m:
        s = s[:m.end()].strip()
    return clean_space(s)


def remove_date_time_noise(title: str) -> str:
    s = clean_space(title)
    s = DATE_RE.sub(" ", s)
    s = TIME_RANGE_RE.sub(" ", s)
    s = re.sub(r"\b오늘\b", " ", s)
    s = re.sub(r"\b내일\b", " ", s)
    s = re.sub(r"\b모레\b", " ", s)
    s = re.sub(r"\([월화수목금토일]\)\s*~\s*\([월화수목금토일]\)", " ", s)
    s = re.sub(r"\([월화수목금토일]\)\s*~", " ", s)
    s = re.sub(r"~\s*\([월화수목금토일]\)", " ", s)
    s = re.sub(r"(^|[\s:])개인(?=[가-힣A-Za-z0-9])", r"\1", s)

    # CNINE 타임라인에서 카테고리명이 제목 앞에 붙으면서
    # 씨나인씨나인 / 스타스타부 / 엑셀엑셀댄스부처럼 중복되는 문제 정리
    replacements = {
        "씨나인씨나인": "씨나인",
        "스타스타부": "스타부",
        "엑셀엑셀댄스부": "엑셀댄스부",
        "엑셀엑셀": "엑셀",
        "뮤직뮤직부": "뮤직부",
    }
    for a, b in replacements.items():
        s = s.replace(a, b)

    # 혹시 같은 단어가 앞에서 바로 2번 반복되는 케이스 보정
    # 예: 씨나인씨나인 : 제목 -> 씨나인 : 제목
    s = re.sub(r"^(씨나인)\1\s*:", r"\1 :", s)
    s = re.sub(r"^(스타부)\1\s*:", r"\1 :", s)
    s = re.sub(r"^(엑셀댄스부)\1\s*:", r"\1 :", s)

    s = re.sub(r"^[\s\-\|·:~]+", "", s)
    s = re.sub(r"[\s\-\|·:~]+$", "", s)
    return trim_repeated_phrase(s)


def is_bad_title(title: str) -> bool:
    t = clean_space(title)
    if not t or len(t) <= 2:
        return True
    if DDAY_ONLY_RE.match(t):
        return True
    if t.upper() in BAD_UI_WORDS:
        return True
    if DATE_ONLY_RE.match(t) or BAD_TITLE_RE.match(t):
        return True
    no = re.sub(r"[\s~()월화수목금토일0-9.\-/DdayTODAY]+", "", t, flags=re.I)
    if not no:
        return True
    return False


def classify(title: str) -> str:
    t = title.lower()
    if "엑셀" in title:
        return "엑셀"
    if "asl" in t or "스타" in title or "이스코어" in title or "김택용" in title or "이영호" in title:
        return "스타"
    if "생일" in title:
        return "생일"
    if "합방" in title:
        return "합방"
    return "컨텐츠"


def normalize_title_key(title: str) -> str:
    """일정 제목 중복 제거용 키.
    날짜/시간/D-day/공백/기호 차이는 같은 제목으로 처리한다.
    """
    s = clean_space(title).lower()
    s = DATE_RE.sub(" ", s)
    s = TIME_RANGE_RE.sub(" ", s)
    s = re.sub(r"\b(오늘|내일|모레)\b", " ", s)
    s = re.sub(r"\bd\s*-\s*\d+\b", " ", s, flags=re.I)
    s = re.sub(r"20\d{2}[.\-/]\d{1,2}[.\-/]\d{1,2}", " ", s)
    s = re.sub(r"\([월화수목금토일]\)", " ", s)
    s = re.sub(r"(^|[\s:])개인(?=[가-힣a-z0-9])", r"\1", s)
    # 화면 표시용 구분 기호/공백은 모두 무시
    s = re.sub(r"[\s\-_·|:!~<>.,/\[\]{}()]+", "", s)
    s = re.sub(r"[\"'“”‘’]", "", s)
    return s


def dedupe_saved_items(items: List[Dict]) -> List[Dict]:
    """마지막 저장 직전에도 한 번 더 중복 제거한다.
    앞단 파싱이 바뀌거나 다른 코드에서 items가 추가돼도 제목 기준 1개만 남긴다.
    """
    result = []
    seen = set()
    for item in sorted(items, key=lambda x: (x.get("raw_date", "9999-99-99"), x.get("time", "99:99"), normalize_title_key(x.get("title", "")))):
        title = item.get("title", "")
        # 와플컵은 어떤 형태로 중복 수집되더라도 무조건 1건만 출력
        if "와플컵" in title:
            key = "__WAFFLECUP_SINGLE__"
        else:
            key = normalize_title_key(title)
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result[:MAX_ITEMS]


def event_sort_key(ev: Dict):
    return (ev["date"], ev.get("time") or "99:99", normalize_title_key(ev["title"]))


def dedupe_events(events: List[Dict]) -> List[Dict]:
    cleaned = []
    for ev in events:
        title = remove_date_time_noise(ev.get("title", ""))
        if is_bad_title(title):
            continue
        ev = dict(ev)
        ev["title"] = title
        ev["category"] = classify(title)
        cleaned.append(ev)

    # 제목이 완전히 같은 일정은 날짜/시간이 달라도 1개만 남김.
    # 같은 제목이 여러 번 잡히면 가장 빠른 날짜/시간 1건을 대표로 사용.
    by_title = {}
    for ev in sorted(cleaned, key=event_sort_key):
        key = normalize_title_key(ev["title"])
        if not key:
            continue
        if key not in by_title or event_sort_key(ev) < event_sort_key(by_title[key]):
            by_title[key] = ev

    result = []
    seen_titles = set()
    for ev in sorted(by_title.values(), key=event_sort_key):
        k = normalize_title_key(ev["title"])
        if k in seen_titles:
            continue
        seen_titles.add(k)
        result.append(ev)
    return result[:MAX_ITEMS]


def extract_candidates_from_body(body: str) -> List[Dict]:
    today = now_kst_naive().date()
    lines = [clean_space(x) for x in body.splitlines()]
    lines = [x for x in lines if x]
    raw_events = []

    for i, line in enumerate(lines):
        d = parse_date_from_text(line)
        if not d:
            continue
        if d < today or d > today + timedelta(days=MAX_DAYS):
            continue
        tm = parse_time_from_text(line)

        candidates = []
        for j in range(max(0, i - 8), i):
            c = clean_space(lines[j])
            if not c or DATE_RE.search(c) or TIME_RANGE_RE.fullmatch(c):
                continue
            if c in {"오늘", "내일", "모레", "TODAY"}:
                continue
            if DDAY_ONLY_RE.match(c):
                continue
            if c.startswith("오늘 ") and "개" in c and "예정" in c:
                continue
            candidates.append(c)

        title = ""
        for c in reversed(candidates):
            cc = remove_date_time_noise(c)
            if not is_bad_title(cc):
                title = cc
                break

        if not title:
            line_title = remove_date_time_noise(line)
            if not is_bad_title(line_title):
                title = line_title

        if not title or is_bad_title(title):
            continue

        raw_events.append({"title": title, "date": d, "time": tm, "source_line": line})

    return dedupe_events(raw_events)


def dday_label(d: date, today: date) -> str:
    diff = (d - today).days
    return "TODAY" if diff == 0 else f"D-{diff}"


def weekday_label(d: date) -> str:
    return KST_WEEK[d.weekday()]


def format_date(d: date) -> str:
    return f"{d.year}.{d.month:02d}.{d.day:02d} ({weekday_label(d)})"


def fetch_with_playwright() -> Tuple[str, str]:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(
            viewport={"width": 1365, "height": 1800},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
            ),
        )
        page.goto(URL, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(2500)
        body_text = page.locator("body").inner_text(timeout=15000)
        content = page.content()
        browser.close()
    DEBUG_BODY.write_text(body_text, encoding="utf-8")
    DEBUG_RENDERED.write_text(content, encoding="utf-8")
    return content, body_text


def save_json(events: List[Dict], ok: bool = True, error: str = ""):
    now = now_kst_naive()
    today = now.date()
    items = []
    for ev in events:
        d = ev["date"]
        tm = ev.get("time") or "시간미정"
        items.append({
            "title": ev.get("title", ""),
            "date": format_date(d),
            "raw_date": d.isoformat(),
            "time": tm,
            "datetime": f"{format_date(d)} · ⏰ {tm}",
            "dday": dday_label(d, today),
            "type": ev.get("category") or classify(ev.get("title", "")),
            "source_line": ev.get("source_line", ""),
        })
    # 최종 안전장치: schedule_status.json 저장 직전 제목 기준으로 한 번 더 제거
    # 예) 같은 "스타부 : 와플컵 5-6티어 대회"가 여러 멤버/카테고리에서 잡혀도 1건만 저장
    items = dedupe_saved_items(items)

    data = {
        "ok": ok,
        "updated_at": now.strftime("%Y-%m-%d %H:%M:%S"),
        "source": URL,
        "count": len(items),
        "today_count": sum(1 for x in items if x.get("dday") == "TODAY"),
        "future_count": sum(1 for x in items if x.get("dday") != "TODAY"),
        "items": items,
        "error": error,
    }
    OUT_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    DEBUG_LOG.write_text("CNINE schedule updater start\n", encoding="utf-8")
    try:
        _html_source, body = fetch_with_playwright()
        events = extract_candidates_from_body(body)
        before_count = len(events)
        save_json(events, ok=True)
        # 저장 직전에도 중복 제거가 한 번 더 들어가므로 실제 저장 결과를 다시 읽어서 로그에 남김
        try:
            saved = json.loads(OUT_JSON.read_text(encoding="utf-8"))
            final_count = int(saved.get("count", before_count))
        except Exception:
            final_count = before_count
        with DEBUG_LOG.open("a", encoding="utf-8") as f:
            f.write(f"FINAL_ITEMS={final_count}\n")
            for i, e in enumerate(events, 1):
                f.write(f"{i}. {e['date']} {e.get('time') or '시간미정'} | {e['title']}\n")
        print(f"완료: schedule_status.json 일정 {len(events)} 건")
        return 0
    except Exception as e:
        err = f"{type(e).__name__}: {e}"
        save_json([], ok=False, error=err)
        with DEBUG_LOG.open("a", encoding="utf-8") as f:
            f.write(err + "\n")
            f.write(traceback.format_exc())
        print("완료: schedule_status.json 일정 0 건")
        print(f"[WARN] 일정 수집 실패: {err}")
        print("디버그: schedule_debug_log.txt / schedule_debug_body.txt")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
