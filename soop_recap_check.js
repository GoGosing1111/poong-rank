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

    const chulgu = results.find(r => r.key === 'chulgu100');
    const chulguSeconds = chulgu ? Number(chulgu.seconds) || 0 : 0;
    const chulguHours = Math.floor(chulguSeconds / 3600);
    const yeom = results.find(r => r.key === 'yeomboseong');
    const kei = results.find(r => r.key === 'bjkei');
    const h = (r) => `${Math.floor((Number(r && r.seconds) || 0) / 3600)}시간`;

    function centerText(text, x, y, font, fill) {
      ctx.save();
      ctx.textAlign = 'center';
      ctx.textBaseline = 'alphabetic';
      ctx.font = font;
      ctx.fillStyle = fill;
      ctx.fillText(text, x, y);
      ctx.restore();
    }

    function leftText(text, x, y, font, fill) {
      ctx.save();
      ctx.textAlign = 'left';
      ctx.textBaseline = 'alphabetic';
      ctx.font = font;
      ctx.fillStyle = fill;
      ctx.fillText(text, x, y);
      ctx.restore();
    }

    function line(x1, y1, x2, y2, color, width) {
      ctx.save();
      ctx.strokeStyle = color;
      ctx.lineWidth = width || 1;
      ctx.beginPath();
      ctx.moveTo(x1, y1);
      ctx.lineTo(x2, y2);
      ctx.stroke();
      ctx.restore();
    }

    function ornament(cx, cy, scale) {
      ctx.save();
      ctx.translate(cx, cy);
      ctx.scale(scale, scale);
      ctx.strokeStyle = 'rgba(188,143,67,.78)';
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(-90, 0); ctx.lineTo(-20, 0);
      ctx.moveTo(20, 0); ctx.lineTo(90, 0);
      ctx.stroke();
      ctx.fillStyle = 'rgba(188,143,67,.86)';
      ctx.beginPath();
      ctx.moveTo(0, -7); ctx.lineTo(9, 0); ctx.lineTo(0, 7); ctx.lineTo(-9, 0); ctx.closePath();
      ctx.fill();
      ctx.restore();
    }

    function drawCorner(x, y, sx, sy) {
      ctx.save();
      ctx.translate(x, y);
      ctx.scale(sx, sy);
      ctx.strokeStyle = 'rgba(188,143,67,.72)';
      ctx.lineWidth = 2.2;
      ctx.beginPath();
      ctx.moveTo(0, 62); ctx.quadraticCurveTo(28, 52, 34, 24); ctx.quadraticCurveTo(48, 42, 70, 34);
      ctx.moveTo(8, 92); ctx.quadraticCurveTo(52, 62, 84, 20);
      ctx.moveTo(0, 0); ctx.lineTo(0, 118);
      ctx.moveTo(0, 0); ctx.lineTo(118, 0);
      ctx.stroke();
      ctx.restore();
    }

    function drawStamp(x, y) {
      ctx.save();
      ctx.translate(x, y);
      ctx.rotate(-0.045);
      ctx.globalAlpha = 0.92;
      ctx.strokeStyle = 'rgba(180,26,22,.86)';
      ctx.fillStyle = 'rgba(180,26,22,.09)';
      ctx.lineWidth = 7;
      drawRoundRect(ctx, -105, -75, 210, 150, 16);
      ctx.fill(); ctx.stroke();
      ctx.lineWidth = 3;
      ctx.strokeStyle = 'rgba(180,26,22,.76)';
      drawRoundRect(ctx, -90, -60, 180, 120, 10);
      ctx.stroke();

      // 거친 도장 질감: 지워진 부분을 규칙적으로 제거
      ctx.save();
      ctx.globalCompositeOperation = 'destination-out';
      ctx.globalAlpha = 0.20;
      ctx.fillStyle = '#000';
      for (let i = 0; i < 46; i++) {
        const xx = -90 + ((i * 37) % 180);
        const yy = -62 + ((i * 53) % 124);
        ctx.beginPath();
        ctx.ellipse(xx, yy, 2 + (i % 5), 1.2 + (i % 4), (i % 7) * .4, 0, Math.PI * 2);
        ctx.fill();
      }
      ctx.restore();

      ctx.textAlign = 'center';
      ctx.fillStyle = 'rgba(165,22,19,.92)';
      ctx.font = 'bold 36px Georgia, serif';
      ctx.fillText('SOOP', 0, -26);
      ctx.fillText('RECAP', 0, 14);
      ctx.font = 'bold 34px Malgun Gothic, Arial';
      ctx.fillText('인증완료', 0, 55);
      ctx.restore();
    }

    // 종이 배경
    const paper = ctx.createLinearGradient(0, 0, 1200, 840);
    paper.addColorStop(0, '#fffaf0');
    paper.addColorStop(0.5, '#f6eddb');
    paper.addColorStop(1, '#fff8eb');
    ctx.fillStyle = paper;
    ctx.fillRect(0, 0, 1200, 840);

    // 종이 질감
    ctx.save();
    ctx.globalAlpha = 0.10;
    for (let i = 0; i < 900; i++) {
      const x = (i * 47) % 1200;
      const y = (i * 83) % 840;
      const v = 190 + (i % 55);
      ctx.fillStyle = `rgb(${v},${v-18},${v-45})`;
      ctx.fillRect(x, y, 1.2, 1.2);
    }
    ctx.restore();

    // 큰 워터마크 복구
    ctx.save();
    ctx.globalAlpha = 0.070;
    ctx.translate(595, 430);
    ctx.rotate(-0.33);
    ctx.textAlign = 'center';
    ctx.font = 'bold 142px Georgia, serif';
    ctx.fillStyle = '#6f6048';
    ctx.fillText('SOOP RECAP', 0, 0);
    ctx.font = 'bold 96px Malgun Gothic, Arial';
    ctx.fillText('셀프 인증', 0, 120);
    ctx.restore();

    // 프레임
    ctx.strokeStyle = '#b98d43';
    ctx.lineWidth = 4;
    ctx.strokeRect(36, 36, 1128, 768);
    ctx.lineWidth = 1.3;
    ctx.strokeStyle = 'rgba(185,141,67,.70)';
    ctx.strokeRect(52, 52, 1096, 736);
    ctx.lineWidth = 1.1;
    ctx.strokeStyle = 'rgba(185,141,67,.42)';
    ctx.strokeRect(70, 70, 1060, 700);

    drawCorner(56, 56, 1, 1);
    drawCorner(1144, 56, -1, 1);
    drawCorner(56, 784, 1, -1);
    drawCorner(1144, 784, -1, -1);

    // 제목부: 상단 영어 전부 제거
    centerText('리캡 셀프 인증서', 600, 176, 'bold 58px Malgun Gothic, Arial', '#2d2418');
    ornament(600, 210, 1.08);

    drawRoundRect(ctx, 440, 234, 320, 42, 12);
    ctx.fillStyle = 'rgba(255,255,255,.42)';
    ctx.fill();
    ctx.strokeStyle = 'rgba(185,141,67,.50)';
    ctx.lineWidth = 1.3;
    ctx.stroke();
    centerText(`${startDate}  ~  ${endDate}`, 600, 262, '20px Georgia, Malgun Gothic, serif', '#2d2418');

    centerText('본 인증서는 아래 와고닉의 SOOP 시청기록 기준으로 생성되었습니다.', 600, 330, '22px Malgun Gothic, Arial', '#3a2f21');
    centerText('인증 대상자', 600, 378, 'bold 20px Malgun Gothic, Arial', '#b98d43');
    centerText(nick, 600, 438, 'bold 54px Malgun Gothic, Arial', '#16120d');

    ornament(600, 490, 1.34);

    // 시청기록 표: 총 누적 시청시간 계열 제거, 3칸만 표시
    drawRoundRect(ctx, 220, 520, 760, 138, 10);
    ctx.fillStyle = 'rgba(255,255,255,.22)';
    ctx.fill();
    ctx.strokeStyle = 'rgba(185,141,67,.70)';
    ctx.lineWidth = 1.8;
    ctx.stroke();
    line(473, 535, 473, 643, 'rgba(185,141,67,.45)', 1.5);
    line(727, 535, 727, 643, 'rgba(185,141,67,.45)', 1.5);

    const cols = [
      ['철구 시청 누적', `${chulguHours}시간`],
      ['염보성 시청 누적', h(yeom)],
      ['케이 시청 누적', h(kei)]
    ];
    [347, 600, 853].forEach((x, i) => {
      centerText(cols[i][0], x, 570, 'bold 20px Malgun Gothic, Arial', '#3a2f21');
      centerText(cols[i][1], x, 622, 'bold 38px Malgun Gothic, Arial', '#15110c');
    });

    // 발급 정보
    leftText('발급일', 118, 715, 'bold 17px Malgun Gothic, Arial', '#3a2f21');
    leftText(issuedDate, 205, 715, '18px Georgia, Malgun Gothic, serif', '#2d2418');
    line(118, 730, 360, 730, 'rgba(185,141,67,.50)', 1);
    leftText('인증번호', 118, 755, 'bold 17px Malgun Gothic, Arial', '#3a2f21');
    leftText(certNo, 205, 755, '18px Georgia, Malgun Gothic, serif', '#2d2418');
    line(118, 770, 360, 770, 'rgba(185,141,67,.50)', 1);

    // 우측 하단 붉은 직인
    drawStamp(1000, 696);

    // 하단 안내문: 프레임 안쪽에서 여유 있게
    ctx.textAlign = 'center';
    ctx.fillStyle = '#4b4031';
    ctx.font = '13px Malgun Gothic, Arial';
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
          opacity:0!important;
          display:none!important;
          pointer-events:none!important;
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