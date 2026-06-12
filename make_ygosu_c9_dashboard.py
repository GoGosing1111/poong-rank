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
# C9 메인 포스터는 ZIP 안의 assets/c9_main_banner.png 를 GitHub 저장소 assets 폴더에 올리면 와이고수에서 바로 출력됩니다.
BANNER_IMAGE_URL = f"{BASE_URL}/assets/c9_main_banner.png"
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

def fmt_short_dt(v=None):
    """2026-06-12 00:54:03 -> 26-06-12 00:54"""
    if v is None:
        v = datetime.now()
    if isinstance(v, datetime):
        return v.strftime("%y-%m-%d %H:%M")
    s = str(v or "").strip()
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2})", s)
    if m:
        return f"{m.group(1)[2:]}-{m.group(2)}-{m.group(3)} {m.group(4)}:{m.group(5)}"
    return datetime.now().strftime("%y-%m-%d %H:%M")


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
  <div style="padding:9px 11px;background:rgba(0,0,0,.20);border-bottom:1px solid rgba(255,211,79,.22);color:#7ec8ff;font-size:13px;font-weight:1000;text-align:left;text-shadow:0 2px 0 #000;">📢 특이사항</div>
  <div style="padding:10px 11px;color:#fff;font-size:13px;font-weight:900;line-height:1.55;text-align:left;word-break:break-word;max-height:94px;overflow:auto;box-sizing:border-box;">{body}</div>
</div>"""

def render_self_verify_card():
    verify_url = "https://m.sooplive.com/statistics/a/watch/?szModule=UserLiveWatchTimeData&szMethod=watch"

    # 리캡 셀프 인증 JS. GitHub 최상단에 soop_recap_check.js를 올려두면 동작한다.
    auto_verify_js = f"{BASE_URL}/soop_recap_check.js?v=2026060316"

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

&lt;button id='btn'&gt;📋 리캡 인증 코드 복사&lt;/button&gt;

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
    <span style="color:#7ec8ff;font-weight:1000;">A-염보성!! / [BJ]케이</span> 기록을 자동 판독합니다.

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


def render_vodchat_card():
    """SOOP VOD/클립 다시보기 채팅 패널 북마크릿 카드.
    - 리캡 셀프인증과 동일한 iframe srcdoc 복사 버튼 방식 사용
    - 복사 코드는 짧은 loader 한 줄만 사용해서 와고 iframe 복사 실패를 줄임
    - 원본 UI 생성은 loader가 담당하고, CNINE 패치는 원본 UI 생성 이후 문구만 안전하게 변경
    """
    vod_url = "https://vod.sooplive.co.kr/"
    loader_js = f"{BASE_URL}/soop_vodchat_loader.js?v=2026061204"

    iframe_html = f"""<iframe height="48" frameborder="0" allow="clipboard-write" referrerpolicy="strict-origin-when-cross-origin" style="flex:1 1 160px;min-width:160px;width:0;border:0;border-radius:9px;overflow:hidden;" srcdoc="&lt;!doctype html&gt;
&lt;meta charset='utf-8'&gt;

