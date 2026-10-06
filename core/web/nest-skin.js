/* ══════════════════════════════════════════════════════════
   巢 · 皮肤模块 v1  （外观面板 + 离线标识 + 打字机）
   装法：在 nest.html 的 </body> 前面加一行
        <script src="/nest-skin.js?v=1"></script>
   全部存本机 localStorage；存服务器（换设备同步）下一批做。
   ══════════════════════════════════════════════════════════ */
(function(){
"use strict";
try{
  const LS="nest_theme";
  const D={
    bg:"#0f1115",panel:"#151a21",panel2:"#1b212b",line:"#252c38",
    fg:"#e9edf4",dim:"#96a0b1",dim2:"#6b7486",
    accent:"#7aa2f7",ok:"#5ec27f",err:"#e0716f",warn:"#e0b96f",
    aiBubble:"#1b212b",meBubble:"#7aa2f7",
    rBubble:14,rCard:9,bubbleMax:88,fs:15,lh:1.6,colw:760,tail:0,
    bgMode:"solid",grad1:"#1b2233",grad2:"#3a2a4d",bgImg:"",bgDim:45,
    icThink:"💡",icSide:"☰",icDbg:"🐞",send:"发送",
    offBadge:1,tw:0,twCps:45
  };
  let T=Object.assign({},D,JSON.parse(localStorage.getItem(LS)||"{}"));
  const save=()=>localStorage.setItem(LS,JSON.stringify(T));
  const say=t=>{try{if(typeof toast==="function")toast(t);}catch(e){}};

  const st=document.createElement("style");
  st.textContent=`
body{background:var(--nest-page-bg,var(--bg))}
.bubble{background:var(--nest-ai-bubble,var(--panel2));border-radius:var(--nest-r-bubble,var(--r));max-width:var(--nest-bubble-max,88%)}
.turn.me .bubble{background:var(--nest-me-bubble,var(--accent));color:var(--nest-me-fg,#0b1020)}
.turn.ai .bubble:first-child{border-top-left-radius:var(--nest-tail,var(--r))}
.turn.me .bubble:first-child{border-top-right-radius:var(--nest-tail,var(--r))}
details.think,.tool{border-radius:var(--nest-r-card,var(--r-sm))}
.sk-h{font-size:13px;color:var(--dim);margin:15px 0 7px;letter-spacing:.5px}
.sk-h:first-child{margin-top:0}
.sk-row{display:flex;align-items:center;gap:7px;margin:6px 0;font-size:13px;color:var(--dim)}
.sk-row>span.lb{flex:0 0 76px}
.sk-row input[type=range]{flex:1;min-width:0;accent-color:var(--accent)}
.sk-row input[type=color]{width:36px;height:26px;padding:0;border:1px solid var(--line);border-radius:6px;background:none}
.sk-row input[type=text]{flex:1;min-width:0;width:100%;background:var(--panel2);border:1px solid var(--line);
  color:var(--fg);border-radius:7px;padding:6px 8px;font:inherit;font-size:13px}
.sk-row .v{flex:0 0 40px;text-align:right;color:var(--dim2);font-size:12px}
.sk-btns{display:flex;flex-wrap:wrap;gap:6px;margin:9px 0}
.sk-btns button{padding:7px 11px;border-radius:8px;border:1px solid var(--line);background:var(--panel2);font-size:13px}
.sk-btns button.on{border-color:var(--accent);color:var(--accent)}
.sk-presets{display:flex;gap:7px;flex-wrap:wrap}
.sk-presets i{width:36px;height:28px;border-radius:8px;border:1px solid var(--line);cursor:pointer;display:block}
.nest-off{display:flex;align-items:center;gap:5px;font-size:12px;color:var(--warn);
  border:1px solid var(--warn);border-radius:20px;padding:2px 9px;cursor:pointer;white-space:nowrap}
.nest-off .moon{animation:skbreath 2.6s ease-in-out infinite}
@keyframes skbreath{0%,100%{opacity:.4}50%{opacity:1}}
@media(max-width:600px){.nest-off .txt{display:none}}
`;
  document.head.append(st);

  const money=v=>"#"+String(v||"#000").replace("#","");
  function lum(hex){
    const c=money(hex).slice(1);
    const n=parseInt(c.length===3?c.split("").map(x=>x+x).join(""):c,16)||0;
    return (0.299*((n>>16)&255)+0.587*((n>>8)&255)+0.114*(n&255))/255;
  }
  function apply(){
    const s=document.documentElement.style;
    const set=(k,v)=>s.setProperty(k,v);
    set("--bg",T.bg);set("--panel",T.panel);set("--panel2",T.panel2);set("--line",T.line);
    set("--fg",T.fg);set("--dim",T.dim);set("--dim2",T.dim2);
    set("--accent",T.accent);set("--ok",T.ok);set("--err",T.err);set("--warn",T.warn);
    set("--nest-ai-bubble",T.aiBubble);set("--nest-me-bubble",T.meBubble);
    set("--nest-me-fg",lum(T.meBubble)>0.62?"#10131a":"#ffffff");
    set("--nest-r-bubble",T.rBubble+"px");set("--nest-r-card",T.rCard+"px");
    set("--nest-bubble-max",T.bubbleMax+"%");set("--nest-tail",T.tail?"4px":"0px");
    set("--fs",T.fs+"px");set("--lh",String(T.lh));set("--colw",T.colw+"px");
    if(T.bgMode==="img"&&T.bgImg){
      const d=(T.bgDim/100).toFixed(2);
      set("--nest-page-bg",'linear-gradient(rgba(0,0,0,'+d+'),rgba(0,0,0,'+d+')), url("'+T.bgImg+'") center/cover no-repeat fixed');
    }else if(T.bgMode==="grad"){
      set("--nest-page-bg","linear-gradient(160deg, "+T.grad1+", "+T.grad2+")");
    }else{
      set("--nest-page-bg",T.bg);
    }
    const sb=document.querySelector("#btnSide"); if(sb)sb.textContent=T.icSide;
    const db=[].slice.call(document.querySelectorAll("#bar .ibtn")).find(b=>(b.title||"").indexOf("看这一轮")===0);
    if(db)db.textContent=T.icDbg;
    const snd=document.querySelector("#btnSend");
    if(snd&&!snd.classList.contains("stop"))snd.textContent=T.send;
    if(T.offBadge)badge.hidden=badge.hidden;   /* 交给轮询控制 */
  }

  /* ── 图标替换（思考的小灯泡）── */
  let thinkWrapped=false;
  function wrapThink(){
    if(thinkWrapped||typeof window.thinkEl!=="function")return;
    const orig=window.thinkEl; thinkWrapped=true;
    window.thinkEl=function(t){
      const d=orig(t);
      try{const ic=d.querySelector("summary .ic"); if(ic)ic.textContent=T.icThink;}catch(e){}
      return d;
    };
  }

  /* ── 打字机 ── */
  const TY={q:[],busy:false,flush:false};
  function typeOut(L,text){
    const b=document.createElement("div"); b.className="bubble"; L.bs.append(b);
    return new Promise(res=>{
      const cps=Math.max(2,T.twCps||45);
      let i=0,last=performance.now(),acc=0;
      const step=now=>{
        const dt=Math.min(0.1,(now-last)/1000); last=now;
        acc+=dt*cps*(TY.flush?300:1);
        if(acc>=1){const n=Math.floor(acc);acc-=n;i=Math.min(text.length,i+n);b.textContent=text.slice(0,i);
          try{toBottom();}catch(e){}}
        if(TY.flush){i=text.length;b.textContent=text;}
        if(i>=text.length){res();return;}
        requestAnimationFrame(step);
      };
      requestAnimationFrame(step);
    });
  }
  async function pump(){
    if(TY.busy)return; TY.busy=true;
    while(TY.q.length){const it=TY.q.shift(); try{await typeOut(it.L,it.t);}catch(e){}}
    TY.busy=false; TY.flush=false;
  }
  function wrapHandle(){
    if(typeof window.handle!=="function"||window.__skHandle)return;
    const base=window.handle; window.__skHandle=1;
    window.handle=function(ev,L){
      try{
        if(ev.type==="s"&&T.tw){
          if(L.st&&!L.st.hidden){L.st.hidden=true;L.st.textContent="";}
          TY.q.push({L:L,t:(ev.text||"").trim()}); pump(); return;
        }
        if(ev.type==="done"&&T.tw)TY.flush=true;
      }catch(e){}
      return base(ev,L);
    };
  }

  /* ── 离线标识 ── */
  const badge=document.createElement("div");
  badge.className="nest-off"; badge.hidden=true;
  badge.innerHTML='<span class="moon">🌙</span><span class="txt">在自己的时间里</span>';
  badge.onclick=()=>{ say(badge.dataset.tip||"它还不在自己的时间里"); };
  (function put(){
    const bar=document.querySelector("#bar"); if(!bar)return;
    const sp=bar.querySelector(".sp");
    if(sp)bar.insertBefore(badge,sp); else bar.append(badge);
    const side=document.querySelector("#btnSide");
    if(side)bar.append(badge);           /* 保证在可见区 */
  })();
  let lastOff=null;
  async function pollOff(){
    try{
      const r=await fetch("/api/offline",{credentials:"same-origin"});
      if(!r.ok)return;
      const j=await r.json();
      if(j.active){
        const mins=Math.max(1,Math.round((Date.now()/1000-(j.started||Date.now()/1000))/60));
        badge.hidden=!T.offBadge;
        badge.querySelector(".txt").textContent="在自己的时间里 · "+mins+" 分钟";
        badge.dataset.tip="它从 "+new Date((j.started||0)*1000).toLocaleTimeString("zh-CN",{hour:"2-digit",minute:"2-digit"})+" 起就在自己待着了";
      }else{
        badge.hidden=true;
        if(j.last)lastOff=j.last;
        badge.dataset.tip=lastOff?("上次自由时段："+new Date(lastOff*1000).toLocaleString("zh-CN",{month:"2-digit",day:"2-digit",hour:"2-digit",minute:"2-digit"})):"它还不在自己的时间里";
      }
    }catch(e){}
  }
  pollOff(); setInterval(pollOff,30000);

  /* ── 外观面板 ── */
  const PRESETS=[
    ["夜",{}],
    ["纸",{bg:"#f4f1ea",panel:"#fffdf8",panel2:"#efeae0",line:"#ded7c9",fg:"#2f2b26",dim:"#6f675c",dim2:"#948b7d",
          accent:"#b07d3a",aiBubble:"#fffdf8",meBubble:"#e8d9bd",bgMode:"solid"}],
    ["森",{bg:"#0c1410",panel:"#12201a",panel2:"#16291f",line:"#23392c",fg:"#e6f0e8",dim:"#8fa79a",dim2:"#6b8175",
          accent:"#6fbf8b",aiBubble:"#16291f",meBubble:"#2f6b4a",bgMode:"solid"}],
    ["霓",{bg:"#0a0a12",panel:"#12121f",panel2:"#191931",line:"#2a2a4a",fg:"#eae6ff",dim:"#9a92c9",dim2:"#6f679b",
          accent:"#b06cff",aiBubble:"#191931",meBubble:"#7a2bd6",bgMode:"solid"}],
    ["暖",{bg:"#140f0c",panel:"#1d1613",panel2:"#261c17",line:"#38291f",fg:"#f2e8e0",dim:"#b39a88",dim2:"#8a7566",
          accent:"#e0915c",aiBubble:"#261c17",meBubble:"#a95c2e",bgMode:"solid"}]
  ];
  function cRow(box,k,lb){
    const i=document.createElement("input"); i.type="color"; i.value=money(T[k]||D[k]);
    i.oninput=()=>{T[k]=i.value;save();apply();};
    const r=document.createElement("div"); r.className="sk-row";
    r.append(Object.assign(document.createElement("span"),{className:"lb",textContent:lb}),i);
    box.append(r);
  }
  function nRow(box,k,lb,mn,mx,step,unit){
    const i=document.createElement("input"); i.type="range"; i.min=mn;i.max=mx;i.step=step;i.value=T[k];
    const v=document.createElement("span"); v.className="v"; v.textContent=T[k]+unit;
    i.oninput=()=>{T[k]=parseFloat(i.value);v.textContent=T[k]+unit;save();apply();};
    const r=document.createElement("div"); r.className="sk-row";
    r.append(Object.assign(document.createElement("span"),{className:"lb",textContent:lb}),i,v);
    box.append(r);
  }
  function tRow(box,k,lb,w){
    const i=document.createElement("input"); i.type="text"; i.value=T[k]||"";
    if(w)i.style.maxWidth=w;
    i.oninput=()=>{T[k]=i.value;save();apply();};
    const r=document.createElement("div"); r.className="sk-row";
    r.append(Object.assign(document.createElement("span"),{className:"lb",textContent:lb}),i);
    box.append(r);
  }
  function testImg(url,cb){
    if(!url){cb(false);return;}
    const im=new Image(); let done=false;
    const fin=ok=>{if(!done){done=true;cb(ok);}};
    setTimeout(()=>fin(false),5000);
    im.onload=()=>fin(true); im.onerror=()=>fin(false); im.src=url;
  }
  function buildPanel(){
    const side=document.querySelector("#side"); if(!side)return;
    side.innerHTML="";
    const box=document.createElement("div");
    const H=x=>Object.assign(document.createElement("div"),{className:"sk-h",textContent:x});

    box.append(H("外观 · 预设"));
    const pr=document.createElement("div"); pr.className="sk-presets";
    PRESETS.forEach(p=>{
      const i=document.createElement("i"); i.title=p[0];
      i.style.background=(p[1].meBubble||p[1].accent||T.meBubble);
      i.onclick=()=>{Object.assign(T,p[1]);save();apply();buildPanel();say("换了「"+p[0]+"」");};
      pr.append(i);
    });
    box.append(pr);

    box.append(H("颜色"));
    cRow(box,"bg","页面底色"); cRow(box,"panel","面板");
    cRow(box,"panel2","卡片"); cRow(box,"line","分隔线");
    cRow(box,"accent","主色"); cRow(box,"fg","字色");
    cRow(box,"dim","次要字"); cRow(box,"warn","进行中");
    cRow(box,"aiBubble","它的气泡"); cRow(box,"meBubble","我的气泡");

    box.append(H("形状 · 字号"));
    nRow(box,"rBubble","气泡圆角",0,28,1,"px");
    nRow(box,"rCard","卡片圆角",0,20,1,"px");
    nRow(box,"bubbleMax","气泡宽度",55,96,1,"%");
    nRow(box,"fs","字号",13,20,0.5,"px");
    nRow(box,"lh","行高",1.3,2.1,0.05,"");
    nRow(box,"colw","聊天区宽",560,1200,20,"px");
    const tb=document.createElement("div"); tb.className="sk-btns";
    const bt=document.createElement("button"); bt.textContent="气泡小尾巴：开";
    bt.className=T.tail?"on":"";
    bt.onclick=()=>{T.tail=T.tail?0:1;save();apply();buildPanel();};
    tb.append(bt); box.append(tb);

    box.append(H("背景"));
    const mb=document.createElement("div"); mb.className="sk-btns";
    [["solid","纯色"],["grad","渐变"],["img","图片"]].forEach(m=>{
      const b=document.createElement("button"); b.textContent=m[1];
      b.className=(T.bgMode===m[0])?"on":"";
      b.onclick=()=>{T.bgMode=m[0];save();apply();buildPanel();};
      mb.append(b);
    });
    box.append(mb);
    if(T.bgMode==="grad"){ cRow(box,"grad1","渐变 1"); cRow(box,"grad2","渐变 2"); }
    if(T.bgMode==="img"){
      const r=document.createElement("div"); r.className="sk-row";
      r.append(Object.assign(document.createElement("span"),{className:"lb",textContent:"图片链接"}));
      const i=document.createElement("input"); i.type="text"; i.placeholder="https://…直链"; i.value=T.bgImg||"";
      const ok=document.createElement("span"); ok.className="v"; 
      i.oninput=()=>{T.bgImg=i.value.trim();save();apply();};
      const t=document.createElement("button"); t.textContent="试"; t.className="on";
      t.onclick=()=>{ok.textContent="…";testImg(T.bgImg,g=>{ok.textContent=g?"✓":"✗";ok.style.color=g?"var(--ok)":"var(--err)";});};
      r.append(i,t,ok); box.append(r);
      nRow(box,"bgDim","变暗",0,90,5,"%");
    }

    box.append(H("图标 · 文字"));
    tRow(box,"icThink","思考","60px"); tRow(box,"icSide","侧栏","60px");
    tRow(box,"icDbg","调试","60px"); tRow(box,"send","发送按钮","90px");

    box.append(H("打字机"));
    const wb=document.createElement("div"); wb.className="sk-btns";
    [["off","关"],["slow","慢"],["mid","中"],["fast","快"]].forEach(m=>{
      const b=document.createElement("button"); b.textContent=m[1];
      const on=(m[0]==="off"&&!T.tw)||(m[0]==="slow"&&T.tw&&T.twCps===22)||(m[0]==="mid"&&T.tw&&T.twCps===45)||(m[0]==="fast"&&T.tw&&T.twCps===90);
      b.className=on?"on":"";
      b.onclick=()=>{
        if(m[0]==="off")T.tw=0; else {T.tw=1;T.twCps={slow:22,mid:45,fast:90}[m[0]];}
        save();buildPanel();say(T.tw?"打字机：开":"打字机：关");
      };
      wb.append(b);
    });
    box.append(wb);

    box.append(H("离线标识"));
    const ob=document.createElement("div"); ob.className="sk-btns";
    const obb=document.createElement("button"); obb.textContent=T.offBadge?"🌙 显示：开":"🌙 显示：关";
    obb.className=T.offBadge?"on":"";
    obb.onclick=()=>{T.offBadge=T.offBadge?0:1;save();buildPanel();pollOff();};
    ob.append(obb); box.append(ob);
    box.append(Object.assign(document.createElement("div"),{className:"sk-row",
      textContent:"它进自己的时间时，顶上会亮一个月亮。"}));

    const bb=document.createElement("div"); bb.className="sk-btns";
    const b1=document.createElement("button"); b1.textContent="恢复默认";
    b1.onclick=()=>{if(confirm("恢复默认外观？")){T=Object.assign({},D);save();apply();buildPanel();}};
    const b2=document.createElement("button"); b2.textContent="复制主题";
    b2.onclick=async()=>{try{await navigator.clipboard.writeText(JSON.stringify(T));b2.textContent="已复制";
      setTimeout(()=>b2.textContent="复制主题",1200);}catch(e){say("复制失败");}};
    const b3=document.createElement("button"); b3.textContent="粘贴导入";
    b3.onclick=()=>{const s=prompt("把主题那串字粘进来：");if(!s)return;
      try{T=Object.assign({},D,JSON.parse(s));save();apply();buildPanel();say("导进来了");}catch(e){say("这串字看不懂");}};
    bb.append(b1,b2,b3); box.append(bb);

    side.append(box);
  }

  /* ── 启动 ── */
  function boot(){
    wrapThink(); wrapHandle(); apply(); buildPanel();
  }
  if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",boot);
  else boot();
  new MutationObserver(()=>{
    const b=document.querySelector("#btnSend");
    if(b&&b.textContent==="发送"&&T.send!=="发送")b.textContent=T.send;
  }).observe(document.body,{childList:true,subtree:true});

}catch(e){console.error("nest-skin 挂了：",e);}
})();
