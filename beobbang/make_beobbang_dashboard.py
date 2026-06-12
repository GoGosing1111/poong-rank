# -*- coding: utf-8 -*-
"""
버빵동 Dashboard -> 와이고수 업로드용 정적 HTML/TXT 생성기

실행 결과:
- ygosu_beobbang_dashboard_full.html
- ygosu_paste.txt
- ygosu_paste_YYYYMMDD_HHMM.txt

특징:
- 베이커리/크림/오렌지 전용 테마
- beobbang_members.json 우선 사용
- SOOP 공지 글에서 제목/본문 최대한 수집
- 인라인 스타일 기반, 와이고수 붙여넣기용
"""

import html
import json
import os
import re
from datetime import datetime
from urllib.request import Request, urlopen
from urllib.parse import unquote

POST_URL = "https://www.sooplive.com/station/vlfvlf789/post/197602167"
BASE_URL = "https://keyman1335-maker.github.io/poong-rank/beobbang"
LOGO_URL = f"{BASE_URL}/assets/beobbang_logo.png"
OUT_HTML = "ygosu_beobbang_dashboard_full.html"
OUT_TXT = "ygosu_paste.txt"
WATERMARK = "BEOBBANG Dashboard Developed by 유두위생크림"
CACHE_BUST = datetime.now().strftime("%Y%m%d%H%M%S")
LEADER_MEMBER = {"name": "빵훈", "soop_id": "vlfvlf789", "part": "수장", "soop_url": "https://www.sooplive.com/station/vlfvlf789"}


CREAM = "#fff7ec"
PAPER = "#fffdf8"
ORANGE = "#f97316"
BROWN = "#5b2a12"
LINE = "#f3c58c"


def esc(v):
    return html.escape(str(v if v is not None else ""), quote=True)


def safe(v):
    return str(v or "").strip()


def strip_tags(src):
    src = re.sub(r"<script\b[^>]*>.*?</script>", "", src, flags=re.I | re.S)
    src = re.sub(r"<style\b[^>]*>.*?</style>", "", src, flags=re.I | re.S)
    src = re.sub(r"<br\s*/?>", "\n", src, flags=re.I)
    src = re.sub(r"</(p|div|li|tr|h\d)>", "\n", src, flags=re.I)
    src = re.sub(r"<[^>]+>", " ", src)
    src = html.unescape(src)
    src = unquote(src)
    src = re.sub(r"[ \t]+", " ", src)
    src = re.sub(r"\n\s*\n+", "\n", src)
    return src.strip()


def fetch_url(url):
    req = Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    })
    with urlopen(req, timeout=25) as res:
        raw = res.read()
    return raw.decode("utf-8", errors="ignore")


def load_local_text(*names):
    for name in names:
        if os.path.exists(name):
            try:
                txt = open(name, "r", encoding="utf-8-sig").read().strip()
                if txt:
                    print(f"[LOCAL] {name} 로드")
                    return txt
            except Exception as e:
                print(f"[WARN] {name} 로드 실패: {e}")
    return ""


def load_members():
    for name in ("beobbang_members.json", "members.json"):
        if os.path.exists(name):
            try:
                data = json.load(open(name, "r", encoding="utf-8-sig"))
                if isinstance(data, list):
                    print(f"[LOCAL] {name} 멤버 {len(data)}명 로드")
                    return data
                if isinstance(data, dict):
                    arr = data.get("members") or data.get("data") or []
                    if isinstance(arr, list):
                        print(f"[LOCAL] {name} 멤버 {len(arr)}명 로드")
                        return arr
            except Exception as e:
                print(f"[WARN] {name} 로드 실패: {e}")
    return []


