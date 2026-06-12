(function () {
  'use strict';

  var cfg = window.C9_GUARD_CONFIG || {};
  var KEYWORD_URL = cfg.keywordUrl || 'https://keyman1335-maker.github.io/poong-rank/bad_words.json?v=' + Date.now();
  var PANEL_ID = 'guard-pop';

  function $(id) { return document.getElementById(id); }

  function esc(s) {
    return String(s || '').replace(/[&<>"']/g, function (c) {
      return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c] || c;
    });
  }

  function setStatus(text, color) {
    var st = $('guard-status');
    if (st) {
      st.textContent = text;
      if (color) st.style.color = color;
    }
  }

  function closePanel() {
    var p = $(PANEL_ID);
    if (p) p.style.display = 'none';
  }

  function wireClose() {
    var b = $('guard-close-ready') || $('guard-close');
    if (b) b.onclick = closePanel;
  }

  wireClose();

  window.onerror = function (msg) {
    setStatus('제목 감지 스크립트 오류 · ' + String(msg).slice(0, 100), '#fca5a5');
  };

  function fallbackDict() {
    return {
      categories: {
        "팬덤비하자": [
          {"word":"길견","score":3},{"word":"길나인","score":3},{"word":"길태","score":3},{"word":"젖퀴","score":3}
        ],
        "타퀴의심": [
          {"word":"덕구","score":2},{"word":"강덕구","score":2},{"word":"케이","score":2},{"word":"보성","score":2}
        ],
        "이간질": [
          {"word":"방갤","score":2},{"word":"벽갤","score":2},{"word":"씨나갤","score":2}
        ]
      },
      levels: [
        {"min":6,"label":"위험","emoji":"🚨"},
        {"min":3,"label":"주의","emoji":"⚠️"},
        {"min":1,"label":"감지","emoji":"🟡"},
        {"min":0,"label":"정상","emoji":"✅"}
      ]
    };
  }

  function flattenKeywords(dict) {
    var out = [];
    var root = dict && dict.categories ? dict.categories : dict;
    if (!root || typeof root !== 'object') return out;

    Object.keys(root).forEach(function (cat) {
      var arr = root[cat];
      if (!Array.isArray(arr)) return;

      arr.forEach(function (x) {
        if (typeof x === 'string') {
          out.push({category:cat, word:x, score:1});
        } else if (x && x.word) {
          out.push({category:cat, word:String(x.word), score:Number(x.score || 1)});
        }
      });
    });

    var seen = {};
    out = out.filter(function (k) {
      var key = k.category + '|' + k.word;
      if (seen[key]) return false;
      seen[key] = true;
      return true;
    });

    out.sort(function (a, b) {
      return String(b.word).length - String(a.word).length;
    });

    return out;
  }

  function getLevels(dict) {
    var levels = dict && Array.isArray(dict.levels) ? dict.levels : fallbackDict().levels;
    return levels.slice().sort(function(a,b){
      return Number(b.min || 0) - Number(a.min || 0);
    });
  }

  function loadDict() {
    return fetch(KEYWORD_URL, {cache:'no-store'})
      .then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      })
      .catch(function () {
        return fallbackDict();
      });
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
      if (/^(전체|인기|와토|공지|정보|사진|영상|이벤트|관리자|추천|댓글|목록)$/.test(t)) return;
      if (!/\/board\//.test(href) && !a.closest('td.subject,.subject,.list_subject')) return;

      titles.push({title:t, href:href});
    });

    var seen = {};
    return titles.filter(function (x) {
      var k = x.title + '|' + x.href;
      if (seen[k]) return false;
      seen[k] = true;
      return true;
    }).slice(0, 80);
  }

  function normalize(s) {
    return String(s || '').toLowerCase().replace(/\s+/g, '');
  }

  function scanTitle(title, keywords) {
    var low = normalize(title);
    var hits = [];

    keywords.forEach(function (k) {
      var w = normalize(k.word);
      if (!w) return;

      var pos = 0, count = 0;
      while ((pos = low.indexOf(w, pos)) !== -1) {
        count++;
        pos += w.length;
      }

      if (count) {
        hits.push({
          category: k.category,
          word: k.word,
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
        var hits = scanTitle(t.title, keywords);
        if (hits.length) rows.push({board:board, title:t.title, href:t.href, hits:hits});
      });

      return rows;
    } catch (e) {
      return [];
    }
  }

  function pickLevel(score, levels) {
    for (var i = 0; i < levels.length; i++) {
      if (score >= Number(levels[i].min || 0)) return levels[i];
    }
    return {label:'정상', emoji:'✅', min:0};
  }

  function render(rows, levels) {
    var total = 0;
    rows.forEach(function (r) {
      r.hits.forEach(function (h) { total += Number(h.sum || h.score || 1); });
    });

    var p = $(PANEL_ID);
    if (!p) return;

    var level = pickLevel(total, levels);

    if (!rows.length) {
      p.style.border = '1px solid #3b82f6';
      p.innerHTML =
        '<div style="padding:10px 42px 10px 13px;background:rgba(15,23,42,.94);border-bottom:1px solid rgba(59,130,246,.45);">' +
        '<button id="guard-close" type="button" style="position:absolute;right:10px;top:8px;width:28px;height:28px;border:0;border-radius:8px;background:#475569;color:#fff;font-weight:1000;cursor:pointer;">×</button>' +
        '<div style="font-size:16px;font-weight:1000;color:#fff;">✅ 게시글 제목 감지</div>' +
        '<div style="margin-top:4px;color:#93c5fd;font-size:13px;font-weight:900;">감지 없음 · 점수 0점 · 감지글 0건</div>' +
        '</div>';
      p.style.display = 'block';
      wireClose();
      return;
    }

    var byCat = {};
    rows.forEach(function (r) {
      r.hits.forEach(function (h) {
        var c = h.category || '감지';
        if (!byCat[c]) byCat[c] = [];
        byCat[c].push(h.word);
      });
    });

    var catHtml = Object.keys(byCat).map(function (cat) {
      var uniq = byCat[cat].filter(function (v, i, a) { return a.indexOf(v) === i; });
      return '<span style="display:inline-block;margin:3px;padding:5px 8px;border-radius:999px;background:#7f1d1d;border:1px solid #ef4444;color:#fff;font-size:12px;font-weight:900;">' +
        esc(cat) + ' : ' + esc(uniq.join(', ')) + '</span>';
    }).join('');

    var list = rows.slice(0, 12).map(function (r) {
      var hitText = r.hits.map(function (h) {
        return h.word + (h.count > 1 ? '×' + h.count : '') + ' +' + h.sum;
      }).join(', ');

      return '<div style="margin-top:8px;padding:9px;border-radius:10px;background:rgba(0,0,0,.25);border:1px solid rgba(255,255,255,.10);">' +
        '<div style="color:#7ec8ff;font-size:12px;font-weight:1000;">' + esc(r.board) + '</div>' +
        '<div style="margin-top:3px;color:#fff;font-size:13px;font-weight:900;line-height:1.35;">' + esc(r.title) + '</div>' +
        '<div style="margin-top:5px;color:#ffb4b4;font-size:12px;font-weight:900;">감지: ' + esc(hitText) + '</div>' +
        '</div>';
    }).join('');

    p.style.border = '1px solid #ef4444';
    p.innerHTML =
      '<div style="position:sticky;top:0;padding:12px 42px 10px 13px;background:rgba(15,23,42,.94);border-bottom:1px solid rgba(239,68,68,.45);">' +
      '<button id="guard-close" type="button" style="position:absolute;right:10px;top:8px;width:28px;height:28px;border:0;border-radius:8px;background:#475569;color:#fff;font-weight:1000;cursor:pointer;">×</button>' +
      '<div style="font-size:17px;font-weight:1000;color:#fff;">' + esc(level.emoji || '🚨') + ' 게시글 제목 감지</div>' +
      '<div style="margin-top:4px;color:#ffb4b4;font-size:13px;font-weight:900;">' + esc(level.label || '감지') + ' · 점수 ' + total + '점 · 감지글 ' + rows.length + '건</div>' +
      '<div style="margin-top:7px;">' + catHtml + '</div>' +
      '</div><div style="padding:10px 12px 13px;">' + list + '</div>';

    p.style.display = 'block';
    wireClose();
  }

  function run(keywords, levels) {
    var all = [];
    document.querySelectorAll('iframe.yg-frame').forEach(function (f) {
      all = all.concat(scanFrame(f, keywords));
    });
    render(all, levels);
  }

  setStatus('키워드 로딩중...', '#93c5fd');

  loadDict().then(function (dict) {
    var keywords = flattenKeywords(dict);
    var levels = getLevels(dict);

    setStatus('키워드 ' + keywords.length + '개 로드 완료 · 검색결과 로딩중...', '#93c5fd');

    document.querySelectorAll('iframe.yg-frame').forEach(function (f) {
      f.addEventListener('load', function () {
        setTimeout(function () { run(keywords, levels); }, 700);
      });
    });

    setTimeout(function () { run(keywords, levels); }, 1800);
    setTimeout(function () { run(keywords, levels); }, 3500);
  });
})();
