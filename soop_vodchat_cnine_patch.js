/*
CNINE VOD patch v3
- 원본 UI를 파괴하지 않고 생성 후 스타일/문구만 적용
- 티큐 원본 UI 플래시를 줄이기 위해 적용 완료 후 body.c9-vodchat-loading 해제
*/
(function(){
  'use strict';

  var STYLE_ID = 'c9-vodchat-skin-v3';
  var DONE_CLASS = 'c9-vodchat-themed';

  function addStyle(){
    if(document.getElementById(STYLE_ID)) return;
    var css = `
      body .${DONE_CLASS}{
        background:linear-gradient(180deg,#071a31 0%,#07162a 42%,#020711 100%)!important;
        border:1px solid rgba(78,168,255,.75)!important;
        box-shadow:0 0 0 1px rgba(78,168,255,.22),0 18px 42px rgba(0,0,0,.60),0 0 28px rgba(47,155,255,.30)!important;
      }
      body .${DONE_CLASS} *{
        text-shadow:none;
      }
      body .${DONE_CLASS} input,
      body .${DONE_CLASS} select{
        background:#06101f!important;
        border:1px solid rgba(78,168,255,.45)!important;
        color:#eaf6ff!important;
      }
      body .${DONE_CLASS} button{
        border-color:rgba(78,168,255,.42)!important;
      }
      body .${DONE_CLASS}::-webkit-scrollbar,
      body .${DONE_CLASS} *::-webkit-scrollbar{width:10px!important;height:10px!important}
      body .${DONE_CLASS}::-webkit-scrollbar-thumb,
      body .${DONE_CLASS} *::-webkit-scrollbar-thumb{
        background:linear-gradient(180deg,#4ea8ff,#1d6dff)!important;
        border-radius:999px!important;
      }
      body .${DONE_CLASS}::-webkit-scrollbar-track,
      body .${DONE_CLASS} *::-webkit-scrollbar-track{
        background:#06101f!important;
      }
      .c9-vod-titlebar{
        display:flex!important;
        align-items:center!important;
        justify-content:space-between!important;
        gap:10px!important;
        padding:14px 18px!important;
        background:linear-gradient(135deg,#0a2544,#10265a 55%,#06101f)!important;
        border-bottom:1px solid rgba(78,168,255,.45)!important;
        color:#fff!important;
        font-family:Arial,'Malgun Gothic',sans-serif!important;
      }
      .c9-vod-titlebar b{
        font-size:18px!important;
        font-weight:1000!important;
        color:#fff!important;
        text-shadow:0 0 10px rgba(78,168,255,.55)!important;
      }
      .c9-vod-titlebar span{
        padding:5px 11px!important;
        border-radius:999px!important;
        border:1px solid rgba(126,200,255,.65)!important;
        color:#dff2ff!important;
        background:rgba(2,12,24,.62)!important;
        font-size:11px!important;
        font-weight:1000!important;
        letter-spacing:.5px!important;
      }
    `;
    var st=document.createElement('style');
    st.id=STYLE_ID;
    st.textContent=css;
    document.head.appendChild(st);
  }

  var replacePairs = [
    ['채팅 순위','채팅 랭킹'],
    ['후원 순위','후원 랭킹'],
    ['도전 순위','도전 랭킹'],
    ['대결 순위','대결 랭킹'],
    ['채팅 내역','채팅 로그'],
    ['후원 내역','후원 로그'],
    ['도전미션 내역','도전 로그'],
    ['대결미션 내역','대결 로그'],
    ['완료 ✨','수집완료'],
    ['완료','수집완료']
  ];

  function replaceText(root){
    var walker=document.createTreeWalker(root||document.body, NodeFilter.SHOW_TEXT, null);
    var nodes=[];
    while(walker.nextNode()) nodes.push(walker.currentNode);
    nodes.forEach(function(n){
      var v=n.nodeValue;
      if(!v) return;
      if(v.indexOf('분석 분석')>-1 || v.indexOf('분석완료분석완료')>-1){
        n.nodeValue='수집완료';
        return;
      }
      replacePairs.forEach(function(p){
        if(v.indexOf(p[0])>-1) v=v.split(p[0]).join(p[1]);
      });
      n.nodeValue=v;
    });
  }

  function scorePanel(el){
    if(!el || !el.getBoundingClientRect) return 0;
    var r=el.getBoundingClientRect();
    var txt=(el.innerText||'');
    var score=0;
    if(r.width>500 && r.height>350) score+=2;
    if(txt.indexOf('채팅')>-1) score+=2;
    if(txt.indexOf('후원')>-1) score+=1;
    if(txt.indexOf('도전')>-1) score+=1;
    if(txt.indexOf('대결')>-1) score+=1;
    if(txt.indexOf('방송 시간')>-1) score+=2;
    if(txt.indexOf('닉네임')>-1 || txt.indexOf('검색')>-1) score+=1;
    return score;
  }

  function findPanel(){
    var best=null, bestScore=0;
    var els=document.querySelectorAll('body div');
    for(var i=0;i<els.length;i++){
      var s=scorePanel(els[i]);
      if(s>bestScore){
        bestScore=s; best=els[i];
      }
    }
    return bestScore>=5 ? best : null;
  }

  function addTitle(panel){
    if(!panel || panel.querySelector('.c9-vod-titlebar')) return;
    var bar=document.createElement('div');
    bar.className='c9-vod-titlebar';
    bar.innerHTML='<b>🎬 CNINE 다시보기 분석</b><span>VOD CHAT LOG</span>';
    panel.insertBefore(bar, panel.firstChild);
  }

  function normalizeStatus(){
    document.querySelectorAll('*').forEach(function(el){
      if(el.children && el.children.length) return;
      var t=(el.textContent||'').trim();
      if(t.indexOf('분석 분석')>-1 || t.indexOf('분석완료분석완료')>-1){
        el.textContent='수집완료';
      }
    });
  }

  function run(){
    addStyle();
    replaceText(document.body);
    normalizeStatus();

    var panel=findPanel();
    if(panel){
      panel.classList.add(DONE_CLASS);
      addTitle(panel);
      try{
        document.body.classList.remove('c9-vodchat-loading');
        document.body.classList.add('c9-vodchat-ready');
      }catch(e){}
      return true;
    }
    return false;
  }

  var tries=0;
  var timer=setInterval(function(){
    tries++;
    if(run() || tries>80){
      if(tries>80){
        try{
          document.body.classList.remove('c9-vodchat-loading');
          document.body.classList.add('c9-vodchat-ready');
        }catch(e){}
      }
      clearInterval(timer);
    }
  },100);

  var mo=new MutationObserver(function(){ run(); });
  try{ mo.observe(document.body,{childList:true,subtree:true,characterData:true}); }catch(e){}

  setTimeout(run,30);
})();
