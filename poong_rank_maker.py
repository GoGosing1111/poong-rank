import argparse
import datetime as dt
import html
import json
import os
import re
import unicodedata
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = Path(__file__).resolve().parent
MEMBERS_FILE = BASE_DIR / "members.json"
VALUES_FILE = BASE_DIR / "values.json"
RESULT_TXT = BASE_DIR / "result.txt"
RESULT_HTML = BASE_DIR / "ranking.html"
RESULT_PNG = BASE_DIR / "ranking.png"
UNMATCHED_FILE = BASE_DIR / "unmatched_members.txt"
API_DEBUG_FILE = BASE_DIR / "api_debug.txt"
API_RAW_DIR = BASE_DIR / "api_raw"

POONGGO_RANK_URL = "https://poonggo.com/ranking/broadcast"

HEADERS = {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "referer": "https://poonggo.com/ranking/broadcast?c=monthly&s=b",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
}

def clean_name(s: str) -> str:
    if s is None:
        return ""
    s = unicodedata.normalize("NFKC", str(s))
    s = re.sub(r"[\u2600-\u27BF\U0001F000-\U0001FAFF]", "", s)
    s = s.replace("↑", "").replace("↓", "")
    s = re.sub(r"^\s*\[BJ\]\s*", "", s, flags=re.I)
    s = re.sub(r"BJ", "", s, flags=re.I)
    s = re.sub(r"[\[\]\(\)\{\}♡♥★☆♬♪:._°º˚。~!@#%^&*+=|\\/<>,?`'\"·ㆍ;\-]", "", s)
    s = re.sub(r"\s+", "", s)
    return s.strip().lower()

def strict_name(s: str) -> str:
    """
    하트/특수문자까지 보존한 정확매칭용 키.
    함지아 != 함지아♥ 로 구분해서 다른 BJ가 잡히는 문제를 막는다.
    """
    if s is None:
        return ""
    s = unicodedata.normalize("NFKC", str(s))
    s = s.replace("↑", "").replace("↓", "")
    s = re.sub(r"^\s*\[BJ\]\s*", "", s, flags=re.I)
    s = re.sub(r"^\s*BJ\s*", "", s, flags=re.I)
    s = re.sub(r"\s+", "", s)
    return s.strip().lower()

def display_name(item):
    if isinstance(item, dict):
        return item.get("name") or item.get("display") or item.get("match") or ""
    return str(item)

def match_names(item):
    if isinstance(item, dict):
        names = []
        for key in ("match", "name", "display"):
            val = item.get(key)
            if isinstance(val, list):
                names.extend([str(v) for v in val])
            elif val:
                names.append(str(val))
        aliases = item.get("aliases")
        if isinstance(aliases, list):
            names.extend([str(v) for v in aliases])
        return list(dict.fromkeys(names))
    return [str(item)]

