(function () {
  'use strict';

  const API_URL = 'https://broadstatistic.sooplive.com/api/watch_statistic.php';

  const TARGETS = [
    { key: 'chulgu100', label: '철구형2↑', patterns: ['철구형2↑','철구형2','철구형'], thresholdSeconds: 360000 },
    { key: 'yeomboseong', label: 'A-염보성!!', patterns: ['A-염보성!!', 'A-염보성', '염보성', '염보'] },
    { key: 'bjkei', label: '[BJ]케이', patterns: ['[BJ]케이', 'BJ케이', '비제이케이', '비제이 케이', '케이'] }
  ];

  const pad = n => String(n).padStart(2, '0');
  const today = new Date();
  const fmtDate = d => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
  const defaultEnd = fmtDate(today);
  const defaultStartDate = new Date(today.getTime() - 6 * 24 * 60 * 60 * 1000);
  const defaultStart = fmtDate(defaultStartDate);

  function normalize(s) {
    return String(s || '')
      .replace(/\s+/g, '')
      .replace(/[\u200B-\u200D\uFEFF]/g, '')
      .toLowerCase();
  }

  function escapeHtml(s) {
    return String(s || '').replace(/[&<>"']/g, ch => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    }[ch]));
  }

  function getCookie(name) {
    const m = document.cookie.match(new RegExp('(?:^|; )' + name.replace(/[.$?*|{}()[\]\\/+^]/g, '\\$&') + '=([^;]*)'));
    return m ? decodeURIComponent(m[1]) : '';
  }

  function getSoopIdFromCookie() {
    const ticket = getCookie('UserTicket');
    if (!ticket) return '';
    try {
      const params = new URLSearchParams(ticket);
      return params.get('uid') || '';
    } catch (e) {
      const m = ticket.match(/(?:^|&)uid=([^&]+)/);
      return m ? decodeURIComponent(m[1]) : '';
    }
  }

  function parseTimeToSeconds(v) {
    if (typeof v === 'number') return v;
    const s = String(v || '').trim();
    const m = s.match(/^(\d+):(\d+):(\d+)$/);
    if (!m) return 0;
    return (+m[1]) * 3600 + (+m[2]) * 60 + (+m[3]);
  }

  function secondsToHms(sec) {
    sec = Math.max(0, Math.floor(Number(sec) || 0));
    const h = Math.floor(sec / 3600);
    const m = Math.floor((sec % 3600) / 60);
    const s = sec % 60;
    return `${pad(h)}:${pad(m)}:${pad(s)}`;
  }

  function sumData(arr) {
    if (!Array.isArray(arr)) return 0;
    return arr.reduce((a, b) => a + (Number(b) || 0), 0);
  }

  async function fetchWatchPage({ soopId, startDate, endDate, page }) {
    const body = new URLSearchParams();
    body.set('szModule', 'UserLiveWatchTimeData');
    body.set('szMethod', 'watch');
    body.set('szStartDate', startDate);
    body.set('szEndDate', endDate);
    body.set('nPage', String(page || 1));
    body.set('szId', soopId);

    const res = await fetch(API_URL, {
      method: 'POST',
      credentials: 'include',
      mode: 'cors',
      headers: {
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',      },
      body: body.toString()
    });

    const text = await res.text();
    let json;
    try {
      json = JSON.parse(text);
    } catch (e) {
      throw new Error('SOOP 응답을 JSON으로 읽지 못했습니다. 로그인 상태/페이지 위치를 확인하세요.');
    }
    if (!json || json.result !== 1) {
      throw new Error((json && json.message) ? json.message : 'SOOP 시청기록 조회 실패');
    }
    return json;
  }

  async function fetchWatchData(opts) {
    // nPage가 실제 페이지에 따라 달라질 수 있어서 1~5페이지까지 중복 없이 합친다.
    const merged = new Map();
    let first = null;
    for (let page = 1; page <= 5; page++) {
      const json = await fetchWatchPage({ ...opts, page });
      if (!first) first = json;
      const stack = (((json || {}).data || {}).chart || {}).data_stack || [];
      if (!Array.isArray(stack) || stack.length === 0) break;
      let newCount = 0;
      for (const row of stack) {
        const nick = String(row.bj_nick || '').trim();
        if (!nick || nick === '기타') continue;
        const key = normalize(nick);
        const seconds = sumData(row.data);
        if (!merged.has(key)) {
          merged.set(key, { bj_nick: nick, seconds, raw: row });
          newCount++;
        } else {
          const prev = merged.get(key);
          prev.seconds = Math.max(prev.seconds, seconds);
        }
      }
      if (page > 1 && newCount === 0) break;
    }
    return { raw: first, rows: Array.from(merged.values()) };
  }

  function judgeTargets(rows) {
    return TARGETS.map(t => {
      const pats = t.patterns.map(normalize).filter(Boolean);
      const hits = rows.filter(r => pats.some(p => normalize(r.bj_nick).includes(p)));
      const seconds = hits.reduce((a, r) => a + (Number(r.seconds) || 0), 0);
      return {
        key: t.key,
        label: t.label,
        found: hits.length > 0 && seconds > 0,
        seconds,
        hits: hits.map(h => h.bj_nick)
      };
    });
  }

  function drawRoundRect(ctx, x, y, w, h, r) {
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.arcTo(x + w, y, x + w, y + h, r);
    ctx.arcTo(x + w, y + h, x, y + h, r);
    ctx.arcTo(x, y + h, x, y, r);
    ctx.arcTo(x, y, x + w, y, r);
    ctx.closePath();
  }

  function makeCanvas({ nick, soopId, startDate, endDate, results, updatedAt }) {
    const issuedAt = `${fmtDate(new Date())} ${pad(new Date().getHours())}:${pad(new Date().getMinutes())}`;
    const c = document.createElement('canvas');
    c.width = 1200;
    c.height = 820;
    const ctx = c.getContext('2d');

    const bg = ctx.createLinearGradient(0, 0, 1200, 820);
    bg.addColorStop(0, '#071426');
    bg.addColorStop(0.5, '#04070f');
    bg.addColorStop(1, '#001d36');
    ctx.fillStyle = bg;
    ctx.fillRect(0, 0, 1200, 820);

    // Soft glow
    ctx.save();
    ctx.globalAlpha = 0.14;
    ctx.fillStyle = '#60a5fa';
    ctx.beginPath(); ctx.arc(170, 85, 250, 0, Math.PI * 2); ctx.fill();
    ctx.beginPath(); ctx.arc(1040, 760, 290, 0, Math.PI * 2); ctx.fill();
    ctx.restore();

    // Watermark pattern
    ctx.save();
    ctx.globalAlpha = 0.045;
    ctx.translate(60, 760);
    ctx.rotate(-0.35);
    ctx.font = 'bold 38px Malgun Gothic, Arial';
    ctx.fillStyle = '#ffffff';
    const wm = `YGOSU ${nick}  ·  RECAP SELF CHECK  ·  ${startDate}~${endDate}`;
    for (let y = -980; y < 560; y += 120) {
      for (let x = -320; x < 1380; x += 700) ctx.fillText(wm, x, y);
    }
    ctx.restore();

    // Main certificate card
    drawRoundRect(ctx, 80, 55, 1040, 710, 40);
    ctx.fillStyle = 'rgba(3, 8, 18, 0.84)';
    ctx.fill();
    ctx.lineWidth = 3;
    ctx.strokeStyle = 'rgba(96, 165, 250, .72)';
    ctx.stroke();

    drawRoundRect(ctx, 110, 85, 980, 650, 32);
    ctx.strokeStyle = 'rgba(147, 197, 253, .22)';
    ctx.lineWidth = 2;
    ctx.stroke();

    ctx.textAlign = 'center';

    ctx.fillStyle = '#ffffff';
    ctx.font = 'bold 56px Malgun Gothic, Arial';
    ctx.fillText('📋 리캡 셀프 인증', 600, 145);

    ctx.font = 'bold 22px Malgun Gothic, Arial';
    ctx.fillStyle = '#bfdbfe';
    ctx.fillText(`${startDate} ~ ${endDate}`, 600, 188);

    // Nick certificate line
    ctx.fillStyle = '#93c5fd';
    ctx.font = 'bold 24px Malgun Gothic, Arial';
    ctx.fillText('🧑 와고닉', 600, 250);

    ctx.fillStyle = '#ffffff';
    ctx.font = 'bold 48px Malgun Gothic, Arial';
    ctx.fillText(nick, 600, 305);

    const chulgu = results.find(r => r.key === 'chulgu100');
    const chulguHours = chulgu ? Math.floor((Number(chulgu.seconds) || 0) / 3600) : 0;

    // Chulgu highlight
    drawRoundRect(ctx, 225, 350, 750, 132, 30);
    ctx.fillStyle = 'rgba(120, 53, 15, .72)';
    ctx.fill();
    ctx.lineWidth = 3;
    ctx.strokeStyle = 'rgba(253, 230, 138, .70)';
    ctx.stroke();

    ctx.fillStyle = '#fde68a';
    ctx.font = 'bold 34px Malgun Gothic, Arial';
    ctx.fillText('🐵 철구 시청', 600, 402);

    ctx.fillStyle = '#ffffff';
    ctx.font = 'bold 58px Malgun Gothic, Arial';
    ctx.fillText(`${chulguHours}시간`, 600, 460);

    // Target rows
    const checkRows = results.filter(r => r.key !== 'chulgu100');
    let y = 560;
    ctx.font = 'bold 34px Malgun Gothic, Arial';
    checkRows.forEach((r) => {
      ctx.fillStyle = r.found ? '#fecaca' : '#bbf7d0';
      const mark = r.found ? '✅' : '❌';
      const word = r.found ? '감지' : '미감지';
      const timeText = r.found ? ` · ${secondsToHms(r.seconds)}` : '';
      ctx.fillText(`${mark} ${r.label} ${word}${timeText}`, 600, y);
      y += 58;
    });

    // Footer
    ctx.textAlign = 'left';
    ctx.fillStyle = '#cbd5e1';
    ctx.font = 'bold 18px Malgun Gothic, Arial';
    ctx.fillText('※ SOOP 시청기록 API 기준으로 생성된 리캡 셀프 인증 이미지입니다.', 145, 700);
    ctx.fillText(`※ 조회갱신: ${updatedAt || '-'} · 생성시각: ${issuedAt}`, 145, 728);
    ctx.fillText('※ 본인 로그인 상태에서만 조회되며, 타인의 기록은 조회하지 않습니다.', 145, 756);

    return c;
  }

  function showResultOverlay(opts) {
    const old = document.getElementById('soop-recap-check-overlay');
    if (old) old.remove();

    const canvas = makeCanvas(opts);
    canvas.style.maxWidth = '100%';
    canvas.style.height = 'auto';
    canvas.style.borderRadius = '16px';
    canvas.style.boxShadow = '0 12px 35px rgba(0,0,0,.35)';

    const wrap = document.createElement('div');
    wrap.id = 'soop-recap-check-overlay';
    wrap.style.cssText = 'position:fixed;z-index:2147483647;inset:0;background:rgba(0,0,0,.72);display:flex;align-items:center;justify-content:center;padding:24px;font-family:Arial,Malgun Gothic,sans-serif;box-sizing:border-box;';

    const panel = document.createElement('div');
    panel.style.cssText = 'width:980px;max-width:96vw;max-height:96vh;overflow:auto;background:#071426;border:1px solid #60a5fa;border-radius:22px;padding:18px;box-shadow:0 0 45px rgba(96,165,250,.45);box-sizing:border-box;text-align:center;color:#fff;';

    const title = document.createElement('div');
    title.textContent = '📋 리캡 셀프 인증 이미지 생성 완료';
    title.style.cssText = 'font-size:22px;font-weight:1000;margin:4px 0 14px;color:#fff;';

    const btns = document.createElement('div');
    btns.style.cssText = 'margin-top:14px;display:flex;gap:10px;justify-content:center;flex-wrap:wrap;';

    const save = document.createElement('button');
    save.textContent = 'PNG 저장';
    save.style.cssText = 'cursor:pointer;border:0;border-radius:999px;padding:12px 22px;background:#2563eb;color:#fff;font-weight:1000;font-size:15px;';
    save.onclick = function () {
      const a = document.createElement('a');
      const safeNick = opts.nick.replace(/[\\/:*?"<>|\s]+/g, '_').slice(0, 40) || 'ygosu';
      a.download = `리캡셀프인증_${safeNick}_${opts.startDate}_${opts.endDate}.png`;
      a.href = canvas.toDataURL('image/png');
      a.click();
    };

    const back = document.createElement('button');
    back.textContent = '다시 조회';
    back.style.cssText = 'cursor:pointer;border:1px solid #60a5fa;border-radius:999px;padding:12px 22px;background:#0f172a;color:#fff;font-weight:1000;font-size:15px;';
    back.onclick = function () { wrap.remove(); showInputOverlay(); };

    const close = document.createElement('button');
    close.textContent = '닫기';
    close.style.cssText = 'cursor:pointer;border:1px solid #64748b;border-radius:999px;padding:12px 22px;background:#111827;color:#fff;font-weight:1000;font-size:15px;';
    close.onclick = function () { wrap.remove(); };

    btns.appendChild(save);
    btns.appendChild(back);
    btns.appendChild(close);
    panel.appendChild(title);
    panel.appendChild(canvas);
    panel.appendChild(btns);
    wrap.appendChild(panel);
    document.body.appendChild(wrap);
  }

  function showInputOverlay() {
    const old = document.getElementById('soop-recap-check-input');
    if (old) old.remove();

    const uid = getSoopIdFromCookie();

    const wrap = document.createElement('div');
    wrap.id = 'soop-recap-check-input';
    wrap.style.cssText = 'position:fixed;z-index:2147483647;inset:0;background:rgba(0,0,0,.74);display:flex;align-items:center;justify-content:center;padding:22px;font-family:Arial,Malgun Gothic,sans-serif;box-sizing:border-box;';

    const panel = document.createElement('div');
    panel.style.cssText = 'width:500px;max-width:94vw;background:radial-gradient(circle at top,rgba(45,145,255,.24),transparent 38%),linear-gradient(180deg,#071426,#03070f);border:1px solid rgba(96,165,250,.72);border-radius:24px;padding:22px;box-shadow:0 0 45px rgba(96,165,250,.42);box-sizing:border-box;color:#fff;';

    panel.innerHTML = `
      <div style="text-align:center;margin-bottom:16px;">
        <div style="display:inline-block;padding:6px 12px;border-radius:999px;background:rgba(96,165,250,.14);border:1px solid rgba(147,197,253,.34);color:#bfdbfe;font-size:11px;font-weight:1000;">SOOP WATCH CHECK</div>
        <div style="margin-top:10px;font-size:25px;font-weight:1000;letter-spacing:-.6px;">📋 리캡 셀프 인증</div>
        <div style="margin-top:7px;font-size:12px;font-weight:800;color:#cbd5e1;line-height:1.55;">
          SOOP 로그인 상태에서 기간을 선택하면<br>
          A-염보성!! / [BJ]케이 기록만 자동 판독합니다.
        </div>
      </div>

      <div style="padding:14px;border-radius:16px;background:rgba(15,23,42,.72);border:1px solid rgba(147,197,253,.22);">
        <label style="display:block;font-size:12px;font-weight:1000;color:#93c5fd;margin-bottom:6px;">와이고수 닉네임</label>
        <input id="rcNick" type="text" placeholder="와이고수 닉네임 입력" style="width:100%;box-sizing:border-box;border:1px solid #334155;border-radius:12px;background:#020617;color:#fff;padding:12px;font-size:15px;font-weight:900;outline:none;">

        <div style="display:flex;gap:10px;margin-top:10px;">
          <div style="flex:1;">
            <label style="display:block;font-size:12px;font-weight:1000;color:#93c5fd;margin-bottom:6px;">시작일</label>
            <input id="rcStart" type="date" value="${defaultStart}" style="width:100%;box-sizing:border-box;border:1px solid #334155;border-radius:12px;background:#020617;color:#fff;padding:11px;font-size:14px;font-weight:900;outline:none;">
          </div>
          <div style="flex:1;">
            <label style="display:block;font-size:12px;font-weight:1000;color:#93c5fd;margin-bottom:6px;">종료일</label>
            <input id="rcEnd" type="date" value="${defaultEnd}" style="width:100%;box-sizing:border-box;border:1px solid #334155;border-radius:12px;background:#020617;color:#fff;padding:11px;font-size:14px;font-weight:900;outline:none;">
          </div>
        </div>
      </div>

      <div id="rcMsg" style="margin-top:12px;min-height:20px;font-size:12px;font-weight:900;color:#fcd34d;text-align:center;"></div>

      <div style="margin-top:16px;display:flex;gap:9px;justify-content:center;flex-wrap:wrap;">
        <button id="rcRun" style="cursor:pointer;border:0;border-radius:999px;padding:13px 22px;background:linear-gradient(135deg,#dc2626,#991b1b);color:#fff;font-weight:1000;font-size:15px;box-shadow:0 8px 20px rgba(220,38,38,.24);">조회 후 이미지 생성</button>
        <button id="rcClose" style="cursor:pointer;border:1px solid #64748b;border-radius:999px;padding:13px 22px;background:#111827;color:#fff;font-weight:1000;font-size:15px;">닫기</button>
      </div>

      <div style="margin-top:12px;text-align:center;color:#94a3b8;font-size:11px;font-weight:800;line-height:1.45;">
        ※ 조회 기간은 최대 30일까지만 가능합니다.<br>
        ※ SOOP ID는 이미지에 표시하지 않습니다.
      </div>
    `;

    wrap.appendChild(panel);
    document.body.appendChild(wrap);

    const msg = panel.querySelector('#rcMsg');
    const startInput = panel.querySelector('#rcStart');
    const endInput = panel.querySelector('#rcEnd');

    [startInput, endInput].forEach(function (el) {
      el.addEventListener('click', function () {
        if (this.showPicker) {
          try { this.showPicker(); } catch (e) {}
        }
      });
    });

    panel.querySelector('#rcClose').onclick = () => wrap.remove();

    panel.querySelector('#rcRun').onclick = async function () {
      const nick = panel.querySelector('#rcNick').value.trim();
      const soopId = getSoopIdFromCookie();
      const startDate = startInput.value;
      const endDate = endInput.value;

      if (!nick) return alert('와이고수 닉네임을 입력하세요.');
      if (!soopId) return alert('SOOP 로그인 상태를 확인할 수 없습니다. SOOP 로그인 후 다시 실행하세요.');
      if (!startDate || !endDate) return alert('시작일/종료일을 선택하세요.');
      if (startDate > endDate) return alert('시작일이 종료일보다 늦습니다.');

      const s = new Date(startDate + 'T00:00:00');
      const e = new Date(endDate + 'T00:00:00');
      const diffDays = Math.floor((e - s) / (24 * 60 * 60 * 1000)) + 1;
      if (diffDays > 30) return alert('조회 기간은 최대 30일까지만 가능합니다.');

      try {
        msg.textContent = 'SOOP 시청기록 조회 중...';
        const data = await fetchWatchData({ soopId, startDate, endDate });
        const results = judgeTargets(data.rows);
        const updatedAt = (((data.raw || {}).data || {}).updatetime) || '';
        wrap.remove();
        showResultOverlay({ nick, soopId, startDate, endDate, results, updatedAt });
      } catch (err) {
        msg.textContent = '';
        alert('조회 실패: ' + (err && err.message ? err.message : err));
        console.error('[SOOP Recap Check]', err);
      }
    };
  }

  try {
    showInputOverlay();
  } catch (err) {
    alert('리캡 셀프 인증 실행 실패: ' + (err && err.message ? err.message : err));
    console.error('[SOOP Recap Check]', err);
  }
})();