/*
CNINE VOD loader v6 - DESIGN ONLY
- 티큐 원본 soop_vodchat.js 먼저 로드
- 이후 디자인 CSS 패치만 로드
- fetch / XHR 후킹 없음
*/
(function(){
  'use strict';

  if(window.__C9_VOD_LOADER_V6__) return;
  window.__C9_VOD_LOADER_V6__ = true;

  var BASE = 'https://keyman1335-maker.github.io/poong-rank';
  var ORIGIN_JS = BASE + '/soop_vodchat.js?v=2026061216';
  var PATCH_JS  = BASE + '/soop_vodchat_cnine_patch.js?v=2026061216';

  function load(src, cb){
    var s = document.createElement('script');
    s.src = src;
    s.async = false;
    s.onload = cb || function(){};
    s.onerror = function(){
      try{ console.warn('[CNINE VOD] script load failed:', src); }catch(e){}
      if(cb) cb();
    };
    document.head.appendChild(s);
  }

  load(ORIGIN_JS, function(){
    setTimeout(function(){ load(PATCH_JS); }, 150);
  });
})();
