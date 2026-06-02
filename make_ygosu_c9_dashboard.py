# -*- coding: utf-8 -*-
"""
CNINE Dashboard -> 와이고수 업로드용 정적 HTML/TXT 변환기

실행 결과:
- ygosu_c9_dashboard_full.html
- ygosu_paste.txt

특징:
- GitHub Pages 최신 JSON을 읽어서 정적 HTML 생성
- 와이고수에 붙여넣기 가능한 TXT도 같이 생성
- 인라인 스타일 유지
- script 제거
- 하단 제작자 워터마크 포함
"""

import json
import os
import html
import re
from datetime import datetime
from urllib.request import Request, urlopen

BASE_URL = "https://keyman1335-maker.github.io/poong-rank"
CACHE_BUST = datetime.now().strftime("%Y%m%d%H%M%S")
OUT_HTML = "ygosu_c9_dashboard_full.html"
OUT_TXT = "ygosu_paste.txt"
WATERMARK = "CNINE Dashboard Developed by 유두위생크림"
LEADER_SOOP_IDS = {"y1026"}
LEADER_NAMES = {"철구형"}


def fetch_json(name, default):
    url = f"{BASE_URL}/{name}?v={CACHE_BUST}"
    try:
        req = Request(url, headers={
            "User-Agent": "Mozilla/5.0",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        })
        with urlopen(req, timeout=20) as res:
            raw = res.read().decode("utf-8-sig", errors="ignore")
            return json.loads(raw)
    except Exception as e:
        print(f"[WARN] {name} 로드 실패: {e}")
        return default


def load_json(name, default):
    """로컬 JSON을 우선 사용하고, 없거나 실패하면 GitHub Pages JSON으로 fallback."""
    try:
        if os.path.exists(name):
            with open(name, "r", encoding="utf-8-sig") as f:
                print(f"[LOCAL] {name} 로드")
                return json.load(f)
    except Exception as e:
        print(f"[WARN] 로컬 {name} 로드 실패: {e}")

    return fetch_json(name, default)

def esc(v):
    return html.escape(str(v if v is not None else ""), quote=True)

def safe(v):
    return str(v or "").strip()

def is_leader_member(m):
    sid = safe(m.get("soop_id") or m.get("id")).lower()
    name = safe(m.get("name"))
    return sid in LEADER_SOOP_IDS or name in LEADER_NAMES

def unique_members_by_soop_id(members):
    seen = set()
    out = []
    source = members if isinstance(members, list) else []
    for m in source:
        sid = safe(m.get("soop_id") or m.get("id")).lower()
        key = sid or safe(m.get("name"))
        if key in seen:
            continue
        seen.add(key)
        out.append(m)
    return out

def read_dashboard_notice():
    # dashboard_notice.txt에 적은 줄을 그대로 특이사항에 표시한다.
    # 2줄 이상도 가능하며 줄바꿈은 <br>로 변환된다.
    for name in ("dashboard_notice.txt", "notice.txt"):
        try:
            if os.path.exists(name):
                txt = open(name, "r", encoding="utf-8-sig").read().strip()
                if txt:
                    return txt
        except Exception as e:
            print(f"[WARN] {name} 로드 실패: {e}")
    return "-"

def render_dashboard_notice(text):
    lines = [x.strip() for x in str(text or "").splitlines() if x.strip()]
    if not lines:
        lines = ["-"]
    body = "<br>".join(esc(x) for x in lines)
    return f"""
<div style="margin-top:9px;border:1px solid rgba(255,211,79,.32);border-radius:15px;background:linear-gradient(135deg,rgba(255,211,79,.10),rgba(0,0,0,.22));overflow:hidden;box-sizing:border-box;">
  <div style="padding:9px 11px;background:rgba(0,0,0,.20);border-bottom:1px solid rgba(255,211,79,.22);color:#ffd34f;font-size:13px;font-weight:1000;text-align:left;text-shadow:0 2px 0 #000;">📢 특이사항</div>
  <div style="padding:10px 11px;color:#fff;font-size:13px;font-weight:900;line-height:1.55;text-align:left;word-break:break-word;max-height:94px;overflow:auto;box-sizing:border-box;">{body}</div>
</div>"""

