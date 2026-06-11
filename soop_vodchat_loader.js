(function(){
  function load(src, cb){
    var base = src.split('?')[0];
    var old = Array.prototype.slice.call(document.scripts).find(function(s){ return (s.src || '').split('?')[0] === base; });
    if (old) { if (cb) setTimeout(cb, 800); return; }
    var s = document.createElement('script');
    s.src = src;
    s.onload = cb || function(){};
    s.onerror = function(){ console.error('[CNINE VOD] load failed:', src); };
    document.head.appendChild(s);
  }

  load('https://keyman1335-maker.github.io/poong-rank/soop_vodchat.js?v=2026061207', function(){
    setTimeout(function(){
      load('https://keyman1335-maker.github.io/poong-rank/soop_vodchat_cnine_patch.js?v=2026061207');
    }, 1600);
  });
})();
