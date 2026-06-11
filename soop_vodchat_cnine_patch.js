/*
CNINE VOD UI v4
- 티큐 원본 UI를 꾸미지 않고 별도 CNINE 패널 생성
- 원본 패널은 감지되면 숨김
- 데이터는 fetch/XHR 후킹 저장소 + DOM 텍스트 fallback으로 렌더링
*/
(function(){
  'use strict';

  if(window.__C9_VODCHAT_UI_V4__) return;
  window.__C9_VODCHAT_UI_V4__ = true;

  var STORE = window.__C9_VODCHAT_STORE__ || {responses:[], jsons:[], texts:[]};
  var state = {
    tab:'chat',
    search:'',
    rows:[],
    ranks:[],
    stats:{duration:'-', chats:'-', users:'-', status:'수집중'}
  };

  function css(){
    if(document.getElementById('c9-vod-ui-v4-style')) return;
    var st=document.createElement('style');
    st.id='c9-vod-ui-v4-style';
    st.textContent = `
#c9VodPanelV4{position:fixed;right:18px;top:76px;width:min(760px,calc(100vw - 36px));height:min(760px,calc(100vh - 104px));z-index:2147483647;background:linear-gradient(180deg,#071a31 0%,#071426 48%,#030711 100%);border:1px solid rgba(78,168,255,.74);border-radius:22px;box-shadow:0 26px 70px rgba(0,0,0,.72),0 0 32px rgba(47,155,255,.38);font-family:Arial,'Malgun Gothic',sans-serif;color:#fff;overflow:hidden;display:flex;flex-direction:column}
#c9VodPanelV4 *{box-sizing:border-box}
.c9v-head{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:14px 16px;background:linear-gradient(135deg,#0b2849,#112a63 55%,#07101e);border-bottom:1px solid rgba(126,200,255,.40)}
.c9v-title{display:flex;flex-direction:column;gap:3px;min-width:0}
.c9v-title b{font-size:19px;font-weight:1000;color:#fff;text-shadow:0 0 10px rgba(78,168,255,.55);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.c9v-title span{font-size:11px;font-weight:900;color:#9fd3ff}
.c9v-actions{display:flex;gap:7px;align-items:center}
.c9v-btn{height:32px;padding:0 11px;border-radius:999px;border:1px solid rgba(126,200,255,.45);background:rgba(2,12,24,.45);color:#dff2ff;font-size:12px;font-weight:1000;cursor:pointer}
.c9v-btn:hover{background:rgba(78,168,255,.20)}
.c9v-close{background:linear-gradient(135deg,#2563eb,#0ea5e9);color:#fff}
.c9v-stats{display:grid;grid-template-columns:repeat(4,1fr);gap:9px;padding:12px 14px;background:rgba(0,0,0,.18);border-bottom:1px solid rgba(126,200,255,.14)}
.c9v-stat{padding:11px 10px;border-radius:16px;background:linear-gradient(135deg,rgba(78,168,255,.16),rgba(0,0,0,.22));border:1px solid rgba(126,200,255,.20);text-align:center}
.c9v-stat small{display:block;color:#a8c7e5;font-size:11px;font-weight:900}
.c9v-stat b{display:block;margin-top:5px;color:#fff;font-size:18px;font-weight:1000;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.c9v-tabs{display:flex;gap:8px;padding:10px 14px;background:#06101f;border-bottom:1px solid rgba(126,200,255,.16)}
.c9v-tab{flex:1;height:36px;border:1px solid rgba(126,200,255,.22);border-radius:13px;background:rgba(255,255,255,.04);color:#cfeaff;font-weight:1000;cursor:pointer}
.c9v-tab.on{background:linear-gradient(135deg,#1d6dff,#0ea5e9);border-color:rgba(255,255,255,.24);color:#fff;box-shadow:0 0 16px rgba(47,155,255,.32)}
.c9v-body{display:grid;grid-template-columns:260px 1fr;gap:12px;padding:12px 14px;min-height:0;flex:1;background:radial-gradient(circle at top left,rgba(78,168,255,.09),transparent 34%)}
.c9v-card{min-height:0;border:1px solid rgba(126,200,255,.18);border-radius:18px;background:rgba(2,8,18,.55);overflow:hidden;display:flex;flex-direction:column}
.c9v-card-head{padding:12px 13px;background:linear-gradient(135deg,rgba(78,168,255,.15),rgba(0,0,0,.22));border-bottom:1px solid rgba(126,200,255,.15);font-size:14px;font-weight:1000;color:#eaf6ff}
.c9v-list{overflow:auto;padding:8px}
.c9v-rank{display:flex;align-items:center;gap:8px;padding:9px 8px;border-radius:12px;margin-bottom:6px;background:rgba(255,255,255,.035);border:1px solid rgba(255,255,255,.04)}
.c9v-rank:nth-child(odd){background:rgba(78,168,255,.055)}
.c9v-medal{width:28px;height:28px;display:flex;align-items:center;justify-content:center;border-radius:50%;background:#081b35;border:1px solid rgba(126,200,255,.28);font-size:12px;font-weight:1000;color:#7ec8ff}
.c9v-name{flex:1;min-width:0;font-size:13px;font-weight:1000;color:#fff;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.c9v-count{padding:4px 8px;border-radius:999px;background:linear-gradient(135deg,#0d6efd,#0ea5e9);font-size:11px;font-weight:1000;color:#fff}
.c9v-search{padding:10px;border-bottom:1px solid rgba(126,200,255,.12)}
.c9v-search input{width:100%;height:34px;border-radius:12px;border:1px solid rgba(126,200,255,.28);background:#06101f;color:#fff;padding:0 12px;font-weight:800;outline:none}
.c9v-log{overflow:auto;padding:8px}
.c9v-msg{padding:8px 9px;margin-bottom:5px;border-radius:10px;background:rgba(255,255,255,.035);border:1px solid rgba(255,255,255,.04);font-size:12px;line-height:1.38;color:#e8f5ff}
.c9v-msg:nth-child(odd){background:rgba(78,168,255,.045)}
.c9v-nick{color:#7ec8ff;font-weight:1000;margin-right:5px}
.c9v-time{color:#9fb7ce;font-size:10px;margin-right:5px}
.c9v-empty{padding:24px 12px;text-align:center;color:#9fb7ce;font-size:13px;font-weight:900;line-height:1.5}
#c9VodPanelV4 ::-webkit-scrollbar{width:9px;height:9px}
#c9VodPanelV4 ::-webkit-scrollbar-thumb{background:linear-gradient(180deg,#4ea8ff,#1d6dff);border-radius:999px}
#c9VodPanelV4 ::-webkit-scrollbar-track{background:#06101f}
@media(max-width:720px){#c9VodPanelV4{left:8px;right:8px;top:60px;width:auto;height:calc(100vh - 76px)}.c9v-body{grid-template-columns:1fr}.c9v-stats{grid-template-columns:repeat(2,1fr)}}
`;
    document.head.appendChild(st);
  }

  function el(tag, cls, html){
    var e=document.createElement(tag);
    if(cls) e.className=cls;
    if(html!==undefined) e.innerHTML=html;
    return e;
  }

  function createPanel(){
    if(document.getElementById('c9VodPanelV4')) return;
    css();
    var panel=el('div', '', '');
    panel.id='c9VodPanelV4';
    panel.innerHTML = `
      <div class="c9v-head">
        <div class="c9v-title"><b>🎬 CNINE 다시보기 분석</b><span>VOD CHAT LOG · 채팅 / 후원 / 도전 / 대결</span></div>
        <div class="c9v-actions"><button class="c9v-btn" id="c9Refresh">새로고침</button><button class="c9v-btn c9v-close" id="c9Close">닫기</button></div>
      </div>
      <div class="c9v-stats">
        <div class="c9v-stat"><small>방송 시간</small><b id="c9StatDuration">-</b></div>
        <div class="c9v-stat"><small>채팅 수</small><b id="c9StatChats">-</b></div>
        <div class="c9v-stat"><small>참여 인원</small><b id="c9StatUsers">-</b></div>
        <div class="c9v-stat"><small>상태</small><b id="c9StatStatus">수집중</b></div>
      </div>
      <div class="c9v-tabs">
        <button class="c9v-tab on" data-tab="chat">💬 전체</button>
        <button class="c9v-tab" data-tab="donation">🎁 후원</button>
        <button class="c9v-tab" data-tab="challenge">🎯 도전</button>
        <button class="c9v-tab" data-tab="battle">⚔ 대결</button>
      </div>
      <div class="c9v-body">
        <div class="c9v-card">
          <div class="c9v-card-head" id="c9RankTitle">채팅 랭킹</div>
          <div class="c9v-list" id="c9Ranks"></div>
        </div>
        <div class="c9v-card">
          <div class="c9v-card-head" id="c9LogTitle">채팅 로그</div>
          <div class="c9v-search"><input id="c9Search" placeholder="닉네임 / 내용 검색"></div>
          <div class="c9v-log" id="c9Logs"></div>
        </div>
      </div>
    `;
    document.body.appendChild(panel);
    panel.querySelector('#c9Close').onclick=function(){ panel.remove(); };
    panel.querySelector('#c9Refresh').onclick=function(){ collectAndRender(); };
    panel.querySelector('#c9Search').oninput=function(){ state.search=this.value.trim(); render(); };
    panel.querySelectorAll('.c9v-tab').forEach(function(b){
      b.onclick=function(){
        panel.querySelectorAll('.c9v-tab').forEach(x=>x.classList.remove('on'));
        b.classList.add('on');
        state.tab=b.dataset.tab;
        render();
      };
    });
  }

  function hideOriginalPanels(){
    // 원본 UI 흔적 숨김. CNINE 패널은 제외.
    document.querySelectorAll('body div').forEach(function(d){
      if(d.id==='c9VodPanelV4' || d.closest('#c9VodPanelV4')) return;
      var t=(d.innerText||'');
      var r=d.getBoundingClientRect ? d.getBoundingClientRect() : {width:0,height:0};
      if(r.width>450 && r.height>280 && t.indexOf('채팅')>-1 && (t.indexOf('후원')>-1 || t.indexOf('도전')>-1 || t.indexOf('대결')>-1)){
        d.style.display='none';
      }
    });
  }

  function flatten(obj, out, depth){
    out = out || [];
    depth = depth || 0;
    if(!obj || depth>7) return out;
    if(Array.isArray(obj)){
      obj.forEach(function(x){ flatten(x,out,depth+1); });
    }else if(typeof obj==='object'){
      out.push(obj);
      Object.keys(obj).forEach(function(k){ flatten(obj[k],out,depth+1); });
    }
    return out;
  }

  function pick(o, keys){
    for(var i=0;i<keys.length;i++){
      if(o && o[keys[i]]!==undefined && o[keys[i]]!==null && String(o[keys[i]]).trim()!=='') return o[keys[i]];
    }
    return '';
  }

  function normalizeType(o, text){
    text = String(text||'');
    var raw = String(pick(o,['type','kind','category','messageType','actionType','log_type','szType','nType'])||'').toLowerCase();
    if(raw.indexOf('gift')>-1 || raw.indexOf('don')>-1 || raw.indexOf('balloon')>-1 || text.indexOf('별풍')>-1 || text.indexOf('후원')>-1) return 'donation';
    if(raw.indexOf('challenge')>-1 || text.indexOf('도전')>-1) return 'challenge';
    if(raw.indexOf('battle')>-1 || text.indexOf('대결')>-1) return 'battle';
    return 'chat';
  }

  function parseRows(){
    var rows=[];
    var jsonItems=(STORE.jsons||[]).slice(-30);
    jsonItems.forEach(function(item){
      flatten(item.data).forEach(function(o){
        var msg = pick(o,['message','msg','chat','comment','content','text','memo','body','szMessage','szMsg']);
        var nick = pick(o,['nickname','nick','userNick','user_nick','name','userName','sender','szNick','szUserNick']);
        var time = pick(o,['time','date','createdAt','created_at','regDate','timestamp','szTime']);
        var amount = pick(o,['count','amount','balloon','starballoon','cnt','value','nCount']);
        if(msg || nick){
          rows.push({
            nick:String(nick||'익명'),
            msg:String(msg||''),
            time:String(time||''),
            amount:amount ? String(amount) : '',
            type:normalizeType(o,msg)
          });
        }
      });
    });

    // fallback: 원본 DOM 텍스트에서 라인 수집
    if(rows.length<3){
      document.querySelectorAll('body div, body li, body p, body span').forEach(function(e){
        if(e.closest('#c9VodPanelV4')) return;
        var t=(e.innerText||'').trim();
        if(t.length>6 && t.length<220 && !/CNINE|다시보기 분석/.test(t)){
          if(t.indexOf('채팅')>-1 || t.indexOf(':')>-1 || t.indexOf('별풍')>-1 || t.indexOf('후원')>-1){
            rows.push({nick:'로그',msg:t,time:'',amount:'',type:normalizeType({},t)});
          }
        }
      });
    }

    // de-dup
    var seen={}, dedup=[];
    rows.forEach(function(r){
      var key=[r.nick,r.msg,r.time,r.type].join('|');
      if(seen[key]) return;
      seen[key]=1; dedup.push(r);
    });
    return dedup.slice(-2000);
  }

  function buildRanks(rows){
    var map={};
    rows.forEach(function(r){
      var key=r.nick||'익명';
      if(!map[key]) map[key]=0;
      map[key]++;
    });
    return Object.keys(map).map(function(k){return {nick:k,count:map[k]};}).sort(function(a,b){return b.count-a.count;}).slice(0,30);
  }

  function collectAndRender(){
    hideOriginalPanels();
    state.rows=parseRows();
    state.ranks=buildRanks(state.rows);
    var users={};
    state.rows.forEach(r=>users[r.nick]=1);
    state.stats.chats = state.rows.length ? String(state.rows.length.toLocaleString()) : '-';
    state.stats.users = Object.keys(users).length ? String(Object.keys(users).length.toLocaleString()) : '-';
    state.stats.status = state.rows.length ? '수집완료' : '수집중';
    render();
  }

  function titleFor(tab, side){
    var names={chat:'채팅',donation:'후원',challenge:'도전',battle:'대결'};
    return names[tab]+(side==='rank'?' 랭킹':' 로그');
  }

  function render(){
    createPanel();
    var rows=state.rows.filter(function(r){ return state.tab==='chat' ? true : r.type===state.tab; });
    if(state.search){
      var q=state.search.toLowerCase();
      rows=rows.filter(function(r){ return (r.nick+' '+r.msg).toLowerCase().indexOf(q)>-1; });
    }
    var ranks=buildRanks(rows);

    document.getElementById('c9StatDuration').textContent=state.stats.duration;
    document.getElementById('c9StatChats').textContent=state.stats.chats;
    document.getElementById('c9StatUsers').textContent=state.stats.users;
    document.getElementById('c9StatStatus').textContent=state.stats.status;

    document.getElementById('c9RankTitle').textContent=titleFor(state.tab,'rank');
    document.getElementById('c9LogTitle').textContent=titleFor(state.tab,'log');

    var rankBox=document.getElementById('c9Ranks');
    if(!ranks.length){
      rankBox.innerHTML='<div class="c9v-empty">수집된 랭킹 데이터가 없습니다.<br>잠시 후 자동 갱신됩니다.</div>';
    }else{
      rankBox.innerHTML=ranks.map(function(r,i){
        var medal=i===0?'🥇':(i===1?'🥈':(i===2?'🥉':String(i+1)));
        return '<div class="c9v-rank"><div class="c9v-medal">'+medal+'</div><div class="c9v-name">'+escapeHtml(r.nick)+'</div><div class="c9v-count">'+r.count.toLocaleString()+'회</div></div>';
      }).join('');
    }

    var logBox=document.getElementById('c9Logs');
    if(!rows.length){
      logBox.innerHTML='<div class="c9v-empty">수집된 로그가 없습니다.<br>VOD 채팅 데이터 로딩 중입니다.</div>';
    }else{
      logBox.innerHTML=rows.slice(-500).reverse().map(function(r){
        return '<div class="c9v-msg">'+(r.time?'<span class="c9v-time">'+escapeHtml(r.time)+'</span>':'')+'<span class="c9v-nick">'+escapeHtml(r.nick)+'</span>'+escapeHtml(r.msg||r.amount||'')+'</div>';
      }).join('');
    }
  }

  function escapeHtml(s){
    return String(s||'').replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});
  }

  function start(){
    createPanel();
    collectAndRender();
    window.addEventListener('c9-vodchat-data', function(){ setTimeout(collectAndRender,50); });
    setInterval(collectAndRender,1200);
  }

  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded', start);
  else start();
})();
