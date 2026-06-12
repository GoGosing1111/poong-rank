(function () {
  'use strict';

  var cfg = window.C9_GUARD_CONFIG || {};
  var KEYWORD_URL = cfg.keywordUrl || 'https://keyman1335-maker.github.io/poong-rank/bad_words.json?v=' + Date.now();

  function status(msg, color) {
    var st = document.getElementById('guard-status');
    if (st) {
      st.textContent = msg;
      if (color) st.style.color = color;
    }
  }

  function esc(s) {
    return String(s || '').replace(/[&<>"']/g, function (c) {
      return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c] || c;
    });
  }

  function fallbackDict() {
    return {
      "팬덤비하": [
        {"word":"길견","score":3},
        {"word":"똥퀴","score":3},
        {"word":"염퀴","score":3},
        {"word":"물소","score":2}
      ],
      "타퀴의심": [
        {"word":"민심","score":1},
        {"word":"박살","score":2},
        {"word":"손절","score":2}
      ],
      "이간질": [
        {"word":"갈라치기","score":2},
        {"word":"분열","score":2},
        {"word":"내분","score":2}
      ]
    };
  }

  function flatten(data) {
    var out = [];
    if (!data) return out;

    var root = data.categories || data;

    if (Array.isArray(root)) {
      root.forEach(function (x) {
        if (typeof x === 'string') out.push({ category: '감지', word: x, score: 1 });
        else if (x && x.word) out.push({ category: x.category || '감지', word: x.word, score: Number(x.score || 1) });
      });
      return out;
    }

    Object.keys(root).forEach(function (cat) {
      var arr = root[cat];
      if (!Array.isArray(arr)) return;
      arr.forEach(function (x) {
        if (typeof x === 'string') out.push({ category: cat, word: x, score: 1 });
        else if (x && x.word) out.push({ category: cat, word: x.word, score: Number(x.score || 1) });
      });
    });
    return out;
  }

  function normalize(s) {
    return String(s || '').toLowerCase().replace(/\s+/g, '');
  }

  function countMatches(text, word) {
    var t = normalize(text);
    var w = normalize(word);
    if (!w) return 0;
    var count = 0;
    var pos = 0;
    while ((pos = t.indexOf(w, pos)) !== -1) {
      count += 1;
      pos += w.length;
    }
    return count;
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
      if (/^(전체|인기|와토|공지|정보|사진|영상|이벤트|관리자|추천|댓글|목록|글쓰기|삭제|수정)$/.test(t)) return;
      if (!/\/board\//.test(href) && !a.closest('td.subject,.subject,.list_subject')) return;
      titles.push({ title: t, href: href });
    });

    var seen = {};
    return titles.filter(function (x) {
      var k = x.title + '|' + x.href;
      if (seen[k]) return false;
      seen[k] = 1;
      return true;
    }).slice(0, 80);
  }

  function scanTitle(title, keywords) {
    var hits = [];
    keywords.forEach(function (k) {
      var word = String(k.word || '').trim();
      if (!word) return;
      var count = countMatches(title, word);
      if (count > 0) {
        hits.push({
          category: k.category || '감지',
          word: word,
          score: Number(k.score || 1),
          count: count,
          sum: Number(k.score || 1) * count
        });
      }
    });
    return hits;
  }

  function judge(score) {
    if (score >= 6) return '🚨 팬덤비하자 / 타퀴의심 강함';
    if (score >= 3) return '⚠️ 타퀴의심 / 이간질 의심';
    if (score > 0) return '주의 키워드 감지';
    return '감지 없음';
  }

  function render(rows, scannedCount) {
    var pop = document.getElementById('guard-pop');
    if (!pop) return;

    var totalScore = 0;
    rows.forEach(function (r) {
      r.hits.forEach(function (h) { totalScore += Number(h.sum || h.score || 1); });
    });

    var danger = totalScore >= 6;
    var warn = totalScore >= 3;
    var accent = danger ? '#ef4444' : warn ? '#f59e0b' : totalScore > 0 ? '#eab308' : '#3b82f6';

    if (!rows.length) {
      pop.style.border = '1px solid ' + accent;
      pop.innerHTML =
        '<div style="padding:10px 42px 10px 13px;background:rgba(15,23,42,.94);border-bottom:1px solid rgba(59,130,246,.45);">' +
        '<button id="guard-close" type="button" style="position:absolute;right:10px;top:8px;width:28px;height:28px;border:0;border-radius:8px;background:#475569;color:#fff;font-weight:1000;cursor:pointer;">×</button>' +
        '<div style="font-size:16px;font-weight:1000;color:#fff;">✅ 게시글 제목 감지</div>' +
        '<div style="margin-top:4px;color:#93c5fd;font-size:13px;font-weight:900;">감지 없음 · 점수 0점 · 감지글 0건 · 스캔 제목 ' + scannedCount + '개</div>' +
        '</div>';
      document.getElementById('guard-close').onclick = function () { pop.style.display = 'none'; };
      return;
    }

    var byCat = {};
    rows.forEach(function (r) {
      r.hits.forEach(function (h) {
        if (!byCat[h.category]) byCat[h.category] = [];
        byCat[h.category].push(h.word);
      });
    });

    var catHtml = Object.keys(byCat).map(function (cat) {
      var uniq = byCat[cat].filter(function (v, i, a) { return a.indexOf(v) === i; });
      return '<span style="display:inline-block;margin:3px;padding:5px 8px;border-radius:999px;background:#7f1d1d;border:1px solid #ef4444;color:#fff;font-size:12px;font-weight:900;">' +
        esc(cat) + ' : ' + esc(uniq.join(', ')) + '</span>';
    }).join('');

    var list = rows.slice(0, 14).map(function (r) {
      return '<div style="margin-top:8px;padding:9px;border-radius:10px;background:rgba(0,0,0,.25);border:1px solid rgba(255,255,255,.10);">' +
        '<div style="color:#7ec8ff;font-size:12px;font-weight:1000;">' + esc(r.board) + '</div>' +
        '<div style="margin-top:3px;color:#fff;font-size:13px;font-weight:900;line-height:1.35;">' + esc(r.title) + '</div>' +
        '<div style="margin-top:5px;color:#ffb4b4;font-size:12px;font-weight:900;">감지: ' + esc(r.hits.map(function (h) { return h.word + ' +' + h.sum; }).join(', ')) + '</div>' +
        '</div>';
    }).join('');

    pop.style.border = '1px solid ' + accent;
    pop.innerHTML =
      '<div style="position:sticky;top:0;padding:12px 42px 10px 13px;background:rgba(15,23,42,.96);border-bottom:1px solid rgba(239,68,68,.45);">' +
      '<button id="guard-close" type="button" style="position:absolute;right:10px;top:8px;width:28px;height:28px;border:0;border-radius:8px;background:#475569;color:#fff;font-weight:1000;cursor:pointer;">×</button>' +
      '<div style="font-size:17px;font-weight:1000;color:#fff;">🚨 게시글 제목 감지</div>' +
      '<div style="margin-top:4px;color:#ffb4b4;font-size:13px;font-weight:900;">' + esc(judge(totalScore)) + ' · 점수 ' + totalScore + '점 · 감지글 ' + rows.length + '건 · 스캔 제목 ' + scannedCount + '개</div>' +
      '<div style="margin-top:7px;">' + catHtml + '</div>' +
      '</div><div style="padding:10px 12px 13px;">' + list + '</div>';
    document.getElementById('guard-close').onclick = function () { pop.style.display = 'none'; };
  }

  function scanAll(keywords) {
    var rows = [];
    var scannedCount = 0;
    document.querySelectorAll('iframe.yg-frame').forEach(function (frame) {
      try {
        var doc = frame.contentDocument || frame.contentWindow.document;
        var board = frame.getAttribute('data-board') || '게시판';
        var titles = collectTitles(doc);
        scannedCount += titles.length;
        titles.forEach(function (t) {
          var hits = scanTitle(t.title, keywords);
          if (hits.length) rows.push({ board: board, title: t.title, href: t.href, hits: hits });
        });
      } catch (e) {
        // 같은 ygosu origin about:blank에서는 보통 접근 가능. 막히면 해당 frame만 스킵.
      }
    });
    render(rows, scannedCount);
  }

  function initClose() {
    var b = document.getElementById('guard-close-ready');
    if (b) b.onclick = function () {
      var p = document.getElementById('guard-pop');
      if (p) p.style.display = 'none';
    };
  }

  async function main() {
    initClose();
    status('키워드 로드중...');

    var dict;
    try {
      var res = await fetch(KEYWORD_URL, { cache: 'no-store' });
      dict = await res.json();
    } catch (e) {
      dict = fallbackDict();
      status('키워드 파일 로드 실패 · 기본 키워드로 감지중...', '#fca5a5');
    }

    var keywords = flatten(dict);
    status('키워드 로드 완료 · 검색결과 로딩중...');

    document.querySelectorAll('iframe.yg-frame').forEach(function (f) {
      f.addEventListener('load', function () {
        setTimeout(function () { scanAll(keywords); }, 700);
      }, false);
    });

    setTimeout(function () { scanAll(keywords); }, 1600);
    setTimeout(function () { scanAll(keywords); }, 3200);
    setTimeout(function () { scanAll(keywords); }, 5200);
  }

  window.onerror = function (msg) {
    status('제목 감지 스크립트 오류 · ' + String(msg).slice(0, 90), '#fca5a5');
  };

  main();
})();
