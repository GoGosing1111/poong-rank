(function () {
  'use strict';

  const KEYWORD_URL = 'https://keyman1335-maker.github.io/poong-rank/bad_words.json?v=' + Date.now();
  const PANEL_ID = 'ygosu-title-guard-panel';

  function cleanTitle(raw) {
    let t = String(raw || '').trim();
    t = t.replace(/\s*\|\s*YGOSU.*$/i, '');
    t = t.replace(/\s*-\s*와이고수.*$/i, '');
    return t.trim();
  }

  function getTitle() {
    const candidates = [
      document.querySelector('.board_view_subject'),
      document.querySelector('.view_title'),
      document.querySelector('.title'),
      document.querySelector('h1'),
      document.querySelector('h2')
    ];
    for (const el of candidates) {
      if (el && el.textContent && el.textContent.trim().length > 2) {
        return cleanTitle(el.textContent);
      }
    }
    return cleanTitle(document.title);
  }

  function normalize(s) {
    return String(s || '').toLowerCase().replace(/\s+/g, '');
  }

  function countMatches(text, word) {
    const t = normalize(text);
    const w = normalize(word);
    if (!w) return 0;
    let count = 0;
    let pos = 0;
    while ((pos = t.indexOf(w, pos)) !== -1) {
      count += 1;
      pos += w.length;
    }
    return count;
  }

  function analyze(title, dict) {
    const categories = dict.categories || {};
    const hits = [];
    let totalScore = 0;

    Object.keys(categories).forEach((category) => {
      const items = categories[category] || [];
      items.forEach((item) => {
        const word = typeof item === 'string' ? item : item.word;
        const score = Number(typeof item === 'string' ? 1 : (item.score || 1));
        const count = countMatches(title, word);
        if (count > 0) {
          const sum = score * count;
          totalScore += sum;
          hits.push({ category, word, count, score, sum });
        }
      });
    });

    const levels = dict.levels || [
      { min: 6, label: '위험', emoji: '🚨' },
      { min: 3, label: '주의', emoji: '⚠️' },
      { min: 1, label: '감지', emoji: '🟡' },
      { min: 0, label: '정상', emoji: '✅' }
    ];
    const level = levels
      .slice()
      .sort((a, b) => Number(b.min) - Number(a.min))
      .find((x) => totalScore >= Number(x.min)) || levels[levels.length - 1];

    return { title, hits, totalScore, level };
  }

  function esc(s) {
    return String(s || '').replace(/[&<>"']/g, (c) => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    }[c]));
  }

  function render(result) {
    const old = document.getElementById(PANEL_ID);
    if (old) old.remove();

    const danger = result.totalScore >= 6;
    const warn = result.totalScore >= 3;
    const accent = danger ? '#ef4444' : warn ? '#f59e0b' : result.totalScore > 0 ? '#eab308' : '#22c55e';

    const hitHtml = result.hits.length
      ? result.hits.map((h) => `
        <div style="display:flex;justify-content:space-between;gap:10px;padding:8px 0;border-bottom:1px dotted rgba(255,255,255,.14);">
          <div><b style="color:#fff;">${esc(h.word)}</b> <span style="color:#94a3b8;">${esc(h.category)}</span></div>
          <div style="color:#7ec8ff;font-weight:900;white-space:nowrap;">${h.count}회 / +${h.sum}</div>
        </div>`).join('')
      : '<div style="padding:12px 0;color:#cbd5e1;font-weight:900;text-align:center;">감지된 키워드 없음</div>';

    const box = document.createElement('div');
    box.id = PANEL_ID;
    box.style.cssText = 'position:fixed;right:18px;top:18px;width:min(420px,calc(100vw - 36px));z-index:2147483647;background:#071426;color:#fff;border:1px solid ' + accent + ';border-radius:18px;box-shadow:0 18px 50px rgba(0,0,0,.65),0 0 22px ' + accent + '55;overflow:hidden;font-family:Arial,Malgun Gothic,sans-serif;';
    box.innerHTML = `
      <div style="padding:14px 15px;background:linear-gradient(135deg,${accent}33,rgba(0,0,0,.36));border-bottom:1px solid rgba(255,255,255,.12);">
        <div style="display:flex;justify-content:space-between;align-items:center;gap:10px;">
          <div style="font-size:16px;font-weight:1000;color:#fff;text-shadow:0 2px 0 #000;">${esc(result.level.emoji)} 게시글 제목 감지</div>
          <button id="ygosu-title-guard-close" style="border:0;background:rgba(255,255,255,.12);color:#fff;border-radius:999px;width:30px;height:30px;font-size:18px;font-weight:900;cursor:pointer;">×</button>
        </div>
        <div style="margin-top:9px;display:flex;gap:8px;align-items:center;">
          <span style="display:inline-block;padding:5px 9px;border-radius:999px;background:${accent};color:#fff;font-size:12px;font-weight:1000;">${esc(result.level.label)}</span>
          <span style="color:#cbd5e1;font-size:12px;font-weight:900;">점수 ${result.totalScore}</span>
        </div>
      </div>
      <div style="padding:14px 15px;">
        <div style="color:#94a3b8;font-size:11px;font-weight:900;margin-bottom:6px;">분석 제목</div>
        <div style="padding:10px;border-radius:12px;background:rgba(0,0,0,.28);border:1px solid rgba(255,255,255,.10);color:#fff;font-size:13px;font-weight:900;line-height:1.45;word-break:break-word;">${esc(result.title)}</div>
        <div style="margin-top:12px;color:#94a3b8;font-size:11px;font-weight:900;">감지 키워드</div>
        <div style="margin-top:2px;font-size:13px;">${hitHtml}</div>
      </div>
      <div style="padding:10px 15px;border-top:1px solid rgba(255,255,255,.10);color:#64748b;font-size:10px;font-weight:800;text-align:center;">bad_words.json 외부 키워드 기준</div>`;
    document.body.appendChild(box);
    document.getElementById('ygosu-title-guard-close').onclick = () => box.remove();
  }

  async function main() {
    const title = getTitle();
    let dict;
    try {
      const res = await fetch(KEYWORD_URL, { cache: 'no-store' });
      dict = await res.json();
    } catch (e) {
      alert('키워드 파일을 불러오지 못했습니다: ' + e.message);
      return;
    }
    render(analyze(title, dict));
  }

  main();
})();
