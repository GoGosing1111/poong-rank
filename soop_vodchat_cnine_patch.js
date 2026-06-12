(function(){
  'use strict';

  if (window.__CNINE_VODCHAT_SAFE_PATCH__) return;
  window.__CNINE_VODCHAT_SAFE_PATCH__ = true;

  var MAP = {
    '채팅 순위': '채팅 랭킹',
    '후원 순위': '후원 랭킹',
    '도전 순위': '도전 랭킹',
    '대결 순위': '대결 랭킹',
    '채팅 내역': '채팅 로그',
    '후원 내역': '후원 로그',
    '도전미션 내역': '도전 로그',
    '대결미션 내역': '대결 로그',
    '총 방송 시간': '방송 시간',
    '총 채팅 수': '채팅 수',
    '채팅 인원': '참여 인원',
    '상태': '분석 상태',
    '완료 ✨': '분석완료',
    '완료': '분석완료'
  };

  var KEYS = Object.keys(MAP);

  function replaceTextNode(node){
    var before = node.nodeValue;
    if (!before) return;
    var after = before;
    for (var i=0;i<KEYS.length;i++) {
      var k = KEYS[i];
      if (after.indexOf(k) !== -1) after = after.split(k).join(MAP[k]);
    }
    if (after !== before) node.nodeValue = after;
  }

  function walk(root){
    if (!root) return;
    var walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
      acceptNode: function(node){
        var p = node.parentNode;
        if (!p) return NodeFilter.FILTER_REJECT;
        var tag = (p.nodeName || '').toLowerCase();
        if (tag === 'script' || tag === 'style' || tag === 'textarea' || tag === 'input') return NodeFilter.FILTER_REJECT;
        var v = node.nodeValue || '';
        for (var i=0;i<KEYS.length;i++) {
          if (v.indexOf(KEYS[i]) !== -1) return NodeFilter.FILTER_ACCEPT;
        }
        return NodeFilter.FILTER_REJECT;
      }
    });
    var nodes = [];
    while (walker.nextNode()) nodes.push(walker.currentNode);
    for (var j=0;j<nodes.length;j++) replaceTextNode(nodes[j]);
  }

  function removeBadges(){
    // 이전 테스트 패치가 만든 좌측 상단 배지 제거용. 원본 패널은 건드리지 않음.
    var all = document.querySelectorAll('div,span');
    for (var i=0;i<all.length;i++) {
      var el = all[i];
      var txt = (el.textContent || '').trim();
      if (txt === '🎬 CNINE VOD TOOL' || txt === 'CNINE VOD TOOL') {
        var st = window.getComputedStyle(el);
        if (st.position === 'fixed' || st.position === 'absolute') {
          el.remove();
        }
      }
    }
  }

  function injectStyle(){
    if (document.getElementById('cnine-vodchat-safe-style')) return;
    var css = document.createElement('style');
    css.id = 'cnine-vodchat-safe-style';
    css.textContent = [
      '/* CNINE safe skin: no layout override */',
      '[class*="rank"], [class*="chat"], [class*="mission"]{scrollbar-color:#2f9bff #071426;}',
      'button{font-family:Arial,"Malgun Gothic",sans-serif;}'
    ].join('\n');
    document.head.appendChild(css);
  }

  function run(){
    removeBadges();
    walk(document.body);
    injectStyle();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', run);
  } else {
    run();
  }

  var timer = setInterval(run, 1000);
  setTimeout(function(){ clearInterval(timer); }, 30000);

  try {
    var obs = new MutationObserver(function(muts){
      for (var i=0;i<muts.length;i++) {
        var m = muts[i];
        for (var j=0;j<m.addedNodes.length;j++) {
          var n = m.addedNodes[j];
          if (n.nodeType === 1 || n.nodeType === 3) {
            setTimeout(run, 50);
            return;
          }
        }
      }
    });
    obs.observe(document.documentElement || document.body, {childList:true, subtree:true});
    setTimeout(function(){ try{ obs.disconnect(); }catch(e){} }, 60000);
  } catch(e) {}
})();
