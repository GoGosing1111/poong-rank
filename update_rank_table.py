# -*- coding: utf-8 -*-
"""
CNINE 별풍선표 직접 수집기 v7
- poong.today chart API 직접 수집
- poong.today 축약 필드(i/n/b) 대응
- 이번 달 매칭률이 낮으면 지난달 월간 데이터 자동 fallback
- ranking_data.json을 현재 index.html이 요구하는 excel/star 구조로 생성
"""
from __future__ import annotations

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
API_BASE = "https://static.poong.today/chart/get"
TIMEOUT = 20
REQUEST_DELAY = 0.25

# 철구형은 수장으로만 1회 집계한다.
# cnine_members.json에 스타부/엑셀부 양쪽으로 들어있어도 별풍선표 평균/순위에서는 제외된다.
LEADER_SOOP_IDS = {"y1026"}
LEADER_NAMES = {"철구형"}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/148 Safari/537.36",
    "Accept": "application/json,text/plain,*/*",
    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
    "Referer": "https://poong.today/",
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


def build_url(ctype: str, year: int, month: int, day: int | str | None = None) -> str:
    params = {"ctype": ctype, "ks": "false", "year": year, "month": month}
    params["day"] = "undefined" if ctype == "month" else (day if day is not None else datetime.now().day)
    return API_BASE + "?" + urllib.parse.urlencode(params)


def fetch_json(url: str) -> Any:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as res:
        raw = res.read()
    text = raw.decode("utf-8", errors="ignore")
    return json.loads(text)


def extract_rows(data: Any) -> List[Dict[str, Any]]:
    """poong.today 응답에서 방송자 row만 추출.
    현재 구조 {"b":[{"i","n","b"}]} 대응.
    nested f(후원자)는 제외하되, 구조 변경 시 재귀로 방송자 row를 다시 찾는다.
    """
    rows: List[Dict[str, Any]] = []

    def valid_row(x: Any) -> bool:
        return (
            isinstance(x, dict)
            and safe(x.get("i"))
            and safe(x.get("n"))
            and to_int(x.get("b")) > 0
        )

    def add_row(x: Dict[str, Any]):
        # f는 후원자 정보이므로 row 자체에 포함만 하고 별도 row로는 넣지 않는다.
        if valid_row(x):
            rows.append(x)

    if isinstance(data, dict):
        if isinstance(data.get("b"), list):
            for x in data["b"]:
                if isinstance(x, dict):
                    add_row(x)
            if rows:
                return rows
        for key in ("items", "data", "list", "rows", "content", "result"):
            if isinstance(data.get(key), list):
                for x in data[key]:
                    if isinstance(x, dict):
                        add_row(x)
                if rows:
                    return rows

    if isinstance(data, list):
        for x in data:
            if isinstance(x, dict):
                add_row(x)
        if rows:
            return rows

    # 마지막 방어: 전체 재귀. 단, f 내부는 후원자라 제외.
    def walk(x: Any, parent_key: str = ""):
        if isinstance(x, list):
            for it in x:
                walk(it, parent_key)
        elif isinstance(x, dict):
            if parent_key != "f":
                add_row(x)
                for k, v in x.items():
                    if isinstance(v, (list, dict)):
                        walk(v, str(k))
    walk(data)
    return rows


def row_name(row: Dict[str, Any]) -> str:
    for k in ("n", "name", "nickname", "nick", "user_name", "bj_name", "bjnick", "title"):
        if safe(row.get(k)):
            return safe(row.get(k))
    return ""


def row_id(row: Dict[str, Any]) -> str:
    for k in ("i", "id", "user_id", "bj_id", "soop_id", "afreeca_id", "station_id"):
        if safe(row.get(k)):
            return safe(row.get(k))
    return ""


def row_value(row: Dict[str, Any]) -> int:
    for k in ("b", "value", "count", "cnt", "amount", "total", "score", "balloon", "star", "poong", "sum"):
        val = to_int(row.get(k))
        if val > 0:
            return val
    return 0


def make_index(rows: Iterable[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    idx: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        name = row_name(row)
        uid = row_id(row)
        val = row_value(row)
        if val <= 0:
            continue
        keys = {norm_name(name), safe(name).lower(), norm_name(uid), safe(uid).lower()}
        for k in keys:
            if not k:
                continue
            if k not in idx or val > idx[k].get("value", 0):
                idx[k] = {"value": val, "api_name": name, "api_id": uid, "raw": row}
    return idx


def find_value(member: Dict[str, Any], idx: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    # ID가 가장 정확하므로 ID 우선
    candidates = [member.get("soop_id"), member.get("id"), member.get("match"), member.get("name")]
    for c in candidates:
        for k in (safe(c).lower(), norm_name(c)):
            if k and k in idx:
                return idx[k]
    return {"value": 0, "api_name": "", "api_id": "", "raw": {}}


def fetch_chart(ctype: str, year: int, month: int, day: int | str | None, tag: str, logs: List[str]) -> Tuple[List[Dict[str, Any]], str]:
    url = build_url(ctype, year, month, day)
    logs.append(f"FETCH {tag}: {url}")
    data = fetch_json(url)
    RAW_DIR.mkdir(exist_ok=True)
    (RAW_DIR / f"{tag}.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    rows = extract_rows(data)
    logs.append(f"ROWS {tag}: {len(rows)}")
    if rows:
        logs.append(f"SAMPLE {tag}: id={row_id(rows[0])} name={row_name(rows[0])} value={row_value(rows[0])}")
    return rows, url


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
            rows, url = fetch_chart("month", yy, mm, "undefined", tag, logs)
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
                rows, url = fetch_chart("month", yy, mm, "undefined", tag, logs)
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
        wait_msg = "월초 집계 반영 대기중입니다. 풍투데이 1일 데이터 반영 후 자동 갱신됩니다."
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
            "source": "poong.today chart API direct v8 current-month-lock",
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
        day_rows, day_url = fetch_chart("day", dt.year, dt.month, dt.day, "day", logs)
        day_idx = make_index(day_rows)
    except Exception as e:
        logs.append(f"DAY_FAILED={type(e).__name__}: {e}")
    try:
        today_rows, today_url = fetch_chart("today", dt.year, dt.month, dt.day, "today", logs)
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
        "source": "poong.today chart API direct v8 current-month-lock",
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
