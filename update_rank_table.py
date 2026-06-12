# -*- coding: utf-8 -*-
"""
CNINE 별풍선표 직접 수집기 v9 POONGGO
- poong.today 대신 poonggo.com 방송 랭킹 HTML 직접 수집
- 월간/일별 페이지네이션 전체 순회
- ranking_data.json을 현재 index.html이 요구하는 excel/star 구조로 생성
"""
from __future__ import annotations

import html
import json
import re
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

INPUT_MEMBERS = "cnine_members.json"
OUTPUT_JSON = "ranking_data.json"
DEBUG_LOG = "ranking_debug.txt"
RAW_DIR = Path("api_raw")
API_BASE = "https://poonggo.com/ranking/broadcast"
TIMEOUT = 20
REQUEST_DELAY = 0.08
MAX_MONTHLY_PAGES = 260
MAX_DAILY_PAGES = 120

# 철구형은 수장으로만 1회 집계한다.
# cnine_members.json에 스타부/엑셀부 양쪽으로 들어있어도 별풍선표 평균/순위에서는 제외된다.
LEADER_SOOP_IDS = {"y1026"}
LEADER_NAMES = {"철구형"}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/148 Safari/537.36",
    "Accept": "application/json,text/plain,*/*",
    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
    "Referer": "https://poonggo.com/ranking/broadcast?c=monthly&s=b",
}


def safe(v: Any) -> str:
    return str(v or "").strip()


def norm_name(v: Any) -> str:
    s = safe(v).lower()
    s = re.sub(r"\s+", "", s)
    s = re.sub(r"[♡♥❤★☆\[\]\(\){}<>ㆍ·_\-\.~,!/\\|#＠@;:+=\^˚´`'\"]", "", s)
    return s


def is_leader_member(m: Dict[str, Any]) -> bool:
    sid = safe(m.get("soop_id") or m.get("id")).lower()
    name = safe(m.get("name"))
    return sid in LEADER_SOOP_IDS or name in LEADER_NAMES


