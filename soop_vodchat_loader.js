/*
CNINE VOD loader - no flash version
- 원본 UI가 잠깐 보이는 현상을 줄이기 위해 원본 로드 전에 숨김 CSS를 먼저 삽입
*/
(function(){
  'use strict';

  if (window.__C9_VODCHAT_LOADER_ACTIVE__) return;
  window.__C9_VODCHAT_LOADER_ACTIVE__ = true;
  window.__C9_VODCHAT_READY__ = false;

  var HIDE_ID = 'c9-vodchat-prehide-style';
  function addPreHide(){
    if (document.getElementById(HIDE_ID)) return;
    var st = document.createElement('style');
    st.id = HIDE_ID;
    st.textContent = [
      'body.c9-vodchat-loading div{transition:none!important}',
      'body.c9-vodchat-loading *{}',
      'body.c9-vodchat-loading div[style*="position: fixed"]{visibility:hidden!important;opacity:0!important}',
      'body.c9-vodchat-loading div[style*="z-index"]{visibility:hidden!important;opacity:0!important}',
      'body.c9-vodchat-loading [class*="vod"],',
      'body.c9-vodchat-loading [class*="chat"],',
      'body.c9-vodchat-loading [id*="vod"],',
      'body.c9-vodchat-loading [id*="chat"]{visibility:hidden!important;opacity:0!important}',
      'body.c9-vodchat-ready div[style*="position: fixed"]{visibility:visible}'
    ].join('\n');
    (document.head || document.documentElement).appendChild(st);
  }

  function load(src, cb){
    var s = document.createElement('script');
    s.src = src;
    s.onload = cb || function(){};
    s.onerror = cb || function(){};
    document.head.appendChild(s);
  }

  try {
    addPreHide();
    document.body.classList.add('c9-vodchat-loading');
  } catch(e) {}

  load('https://keyman1335-maker.github.io/poong-rank/soop_vodchat.js?v=2026061207', function(){
    setTimeout(function(){
      load('https://keyman1335-maker.github.io/poong-rank/soop_vodchat_cnine_patch.js?v=2026061206', function(){
        setTimeout(function(){
          window.__C9_VODCHAT_READY__ = true;
          try {
            document.body.classList.remove('c9-vodchat-loading');
            document.body.classList.add('c9-vodchat-ready');
          } catch(e) {}
        }, 250);
      });
    }, 50);
  });
})();