def parse_title(raw):
    patterns = [
        r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:title["\']',
        r'<title[^>]*>(.*?)</title>',
        r'"title"\s*:\s*"(.*?)"',
        r'"subject"\s*:\s*"(.*?)"',
    ]
    for p in patterns:
        m = re.search(p, raw, flags=re.I | re.S)
        if m:
            t = html.unescape(m.group(1))
            t = re.sub(r"\\u([0-9a-fA-F]{4})", lambda x: chr(int(x.group(1), 16)), t)
            t = re.sub(r"\s+", " ", t).strip()
            if t:
                return t
    return "버빵동 공지사항"


def parse_body(raw):
    candidates = []
    for key in ("content", "contents", "body", "postContent", "stationPostContent"):
        for m in re.finditer(r'"' + re.escape(key) + r'"\s*:\s*"(.*?)"', raw, flags=re.I | re.S):
            val = m.group(1)
            val = val.replace(r"\n", "\n").replace(r"\/", "/").replace(r'\"', '"')
            val = re.sub(r"\\u([0-9a-fA-F]{4})", lambda x: chr(int(x.group(1), 16)), val)
            txt = strip_tags(val)
            if len(txt) > 30:
                candidates.append(txt)
    txt = strip_tags(raw)
    if len(txt) > 30:
        candidates.append(txt)
    if not candidates:
        return "SOOP 원문 수집 대기 또는 원문 확인 필요"
    candidates.sort(key=len, reverse=True)
    return candidates[0]


def fetch_post_data():
    local = load_local_text("beobbang_post_cache.html", "soop_post_cache.html")
    raw = local
    if not raw:
        try:
            raw = fetch_url(POST_URL)
            open("beobbang_post_cache.html", "w", encoding="utf-8").write(raw)
            print("[SOOP] 공지 원문 수집 완료")
        except Exception as e:
            print(f"[WARN] SOOP 공지 수집 실패: {e}")
            raw = ""
    title = parse_title(raw) if raw else "버빵동 공지사항"
    body = parse_body(raw) if raw else "SOOP 공지 수집 실패 - 원문 링크에서 확인 필요"
    return {"title": title, "body": body, "url": POST_URL}


def extract_members_from_text(text):
    members = []
    seen = set()
    url_pat = re.compile(r"https?://(?:www\.)?sooplive\.com/station/([A-Za-z0-9_\-]+)", re.I)
    for m in url_pat.finditer(text):
        sid = m.group(1)
        start = max(0, m.start() - 80)
        ctx = text[start:m.start()]
        ctx = re.sub(r"[\[\](){}<>|:/]+", " ", ctx)
        tokens = [x.strip() for x in re.split(r"\s+", ctx) if x.strip()]
        name = ""
        for tok in reversed(tokens):
            if 1 < len(tok) <= 16 and not tok.startswith("http") and not re.search(r"공지|멤버|현황|SOOP|방송국", tok, re.I):
                name = tok
                break
        key = sid.lower()
        if key not in seen:
            seen.add(key)
            members.append({"name": name or sid, "soop_id": sid, "part": "멤버", "soop_url": f"https://www.sooplive.com/station/{sid}"})
    return members


def normalize_members(members, post_text):
    if not members:
        members = extract_members_from_text(post_text)

    raw = [LEADER_MEMBER] + (members or [])
    out, seen = [], set()
    for m in raw:
        if not isinstance(m, dict):
            continue
        sid = safe(m.get("soop_id") or m.get("id"))
        if sid.lower() == "vlfvlf789":
            m = {**m, **LEADER_MEMBER}
            sid = "vlfvlf789"
        name = safe(m.get("display_name") or m.get("name") or m.get("nickname") or sid or "멤버")
        key = (sid or name).lower()
        if key in seen:
            continue
        seen.add(key)
        out.append({
            "name": name,
            "soop_id": sid,
            "part": safe(m.get("part") or m.get("role") or ("수장" if sid.lower() == "vlfvlf789" else "멤버")),
            "soop_url": safe(m.get("soop_url") or (f"https://www.sooplive.com/station/{sid}" if sid else "#")),
            "profile_img": safe(m.get("profile_img") or ""),
        })
    return out or [LEADER_MEMBER]

def extract_special(text):
    local = load_local_text("beobbang_special.txt", "dashboard_notice.txt", "notice.txt")
    if local:
        return local
    keywords = r"신규|탈퇴|휴방|복귀|변경|중요|필독|공지|특이사항|주의|확정|예정|금지|규칙"
    lines = []
    for line in text.splitlines():
        line = line.strip(" -•·\t")
        if 5 <= len(line) <= 120 and re.search(keywords, line):
            if line not in lines:
                lines.append(line)
        if len(lines) >= 6:
            break
    return "\n".join(lines) if lines else "오늘은 따끈한 특이사항이 없습니다."



def load_schedule():
    """beobbang_schedule.json 또는 beobbang_schedule.txt를 읽어서 버빵동 일정으로 표시."""
    for name in ("beobbang_schedule.json", "schedule_status.json"):
        if os.path.exists(name):
            try:
                data = json.load(open(name, "r", encoding="utf-8-sig"))
                arr = (data.get("schedules") or data.get("items") or data.get("events")) if isinstance(data, dict) else data
                if isinstance(arr, list):
                    out = []
                    for x in arr:
                        if isinstance(x, dict):
                            out.append({
                                "date": safe(x.get("date") or x.get("time") or x.get("start_at") or x.get("startAt") or ""),
                                "title": safe(x.get("title") or x.get("name") or x.get("subject") or "일정"),
                                "memo": safe(x.get("memo") or x.get("desc") or x.get("description") or ""),
                            })
                        else:
                            out.append({"date": "", "title": safe(x), "memo": ""})
                    if out:
                        print(f"[LOCAL] {name} 일정 {len(out)}개 로드")
                        return out
            except Exception as e:
                print(f"[WARN] {name} 로드 실패: {e}")

    txt = load_local_text("beobbang_schedule.txt", "schedule.txt")
    if txt:
        out = []
        for line in txt.splitlines():
            line = line.strip(" -•·\t")
            if not line:
                continue
            parts = [x.strip() for x in re.split(r"\s*\|\s*", line)]
            if len(parts) >= 2:
                out.append({"date": parts[0], "title": parts[1], "memo": parts[2] if len(parts) >= 3 else ""})
            else:
                out.append({"date": "", "title": line, "memo": ""})
        if out:
            print(f"[LOCAL] beobbang_schedule.txt 일정 {len(out)}개 로드")
            return out
    return []

def summary_text(text, limit=520):
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > limit:
        return text[:limit].rstrip() + "..."
    return text or "본문 수집 대기 또는 원문에서 확인"


def clean_html_for_wago(src):
    src = re.sub(r"<script\b[^>]*>.*?</script>", "", src, flags=re.I | re.S)
    src = re.sub(r"<style\b[^>]*>.*?</style>", "", src, flags=re.I | re.S)
    src = re.sub(r"\s+on\w+\s*=\s*(['\"]).*?\1", "", src, flags=re.I | re.S)
    src = re.sub(r"javascript\s*:", "", src, flags=re.I)
    src = src.replace("\r\n", "\n").replace("\r", "\n")
    src = re.sub(r"\n{3,}", "\n\n", src)
    return src.strip()


def section(title, body, open_attr=False, color=ORANGE, icon="🍞"):
    # SOOP 호환용: details/summary 제거 + 둥근 엣지 유지
    # details/summary와 overflow:hidden 조합이 SOOP 게시글에서 테두리 끝선을 깨는 경우가 있어
    # 일반 div 섹션으로 출력한다.
    return f"""
<div style="margin:12px 0 14px;padding:0;border:2px solid {color};border-radius:22px;background:{PAPER};box-sizing:border-box;">
  <div style="padding:13px 14px;background:linear-gradient(180deg,#fff3df,#ffe0b9);color:{BROWN};font-size:18px;font-weight:1000;text-align:center;text-shadow:0 1px 0 #fff;border-bottom:2px dashed {color};border-radius:19px 19px 0 0;letter-spacing:-.3px;">
    {icon} {esc(title)}
  </div>
  <div style="padding:12px;background:linear-gradient(180deg,#fffdf8,#fff7ec);border-radius:0 0 19px 19px;box-sizing:border-box;">
    {body}
  </div>
</div>"""

def metric(label, value, icon="•"):
    return f"""<div style="display:inline-block;vertical-align:top;width:31.5%;min-width:150px;margin:4px .5%;padding:11px 8px;border-radius:16px;background:#fffdf8;border:2px solid #f3c58c;box-sizing:border-box;box-shadow:0 3px 0 rgba(91,42,18,.10);text-align:center;">
  <div style="color:#f97316;font-size:18px;font-weight:1000;line-height:1;">{esc(icon)}</div>
  <div style="margin-top:5px;color:#8a4a21;font-size:11px;font-weight:900;">{esc(label)}</div>
  <div style="margin-top:3px;color:#4a220f;font-size:14px;font-weight:1000;word-break:break-word;">{esc(value)}</div>
</div>"""


def profile_src(m):
    if m.get("profile_img"):
        return m.get("profile_img")
    sid = m.get("soop_id") or ""
    if not sid:
        return ""
    return f"https://profile.img.sooplive.com/LOGO/{sid[:2]}/{sid}/{sid}.jpg"


def member_card(m, idx=0):
    sid = m.get("soop_id") or ""
    img = profile_src(m)
    is_leader = sid.lower() == "vlfvlf789" or m.get("part") == "수장"
    img_html = f'<img src="{esc(img)}" style="width:66px;height:66px;border-radius:50%;object-fit:cover;border:3px solid #f59e0b;background:#fff7ec;box-shadow:0 3px 0 rgba(91,42,18,.16);">' if img else '<div style="width:66px;height:66px;border-radius:50%;border:3px solid #f59e0b;background:#fff3df;display:inline-flex;align-items:center;justify-content:center;color:#f97316;font-size:24px;font-weight:1000;">빵</div>'
    label = "👑 수장" if is_leader else ("🥖 멤버" if (idx % 2 == 0) else "🍞 멤버")
    card_bg = "linear-gradient(180deg,#fff4d6,#ffe5b7)" if is_leader else "linear-gradient(180deg,#fffdf8,#fff0db)"
    width = "98%" if is_leader else "47.8%"
    return f"""
<div style="display:inline-block;vertical-align:top;width:{width};margin:0 .6% 9px;padding:12px 8px 13px;border-radius:19px;background:{card_bg};border:2px solid #f3c58c;text-align:center;box-sizing:border-box;font-size:13px;box-shadow:0 4px 0 rgba(91,42,18,.10);">
  <div style="margin-bottom:7px;text-align:left;"><span style="display:inline-block;padding:4px 8px;border-radius:999px;background:#fff7ec;border:1px solid #f59e0b;color:#8a4a21;font-size:10px;font-weight:1000;">{esc(label)}</span></div>
  {img_html}
  <div style="margin-top:8px;color:#4a220f;font-size:20px;font-weight:1000;white-space:nowrap;text-overflow:ellipsis;text-shadow:0 1px 0 #fff;letter-spacing:-.5px;">{esc(m.get('name','-'))}</div>
  <div style="margin-top:2px;color:#a16207;font-size:10px;font-weight:900;white-space:nowrap;text-overflow:ellipsis;">SOOP ID · {esc(sid or '-')}</div>
  <a href="{esc(m.get('soop_url') or '#')}" target="_blank" rel="nofollow" style="display:inline-block;margin-top:8px;padding:6px 10px;border-radius:999px;background:#f97316;border:1px solid #c2410c;color:#fff;font-size:11px;font-weight:1000;text-decoration:none;box-shadow:0 2px 0 rgba(91,42,18,.18);">방송국 바로가기</a>
</div>"""

def render_members(members):
    if not members:
        return '<div style="padding:16px;color:#8a4a21;font-weight:900;text-align:center;">멤버 데이터 없음</div>'
    leader_count = sum(1 for m in members if (m.get("soop_id") or "").lower() == "vlfvlf789" or m.get("part") == "수장")
    regular_count = max(0, len(members) - leader_count)
    summary = f"""<div style="padding:10px 9px;margin-bottom:10px;border-radius:17px;background:#fff3df;border:2px dashed #f59e0b;color:#7c2d12;font-size:13px;font-weight:1000;text-align:center;box-sizing:border-box;">🍞 수장 {leader_count}명 · 멤버 {regular_count}명 · 닉네임 우선 표시</div>"""
    return summary + '<div style="text-align:left;font-size:0;">' + ''.join(member_card(m, i) for i, m in enumerate(members)) + '</div>'

def render_special(text):
    lines = [x.strip() for x in str(text or "").splitlines() if x.strip()]
    if not lines:
        lines = ["오늘은 따끈한 특이사항이 없습니다."]
    return ''.join(f'<div style="padding:10px 11px;margin-bottom:8px;border-radius:16px;background:#fffaf0;border:2px solid #fed7aa;color:#5b2a12;font-size:13px;font-weight:900;line-height:1.55;word-break:break-word;box-sizing:border-box;">⭐ {esc(x)}</div>' for x in lines[:8])


def render_schedule(items):
    if not items:
        return '<div style="padding:14px;border-radius:16px;background:#fffaf0;border:2px solid #fed7aa;color:#5b2a12;font-size:13px;font-weight:900;line-height:1.55;text-align:center;box-sizing:border-box;">등록된 버빵동 일정이 없습니다.<br>beobbang_schedule.txt에 한 줄씩 추가하면 자동 표시됩니다.</div>'
    blocks = []
    for x in items[:10]:
        date = safe(x.get("date"))
        title = safe(x.get("title") or "일정")
        memo = safe(x.get("memo"))
        memo_html = f'<div style="margin-top:5px;color:#8a4a21;font-size:12px;font-weight:800;line-height:1.45;word-break:break-word;">{esc(memo)}</div>' if memo else ''
        blocks.append(f'''
<div style="margin-bottom:8px;padding:11px 12px;border-radius:16px;background:#fffaf0;border:2px solid #fed7aa;color:#5b2a12;box-sizing:border-box;box-shadow:0 3px 0 rgba(91,42,18,.08);">
  <div style="display:inline-block;padding:4px 9px;border-radius:999px;background:#f97316;color:#fff;font-size:11px;font-weight:1000;box-shadow:0 2px 0 rgba(91,42,18,.12);">{esc(date or '일정')}</div>
  <div style="margin-top:7px;font-size:14px;font-weight:1000;line-height:1.45;word-break:break-word;">{esc(title)}</div>
  {memo_html}
</div>''')
    return ''.join(blocks)

def render_notice(post):
    body = summary_text(post.get("body", ""), 760)
    return f"""
<div style="margin:0 0 9px;padding:0;border:2px solid #f3c58c;border-radius:12px;background:#fffdf8;box-sizing:border-box;">
  <div style="padding:12px 13px;background:linear-gradient(180deg,#fff0db,#ffe0b9);border-bottom:2px dashed #f97316;box-sizing:border-box;">
    <div style="color:#5b2a12;font-size:16px;line-height:1.35;font-weight:1000;letter-spacing:-.4px;text-shadow:0 1px 0 #fff;word-break:keep-all;">🍞 {esc(post.get('title','버빵동 공지사항'))}</div>
  </div>
  <div style="padding:13px;background:#fffdf8;box-sizing:border-box;">
    <div style="padding:12px;border-radius:10px;background:#fff7ec;border:1px solid #fed7aa;color:#5b2a12;font-size:13px;line-height:1.62;font-weight:800;word-break:break-word;box-sizing:border-box;">{esc(body)}</div>
    <a href="{esc(post.get('url') or POST_URL)}" target="_blank" rel="nofollow" style="display:inline-block;margin-top:10px;padding:8px 12px;border-radius:999px;background:#7c2d12;color:#fff;font-size:12px;font-weight:1000;text-decoration:none;box-shadow:0 2px 0 rgba(91,42,18,.18);">원문 확인</a>
  </div>
</div>"""


def render_hero(updated):
    return f"""
<div style="position:relative;border-radius:24px;border:2px solid #f3c58c;background:radial-gradient(circle at 18% 15%,#fff7ec 0,#ffe7c2 34%,#ffd6a3 100%);box-shadow:0 5px 0 rgba(91,42,18,.12);box-sizing:border-box;">
  <div style="padding:18px 14px 14px;text-align:center;box-sizing:border-box;">
    <img src="{LOGO_URL}?v={CACHE_BUST}" style="display:block;max-width:230px;width:58%;height:auto;margin:0 auto;border:0;">
    <div style="margin:8px auto 0;max-width:260px;border-top:2px solid #f97316;height:1px;line-height:1px;"></div>
    <div style="margin-top:8px;color:#8a4a21;font-size:11px;font-weight:900;">집계시간: {esc(updated)}</div>
  </div>
</div>"""


def main():
    updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    post = fetch_post_data()
    members = normalize_members(load_members(), post.get("body", ""))
    special = extract_special(post.get("body", ""))
    schedule = load_schedule()

    html_out = f"""<div style="width:100%;max-width:760px;margin:0 auto;background:radial-gradient(circle at top,#fff9ef 0,#fff1dc 45%,#f8dfbc 100%);padding:10px;box-sizing:border-box;font-family:Arial,'Malgun Gothic',sans-serif;color:#5b2a12;border-radius:24px;border:2px solid #f3c58c;">
  {render_hero(updated)}
  {section('멤버 현황', render_members(members), True, '#f97316', '🥐')}
  {section('오늘의 특이사항', render_special(special), True, '#f59e0b', '⭐')}
  {section('버빵동 일정', render_schedule(schedule), True, '#f97316', '📅')}
  {section('SOOP 공지사항', render_notice(post), True, '#7c2d12', '📢')}
  <div style="margin-top:12px;text-align:center;color:#8a4a21;font-size:11px;font-weight:900;text-shadow:0 1px 0 #fff;">{esc(WATERMARK)}</div>
  <div style="margin-top:5px;text-align:center;color:#a16207;font-size:10px;font-weight:800;">자동 변환: {esc(updated)}</div>
</div>"""

    paste_txt = clean_html_for_wago(html_out)
    stamped = "ygosu_paste_" + datetime.now().strftime("%Y%m%d_%H%M") + ".txt"

    open(OUT_HTML, "w", encoding="utf-8").write(html_out)
    open(OUT_TXT, "w", encoding="utf-8").write(paste_txt)
    open(stamped, "w", encoding="utf-8").write(paste_txt)

    print("완료:", OUT_HTML)
    print("완료:", OUT_TXT)
    print("완료:", stamped)
    print("멤버:", len(members))
    print("와이고수에는 ygosu_paste.txt 또는 최신 ygosu_paste_*.txt 내용을 붙여넣으면 됩니다.")


if __name__ == "__main__":
    main()
