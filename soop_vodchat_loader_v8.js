/*
CNINE VOD loader v8 - GitHub Pages URL fixed
- Loads original soop_vodchat.js first
- Patch is disabled by default
*/
(function(){
  'use strict';

  if (window.__C9_VOD_LOADER_V8__) return;
  window.__C9_VOD_LOADER_V8__ = true;

  var BASE = 'https://gogosing1111.github.io/poong-rank';

  // Change this version whenever you update soop_vodchat.js
  var ORIGIN_JS = BASE + '/soop_vodchat.js?v=2026070502';

  // Keep patch off until original UI works
  var ENABLE_PATCH = false;
  var PATCH_JS = BASE + '/soop_vodchat_cnine_patch.js?v=2026070502';

  function load(src, cb){
    var s = document.createElement('script');
    s.src = src;
    s.async = false;
    s.onload = cb || function(){};
    s.onerror = function(){
      try {
        console.warn('[CNINE VOD] script load failed:', src);
      } catch(e) {}
      if (cb) cb();
    };
    (document.head || document.documentElement).appendChild(s);
  }

  load(ORIGIN_JS, function(){
    if (!ENABLE_PATCH) return;
    setTimeout(function(){
      load(PATCH_JS);
    }, 800);
  });
})();