def load_members():
    if not MEMBERS_FILE.exists():
        raise FileNotFoundError("members.json 파일이 없습니다.")
    try:
        return json.loads(MEMBERS_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise SystemExit(f"members.json 문법 오류: {e}")

def normalize_member_structure(members):
    """
    지원 구조:
    1) {"크루": ["BJ", {"name":"표시","match":"실제"}]}
    2) 구버전 {"크루": {"남자": [...], "여자": [...]}}
    """
    normalized = {}
    for crew, value in members.items():
        if isinstance(value, list):
            normalized[crew] = value
        elif isinstance(value, dict):
            merged = []
            for _, arr in value.items():
                if isinstance(arr, list):
                    merged.extend(arr)
            normalized[crew] = merged
        else:
            normalized[crew] = []
    return normalized

def iter_member_items(members):
    for crew, arr in members.items():
        for item in arr:
            yield crew, item, display_name(item), match_names(item)

def flatten_members(members, limit=0):
    out = []
    for row in iter_member_items(members):
        out.append(row)
        if limit and len(out) >= limit:
            break
    return out

def _num(v):
    try:
        return int(re.sub(r"[^0-9]", "", str(v)) or "0")
    except Exception:
        return 0

def _extract_poonggo_rows(text):
    """
    풍고 랭킹 HTML에서 닉네임/SOOP ID/별풍 숫자를 추출한다.
    - /ranking/broadcast?c=monthly&s=b&page=N
    - /ranking/broadcast?c=daily&s=b&page=N
    """
    rows = []
    for m in re.finditer(r'<a\s+href="/station/([^"/?]+)(?:[^"]*)"\s+class="row">(.*?)</a>\s*</li>', text, re.S | re.I):
        soop_id = html.unescape(m.group(1)).strip()
        body = m.group(2)

        nm = re.search(r'<p\s+class="nick">(.*?)</p>', body, re.S | re.I)
        if not nm:
            continue
        nick = re.sub(r"<.*?>", "", nm.group(1), flags=re.S)
        nick = html.unescape(nick).strip()

        val = None
        active = re.search(r'<div\s+class="cl[^"]*_c\s+active[^"]*"[^>]*>(.*?)</div>', body, re.S | re.I)
        if active:
            active_txt = re.sub(r"<.*?>", " ", active.group(1), flags=re.S)
            nums = re.findall(r'\d[\d,]*', active_txt)
            if nums:
                val = _num(nums[-1])

        if val is None:
            # 안전장치: row 안 숫자 중 첫 번째 큰 숫자를 별풍으로 간주
            plain = re.sub(r"<.*?>", " ", body, flags=re.S)
            nums = [_num(x) for x in re.findall(r'\d[\d,]*', plain)]
            nums = [x for x in nums if x >= 0]
            if nums:
                val = max(nums)

        rows.append({"i": soop_id, "n": nick, "b": int(val or 0), "source": "poonggo_rank"})
    return rows

def _request_poonggo_rank(period, page):
    params = {"c": period, "s": "b", "page": page}
    r = requests.get(POONGGO_RANK_URL, params=params, headers=HEADERS, timeout=25)
    r.raise_for_status()
    return r.url, r.status_code, r.text

def request_chart(ctype, year, month, day):
    # 기존 함수명 유지: 다른 코드와의 호환용. 실제 수집은 풍고 랭킹 HTML 기반.
    period = "monthly" if ctype == "month" else "daily"
    return _request_poonggo_rank(period, 1)

def parse_json_loose(text):
    return None

def extract_entries(obj):
    return []

def build_index(entries):
    idx = {}
    raw_count = 0
    for e in entries:
        if not isinstance(e, dict):
            continue
        name = e.get("n") or e.get("name") or e.get("nick") or e.get("nickname") or e.get("bjName")
        if not name:
            continue
        val = e.get("b")
        if val is None:
            for k in ("balloon", "poong", "star", "value", "total", "cnt", "count"):
                if k in e:
                    val = e.get(k)
                    break
        try:
            val = int(str(val).replace(",", ""))
        except Exception:
            continue
        raw_count += 1
        names_to_add = [name]
        if e.get("i"):
            names_to_add.append(str(e.get("i")))
        for nm in names_to_add:
            key = clean_name(nm)
            if not key:
                continue
            old = idx.get(key)
            if old is None or val > old.get("value", 0):
                idx[key] = {"name": str(name), "value": val, "raw": e}
    return idx, raw_count

def find_value(index, item):
    candidates = match_names(item)

    strict_candidates = [strict_name(c) for c in candidates if strict_name(c)]
    for data in index.values():
        api_name = strict_name(data.get("name", ""))
        raw = data.get("raw") or {}
        api_id = strict_name(raw.get("i", "")) if isinstance(raw, dict) else ""
        if api_name in strict_candidates or (api_id and api_id in strict_candidates):
            return data["value"], data["name"], "strict"

    if isinstance(item, dict) and item.get("match"):
        return None, None, "miss_strict"

    for cand in candidates:
        key = clean_name(cand)
        if key in index:
            return index[key]["value"], index[key]["name"], "exact"

    cand_keys = [clean_name(c) for c in candidates if clean_name(c)]
    hits = []
    for key, data in index.items():
        for ck in cand_keys:
            if ck and (ck in key or key in ck):
                hits.append((key, data))
                break
    unique = {}
    for _, d in hits:
        unique[d["name"]] = d
    if len(unique) == 1:
        d = next(iter(unique.values()))
        return d["value"], d["name"], "fuzzy"
    return None, None, "miss"

def fetch_period(label, candidates, year, month, day):
    API_RAW_DIR.mkdir(exist_ok=True)
    debug_lines = []
    period = "monthly" if label == "month" else "daily"
    all_entries = []
    empty_streak = 0
    max_pages = int(os.environ.get("POONGGO_MAX_PAGES", "40"))

    for page in range(1, max_pages + 1):
        safe = f"poonggo_{period}_page{page}"
        try:
            url, status, text = _request_poonggo_rank(period, page)
            (API_RAW_DIR / f"{safe}.html").write_text(text[:800000], encoding="utf-8", errors="ignore")
            entries = _extract_poonggo_rows(text)
            debug_lines.append(f"[{safe}] status={status} url={url}")
            debug_lines.append(f"[{safe}] text_len={len(text)}, entries={len(entries)}")
            if entries:
                all_entries.extend(entries)
                empty_streak = 0
            else:
                empty_streak += 1
                if empty_streak >= 2:
                    break
        except Exception as ex:
            debug_lines.append(f"[{safe}] ERROR {type(ex).__name__}: {ex}")
            empty_streak += 1
            if empty_streak >= 2:
                break

    idx, raw_count = build_index(all_entries)
    debug_lines.append(f"{label}_selected=poonggo_{period}, pages_max={max_pages}, entries={len(all_entries)}, names={raw_count}, normalized={len(idx)}")
    sample = [{k: e.get(k) for k in ("i", "n", "b")} for e in all_entries[:8]]
    debug_lines.append(f"[poonggo_{period}] sample={json.dumps(sample, ensure_ascii=False)[:1200]}")
    return idx, f"poonggo_{period}", debug_lines


def make_values(members, today_idx, month_idx, limit=0):
    values = {}
    unmatched = []
    limited = flatten_members(members, limit)
    allowed = set((crew, display) for crew, item, display, matches in limited)

    for crew, arr in members.items():
        values[crew] = []
        for item in arr:
            display = display_name(item)
            if limit and (crew, display) not in allowed:
                continue
            tv, tmatched, tmode = find_value(today_idx, item)
            mv, mmatched, mmode = find_value(month_idx, item)
            values[crew].append({
                "name": display,
                "today": tv,
                "month": mv,
                "today_match": tmatched,
                "month_match": mmatched,
                "today_mode": tmode,
                "month_mode": mmode,
            })
            if tv is None and mv is None:
                unmatched.append(f"{crew}\t{display}\t미집계")
            elif tv is None:
                unmatched.append(f"{crew}\t{display}\t오늘 미집계 / 월간:{mmatched}")
            elif mv is None:
                unmatched.append(f"{crew}\t{display}\t월간 미집계 / 오늘:{tmatched}")
    return values, unmatched

def fmt(v):
    return "-" if v is None else f"{int(v):,}"

def sum_known(rows, key):
    return sum((r[key] or 0) for r in rows if r[key] is not None)

def write_result_txt(values):
    lines = []
    grand_today = 0
    grand_month = 0
    for crew, rows in values.items():
        sorted_rows = sorted(rows, key=lambda r: (r["month"] is not None, r["month"] or -1, r["today"] or -1), reverse=True)
        crew_today = sum_known(sorted_rows, "today")
        crew_month = sum_known(sorted_rows, "month")
        grand_today += crew_today
        grand_month += crew_month
        lines.append(crew)
        for r in sorted_rows:
            lines.append(f"{r['name']}\t오늘 {fmt(r['today'])}\t월간 {fmt(r['month'])}")
        lines.append(f"합계\t오늘 {fmt(crew_today)}\t월간 {fmt(crew_month)}")
        lines.append("="*42)
    lines.append(f"전체 합계\t오늘 {fmt(grand_today)}\t월간 {fmt(grand_month)}")
    RESULT_TXT.write_text("\n".join(lines), encoding="utf-8")

def font(size, bold=False):
    candidates = [
        "C:/Windows/Fonts/malgunbd.ttf" if bold else "C:/Windows/Fonts/malgun.ttf",
        "C:/Windows/Fonts/NanumGothicBold.ttf" if bold else "C:/Windows/Fonts/NanumGothic.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc" if bold else "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for p in candidates:
        if p and os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()


def draw_3d_text(draw, pos, text, font, fill, shadow=(0,0,0), depth=3):
    x, y = pos
    for i in range(depth, 0, -1):
        draw.text((x+i, y+i), text, font=font, fill=shadow)
    draw.text((x, y), text, font=font, fill=fill)


def draw_ranking(values):
    W = 1500
    margin = 42
    row_h = 34
    card_gap = 26
    header_h = 160
    crew_heights = []
    for crew, rows in values.items():
        h = 120 + max(1, len(rows)) * row_h + 62
        crew_heights.append(h)
    H = header_h + sum(crew_heights) + card_gap * len(crew_heights) + 92

    bg = (6, 7, 10)
    card = (15, 16, 22)
    card2 = (19, 20, 28)
    gold = (244, 203, 100)
    line = (189, 143, 55)
    text = (240, 240, 236)
    muted = (162, 164, 173)
    blue = (130, 192, 255)
    red = (255, 126, 126)

    img = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(img)

    d.rectangle([0,0,W,H], fill=bg)
    d.rounded_rectangle([24,24,W-24,H-24], radius=28, outline=line, width=3)

    f_title = font(52, True)
    f_sub = font(22)
    f_crew = font(32, True)
    f_head = font(21, True)
    f_row = font(21)
    f_rank = font(20, True)
    f_sum = font(24, True)

    now = dt.datetime.now().strftime("%Y.%m.%d %H:%M")
    draw_3d_text(d, (64, 58), "SOOP CREW RANKING", f_title, gold, shadow=(40,25,0), depth=5)
    d.text((68, 120), f"오늘 별풍선 / {dt.datetime.now().month}월 별풍선 · {now} 갱신", font=f_sub, fill=muted)

    y = header_h
    grand_today = grand_month = 0
    for crew, rows in values.items():
        sorted_rows = sorted(rows, key=lambda r: (r["month"] is not None, r["month"] or -1, r["today"] or -1), reverse=True)
        crew_today = sum_known(sorted_rows, "today")
        crew_month = sum_known(sorted_rows, "month")
        grand_today += crew_today
        grand_month += crew_month
        miss = sum(1 for r in sorted_rows if r["today"] is None and r["month"] is None)

        h = 120 + max(1, len(sorted_rows)) * row_h + 62
        x1, y1, x2, y2 = margin, y, W-margin, y+h
        d.rounded_rectangle([x1,y1,x2,y2], radius=20, fill=card, outline=line, width=2)
        d.rectangle([x1+2, y1+2, x2-2, y1+64], fill=(24,22,27))

        draw_3d_text(d, (x1+28, y1+18), crew, f_crew, gold, shadow=(35,25,0), depth=3)
        d.text((x2-470, y1+23), f"오늘 {fmt(crew_today)}", font=f_head, fill=blue)
        d.text((x2-245, y1+23), f"월간 {fmt(crew_month)}", font=f_head, fill=gold)

        hy = y1 + 82
        cols = [x1+32, x1+110, x1+315, x2-470, x2-270, x2-135]
        for label, cx in zip(["순위", "BJ", "게이지", "오늘", "월간", ""], cols):
            d.text((cx, hy), label, font=f_head, fill=muted)

        max_month = max([r["month"] or 0 for r in sorted_rows] + [1])
        max_today = max([r["today"] or 0 for r in sorted_rows] + [1])

        ry = hy + 36
        for i, r in enumerate(sorted_rows, 1):
            if i % 2 == 1:
                d.rectangle([x1+22, ry-5, x2-22, ry+row_h-5], fill=card2)

            rank_fill = gold if i <= 3 else muted
            draw_3d_text(d, (cols[0], ry), str(i), f_rank, rank_fill, shadow=(10,10,12), depth=2)

            name_fill = gold if i <= 3 else text
            draw_3d_text(d, (cols[1], ry), r["name"][:17], f_row, name_fill, shadow=(15,15,18), depth=2)

            # 월간 1위 기준 게이지
            gx, gy = cols[2], ry + 7
            gw, gh = 285, 13
            d.rounded_rectangle([gx, gy, gx+gw, gy+gh], radius=6, fill=(38, 39, 48), outline=(70, 63, 38), width=1)
            ratio = 0 if r["month"] is None else max(0, min(1, (r["month"] or 0) / max_month))
            fill_w = int(gw * ratio)
            if fill_w > 0:
                d.rounded_rectangle([gx, gy, gx+fill_w, gy+gh], radius=6, fill=gold if i <= 3 else blue)

            today_fill = text if r["today"] is not None else red
            month_fill = gold if r["month"] is not None else red
            draw_3d_text(d, (cols[3], ry), fmt(r["today"]), f_row, today_fill, shadow=(12,12,15), depth=2)
            draw_3d_text(d, (cols[4], ry), fmt(r["month"]), f_row, month_fill, shadow=(18,14,5), depth=2)

            ry += row_h

        d.line([x1+24, y2-48, x2-24, y2-48], fill=(73,58,30), width=1)
        d.text((x1+28, y2-36), f"합계  오늘 {fmt(crew_today)}  ·  월간 {fmt(crew_month)}", font=f_sum, fill=gold)
        d.text((x2-180, y2-34), f"미집계 {miss}명", font=font(18), fill=muted)
        y += h + card_gap

    draw_3d_text(d, (W//2-285, H-70), f"전체 오늘 {fmt(grand_today)}    |    전체 월간 {fmt(grand_month)}", font(30, True), gold, shadow=(35,25,0), depth=4)
    img.save(RESULT_PNG)

def write_html(values):
    now = dt.datetime.now().strftime("%Y.%m.%d %H:%M")
    css = """
    body{margin:0;background:#06070a;color:#eee;font-family:Arial,'Malgun Gothic',sans-serif}
    .wrap{max-width:1060px;margin:0 auto;padding:28px}
    .title{border:1px solid #bd8f37;border-radius:18px;padding:24px 26px;margin-bottom:18px;background:linear-gradient(135deg,#17171d,#090a0e)}
    h1{margin:0;color:#f4cb64;font-size:34px;letter-spacing:.5px}.sub{color:#aaa;margin-top:8px}
    .crew{border:1px solid #bd8f37;border-radius:18px;background:#101116;margin:18px 0;overflow:hidden}
    .crew-head{display:flex;justify-content:space-between;align-items:center;background:#18161b;padding:16px 20px}
    .crew-name{color:#f4cb64;font-size:22px;font-weight:800;text-shadow:2px 2px 0 #2a1c00}.sum{color:#ddd;font-weight:700}
    table{width:100%;border-collapse:collapse}th,td{padding:10px 12px;border-bottom:1px solid #292a31}
    th{color:#aaa;text-align:left;font-size:13px}.num{text-align:right;font-variant-numeric:tabular-nums;text-shadow:1px 1px 0 #000}.gold{color:#f4cb64;font-weight:800}.today{color:#8ac0ff}.miss{color:#ff7e7e}
    tr:nth-child(even){background:#14151c}.rank{color:#aaa;width:50px}.top{color:#f4cb64;font-weight:900;text-shadow:2px 2px 0 #2a1c00}
    .bar{height:10px;background:#272932;border-radius:10px;overflow:hidden;min-width:150px}.bar span{display:block;height:10px;background:linear-gradient(90deg,#8ac0ff,#f4cb64);border-radius:10px}
    """
    parts = [f"<html><head><meta charset='utf-8'><style>{css}</style></head><body><div class='wrap'>"]
    parts.append(f"<div class='title'><h1>SOOP CREW RANKING</h1><div class='sub'>오늘 별풍선 / {dt.datetime.now().month}월 별풍선 · {now} 갱신</div></div>")
    for crew, rows in values.items():
        sorted_rows = sorted(rows, key=lambda r: (r["month"] is not None, r["month"] or -1, r["today"] or -1), reverse=True)
        st, sm = sum_known(sorted_rows, "today"), sum_known(sorted_rows, "month")
        parts.append(f"<div class='crew'><div class='crew-head'><div class='crew-name'>{crew}</div><div class='sum'>오늘 {fmt(st)} · 월간 {fmt(sm)}</div></div>")
        parts.append("<table><tr><th>순위</th><th>BJ</th><th>게이지</th><th class='num'>오늘</th><th class='num'>월간</th><th>매칭</th></tr>")
        max_month = max([r["month"] or 0 for r in sorted_rows] + [1])
        for i,r in enumerate(sorted_rows,1):
            cls = "top" if i <= 3 else ""
            match = r.get("today_match") or r.get("month_match") or "-"
            today_cls = "today num" if r["today"] is not None else "miss num"
            month_cls = "gold num" if r["month"] is not None else "miss num"
            pct = 0 if r["month"] is None else int(max(0, min(100, (r["month"] or 0) / max_month * 100)))
            parts.append(f"<tr><td class='rank {cls}'>{i}</td><td class='{cls}'>{r['name']}</td><td><div class='bar'><span style='width:{pct}%'></span></div></td><td class='{today_cls}'>{fmt(r['today'])}</td><td class='{month_cls}'>{fmt(r['month'])}</td><td>{match}</td></tr>")
        parts.append("</table></div>")
    parts.append("</div></body></html>")
    RESULT_HTML.write_text("\n".join(parts), encoding="utf-8")


# ============================================================
# V21 OUTPUT OVERRIDE
# 기준: 사용자가 업로드한 crew_ranking_v18.html 카드형 디자인
# - 기존 API 데이터 수집/매칭 기능 유지
# - ranking.html: 업로드 HTML 디자인 기반
# - ranking.png: 같은 카드형 스타일로 PIL 출력
# - 대표 BJ는 수장으로 분리
# - 개인 랭킹 게이지는 대표 BJ 제외 후 1위 기준
# - 숫자와 닉네임 사이 원형 이미지 없음
# ============================================================

# ============================================================
# STARCREW MODE
# - members.json 각 크루 배열의 첫 번째 멤버를 "수장"으로 처리
# - 수장은 카드 상단 별도 칸에 표시
# - 수장은 멤버 랭킹/게이지/월간 월간 평균 별풍선 계산에서 제외
# - 풍고 랭킹 HTML 매칭 로직 사용
# ============================================================
STARCREW_LEADER_SEPARATE = True

CREW_SALES_NAMES = set()
CREW_SALES_CLEAN = set()

def _is_crew_sales_row(row):
    return False

def _split_rows_v21(rows):
    normal = list(rows)
    normal.sort(key=lambda r: (r["month"] is not None, r["month"] or -1, r["today"] or -1), reverse=True)
    return normal, []

def _sum_v21(rows, key):
    return sum((r.get(key) or 0) for r in rows)

def _prepare_crews_v21(values):
    themes = ["green", "pink", "cyan", "blue", "purple", "orange"]
    prepared = []
    for crew, rows in values.items():
        rows = list(rows)

        # 스타크루 기준: members.json에서 각 크루 첫 번째 멤버를 수장으로 분리한다.
        # 수장은 상단 별도 칸에 표시하고, 멤버 순위/게이지/월 평균 계산에서는 제외한다.
        if STARCREW_LEADER_SEPARATE and rows:
            leaders = [rows[0]]
            normal = rows[1:]
        else:
            normal, leaders = _split_rows_v21(rows)

        normal.sort(key=lambda r: (r["month"] is not None, r["month"] or -1, r["today"] or -1), reverse=True)
        leaders.sort(key=lambda r: (r["month"] is not None, r["month"] or -1, r["today"] or -1), reverse=True)

        personal_month = _sum_v21(normal, "month")
        personal_today = _sum_v21(normal, "today")
        leader_month = _sum_v21(leaders, "month")
        leader_today = _sum_v21(leaders, "today")
        avg = int(personal_month / len(normal)) if normal else 0
        prepared.append({
            "crew": crew,
            "normal": normal,
            "sales": leaders,          # 기존 출력부 호환용: sales 자리에 수장 보관
            "personal_month": personal_month,
            "personal_today": personal_today,
            "sales_month": leader_month,
            "sales_today": leader_today,
            "avg": avg,
        })
    # 크루 순서: 수장을 제외한 멤버 월간 월간 평균 별풍선(avg) 높은 순
    prepared.sort(key=lambda c: c["avg"], reverse=True)
    for i, c in enumerate(prepared):
        c["theme"] = themes[i % len(themes)]
        c["rank"] = i + 1
    return prepared

def write_html(values):
    crews = _prepare_crews_v21(values)
    theme_color = {
        "green": "#2fff58",
        "pink": "#ff5b9d",
        "cyan": "#35f5ff",
        "blue": "#4f68ff",
        "purple": "#bd6cff",
        "orange": "#ffad3d",
    }
    top_css = {
        "green": "linear-gradient(135deg,#00ff44,#10351a)",
        "pink": "linear-gradient(135deg,#ff2c7c,#401325)",
        "cyan": "linear-gradient(135deg,#24f3ff,#143d46)",
        "blue": "linear-gradient(135deg,#304dff,#11194f)",
        "purple": "linear-gradient(135deg,#a83dff,#27153f)",
        "orange": "linear-gradient(135deg,#ff961f,#3e2410)",
    }

    cards = []
    for c in crews:
        color = theme_color[c["theme"]]
        max_month = max([r["month"] or 0 for r in c["normal"]] + [1])
        sales_label = fmt(c["sales_month"])
        sales_names = ", ".join([r["name"] for r in c["sales"]]) if c["sales"] else "수장 없음"

        rows_html = []
        for idx, r in enumerate(c["normal"], start=1):
            pct = 0 if r["month"] is None else int(max(0, min(100, (r["month"] or 0) / max_month * 100)))
            first = " first" if idx == 1 else ""
            score = fmt(r["month"])
            rows_html.append(f"""
<div class="row{first}" style="--w:{pct}%;--c:{color};">
  <div class="rank">{idx}</div>
  <div class="name">{r["name"]}</div>
  <div class="score">{score}</div>
</div>
""")

        cards.append(f"""
<div class="card {c["theme"]}">
  <div class="rank-badge">{c["rank"]}</div>
  <div class="top" style="background:{top_css[c["theme"]]}">
    <div class="crew-title">{c["crew"]}</div>
    <div class="avg-label">월간 평균 별풍선</div>
    <div class="avg-num">{fmt(c["avg"])}</div>
  </div>
  <div class="sales">
    <span>👑 수장</span>
    <span>{sales_label}</span>
  </div>
  <div class="sales-sub">{sales_names}</div>
  {''.join(rows_html)}
</div>
""")

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Poong Rank Maker V21</title>
<style>
body{{
margin:0;
background:#070812;
font-family:Pretendard,'Malgun Gothic','Noto Sans KR',sans-serif;
color:white;
}}
.wrap{{
width:1060px;
margin:auto;
padding:14px;
display:grid;
grid-template-columns:repeat(4,1fr);
gap:16px;
}}
.card{{
position:relative;
background:#11121d;
border-radius:16px;
overflow:hidden;
border:1px solid rgba(255,255,255,.08);
box-shadow:0 15px 35px rgba(0,0,0,.5);
}}
.rank-badge{{
position:absolute;
top:0;
left:0;
width:38px;
height:38px;
display:flex;
align-items:center;
justify-content:center;
font-size:19px;
font-weight:1000;
z-index:3;
color:#fff;
text-shadow:0 2px 0 rgba(0,0,0,.55),0 0 10px rgba(255,255,255,.4);
clip-path:polygon(0 0,100% 0,100% 72%,72% 100%,0 100%);
background:rgba(255,255,255,.18);
}}
.top{{
height:116px;
padding:20px;
font-weight:900;
font-size:28px;
text-align:right;
}}
.crew-title{{
font-size:28px;
font-weight:1000;
white-space:nowrap;
overflow:hidden;
text-overflow:ellipsis;
text-shadow:0 1px 0 rgba(255,255,255,.45),0 3px 0 rgba(0,0,0,.75),0 0 12px rgba(255,255,255,.25);
}}
.avg-label{{
font-size:12px;
margin-top:14px;
color:#e7ecff;
font-weight:900;
text-shadow:0 2px 0 rgba(0,0,0,.65);
}}
.avg-num{{
font-size:32px;
line-height:1.15;
font-weight:1000;
text-shadow:0 1px 0 rgba(255,255,255,.32),0 3px 0 rgba(0,0,0,.78),0 0 13px currentColor;
}}
.green .avg-num{{color:#36ff4f}}
.pink .avg-num{{color:#ff5c9c}}
.cyan .avg-num{{color:#35f8ff}}
.blue .avg-num{{color:#4d67ff}}
.purple .avg-num{{color:#bd6cff}}
.orange .avg-num{{color:#ffad3d}}
.sales{{
padding:12px 18px;
background:#1b1a17;
color:#ffd34f;
font-weight:900;
display:flex;
justify-content:space-between;
text-shadow:0 2px 0 rgba(0,0,0,.75),0 0 10px rgba(255,210,74,.35);
}}
.sales-sub{{
height:22px;
padding:3px 18px 0;
background:#171612;
color:#bda870;
font-size:11px;
font-weight:800;
white-space:nowrap;
overflow:hidden;
text-overflow:ellipsis;
border-bottom:1px solid rgba(255,255,255,.06);
}}
.row{{
position:relative;
display:flex;
align-items:center;
gap:10px;
padding:12px 14px;
border-bottom:1px solid rgba(255,255,255,.06);
font-weight:800;
overflow:hidden;
}}
.row:after{{
content:"";
position:absolute;
left:0;
bottom:0;
height:4px;
width:var(--w);
background:linear-gradient(90deg,var(--c),white);
box-shadow:0 0 10px var(--c);
}}
.rank{{
width:24px;
height:22px;
border-radius:7px;
display:flex;
align-items:center;
justify-content:center;
background:rgba(255,255,255,.1);
color:#a7aec5;
font-size:12px;
font-weight:1000;
text-shadow:0 1px 0 #000;
}}
.name{{
flex:1;
min-width:0;
white-space:nowrap;
overflow:hidden;
text-overflow:ellipsis;
font-size:15px;
font-weight:1000;
text-shadow:0 1px 0 rgba(255,255,255,.28),0 2px 0 rgba(0,0,0,.85),0 0 8px rgba(255,255,255,.22);
}}
.score{{
font-size:18px;
font-weight:1000;
text-shadow:0 1px 0 rgba(255,255,255,.2),0 2px 0 rgba(0,0,0,.85),0 0 10px currentColor;
}}
.first{{
height:70px;
font-size:20px;
background:rgba(255,255,255,.03);
}}
.first .score{{color:var(--c)}}
.first .name{{font-size:17px}}
@media(max-width:1100px){{
.wrap{{width:100%;grid-template-columns:repeat(2,1fr)}}
}}
@media(max-width:620px){{
.wrap{{grid-template-columns:1fr}}
}}
</style>
</head>
<body>
<div class="wrap">
{''.join(cards)}
</div>
</body>
</html>"""
    RESULT_HTML.write_text(html, encoding="utf-8")

def _round(d, xy, r, fill, outline=None, width=1):
    d.rounded_rectangle(xy, radius=r, fill=fill, outline=outline, width=width)

def _text_right_v21(d, x, y, txt, fnt, fill):
    txt = str(txt)
    b = d.textbbox((0, 0), txt, font=fnt)
    d.text((x - (b[2] - b[0]), y), txt, font=fnt, fill=fill)

def _fit_text_v21(d, txt, fnt, max_w):
    txt = str(txt)
    if d.textbbox((0, 0), txt, font=fnt)[2] <= max_w:
        return txt
    while txt and d.textbbox((0, 0), txt + "…", font=fnt)[2] > max_w:
        txt = txt[:-1]
    return txt + "…"

def _draw_grad_h(d, x1, y1, x2, y2, c1, c2):
    x1=int(x1);y1=int(y1);x2=int(x2);y2=int(y2)
    for x in range(x1, max(x1+1,x2)):
        t=(x-x1)/max(1,(x2-x1))
        col=tuple(int(c1[i]*(1-t)+c2[i]*t) for i in range(3))
        d.line([(x,y1),(x,y2)], fill=col)

def draw_ranking(values):
    crews = _prepare_crews_v21(values)

    card_w = 250
    gap = 16
    margin = 8
    top_h = 116
    sales_h = 42
    sales_sub_h = 22
    row_h = 53
    first_h = 70

    max_rows = max([len(c["normal"]) for c in crews] + [1])
    card_h = top_h + sales_h + sales_sub_h + first_h + max(0, max_rows-1) * row_h
    W = margin*2 + len(crews)*card_w + max(0,len(crews)-1)*gap
    H = margin*2 + card_h

    bg = (7, 8, 18)
    panel = (17, 18, 29)
    line = (42, 44, 58)
    gold = (255, 211, 79)
    white = (255, 255, 255)
    muted = (167, 174, 197)
    themes = {
        "green": ((0,255,68),(16,53,26),(47,255,88),(54,255,79)),
        "pink": ((255,44,124),(64,19,37),(255,91,157),(255,92,156)),
        "cyan": ((36,243,255),(20,61,70),(53,245,255),(53,248,255)),
        "blue": ((48,77,255),(17,25,79),(79,104,255),(77,103,255)),
        "purple": ((168,61,255),(39,21,63),(189,108,255),(189,108,255)),
        "orange": ((255,150,31),(62,36,16),(255,173,61),(255,173,61)),
    }

    img = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(img)

    f_crew = font(28, True)
    f_label = font(12, True)
    f_avg = font(32, True)
    f_sales = font(14, True)
    f_sales_sub = font(11, True)
    f_rank = font(12, True)
    f_name = font(15, True)
    f_name_first = font(17, True)
    f_score = font(18, True)
    f_badge = font(19, True)

    for ci, c in enumerate(crews):
        x = margin + ci * (card_w + gap)
        y = margin
        theme = themes[c["theme"]]
        t1, t2, accent, avg_col = theme

        _round(d, [x, y, x+card_w, y+card_h], 16, panel, outline=(38,39,52), width=1)

        # top gradient
        _draw_grad_h(d, x, y, x+card_w, y+top_h, t1, t2)
        # rank badge
        d.polygon([(x,y),(x+38,y),(x+38,y+27),(x+27,y+38),(x,y+38)], fill=(255,255,255))
        d.polygon([(x+1,y+1),(x+37,y+1),(x+37,y+26),(x+26,y+37),(x+1,y+37)], fill=t1)
        d.text((x+13, y+7), str(c["rank"]), font=f_badge, fill=white)

        crew_text = _fit_text_v21(d, c["crew"], f_crew, 160)
        _text_right_v21(d, x+card_w-18, y+20, crew_text, f_crew, white)
        _text_right_v21(d, x+card_w-18, y+62, "월간 평균 별풍선", f_label, (231,236,255))
        _text_right_v21(d, x+card_w-18, y+78, fmt(c["avg"]), f_avg, avg_col)

        sy = y + top_h
        d.rectangle([x, sy, x+card_w, sy+sales_h], fill=(27,26,23))
        d.text((x+18, sy+13), "👑 수장", font=f_sales, fill=gold)
        _text_right_v21(d, x+card_w-18, sy+13, fmt(c["sales_month"]), f_sales, gold)

        ssy = sy + sales_h
        d.rectangle([x, ssy, x+card_w, ssy+sales_sub_h], fill=(23,22,18))
        sales_names = ", ".join([r["name"] for r in c["sales"]]) if c["sales"] else "수장 없음"
        d.text((x+18, ssy+4), _fit_text_v21(d, sales_names, f_sales_sub, card_w-36), font=f_sales_sub, fill=(189,168,112))

        rows_y = ssy + sales_sub_h
        max_month = max([r["month"] or 0 for r in c["normal"]] + [1])

        for ri, r in enumerate(c["normal"], start=1):
            rh = first_h if ri == 1 else row_h
            ry = rows_y + (first_h if ri > 1 else 0) + max(0, ri-2)*row_h
            if ri == 1:
                d.rectangle([x, ry, x+card_w, ry+rh], fill=(22,23,34))
            else:
                d.rectangle([x, ry, x+card_w, ry+rh], fill=panel if ri % 2 == 0 else (15,16,26))
            d.line([x, ry+rh-1, x+card_w, ry+rh-1], fill=(34,35,47))

            if ri == 1:
                d.text((x+14, ry+24), str(ri), font=f_rank, fill=muted)
                d.text((x+45, ry+23), _fit_text_v21(d, r["name"], f_name_first, 95), font=f_name_first, fill=white)
                _text_right_v21(d, x+card_w-16, ry+23, fmt(r["month"]), f_score, accent)
            else:
                d.rounded_rectangle([x+14, ry+16, x+38, ry+38], radius=7, fill=(35,36,49))
                _text_right_v21(d, x+31, ry+20, str(ri), f_rank, muted)
                d.text((x+48, ry+16), _fit_text_v21(d, r["name"], f_name, 93), font=f_name, fill=white)
                _text_right_v21(d, x+card_w-16, ry+16, fmt(r["month"]), f_score, (235,241,255))

            # bottom gauge
            pct = 0 if r["month"] is None else max(0, min(1, (r["month"] or 0) / max_month))
            fill_w = int((card_w-20) * pct)
            gy = ry + rh - 4
            d.rectangle([x, gy, x+card_w, gy+3], fill=(25,26,34))
            if fill_w > 0:
                _draw_grad_h(d, x, gy, x+fill_w, gy+3, accent, white)

    img.save(RESULT_PNG)



# ============================================================
# V22 OUTPUT OVERRIDE
# 기준: v21 카드형 디자인 + 3열 레이아웃 + 크루별 로고 이미지
# - 기존 API 데이터 수집/매칭 기능 유지
# - ranking.html / ranking.png 모두 로고 반영
# - 로고 파일 위치: assets/crew_logos/
# ============================================================

CREW_LOGO_DIR = BASE_DIR / "assets" / "crew_logos"

def _logo_map_v22():
    files = {}
    if CREW_LOGO_DIR.exists():
        for p in CREW_LOGO_DIR.iterdir():
            if p.is_file() and p.suffix.lower() in [".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"]:
                files[clean_name(p.stem)] = p
    result = {}
    aliases = {
        "광우상사": ["광우상사"],
        "씨나인엑셀": ["씨나인엑셀부", "씨나인엑셀", "씨나인"],
        "씨나인스타": ["씨나인스타부", "씨나인스타"],
        "YXL": ["YXL"],
        "정선컴퍼니": ["정선컴퍼니"],
        "이노레이블": ["이노레이블"],
    }
    for crew, names in aliases.items():
        for n in names:
            k = clean_name(n)
            if k in files:
                result[crew] = files[k]
                break
    return result

def _crew_logo_path_v22(crew):
    lm = _logo_map_v22()
    if crew in lm:
        return lm[crew]

    ck = clean_name(crew)
    for k, p in lm.items():
        if clean_name(k) == ck:
            return p

    if CREW_LOGO_DIR.exists():
        for p in CREW_LOGO_DIR.iterdir():
            if p.is_file() and clean_name(p.stem) in ck:
                return p

    # GitHub 실제 파일명 기준 고정 매핑.
    logo_urls = {
        "광우상사": "https://keyman1335-maker.github.io/poong-rank/assets/crew_logos/%EA%B4%91%EC%9A%B0%EC%83%81%EC%82%AC.png",
        "씨나인엑셀": "https://keyman1335-maker.github.io/poong-rank/assets/crew_logos/%EC%94%A8%EB%82%98%EC%9D%B8%EC%97%91%EC%85%80%EB%B6%80.png",
        "씨나인엑셀부": "https://keyman1335-maker.github.io/poong-rank/assets/crew_logos/%EC%94%A8%EB%82%98%EC%9D%B8%EC%97%91%EC%85%80%EB%B6%80.png",
        "씨나인스타": "https://keyman1335-maker.github.io/poong-rank/assets/crew_logos/%EC%94%A8%EB%82%98%EC%9D%B8%EC%8A%A4%ED%83%80%EB%B6%80.png",
        "씨나인스타부": "https://keyman1335-maker.github.io/poong-rank/assets/crew_logos/%EC%94%A8%EB%82%98%EC%9D%B8%EC%8A%A4%ED%83%80%EB%B6%80.png",
        "YXL": "https://keyman1335-maker.github.io/poong-rank/assets/crew_logos/YXL.gif",
        "정선컴퍼니": "https://keyman1335-maker.github.io/poong-rank/assets/crew_logos/%EC%A0%95%EC%84%A0%EC%BB%B4%ED%8D%BC%EB%8B%88.png",
        "이노레이블": "https://keyman1335-maker.github.io/poong-rank/assets/crew_logos/%EC%9D%B4%EB%85%B8%EB%A0%88%EC%9D%B4%EB%B8%94.gif",
        "더케이": "https://keyman1335-maker.github.io/poong-rank/assets/crew_logos/%EB%8D%94%EC%BC%80%EC%9D%B4.png",
        "GD컴퍼니": "https://keyman1335-maker.github.io/poong-rank/assets/crew_logos/GD%EC%BB%B4%ED%8D%BC%EB%8B%88.gif",
        "771": "https://keyman1335-maker.github.io/poong-rank/assets/crew_logos/771.png",
        "쇼케이": "https://keyman1335-maker.github.io/poong-rank/assets/crew_logos/%EC%87%BC%EC%BC%80%EC%9D%B4.png",
        "판타지유": "https://keyman1335-maker.github.io/poong-rank/assets/crew_logos/%ED%8C%90%ED%83%80%EC%A7%80%EC%9C%A02.png",
        "문에이": "https://keyman1335-maker.github.io/poong-rank/assets/crew_logos/%EB%AC%B8%EC%97%90%EC%9D%B4.png",
    }
    if crew in logo_urls:
        return logo_urls[crew]

    for name, url in logo_urls.items():
        if clean_name(name) == ck:
            return url

    return None

def _safe_img_src_v22(path):
    if not path:
        return ""
    raw = str(path)
    if raw.lower().startswith(("http://", "https://")):
        return raw
    try:
        return Path(path).relative_to(BASE_DIR).as_posix()
    except Exception:
        return raw.replace(chr(92), "/")

def write_html(values):
    now = dt.datetime.now().strftime('%Y-%m-%d %H:%M')
    crews = _prepare_crews_v21(values)
    theme_color = {
        "green": "#2fff58",
        "pink": "#ff5b9d",
        "cyan": "#35f5ff",
        "blue": "#4f68ff",
        "purple": "#bd6cff",
        "orange": "#ffad3d",
    }
    top_css = {
        "green": "linear-gradient(135deg,#00ff44,#10351a)",
        "pink": "linear-gradient(135deg,#ff2c7c,#401325)",
        "cyan": "linear-gradient(135deg,#24f3ff,#143d46)",
        "blue": "linear-gradient(135deg,#304dff,#11194f)",
        "purple": "linear-gradient(135deg,#a83dff,#27153f)",
        "orange": "linear-gradient(135deg,#ff961f,#3e2410)",
    }

    css = """
body{
margin:0;
background:#070812;
font-family:Pretendard,'Malgun Gothic','Noto Sans KR',sans-serif;
color:white;
}

.update-time{
width:1180px;
margin:10px auto 0;
text-align:center;
font-size:12px;
font-weight:900;
color:#bda870;
text-shadow:0 2px 0 #000;
}
.wrap{
width:1180px;
margin:auto;
padding:14px;
display:grid;
grid-template-columns:repeat(3,1fr);
gap:16px;
}
.card{
position:relative;
background:#11121d;
border-radius:16px;
overflow:hidden;
border:1px solid rgba(255,255,255,.08);
box-shadow:0 15px 35px rgba(0,0,0,.5);
}
.rank-badge{
position:absolute;
top:0;
left:0;
width:38px;
height:38px;
display:flex;
align-items:center;
justify-content:center;
font-size:19px;
font-weight:1000;
z-index:3;
color:#fff;
text-shadow:0 2px 0 rgba(0,0,0,.55),0 0 10px rgba(255,255,255,.4);
clip-path:polygon(0 0,100% 0,100% 72%,72% 100%,0 100%);
background:rgba(255,255,255,.18);
}
.top{
height:126px;
padding:18px 20px;
font-weight:900;
font-size:28px;
display:flex;
gap:16px;
align-items:center;
}
.crew-logo{
width:104px;
height:76px;
border-radius:10px;
object-fit:contain;
background:transparent;
padding:2px;
flex:0 0 auto;
filter:drop-shadow(0 0 10px rgba(255,255,255,.18));
}
.logo-empty{opacity:.2;}
.crew-info{
flex:1;
min-width:0;
text-align:right;
}
.crew-title{
font-size:34px;
font-weight:1000;
white-space:nowrap;
overflow:hidden;
text-overflow:ellipsis;
text-shadow:0 1px 0 rgba(255,255,255,.45),0 3px 0 rgba(0,0,0,.75),0 0 12px rgba(255,255,255,.25);
}
.avg-label{
font-size:12px;
margin-top:12px;
color:#e7ecff;
font-weight:900;
text-shadow:0 2px 0 rgba(0,0,0,.65);
}
.avg-num{
font-size:40px;
line-height:1.15;
font-weight:1000;
text-shadow:0 1px 0 rgba(255,255,255,.32),0 3px 0 rgba(0,0,0,.78),0 0 13px currentColor;
}
.green .avg-num{color:#36ff4f}
.pink .avg-num{color:#ff5c9c}
.cyan .avg-num{color:#35f8ff}
.blue .avg-num{color:#4d67ff}
.purple .avg-num{color:#bd6cff}
.orange .avg-num{color:#ffad3d}
.sales{
padding:12px 18px;
background:#1b1a17;
color:#ffd34f;
font-weight:900;
display:flex;
justify-content:space-between;
text-shadow:0 2px 0 rgba(0,0,0,.75),0 0 10px rgba(255,210,74,.35);
}
.sales-sub{
height:22px;
padding:3px 18px 0;
background:#171612;
color:#bda870;
font-size:11px;
font-weight:800;
white-space:nowrap;
overflow:hidden;
text-overflow:ellipsis;
border-bottom:1px solid rgba(255,255,255,.06);
}
.col-head{
height:24px;
display:flex;
align-items:center;
gap:8px;
padding:0 12px;
background:#0b0d16;
border-bottom:1px solid rgba(255,255,255,.08);
box-sizing:border-box;
font-size:10px;
font-weight:1000;
letter-spacing:-0.3px;
text-shadow:0 1px 0 #000;
}
.h-rank{
width:24px;
flex:0 0 24px;
text-align:center;
color:#7f879e;
}
.h-name{
flex:1 1 auto;
min-width:0;
text-align:left;
color:#9da6bf;
}

.h-today{
width:72px;
flex:0 0 72px;
text-align:right;
color:#ffd34f;
}
.today-mini{
width:72px;
flex:0 0 72px;
text-align:right;
font-size:15px;
font-weight:1000;
letter-spacing:-0.4px;
color:#ffd34f;
white-space:nowrap;
font-variant-numeric:tabular-nums;
text-shadow:0 1px 0 rgba(255,255,255,.18),0 3px 0 rgba(0,0,0,.95),0 0 10px rgba(255,211,79,.35);
}

.h-month{
width:120px;
flex:0 0 120px;
text-align:right;
color:#dfe6ff;
}
.row{
position:relative;
display:flex;
align-items:center;
gap:8px;
padding:10px 12px;
border-bottom:1px solid rgba(255,255,255,.06);
font-weight:800;
overflow:hidden;
}
.row:after{
content:"";
position:absolute;
left:0;
bottom:0;
height:4px;
width:var(--w);
background:linear-gradient(90deg,var(--c),white);
box-shadow:0 0 10px var(--c);
}
.rank{
width:24px;
height:22px;
flex:0 0 24px;
border-radius:7px;
display:flex;
align-items:center;
justify-content:center;
background:rgba(255,255,255,.1);
color:#a7aec5;
font-size:12px;
font-weight:1000;
text-shadow:0 1px 0 #000;
}
.name{
flex:1 1 auto;
min-width:0;
white-space:nowrap;
overflow:hidden;
text-overflow:ellipsis;
font-size:17px;
font-weight:1000;
letter-spacing:-0.4px;
text-align:left;
text-shadow:0 1px 0 rgba(255,255,255,.35),0 3px 0 rgba(0,0,0,.95),0 0 10px rgba(255,255,255,.28);
}
.score{
width:120px;
flex:0 0 120px;
text-align:right;
font-size:19px;
font-weight:1000;
letter-spacing:-0.5px;
white-space:nowrap;
font-variant-numeric:tabular-nums;
text-shadow:0 1px 0 rgba(255,255,255,.28),0 3px 0 rgba(0,0,0,.95),0 0 12px currentColor;
}
.score span{
display:none;
}
.first{
height:58px;
font-size:20px;
background:rgba(255,255,255,.03);
}
.first .name{
font-size:20px;
}
.first .today-mini,
.first .score{
display:flex;
flex-direction:column;
align-items:flex-end;
justify-content:center;
gap:2px;
line-height:1.05;
}
.first .today-mini{
font-size:15px;
color:#ffd34f;
}
.first .score{
font-size:18px;
color:var(--c);
}
/* 1등 칸 내부 라벨 제거: 헤더의 오늘/월간만 사용 */
@media(max-width:1100px){
.wrap{width:100%;grid-template-columns:repeat(2,1fr)}
}
@media(max-width:620px){
.wrap{grid-template-columns:1fr}
.row{gap:6px;padding:9px 8px}
.name{font-size:16px}
.first .name{font-size:18px}
.today-mini,.h-today{width:62px;flex-basis:62px;font-size:13px}
.score,.h-month{width:108px;flex-basis:108px;font-size:17px}
.first .today-mini{font-size:13px}
.first .score{font-size:16px}
}
"""

    cards = []
    for c in crews:
        color = theme_color[c["theme"]]
        max_month = max([r["month"] or 0 for r in c["normal"]] + [1])
        sales_label = fmt(c["sales_month"])
        sales_names = ", ".join([r["name"] for r in c["sales"]]) if c["sales"] else "수장 없음"
        logo = _crew_logo_path_v22(c["crew"])
        logo_src = _safe_img_src_v22(logo)
        if logo_src:
            logo_html = '<img class="crew-logo" src="' + logo_src + '" />'
        else:
            logo_html = '<div class="crew-logo logo-empty"></div>'

        rows_html = []
        for idx, r in enumerate(c["normal"], start=1):
            pct = 0 if r["month"] is None else int(max(0, min(100, (r["month"] or 0) / max_month * 100)))
            today_val = fmt(r["today"])
            month_val = fmt(r["month"])

            if idx == 1:
                rows_html.append(
                    '<div class="row first" style="--w:' + str(pct) + '%;--c:' + color + ';">\n'
                    '  <div class="rank">1</div>\n'
                    '  <div class="name">' + str(r["name"]) + '</div>\n'
                    '  <div class="today-mini first-today">' + today_val + '</div>\n'
                    '  <div class="score first-month">' + month_val + '</div>\n'
                    '</div>\n'
                )
            else:
                rows_html.append(
                    '<div class="row" style="--w:' + str(pct) + '%;--c:' + color + ';">\n'
                    '  <div class="rank">' + str(idx) + '</div>\n'
                    '  <div class="name">' + str(r["name"]) + '</div>\n'
                    '  <div class="today-mini">' + today_val + '</div>\n'
                    '  <div class="score">' + month_val + '</div>\n'
                    '</div>\n'
                )

        cards.append(
            '<div class="card ' + c["theme"] + '">\n'
            '  <div class="rank-badge">' + str(c["rank"]) + '</div>\n'
            '  <div class="top" style="background:' + top_css[c["theme"]] + '">\n'
            '    ' + logo_html + '\n'
            '    <div class="crew-info">\n'
            '      <div class="crew-title">' + c["crew"] + '</div>\n'
            '      <div class="avg-label">월간 월간 평균 별풍선</div>\n'
            '      <div class="avg-num">' + fmt(c["avg"]) + '</div>\n'
            '    </div>\n'
            '  </div>\n'
            '  <div class="sales">\n'
            '    <span>👑 수장</span>\n'
            '    <span>' + sales_label + '</span>\n'
            '  </div>\n'
            '  <div class="sales-sub">' + sales_names + '</div>\n'
            '  <div class="col-head">\n'
            '    <div class="h-rank">순위</div>\n'
            '    <div class="h-name">멤버</div>\n'
            '    <div class="h-month">월간</div>\n'
            '  </div>\n'
            + ''.join(rows_html) +
            '</div>\n'
        )

    html = (
        '<!DOCTYPE html>\n'
        '<html lang="ko">\n'
        '<head>\n'
        '<meta charset="UTF-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        '<title>Poong Rank Maker V24 Top1 Today</title>\n'
        '<style>\n' + css + '\n</style>\n'
        '</head>\n'
        '<body>\n'
        '<div class="update-time">집계시간: ' + now + '</div>\n'
        '<div class="wrap">\n'
        + ''.join(cards) +
        '</div>\n'
        '</body>\n'
        '</html>'
    )
    RESULT_HTML.write_text(html, encoding="utf-8")

def _open_logo_v22(path, width=104, height=76):
    if not path or not Path(path).exists():
        return None
    try:
        im = Image.open(path).convert("RGBA")
        iw, ih = im.size
        scale = min(width / iw, height / ih)
        nw, nh = int(iw * scale), int(ih * scale)
        im = im.resize((nw, nh), Image.LANCZOS)

        canvas = Image.new("RGBA", (width, height), (0,0,0,0))
        ox = (width - nw) // 2
        oy = (height - nh) // 2
        canvas.paste(im, (ox, oy), im)
        return canvas
    except Exception:
        return None
    try:
        im = Image.open(path).convert("RGBA")
        # GIF first frame is enough
        im.thumbnail((size*2, size*2), Image.LANCZOS)
        canvas = Image.new("RGBA", (size, size), (0,0,0,0))
        # cover crop
        w,h = im.size
        scale = max(size/w, size/h)
        nw,nh = int(w*scale), int(h*scale)
        im = im.resize((nw,nh), Image.LANCZOS)
        crop = im.crop(((nw-size)//2, (nh-size)//2, (nw+size)//2, (nh+size)//2))
        mask = Image.new("L", (size,size), 0)
        md = ImageDraw.Draw(mask)
        md.ellipse([0,0,size-1,size-1], fill=255)
        canvas.paste(crop, (0,0), mask)
        return canvas
    except Exception:
        return None

def draw_ranking(values):
    crews = _prepare_crews_v21(values)

    cols = 3
    card_w = 372
    gap = 16
    margin = 14
    top_h = 126
    sales_h = 42
    sales_sub_h = 22
    row_h = 53
    first_h = 70

    rows_count = (len(crews) + cols - 1) // cols
    max_rows_per_card = max([len(c["normal"]) for c in crews] + [1])
    card_h = top_h + sales_h + sales_sub_h + first_h + max(0, max_rows_per_card-1) * row_h
    W = margin*2 + cols*card_w + (cols-1)*gap
    H = margin*2 + rows_count*card_h + (rows_count-1)*gap

    bg = (7, 8, 18)
    panel = (17, 18, 29)
    gold = (255, 211, 79)
    white = (255, 255, 255)
    muted = (167, 174, 197)
    themes = {
        "green": ((0,255,68),(16,53,26),(47,255,88),(54,255,79)),
        "pink": ((255,44,124),(64,19,37),(255,91,157),(255,92,156)),
        "cyan": ((36,243,255),(20,61,70),(53,245,255),(53,248,255)),
        "blue": ((48,77,255),(17,25,79),(79,104,255),(77,103,255)),
        "purple": ((168,61,255),(39,21,63),(189,108,255),(189,108,255)),
        "orange": ((255,150,31),(62,36,16),(255,173,61),(255,173,61)),
    }

    img = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(img)

    f_crew = font(34, True)
    f_label = font(12, True)
    f_avg = font(38, True)
    f_sales = font(14, True)
    f_sales_sub = font(11, True)
    f_rank = font(12, True)
    f_name = font(18, True)
    f_name_first = font(21, True)
    f_score = font(22, True)
    f_badge = font(19, True)

    for ci, c in enumerate(crews):
        col = ci % cols
        row = ci // cols
        x = margin + col * (card_w + gap)
        y = margin + row * (card_h + gap)
        t1, t2, accent, avg_col = themes[c["theme"]]

        _round(d, [x, y, x+card_w, y+card_h], 16, panel, outline=(38,39,52), width=1)
        _draw_grad_h(d, x, y, x+card_w, y+top_h, t1, t2)

        d.polygon([(x,y),(x+38,y),(x+38,y+27),(x+27,y+38),(x,y+38)], fill=(255,255,255))
        d.polygon([(x+1,y+1),(x+37,y+1),(x+37,y+26),(x+26,y+37),(x+1,y+37)], fill=t1)
        d.text((x+13, y+7), str(c["rank"]), font=f_badge, fill=white)

        logo = _open_logo_v22(_crew_logo_path_v22(c["crew"]), 104, 76)
        lx, ly = x+16, y+24
        if logo:
            img.paste(logo.convert("RGB"), (lx, ly), logo.split()[-1])

        right_x = x + card_w - 18
        crew_text = _fit_text_v21(d, c["crew"], f_crew, 235)
        _text_right_v21(d, right_x, y+20, crew_text, f_crew, white)
        _text_right_v21(d, right_x, y+64, "월간 평균 별풍선", f_label, (231,236,255))
        _text_right_v21(d, right_x, y+80, fmt(c["avg"]), f_avg, avg_col)

        sy = y + top_h
        d.rectangle([x, sy, x+card_w, sy+sales_h], fill=(27,26,23))
        d.text((x+18, sy+13), "수장", font=f_sales, fill=gold)
        _text_right_v21(d, x+card_w-18, sy+13, fmt(c["sales_month"]), f_sales, gold)

        ssy = sy + sales_h
        d.rectangle([x, ssy, x+card_w, ssy+sales_sub_h], fill=(23,22,18))
        sales_names = ", ".join([r["name"] for r in c["sales"]]) if c["sales"] else "수장 없음"
        d.text((x+18, ssy+4), _fit_text_v21(d, sales_names, f_sales_sub, card_w-36), font=f_sales_sub, fill=(189,168,112))

        rows_y = ssy + sales_sub_h
        max_month = max([r["month"] or 0 for r in c["normal"]] + [1])

        for ri, r in enumerate(c["normal"], start=1):
            rh = first_h if ri == 1 else row_h
            ry = rows_y + (first_h if ri > 1 else 0) + max(0, ri-2)*row_h
            d.rectangle([x, ry, x+card_w, ry+rh], fill=(22,23,34) if ri == 1 else (panel if ri % 2 == 0 else (15,16,26)))
            d.line([x, ry+rh-1, x+card_w, ry+rh-1], fill=(34,35,47))

            if ri == 1:
                d.text((x+14, ry+24), str(ri), font=f_rank, fill=muted)
                d.text((x+48, ry+23), _fit_text_v21(d, r["name"], f_name_first, 170), font=f_name_first, fill=white)
                _text_right_v21(d, x+card_w-16, ry+23, fmt(r["month"]), f_score, accent)
            else:
                d.rounded_rectangle([x+14, ry+16, x+38, ry+38], radius=7, fill=(35,36,49))
                _text_right_v21(d, x+31, ry+20, str(ri), f_rank, muted)
                d.text((x+48, ry+16), _fit_text_v21(d, r["name"], f_name, 170), font=f_name, fill=white)
                _text_right_v21(d, x+card_w-16, ry+16, fmt(r["month"]), f_score, (235,241,255))

            pct = 0 if r["month"] is None else max(0, min(1, (r["month"] or 0) / max_month))
            fill_w = int((card_w-20) * pct)
            gy = ry + rh - 4
            d.rectangle([x, gy, x+card_w, gy+3], fill=(25,26,34))
            if fill_w > 0:
                _draw_grad_h(d, x, gy, x+fill_w, gy+3, accent, white)

    img.save(RESULT_PNG)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="테스트용 멤버 수 제한")
    ap.add_argument("--year", type=int, default=dt.datetime.now().year)
    ap.add_argument("--month", type=int, default=dt.datetime.now().month)
    ap.add_argument("--day", type=int, default=dt.datetime.now().day)
    args = ap.parse_args()

    members = normalize_member_structure(load_members())
    total_members = sum(1 for _ in iter_member_items(members))
    print(f"members.json 기준 멤버 {total_members}명 로드 완료")
    if args.limit:
        print(f"테스트 제한: {args.limit}명")

    print("풍고 랭킹 HTML 직접 수집 중...")
    base_date = dt.date(args.year, args.month, args.day)
    today_candidates = [("day", base_date - dt.timedelta(days=o)) for o in range(0, 3)]
    month_candidates = [("month", None)]

    today_idx, today_used, dbg_today = fetch_period("today", today_candidates, args.year, args.month, args.day)
    month_idx, month_used, dbg_month = fetch_period("month", month_candidates, args.year, args.month, args.day)

    # 월간 API가 200이어도 entries=0으로 오는 경우가 있어서, 그때만 day API 합산으로 복구한다.
    # 오늘 집계(today_idx)와 members.json/HTML 구조는 절대 변경하지 않는다.
    if len(month_idx) == 0:
        fallback_idx, fallback_used, fallback_debug = fetch_month_by_daily_sum(args.year, args.month, args.day)
        dbg_month.append("")
        dbg_month.append("month_api_empty_fallback=daily_sum")
        dbg_month.extend(fallback_debug)
        if len(fallback_idx) > 0:
            month_idx, month_used = fallback_idx, fallback_used

    if len(month_idx) == 0:
        API_DEBUG_FILE.write_text("\n".join(dbg_today + ["", *dbg_month, "", "ERROR: month_count=0"]), encoding="utf-8")
        raise SystemExit("[ERROR] 월간 데이터가 0건입니다. api_debug.txt와 api_raw 폴더를 확인하세요. ranking.html 생성을 중단합니다.")

    debug = []
    debug.extend(dbg_today)
    debug.append("")
    debug.extend(dbg_month)
    debug.append("")
    debug.append(f"today_used={today_used}, today_count={len(today_idx)}")
    debug.append(f"month_used={month_used}, month_count={len(month_idx)}")
    API_DEBUG_FILE.write_text("\n".join(debug), encoding="utf-8")

    values, unmatched = make_values(members, today_idx, month_idx, args.limit)
    VALUES_FILE.write_text(json.dumps(values, ensure_ascii=False, indent=2), encoding="utf-8")
    UNMATCHED_FILE.write_text("\n".join(unmatched), encoding="utf-8")

    write_result_txt(values)
    write_html(values)
    draw_ranking(values)

    print("완료: result.txt / ranking.png / ranking.html / values.json 생성")
    print("풍고 수집 확인: api_debug.txt / api_raw 폴더")
    print("미집계 확인: unmatched_members.txt")

if __name__ == "__main__":
    main()
