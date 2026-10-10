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
  /* ★ 默认值＝外壳那一套「和纸墨晕 × 海沫玻璃」。
     以前这里是一份**深色**默认（bg #0f1115 / accent #7aa2f7），而 apply() 会在每次
     进站时把这些写进 <html> 的行内样式 —— 行内优先于 :root，于是外壳刚画好的和纸、
     墨晕、海沫玻璃全被盖掉，整站变成一块黑板。把默认值对齐外壳之后，apply() 变成
     一次「写进去也和外壳一样」的空操作；只有用户自己改过外观才真的会不一样。 */
  const D={
    bg:"#F2EDE2",panel:"rgba(255,255,255,.42)",panel2:"rgba(255,255,255,.24)",
    line:"rgba(110,130,150,.20)",
    fg:"#46505C",dim:"#7C8794",dim2:"#A7B0BB",
    accent:"#6E93B3",ok:"#6E9E86",err:"#B0757C",warn:"#9A8FA8",
    aiBubble:"rgba(110,130,150,.10)",meBubble:"rgba(220,234,243,.58)",
    /* ★ 气泡的**字色**也能改：空着就按底色自动推（或退回正文色） */
    aiBubbleFg:"",meBubbleFg:"",
    rCard:20,bubbleMax:76,fs:15,lh:1.8,colw:720,
    bgMode:"solid",grad1:"#1b2233",grad2:"#3a2a4d",bgImg:"",bgDim:45,
    icThink:"spark",icSide:"menu",icDbg:"chip",send:"发送",
    offBadge:1,tw:0,twCps:45
  };
  let T=Object.assign({},D,JSON.parse(localStorage.getItem(LS)||"{}"));
  const save=()=>localStorage.setItem(LS,JSON.stringify(T));
  const say=t=>{try{if(typeof toast==="function")toast(t);}catch(e){}};

  /* ── 图标槽：图片直链 / 自绘图标名 / 任意字符（旧存档里的符号不再画出来）── */
  const isUrl=v=>/^(https?:\/\/|data:image\/|\/)/i.test((v||"").trim());
  const isIcon=v=>(window.NEST_ICON_NAMES||[]).indexOf((v||"").trim())>=0;
  const isEmoji=v=>/[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}\u{2B00}-\u{2BFF}\u{FE0F}]/u.test(v||"");
  function paintIc(host,v,w,def){
    if(!host)return;
    v=(v||"").trim();
    if(isEmoji(v))v="";
    const hasImg=host.querySelector("img");
    if(isUrl(v)){
      if(host.dataset.ic===v&&hasImg)return;
      host.textContent=""; delete host.dataset.ni;
      const im=document.createElement("img"); im.alt=""; im.src=v;
      im.style.width=w+"px"; im.style.height=w+"px"; im.style.objectFit="contain";
      im.onerror=()=>{im.remove();delete host.dataset.ic;paintIc(host,"",w,def);};
      host.dataset.ic=v; host.append(im); return;
    }
    if(hasImg){hasImg.remove(); delete host.dataset.ic;}
    const name=isIcon(v)?v:(v?null:def);
    if(name){
      if(host.dataset.ni===name&&host.querySelector("svg"))return;
      host.textContent=""; host.dataset.ni=name;
      if(window.nestIcon)host.append(nestIcon(name,w));
      return;
    }
    delete host.dataset.ni;
    if(host.textContent!==v)host.textContent=v;
  }

  const st=document.createElement("style");
  st.textContent=`
body{background:var(--nest-page-bg,var(--bg))}
/* ★ 气泡的**形状**（那两组不对称圆角、76% 宽度）由外壳定死，这儿一条都不写 ——
   以前这里给 .bubble 重新指定 border-radius / max-width，还靠 :first-child 把
   左上角抹成 0，注入的样式又排在外壳后面，于是设计稿的软边全被盖掉。
   这里只保留「颜色可换」：外壳读 --nest-ai-bubble / --nest-me-bubble / --nest-me-fg。 */
details.think,.tool{border-radius:var(--nest-r-card,var(--r))}
.sk-h{font-size:13px;color:var(--dim);margin:15px 0 7px;letter-spacing:.5px}
.sk-h:first-child{margin-top:0}
.sk-row{display:flex;align-items:center;gap:7px;margin:6px 0;font-size:13px;color:var(--dim)}
.sk-row>span.lb{flex:0 0 76px}
.sk-row input[type=range]{flex:1;min-width:0;accent-color:var(--accent)}
.sk-row input[type=color]{width:36px;height:26px;padding:0;border:1px solid var(--ink-1);border-radius:6px;background:none}
.sk-row input[type=text]{flex:1;min-width:0;width:100%;background:var(--glass-bg);border:1px solid var(--glass-line);
  color:var(--fg);border-radius:12px;padding:6px 8px;font:inherit;font-size:16px}
.sk-row .v{flex:0 0 44px;text-align:right;color:var(--tx-3);font-size:10px;letter-spacing:.14em;
  font-family:var(--latin)}
.sk-btns{display:flex;flex-wrap:wrap;gap:6px;margin:9px 0}
.sk-btns button{padding:7px 11px;border-radius:10px;border:1px solid var(--ink-1);background:transparent;font-size:13px}
.sk-btns button.on{border-color:var(--accent);color:var(--accent)}
.sk-presets{display:flex;gap:7px;flex-wrap:wrap}
.sk-presets i{width:36px;height:28px;border-radius:8px;border:1px solid var(--ink-1);cursor:pointer;display:block}
.nest-off{display:flex;align-items:center;gap:5px;font-size:12px;color:var(--tx-2);
  border:1px solid var(--ink-1);border-radius:10px;padding:2px 9px;cursor:pointer;white-space:nowrap}
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
    /* ★ 字色：用户填了就听用户的；没填就按底色推 ——
       只有 #rrggbb / #rgb 推得出该配深字还是浅字，海沫玻璃那种 rgba(...) 推不出来，
       退回正文色 --tx-1（写死白色会变成白字白底）。 */
    const autoFg=bg=>/^#([0-9a-f]{3}|[0-9a-f]{6})$/i.test(String(bg||""))
        ?(lum(bg)>0.62?"#10131a":"#ffffff"):"var(--tx-1)";
    set("--nest-ai-fg",String(T.aiBubbleFg||"").trim()||autoFg(T.aiBubble));
    set("--nest-me-fg",String(T.meBubbleFg||"").trim()||autoFg(T.meBubble));
    /* ★ --nest-r-bubble / --nest-tail 不再写了：气泡那两组不对称软边是设计定死的，
       面板里那两枚控件也一起撤了，留着这两个变量只会让人以为还能调。 */
    set("--nest-r-card",T.rCard+"px");
    set("--nest-bubble-max",T.bubbleMax+"%");
    set("--fs",T.fs+"px");set("--lh",String(T.lh));set("--colw",T.colw+"px");
    if(T.bgMode==="img"&&T.bgImg){
      const d=(T.bgDim/100).toFixed(2);
      set("--nest-page-bg",'linear-gradient(rgba(0,0,0,'+d+'),rgba(0,0,0,'+d+')), url("'+T.bgImg+'") center/cover no-repeat fixed');
    }else if(T.bgMode==="grad"){
      set("--nest-page-bg","linear-gradient(160deg, "+T.grad1+", "+T.grad2+")");
    }else{
      set("--nest-page-bg",T.bg);
    }
    const sb=document.querySelector("#btnSide"); if(sb)paintIc(sb,T.icSide,18,"menu");
    const db=[].slice.call(document.querySelectorAll("#bar .ibtn")).find(b=>(b.title||"").indexOf("看这一轮")===0);
    if(db)paintIc(db,T.icDbg,16,"chip");
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
      try{const ic=d.querySelector("summary .ic"); if(ic)paintIc(ic,T.icThink,15,"spark");}catch(e){}
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
  badge.innerHTML='<span class="moon"></span><span class="txt">在自己的时间里</span>';
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
  /* ★ 预设里原来有「纸」和「暖」两套暖土金 —— 那是上一版的皮，
     跟和纸墨晕 × 海沫玻璃冲突，换成了冷调的两套（海雾 / 月白）。
     剩下几套只是把纸换成别的颜色，主色一律还在青灰那一族里。 */
  const PRESETS=[
    ["和纸",{bg:"#F2EDE2",panel:"rgba(255,255,255,.42)",panel2:"rgba(255,255,255,.24)",
            line:"rgba(110,130,150,.20)",fg:"#46505C",dim:"#7C8794",dim2:"#A7B0BB",
            accent:"#6E93B3",aiBubble:"rgba(110,130,150,.10)",meBubble:"rgba(220,234,243,.58)",bgMode:"solid"}],
    ["月白",{bg:"#E8EEF2",panel:"rgba(255,255,255,.46)",panel2:"rgba(255,255,255,.26)",
            line:"rgba(110,130,150,.20)",fg:"#3E4A57",dim:"#72808E",dim2:"#9FAAB6",
            accent:"#6E93B3",aiBubble:"rgba(110,130,150,.10)",meBubble:"rgba(214,232,244,.60)",bgMode:"solid"}],
    ["海雾",{bg:"#E6EDF1",panel:"rgba(255,255,255,.44)",panel2:"rgba(255,255,255,.25)",
            line:"rgba(110,130,150,.22)",fg:"#42505E",dim:"#75838F",dim2:"#A2ADB8",
            accent:"#6E93B3",aiBubble:"rgba(110,130,150,.12)",meBubble:"rgba(204,226,238,.62)",bgMode:"solid"}],
    ["夜蓝",{bg:"#1C2430",panel:"rgba(255,255,255,.08)",panel2:"rgba(255,255,255,.05)",
            line:"rgba(255,255,255,.12)",fg:"#DCE4EC",dim:"#9FAEBD",dim2:"#7C8B9A",
            accent:"#8FB4D4",aiBubble:"rgba(110,140,175,.14)",meBubble:"rgba(110,140,175,.16)",bgMode:"solid"}]
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
    const i=document.createElement("input"); i.type="text";
    i.value=isEmoji(T[k])?(D[k]||""):(T[k]||"");
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
    cRow(box,"aiBubbleFg","它的字"); cRow(box,"meBubbleFg","我的字");

    box.append(H("形状 · 字号"));
    /* ★ 「气泡圆角 / 小尾巴」两枚控件撤了：那两组不对称软边（22/30/26/18 与
       22/22/6/22）是这一套皮的一部分，留着滑杆等于留一个能把它调坏的入口。 */
    nRow(box,"rCard","卡片圆角",0,28,1,"px");
    nRow(box,"bubbleMax","气泡宽度",55,96,1,"%");
    nRow(box,"fs","字号",13,20,0.5,"px");
    nRow(box,"lh","行高",1.3,2.1,0.05,"");
    nRow(box,"colw","聊天区宽",560,1200,20,"px");

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
      t.onclick=()=>{ok.textContent="…";testImg(T.bgImg,g=>{ok.textContent="";ok.append(nestIcon(g?"check":"close",14));ok.style.color=g?"var(--ok)":"var(--err)";});};
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
    const obb=document.createElement("button"); obb.className=T.offBadge?"on":"";
    obb.append(nestIcon("moon",14),document.createTextNode(T.offBadge?"显示：开":"显示：关"));
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

  /* ── 主题对外的口子 ──
     「我的 › 外观」那一节（nest-setting.js）通过它读写同一份主题，
     不另存一套 —— 两处改的是同一个 localStorage 键。 */
  const WATCHERS=[];
  function changed(){ apply(); WATCHERS.forEach(f=>{ try{ f(Object.assign({},T)); }catch(e){} }); }
  window.nestTheme={
    all:()=>Object.assign({},T),
    defaults:()=>Object.assign({},D),
    presets:()=>PRESETS.map(p=>[p[0],Object.assign({},p[1])]),
    set(patch){ Object.assign(T,patch||{}); save(); changed(); },
    reset(){ T=Object.assign({},D); save(); changed(); },
    on(fn){ if(typeof fn==="function")WATCHERS.push(fn); },
  };

  /* ── 启动 ── */
  function boot(){
    wrapThink(); wrapHandle(); apply(); buildPanel();
    const mo=badge.querySelector(".moon");
    if(mo&&window.nestIcon&&!mo.querySelector("svg"))mo.append(nestIcon("moon",14));
  }
  if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",boot);
  else boot();
  new MutationObserver(()=>{
    const b=document.querySelector("#btnSend");
    if(b&&b.textContent==="发送"&&T.send!=="发送")b.textContent=T.send;
  }).observe(document.body,{childList:true,subtree:true});

}catch(e){console.error("nest-skin 挂了：",e);}
})();
