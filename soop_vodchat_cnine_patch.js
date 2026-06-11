/* CNINE VOD TOOL UI PATCH
 * 원본 SOOP VOD 채팅 패널 로드 후 UI 문구/컬러를 CNINE 대시보드 톤으로 보정합니다.
 * 기능 로직은 건드리지 않고 DOM 텍스트와 스타일만 후처리합니다.
 */
(function () {
  'use strict';

  if (window.__CNINE_VOD_TOOL_PATCHED__) return;
  window.__CNINE_VOD_TOOL_PATCHED__ = true;

  var BRAND = 'CNINE VOD TOOL';
  var replaceMap = {
    '총 방송 시간': '방송 시간',
    '총 채팅 수': '채팅 수',
    '채팅 인원': '참여 인원',
    '상태': '분석 상태',
    '완료 ✨': '분석완료',
    '완료': '분석완료',
    '채팅 순위': '채팅 랭킹',
    '후원 순위': '후원 랭킹',
    '도전 순위': '도전 랭킹',
    '대결 순위': '대결 랭킹',
    '채팅 내역': '채팅 로그',
    '후원 내역': '후원 로그',
    '도전미션 내역': '도전 로그',
    '대결미션 내역': '대결 로그',
    '총 별풍선': '별풍선 합계',
    '총 도전미션': '도전 합계',
    '총 대결미션': '대결 합계',
    '후원 인원': '후원 참여',
    '도전 인원': '도전 참여',
    '대결 인원': '대결 참여'
  };

  function injectStyle() {
    if (document.getElementById('cnine-vod-tool-style')) return;
    var style = document.createElement('style');
    style.id = 'cnine-vod-tool-style';
    style.textContent = `
      :root{
        --cnine-blue:#2f9bff;
        --cnine-sky:#7ec8ff;
        --cnine-deep:#071426;
        --cnine-panel:#0b1220;
        --cnine-line:rgba(126,200,255,.30);
      }

      /* 원본 패널이 어떤 클래스명을 쓰든 최대한 안전하게 후처리 */
      body [style*="#00"], body [style*="#10"], body [style*="#16a"], body [style*="rgb(0"], body [style*="rgb(16"]{
        --patched-by-cnine:1;
      }

      /* 우측 패널/모달 계열 */
      body div[style*="position: fixed"],
      body div[style*="position:fixed"]{
        font-family:Arial,'Malgun Gothic',sans-serif !important;
      }

      .cnine-vod-badge{
        display:inline-flex;
        align-items:center;
        justify-content:center;
        gap:5px;
        margin-right:8px;
        padding:4px 9px;
        border-radius:999px;
        background:linear-gradient(135deg,rgba(47,155,255,.22),rgba(99,91,255,.18));
        border:1px solid rgba(126,200,255,.50);
        color:#dff2ff;
        font-size:11px;
        font-weight:1000;
        letter-spacing:.2px;
        text-shadow:0 1px 0 #000;
        box-shadow:0 0 12px rgba(47,155,255,.24);
        white-space:nowrap;
      }

      .cnine-vod-watermark{
        position:absolute;
        right:18px;
        bottom:10px;
        z-index:999999;
        pointer-events:none;
        color:rgba(126,200,255,.34);
        font-size:10px;
        font-weight:900;
        letter-spacing:.3px;
        text-shadow:0 1px 0 #000;
      }

      /* 버튼/뱃지 계열을 블루 네온 쪽으로 약하게 보정 */
      button, input, select{
        font-family:Arial,'Malgun Gothic',sans-serif !important;
      }
      button[style*="background"], a[style*="background"]{
        transition:filter .12s ease, transform .12s ease !important;
      }
      button[style*="background"]:hover, a[style*="background"]:hover{
        filter:brightness(1.12) !important;
      }

      /* 검색창/카드 외곽선 보정 */
      input[type="text"], input[type="search"], input:not([type]){
        border-color:rgba(126,200,255,.22) !important;
      }
    `;
    document.head.appendChild(style);
  }

  function textReplace(root) {
    if (!root || !root.querySelectorAll) return;
    var walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
      acceptNode: function (node) {
        if (!node.nodeValue || !node.nodeValue.trim()) return NodeFilter.FILTER_REJECT;
        var p = node.parentElement;
        if (!p) return NodeFilter.FILTER_REJECT;
        var tag = (p.tagName || '').toLowerCase();
        if (tag === 'script' || tag === 'style' || tag === 'textarea') return NodeFilter.FILTER_REJECT;
        return NodeFilter.FILTER_ACCEPT;
      }
    });
    var nodes = [];
    while (walker.nextNode()) nodes.push(walker.currentNode);
    nodes.forEach(function (node) {
      var v = node.nodeValue;
      Object.keys(replaceMap).forEach(function (k) {
        if (v.indexOf(k) !== -1) v = v.split(k).join(replaceMap[k]);
      });
      if (node.nodeValue !== v) node.nodeValue = v;
    });
  }

  function findVodPanel() {
    var candidates = Array.prototype.slice.call(document.querySelectorAll('body div'));
    var best = null;
    var bestScore = 0;
    candidates.forEach(function (el) {
      var txt = (el.innerText || '').slice(0, 1500);
      var score = 0;
      if (txt.indexOf('채팅') !== -1) score += 2;
      if (txt.indexOf('후원') !== -1) score += 1;
      if (txt.indexOf('도전') !== -1) score += 1;
      if (txt.indexOf('대결') !== -1) score += 1;
      if (txt.indexOf('방송 시간') !== -1 || txt.indexOf('총 방송 시간') !== -1) score += 2;
      var rect = el.getBoundingClientRect ? el.getBoundingClientRect() : {width:0,height:0};
      if (rect.width > 500 && rect.height > 300) score += 2;
      if (score > bestScore) { bestScore = score; best = el; }
    });
    return bestScore >= 4 ? best : null;
  }

  function addBrand(panel) {
    if (!panel || panel.querySelector('.cnine-vod-badge')) return;
    var titleTarget = null;
    var els = Array.prototype.slice.call(panel.querySelectorAll('div,span,b,strong,h1,h2,h3'));
    for (var i = 0; i < els.length; i++) {
      var t = (els[i].innerText || '').trim();
      var r = els[i].getBoundingClientRect ? els[i].getBoundingClientRect() : {width:0,height:0};
      if (t && t.length >= 4 && r.width > 120 && r.height > 16 && t.indexOf('랭킹') === -1 && t.indexOf('로그') === -1) {
        titleTarget = els[i];
        break;
      }
    }
    if (titleTarget) {
      var badge = document.createElement('span');
      badge.className = 'cnine-vod-badge';
      badge.textContent = '🎬 ' + BRAND;
      titleTarget.insertBefore(badge, titleTarget.firstChild);
    }
    if (!panel.querySelector('.cnine-vod-watermark')) {
      try { if (getComputedStyle(panel).position === 'static') panel.style.position = 'relative'; } catch(e) {}
      var wm = document.createElement('div');
      wm.className = 'cnine-vod-watermark';
      wm.textContent = 'CNINE Dashboard';
      panel.appendChild(wm);
    }
  }

  function polishPanel(panel) {
    if (!panel) return;
    panel.setAttribute('data-cnine-vod-tool', '1');
    try {
      panel.style.borderColor = 'rgba(126,200,255,.35)';
      panel.style.boxShadow = '0 24px 70px rgba(0,0,0,.70),0 0 24px rgba(47,155,255,.18)';
    } catch (e) {}

    var all = panel.querySelectorAll('*');
    for (var i = 0; i < all.length; i++) {
      var el = all[i];
      var txt = (el.textContent || '').trim();
      var style = el.getAttribute('style') || '';
      if (/완료|분석완료|회$|개$/.test(txt) || style.indexOf('green') !== -1 || style.indexOf('#00') !== -1) {
        try { el.style.color = '#7ec8ff'; } catch(e) {}
      }
      if (txt === '전체' || txt === '후원' || txt === '도전' || txt === '대결') {
        try {
          el.style.borderColor = 'rgba(126,200,255,.35)';
        } catch(e) {}
      }
    }
  }

  function runPatch() {
    injectStyle();
    textReplace(document.body);
    var panel = findVodPanel();
    if (panel) {
      addBrand(panel);
      polishPanel(panel);
    }
  }

  var timer = 0;
  function schedule() {
    clearTimeout(timer);
    timer = setTimeout(runPatch, 120);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', schedule);
  } else {
    schedule();
  }

  var mo = new MutationObserver(schedule);
  try { mo.observe(document.documentElement, {childList:true, subtree:true, characterData:true}); } catch(e) {}

  // 원본 패널 생성이 늦는 경우 대비
  var count = 0;
  var iv = setInterval(function(){
    runPatch();
    count += 1;
    if (count > 40) clearInterval(iv);
  }, 500);
})();
