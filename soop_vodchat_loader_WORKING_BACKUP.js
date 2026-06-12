/*
CNINE VOD loader v7 - STABLE RECOVERY
- 원본 soop_vodchat.js만 먼저 로드
- 무한로딩 원인 분리를 위해 텍스트 치환 패치는 기본 비활성
- fetch / XHR / DOM 파싱 로직 건드리지 않음
*/
(function(){
  'use strict';

  if (window.__C9_VOD_LOADER_V7__) return;
  window.__C9_VOD_LOADER_V7__ = true;

  var BASE = 'https://keyman1335-maker.github.io/poong-rank';

  // 캐시 우회용 버전. GitHub push 후 이 값이 바뀌어야 새 파일을 강제로 받음.
  var ORIGIN_JS = BASE + '/soop_vodchat.js?v=2026061234';

  // 안정화 전까지 패치는 끔. 원본 UI 정상 확인 후 다시 켜는 게 맞음.
  var ENABLE_PATCH = false;
  var PATCH_JS = BASE + '/soop_vodchat_cnine_patch.js?v=2026061234';

  function load(src, cb){
    var s = document.createElement('script');
    s.src = src;
    s.async = false;
    s.onload = cb || function(){};
    s.onerror = function(){
      try { console.warn('[CNINE VOD] script load failed:', src); } catch(e) {}
      if (cb) cb();
    };
    (document.head || document.documentElement).appendChild(s);
  }

  load(ORIGIN_JS, function(){
    if (!ENABLE_PATCH) return;
    setTimeout(function(){ load(PATCH_JS); }, 800);
  });
})();
