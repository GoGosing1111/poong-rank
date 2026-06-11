/*
CNINE VOD loader v4
- 원본 soop_vodchat.js는 데이터 수집용으로만 사용
- fetch / XHR 응답을 먼저 후킹해서 VOD 채팅 관련 데이터를 window.__C9_VODCHAT_STORE__에 저장
- CNINE 전용 UI 패널을 별도 생성
*/
(function(){
  'use strict';

  if(window.__C9_VODCHAT_LOADER_V4__) return;
  window.__C9_VODCHAT_LOADER_V4__ = true;

  var BASE = 'https://keyman1335-maker.github.io/poong-rank';
  var ORIGIN_JS = BASE + '/soop_vodchat.js?v=2026061211';
  var PATCH_JS = BASE + '/soop_vodchat_cnine_patch.js?v=2026061211';

  window.__C9_VODCHAT_STORE__ = window.__C9_VODCHAT_STORE__ || {
    responses: [],
    texts: [],
    jsons: [],
    updatedAt: Date.now()
  };

  function pushStore(type, url, data){
    try{
      var item = {type:type, url:String(url||''), data:data, time:Date.now()};
      window.__C9_VODCHAT_STORE__.responses.push(item);
      if(type === 'json') window.__C9_VODCHAT_STORE__.jsons.push(item);
      if(type === 'text') window.__C9_VODCHAT_STORE__.texts.push(item);
      window.__C9_VODCHAT_STORE__.updatedAt = Date.now();
      try{ window.dispatchEvent(new CustomEvent('c9-vodchat-data', {detail:item})); }catch(e){}
    }catch(e){}
  }

  // fetch hook
  if(!window.__C9_FETCH_HOOKED__ && window.fetch){
    window.__C9_FETCH_HOOKED__ = true;
    var nativeFetch = window.fetch;
    window.fetch = function(){
      var args = arguments;
      var url = args && args[0] && (args[0].url || args[0]);
      return nativeFetch.apply(this,args).then(function(res){
        try{
          var clone = res.clone();
          var ct = (clone.headers && clone.headers.get('content-type')) || '';
          if(ct.indexOf('json') > -1){
            clone.json().then(function(j){ pushStore('json', url, j); }).catch(function(){});
          }else{
            clone.text().then(function(t){
              if(t && (t.indexOf('chat')>-1 || t.indexOf('message')>-1 || t.indexOf('풍')>-1 || t.indexOf('balloon')>-1)){
                pushStore('text', url, t.slice(0, 200000));
              }
            }).catch(function(){});
          }
        }catch(e){}
        return res;
      });
    };
  }

  // XHR hook
  if(!window.__C9_XHR_HOOKED__ && window.XMLHttpRequest){
    window.__C9_XHR_HOOKED__ = true;
    var NativeXHR = window.XMLHttpRequest;
    window.XMLHttpRequest = function(){
      var xhr = new NativeXHR();
      var _open = xhr.open;
      var _url = '';
      xhr.open = function(method, url){
        _url = url;
        return _open.apply(xhr, arguments);
      };
      xhr.addEventListener('load', function(){
        try{
          var txt = xhr.responseText || '';
          var ct = xhr.getResponseHeader && (xhr.getResponseHeader('content-type') || '');
          if((ct.indexOf('json')>-1 || txt.charAt(0)==='{' || txt.charAt(0)==='[') && txt.length < 5000000){
            try{ pushStore('json', _url, JSON.parse(txt)); }
            catch(e){ pushStore('text', _url, txt.slice(0, 200000)); }
          }else if(txt && (txt.indexOf('chat')>-1 || txt.indexOf('message')>-1 || txt.indexOf('풍')>-1 || txt.indexOf('balloon')>-1)){
            pushStore('text', _url, txt.slice(0, 200000));
          }
        }catch(e){}
      });
      return xhr;
    };
  }

  function load(src, cb){
    var s = document.createElement('script');
    s.src = src;
    s.onload = cb || function(){};
    s.onerror = cb || function(){};
    document.head.appendChild(s);
  }

  load(ORIGIN_JS, function(){
    setTimeout(function(){ load(PATCH_JS); }, 150);
  });
})();