&lt;style&gt;
body{{margin:0}}
button{{
  width:100%;
  height:48px;
  background:linear-gradient(135deg,#2f9bff,#635bff);
  color:#fff;
  border:0;
  border-radius:9px;
  font-size:14px;
  font-weight:900;
  cursor:pointer;
}}
&lt;/style&gt;

&lt;button id='btn'&gt;🎬 다시보기 채팅 코드 복사&lt;/button&gt;

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
var code = '!function(){{var s=document.createElement(\\'script\\');s.id=\\'c9-vodchat-loader\\';s.src=\\'{loader_js}\\';document.head.appendChild(s)}}();';

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
<div id="section_replay" style="margin-top:10px;border:1px solid rgba(126,200,255,.46);border-radius:15px;background:linear-gradient(135deg,rgba(47,155,255,.18),rgba(99,91,255,.16),rgba(0,0,0,.24));overflow:hidden;box-sizing:border-box;">
  <div style="padding:10px 12px;background:rgba(0,0,0,.24);border-bottom:1px solid rgba(126,200,255,.26);color:#7ec8ff;font-size:14px;font-weight:1000;text-align:left;text-shadow:0 2px 0 #000;">
    🎬 다시보기 채팅보기
  </div>

  <div style="padding:12px 11px;color:#fff;font-size:13px;font-weight:900;line-height:1.62;text-align:center;word-break:keep-all;box-sizing:border-box;">
    SOOP VOD·클립 페이지에서<br>
    <span style="color:#7ec8ff;font-weight:1000;">채팅 로그 / 후원 / 도전 / 대결</span>을 한 번에 확인합니다.

    <div style="margin-top:12px;display:flex;gap:8px;justify-content:center;align-items:stretch;flex-wrap:wrap;box-sizing:border-box;">
      {iframe_html}

      <a href="{vod_url}" target="_blank" rel="nofollow"
         style="flex:1 1 160px;min-width:160px;height:48px;display:flex;align-items:center;justify-content:center;border-radius:9px;background:#0ea5e9;color:#fff;font-size:14px;font-weight:1000;text-decoration:none;box-sizing:border-box;">
        🔍 SOOP 다시보기 열기
      </a>
    </div>

    <div style="margin-top:10px;color:#cbd5e1;font-size:11px;font-weight:800;line-height:1.45;">
      ※ VOD/클립 페이지에서 주소창에 <span style="color:#fff;">javascript:</span> 입력 후 복사한 코드를 붙여넣고 실행하세요.<br>
      ※ 다시보기 툴 제작자 : 티큐양봉피꺼솟.
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

def section(title, body, open_attr=False, color="#2f9bff"):
    open_text = " open" if open_attr else ""
    # v10 HTML 기준: 파란 네온/둥근 엣지/어두운 남청 배경
    return f"""
<details{open_text} style="margin:10px 0 13px;padding:0;border:1px solid {color};border-radius:18px;background:#071426;overflow:hidden;box-sizing:border-box;box-shadow:0 0 14px {color}73;">
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
    badge_bg = "#1088ff" if live else "#333"
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
<details style="margin:0 0 9px;padding:0;border:1px solid #2f9bff;border-radius:15px;background:linear-gradient(135deg,rgba(45,145,255,.12),rgba(0,0,0,.24));overflow:hidden;box-shadow:0 0 10px rgba(47,155,255,.16);box-sizing:border-box;">
  <summary style="list-style:none;cursor:pointer;padding:11px 12px;background:rgba(12,12,12,.92);border-bottom:1px solid rgba(90,175,255,.30);box-sizing:border-box;">
    <div style="display:flex;align-items:center;gap:8px;min-width:0;">
      <span style="flex:0 0 auto;display:inline-block;padding:5px 8px;border-radius:999px;background:#081c33;border:1px solid #2f9bff;color:#fff;font-size:11px;font-weight:1000;text-shadow:0 1px 0 #000;max-width:92px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{esc(author)}</span>
      <span style="flex:1 1 auto;min-width:0;color:#fff;font-size:16px;line-height:1.35;font-weight:1000;letter-spacing:-.4px;text-shadow:0 2px 0 #000,0 0 8px rgba(80,170,255,.42);word-break:keep-all;">{esc(title)}</span>
    </div>
  </summary>
  <div style="padding:10px 11px 12px;background:#090909;box-sizing:border-box;">
    <div style="margin-top:0;padding:12px;border-radius:13px;background:rgba(0,0,0,.24);color:#f3f9ff;font-size:13px;line-height:1.62;word-break:break-word;box-sizing:border-box;">{content}</div>
  </div>
</details>''')
    return "".join(blocks)

def render_rank_card(card):
    if not isinstance(card, dict):
        return '<div style="padding:16px;text-align:center;color:#dff2ff;font-weight:900;">별풍선표 데이터 없음</div>'

    if card.get("month_reset"):
        msg = card.get("message") or "월초 집계 초기화 중입니다. 풍투데이 월간 데이터 반영 대기중입니다."
        return f"""<div style="padding:18px;border-radius:16px;background:rgba(0,0,0,.32);border:1px solid rgba(90,175,255,.30);text-align:center;color:#fff;font-size:15px;font-weight:1000;line-height:1.6;">
📢 {esc(msg)}<br><span style="color:#dff2ff;font-size:12px;">풍투데이 데이터 안정화 후 자동 집계됩니다.</span>
</div>"""

    rows = card.get("members") or []
    if not rows:
        return '<div style="padding:16px;text-align:center;color:#dff2ff;font-weight:900;">별풍선표 데이터 없음</div>'

    head = f"""
<div style="border-radius:18px;overflow:hidden;border:1px solid rgba(212,175,55,.40);background:#111;box-shadow:0 0 16px rgba(212,175,55,.18);">
  <div style="padding:14px;background:linear-gradient(135deg,#2f9bff,#2a1800 70%,#060606);text-align:center;">
    <div style="color:#fff;font-size:26px;font-weight:1000;text-shadow:0 2px 0 #000;">{esc(card.get("crew",""))}</div>
    <div style="margin-top:6px;color:#dff2ff;font-size:12px;font-weight:900;">월간 평균 별풍선</div>
    <div style="color:#dff2ff;font-size:30px;font-weight:1000;text-shadow:0 2px 0 #000,0 0 8px rgba(255,215,110,.55);">{esc(card.get("avg","-"))}</div>
  </div>
  <div style="display:flex;background:#0b0b0b;color:#d8c99b;font-size:11px;font-weight:1000;border-bottom:1px solid rgba(255,255,255,.08);">
    <div style="width:38px;padding:8px 4px;text-align:center;">순위</div>
    <div style="flex:1;padding:8px 4px;text-align:left;">멤버</div>
    <div style="width:70px;padding:8px 4px;text-align:right;">오늘</div>
    <div style="width:96px;padding:8px 8px;text-align:right;">월간</div>
  </div>
"""
    body = []
    for r in rows:
        rank = str(r.get("rank", ""))
        medal = "🥇" if rank == "1" else ("🥈" if rank == "2" else ("🥉" if rank == "3" else rank))
        bg = "rgba(45,145,255,.12)" if rank in ("1", "2", "3") else "rgba(255,255,255,.015)"
        body.append(f"""
  <div style="display:flex;align-items:center;border-bottom:1px solid rgba(255,255,255,.06);background:{bg};font-weight:900;">
    <div style="width:38px;padding:9px 4px;text-align:center;color:#7ec8ff;">{esc(medal)}</div>
    <div style="flex:1;min-width:0;padding:9px 4px;text-align:left;color:#fff;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{esc(r.get("name",""))}</div>
    <div style="width:70px;padding:9px 4px;text-align:right;color:#7ec8ff;white-space:nowrap;">{esc(r.get("today","-"))}</div>
    <div style="width:96px;padding:9px 8px;text-align:right;color:#dff2ff;white-space:nowrap;">{esc(r.get("month","-"))}</div>
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
  <div style="padding:12px;background:linear-gradient(135deg,#7ec8ff,#4a3100);color:#fff;font-size:20px;font-weight:1000;text-shadow:0 2px 0 #000;">👑 수장 별풍선</div>
  <div style="padding:14px 12px 15px;">
    <div style="color:#fff;font-size:21px;font-weight:1000;text-shadow:0 2px 0 #000;">{esc(name)}</div>
    <div style="margin-top:3px;color:#9ccfff;font-size:11px;font-weight:900;">{esc(sid)}</div>
    <div style="display:flex;justify-content:center;gap:10px;margin-top:12px;flex-wrap:wrap;">
      <div style="min-width:118px;padding:9px 10px;border-radius:13px;background:rgba(0,0,0,.25);border:1px solid rgba(255,211,79,.28);">
        <div style="color:#dff2ff;font-size:11px;font-weight:900;">오늘</div>
        <div style="color:#7ec8ff;font-size:18px;font-weight:1000;text-shadow:0 2px 0 #000;">{esc(today)}</div>
      </div>
      <div style="min-width:142px;padding:9px 10px;border-radius:13px;background:rgba(0,0,0,.25);border:1px solid rgba(255,211,79,.28);">
        <div style="color:#dff2ff;font-size:11px;font-weight:900;">월간</div>
        <div style="color:#7ec8ff;font-size:18px;font-weight:1000;text-shadow:0 2px 0 #000;">{esc(month)}</div>
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
<div style="padding:8px 8px;margin-bottom:8px;border-radius:12px;background:rgba(212,175,55,.08);border:1px solid rgba(212,175,55,.20);color:#dff2ff;font-size:12px;font-weight:900;text-align:center;">갱신 {esc(updated)} · 기준 {esc(used)}</div>
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
        badge_style = "background:#c89b2c;color:#fff;"
        if str(dday).strip().upper() in ("TODAY", "D-DAY", "D-0"):
            badge_style = "background:#ff3b3b;border:1px solid #ff8a8a;color:#fff;box-shadow:0 0 12px rgba(255,0,0,.40);"
        blocks.append(f'''
<div style="margin:8px 0;padding:12px;border-radius:14px;background:rgba(0,0,0,.25);border:1px solid rgba(90,175,255,.25);">
  <div style="margin-bottom:7px;"><span style="display:inline-block;padding:4px 8px;border-radius:999px;{badge_style}font-size:11px;font-weight:1000;">{esc(badge_text)}</span></div>
  <div style="color:#fff;font-size:14px;font-weight:1000;line-height:1.45;">{esc(title)}</div>
  <div style="margin-top:6px;color:#dff2ff;font-size:12px;font-weight:900;">{esc(date)}</div>
</div>''')
    return "".join(blocks)

def render_hero_banner(updated, total_members, live_count):
    logo_url = f"{BASE_URL}/assets//crew_logos/cninelogo.png?v=9999"
    contact_url = "https://ygosu.com/msg/?m2=write&member=152117"
    short_updated = fmt_short_dt(updated)
    return f"""
  <div id="section_top" style="position:relative;padding:18px 10px 16px;text-align:center;border:1px solid rgba(90,175,255,.55);border-radius:18px;background:linear-gradient(135deg,rgba(25,125,255,.28),rgba(0,0,0,.70));box-shadow:0 0 18px rgba(40,145,255,.25);">
    <div style="position:absolute;right:10px;top:9px;display:flex;align-items:center;gap:7px;z-index:2;">
      <span style="display:inline-block;padding:6px 9px;border-radius:999px;background:rgba(0,18,38,.48);border:1px solid rgba(105,185,255,.35);color:#9ccfff;font-size:11px;font-weight:900;line-height:1;white-space:nowrap;">{esc(short_updated)}</span>
      <a href="{contact_url}" target="_blank" rel="nofollow" style="display:inline-flex;align-items:center;justify-content:center;min-height:26px;padding:6px 10px;border-radius:999px;background:linear-gradient(135deg,#2f9bff,#635bff);border:1px solid rgba(255,255,255,.22);color:#fff;font-size:11px;font-weight:1000;text-decoration:none;line-height:1;box-shadow:0 0 12px rgba(47,155,255,.30);">📩 관리자 문의</a>
    </div>
    <img src="{logo_url}" style="display:block;width:112px;max-width:45%;height:auto;margin:0 auto 8px;filter:drop-shadow(0 0 8px rgba(255,255,255,.30));">
    <div style="font-size:27px;line-height:1.05;font-weight:1000;color:#fff;text-shadow:0 0 9px rgba(75,170,255,.95),0 3px 0 #002b55,0 8px 18px #000;">CNINE DASHBOARD</div>
    <div style="display:inline-block;margin-top:9px;padding:6px 12px;border-radius:999px;color:#fff;font-size:12px;font-weight:900;border:1px solid rgba(105,185,255,.55);background:rgba(0,18,38,.50);">씨나인 통합 현황판</div>
  </div>"""



def render_welcome_popup_iframe():
    """와이고수 iframe srcdoc 팝업.
    - 본문에 끼워지는 방식이 아니라 대시보드 전체 위에 absolute overlay로 덮음
    - 닫기/오늘 하루 안보기 클릭 시 iframe 자체를 숨겨서 아래 본문 클릭 가능
    """
    srcdoc = """<!doctype html>
<html lang='ko'>
<head>
<meta charset='utf-8'>
<meta name='viewport' content='width=device-width, initial-scale=1.0'>
<style>
*{box-sizing:border-box}
html,body{margin:0;padding:0;width:100%;height:100%;background:transparent;font-family:Arial,'Malgun Gothic',sans-serif;color:#fff;overflow:hidden}
.popup-overlay{
  position:fixed;inset:0;z-index:9999;
  display:flex;align-items:flex-start;justify-content:center;
  background:rgba(0,0,0,.62);
  backdrop-filter:blur(5px);
  -webkit-backdrop-filter:blur(5px);
  padding:42px 14px 14px;
}
.popup-box{
  width:min(94vw,520px);
  border-radius:24px;
  overflow:hidden;
  border:1px solid rgba(126,200,255,.60);
  background:radial-gradient(circle at top left,rgba(47,155,255,.30),transparent 38%),linear-gradient(180deg,#0b1830,#05070d);
  box-shadow:0 24px 70px rgba(0,0,0,.78),0 0 28px rgba(47,155,255,.42);
  text-align:center;
}
.popup-head{
  padding:22px 18px 14px;
  background:linear-gradient(135deg,rgba(47,155,255,.22),rgba(255,79,114,.14));
  border-bottom:1px solid rgba(255,255,255,.10);
}
.badge{
  display:inline-block;
  padding:6px 12px;
  border-radius:999px;
  border:1px solid rgba(126,200,255,.55);
  background:rgba(0,0,0,.25);
  color:#7ec8ff;
  font-size:12px;
  font-weight:1000;
  box-shadow:0 0 13px rgba(126,200,255,.22);
}
.title{
  margin-top:12px;
  font-size:28px;
  line-height:1.1;
  font-weight:1000;
  color:#fff;
  text-shadow:0 0 12px rgba(126,200,255,.85),0 3px 0 #001b36;
}
.sub{
  margin-top:8px;
  color:#cfeaff;
  font-size:13px;
  font-weight:900;
  line-height:1.45;
}
.popup-body{padding:15px 16px 16px}
.grid{
  display:grid;
  grid-template-columns:1fr 1fr;
  gap:9px;
}
.item{
  min-height:74px;
  padding:12px 9px;
  border-radius:16px;
  border:1px solid rgba(255,255,255,.10);
  background:linear-gradient(135deg,rgba(255,255,255,.08),rgba(0,0,0,.18));
  text-align:left;
  color:#fff;
  cursor:pointer;
  font-family:inherit;
}
.item:hover{filter:brightness(1.15);border-color:rgba(126,200,255,.55)}
.ico{font-size:21px;line-height:1}
.item b{
  display:block;
  margin-top:6px;
  color:#fff;
  font-size:13px;
  font-weight:1000;
  text-shadow:0 2px 0 #000;
}
.item span{
  display:block;
  margin-top:4px;
  color:#b9d9f5;
  font-size:11px;
  font-weight:800;
  line-height:1.32;
}
.popup-actions{
  display:flex;
  gap:8px;
  padding:0 16px 16px;
}
.btn{
  flex:1;
  height:44px;
  border:0;
  border-radius:13px;
  color:#fff;
  font-size:13px;
  font-weight:1000;
  cursor:pointer;
}
.btn-close{background:linear-gradient(135deg,#2f9bff,#0b4f95)}
.btn-hide{background:linear-gradient(135deg,#475569,#111827)}
.footer{
  padding:9px 12px 13px;
  color:#9ccfff;
  font-size:10px;
  font-weight:800;
  border-top:1px solid rgba(255,255,255,.08);
}
.hidden{display:none!important}
@media(max-width:420px){
  .popup-overlay{padding-top:22px;align-items:flex-start}
  .title{font-size:23px}
  .grid{grid-template-columns:1fr}
  .popup-actions{flex-direction:column}
}
</style>
</head>
<body>
<div id='popup' class='popup-overlay'>
  <div class='popup-box'>
    <div class='popup-head'>
      <span class='badge'>⚡ CNINE DASHBOARD GUIDE</span>
      <div class='title'>어떤 기능들이<br>있는지 알아봐요</div>
      <div class='sub'>씨나인 현황판에서 자주 쓰는 기능을 한눈에 확인하세요.</div>
    </div>
    <div class='popup-body'>
      <div class='grid'>
        <button class='item nav-item' data-target='section_members' type='button'><div class='ico'>📡</div><b>LIVE 현황</b><span>멤버 방송 상태를 자동 표시</span></button>
        <button class='item nav-item' data-target='section_rank' type='button'><div class='ico'>⭐</div><b>월간 별풍선</b><span>엑셀부 · 스타부 집계표 확인</span></button>
        <button class='item nav-item' data-target='section_notice' type='button'><div class='ico'>📢</div><b>공지사항</b><span>씨나인 SOOP 공지 펼쳐보기</span></button>
        <button class='item nav-item' data-target='section_schedule' type='button'><div class='ico'>📅</div><b>씨나인 일정</b><span>TODAY 일정 자동 강조</span></button>
        <button class='item nav-item' data-target='section_main' type='button'><div class='ico'>🚨</div><b>리캡 셀프인증</b><span>SOOP 시청기록 인증 코드 복사</span></button>
        <button class='item nav-item' data-target='section_replay' type='button'><div class='ico'>🎬</div><b>다시보기 채팅</b><span>VOD 채팅 패널 코드 복사</span></button>
      </div>
    </div>
    <div class='popup-actions'>
      <button id='btnClose' class='btn btn-close' type='button'>확인했어요</button>
      <button id='btnHide' class='btn btn-hide' type='button'>오늘 하루 안보기</button>
    </div>
    <div class='footer'>CNINE Dashboard Developed by 유두위생크림</div>
  </div>
</div>
<script>
(function(){
  var key='c9_dashboard_popup_hide_until';

  function hidePopupOnly(){
    var p=document.getElementById('popup');
    if(p){ p.className='popup-overlay hidden'; }
    document.documentElement.style.display='none';
    document.body.style.display='none';
  }

  function hideFrame(){
    hidePopupOnly();
    try{
      var f = window.frameElement;
      if(f){
        f.style.display='none';
        f.style.height='0px';
        f.style.minHeight='0px';
      }
    }catch(e){}
  }

  function closePopup(){
    hideFrame();
  }

  function hideToday(){
    try{
      var tomorrow = Date.now() + 24*60*60*1000;
      localStorage.setItem(key, String(tomorrow));
    }catch(e){}
    hideFrame();
  }

  function init(){
    try{
      var until=localStorage.getItem(key);
      if(until && Number(until) > Date.now()){
        hideFrame();
        return;
      }
    }catch(e){}

    function goTarget(id){
      try{
        var el = window.parent.document.getElementById(id);
        if(el){
          if(String(el.tagName).toLowerCase()==='details'){ el.open = true; }
          var inner = el.querySelector ? el.querySelector('details') : null;
          if(inner){ inner.open = true; }
          el.scrollIntoView({behavior:'smooth', block:'start'});
        }
      }catch(e){}
      hideFrame();
    }

    var navs=document.querySelectorAll('.nav-item');
    for(var i=0;i<navs.length;i++){
      navs[i].addEventListener('click', function(e){
        e.preventDefault();
        e.stopPropagation();
        goTarget(this.getAttribute('data-target'));
      }, false);
    }

    var c=document.getElementById('btnClose');
    var h=document.getElementById('btnHide');

    if(c){
      c.addEventListener('click', function(e){
        e.preventDefault();
        e.stopPropagation();
        closePopup();
      }, false);
    }
    if(h){
      h.addEventListener('click', function(e){
        e.preventDefault();
        e.stopPropagation();
        hideToday();
      }, false);
    }

    // 혹시 버튼 이벤트가 막히는 환경 대비: 배경 클릭 시 닫기
    var p=document.getElementById('popup');
    if(p){
      p.addEventListener('click', function(e){
        if(e.target === p){ closePopup(); }
      }, false);
    }
  }

  if(document.readyState === 'loading'){
    document.addEventListener('DOMContentLoaded', init);
  }else{
    init();
  }

  window.closePopup = closePopup;
  window.hideToday = hideToday;
})();
</script>
</body>
</html>"""
    srcdoc = srcdoc.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")
    return f"""<iframe
  width="100%"
  height="100%"
  frameborder="0"
  scrolling="no"
  allow="clipboard-write"
  referrerpolicy="strict-origin-when-cross-origin"
  style="position:absolute;left:0;top:0;width:100%;height:100%;border:0;margin:0;border-radius:18px;overflow:hidden;background:transparent;z-index:9999;display:block;"
  srcdoc="{srcdoc}"></iframe>"""


def expand_card(title, subtitle, icon, body, color="#2f9bff", open_attr=False, anchor_id=""):
    """리캡 버튼 폭에 맞춘 전체폭 펼침 메뉴.

    핵심:
    - 메뉴 summary를 width:100%로 출력해서 좁은 2열 카드처럼 보이지 않게 함
    - 메뉴 세로 높이를 72px로 키워 얇아 보이지 않게 함
    - 펼친 내용도 바로 아래 전체폭으로 출력되어 잘리지 않음
    - JS 없이 details/summary만 사용
    """
    open_text = " open" if open_attr else ""
    return f"""
<details{open_text} id="{esc(anchor_id)}" style="display:block;width:100%;margin:0 0 10px 0;padding:0;box-sizing:border-box;">
  <summary style="list-style:none;cursor:pointer;display:flex;width:100%;min-height:72px;margin:0;padding:0 16px;border:1px solid {color};border-radius:14px;background:linear-gradient(135deg,rgba(25,125,255,.22),rgba(0,0,0,.48));box-shadow:0 0 13px {color}59;color:#fff;text-align:center;box-sizing:border-box;overflow:hidden;align-items:center;justify-content:center;gap:10px;">
    <span style="display:inline-block;font-size:24px;line-height:1;filter:drop-shadow(0 0 6px rgba(255,255,255,.28));">{icon}</span>
    <span style="display:inline-block;color:#fff;font-size:18px;font-weight:1000;line-height:1.15;text-shadow:0 0 8px rgba(80,170,255,.90),0 2px 0 #000;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{esc(title)}</span>
  </summary>
  <div style="display:block;width:100%;margin:9px 0 12px 0;padding:10px;background:#081525;border:1px solid {color};border-radius:16px;box-shadow:0 0 13px {color}33;box-sizing:border-box;text-align:left;overflow:hidden;">
    {body}
  </div>
</details>"""


def render_expand_cards(rank, members, live_map, notice, schedule):
    """리캡 아래 섹션을 앵커 점프가 아닌 2열 펼침 카드로 출력한다."""
    cards = [
        expand_card("월간 별풍선", "엑셀부 · 스타부 집계", "⭐", render_rank(rank), "#2f9bff", False, "section_rank"),
        expand_card("멤버 현황판", "LIVE · 파트별 현황", "👥", render_members(members, live_map), "#19c2ff", False, "section_members"),
        expand_card("공지사항", "씨나인 SOOP 공지", "📢", render_notice(notice), "#ff4b6e", False, "section_notice"),
        expand_card("씨나인 일정", "TODAY · 주요 일정", "📅", render_schedule(schedule), "#22c55e", False, "section_schedule"),
    ]
    return f"""
<div style="margin:10px 0 13px;padding:0;border:0;background:transparent;box-sizing:border-box;text-align:center;">
  {''.join(cards)}
</div>"""

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
  {render_dashboard_notice(dashboard_notice)}
  {render_self_verify_card()}
  {render_vodchat_card()}
</div>"""

    html_out = f"""<div style="position:relative;width:100%;max-width:760px;margin:0 auto;background:radial-gradient(circle at top,rgba(45,145,255,.22),transparent 34%),linear-gradient(180deg,#05070d 0%,#071426 52%,#030507 100%);padding:8px;box-sizing:border-box;font-family:Arial,'Malgun Gothic',sans-serif;color:#fff;overflow:hidden;border-radius:18px;border:1px solid rgba(90,175,255,.45);">
  {render_hero_banner(updated, len(unique_members), live_count)}
  {render_welcome_popup_iframe()}

  <div id="section_main">{section("메인 현황", main_body, True, "#2f9bff")}</div>
  {render_expand_cards(rank, members, live_map, notice, schedule)}

  <div style="margin-top:12px;text-align:center;color:#7ec8ff;font-size:11px;font-weight:800;text-shadow:0 0 6px rgba(80,170,255,.35);">{esc(WATERMARK)}</div>
  <div style="margin-top:5px;text-align:center;color:#9ccfff;font-size:10px;font-weight:700;">자동 변환: {esc(updated)}</div>
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