def render_self_verify_card():
    verify_url = "https://m.sooplive.com/statistics/a/watch/?szModule=UserLiveWatchTimeData&szMethod=watch"

    # 자동 판독형 셀프인증 JS. GitHub 최상단에 soop_fandom_verify.js를 올려두면 동작한다.
    auto_verify_js = f"{BASE_URL}/soop_fandom_verify.js?v=20260603"

    # 1073983에서 실제 동작한 iframe srcdoc 구조 유지.
    # srcdoc 내부는 &lt; / &gt; 엔티티 형태로 넣어야 와고에서 깨질 확률이 낮다.
    iframe_html = f"""<iframe height="48" frameborder="0" allow="clipboard-write" referrerpolicy="strict-origin-when-cross-origin" style="flex:1 1 160px;min-width:160px;width:0;border:0;border-radius:9px;overflow:hidden;" srcdoc="&lt;!doctype html&gt;
&lt;meta charset='utf-8'&gt;

&lt;style&gt;
body{{margin:0}}
button{{
  width:100%;
  height:48px;
  background:#dc2626;
  color:#fff;
  border:0;
  border-radius:9px;
  font-size:14px;
  font-weight:900;
  cursor:pointer;
}}
&lt;/style&gt;

&lt;button id='btn'&gt;📋 자동 인증 코드 복사&lt;/button&gt;

&lt;script&gt;
function copyText(text){{
  if(navigator.clipboard &amp;&amp; window.isSecureContext){{
    return navigator.clipboard.writeText(text);
  }}else{{
    var ta=document.createElement('textarea');
    ta.value=text;
    ta.style.position='fixed';
    ta.style.opacity='0';
    document.body.appendChild(ta);
    ta.select();
    try{{ document.execCommand('copy'); }} finally {{ document.body.removeChild(ta); }}
    return Promise.resolve();
  }}
}}

var btn = document.getElementById('btn');
var code = '!function(){{var s=document.createElement(\\'script\\');s.id=\\'soop-fandom-verify-loader\\';s.src=\\'{auto_verify_js}\\';document.head.appendChild(s)}}();';

btn.onclick = function() {{
  copyText(code).then(function(){{
    alert('복사되었습니다');
  }}).catch(function(){{
    alert('복사 실패');
  }});
}};
&lt;/script&gt;
" src=""></iframe>"""

    return f"""
<div style="margin-top:10px;border:1px solid rgba(255,79,114,.42);border-radius:15px;background:linear-gradient(135deg,rgba(255,79,114,.15),rgba(0,0,0,.24));overflow:hidden;box-sizing:border-box;">
  <div style="padding:10px 12px;background:rgba(0,0,0,.24);border-bottom:1px solid rgba(255,79,114,.25);color:#ff6b8a;font-size:14px;font-weight:1000;text-align:left;text-shadow:0 2px 0 #000;">
    🚨 리캡 셀프인증
  </div>

  <div style="padding:12px 11px;color:#fff;font-size:13px;font-weight:900;line-height:1.62;text-align:center;word-break:keep-all;box-sizing:border-box;">
    SOOP 시청기록에서<br>
    <span style="color:#ffd34f;font-weight:1000;">염보성 / 비제이 케이</span> 기록을 자동 판독합니다.

    <div style="margin-top:12px;display:flex;gap:8px;justify-content:center;align-items:stretch;flex-wrap:wrap;box-sizing:border-box;">
      {iframe_html}

      <a href="{verify_url}" target="_blank" rel="nofollow"
         style="flex:1 1 160px;min-width:160px;height:48px;display:flex;align-items:center;justify-content:center;border-radius:9px;background:#16a34a;color:#fff;font-size:14px;font-weight:1000;text-decoration:none;box-sizing:border-box;">
        🔍 시청기록 확인
      </a>
    </div>

    <div style="margin-top:10px;color:#cbd5e1;font-size:11px;font-weight:800;line-height:1.45;">
      ※ 시청기록 페이지에서 복사한 코드를 주소창에 실행하면 자동 인증 이미지가 생성됩니다.<br>
      ※ 본인 로그인 상태에서만 확인 가능합니다.
    </div>
  </div>
</div>"""

