(function(){
  function load(src, cb){
    var old = document.querySelector('script[src^="'+src.split('?')[0]+'"]');
    if (old) { if (cb) setTimeout(cb, 300); return; }
    var s = document.createElement('script');
    s.src = src;
    s.onload = cb || function(){};
    document.head.appendChild(s);
  }
  load('https://keyman1335-maker.github.io/poong-rank/soop_vodchat.js?v=20260612', function(){
    load('https://keyman1335-maker.github.io/poong-rank/soop_vodchat_cnine_patch.js?v=20260612');
  });
})();
