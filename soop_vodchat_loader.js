(function(){
  if(!document.getElementById('cnine-vod-prehide')){
    var st=document.createElement('style');
    st.id='cnine-vod-prehide';
    st.textContent='body *{visibility:hidden !important;} .cnine-vod-allow{visibility:visible !important;}';
    document.head.appendChild(st);
  }
  function reveal(){
    var s=document.getElementById('cnine-vod-prehide');
    if(s) s.remove();
  }
  function load(src, cb){
    var s=document.createElement('script');
    s.src=src;
    s.onload=cb||function(){};
    document.head.appendChild(s);
  }
  load('https://keyman1335-maker.github.io/poong-rank/soop_vodchat.js?v=2026061207', function(){
    load('https://keyman1335-maker.github.io/poong-rank/soop_vodchat_cnine_patch.js?v=2026061207', function(){});
    setTimeout(reveal,2200);
  });
})();