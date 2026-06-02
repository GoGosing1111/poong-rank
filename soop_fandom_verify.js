(function () {
  'use strict';

  const TARGETS = [
    { key: 'yeomboseong', label: 'A-염보성!!', patterns: ['A-염보성!!', 'A-염보성', '염보성', '염보'] },
    { key: 'bjkei', label: '[BJ]케이', patterns: ['[BJ]케이', 'BJ케이', '비제이케이', '비제이 케이', '케이'] }
  ];

  const now = new Date();
  const pad = n => String(n).padStart(2, '0');
  const issuedAt = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())} ${pad(now.getHours())}:${pad(now.getMinutes())}`;

  function normalize(s) {
    return String(s || '')
      .replace(/\s+/g, '')
      .replace(/[\u200B-\u200D\uFEFF]/g, '')
      .toLowerCase();
  }

  function getRows() {
    const rows = [];
    document.querySelectorAll('tr, li, .item, [class*=item], [class*=row], [class*=list]').forEach((el) => {
      const text = (el.innerText || el.textContent || '').trim();
      if (!text || text.length < 2) return;
      rows.push({ text, norm: normalize(text) });
    });
    return rows;
  }

  function findTarget(rows, target) {
    const pats = target.patterns.map(normalize).filter(Boolean);
    const hitRows = [];
    for (const row of rows) {
      if (pats.some(p => row.norm.includes(p))) {
        hitRows.push(row.text.replace(/\n+/g, ' / ').slice(0, 120));
      }
    }
    const bodyText = document.body ? document.body.innerText || document.body.textContent || '' : '';
    const bodyNorm = normalize(bodyText);
    const bodyHit = pats.some(p => bodyNorm.includes(p));
    return {
      found: hitRows.length > 0 || bodyHit,
      rows: Array.from(new Set(hitRows)).slice(0, 5)
    };
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

  function drawText(ctx, text, x, y, maxWidth, lineHeight) {
    const words = String(text).split(' ');
    let line = '';
    for (let i = 0; i < words.length; i++) {
      const test = line ? line + ' ' + words[i] : words[i];
      if (ctx.measureText(test).width > maxWidth && i > 0) {
        ctx.fillText(line, x, y);
        line = words[i];
        y += lineHeight;
      } else {
        line = test;
      }
    }
    if (line) ctx.fillText(line, x, y);
    return y + lineHeight;
  }

  function makeCanvas(nick, results) {
    const c = document.createElement('canvas');
    c.width = 1200;
    c.height = 800;
    const ctx = c.getContext('2d');

    const bg = ctx.createLinearGradient(0, 0, 1200, 800);
    bg.addColorStop(0, '#071426');
    bg.addColorStop(0.45, '#05070d');
    bg.addColorStop(1, '#001d36');
    ctx.fillStyle = bg;
    ctx.fillRect(0, 0, 1200, 800);

    ctx.save();
    ctx.globalAlpha = 0.12;
    ctx.fillStyle = '#60a5fa';
    ctx.beginPath(); ctx.arc(200, 80, 230, 0, Math.PI * 2); ctx.fill();
    ctx.beginPath(); ctx.arc(1030, 720, 260, 0, Math.PI * 2); ctx.fill();
    ctx.restore();

    ctx.save();
    ctx.globalAlpha = 0.075;
    ctx.translate(70, 720);
    ctx.rotate(-0.35);
    ctx.font = 'bold 42px Malgun Gothic, Arial';
    ctx.fillStyle = '#ffffff';
    const wm = `YGOSU ${nick}  ·  RECAP CHECK  ·  ${issuedAt}`;
    for (let y = -900; y < 500; y += 115) {
      for (let x = -300; x < 1300; x += 620) ctx.fillText(wm, x, y);
    }
    ctx.restore();

    drawRoundRect(ctx, 70, 55, 1060, 690, 34);
    ctx.fillStyle = 'rgba(3, 8, 18, 0.78)';
    ctx.fill();
    ctx.lineWidth = 3;
    ctx.strokeStyle = 'rgba(96, 165, 250, .75)';
    ctx.stroke();

    ctx.textAlign = 'center';
    ctx.fillStyle = '#ffffff';
    ctx.font = 'bold 54px Malgun Gothic, Arial';
    ctx.fillText('📋 리캡 부검 제출용', 600, 145);

    ctx.font = 'bold 26px Malgun Gothic, Arial';
    ctx.fillStyle = '#bfdbfe';
    ctx.fillText(`시청기록 확인 결과 · ${issuedAt}`, 600, 192);

    ctx.textAlign = 'left';
    drawRoundRect(ctx, 115, 225, 970, 86, 22);
    ctx.fillStyle = 'rgba(15, 23, 42, .92)';
    ctx.fill();
    ctx.strokeStyle = 'rgba(147, 197, 253, .35)';
    ctx.stroke();
    ctx.fillStyle = '#93c5fd';
    ctx.font = 'bold 24px Malgun Gothic, Arial';
    ctx.fillText('와이고수 닉네임', 155, 260);
    ctx.fillStyle = '#ffffff';
    ctx.font = 'bold 38px Malgun Gothic, Arial';
    ctx.fillText(nick, 155, 300);

    const anyFound = results.some(r => r.found);
    drawRoundRect(ctx, 115, 345, 970, 170, 28);
    ctx.fillStyle = anyFound ? 'rgba(127, 29, 29, .78)' : 'rgba(6, 78, 59, .78)';
    ctx.fill();
    ctx.strokeStyle = anyFound ? 'rgba(248, 113, 113, .75)' : 'rgba(52, 211, 153, .75)';
    ctx.lineWidth = 3;
    ctx.stroke();

    ctx.textAlign = 'center';
    ctx.fillStyle = '#ffffff';
    ctx.font = 'bold 58px Malgun Gothic, Arial';
    ctx.fillText(anyFound ? '부검 대상 기록 발견' : '부검 대상 기록 없음', 600, 425);
    ctx.font = 'bold 25px Malgun Gothic, Arial';
    ctx.fillStyle = anyFound ? '#fecaca' : '#bbf7d0';
    ctx.fillText(anyFound ? 'A-염보성!! 또는 [BJ]케이 기록 감지' : 'A-염보성!! / [BJ]케이 기록 미감지', 600, 470);

    ctx.textAlign = 'left';
    let y = 565;
    ctx.font = 'bold 28px Malgun Gothic, Arial';
    results.forEach((r) => {
      ctx.fillStyle = r.found ? '#fecaca' : '#bbf7d0';
      ctx.fillText(`${r.found ? '✅' : '❌'} ${r.label}: ${r.found ? '기록 있음' : '기록 없음'}`, 145, y);
      y += 44;
    });

    ctx.fillStyle = '#cbd5e1';
    ctx.font = 'bold 20px Malgun Gothic, Arial';
    ctx.fillText('※ 본인 SOOP 로그인 상태의 브라우저에서 생성된 리캡 부검 이미지입니다.', 145, 690);
    ctx.fillText('※ 캡처/해명자료용이며, 타인의 기록은 조회하지 않습니다.', 145, 720);

    return c;
  }

  function showOverlay(nick, results) {
    const old = document.getElementById('soop-fandom-verify-overlay');
    if (old) old.remove();

    const canvas = makeCanvas(nick, results);
    canvas.style.maxWidth = '100%';
    canvas.style.height = 'auto';
    canvas.style.borderRadius = '16px';
    canvas.style.boxShadow = '0 12px 35px rgba(0,0,0,.35)';

    const wrap = document.createElement('div');
    wrap.id = 'soop-fandom-verify-overlay';
    wrap.style.cssText = 'position:fixed;z-index:2147483647;inset:0;background:rgba(0,0,0,.72);display:flex;align-items:center;justify-content:center;padding:24px;font-family:Arial,Malgun Gothic,sans-serif;box-sizing:border-box;';

    const panel = document.createElement('div');
    panel.style.cssText = 'width:980px;max-width:96vw;max-height:96vh;overflow:auto;background:#071426;border:1px solid #60a5fa;border-radius:22px;padding:18px;box-shadow:0 0 45px rgba(96,165,250,.45);box-sizing:border-box;text-align:center;color:#fff;';

    const title = document.createElement('div');
    title.textContent = '📋 리캡 부검 제출용 이미지 생성 완료';
    title.style.cssText = 'font-size:22px;font-weight:1000;margin:4px 0 14px;color:#fff;';

    const btns = document.createElement('div');
    btns.style.cssText = 'margin-top:14px;display:flex;gap:10px;justify-content:center;flex-wrap:wrap;';

    const save = document.createElement('button');
    save.textContent = 'PNG 저장';
    save.style.cssText = 'cursor:pointer;border:0;border-radius:999px;padding:12px 22px;background:#2563eb;color:#fff;font-weight:1000;font-size:15px;';
    save.onclick = function () {
      const a = document.createElement('a');
      const safeNick = nick.replace(/[\\/:*?"<>|\s]+/g, '_').slice(0, 40) || 'ygosu';
      a.download = `리캡부검제출용_${safeNick}_${now.getFullYear()}${pad(now.getMonth()+1)}${pad(now.getDate())}.png`;
      a.href = canvas.toDataURL('image/png');
      a.click();
    };

    const close = document.createElement('button');
    close.textContent = '닫기';
    close.style.cssText = 'cursor:pointer;border:1px solid #64748b;border-radius:999px;padding:12px 22px;background:#111827;color:#fff;font-weight:1000;font-size:15px;';
    close.onclick = function () { wrap.remove(); };

    btns.appendChild(save);
    btns.appendChild(close);
    panel.appendChild(title);
    panel.appendChild(canvas);
    panel.appendChild(btns);
    wrap.appendChild(panel);
    document.body.appendChild(wrap);
  }

  try {
    const nick = (prompt('와이고수 닉네임을 입력하세요.\n인증 이미지에 워터마크로 표시됩니다.', '') || '').trim();
    if (!nick) return alert('와이고수 닉네임이 없어 인증을 취소했습니다.');

    const rows = getRows();
    const results = TARGETS.map(t => Object.assign({ label: t.label }, findTarget(rows, t)));
    showOverlay(nick, results);
  } catch (err) {
    alert('인증 이미지 생성 실패: ' + (err && err.message ? err.message : err));
    console.error('[SOOP Fandom Verify]', err);
  }
})();
