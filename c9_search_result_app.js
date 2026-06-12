(function(){
  'use strict';

  var q = window.C9_SEARCH_QUERY || '';
  var KEYWORD_URL = window.C9_BAD_WORDS_URL || 'https://keyman1335-maker.github.io/poong-rank/bad_words.json?v=' + Date.now();

  var boards = [
    {name:'SOOP(숲)', url:'https://ygosu.com/board/soop'},
    {name:'인터넷방송', url:'https://ygosu.com/board/ib'},
    {name:'스타방송', url:'https://ygosu.com/board/starbbs'},
    {name:'스타대학', url:'https://ygosu.com/board/pan_monstarz'}
  ];

  function esc(s){
    return String(s||'').replace(/[&<>"']/g,function(c){
      return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]||c;
    });
  }

  function normalize(s){
    return String(s||'')
      .toLowerCase()
      .replace(/[|｜┃│∣❘❙❚]/g,'ㅣ')
      .replace(/\s+/g,'');
  }

  function fallbackDict(){
    return {
      categories:{
        "팬덤비하자":[
          {"word":"길견","score":3},{"word":"길나인","score":3},{"word":"ㅣㅣ","score":3},{"word":"길태","score":3},{"word":"젖퀴","score":3}
        ],
        "타퀴의심":[
          {"word":"덕구","score":2},{"word":"강덕구","score":2},{"word":"케이","score":2},{"word":"보성","score":2}
        ],
        "이간질":[
          {"word":"방갤","score":2},{"word":"벽갤","score":2},{"word":"씨나갤","score":2}
        ]
      },
      levels:[
        {"min":6,"label":"위험","emoji":"🚨"},
        {"min":3,"label":"주의","emoji":"⚠️"},
        {"min":1,"label":"감지","emoji":"🟡"},
        {"min":0,"label":"정상","emoji":"✅"}
      ]
    };
  }

  function flatten(dict){
    var root = dict && dict.categories ? dict.categories : dict;
    var out = [];
    if(!root || typeof root !== 'object') return out;

    Object.keys(root).forEach(function(cat){
      var arr = root[cat];
      if(!Array.isArray(arr)) return;
      arr.forEach(function(x){
        if(typeof x === 'string') out.push({category:cat, word:x, score:1});
        else if(x && x.word) out.push({category:cat, word:String(x.word), score:Number(x.score||1)});
      });
    });

    var seen = {};
    out = out.filter(function(k){
      var key = k.category + '|' + k.word;
      if(seen[key]) return false;
      seen[key]=1;
      return true;
    });
    out.sort(function(a,b){return String(b.word).length - String(a.word).length;});
    return out;
  }

  function levels(dict){
    var lv = dict && Array.isArray(dict.levels) ? dict.levels : fallbackDict().levels;
    return lv.slice().sort(function(a,b){return Number(b.min||0)-Number(a.min||0);});
  }

  function pickLevel(score, lv){
    for(var i=0;i<lv.length;i++){
      if(score >= Number(lv[i].min||0)) return lv[i];
    }
    return {min:0,label:'정상',emoji:'✅'};
  }

  function loadDict(){
    return fetch(KEYWORD_URL,{cache:'no-store'})
      .then(function(r){ if(!r.ok) throw new Error('HTTP '+r.status); return r.json(); })
      .catch(function(){ return fallbackDict(); });
  }

  function status(msg,color){
    var el = document.getElementById('guard-status');
    if(el){
      el.textContent = msg;
      if(color) el.style.color = color;
    }
  }

  function closePanel(){
    var p=document.getElementById('guard-pop');
    if(p) p.style.display='none';
  }

  function build(){
    var enc=encodeURIComponent(q);
    document.title='와이고수 닉네임 검색 - '+q;
    document.body.innerHTML =
      '<div id="guard-pop" style="display:block;position:fixed;z-index:999999;left:50%;top:14px;transform:translateX(-50%);width:min(920px,calc(100vw - 24px));max-height:58vh;overflow:auto;border:1px solid #3b82f6;border-radius:16px;background:linear-gradient(135deg,#0f172a,#111827);box-shadow:0 18px 60px rgba(0,0,0,.55);color:#fff;">'
      +'<div style="padding:10px 42px 10px 13px;background:rgba(15,23,42,.94);border-bottom:1px solid rgba(59,130,246,.45);">'
      +'<button id="guard-close-ready" type="button" style="position:absolute;right:10px;top:8px;width:28px;height:28px;border:0;border-radius:8px;background:#475569;color:#fff;font-weight:1000;cursor:pointer;">×</button>'
      +'<div style="font-size:16px;font-weight:1000;color:#fff;">🚨 게시글 제목 감지</div>'
      +'<div id="guard-status" style="margin-top:4px;color:#93c5fd;font-size:13px;font-weight:900;">제목 감지 준비중... · iframe 로딩 대기</div>'
      +'</div></div>'
      +'<div id="frames" style="display:flex;width:100%;height:100%;overflow:auto;"></div>';

    document.getElementById('guard-close-ready').onclick=closePanel;

    var html = boards.map(function(b){
      var src=b.url+'?best_article=N&searcht=w&search='+enc;
      return '<div style="flex:1;min-width:360px;height:100%;display:flex;flex-direction:column;border-right:1px solid #334155;background:#111827;">'
        +'<div style="height:42px;display:flex;align-items:center;justify-content:center;background:#0f172a;color:#fff;font-weight:900;font-size:14px;border-bottom:1px solid #334155;">'+esc(b.name)+' 검색 : '+esc(q)+'</div>'
        +'<iframe class="yg-frame" data-board="'+esc(b.name)+'" src="'+src+'" style="flex:1;width:100%;border:0;background:#fff;"></iframe>'
        +'</div>';
    }).join('');
    document.getElementById('frames').innerHTML=html;
  }

  function collectTitles(doc){
    var titles=[];
    var selectors=['td.subject a','.subject a','.list_subject a','a[href*="/board/"]'].join(',');
    doc.querySelectorAll(selectors).forEach(function(a){
      var t=(a.textContent||'').replace(/\s+/g,' ').trim();
      var href=a.href||'';
      if(t.length<2 || t.length>140) return;
      if(/^(전체|인기|와토|공지|정보|사진|영상|이벤트|관리자|추천|댓글|목록)$/.test(t)) return;
      if(!/\/board\//.test(href) && !a.closest('td.subject,.subject,.list_subject')) return;
      titles.push({title:t,href:href});
    });
    var seen={};
    return titles.filter(function(x){
      var k=x.title+'|'+x.href;
      if(seen[k]) return false;
      seen[k]=1;
      return true;
    }).slice(0,80);
  }

  function scanTitle(title, keywords){
    var low=normalize(title);
    var hits=[];
    keywords.forEach(function(k){
      var w=normalize(k.word);
      if(!w) return;
      var pos=0,count=0;
      while((pos=low.indexOf(w,pos))!==-1){
        count++;
        pos+=w.length;
      }
      if(count){
        hits.push({category:k.category,word:k.word,score:Number(k.score||1),count:count,sum:Number(k.score||1)*count});
      }
    });
    return hits;
  }

  function scanFrame(f, keywords){
    try{
      var doc=f.contentDocument || f.contentWindow.document;
      var board=f.getAttribute('data-board') || '게시판';
      var rows=[];
      collectTitles(doc).forEach(function(t){
        var hits=scanTitle(t.title, keywords);
        if(hits.length) rows.push({board:board,title:t.title,href:t.href,hits:hits});
      });
      return rows;
    }catch(e){
      return [];
    }
  }

  function render(rows, lv){
    var total=0;
    rows.forEach(function(r){r.hits.forEach(function(h){total += Number(h.sum||h.score||1);});});
    var p=document.getElementById('guard-pop');
    if(!p) return;
    var level=pickLevel(total,lv);

    if(!rows.length){
      p.style.border='1px solid #3b82f6';
      p.innerHTML='<div style="padding:10px 42px 10px 13px;background:rgba(15,23,42,.94);border-bottom:1px solid rgba(59,130,246,.45);">'
        +'<button id="guard-close" type="button" style="position:absolute;right:10px;top:8px;width:28px;height:28px;border:0;border-radius:8px;background:#475569;color:#fff;font-weight:1000;cursor:pointer;">×</button>'
        +'<div style="font-size:16px;font-weight:1000;color:#fff;">✅ 게시글 제목 감지</div>'
        +'<div style="margin-top:4px;color:#93c5fd;font-size:13px;font-weight:900;">감지 없음 · 점수 0점 · 감지글 0건</div>'
        +'</div>';
      document.getElementById('guard-close').onclick=closePanel;
      return;
    }

    var byCat={};
    rows.forEach(function(r){
      r.hits.forEach(function(h){
        var c=h.category||'감지';
        if(!byCat[c]) byCat[c]=[];
        byCat[c].push(h.word);
      });
    });

    var catHtml=Object.keys(byCat).map(function(cat){
      var uniq=byCat[cat].filter(function(v,i,a){return a.indexOf(v)===i;});
      return '<span style="display:inline-block;margin:3px;padding:5px 8px;border-radius:999px;background:#7f1d1d;border:1px solid #ef4444;color:#fff;font-size:12px;font-weight:900;">'+esc(cat)+' : '+esc(uniq.join(', '))+'</span>';
    }).join('');

    var list=rows.slice(0,12).map(function(r){
      var hitText=r.hits.map(function(h){return h.word+(h.count>1?'×'+h.count:'')+' +'+h.sum;}).join(', ');
      return '<div style="margin-top:8px;padding:9px;border-radius:10px;background:rgba(0,0,0,.25);border:1px solid rgba(255,255,255,.10);">'
        +'<div style="color:#7ec8ff;font-size:12px;font-weight:1000;">'+esc(r.board)+'</div>'
        +'<div style="margin-top:3px;color:#fff;font-size:13px;font-weight:900;line-height:1.35;">'+esc(r.title)+'</div>'
        +'<div style="margin-top:5px;color:#ffb4b4;font-size:12px;font-weight:900;">감지: '+esc(hitText)+'</div>'
        +'</div>';
    }).join('');

    p.style.border='1px solid #ef4444';
    p.innerHTML='<div style="position:sticky;top:0;padding:12px 42px 10px 13px;background:rgba(15,23,42,.94);border-bottom:1px solid rgba(239,68,68,.45);">'
      +'<button id="guard-close" type="button" style="position:absolute;right:10px;top:8px;width:28px;height:28px;border:0;border-radius:8px;background:#475569;color:#fff;font-weight:1000;cursor:pointer;">×</button>'
      +'<div style="font-size:17px;font-weight:1000;color:#fff;">'+esc(level.emoji||'🚨')+' 게시글 제목 감지</div>'
      +'<div style="margin-top:4px;color:#ffb4b4;font-size:13px;font-weight:900;">'+esc(level.label||'감지')+' · 점수 '+total+'점 · 감지글 '+rows.length+'건</div>'
      +'<div style="margin-top:7px;">'+catHtml+'</div>'
      +'</div><div style="padding:10px 12px 13px;">'+list+'</div>';
    document.getElementById('guard-close').onclick=closePanel;
  }

  function run(keywords, lv){
    var all=[];
    document.querySelectorAll('iframe.yg-frame').forEach(function(f){
      all=all.concat(scanFrame(f,keywords));
    });
    render(all,lv);
  }

  build();
  status('키워드 로딩중...','#93c5fd');
  loadDict().then(function(dict){
    var keywords=flatten(dict);
    var lv=levels(dict);
    status('키워드 '+keywords.length+'개 로드 완료 · 검색결과 로딩중...','#93c5fd');
    document.querySelectorAll('iframe.yg-frame').forEach(function(f){
      f.addEventListener('load',function(){setTimeout(function(){run(keywords,lv);},700);});
    });
    setTimeout(function(){run(keywords,lv);},1800);
    setTimeout(function(){run(keywords,lv);},3500);
  });
})();