def clean_html_for_wago(src):
    # iframe srcdoc 내부의 <script>는 와고 1073983 리캡 복사 버튼과 같은 방식이라 보호한다.
    protected = []
    def _keep_srcdoc(m):
        protected.append(m.group(0))
        return f"__SRC_DOC_BLOCK_{len(protected)-1}__"

    src = re.sub(r'srcdoc=".*?"', _keep_srcdoc, src, flags=re.I | re.S)

    src = re.sub(r"<script\b[^>]*>.*?</script>", "", src, flags=re.I | re.S)
    src = re.sub(r"<style\b[^>]*>.*?</style>", "", src, flags=re.I | re.S)
    src = re.sub(r"\s+on\w+\s*=\s*(['\"]).*?\1", "", src, flags=re.I | re.S)
    src = re.sub(r"javascript\s*:", "", src, flags=re.I)

    for i, block in enumerate(protected):
        src = src.replace(f"__SRC_DOC_BLOCK_{i}__", block)

    src = src.replace("\r\n", "\n").replace("\r", "\n")
    src = re.sub(r"\n{3,}", "\n\n", src)
    return src.strip()

def profile_src(m):
    if m.get("profile_img"):
        return m.get("profile_img")
    sid = m.get("soop_id") or ""
    if not sid:
        return ""
    return f"https://profile.img.sooplive.com/LOGO/{sid[:2]}/{sid}/{sid}.jpg"

def get_live_map(live_json):
    if isinstance(live_json, dict):
        return live_json.get("members") or live_json.get("data") or {}
    return {}

def is_live(member, live_map):
    sid = member.get("soop_id") or ""
    info = live_map.get(sid) or {}
    return bool(info.get("is_live"))

def section(title, body, open_attr=False, color="#2798ff"):
    open_text = " open" if open_attr else ""
    return f"""
<details{open_text} style="margin:10px 0 13px;padding:0;border:1px solid {color};border-radius:18px;background:#071426;overflow:hidden;box-sizing:border-box;box-shadow:0 0 14px rgba(80,170,255,.35);">
  <summary style="list-style:none;cursor:pointer;padding:14px 12px;background:linear-gradient(180deg,#12345c,#071526);color:#fff;font-size:19px;font-weight:1000;text-align:center;text-shadow:0 0 8px rgba(80,170,255,.85),0 2px 0 #000;border-bottom:2px solid {color};">
    {esc(title)}
  </summary>
  <div style="padding:10px;background:#081525;border-top:1px solid rgba(255,255,255,.10);box-sizing:border-box;">
    {body}
  </div>
</details>"""

def metric(label, value):
    return f"""<div style="display:flex;justify-content:space-between;gap:8px;padding:9px 2px;border-bottom:1px solid rgba(255,255,255,.08);font-size:13px;font-weight:900;">
<span style="color:#dff2ff;">{esc(label)}</span><span style="color:#7ec8ff;text-align:right;">{esc(value)}</span></div>"""

