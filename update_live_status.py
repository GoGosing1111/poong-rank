# -*- coding: utf-8 -*-
"""
C9 LIVE 상태 수집기 v3 - bjapi 방식

핵심:
- 크롬/셀레니움 사용 안 함
- https://bjapi.afreecatv.com/api/{soop_id}/station 직접 조회
- station.broad 항목을 기준으로 LIVE 판정
- live_status.json 생성

입력:
- cnine_members.json

출력:
- live_status.json
- live_status_debug.txt

실행:
python update_live_status.py
"""

import json
import time
import urllib.request
from pathlib import Path
from datetime import datetime

INPUT_MEMBERS = "cnine_members.json"
OUTPUT_LIVE = "live_status.json"
DEBUG_LOG = "live_status_debug.txt"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36",
    "Accept": "application/json,text/plain,*/*",
    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
    "Referer": "https://www.sooplive.com/",
}

def safe(value):
    return str(value or "").strip()

def extract_soop_id(url):
    if not url:
        return ""
    return safe(url).rstrip("/").split("/")[-1]

def fetch_json(url, timeout=10):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as res:
        raw = res.read()
        text = raw.decode("utf-8", errors="ignore")
        return json.loads(text)

def get_nested(obj, *keys, default=None):
    cur = obj
    for k in keys:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(k)
    return cur if cur is not None else default

def detect_live_from_station(data):
    """
    bjapi station 응답에서 LIVE 판정.

    방송중일 때 보통 station.broad 또는 broad 정보에:
    - broad_no
    - broad_title
    - current_view_cnt / total_view_cnt / view_cnt
    등이 존재함.
    """
    station = data.get("station") if isinstance(data, dict) else {}
    broad = station.get("broad") if isinstance(station, dict) else None

    if not isinstance(broad, dict):
        # 응답 최상위에 broad가 있는 경우도 대비
        broad = data.get("broad") if isinstance(data, dict) else None

    if not isinstance(broad, dict):
        return False, {
            "reason": "no_broad_object",
            "broad_no": "",
            "title": "",
            "viewers": 0,
        }

    broad_no = safe(
        broad.get("broad_no")
        or broad.get("broadNo")
        or broad.get("broad_no_hash")
        or broad.get("id")
    )

    title = safe(
        broad.get("broad_title")
        or broad.get("title")
        or broad.get("subject")
    )

    viewers_raw = (
        broad.get("current_view_cnt")
        or broad.get("current_viewer")
        or broad.get("view_cnt")
        or broad.get("viewer_cnt")
        or broad.get("total_view_cnt")
        or 0
    )

    try:
        viewers = int(str(viewers_raw).replace(",", ""))
    except Exception:
        viewers = 0

    # broad 객체가 있고 broad_no 또는 제목이 있으면 LIVE로 판단
    is_live = bool(broad_no or title)

    return is_live, {
        "reason": "broad_object_found" if is_live else "broad_object_empty",
        "broad_no": broad_no,
        "title": title,
        "viewers": viewers,
    }

def check_member(member):
    name = safe(member.get("name"))
    part = safe(member.get("part"))
    soop_id = safe(member.get("soop_id")) or extract_soop_id(member.get("soop_url"))
    soop_url = safe(member.get("soop_url")) or f"https://www.sooplive.com/station/{soop_id}"

    if not soop_id:
        return {
            "name": name,
            "part": part,
            "soop_id": "",
            "soop_url": soop_url,
            "is_live": False,
            "status": "OFF",
            "reason": "no_soop_id",
            "broad_no": "",
            "title": "",
            "viewers": 0,
            "checked_url": "",
        }

    api_url = f"https://bjapi.afreecatv.com/api/{soop_id}/station"

    try:
        data = fetch_json(api_url)
        is_live, info = detect_live_from_station(data)
        return {
            "name": name,
            "part": part,
            "soop_id": soop_id,
            "soop_url": soop_url,
            "is_live": bool(is_live),
            "status": "LIVE" if is_live else "OFF",
            "reason": info.get("reason", ""),
            "broad_no": info.get("broad_no", ""),
            "title": info.get("title", ""),
            "viewers": info.get("viewers", 0),
            "checked_url": api_url,
        }

    except Exception as e:
        return {
            "name": name,
            "part": part,
            "soop_id": soop_id,
            "soop_url": soop_url,
            "is_live": False,
            "status": "OFF",
            "reason": f"fetch_failed:{e}",
            "broad_no": "",
            "title": "",
            "viewers": 0,
            "checked_url": api_url,
        }

def main():
    members_path = Path(INPUT_MEMBERS)

    if not members_path.exists():
        print(f"[ERROR] {INPUT_MEMBERS} 파일이 없습니다.")
        print("같은 폴더에 cnine_members.json을 넣고 다시 실행하세요.")
        return

    members = json.loads(members_path.read_text(encoding="utf-8"))
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    result = {
        "updated_at": now,
        "total": len(members),
        "live_count": 0,
        "members": {}
    }

    logs = []
    logs.append(f"UPDATED_AT={now}")
    logs.append(f"TOTAL={len(members)}")
    logs.append("METHOD=bjapi_station")
    logs.append("")

    for idx, member in enumerate(members, 1):
        info = check_member(member)
        soop_id = info.get("soop_id") or info.get("name")

        if info["is_live"]:
            result["live_count"] += 1

        result["members"][soop_id] = info

        print(f"[{idx}/{len(members)}] [{info['status']}] {info['part']} / {info['name']} / {soop_id}")

        logs.append(
            f"[{info['status']}] [{info['part']}] {info['name']} / {soop_id} "
            f"/ viewers={info.get('viewers', 0)} / title={info.get('title', '')} "
            f"/ reason={info.get('reason', '')} / {info.get('checked_url', '')}"
        )

        time.sleep(0.12)

    Path(OUTPUT_LIVE).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    Path(DEBUG_LOG).write_text("\n".join(logs), encoding="utf-8")

    print("")
    print("=" * 60)
    print("완료:", OUTPUT_LIVE)
    print("LIVE:", result["live_count"], "/", result["total"])
    print("로그:", DEBUG_LOG)
    print("=" * 60)

if __name__ == "__main__":
    main()
