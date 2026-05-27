# -*- coding: utf-8 -*-
"""
C9 LIVE 상태 수집기 v2

사용:
python update_live_status.py

입력:
- cnine_members.json

출력:
- live_status.json
- live_status_debug.txt

주의:
SOOP 공개 페이지/응답 구조에 따라 LIVE 탐지가 조정될 수 있음.
처음 돌린 뒤 live_status_debug.txt를 보면 어떤 기준으로 LIVE/OFF 처리됐는지 확인 가능.
"""

import json
import re
import time
import urllib.request
from pathlib import Path
from datetime import datetime

INPUT_MEMBERS = "cnine_members.json"
OUTPUT_LIVE = "live_status.json"
DEBUG_LOG = "live_status_debug.txt"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36",
    "Accept": "text/html,application/json,text/plain,*/*",
    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
}

def fetch(url, timeout=10):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as res:
        raw = res.read()
        return raw.decode("utf-8", errors="ignore")

def safe(value):
    return str(value or "").strip()

def extract_id(url):
    return safe(url).rstrip("/").split("/")[-1] if url else ""

def detect_live(text):
    if not text:
        return False, "empty"

    offline_patterns = [
        r'"is_live"\s*:\s*false',
        r'"isLive"\s*:\s*false',
        r'"live"\s*:\s*false',
        r'"isBroad"\s*:\s*false',
        r'오프라인',
        r'방송\s*종료',
        r'방송\s*준비',
    ]

    live_patterns = [
        r'"is_live"\s*:\s*true',
        r'"isLive"\s*:\s*true',
        r'"live"\s*:\s*true',
        r'"isBroad"\s*:\s*true',
        r'"broad_status"\s*:\s*"on"',
        r'"broadcast_status"\s*:\s*"on"',
        r'"status"\s*:\s*"live"',
        r'방송중',
        r'\bLIVE\b',
    ]

    for p in offline_patterns:
        if re.search(p, text, re.I):
            return False, "offline:" + p

    for p in live_patterns:
        if re.search(p, text, re.I):
            return True, "live:" + p

    return False, "no_pattern"

def check_member(m):
    soop_id = safe(m.get("soop_id")) or extract_id(m.get("soop_url"))
    urls = [
        f"https://www.sooplive.com/station/{soop_id}",
        f"https://ch.sooplive.co.kr/{soop_id}",
    ]

    last_err = ""

    for url in urls:
        try:
            text = fetch(url)
            is_live, reason = detect_live(text)
            return is_live, reason, url
        except Exception as e:
            last_err = str(e)

    return False, "fetch_failed:" + last_err, urls[0] if urls else ""

def main():
    path = Path(INPUT_MEMBERS)
    if not path.exists():
        print("[ERROR] cnine_members.json 없음")
        return

    members = json.loads(path.read_text(encoding="utf-8"))
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    result = {
        "updated_at": now,
        "total": len(members),
        "live_count": 0,
        "members": {}
    }

    logs = [f"UPDATED_AT={now}", f"TOTAL={len(members)}", ""]

    for i, m in enumerate(members, 1):
        name = safe(m.get("name"))
        part = safe(m.get("part"))
        soop_id = safe(m.get("soop_id")) or extract_id(m.get("soop_url"))
        soop_url = safe(m.get("soop_url")) or f"https://www.sooplive.com/station/{soop_id}"

        print(f"[{i}/{len(members)}] {part} / {name} / {soop_id}")

        is_live, reason, checked_url = check_member(m)
        if is_live:
            result["live_count"] += 1

        result["members"][soop_id] = {
            "name": name,
            "part": part,
            "soop_id": soop_id,
            "soop_url": soop_url,
            "is_live": is_live,
            "status": "LIVE" if is_live else "OFF",
            "reason": reason,
            "checked_url": checked_url,
        }

        logs.append(f"[{'LIVE' if is_live else 'OFF'}] [{part}] {name} / {soop_id} / {reason} / {checked_url}")
        time.sleep(0.2)

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
