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

    function roundRect(x, y, w, h, r, fill, stroke, lw) {
      drawRoundRect(ctx, x, y, w, h, r);
      if (fill) {
        ctx.fillStyle = fill;
        ctx.fill();
      }
      if (stroke) {
        ctx.lineWidth = lw || 1;
        ctx.strokeStyle = stroke;
        ctx.stroke();
      }
    }

    function centerText(text, x, y, font, color, shadow) {
      ctx.save();
      ctx.textAlign = 'center';
      ctx.textBaseline = 'alphabetic';
      ctx.font = font;
      ctx.fillStyle = color;
      if (shadow) {
        ctx.shadowColor = 'rgba(0,0,0,.72)';
        ctx.shadowBlur = 8;
        ctx.shadowOffsetY = 3;
      }
      ctx.fillText(text, x, y);
      ctx.restore();
    }

    function drawGoldRule(y) {
      ctx.save();
      const g = ctx.createLinearGradient(210, y, 990, y);
      g.addColorStop(0, 'rgba(214,168,79,0)');
      g.addColorStop(.18, 'rgba(214,168,79,.75)');
      g.addColorStop(.50, 'rgba(255,232,170,.95)');
      g.addColorStop(.82, 'rgba(214,168,79,.75)');
      g.addColorStop(1, 'rgba(214,168,79,0)');
      ctx.strokeStyle = g;
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(210, y); ctx.lineTo(990, y);
      ctx.stroke();
      ctx.fillStyle = '#d6a84f';
      ctx.beginPath(); ctx.arc(600, y, 5, 0, Math.PI * 2); ctx.fill();
      ctx.restore();
    }

    function drawStamp(cx, cy, r) {
      ctx.save();
      ctx.translate(cx, cy);
      ctx.rotate(-0.18);
      ctx.globalAlpha = 0.92;

      // 붉은 직인 번짐
      const bleed = ctx.createRadialGradient(0, 0, 8, 0, 0, r + 20);
      bleed.addColorStop(0, 'rgba(210, 31, 31, .10)');
      bleed.addColorStop(.58, 'rgba(210, 31, 31, .08)');
      bleed.addColorStop(1, 'rgba(210, 31, 31, 0)');
      ctx.fillStyle = bleed;
      ctx.beginPath(); ctx.arc(0, 0, r + 22, 0, Math.PI * 2); ctx.fill();

      // 찐 직인 라인
      ctx.strokeStyle = 'rgba(214, 36, 36, .78)';
      ctx.lineWidth = 7;
      ctx.beginPath(); ctx.arc(0, 0, r, 0, Math.PI * 2); ctx.stroke();
      ctx.strokeStyle = 'rgba(255, 91, 91, .66)';
      ctx.lineWidth = 2.8;
      ctx.beginPath(); ctx.arc(0, 0, r - 13, 0, Math.PI * 2); ctx.stroke();
      ctx.strokeStyle = 'rgba(214, 36, 36, .45)';
      ctx.lineWidth = 1.6;
      ctx.beginPath(); ctx.arc(0, 0, r - 26, 0, Math.PI * 2); ctx.stroke();

      // 도장 내부 십자 분할선
      ctx.strokeStyle = 'rgba(214, 36, 36, .42)';
      ctx.lineWidth = 1.8;
      ctx.beginPath(); ctx.moveTo(-r + 18, 0); ctx.lineTo(r - 18, 0); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(0, -r + 18); ctx.lineTo(0, r - 18); ctx.stroke();

      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillStyle = 'rgba(223, 48, 48, .88)';
      ctx.font = '900 34px Malgun Gothic, Arial';
      ctx.fillText('인증', 0, -17);
      ctx.fillText('완료', 0, 27);
      ctx.font = '900 15px Malgun Gothic, Arial';
      ctx.fillText('SOOP 리캡', 0, 58);

      // 낡은 직인 질감
      ctx.globalCompositeOperation = 'destination-out';
      ctx.globalAlpha = 0.14;
      for (let i = 0; i < 50; i++) {
        const a = (i * 2.399963) % (Math.PI * 2);
        const rr = ((i * 37) % 100) / 100 * r * .88;
        ctx.beginPath();
        ctx.arc(Math.cos(a) * rr, Math.sin(a) * rr, 1.4 + (i % 4), 0, Math.PI * 2);
        ctx.fill();
      }
      ctx.restore();
    }

    // 배경
    const bg = ctx.createLinearGradient(0, 0, 1200, 840);
    bg.addColorStop(0, '#050302');
    bg.addColorStop(.48, '#151007');
    bg.addColorStop(1, '#030302');
    ctx.fillStyle = bg;
    ctx.fillRect(0, 0, 1200, 840);

    // 은은한 금빛 조명
    ctx.save();
    ctx.globalAlpha = .20;
    let glow = ctx.createRadialGradient(610, 80, 20, 610, 80, 520);
    glow.addColorStop(0, '#e7bd61');
    glow.addColorStop(1, 'rgba(231,189,97,0)');
    ctx.fillStyle = glow;
    ctx.fillRect(0, 0, 1200, 840);
    ctx.restore();

    // 프레임 안쪽 배경
    roundRect(58, 52, 1084, 736, 24, 'rgba(7, 5, 3, .95)', '#d6a84f', 5);
    roundRect(84, 78, 1032, 684, 16, null, 'rgba(255,231,166,.60)', 2);
    roundRect(110, 104, 980, 632, 12, null, 'rgba(174,122,42,.46)', 1.3);

    // 배경 워터마크 복구: 내용 뒤에 크게, 너무 튀지 않게
    ctx.save();
    ctx.translate(600, 462);
    ctx.rotate(-0.20);
    ctx.globalAlpha = 0.055;
    ctx.textAlign = 'center';
    ctx.fillStyle = '#f6d276';
    ctx.font = '900 138px Georgia, Malgun Gothic, serif';
    ctx.fillText('SOOP RECAP', 0, 0);
    ctx.font = '900 66px Malgun Gothic, Arial';
    ctx.fillText('셀프 인증', 0, 82);
    ctx.restore();

    // 상단 장식
    drawGoldRule(142);
    ctx.save();
    ctx.fillStyle = '#d6a84f';
    ctx.beginPath();
    ctx.moveTo(600, 111); ctx.lineTo(622, 132); ctx.lineTo(600, 153); ctx.lineTo(578, 132); ctx.closePath();
    ctx.fill();
    ctx.restore();

    // 제목: 한글만 사용
    centerText('SOOP 리캡 셀프 인증서', 600, 214, '900 58px Malgun Gothic, Arial', '#f8e7b0', true);

    // 기간
    roundRect(380, 246, 440, 46, 23, 'rgba(214,168,79,.13)', 'rgba(255,231,166,.34)', 1.5);
    centerText(`${startDate}  ~  ${endDate}`, 600, 276, '900 21px Malgun Gothic, Arial', '#ffe7a6', false);

    centerText('본 인증서는 SOOP 시청기록 기준으로 생성되었습니다.', 600, 330, '900 22px Malgun Gothic, Arial', '#d9c595', false);

    centerText('인증 대상자', 600, 380, '900 19px Malgun Gothic, Arial', '#d6a84f', false);
    centerText(nick, 600, 442, '900 56px Malgun Gothic, Arial', '#ffffff', true);

    const chulgu = results.find(r => r.key === 'chulgu100');
    const chulguSeconds = chulgu ? Number(chulgu.seconds) || 0 : 0;
    const chulguHours = Math.floor(chulguSeconds / 3600);
    const yeom = results.find(r => r.key === 'yeomboseong');
    const kei = results.find(r => r.key === 'bjkei');
    const h = (r) => `${Math.floor((Number(r && r.seconds) || 0) / 3600)}시간`;

    // 메인: 총 누적 제거, 철구 시청만 강조
    roundRect(250, 478, 700, 102, 14, 'rgba(0,0,0,.25)', 'rgba(214,168,79,.70)', 1.8);
    centerText('철구 시청 누적', 600, 518, '900 26px Malgun Gothic, Arial', '#f5d98a', false);
    centerText(`${chulguHours}시간`, 600, 568, '900 62px Georgia, Malgun Gothic, serif', '#f4d183', true);

    // 세부 항목: 중복 최소화
    roundRect(190, 613, 820, 74, 12, 'rgba(0,0,0,.18)', 'rgba(214,168,79,.48)', 1.5);
    ctx.save();
    ctx.strokeStyle = 'rgba(214,168,79,.33)';
    ctx.lineWidth = 1.2;
    ctx.beginPath();
    ctx.moveTo(463, 626); ctx.lineTo(463, 674);
    ctx.moveTo(737, 626); ctx.lineTo(737, 674);
    ctx.stroke();
    const cols = [
      ['철구', `${chulguHours}시간`],
      ['염보성', h(yeom)],
      ['케이', h(kei)]
    ];
    [326, 600, 874].forEach((x, i) => {
      centerText(cols[i][0], x, 642, '900 17px Malgun Gothic, Arial', '#d6a84f', false);
      centerText(cols[i][1], x, 673, '900 29px Malgun Gothic, Arial', i === 0 ? '#f4d183' : '#ffffff', false);
    });
    ctx.restore();

    // 발급 정보: 프레임 안쪽에 여유 있게
    ctx.save();
    ctx.textAlign = 'left';
    ctx.fillStyle = '#d9c595';
    ctx.font = '900 15px Malgun Gothic, Arial';
    ctx.fillText('발급일', 174, 720);
    ctx.fillStyle = '#f2d58a';
    ctx.fillText(issuedDate, 235, 720);
    ctx.fillStyle = '#d9c595';
    ctx.fillText('인증번호', 174, 745);
    ctx.fillStyle = '#f2d58a';
    ctx.fillText(certNo, 250, 745);
    ctx.restore();

    // 우측 하단 붉은 직인
    drawStamp(914, 716, 62);

    // 최하단 안내문: 프레임에 안 가리도록 완전히 안쪽으로 올림
    ctx.save();
    ctx.textAlign = 'center';
    ctx.fillStyle = 'rgba(184,154,97,.92)';
    ctx.font = '900 12px Malgun Gothic, Arial';
    ctx.fillText(`조회갱신 ${updatedAt || '-'} · 생성시각 ${issuedAt}`, 600, 772);
    ctx.fillText('본인 로그인 상태에서만 조회되며 타인의 기록은 조회하지 않습니다.', 600, 790);
    ctx.restore();

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