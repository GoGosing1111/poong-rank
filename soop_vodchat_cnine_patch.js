/*
CNINE VOD patch - CSS only
- 티큐 원본 UI 유지
- 원본 패널 숨김/삭제/재생성 없음
- 문구 변경 + 색상/배경만 보정
*/
(function(){
  'use strict';

  if(window.__C9_VOD_CSS_ONLY_PATCH__) return;
  window.__C9_VOD_CSS_ONLY_PATCH__ = true;

  var STYLE_ID = 'c9-vod-css-only-style';

  var replacePairs = [
    ['채팅 순위', '채팅 랭킹'],
    ['채팅 내역', '채팅 로그'],
    ['후원 순위', '후원 랭킹'],
    ['후원 내역', '후원 로그'],
    ['도전 순위', '도전 랭킹'],
    ['도전미션 내역', '도전 로그'],
    ['대결 순위', '대결 랭킹'],
    ['대결미션 내역', '대결 로그'],
    ['완료 ✨', '수집완료']
  ];

  function addStyle(){
    if(document.getElementById(STYLE_ID)) return;

    var css = `
      .c9-vod-themed{
        background:linear-gradient(180deg,#071a31 0%,#071426 52%,#030711 100%)!important;
        border:1px solid rgba(78,168,255,.68)!important;
        box-shadow:0 0 0 1px rgba(78,168,255,.16),0 18px 44px rgba(0,0,0,.62),0 0 26px rgba(47,155,255,.25)!important;
      }
      .c9-vod-titlebar{
        display:flex!important;
        align-items:center!important;
        justify-content:space-between!important;
        gap:10px!important;
        padding:13px 16px!important;
        background:linear-gradient(135deg,#0b2849,#10265a 58%,#06101f)!important;
        border-bottom:1px solid rgba(126,200,255,.42)!important;
        color:#fff!important;
        font-family:Arial,'Malgun Gothic',sans-serif!important;
      }
      .c9-vod-titlebar b{
        font-size:18px!important;
        font-weight:1000!important;
        color:#fff!important;
        text-shadow:0 0 10px rgba(78,168,255,.58)!important;
        letter-spacing:-.5px!important;
      }
      .c9-vod-titlebar span{
        padding:5px 11px!important;
        border-radius:999px!important;
        border:1px solid rgba(126,200,255,.65)!important;
        color:#dff2ff!important;
        background:rgba(2,12,24,.62)!important;
        font-size:11px!important;
        font-weight:1000!important;
        letter-spacing:.4px!important;
      }
      .c9-vod-themed input,
      .c9-vod-themed select{
        background:#06101f!important;
        border:1px solid rgba(126,200,255,.35)!important;
        color:#eaf6ff!important;
      }
      .c9-vod-themed button{
        border-color:rgba(126,200,255,.35)!important;
      }
      .c9-vod-blue{
        background:linear-gradient(135deg,#1d6dff,#0ea5e9)!important;
        color:#fff!important;
        border-color:rgba(126,200,255,.35)!important;
        box-shadow:0 0 10px rgba(47,155,255,.24)!important;
      }
      .c9-vod-themed::-webkit-scrollbar,
      .c9-vod-themed *::-webkit-scrollbar{width:9px!important;height:9px!important}
      .c9-vod-themed::-webkit-scrollbar-thumb,
      .c9-vod-themed *::-webkit-scrollbar-thumb{
        background:linear-gradient(180deg,#4ea8ff,#1d6dff)!important;
        border-radius:999px!important;
      }
      .c9-vod-themed::-webkit-scrollbar-track,
      .c9-vod-themed *::-webkit-scrollbar-track{
        background:#06101f!important;
      }
    `;

    var s = document.createElement('style');
    s.id = STYLE_ID;
    s.textContent = css;
    document.head.appendChild(s);
  }

  function patchText(root){
    if(!root) return;
    var walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, null);
    var nodes = [];
    while(walker.nextNode()) nodes.push(walker.currentNode);

    nodes.forEach(function(n){
      var v = n.nodeValue || '';
      if(!v.trim()) return;

      if(v.indexOf('분석 분석') > -1 || v.indexOf('분석완료분석완료') > -1){
        n.nodeValue = '수집완료';
        return;
      }

      replacePairs.forEach(function(p){
        if(v.indexOf(p[0]) > -1){
          v = v.split(p[0]).join(p[1]);
        }
      });

      n.nodeValue = v;
    });
  }

  function scorePanel(el){
    if(!el || !el.getBoundingClientRect) return 0;
    var r = el.getBoundingClientRect();
    var t = el.innerText || '';
    var score = 0;

    if(r.width > 500 && r.height > 320) score += 3;
    if(t.indexOf('채팅') > -1) score += 2;
    if(t.indexOf('후원') > -1) score += 1;
    if(t.indexOf('도전') > -1) score += 1;
    if(t.indexOf('대결') > -1) score += 1;
    if(t.indexOf('방송 시간') > -1 || t.indexOf('총 방송 시간') > -1) score += 2;
    if(t.indexOf('닉네임') > -1 || t.indexOf('검색') > -1) score += 1;

    return score;
  }

  function findPanel(){
    var best = null;
    var bestScore = 0;
    var list = document.querySelectorAll('body div');

    for(var i=0;i<list.length;i++){
      var el = list[i];
      if(el.closest && el.closest('.c9-vod-titlebar')) continue;
      var s = scorePanel(el);
      if(s > bestScore){
        bestScore = s;
        best = el;
      }
    }

    return bestScore >= 6 ? best : null;
  }

  function addTitle(panel){
    if(!panel || panel.querySelector('.c9-vod-titlebar')) return;

    var bar = document.createElement('div');
    bar.className = 'c9-vod-titlebar';
    bar.innerHTML = '<b>🎬 CNINE 다시보기 분석</b><span>VOD CHAT LOG</span>';
    panel.insertBefore(bar, panel.firstChild);
  }

  function blueAccents(panel){
    if(!panel) return;

    var nodes = panel.querySelectorAll('button, div, span, b');
    for(var i=0;i<nodes.length;i++){
      var el = nodes[i];
      if(el.closest && el.closest('.c9-vod-titlebar')) continue;

      var t = (el.textContent || '').trim();
      var r = el.getBoundingClientRect ? el.getBoundingClientRect() : {width:999,height:999};

      if(/^[\d,]+회$/.test(t) && r.width < 120 && r.height < 45){
        el.classList.add('c9-vod-blue');
      }
      if(t === '전체' || t === '수집완료'){
        el.classList.add('c9-vod-blue');
      }
    }
  }

  function apply(){
    addStyle();
    patchText(document.body);

    var panel = findPanel();
    if(panel){
      panel.classList.add('c9-vod-themed');
      addTitle(panel);
      blueAccents(panel);
    }
  }

  var count = 0;
  var timer = setInterval(function(){
    count++;
    apply();
    if(count > 50) clearInterval(timer);
  }, 150);

  try{
    var mo = new MutationObserver(function(){
      apply();
    });
    mo.observe(document.body || document.documentElement, {
      childList:true,
      subtree:true,
      characterData:true
    });
  }catch(e){}

  setTimeout(apply, 0);
})();