def member_card(m, live_map, single=False):
    sid = m.get("soop_id") or ""
    live = is_live(m, live_map)
    badge_bg = "#168fff" if live else "#333"
    badge = "LIVE" if live else "OFF"
    soop_url = m.get("soop_url") or (f"https://www.sooplive.com/station/{sid}" if sid else "#")
    img = profile_src(m)
    return f"""
<div style="display:inline-block;vertical-align:top;width:{'68%' if single else '48%'};margin:0 .6% 8px;padding:9px 6px;border-radius:14px;background:rgba(0,0,0,.26);border:1px solid rgba(90,175,255,.24);text-align:center;box-sizing:border-box;overflow:hidden;">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
    <span style="padding:3px 7px;border-radius:999px;background:rgba(45,145,255,.18);border:1px solid rgba(90,175,255,.35);color:#fff;font-size:10px;font-weight:900;">{esc(m.get("part","-"))}</span>
    <span style="padding:3px 6px;border-radius:999px;background:{badge_bg};color:#fff;font-size:10px;font-weight:1000;">{badge}</span>
  </div>
  <img src="{esc(img)}" style="width:58px;height:58px;border-radius:50%;object-fit:cover;border:2px solid #7ec8ff;background:#111;box-shadow:0 0 10px rgba(80,170,255,.35);">
  <div style="margin-top:6px;color:#fff;font-size:14px;font-weight:1000;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;text-shadow:0 2px 0 #000;">{esc(m.get("name","-"))}</div>
  <div style="color:#dff2ff;font-size:10px;font-weight:800;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{esc(sid)}</div>
  <a href="{esc(soop_url)}" target="_blank" style="display:inline-block;margin-top:6px;padding:5px 8px;border-radius:999px;background:#081c33;border:1px solid #2b88df;color:#fff;font-size:11px;font-weight:900;text-decoration:none;">SOOP</a>
</div>"""

def render_members(members, live_map):
    def sorted_live_first(arr):
        return sorted(arr, key=lambda m: 0 if is_live(m, live_map) else 1)

    unique = unique_members_by_soop_id(members)
    leaders = [m for m in unique if is_leader_member(m)]
    regulars = [m for m in unique if not is_leader_member(m)]
    star = [m for m in regulars if m.get("part") == "스타부"]
    excel = [m for m in regulars if m.get("part") == "엑셀부"]
    live_count = sum(1 for m in unique if is_live(m, live_map))

    summary = f"""<div style="padding:9px 8px;margin-bottom:8px;border-radius:12px;background:rgba(255,255,255,.045);color:#dff2ff;font-size:12px;font-weight:900;text-align:center;">
전체 {len(unique)}명 · 수장 {len(leaders)}명 · 스타부 {len(star)}명 · 엑셀부 {len(excel)}명 · LIVE {live_count}명
</div>"""

    leader_html = "".join(member_card(m, live_map, True) for m in sorted_live_first(leaders))
    if not leader_html:
        leader_html = '<div style="padding:16px;color:#dff2ff;font-weight:900;text-align:center;">수장 데이터 없음</div>'
    leader_wrap = f'<div style="text-align:center;">{leader_html}</div>'

    all_html = "".join(member_card(m, live_map) for m in sorted_live_first(regulars))
    star_html = "".join(member_card(m, live_map) for m in sorted_live_first(star))
    excel_html = "".join(member_card(m, live_map) for m in sorted_live_first(excel))

    return summary + section("👑 수장", leader_wrap, True) + section("스타부", star_html, False) + section("엑셀부", excel_html, False)

