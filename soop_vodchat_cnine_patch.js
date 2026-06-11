(function(){
  'use strict';

  if (window.__CNINE_VODCHAT_SKIN_V2__) return;
  window.__CNINE_VODCHAT_SKIN_V2__ = true;

  var MAP = {
    '채팅 순위': '채팅 랭킹',
    '후원 순위': '후원 랭킹',
    '도전 순위': '도전 랭킹',
    '대결 순위': '대결 랭킹',
    '채팅 내역': '채팅 로그',
    '후원 내역': '후원 로그',
    '도전미션 내역': '도전 로그',
    '대결미션 내역': '대결 로그',
    '총 방송 시간': '방송 시간',
    '총 채팅 수': '채팅 수',
    '채팅 인원': '참여 인원'
  };

  var EXACT_MAP = {
    '상태': '분석 상태',
    '완료 ✨': '수집완료',
    '완료': '수집완료',
    '분석완료': '수집완료'
  };

  var BAD_PHRASES = [
    '원본 패널 생성 후 CNINE 문구만 안전하게 적용됩니다.',
    '※ 원본 패널 생성 후 CNINE 문구만 안전하게 적용됩니다.'
  ];

  function isBadText(t){
    for (var i=0;i<BAD_PHRASES.length;i++){
      if (t.indexOf(BAD_PHRASES[i]) !== -1) return true;
    }
    return false;
  }

  function normalizeText(t){
    if (!t) return t;
    var s = t;

    if (/^(분석\s*){2,}$/.test(s.trim()) || /^(분석완료\s*){2,}$/.test(s.trim()) || /^(수집완료\s*){2,}$/.test(s.trim())) {
      return '수집완료';
    }

    var trim = s.trim();
    if (EXACT_MAP[trim]) {
      return s.replace(trim, EXACT_MAP[trim]);
    }

    Object.keys(MAP).forEach(function(k){
      if (s.indexOf(k) !== -1) s = s.split(k).join(MAP[k]);
    });

    return s;
  }

  function replaceText(){
    var walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, {
      acceptNode: function(node){
        var p = node.parentNode;
        if (!p) return NodeFilter.FILTER_REJECT;
        var tag = (p.nodeName || '').toLowerCase();
        if (tag === 'script' || tag === 'style' || tag === 'textarea' || tag === 'input') return NodeFilter.FILTER_REJECT;

        var v = node.nodeValue || '';
        if (isBadText(v)) return NodeFilter.FILTER_ACCEPT;
        if (/^(분석\s*){2,}$/.test(v.trim()) || /^(분석완료\s*){2,}$/.test(v.trim())) return NodeFilter.FILTER_ACCEPT;

        if (EXACT_MAP[v.trim()]) return NodeFilter.FILTER_ACCEPT;
        for (var k in MAP) if (v.indexOf(k) !== -1) return NodeFilter.FILTER_ACCEPT;
        return NodeFilter.FILTER_REJECT;
      }
    });

    var nodes = [];
    while (walker.nextNode()) nodes.push(walker.currentNode);

    nodes.forEach(function(n){
      var before = n.nodeValue || '';
      if (isBadText(before)) {
        var host = n.parentElement;
        if (host) {
          var box = host;
          for (var i=0;i<4 && box.parentElement;i++){
            var txt = (box.textContent || '').trim();
            var r = box.getBoundingClientRect ? box.getBoundingClientRect() : {height:0};
            if (txt.indexOf('원본 패널 생성 후') !== -1 && r.height < 90) break;
            box = box.parentElement;
          }
          try { box.remove(); } catch(e) { n.nodeValue = ''; }
        } else {
          n.nodeValue = '';
        }
        return;
      }

      var after = normalizeText(before);
      if (after !== before) n.nodeValue = after;
    });
  }

  function removeOldBadge(){
    Array.prototype.slice.call(document.querySelectorAll('div,span')).forEach(function(el){
      var txt = (el.textContent || '').trim();
      if (txt === '🎬 CNINE VOD TOOL' || txt === 'CNINE VOD TOOL') {
        var st = window.getComputedStyle(el);
        if (st.position === 'fixed' || st.position === 'absolute') el.remove();
      }
    });
  }

  function findPanel(){
    var candidates = Array.prototype.slice.call(document.querySelectorAll('body *')).filter(function(el){
      var t = el.textContent || '';
      if (t.length < 100) return false;
      if (!(t.indexOf('채팅 랭킹') !== -1 || t.indexOf('채팅 순위') !== -1)) return false;
      if (!(t.indexOf('채팅 로그') !== -1 || t.indexOf('채팅 내역') !== -1)) return false;
      var r = el.getBoundingClientRect();
      if (r.width < 420 || r.height < 240) return false;
      return true;
    });

    if (!candidates.length) return null;

    candidates.sort(function(a,b){
      var ar = a.getBoundingClientRect(), br = b.getBoundingClientRect();
      var as = ar.width * ar.height, bs = br.width * br.height;
      return bs - as;
    });

    // body/html처럼 너무 큰 영역은 제외하고 가장 큰 실제 패널을 선택
    for (var i=0;i<candidates.length;i++){
      var el = candidates[i];
      if (el === document.body || el === document.documentElement) continue;
      var r = el.getBoundingClientRect();
      if (r.width <= window.innerWidth + 5 && r.height <= window.innerHeight + 5) return el;
    }
    return candidates[0];
  }

  function nearestBox(el, maxUp){
    var cur = el;
    for (var i=0;i<maxUp && cur && cur.parentElement;i++){
      var r = cur.getBoundingClientRect ? cur.getBoundingClientRect() : {width:0,height:0};
      if (r.width >= 60 && r.height >= 24) return cur;
      cur = cur.parentElement;
    }
    return el;
  }

  function addClasses(){
    var panel = findPanel();
    if (panel) {
      panel.classList.add('cnine-vod-panel');

      if (!panel.querySelector('.cnine-vod-titlebar')) {
        var title = document.createElement('div');
        title.className = 'cnine-vod-titlebar';
        title.innerHTML = '<span>🎬 CNINE 다시보기 분석</span><em>VOD CHAT LOG</em>';
        panel.insertBefore(title, panel.firstChild);
      }
    }

    Array.prototype.slice.call(document.querySelectorAll('body *')).forEach(function(el){
      var text = (el.textContent || '').trim();
      if (!text) return;

      if (/^(방송 시간|채팅 수|참여 인원|분석 상태)$/.test(text)) {
        var box = nearestBox(el.parentElement || el, 4);
        if (box) box.classList.add('cnine-metric-card');
      }

      if (/^(수집완료)$/.test(text)) {
        var st = nearestBox(el, 3);
        if (st) st.classList.add('cnine-status-done');
      }

      if (/^(채팅 랭킹|후원 랭킹|도전 랭킹|대결 랭킹|채팅 로그|후원 로그|도전 로그|대결 로그)$/.test(text)) {
        var head = nearestBox(el, 3);
        if (head) head.classList.add('cnine-section-head');
      }

      if (/^[0-9,]+회$/.test(text)) {
        el.classList.add('cnine-count-pill');
      }
    });
  }

  function injectStyle(){
    if (document.getElementById('cnine-vodchat-skin-v2')) return;

    var css = document.createElement('style');
    css.id = 'cnine-vodchat-skin-v2';
    css.textContent = `
      .cnine-vod-panel{
        background:
          radial-gradient(circle at 8% 4%, rgba(78,168,255,.34), transparent 24%),
          radial-gradient(circle at 86% 12%, rgba(99,91,255,.26), transparent 30%),
          linear-gradient(180deg, #06172c 0%, #08111f 55%, #050812 100%) !important;
        border:1px solid rgba(78,168,255,.60) !important;
        box-shadow:0 18px 60px rgba(0,0,0,.55), 0 0 28px rgba(78,168,255,.32) !important;
        color:#f4fbff !important;
        border-radius:22px !important;
        overflow:hidden !important;
        font-family:Arial, "Malgun Gothic", sans-serif !important;
      }

      .cnine-vod-titlebar{
        display:flex;
        justify-content:space-between;
        align-items:center;
        gap:10px;
        padding:14px 16px;
        margin:-1px -1px 12px -1px;
        border-bottom:1px solid rgba(126,200,255,.26);
        background:linear-gradient(135deg, rgba(78,168,255,.22), rgba(7,20,38,.82));
        box-shadow:0 8px 24px rgba(0,0,0,.22);
      }
      .cnine-vod-titlebar span{
        color:#fff;
        font-size:18px;
        font-weight:1000;
        text-shadow:0 0 12px rgba(78,168,255,.75), 0 2px 0 #00172c;
        letter-spacing:-.4px;
      }
      .cnine-vod-titlebar em{
        color:#9fd2ff;
        font-size:11px;
        font-style:normal;
        font-weight:900;
        letter-spacing:.7px;
        padding:5px 8px;
        border:1px solid rgba(126,200,255,.36);
        border-radius:999px;
        background:rgba(0,0,0,.22);
      }

      .cnine-metric-card{
        background:linear-gradient(135deg, rgba(78,168,255,.14), rgba(0,0,0,.20)) !important;
        border:1px solid rgba(126,200,255,.34) !important;
        border-radius:15px !important;
        box-shadow:inset 0 0 0 1px rgba(255,255,255,.03), 0 0 14px rgba(78,168,255,.12) !important;
      }

      .cnine-status-done{
        color:#e9f7ff !important;
        background:linear-gradient(135deg,#2563eb,#0ea5e9) !important;
        border:1px solid rgba(126,200,255,.55) !important;
        border-radius:999px !important;
        padding:4px 9px !important;
        box-shadow:0 0 14px rgba(78,168,255,.32) !important;
      }

      .cnine-section-head{
        color:#ffffff !important;
        text-shadow:0 0 10px rgba(78,168,255,.70),0 2px 0 #00162b !important;
        border-bottom-color:rgba(126,200,255,.35) !important;
      }

      .cnine-count-pill{
        display:inline-block !important;
        min-width:54px !important;
        text-align:center !important;
        padding:3px 8px !important;
        border-radius:999px !important;
        color:#ffffff !important;
        background:linear-gradient(135deg,#1d4ed8,#0ea5e9) !important;
        border:1px solid rgba(126,200,255,.45) !important;
        box-shadow:0 0 12px rgba(78,168,255,.24) !important;
        font-weight:1000 !important;
      }

      .cnine-vod-panel button,
      .cnine-vod-panel [role="button"]{
        border-radius:12px !important;
        border-color:rgba(126,200,255,.32) !important;
      }

      .cnine-vod-panel input{
        background:#071426 !important;
        border:1px solid rgba(126,200,255,.30) !important;
        color:#fff !important;
        border-radius:12px !important;
      }

      .cnine-vod-panel ::-webkit-scrollbar{width:8px;height:8px}
      .cnine-vod-panel ::-webkit-scrollbar-track{background:#071426}
      .cnine-vod-panel ::-webkit-scrollbar-thumb{
        background:linear-gradient(180deg,#4ea8ff,#2563eb);
        border-radius:999px;
      }
    `;
    document.head.appendChild(css);
  }

  function run(){
    removeOldBadge();
    replaceText();
    injectStyle();
    addClasses();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', run);
  } else {
    run();
  }

  var timer = setInterval(run, 700);
  setTimeout(function(){ clearInterval(timer); }, 45000);

  try {
    var obs = new MutationObserver(function(){
      clearTimeout(window.__CNINE_VODCHAT_SKIN_TIMER__);
      window.__CNINE_VODCHAT_SKIN_TIMER__ = setTimeout(run, 120);
    });
    obs.observe(document.documentElement || document.body, {childList:true, subtree:true, characterData:true});
    setTimeout(function(){ try{ obs.disconnect(); }catch(e){} }, 90000);
  } catch(e) {}
})();
