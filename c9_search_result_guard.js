(function () {
  'use strict';

  var cfg = window.C9_GUARD_CONFIG || {};
  var KEYWORD_URL = cfg.keywordUrl || 'https://keyman1335-maker.github.io/poong-rank/bad_words.json?v=' + Date.now();

  function $(id) {
    return document.getElementById(id);
  }

  function esc(s) {
    return String(s || '').replace(/[&<>"']/g, function (c) {
      return {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c] || c;
    });
  }

  function setStatus(msg, color) {
    var st = $('guard-status');
    if (st) {
      st.textContent = msg;
      if (color) st.style.color = color;
    }
  }

  function closeReady() {
    var btn = $('guard-close-ready');
    var pop = $('guard-pop');
    if (btn && pop) btn.onclick = function () { pop.style.display = 'none'; };
  }

  window.onerror = function (msg) {
    setStatus('제목 감지 스크립트 오류 · ' + String(msg).slice(0, 90), '#fca5a5');
  };

  function fallback() {
    return {
      "팬덤비하": [
        {"word": "길견", "score": 3},
        {"word": "똥퀴", "score": 3},
        {"word": "염퀴", "score": 3},
        {"word": "물소", "score": 2}
      ],
      "타퀴의심": [
        {"word": "민심", "score": 1},
        {"word": "박살", "score": 2},
        {"word": "손절", "score": 2}
      ],
      "이간질": [
        {"word": "갈라치기", "score": 2},
        {"word": "분열", "score": 2},
        {"word": "내분", "score": 2}
      ]
    };
  }

  function flattenKeywords(data) {
    var out = [];
    if (!data) return out;

    if (data.categories && typeof data.categories === 'object') {
      data = data.categories;
    }

    if (Array.isArray(data)) {
      data.forEach(function (x) {
        if (typeof x === 'string') out.push({category: '감지', word: x, score: 1});
        else if (x && x.word) out.push({category: x.category || '감지', word: x.word, score: Number(x.score || 1)});
      });
      return out;
    }

    Object.keys(data).forEach(function (cat) {
      var arr = data[cat];
      if (!Array.isArray(arr)) return;
      arr.forEach(function (x) {
        if (typeof x === 'string') out.push({category: cat, word: x, score: 1});
        else if (x && x.word) out.push({category: cat, word: x.word, score: Number(x.score || 1)});
      });
    });
    return out;
  }

  function getKeywords() {
    setStatus('키워드 파일 로딩중...', '#93c5fd');
    return fetch(KEYWORD_URL, {cache: 'no-store'})
      .then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      })
      .catch(function () {
        setStatus('키워드 파일 로드 실패 · 기본 키워드로 감지중...', '#fbbf24');
        return fallback();
      })
      .then(flattenKeywords);
  }

  function collectTitles(doc) {
    var titles = [];
    var selectors = [
      'td.subject a',
      '.subject a',
      '.list_subject a',
      'a[href*="/board/"]'
    ].join(',');

    doc.querySelectorAll(selectors).forEach(function (a) {
      var t = (a.textContent || '').replace(/\s+/g, ' ').trim();
      var href = a.href || '';

      if (t.length < 2 || t.length > 140) return;
      if (/^(전체|인기|와토|공지|정보|사진|영상|이벤트|관리자|추천|댓글|목록|글쓰기|취소)$/.test(t)) return;
      if (!/\/board\//.test(href) && !a.closest('td.subject,.subject,.list_subject')) return;

      titles.push({title: t, href: href});
    });

    var seen = {};
    return titles.filter(function (x) {
      var k = x.title + '|' + x.href;
      if (seen[k]) return false;
      seen[k] = 1;
      return true;
    }).slice(0, 100);
  }

  function scanText(text, keywords) {
    var hits = [];
    var raw = String(text || '');
    var noSpace = raw.toLowerCase().replace(/\s+/g, '');

    keywords.forEach(function (k) {
      var w = String(k.word || '').trim();
      if (!w) return;

      var normalized = w.toLowerCase().replace(/\s+/g, '');
      if (!normalized) return;

      var count = 0;
      var pos = 0;
      while ((pos = noSpace.indexOf(normalized, pos)) !== -1) {
        count += 1;
        pos += normalized.length;
      }
      if (count > 0) {
        hits.push({
          category: k.category || '감지',
          word: w,
          score: Number(k.score || 1),
          count: count,
          sum: Number(k.score || 1) * count
        });
      }
    });

    return hits;
  }

  function scanFrame(frame, keywords) {
    try {
      var doc = frame.contentDocument || frame.contentWindow.document;
      var board = frame.getAttribute('data-board') || '게시판';
      var rows = [];

      collectTitles(doc).forEach(function (t) {
        var hits = scanText(t.title, keywords);
        if (hits.length) rows.push({board: board, title: t.title, href: t.href, hits: hits});
      });

      return {ok: true, board: board, rows: rows};
    } catch (e) {
      return {ok: false, board: frame.getAttribute('data-board') || '게시판', rows: [], error: e.message};
    }
  }

  function judge(total) {
    if (total >= 6) return '🚨 팬덤비하자 / 타퀴의심 강함';
    if (total >= 3) return '⚠️ 타퀴의심 / 이간질 의심';
    if (total > 0) return '주의 키워드 감지';
    return '감지 없음';
  }

  function render(all, blockedCount) {
    var pop = $('guard-pop');
    if (!pop) return;

    var totalScore = 0;
    all.forEach(function (r) {
      r.hits.forEach(function (h) { totalScore += Number(h.sum || h.score || 1); });
    });

    var borderColor = totalScore > 0 ? '#ef4444' : '#3b82f6';
    var titleEmoji = totalScore > 0 ? '🚨' : '✅';
    var statusColor = totalScore > 0 ? '#ffb4b4' : '#93c5fd';

    if (!all.length) {
      pop.style.border = '1px solid ' + borderColor;
      pop.innerHTML =
        '<div style="padding:10px 42px 10px 13px;background:rgba(15,23,42,.94);border-bottom:1px solid rgba(59,130,246,.45);">' +
          '<button id="guard-close" style="position:absolute;right:10px;top:8px;width:28px;height:28px;border:0;border-radius:8px;background:#475569;color:#fff;font-weight:1000;cursor:pointer;">×</button>' +
          '<div style="font-size:16px;font-weight:1000;color:#fff;">' + titleEmoji + ' 게시글 제목 감지</div>' +
          '<div style="margin-top:4px;color:' + statusColor + ';font-size:13px;font-weight:900;">' +
            '감지 없음 · 점수 0점 · 감지글 0건' + (blockedCount ? ' · 접근제한 ' + blockedCount + '개' : '') +
          '</div>' +
        '</div>';
      $('guard-close').onclick = function () { pop.style.display = 'none'; };
      return;
    }

    var byCat = {};
    all.forEach(function (r) {
      r.hits.forEach(function (h) {
        var c = h.category || '감지';
        if (!byCat[c]) byCat[c] = [];
        byCat[c].push(h.word);
      });
    });

    var catHtml = Object.keys(byCat).map(function (c) {
      var uniq = byCat[c].filter(function (v, i, a) { return a.indexOf(v) === i; });
      return '<span style="display:inline-block;margin:3px;padding:5px 8px;border-radius:999px;background:#7f1d1d;border:1px solid #ef4444;color:#fff;font-size:12px;font-weight:900;">' +
        esc(c) + ' : ' + esc(uniq.join(', ')) + '</span>';
    }).join('');

    var list = all.slice(0, 12).map(function (r) {
      return '<div style="margin-top:8px;padding:9px;border-radius:10px;background:rgba(0,0,0,.25);border:1px solid rgba(255,255,255,.10);">' +
        '<div style="color:#7ec8ff;font-size:12px;font-weight:1000;">' + esc(r.board) + '</div>' +
        '<div style="margin-top:3px;color:#fff;font-size:13px;font-weight:900;line-height:1.35;">' + esc(r.title) + '</div>' +
        '<div style="margin-top:5px;color:#ffb4b4;font-size:12px;font-weight:900;">감지: ' +
          esc(r.hits.map(function (h) { return h.word + (h.count > 1 ? '×' + h.count : ''); }).join(', ')) +
        '</div>' +
      '</div>';
    }).join('');

    pop.style.border = '1px solid #ef4444';
    pop.innerHTML =
      '<div style="position:sticky;top:0;padding:12px 42px 10px 13px;background:rgba(15,23,42,.94);border-bottom:1px solid rgba(239,68,68,.45);">' +
        '<button id="guard-close" style="position:absolute;right:10px;top:8px;width:28px;height:28px;border:0;border-radius:8px;background:#475569;color:#fff;font-weight:1000;cursor:pointer;">×</button>' +
        '<div style="font-size:17px;font-weight:1000;color:#fff;">🚨 게시글 제목 감지</div>' +
        '<div style="margin-top:4px;color:#ffb4b4;font-size:13px;font-weight:900;">' +
          esc(judge(totalScore)) + ' · 점수 ' + totalScore + '점 · 감지글 ' + all.length + '건' +
          (blockedCount ? ' · 접근제한 ' + blockedCount + '개' : '') +
        '</div>' +
        '<div style="margin-top:7px;">' + catHtml + '</div>' +
      '</div>' +
      '<div style="padding:10px 12px 13px;">' + list + '</div>';

    $('guard-close').onclick = function () { pop.style.display = 'none'; };
  }

  function scanAll(keywords) {
    var all = [];
    var blocked = 0;

    document.querySelectorAll('iframe.yg-frame').forEach(function (f) {
      var result = scanFrame(f, keywords);
      if (!result.ok) blocked += 1;
      all = all.concat(result.rows);
    });

    render(all, blocked);
  }

  function boot() {
    closeReady();

    getKeywords().then(function (keywords) {
      setStatus('키워드 로드 완료 · 검색결과 로딩중...', '#93c5fd');

      var frames = Array.prototype.slice.call(document.querySelectorAll('iframe.yg-frame'));
      frames.forEach(function (f) {
        f.addEventListener('load', function () {
          setTimeout(function () { scanAll(keywords); }, 700);
        });
      });

      setTimeout(function () { scanAll(keywords); }, 1800);
      setTimeout(function () { scanAll(keywords); }, 3500);
      setTimeout(function () { scanAll(keywords); }, 6000);
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