def render_notice(notice_json):
    raw = []
    if isinstance(notice_json, list):
        raw = notice_json
    elif isinstance(notice_json, dict):
        for key in ("items", "notices", "posts"):
            if isinstance(notice_json.get(key), list):
                raw = notice_json[key]
                break
        if not raw and isinstance(notice_json.get("data"), list):
            raw = notice_json["data"]
        if not raw and isinstance(notice_json.get("data"), dict):
            raw = notice_json["data"].get("items") or notice_json["data"].get("content") or []

    if not raw:
        return '<div style="padding:16px;color:#dff2ff;font-weight:900;text-align:center;">표시할 공지가 없습니다.</div>'

    def pick_author(n):
        def clean_author_value(v):
            if isinstance(v, dict):
                for kk in ("name", "nickname", "nick", "userName", "bjName", "memberName", "displayName"):
                    vv = str(v.get(kk) or "").strip()
                    if vv:
                        return vv
                return ""
            if isinstance(v, list):
                return ""
            return str(v or "").strip()

        for k in ("author", "writer", "nickname", "nick", "name", "userName", "bjName", "memberName"):
            v = clean_author_value(n.get(k))
            if v and not v.startswith("{"):
                return v
        return ""

    def split_author_title(title, author):
        t = str(title or "제목 없음").strip()
        # V10 방식: 제목 안의 [멤버 공지]를 최우선으로 멤버 배지와 제목으로 분리
        m = re.match(r"^\s*\[\s*([^\[\]]+?)\s*공지\s*\]\s*(.*)$", t)
        if m:
            a = m.group(1).strip()
            rest = (m.group(2) or "").strip()
            if not rest:
                rest = "공지"
            return a, rest
        m = re.match(r"^\s*\[\s*([^\[\]]+?)\s*\]\s*(.*)$", t)
        if m:
            a = m.group(1).strip()
            rest = (m.group(2) or "").strip() or t
            return a, rest
        return (author or "공지"), t

    def clean_notice_content(content):
        c = str(content or "본문 수집 대기 또는 원문에서 확인")
        c = re.sub(r"<script.*?</script>", "", c, flags=re.I | re.S)
        c = re.sub(r"<style.*?</style>", "", c, flags=re.I | re.S)
        # 이미지가 와이고수 폭을 밀지 않게 강제 보정
        c = re.sub(r"<img\b", '<img style="max-width:100%;height:auto;border-radius:10px;margin:6px 0;"', c, flags=re.I)
        if c.strip() in ("", "-", "None", "null"):
            c = "본문 수집 대기 또는 원문에서 확인"
        return c

    blocks = []
    for n in raw[:10]:
        title_raw = n.get("title") or n.get("subject") or "제목 없음"
        author = pick_author(n)
        author, title = split_author_title(title_raw, author)
        content = n.get("content") or n.get("body") or n.get("html") or n.get("summary") or "본문 수집 대기 또는 원문에서 확인"
        content = clean_notice_content(content)
        blocks.append(f'''
<details style="margin:0 0 9px;padding:0;border:1px solid rgba(159,123,255,.62);border-radius:15px;background:linear-gradient(135deg,rgba(45,145,255,.13),rgba(0,0,0,.24));overflow:hidden;box-shadow:0 0 10px rgba(159,123,255,.18);box-sizing:border-box;">
  <summary style="list-style:none;cursor:pointer;padding:11px 12px;background:rgba(8,21,37,.88);border-bottom:1px solid rgba(159,123,255,.32);box-sizing:border-box;">
    <div style="display:flex;align-items:center;gap:8px;min-width:0;">
      <span style="flex:0 0 auto;display:inline-block;padding:5px 8px;border-radius:999px;background:#12345c;border:1px solid #9f7bff;color:#fff;font-size:11px;font-weight:1000;text-shadow:0 1px 0 #000;max-width:92px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{esc(author)}</span>
      <span style="flex:1 1 auto;min-width:0;color:#fff;font-size:16px;line-height:1.35;font-weight:1000;letter-spacing:-.4px;text-shadow:0 2px 0 #000,0 0 8px rgba(80,170,255,.42);word-break:keep-all;">{esc(title)}</span>
    </div>
  </summary>
  <div style="padding:10px 11px 12px;background:#071526;box-sizing:border-box;">
    <div style="margin-top:0;padding:12px;border-radius:13px;background:rgba(0,0,0,.24);color:#f3f9ff;font-size:13px;line-height:1.62;word-break:break-word;box-sizing:border-box;">{content}</div>
  </div>
</details>''')
    return "".join(blocks)

