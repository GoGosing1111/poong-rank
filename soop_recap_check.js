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
    const now = new Date();
    const issuedDate = fmtDate(now);
    const issuedAt = `${issuedDate} ${pad(now.getHours())}:${pad(now.getMinutes())}`;
    const certNo = `SR-${issuedDate.replace(/-/g, '')}-${pad(now.getHours())}${pad(now.getMinutes())}`;
    const c = document.createElement('canvas');
    c.width = 1200;
    c.height = 840;
    const ctx = c.getContext('2d');

    // Premium black/gold certificate background
    const bg = ctx.createLinearGradient(0, 0, 1200, 840);
    bg.addColorStop(0, '#060402');
    bg.addColorStop(0.5, '#14100a');
    bg.addColorStop(1, '#030302');
    ctx.fillStyle = bg;
    ctx.fillRect(0, 0, 1200, 840);

    // Soft gold glow
    ctx.save();
    ctx.globalAlpha = 0.16;
    let g1 = ctx.createRadialGradient(220, 120, 10, 220, 120, 360);
    g1.addColorStop(0, '#f6d276');
    g1.addColorStop(1, 'rgba(246,210,118,0)');
    ctx.fillStyle = g1;
    ctx.fillRect(0, 0, 1200, 840);
    let g2 = ctx.createRadialGradient(980, 700, 10, 980, 700, 330);
    g2.addColorStop(0, '#b57924');
    g2.addColorStop(1, 'rgba(181,121,36,0)');
    ctx.fillStyle = g2;
    ctx.fillRect(0, 0, 1200, 840);
    ctx.restore();

    // Subtle watermark, smaller and quieter
    ctx.save();
    ctx.globalAlpha = 0.028;
    ctx.translate(135, 610);
    ctx.rotate(-0.22);
    ctx.font = 'bold 92px Georgia, Malgun Gothic, serif';
    ctx.fillStyle = '#ffe7a6';
    ctx.fillText('SOOP RECAP', 0, 0);
    ctx.restore();

    // Outer frame
    drawRoundRect(ctx, 58, 52, 1084, 728, 22);
    ctx.fillStyle = 'rgba(10, 8, 6, 0.92)';
    ctx.fill();
    ctx.lineWidth = 4;
    ctx.strokeStyle = '#d6a84f';
    ctx.stroke();

    // inner borders
    drawRoundRect(ctx, 82, 76, 1036, 680, 16);
    ctx.lineWidth = 2;
    ctx.strokeStyle = 'rgba(255, 231, 166, .58)';
    ctx.stroke();
    drawRoundRect(ctx, 108, 102, 984, 628, 12);
    ctx.lineWidth = 1.2;
    ctx.strokeStyle = 'rgba(174, 122, 42, .46)';
    ctx.stroke();

    // corner ornaments, smaller
    function corner(x, y, sx, sy) {
      ctx.save();
      ctx.translate(x, y); ctx.scale(sx, sy);
      ctx.strokeStyle = '#e6be69'; ctx.lineWidth = 3; ctx.lineCap = 'round';
      ctx.beginPath(); ctx.moveTo(0, 36); ctx.quadraticCurveTo(0, 0, 36, 0); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(15, 50); ctx.quadraticCurveTo(18, 18, 50, 15); ctx.stroke();
      ctx.restore();
    }
    corner(135, 128, 1, 1); corner(1065, 128, -1, 1); corner(135, 704, 1, -1); corner(1065, 704, -1, -1);

    ctx.textAlign = 'center';

    // Header
    ctx.fillStyle = '#d6a84f';
    ctx.font = 'bold 22px Georgia, Malgun Gothic, serif';
    ctx.fillText('SOOP RECAP', 600, 132);
    ctx.strokeStyle = 'rgba(214,168,79,.62)';
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.moveTo(438, 140); ctx.lineTo(548, 140);
    ctx.moveTo(652, 140); ctx.lineTo(762, 140);
    ctx.stroke();

    ctx.fillStyle = '#f8e7b0';
    ctx.font = 'bold 60px Malgun Gothic, Arial';
    ctx.fillText('리캡 셀프 인증서', 600, 207);

    ctx.fillStyle = '#caa15a';
    ctx.font = 'bold 19px Georgia, Malgun Gothic, serif';
    ctx.fillText('CERTIFICATE OF WATCH RECAP VERIFICATION', 600, 242);

    // Date ribbon
    drawRoundRect(ctx, 390, 264, 420, 42, 20);
    ctx.fillStyle = 'rgba(214,168,79,.13)';
    ctx.fill();
    ctx.strokeStyle = 'rgba(255,231,166,.38)';
    ctx.lineWidth = 1.4;
    ctx.stroke();
    ctx.fillStyle = '#ffe7a6';
    ctx.font = 'bold 20px Malgun Gothic, Arial';
    ctx.fillText(`${startDate}  ~  ${endDate}`, 600, 292);

    // body text
    ctx.fillStyle = '#d9c595';
    ctx.font = 'bold 21px Malgun Gothic, Arial';
    ctx.fillText('본 인증서는 아래 와고닉의 SOOP 시청기록 기준으로 생성되었습니다.', 600, 348);

    ctx.fillStyle = '#d6a84f';
    ctx.font = 'bold 19px Malgun Gothic, Arial';
    ctx.fillText('인증 대상자', 600, 390);
    ctx.fillStyle = '#ffffff';
    ctx.font = 'bold 54px Malgun Gothic, Arial';
    ctx.fillText(nick, 600, 450);

    const chulgu = results.find(r => r.key === 'chulgu100');
    const chulguSeconds = chulgu ? Number(chulgu.seconds) || 0 : 0;
    const chulguHours = Math.floor(chulguSeconds / 3600);
    const yeom = results.find(r => r.key === 'yeomboseong');
    const kei = results.find(r => r.key === 'bjkei');
    const h = (r) => `${Math.floor((Number(r && r.seconds) || 0) / 3600)}시간`;

    // Main watch time box
    drawRoundRect(ctx, 250, 480, 700, 100, 12);
    ctx.fillStyle = 'rgba(0,0,0,.22)';
    ctx.fill();
    ctx.lineWidth = 1.7;
    ctx.strokeStyle = 'rgba(214,168,79,.70)';
    ctx.stroke();
    ctx.fillStyle = '#f5d98a';
    ctx.font = 'bold 25px Malgun Gothic, Arial';
    ctx.fillText('총 누적 시청시간', 600, 516);
    ctx.fillStyle = '#f4d183';
    ctx.font = 'bold 58px Georgia, Malgun Gothic, serif';
    ctx.fillText(`${chulguHours}시간`, 600, 565);

    // 3 columns
    drawRoundRect(ctx, 172, 608, 856, 92, 10);
    ctx.strokeStyle = 'rgba(214,168,79,.62)';
    ctx.lineWidth = 1.5;
    ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(457, 624); ctx.lineTo(457, 686);
    ctx.moveTo(743, 624); ctx.lineTo(743, 686);
    ctx.strokeStyle = 'rgba(214,168,79,.40)';
    ctx.stroke();

    const cols = [
      ['철구 시청 누적', `${chulguHours}시간`],
      ['A-염보성!! 시청 누적', h(yeom)],
      ['[BJ]케이 시청 누적', h(kei)]
    ];
    [315, 600, 885].forEach((x, i) => {
      ctx.fillStyle = '#d6a84f';
      ctx.font = 'bold 18px Malgun Gothic, Arial';
      ctx.fillText(cols[i][0], x, 643);
      ctx.fillStyle = i === 0 ? '#f4d183' : '#ffffff';
      ctx.font = 'bold 31px Malgun Gothic, Arial';
      ctx.fillText(cols[i][1], x, 680);
    });

    // Issue info and signature
    ctx.textAlign = 'left';
    ctx.fillStyle = '#d9c595';
    ctx.font = 'bold 15px Malgun Gothic, Arial';
    ctx.fillText('발급일', 170, 724);
    ctx.fillStyle = '#f2d58a';
    ctx.fillText(issuedDate, 235, 724);
    ctx.fillStyle = '#d9c595';
    ctx.fillText('인증번호', 170, 750);
    ctx.fillStyle = '#f2d58a';
    ctx.fillText(certNo, 250, 750);

    ctx.textAlign = 'center';
    ctx.fillStyle = '#d6a84f';
    ctx.font = 'italic 34px Georgia, serif';
    ctx.fillText('SOOP Recap Verified', 600, 735);
    ctx.strokeStyle = 'rgba(214,168,79,.55)';
    ctx.lineWidth = 1;
    ctx.beginPath(); ctx.moveTo(450, 748); ctx.lineTo(750, 748); ctx.stroke();
    ctx.fillStyle = '#c9b27d';
    ctx.font = 'bold 13px Georgia, Malgun Gothic, serif';
    ctx.fillText('OFFICIAL VERIFICATION', 600, 768);

    // Footer: moved safely inside frame, no overlap
    ctx.fillStyle = '#b89a61';
    ctx.font = 'bold 13px Malgun Gothic, Arial';
    ctx.fillText(`SOOP 시청기록 API 기준 · 조회갱신 ${updatedAt || '-'} · 생성시각 ${issuedAt}`, 600, 790);
    ctx.fillText('본인 로그인 상태에서만 조회되며 타인의 기록은 조회하지 않습니다.', 600, 812);

    return c;
  }

  
  function showResultOverlay(opts) {
    const old = document.getElementById('soop-recap-check-overlay');
    if (old) old.remove();

    const canvas = makeCanvas(opts);
    canvas.style.maxWidth = '100%';
    canvas.style.height = 'auto';
    canvas.style.borderRadius = '16px';
    canvas.style.boxShadow = '0 16px 45px rgba(0,0,0,.55)';

    const wrap = document.createElement('div');
    wrap.id = 'soop-recap-check-overlay';
    wrap.style.cssText = 'position:fixed;z-index:2147483647;inset:0;background:rgba(0,0,0,.72);display:flex;align-items:center;justify-content:center;padding:24px;font-family:Arial,Malgun Gothic,sans-serif;box-sizing:border-box;';

    const panel = document.createElement('div');
    panel.style.cssText = 'width:980px;max-width:96vw;max-height:96vh;overflow:auto;background:linear-gradient(180deg,#130d07,#050403);border:1px solid #d6a84f;border-radius:22px;padding:18px;box-shadow:0 0 48px rgba(214,168,79,.34);box-sizing:border-box;text-align:center;color:#fff;';

    const title = document.createElement('div');
    title.textContent = '🏆 리캡 셀프 인증서 생성 완료';
    title.style.cssText = 'font-size:22px;font-weight:1000;margin:4px 0 14px;color:#f8e7b0;';

    const btns = document.createElement('div');
    btns.style.cssText = 'margin-top:14px;display:flex;gap:10px;justify-content:center;flex-wrap:wrap;';

    const save = document.createElement('button');
    save.textContent = 'PNG 저장';
    save.style.cssText = 'cursor:pointer;border:0;border-radius:999px;padding:12px 22px;background:linear-gradient(135deg,#d6a84f,#7a4a15);color:#171009;font-weight:1000;font-size:15px;';
    save.onclick = function () {
      const a = document.createElement('a');
      const safeNick = opts.nick.replace(/[\\/:*?"<>|\s]+/g, '_').slice(0, 40) || 'ygosu';
      a.download = `리캡셀프인증_${safeNick}_${opts.startDate}_${opts.endDate}.png`;
      a.href = canvas.toDataURL('image/png');
      a.click();
    };

    const back = document.createElement('button');
    back.textContent = '다시 조회';
    back.style.cssText = 'cursor:pointer;border:1px solid #d6a84f;border-radius:999px;padding:12px 22px;background:#171009;color:#f8e7b0;font-weight:1000;font-size:15px;';
    back.onclick = function () { wrap.remove(); showInputOverlay(); };

    const close = document.createElement('button');
    close.textContent = '닫기';
    close.style.cssText = 'cursor:pointer;border:1px solid #64748b;border-radius:999px;padding:12px 22px;background:#171009;color:#f8e7b0;font-weight:1000;font-size:15px;';
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
    wrap.style.cssText = 'position:fixed;z-index:2147483647;inset:0;background:rgba(0,0,0,.78);display:flex;align-items:center;justify-content:center;padding:22px;font-family:Arial,Malgun Gothic,sans-serif;box-sizing:border-box;';

    const panel = document.createElement('div');
    panel.style.cssText = 'width:500px;max-width:94vw;background:radial-gradient(circle at top,rgba(214,168,79,.22),transparent 42%),linear-gradient(180deg,#16100a,#050403);border:1px solid rgba(214,168,79,.84);border-radius:24px;padding:22px;box-shadow:0 0 45px rgba(214,168,79,.32);box-sizing:border-box;color:#fff;';

    if (!document.getElementById('soop-recap-date-style')) {
      const st = document.createElement('style');
      st.id = 'soop-recap-date-style';
      st.textContent = `
        #soop-recap-check-input input[type="date"]{color-scheme:dark;}
        #soop-recap-check-input input[type="date"]::-webkit-calendar-picker-indicator{
          opacity:1!important;
          cursor:pointer!important;
          width:28px!important;
          height:24px!important;
          padding:4px!important;
          border-radius:8px!important;
          background-color:transparent!important;
          filter:invert(77%) sepia(56%) saturate(553%) hue-rotate(359deg) brightness(105%) contrast(94%)!important;
        }
        #soop-recap-check-input input[type="date"]::-webkit-calendar-picker-indicator:hover{
          background-color:rgba(214,168,79,.32)!important;
        }
      `;
      document.head.appendChild(st);
    }

    panel.innerHTML = `
      <div style="text-align:center;margin-bottom:16px;">
        <div style="display:inline-block;padding:6px 12px;border-radius:999px;background:rgba(214,168,79,.15);border:1px solid rgba(255,231,166,.34);color:#f8e7b0;font-size:11px;font-weight:1000;">SOOP WATCH CHECK</div>
        <div style="margin-top:10px;font-size:25px;font-weight:1000;letter-spacing:-.6px;">🏆 리캡 셀프 인증서</div>
        <div style="margin-top:7px;font-size:12px;font-weight:800;color:#d6c29a;line-height:1.55;">
          SOOP 로그인 상태에서 기간을 선택하면<br>
          A-염보성!! / [BJ]케이 기록만 자동 판독합니다.
        </div>
      </div>

      <div style="padding:14px;border-radius:16px;background:rgba(18,13,8,.78);border:1px solid rgba(214,168,79,.28);">
        <label style="display:block;font-size:12px;font-weight:1000;color:#f8e7b0;margin-bottom:6px;">와이고수 닉네임</label>
        <input id="rcNick" type="text" placeholder="와이고수 닉네임 입력" style="width:100%;box-sizing:border-box;border:1px solid #76501e;border-radius:12px;background:#070503;color:#fff;padding:12px;font-size:15px;font-weight:900;outline:none;">

        <div style="display:flex;gap:10px;margin-top:10px;">
          <div style="flex:1;">
            <label style="display:block;font-size:12px;font-weight:1000;color:#f8e7b0;margin-bottom:6px;">시작일</label>
            <div style="position:relative;">
              <input id="rcStart" type="date" value="${defaultStart}" style="width:100%;box-sizing:border-box;border:1px solid #76501e;border-radius:12px;background:#070503;color:#fff;padding:12px 48px 12px 12px;font-size:15px;font-weight:1000;outline:none;">
              <button id="rcStartPick" type="button" title="시작일 선택" style="position:absolute;right:7px;top:50%;transform:translateY(-50%);width:36px;height:32px;border:1px solid rgba(214,168,79,.50);border-radius:10px;background:rgba(214,168,79,.18);color:#f8e7b0;font-size:18px;font-weight:1000;cursor:pointer;line-height:1;">📅</button>
            </div>
          </div>
          <div style="flex:1;">
            <label style="display:block;font-size:12px;font-weight:1000;color:#f8e7b0;margin-bottom:6px;">종료일</label>
            <div style="position:relative;">
              <input id="rcEnd" type="date" value="${defaultEnd}" style="width:100%;box-sizing:border-box;border:1px solid #76501e;border-radius:12px;background:#070503;color:#fff;padding:12px 48px 12px 12px;font-size:15px;font-weight:1000;outline:none;">
              <button id="rcEndPick" type="button" title="종료일 선택" style="position:absolute;right:7px;top:50%;transform:translateY(-50%);width:36px;height:32px;border:1px solid rgba(214,168,79,.50);border-radius:10px;background:rgba(214,168,79,.18);color:#f8e7b0;font-size:18px;font-weight:1000;cursor:pointer;line-height:1;">📅</button>
            </div>
          </div>
        </div>
      </div>

      <div id="rcMsg" style="margin-top:12px;min-height:20px;font-size:12px;font-weight:900;color:#fcd34d;text-align:center;"></div>

      <div style="margin-top:16px;display:flex;gap:9px;justify-content:center;flex-wrap:wrap;">
        <button id="rcRun" style="cursor:pointer;border:0;border-radius:999px;padding:13px 22px;background:linear-gradient(135deg,#d6a84f,#7a4a15);color:#171009;font-weight:1000;font-size:15px;box-shadow:0 8px 20px rgba(214,168,79,.24);">조회 후 이미지 생성</button>
        <button id="rcClose" style="cursor:pointer;border:1px solid #64748b;border-radius:999px;padding:13px 22px;background:#171009;color:#f8e7b0;font-weight:1000;font-size:15px;">닫기</button>
      </div>

      <div style="margin-top:12px;text-align:center;color:#a9915d;font-size:11px;font-weight:800;line-height:1.45;">
        ※ 조회 기간은 최대 31일까지만 가능합니다.<br>
        ※ SOOP ID는 이미지에 표시하지 않습니다.
      </div>
    `;

    wrap.appendChild(panel);
    document.body.appendChild(wrap);

    const msg = panel.querySelector('#rcMsg');
    const startInput = panel.querySelector('#rcStart');
    const endInput = panel.querySelector('#rcEnd');

    function openDatePicker(el) {
      if (!el) return;
      el.focus();
      if (el.showPicker) {
        try { el.showPicker(); return; } catch (e) {}
      }
      try { el.click(); } catch (e) {}
    }

    [startInput, endInput].forEach(function (el) {
      el.addEventListener('click', function () {
        openDatePicker(this);
      });
    });

    const startPick = panel.querySelector('#rcStartPick');
    const endPick = panel.querySelector('#rcEndPick');
    if (startPick) startPick.onclick = function () { openDatePicker(startInput); };
    if (endPick) endPick.onclick = function () { openDatePicker(endInput); };

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
      if (diffDays > 31) return alert('조회 기간은 최대 31일까지만 가능합니다.');

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