def unique_members_by_soop_id(members: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    out = []
    for m in members:
        sid = safe(m.get("soop_id") or m.get("id")).lower()
        key = sid or safe(m.get("name"))
        if key in seen:
            continue
        seen.add(key)
        out.append(m)
    return out


def split_leader_members(members: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    unique = unique_members_by_soop_id(members)
    leaders = [m for m in unique if is_leader_member(m)]
    regulars = [m for m in unique if not is_leader_member(m)]
    return leaders, regulars


def to_int(v: Any) -> int:
    if v is None or isinstance(v, bool):
        return 0
    if isinstance(v, (int, float)):
        return int(v)
    s = re.sub(r"[^0-9\-]", "", str(v))
    if not s or s == "-":
        return 0
    try:
        return int(s)
    except Exception:
        return 0


def fmt_num(n: int) -> str:
    return f"{int(n):,}"


def add_months(year: int, month: int, delta: int) -> Tuple[int, int]:
    m = month + delta
    y = year
    while m <= 0:
        y -= 1
        m += 12
    while m > 12:
        y += 1
        m -= 12
    return y, m

def prev_month(dt: datetime) -> Tuple[int, int]:
    return add_months(dt.year, dt.month, -1)


def build_url(ctype: str, year: int, month: int, day: int | str | None = None, page: int = 1) -> str:
    # 풍고 서버 렌더링 랭킹 페이지.
    # c=monthly: 월간, c=daily: 일별, s=b: 별풍선 기준, tab=1: 랭킹 탭.
    params = {"c": ctype, "s": "b", "tab": "1"}
    if page and page > 1:
        params["page"] = page
    # 풍고는 현재 기간 기본값이 잘 잡히지만, date를 함께 넘겨도 무시/반영된다.
    # 월간은 월초 기준 YYYY-MM-01, 일별은 당일 YYYY-MM-DD.
    if ctype == "monthly":
        params["date"] = f"{year:04d}-{month:02d}-01"
    elif ctype == "daily":
        dd = to_int(day) or datetime.now().day
        params["date"] = f"{year:04d}-{month:02d}-{dd:02d}"
    return API_BASE + "?" + urllib.parse.urlencode(params)


def fetch_text(url: str) -> str:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as res:
        raw = res.read()
    return raw.decode("utf-8", errors="ignore")


def fetch_json(url: str) -> Any:
    # 구버전 호환용. 풍고 전환 후에는 사용하지 않는다.
    text = fetch_text(url)
    return json.loads(text)


CATEGORY_HINTS = [
    "토크/캠방", "스타크래프트", "서든어택", "뮤직/댄스", "먹방/쿡방", "버추얼",
    "리그 오브 레전드", "PUBG: 배틀그라운드", "종합게임", "여행", "스포츠", "피트니스",
    "마인크래프트", "메이플스토리 월드", "마인드 스포츠", "더빙/라디오", "노래방",
    "주식", "취미", "프리스타일", "스페셜포스", "카트라이더", "배틀그라운드",
]


def clean_html_text(html: str) -> str:
    html = re.sub(r"(?is)<script.*?</script>|<style.*?</style>", "\n", html)
    html = re.sub(r"(?i)<br\s*/?>", "\n", html)
    html = re.sub(r"(?i)</(a|li|div|tr|td|span|p|button)>", "\n", html)
    text = re.sub(r"<[^>]+>", " ", html)
    text = text.replace("&nbsp;", " ").replace("&amp;", "&").replace("&#039;", "'").replace("&quot;", '"')
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    return text


def strip_category_from_name(name_part: str) -> str:
    s = safe(name_part)
    s = re.sub(r"^\d+\s+", "", s)
    s = re.sub(r"\bLIVE\b", "", s).strip()
    # 카테고리 앞까지만 닉네임으로 본다.
    best_pos = None
    for cat in CATEGORY_HINTS:
        pos = s.find(cat)
        if pos >= 0 and (best_pos is None or pos < best_pos):
            best_pos = pos
    if best_pos is not None:
        s = s[:best_pos].strip()
    # 혹시 카테고리 목록에 없는 경우 마지막 숫자열 앞 공백까지는 이미 잘려 있으므로 그대로 둔다.
    return s.strip()


def extract_poonggo_rows_from_html(src: str) -> List[Dict[str, Any]]:
    """
    풍고 랭킹 HTML에서 SOOP ID / 닉네임 / 별풍선 수치를 추출한다.
    우선 실제 풍고 row 마크업(<a href="/station/..." class="row">)을 사용하고,
    마크업이 바뀌었을 때만 텍스트 fallback 파서를 사용한다.
    """
    rows: List[Dict[str, Any]] = []
    seen = set()

    # 낙수표 poong_rank_maker에서 쓰는 풍고 방식과 동일 계열 파서.
    for m in re.finditer(r'<a\s+href="/station/([^"/?]+)(?:[^"]*)"\s+class="row">(.*?)</a>\s*</li>', src, re.S | re.I):
        soop_id = html.unescape(m.group(1)).strip()
        body = m.group(2)

        nm = re.search(r'<p\s+class="nick">(.*?)</p>', body, re.S | re.I)
        if not nm:
            continue
        nick = re.sub(r"<.*?>", "", nm.group(1), flags=re.S)
        nick = html.unescape(nick).strip()

        value = None
        active = re.search(r'<div\s+class="cl[^"]*_c\s+active[^"]*"[^>]*>(.*?)</div>', body, re.S | re.I)
        if active:
            active_txt = re.sub(r"<.*?>", " ", active.group(1), flags=re.S)
            nums = re.findall(r"\d[\d,]*", active_txt)
            if nums:
                value = to_int(nums[-1])

        if value is None:
            plain = re.sub(r"<.*?>", " ", body, flags=re.S)
            nums = [to_int(x) for x in re.findall(r"\d[\d,]*", plain)]
            nums = [x for x in nums if x >= 0]
            if nums:
                value = max(nums)

        if not nick or not value:
            continue
        key = (norm_name(soop_id), norm_name(nick), int(value))
        if key in seen:
            continue
        seen.add(key)
        rows.append({
            "i": soop_id,
            "n": nick,
            "b": int(value),
            "rank": 0,
            "source": "poonggo_rank_row",
        })

    if rows:
        return rows

    # fallback: 텍스트 기반 파서. HTML 구조가 깨졌거나 저장 원문만 있을 때 사용.
    text = clean_html_text(src)
    pattern = re.compile(r"(?m)^\s*(?:(\d{1,6})\s+)?(.+?)\s+([0-9][0-9,]*)\s+([0-9][0-9,]*)\s+([0-9][0-9,]*)\s+([0-9][0-9,]*)\s*$")
    for line in text.split("\n"):
        line = line.strip()
        if not line or "받은 별풍선" in line or "별풍선 TOP" in line:
            continue
        m = pattern.match(line)
        if not m:
            continue
        rank, name_part, balloons, hourly, viewers, support_count = m.groups()
        name = strip_category_from_name(name_part)
        value = to_int(balloons)
        if not name or value <= 0 or name in {"닉네임", "순위", "검색결과", "최근검색"}:
            continue
        key = (norm_name(name), value)
        if key in seen:
            continue
        seen.add(key)
        rows.append({
            "i": "",
            "n": name,
            "b": value,
            "rank": to_int(rank),
            "hourly": to_int(hourly),
            "viewers": to_int(viewers),
            "support_count": to_int(support_count),
            "source": "poonggo_text_fallback",
        })
    return rows


def row_name(row: Dict[str, Any]) -> str:
    return safe(row.get("n") or row.get("name") or row.get("nick") or row.get("nickname") or row.get("bjName"))


def row_id(row: Dict[str, Any]) -> str:
    return safe(row.get("i") or row.get("id") or row.get("soop_id") or row.get("station_id"))


def row_value(row: Dict[str, Any]) -> int:
    v = row.get("b")
    if v is None:
        for k in ("balloon", "poong", "star", "value", "total", "cnt", "count"):
            if k in row:
                v = row.get(k)
                break
    return to_int(v)


def member_match_candidates(member: Dict[str, Any]) -> List[str]:
    vals: List[str] = []
    for key in ("match", "soop_id", "id", "name", "display"):
        val = member.get(key)
        if isinstance(val, list):
            vals.extend([safe(x) for x in val if safe(x)])
        elif safe(val):
            vals.append(safe(val))
    aliases = member.get("aliases")
    if isinstance(aliases, list):
        vals.extend([safe(x) for x in aliases if safe(x)])
    return list(dict.fromkeys(vals))


def make_index(rows: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    idx: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        name = row_name(r)
        value = row_value(r)
        if not name or value <= 0:
            continue
        data = {"api_name": name, "value": value, "raw": r}
        keys = [norm_name(name)]
        rid = row_id(r)
        if rid:
            keys.append(norm_name(rid))
        for k in keys:
            if not k:
                continue
            old = idx.get(k)
            if old is None or value > old.get("value", 0):
                idx[k] = data
    return idx


def find_value(member: Dict[str, Any], idx: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    candidates = member_match_candidates(member)

    # 1) match가 있으면 먼저 정확 키만 본다. 엉뚱한 유사 닉 매칭 방지.
    for cand in candidates:
        key = norm_name(cand)
        if key and key in idx:
            out = dict(idx[key])
            out["mode"] = "exact"
            return out

    if safe(member.get("match")):
        return {"api_name": "", "value": 0, "mode": "miss_strict"}

    # 2) match가 없는 멤버만 제한적 포함 매칭 허용.
    cand_keys = [norm_name(c) for c in candidates if norm_name(c)]
    hits: Dict[str, Dict[str, Any]] = {}
    for key, data in idx.items():
        for ck in cand_keys:
            if ck and len(ck) >= 2 and (ck in key or key in ck):
                hits[data.get("api_name", key)] = data
                break
    if len(hits) == 1:
        out = dict(next(iter(hits.values())))
        out["mode"] = "fuzzy"
        return out
    return {"api_name": "", "value": 0, "mode": "miss"}

def detect_last_page(html: str, default_max: int) -> int:
    nums = [to_int(x) for x in re.findall(r"[?&]page=(\d+)", html)]
    nums += [to_int(x) for x in re.findall(r">\s*(\d{1,4})\s*<", html)]
    nums = [n for n in nums if n > 0]
    if not nums:
        return 1
    return max(1, min(max(nums), default_max))


def fetch_poonggo_pages(ctype: str, year: int, month: int, day: int | str | None, tag: str, logs: List[str], members_for_stop: List[Dict[str, Any]] | None = None) -> Tuple[List[Dict[str, Any]], str]:
    max_limit = MAX_MONTHLY_PAGES if ctype == "monthly" else MAX_DAILY_PAGES
    first_url = build_url(ctype, year, month, day, page=1)
    logs.append(f"FETCH {tag}: {first_url}")
    first_html = fetch_text(first_url)
    RAW_DIR.mkdir(exist_ok=True)
    (RAW_DIR / f"{tag}_page_1.html").write_text(first_html, encoding="utf-8")
    last_page = detect_last_page(first_html, max_limit)
    rows = extract_poonggo_rows_from_html(first_html)
    logs.append(f"ROWS {tag}_page_1: {len(rows)} LAST_PAGE={last_page}")

    # 멤버가 전부 매칭되면 조기 종료 가능. 그래도 page1만 보고 끝내지는 않게 2페이지부터 체크.
    def enough(current_rows: List[Dict[str, Any]]) -> bool:
        if not members_for_stop:
            return False
        idx = make_index(current_rows)
        return matched_count(members_for_stop, idx) >= len(members_for_stop)

    for page in range(2, last_page + 1):
        url = build_url(ctype, year, month, day, page=page)
        try:
            html = fetch_text(url)
            if page <= 3 or page == last_page:
                (RAW_DIR / f"{tag}_page_{page}.html").write_text(html, encoding="utf-8")
            page_rows = extract_poonggo_rows_from_html(html)
            logs.append(f"ROWS {tag}_page_{page}: {len(page_rows)}")
            if not page_rows:
                break
            rows.extend(page_rows)
            if page >= 3 and enough(rows):
                logs.append(f"EARLY_STOP {tag}: page={page}")
                break
        except Exception as e:
            logs.append(f"FETCH_FAILED {tag}_page_{page}: {type(e).__name__}: {e}")
            # 한 페이지 실패했다고 전체 중단하지 않는다.
        time.sleep(REQUEST_DELAY)

    # 중복 제거: 같은 닉네임은 큰 값을 우선.
    best: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        k = norm_name(row_name(r))
        if not k:
            continue
        if k not in best or row_value(r) > row_value(best[k]):
            best[k] = r
    out = list(best.values())
    logs.append(f"ROWS {tag}_TOTAL_UNIQUE: {len(out)}")
    if out:
        logs.append(f"SAMPLE {tag}: name={row_name(out[0])} value={row_value(out[0])}")
    return out, first_url

def fetch_chart(ctype: str, year: int, month: int, day: int | str | None, tag: str, logs: List[str], members_for_stop: List[Dict[str, Any]] | None = None) -> Tuple[List[Dict[str, Any]], str]:
    # 풍고는 JSON API가 아니라 HTML 랭킹 페이지를 파싱한다.
    pg_ctype = "monthly" if ctype == "month" else "daily"
    return fetch_poonggo_pages(pg_ctype, year, month, day, tag, logs, members_for_stop=members_for_stop)

def matched_count(members: List[Dict[str, Any]], idx: Dict[str, Dict[str, Any]]) -> int:
    return sum(1 for m in members if find_value(m, idx).get("value", 0) > 0)


def make_rank_card(part: str, members: List[Dict[str, Any]], rank_badge: str) -> Dict[str, Any]:
    # 수장은 일반 부서 랭킹/월평균에서 제외한다.
    part_members = [m for m in members if m.get("part") == part and not is_leader_member(m)]
    part_members.sort(key=lambda x: (x.get("month", 0), x.get("today", 0)), reverse=True)
    max_month = max([m.get("month", 0) for m in part_members] + [1])
    rows = []
    for i, m in enumerate(part_members, 1):
        rows.append({
            "rank": i,
            "name": m.get("name", "-"),
            "today": fmt_num(m.get("today", 0)),
            "month": fmt_num(m.get("month", 0)),
            "width": f"{max(4, int((m.get('month', 0) / max_month) * 100))}%" if m.get("month", 0) else "0%",
            "first": i == 1,
            "color": "#7dc7ff" if part == "엑셀부" else "#ffd34f",
        })
    total = sum(m.get("month", 0) for m in part_members)
    avg = total // len(part_members) if part_members else 0
    leader = part_members[0] if part_members else {}
    return {
        "crew": part,
        "rank_badge": rank_badge,
        "avg": fmt_num(avg),
        "leader": leader.get("name", ""),
        "leader_sales": fmt_num(leader.get("month", 0)) if leader else "-",
        "members": rows,
    }


def make_leader_card(members: List[Dict[str, Any]]) -> Dict[str, Any]:
    leaders = [m for m in members if is_leader_member(m)]
    if not leaders:
        return {"name": "철구형", "today": "0", "month": "0"}
    best = sorted(leaders, key=lambda x: (x.get("month", 0), x.get("today", 0)), reverse=True)[0]
    return {
        "name": best.get("name", "철구형"),
        "today": fmt_num(best.get("today", 0)),
        "month": fmt_num(best.get("month", 0)),
        "soop_id": best.get("soop_id", "y1026"),
    }

def main() -> int:
    logs: List[str] = []
    dt = datetime.now()
    logs.append(f"UPDATED_AT={dt.strftime('%Y-%m-%d %H:%M:%S')}")
    path = Path(INPUT_MEMBERS)
    if not path.exists():
        print(f"[ERROR] {INPUT_MEMBERS} 파일이 없습니다.")
        return 1
    members = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(members, list):
        print("[ERROR] cnine_members.json 최상위는 리스트여야 합니다.")
        return 1
    leaders_for_count, regulars_for_count = split_leader_members(members)
    display_member_count = len(leaders_for_count) + len(regulars_for_count)
    logs.append(f"MEMBERS_RAW={len(members)}")
    logs.append(f"MEMBERS_UNIQUE_DISPLAY={display_member_count} LEADER={len(leaders_for_count)} REGULAR={len(regulars_for_count)}")

    # 매월 1일은 풍투데이 데이터 반영이 늦을 수 있으므로
    # 아래에서 이번 달 데이터만 확인한 뒤, 매칭률이 낮으면 안전한 대기 모드로 출력한다.

    # 월간 데이터는 무조건 현재월을 우선 사용한다.
    # 기존 방식처럼 최근 3개월 중 매칭률이 높은 달을 고르면
    # 월초/신규멤버 반영 시 지난달 데이터가 선택되는 문제가 생긴다.
    # 현재월 매칭이 거의 0건 수준일 때만 과거월을 fallback 후보로 본다.
    month_candidates = []
    month_targets = [("month_current", (dt.year, dt.month))]
    fallback_targets = []
    for back in range(1, 4):
        yy, mm = add_months(dt.year, dt.month, -back)
        fallback_targets.append((f"month_prev_{back}", (yy, mm)))
    for tag, (yy, mm) in month_targets:
        try:
            rows, url = fetch_chart("month", yy, mm, "undefined", tag, logs, members_for_stop=leaders_for_count + regulars_for_count)
            idx = make_index(rows)
            mc = matched_count(leaders_for_count + regulars_for_count, idx)
            logs.append(f"INDEX {tag}: {len(idx)} MATCHED_IF_USED={mc}/{display_member_count}")
            month_candidates.append((mc, len(idx), tag, rows, idx, url, yy, mm))
        except Exception as e:
            logs.append(f"FETCH_FAILED {tag}: {type(e).__name__}: {e}")
        time.sleep(REQUEST_DELAY)

    if not month_candidates:
        print("[ERROR] 현재월 월간 API 수집 실패")
        Path(DEBUG_LOG).write_text("\n".join(logs), encoding="utf-8-sig")
        return 1

    current_mc, current_len, current_tag, current_rows, current_idx, current_url, current_year, current_month = month_candidates[0]
    min_current_match = max(3, int(display_member_count * 0.15))

    if current_mc >= min_current_match or current_len > 0:
        # 현재월 데이터가 일부라도 정상적으로 잡히면 절대 지난달로 바꾸지 않는다.
        best_mc, _, best_tag, month_rows, month_idx, month_url, used_year, used_month = month_candidates[0]
        logs.append(f"MONTH_USED_CURRENT_LOCK={best_tag} {used_year}-{used_month:02d} MATCHED={best_mc}/{display_member_count}")
    else:
        logs.append(f"CURRENT_MONTH_TOO_LOW={current_mc}/{display_member_count}; fallback_check")
        fallback_candidates = []
        for tag, (yy, mm) in fallback_targets:
            try:
                rows, url = fetch_chart("month", yy, mm, "undefined", tag, logs, members_for_stop=leaders_for_count + regulars_for_count)
                idx = make_index(rows)
                mc = matched_count(leaders_for_count + regulars_for_count, idx)
                logs.append(f"INDEX {tag}: {len(idx)} MATCHED_IF_USED={mc}/{display_member_count}")
                fallback_candidates.append((mc, len(idx), tag, rows, idx, url, yy, mm))
            except Exception as e:
                logs.append(f"FETCH_FAILED {tag}: {type(e).__name__}: {e}")
            time.sleep(REQUEST_DELAY)
        if fallback_candidates:
            fallback_candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)
            best_mc, _, best_tag, month_rows, month_idx, month_url, used_year, used_month = fallback_candidates[0]
            logs.append(f"MONTH_USED_FALLBACK={best_tag} {used_year}-{used_month:02d} MATCHED={best_mc}/{display_member_count}")
        else:
            best_mc, _, best_tag, month_rows, month_idx, month_url, used_year, used_month = month_candidates[0]
            logs.append(f"MONTH_USED_EMPTY_CURRENT={best_tag} {used_year}-{used_month:02d} MATCHED={best_mc}/{display_member_count}")

    # 1일에 이번 달 데이터 매칭이 너무 낮으면, 지난달 데이터로 오염시키지 않고 대기 모드 출력.
    # 단, ranking/excel/star 구조는 그대로 유지해서 make_ygosu_c9_dashboard.py가 멈추지 않게 한다.
    if dt.day == 1 and best_mc < max(5, int(display_member_count * 0.5)):
        wait_msg = "월초 집계 반영 대기중입니다. 풍고 1일 데이터 반영 후 자동 갱신됩니다."
        items = []
        for m in (leaders_for_count + regulars_for_count):
            items.append({
                "part": "수장" if is_leader_member(m) else safe(m.get("part")),
                "name": safe(m.get("name")),
                "match": safe(m.get("match")),
                "soop_id": safe(m.get("soop_id") or m.get("id")),
                "today": 0,
                "month": 0,
                "today_api_name": "",
                "month_api_name": "",
                "matched": False,
            })
        result = {
            "updated_at": dt.strftime("%Y-%m-%d %H:%M:%S"),
            "source": "poonggo broadcast ranking HTML v9",
            "month_reset": True,
            "message": wait_msg,
            "used_month": f"{used_year}-{used_month:02d}",
            "api_urls": {"month": month_url, "day": "", "today": ""},
            "total_members": display_member_count,
            "matched_count": 0,
            "unmatched_count": display_member_count,
            "ranking": items,
            "leader": make_leader_card(items),
            "excel": make_rank_card("엑셀부", items, "E"),
            "star": make_rank_card("스타부", items, "S"),
        }
        result["excel"]["message"] = wait_msg
        result["excel"]["month_reset"] = True
        result["star"]["message"] = wait_msg
        result["star"]["month_reset"] = True
        Path(OUTPUT_JSON).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        logs.append("DAY1_WAIT_MODE=True")
        logs.append(wait_msg)
        logs.append(f"MATCHED=0/{display_member_count}")
        Path(DEBUG_LOG).write_text("\n".join(logs), encoding="utf-8-sig")
        print("=" * 60)
        print("완료:", OUTPUT_JSON)
        print("멤버:", display_member_count)
        print("월초 집계 반영 대기중")
        print("디버그:", DEBUG_LOG)
        print("=" * 60)
        return 0

    # 오늘 데이터는 당일 API만 사용. 0건이어도 정상 진행.
    day_idx: Dict[str, Dict[str, Any]] = {}
    today_idx: Dict[str, Dict[str, Any]] = {}
    day_url = today_url = ""
    try:
        day_rows, day_url = fetch_chart("day", dt.year, dt.month, dt.day, "day", logs, members_for_stop=leaders_for_count + regulars_for_count)
        day_idx = make_index(day_rows)
    except Exception as e:
        logs.append(f"DAY_FAILED={type(e).__name__}: {e}")
    try:
        today_rows, today_url = fetch_chart("today", dt.year, dt.month, dt.day, "today", logs, members_for_stop=leaders_for_count + regulars_for_count)
        today_idx = make_index(today_rows)
    except Exception as e:
        logs.append(f"TODAY_FAILED={type(e).__name__}: {e}")

    items = []
    unmatched = []
    for m in (leaders_for_count + regulars_for_count):
        m = dict(m)
        month = find_value(m, month_idx)
        today = find_value(m, today_idx)
        if today.get("value", 0) <= 0:
            today = find_value(m, day_idx)
        item = {
            "part": "수장" if is_leader_member(m) else safe(m.get("part")),
            "name": safe(m.get("name")),
            "match": safe(m.get("match")),
            "soop_id": safe(m.get("soop_id") or m.get("id")),
            "today": int(today.get("value", 0)),
            "month": int(month.get("value", 0)),
            "today_api_name": today.get("api_name", ""),
            "month_api_name": month.get("api_name", ""),
            "matched": bool(month.get("value", 0) or today.get("value", 0)),
        }
        if not item["matched"]:
            unmatched.append(f"{item['part']} / {item['name']} / match={item['match']} / soop_id={item['soop_id']}")
        items.append(item)

    result = {
        "updated_at": dt.strftime("%Y-%m-%d %H:%M:%S"),
        "source": "poonggo broadcast ranking HTML v9",
        "used_month": f"{used_year}-{used_month:02d}",
        "api_urls": {"month": month_url, "day": day_url, "today": today_url},
        "total_members": display_member_count,
        "matched_count": sum(1 for x in items if x["matched"]),
        "unmatched_count": len(unmatched),
        "ranking": sorted(items, key=lambda x: (x["month"], x["today"]), reverse=True),
        "leader": make_leader_card(items),
        "excel": make_rank_card("엑셀부", items, "E"),
        "star": make_rank_card("스타부", items, "S"),
    }
    Path(OUTPUT_JSON).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    logs.append(f"MONTH_INDEX={len(month_idx)}")
    logs.append(f"TODAY_INDEX={len(today_idx)}")
    logs.append(f"MATCHED={result['matched_count']}/{result['total_members']}")
    logs.append("")
    logs.append("UNMATCHED")
    logs.extend(unmatched[:300])
    Path(DEBUG_LOG).write_text("\n".join(logs), encoding="utf-8-sig")

    print("=" * 60)
    print("완료:", OUTPUT_JSON)
    print("멤버:", result["total_members"])
    print("월간 사용:", result["used_month"])
    print("매칭:", result["matched_count"], "/", result["total_members"])
    print("미매칭:", result["unmatched_count"])
    print("디버그:", DEBUG_LOG)
    print("=" * 60)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