def render_rank_card(card):
    if not isinstance(card, dict):
        return '<div style="padding:16px;text-align:center;color:#dff2ff;font-weight:900;">별풍선표 데이터 없음</div>'

    if card.get("month_reset"):
        msg = card.get("message") or "월초 집계 초기화 중입니다. 풍투데이 월간 데이터 반영 대기중입니다."
        return f"""<div style="padding:18px;border-radius:16px;background:rgba(0,0,0,.28);border:1px solid rgba(90,175,255,.28);text-align:center;color:#fff;font-size:15px;font-weight:1000;line-height:1.6;">
📢 {esc(msg)}<br><span style="color:#dff2ff;font-size:12px;">풍투데이 데이터 안정화 후 자동 집계됩니다.</span>
</div>"""

    rows = card.get("members") or []
    if not rows:
        return '<div style="padding:16px;text-align:center;color:#dff2ff;font-weight:900;">별풍선표 데이터 없음</div>'

    head = f"""
<div style="border-radius:18px;overflow:hidden;border:1px solid rgba(90,175,255,.35);background:#111923;box-shadow:0 0 14px rgba(80,170,255,.20);">
  <div style="padding:14px;background:linear-gradient(135deg,#2798ff,#07111f);text-align:center;">
    <div style="color:#fff;font-size:26px;font-weight:1000;text-shadow:0 2px 0 #000;">{esc(card.get("crew",""))}</div>
    <div style="margin-top:6px;color:#dff2ff;font-size:12px;font-weight:900;">월간 평균 별풍선</div>
    <div style="color:#7dc7ff;font-size:30px;font-weight:1000;text-shadow:0 2px 0 #000;">{esc(card.get("avg","-"))}</div>
  </div>
  <div style="display:flex;background:#0b0d16;color:#dff2ff;font-size:11px;font-weight:1000;border-bottom:1px solid rgba(255,255,255,.08);">
    <div style="width:38px;padding:8px 4px;text-align:center;">순위</div>
    <div style="flex:1;padding:8px 4px;text-align:left;">멤버</div>
    <div style="width:70px;padding:8px 4px;text-align:right;">오늘</div>
    <div style="width:96px;padding:8px 8px;text-align:right;">월간</div>
  </div>
"""
    body = []
    for r in rows:
        body.append(f"""
  <div style="display:flex;align-items:center;border-bottom:1px solid rgba(255,255,255,.06);background:rgba(255,255,255,.015);font-weight:900;">
    <div style="width:38px;padding:9px 4px;text-align:center;color:#a7cfff;">{esc(r.get("rank",""))}</div>
    <div style="flex:1;min-width:0;padding:9px 4px;text-align:left;color:#fff;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{esc(r.get("name",""))}</div>
    <div style="width:70px;padding:9px 4px;text-align:right;color:#ffd34f;white-space:nowrap;">{esc(r.get("today","-"))}</div>
    <div style="width:96px;padding:9px 8px;text-align:right;color:#7dc7ff;white-space:nowrap;">{esc(r.get("month","-"))}</div>
  </div>""")
    return head + "".join(body) + "</div>"

def render_leader_rank_card(rank_json):
    if not isinstance(rank_json, dict):
        return ""
    leader = rank_json.get("leader") or {}
    if not leader:
        return ""
    name = leader.get("name", "철구형")
    today = leader.get("today", "0")
    month = leader.get("month", "0")
    sid = leader.get("soop_id", "y1026")
    return f"""
<div style="margin-bottom:10px;border-radius:18px;overflow:hidden;border:1px solid rgba(255,211,79,.45);background:linear-gradient(135deg,rgba(255,211,79,.16),rgba(0,0,0,.28));box-shadow:0 0 14px rgba(255,211,79,.18);text-align:center;">
  <div style="padding:12px;background:linear-gradient(135deg,#ffd34f,#4a3100);color:#fff;font-size:20px;font-weight:1000;text-shadow:0 2px 0 #000;">👑 수장 별풍선</div>
  <div style="padding:14px 12px 15px;">
    <div style="color:#fff;font-size:21px;font-weight:1000;text-shadow:0 2px 0 #000;">{esc(name)}</div>
    <div style="margin-top:3px;color:#bda870;font-size:11px;font-weight:900;">{esc(sid)}</div>
    <div style="display:flex;justify-content:center;gap:10px;margin-top:12px;flex-wrap:wrap;">
      <div style="min-width:118px;padding:9px 10px;border-radius:13px;background:rgba(0,0,0,.25);border:1px solid rgba(255,211,79,.28);">
        <div style="color:#dff2ff;font-size:11px;font-weight:900;">오늘</div>
        <div style="color:#ffd34f;font-size:18px;font-weight:1000;text-shadow:0 2px 0 #000;">{esc(today)}</div>
      </div>
      <div style="min-width:142px;padding:9px 10px;border-radius:13px;background:rgba(0,0,0,.25);border:1px solid rgba(255,211,79,.28);">
        <div style="color:#dff2ff;font-size:11px;font-weight:900;">월간</div>
        <div style="color:#ffd34f;font-size:18px;font-weight:1000;text-shadow:0 2px 0 #000;">{esc(month)}</div>
      </div>
    </div>
  </div>
</div>"""

