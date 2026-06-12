/*
CNINE VOD safe patch v7
- 텍스트 치환 제거
- 원본 데이터 파싱/완료 상태에 영향 없도록 CSS만 최소 적용
*/
(function(){
  'use strict';

  if (window.__CNINE_VODCHAT_SAFE_PATCH_V7__) return;
  window.__CNINE_VODCHAT_SAFE_PATCH_V7__ = true;

  function injectStyle(){
    if (document.getElementById('cnine-vodchat-safe-style-v7')) return;
    var css = document.createElement('style');
    css.id = 'cnine-vodchat-safe-style-v7';
    css.textContent = [
      '/* CNINE safe skin: CSS only */',
      '[class*="rank"], [class*="chat"], [class*="mission"]{scrollbar-color:#2f9bff #071426;}',
      'button{font-family:Arial,"Malgun Gothic",sans-serif;}'
    ].join('\n');
    (document.head || document.documentElement).appendChild(css);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', injectStyle);
  } else {
    injectStyle();
  }
})();