def render_rank(rank_json):
    msg = ""
    if isinstance(rank_json, dict) and rank_json.get("month_reset"):
        msg = f"""<div style="margin-bottom:9px;padding:10px;border-radius:12px;background:rgba(255,211,79,.12);border:1px solid rgba(255,211,79,.35);color:#fff;font-size:13px;font-weight:1000;text-align:center;">📢 {esc(rank_json.get("message","월초 집계 초기화 중입니다."))}</div>"""
    leader_card = render_leader_rank_card(rank_json)
    excel = render_rank_card(rank_json.get("excel") if isinstance(rank_json, dict) else {})
    star = render_rank_card(rank_json.get("star") if isinstance(rank_json, dict) else {})
    updated = rank_json.get("updated_at","-") if isinstance(rank_json, dict) else "-"
    used = rank_json.get("used_month","-") if isinstance(rank_json, dict) else "-"
    return f"""
<div style="padding:8px 8px;margin-bottom:8px;border-radius:12px;background:rgba(255,255,255,.045);color:#dff2ff;font-size:12px;font-weight:900;text-align:center;">갱신 {esc(updated)} · 기준 {esc(used)}</div>
{msg}
{leader_card}
{section("엑셀부 별풍선표", excel, True)}
{section("스타부 별풍선표", star, False)}
"""

def render_schedule(schedule_json):
    raw = []
    if isinstance(schedule_json, list):
        raw = schedule_json
    elif isinstance(schedule_json, dict):
        for key in ("items", "schedules", "events"):
            if isinstance(schedule_json.get(key), list):
                raw = schedule_json[key]
                break
        if not raw and isinstance(schedule_json.get("data"), list):
            raw = schedule_json["data"]

    if not raw:
        return '<div style="padding:16px;color:#dff2ff;font-weight:900;text-align:center;">표시할 일정이 없습니다.</div>'

    blocks = []
    for s in raw[:20]:
        title = s.get("title") or s.get("name") or s.get("subject") or "일정"
        date = s.get("date") or s.get("datetime") or s.get("startAt") or s.get("start_at") or ""
        kind = s.get("type") or s.get("kind") or s.get("category") or "일정"
        dday = s.get("dday") or ""
        badge_text = str(dday or kind)
        badge_style = "background:#168fff;color:#fff;"
        if str(dday).strip().upper() in ("TODAY", "D-DAY", "D-0"):
            badge_style = "background:#ff3b3b;border:1px solid #ff8a8a;color:#fff;box-shadow:0 0 12px rgba(255,0,0,.40);"
        blocks.append(f'''
<div style="margin:8px 0;padding:12px;border-radius:14px;background:rgba(0,0,0,.25);border:1px solid rgba(90,175,255,.25);">
  <div style="margin-bottom:7px;"><span style="display:inline-block;padding:4px 8px;border-radius:999px;{badge_style}font-size:11px;font-weight:1000;">{esc(badge_text)}</span></div>
  <div style="color:#fff;font-size:14px;font-weight:1000;line-height:1.45;">{esc(title)}</div>
  <div style="margin-top:6px;color:#dff2ff;font-size:12px;font-weight:900;">{esc(date)}</div>
</div>''')
    return "".join(blocks)

def main():
    members = load_json("cnine_members.json", [])
    live = load_json("live_status.json", {})
    notice = load_json("notice_status.json", {})
    rank = load_json("ranking_data.json", {})
    schedule = load_json("schedule_status.json", {})

    live_map = get_live_map(live)
    unique_members = unique_members_by_soop_id(members)
    live_count = sum(1 for m in unique_members if is_live(m, live_map))
    updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    dashboard_notice = read_dashboard_notice()

    main_body = f"""
<div style="border:1px solid rgba(90,175,255,.25);border-radius:16px;background:rgba(0,0,0,.22);padding:10px;">
  {metric("전체 멤버", f"{len(unique_members)}명")}
  {metric("현재 LIVE", f"{live_count}명")}
  {metric("집계시간", updated)}
  {render_dashboard_notice(dashboard_notice)}
  {render_self_verify_card()}
</div>"""

    html_out = f"""<div style="width:100%;max-width:760px;margin:0 auto;background:radial-gradient(circle at top,rgba(45,145,255,.22),transparent 34%),linear-gradient(180deg,#05070d 0%,#071426 52%,#030507 100%);padding:8px;box-sizing:border-box;font-family:Arial,'Malgun Gothic',sans-serif;color:#fff;overflow:hidden;border-radius:18px;border:1px solid rgba(90,175,255,.45);">
  <div style="padding:18px 10px 16px;text-align:center;border:1px solid rgba(90,175,255,.55);border-radius:18px;background:linear-gradient(135deg,rgba(25,125,255,.28),rgba(0,0,0,.70));box-shadow:0 0 18px rgba(40,145,255,.25);">
    <img src="{BASE_URL}/assets//crew_logos/cninelogo.png?v=9999" style="display:block;width:112px;max-width:45%;height:auto;margin:0 auto 8px;filter:drop-shadow(0 0 8px rgba(255,255,255,.30));">
    <div style="font-size:27px;line-height:1.05;font-weight:1000;color:#fff;text-shadow:0 0 9px rgba(75,170,255,.95),0 3px 0 #002b55,0 8px 18px #000;">CNINE DASHBOARD</div>
    <div style="display:inline-block;margin-top:9px;padding:6px 12px;border-radius:999px;color:#fff;font-size:12px;font-weight:900;border:1px solid rgba(105,185,255,.55);background:rgba(0,18,38,.50);">씨나인 통합 현황판</div>
  </div>

  {section("메인 현황", main_body, True, "#2f9bff")}
  {section("멤버 현황판", render_members(members, live_map), False, "#19c2ff")}
  {section("씨나인 별풍선표", render_rank(rank), False, "#2798ff")}
  {section("SOOP 공지", render_notice(notice), False, "#9f7bff")}
  {section("씨나인 일정", render_schedule(schedule), False, "#7dc7ff")}

  <div style="margin-top:12px;text-align:center;color:#7ec8ff;font-size:11px;font-weight:800;text-shadow:0 0 6px rgba(126,200,255,.35);">{esc(WATERMARK)}</div>
  <div style="margin-top:5px;text-align:center;color:#8fcfff;font-size:10px;font-weight:700;">자동 변환: {esc(updated)}</div>
</div>"""

    paste_txt = clean_html_for_wago(html_out)

    with open(OUT_HTML, "w", encoding="utf-8") as f:
        f.write(html_out)

    with open(OUT_TXT, "w", encoding="utf-8") as f:
        f.write(paste_txt)

    print("완료:", OUT_HTML)
    print("완료:", OUT_TXT)
    print("멤버:", len(unique_members), "LIVE:", live_count)
    print("와이고수에는", OUT_TXT, "내용을 전체 복사해서 붙여넣으면 됩니다.")

if __name__ == "__main__":
    main()
