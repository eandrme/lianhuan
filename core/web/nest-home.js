/* ══════════════════════════════════════════════════════════
   巢 · 主界面（HOME）—— 和纸墨晕 × 海沫玻璃

   装法：nest.html 里放在 nest-tabs.js 后面
        <script src="/nest-home.js?v=1"></script>

   这一页是「一整个家」的门面：底部导航条撤了之后，所有入口都平铺在这儿，
   靠**点卡片**进子页。从上到下：

     ① 身份栏      ☰  ·  HOME（点它去挑对话窗口）  ·  ⚙
     ② 天数区      大留白，这一页的呼吸口
     ③ OUR TIDE    两个头像 + 陪伴天数 + 名字 + 一句诗
     ④ 记忆        横向滑动的 MEMORY INDEX（点一张 → 记忆详情）
     ⑤ 一起        → 一起页
     ⑥ 日历 / 书房 一行两列
     ⑦ 时间线      → 时间线页
     ⑧ 空间        最下面，最近一条

   卡片之间用 0.5px 的细线串起来（像用线挂着一串纸片）。
   ══════════════════════════════════════════════════════════ */
(function(){
"use strict";
try{
  const NS="http://www.w3.org/2000/svg";
  const $=(s,r=document)=>r.querySelector(s);
  const el=(t,c,x)=>{const e=document.createElement(t);if(c)e.className=c;if(x!=null)e.textContent=x;return e;};
  const say=t=>{try{if(typeof toast==="function")toast(t);}catch(e){}};
  const go=(k,arg)=>{ if(window.nestGo)window.nestGo(k,arg); };
  const jget=async u=>{const r=await fetch(u,{credentials:"same-origin"});if(!r.ok)throw new Error("HTTP "+r.status);return r.json();};
  const pad2=n=>String(n).padStart(2,"0");

  /* ── 两个画出来的小图形（界面里不许出现 emoji / ★ / ✦ 那些字形）── */
  function sparkle(size,cls){
    const s=document.createElementNS(NS,"svg");
    s.setAttribute("viewBox","0 0 24 24");
    s.setAttribute("fill","none"); s.setAttribute("stroke","currentColor");
    s.setAttribute("stroke-width","1.5"); s.setAttribute("stroke-linecap","round");
    s.setAttribute("stroke-linejoin","round"); s.setAttribute("aria-hidden","true");
    s.setAttribute("width",size); s.setAttribute("height",size);
    if(cls)s.setAttribute("class",cls);
    const p=document.createElementNS(NS,"path");
    /* 四角星：从顶点往里收，再回到顶点 —— 淡墨点的那个形状 */
    p.setAttribute("d","M12 2.6 C12.9 8.3 15.7 11.1 21.4 12 C15.7 12.9 12.9 15.7 12 21.4 "
                       +"C11.1 15.7 8.3 12.9 2.6 12 C8.3 11.1 11.1 8.3 12 2.6 Z");
    s.append(p); return s;
  }
  function rings(size){
    const s=document.createElementNS(NS,"svg");
    s.setAttribute("viewBox","0 0 24 24");
    s.setAttribute("fill","none"); s.setAttribute("stroke","currentColor");
    s.setAttribute("stroke-width","1.5"); s.setAttribute("stroke-linecap","round");
    s.setAttribute("stroke-linejoin","round"); s.setAttribute("aria-hidden","true");
    s.setAttribute("width",size); s.setAttribute("height",size);
    [["9","12","5.4"],["15","12","5.4"]].forEach(([cx,cy,r])=>{
      const c=document.createElementNS(NS,"circle");
      c.setAttribute("cx",cx); c.setAttribute("cy",cy); c.setAttribute("r",r);
      s.append(c);
    });
    return s;
  }

  const css=document.createElement("style");
  css.textContent=`
/* ══ 页面外壳：这一页很长，靠纵向滚动 ══ */
.hm{position:relative;padding-bottom:calc(30px + env(safe-area-inset-bottom))}
.hm-wrap{max-width:720px;margin:0 auto;padding:0 16px}
/* ── ① 身份栏 ── */
.hm-top{position:sticky;top:0;z-index:6;display:flex;align-items:center;gap:6px;
  padding:calc(8px + env(safe-area-inset-top)) 10px 8px;
  background:var(--glass-bg);
  backdrop-filter:blur(18px) saturate(140%);-webkit-backdrop-filter:blur(18px) saturate(140%);
  border-bottom:1px solid var(--glass-line)}
.hm-top .ib{width:44px;height:44px;display:flex;align-items:center;justify-content:center;
  color:var(--tx-2);border-radius:50%;flex:0 0 44px;
  transition:transform .3s ease,color .3s ease}
.hm-top .ib:hover{color:var(--tx-1)}
.hm-top .ib:active{transform:scale(.94)}
.hm-top .mid{flex:1;min-width:0;display:flex;flex-direction:column;align-items:center;gap:1px;
  background:none;border:0;padding:6px 4px;min-height:44px;justify-content:center}
.hm-top .mid b{font-family:var(--latin);font-size:13px;font-weight:400;letter-spacing:.32em;
  color:var(--tx-1)}
.hm-top .mid span{font-family:var(--latin);font-size:9px;letter-spacing:.24em;color:var(--latin-c)}
.hm-top .mid:active{transform:scale(.98)}

/* ── 通用玻璃卡 ── */
.hm-card{position:relative;z-index:1;
  background:var(--glass-bg);
  backdrop-filter:blur(18px) saturate(140%);-webkit-backdrop-filter:blur(18px) saturate(140%);
  border:1px solid var(--glass-line);border-radius:24px;
  box-shadow:0 10px 24px rgba(70,100,130,.10);
  transition:transform .3s ease,box-shadow .3s ease}
.hm-card.tap{cursor:pointer}
@media (hover:hover){.hm-card.tap:hover{transform:translateY(-2px);
  box-shadow:0 16px 32px rgba(70,100,130,.16)}}
.hm-card.tap:active{transform:scale(.98)}

/* ── 卡片之间的细线：像用线挂着一串纸片 ── */
.hm-thread{position:relative;z-index:0;display:flex;flex-direction:column;align-items:center;
  height:34px;margin:0 auto;pointer-events:none}
.hm-thread .ln{width:.5px;flex:1;background:rgba(110,130,150,.25)}
.hm-thread .nd{width:3px;height:3px;border-radius:50%;background:rgba(110,130,150,.35);flex:0 0 3px}
.hm-thread svg{display:block;flex:1;overflow:visible}

/* ── ② 天数区：大留白 ── */
/* 定稿要的「大留白」：这一块是整页的呼吸口，上下都放宽一点 */
.hm-days{padding:52px 2px 46px}
.hm-days .since{font-family:var(--latin);font-size:10px;letter-spacing:.28em;
  color:var(--tx-3);text-transform:uppercase}
.hm-days .numwrap{position:relative;display:inline-block;margin:8px 0 12px}
.hm-days .num{font-family:var(--font);font-size:88px;font-weight:500;line-height:1;
  color:var(--tx-1);letter-spacing:.01em}
.hm-days .numwrap .sp{position:absolute;top:4px;right:-17px;width:12px;height:12px;
  color:var(--ink-1);opacity:.65}
.hm-days .cap{font-size:15px;color:var(--tx-2);letter-spacing:.08em}

/* ── ③ OUR TIDE ── */
.hm-tide{padding:22px 18px 20px;text-align:center}
.hm-tide .cap{display:flex;align-items:center;justify-content:center;gap:8px;
  font-family:var(--latin);font-size:10px;letter-spacing:.3em;color:var(--latin-c);
  text-transform:uppercase}
.hm-tide .cap .ni{color:var(--ink-1)}
.hm-tide .avs{display:flex;justify-content:center;align-items:center;margin:16px 0 0}
.hm-ava{width:64px;height:64px;border-radius:50%;overflow:hidden;flex:0 0 64px;
  display:flex;align-items:center;justify-content:center;color:var(--ink-1);
  animation:breathe 4s ease-in-out infinite;transform-origin:50% 50%}
.hm-ava.ai{background:rgba(255,255,255,.55);border:1px solid var(--glass-line);
  box-shadow:0 6px 16px rgba(70,100,130,.10)}
.hm-ava.me{background:var(--foam-2,#DCEAF3);border:1px solid rgba(255,255,255,.65);
  margin-left:-16px}
.hm-ava img{width:100%;height:100%;object-fit:cover;display:block}
.hm-tide .rule{width:56px;height:1px;background:rgba(110,130,150,.30);margin:14px auto}
.hm-tide .names{font-family:var(--font);font-size:16px;letter-spacing:.14em;color:var(--tx-1)}
.hm-tide .poem{font-style:italic;font-size:13px;color:var(--ink-1);margin-top:7px;
  letter-spacing:.04em}
.hm-tide .since{font-family:var(--latin);font-size:10px;letter-spacing:.24em;color:var(--tx-3);
  margin-top:9px;text-transform:uppercase}
/* OUR TIDE 下面那两张小卡 */
.hm-pair{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:16px}
.hm-mini{padding:14px 12px;text-align:center}
.hm-mini .k{font-family:var(--latin);font-size:10px;letter-spacing:.24em;color:var(--latin-c);
  text-transform:uppercase}
.hm-mini .v{font-family:var(--font);font-size:22px;color:var(--tx-1);margin-top:8px;
  letter-spacing:.04em}

/* ── ④ 记忆区块 ── */
.hm-mem{padding:18px 0 8px}
.hm-sec-h{display:flex;align-items:center;gap:10px;padding:0 16px;margin-bottom:12px}
.hm-sec-h .ln{width:40px;height:1px;background:rgba(110,130,150,.30);flex:0 0 40px}
.hm-sec-h .en{font-family:var(--latin);font-size:10px;letter-spacing:.26em;color:var(--tx-3);
  text-transform:uppercase}
.hm-sec-h .sp{flex:1}
/* ★ 左右留 12px：手机上 150px 的卡摆两页多一点，右边自然就露出下一张的一角 ——
   这就是「还能往右滑」的暗示（屏幕更宽时露得更多）。 */
.hm-scroll{display:flex;gap:14px;overflow-x:auto;scroll-snap-type:x mandatory;
  padding:2px 12px 14px;scroll-padding-inline:12px;
  -webkit-overflow-scrolling:touch;scrollbar-width:none}
.hm-scroll::-webkit-scrollbar{display:none}
/* 滑到边缘时右边露出下一张的一半 —— 这一条就是「还能滑」的暗示 */
.hm-mcard{flex:0 0 150px;width:150px;height:210px;border-radius:20px;
  background:rgba(110,130,150,.06);scroll-snap-align:start;
  display:flex;flex-direction:column;align-items:center;padding:0 12px 12px;
  overflow:hidden;cursor:pointer;transition:transform .3s ease,background-color .3s ease}
@media (hover:hover){.hm-mcard:hover{transform:translateY(-2px);background:rgba(110,130,150,.10)}}
.hm-mcard:active{transform:scale(.98)}
.hm-mline{width:.5px;background:rgba(110,130,150,.45);flex:0 0 auto}
.hm-mnode{width:7px;height:7px;border-radius:50%;flex:0 0 7px;position:relative;
  border:1px solid rgba(110,130,150,.7)}
.hm-mnode::after{content:"";position:absolute;left:50%;top:50%;width:.8px;height:.8px;
  background:rgba(110,130,150,.7);transform:translate(-50%,-50%)}
.hm-mtxt{display:flex;align-items:flex-start;gap:9px;margin-top:12px;min-height:0;flex:1}
.hm-mtitle{writing-mode:vertical-rl;text-orientation:upright;
  font-family:var(--font);font-size:14px;letter-spacing:.18em;line-height:1.15;
  color:var(--tx-1);max-height:132px;overflow:hidden}
.hm-mmeta{writing-mode:vertical-rl;text-orientation:upright;
  font-family:var(--latin);font-size:9px;letter-spacing:.24em;line-height:1.2;
  color:var(--tx-3);max-height:132px;overflow:hidden}
.hm-mph{padding:22px 18px;font-size:13px;color:var(--tx-2)}

/* ── ⑤ 一起 / ⑥ 日历·书房 / ⑦ 时间线 / ⑧ 空间 ── */
.hm-blk{margin-top:16px;padding:18px}
.hm-blk .hd{display:flex;align-items:center;gap:11px}
.hm-blk .hd .ic{width:44px;height:44px;border-radius:12px;flex:0 0 44px;
  display:flex;align-items:center;justify-content:center;color:var(--ink-1);
  border:1px solid rgba(110,130,150,.22)}
.hm-blk .hd .tt{font-family:var(--font);font-size:17px;letter-spacing:.14em;color:var(--tx-1)}
.hm-blk .hd .sp{flex:1}
.hm-blk .hd .en{font-family:var(--latin);font-size:10px;letter-spacing:.24em;
  color:var(--latin-c);text-transform:uppercase}
.hm-blk .hd .ar{color:var(--tx-3);display:flex}
.hm-blk .sub{font-size:12px;color:var(--tx-2);margin-top:4px;letter-spacing:.04em}
/* 一起：7 个小入口（44×44 图标 + 11px 名字），放不下就换行 */
.hm-grid{display:flex;flex-wrap:wrap;gap:14px 10px;margin-top:16px}
.hm-grid .it{width:52px;display:flex;flex-direction:column;align-items:center;gap:6px;
  background:none;border:0;padding:0;cursor:pointer}
.hm-grid .it .sq{width:44px;height:44px;border-radius:12px;
  border:1px solid rgba(110,130,150,.22);color:var(--ink-1);
  display:flex;align-items:center;justify-content:center;
  transition:transform .3s ease,border-color .3s ease,color .3s ease}
@media (hover:hover){.hm-grid .it:hover .sq{transform:translateY(-2px);color:var(--accent);
  border-color:var(--accent)}}
.hm-grid .it:active .sq{transform:scale(.96)}
.hm-grid .it .nm{font-size:11px;color:var(--tx-2);letter-spacing:.06em;white-space:nowrap}
/* 一行两列 */
.hm-two{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:16px}
.hm-two .hm-blk{margin-top:0;padding:16px}
/* 最新一条 */
.hm-latest{margin-top:14px}
.hm-latest .tt{font-size:15px;line-height:1.8;color:var(--tx-1);
  display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.hm-latest .mt{font-family:var(--latin);font-size:10px;letter-spacing:.2em;color:var(--tx-3);
  margin-top:10px}
.hm-tag{font-family:var(--latin);font-size:10px;letter-spacing:.24em;color:var(--latin-c);
  text-transform:uppercase;margin-bottom:10px}
.hm-empty{font-size:13px;color:var(--tx-3);margin-top:12px}

/* ── 页面切换（比背景快一点的那一层由 pane 管，这里只管内容）── */
@keyframes hmIn{0%{opacity:0;filter:blur(6px);transform:translateY(6px)}
  100%{opacity:1;filter:blur(0);transform:none}}
.hm-in{animation:hmIn 420ms cubic-bezier(.22,.8,.3,1) forwards}
@media (prefers-reduced-motion:reduce){
  .hm-in{animation:hmFade 420ms ease forwards}
  @keyframes hmFade{from{opacity:0}to{opacity:1}}
  .hm-thread .ln,.hm-thread svg{transition:none}
}
`;

  document.head.append(css);

  /* ══ 小零件 ══ */
  /* 卡片之间的细线（直线 / 曲线交替，像挂纸片的那根线） */
  function thread(curved){
    const t=el("div","hm-thread"); t.setAttribute("aria-hidden","true");
    if(!curved){
      t.append(el("i","nd"),el("i","ln"),el("i","nd"));
      return t;
    }
    const s=document.createElementNS(NS,"svg");
    s.setAttribute("viewBox","0 0 40 30"); s.setAttribute("preserveAspectRatio","none");
    s.setAttribute("width","40"); s.setAttribute("height","30");
    const p=document.createElementNS(NS,"path");
    p.setAttribute("d","M20 0 C20 10 8 18 20 30");
    p.setAttribute("fill","none"); p.setAttribute("stroke","rgba(110,130,150,.25)");
    p.setAttribute("stroke-width","0.5"); p.setAttribute("vector-effect","non-scaling-stroke");
    s.append(p); t.append(s);
    return t;
  }
  /* 44×44 的方图标 + 名字 */
  function sqItem(iconName,label,fn){
    const b=el("button","it");
    const sq=el("span","sq"); sq.append(nestIcon(iconName,20));
    b.append(sq,el("span","nm",label));
    b.title=label;
    b.onclick=fn;
    return b;
  }
  /* 「图标 + 标题 + 拉丁小标 + →」那一行 */
  function blockHead(iconName,title,en){
    const hd=el("div","hd");
    const ic=el("span","ic");
    /* 传进来的可以是一个图标名，也可以已经是一个画好的图形（「一起」那两环相扣） */
    if(iconName&&iconName.nodeType)ic.append(iconName);
    else ic.append(nestIcon(iconName,20));
    hd.append(ic,el("span","tt",title),el("span","sp"));
    if(en)hd.append(el("span","en",en));
    const ar=el("span","ar"); ar.append(nestIcon("forward",16));
    hd.append(ar);
    return hd;
  }

  /* ══ 各块的取数 ══ */
  const LAYER_CN={L1:"短期",L2:"长期",L3:"核心",manual:"校准"};
  function dayShort(d){                       /* 2026-10-08 → 10-08 */
    const m=String(d||"").match(/^(\d{4})-(\d{2})-(\d{2})$/);
    return m?(m[2]+"-"+m[3]):String(d||"");
  }
  function sinceShort(d){                     /* 2026-10-23 → 25/10/23 */
    const m=String(d||"").match(/^(\d{4})-(\d{2})-(\d{2})$/);
    return m?(m[1].slice(2)+"/"+m[2]+"/"+m[3]):String(d||"");
  }
  function daysFromHeat(heat){
    const days=Object.keys(heat||{}).filter(d=>/^\d{4}-\d{2}-\d{2}$/.test(d)).sort();
    if(!days.length)return null;
    const first=new Date(days[0]+"T00:00:00");
    const now=new Date();
    const d0=new Date(now.getFullYear(),now.getMonth(),now.getDate());
    return {days:Math.max(1,Math.round((d0-first)/86400000)+1), since:days[0]};
  }

  /* ══ ① 身份栏 ══ */
  function topBar(){
    const bar=el("div","hm-top");
    const bMenu=el("button","ib"); bMenu.title="全部房间与动作";
    bMenu.append(nestIcon("menu",20));
    bMenu.onclick=()=>{ const d=document.getElementById("drawer"); if(d)d.classList.add("open"); };
    /* ★ 中间那颗 HOME：点了就去挑对话窗口 / 开新窗口（保持原来的行为） */
    const bMid=el("button","mid");
    bMid.title="选择对话窗口或开一扇新窗";
    bMid.append(el("b",null,"HOME"),el("span",null,"COMPANION"));
    bMid.onclick=()=>{ if(window.nestOpenThreads)window.nestOpenThreads(); };
    const bGear=el("button","ib"); bGear.title="设置 · 美化 · 主题";
    bGear.append(nestIcon("setting",20));
    bGear.onclick=()=>go("setting");
    bar.append(bMenu,bMid,bGear);
    return bar;
  }

  /* ══ ② 天数区 ══ */
  function daysBlock(info){
    const d=el("div","hm-days");
    d.append(el("div","since",info?("SINCE · "+sinceShort(info.since)):"SINCE"));
    if(info){
      const w=el("div","numwrap");
      w.append(el("div","num",String(info.days)));
      w.append(sparkle(12,"sp"));
      d.append(w);
    }
    d.append(el("div","cap","我们一起走过的日子"));
    return d;
  }

  /* ══ ③ OUR TIDE ══ */
  function avaBox(who,iconName){
    const A=(window.nestIdent&&window.nestIdent.get&&window.nestIdent.get()[who])||{};
    const b=el("div","hm-ava "+(who==="me"?"me":"ai"));
    const u=(A.avatar||"").trim();
    if(/^(\/|https?:|data:image)/i.test(u)){
      const im=el("img"); im.src=u; im.alt="";
      im.onerror=()=>{ b.innerHTML=""; b.append(nestIcon(iconName,26)); };
      b.append(im);
    }else{
      b.append(nestIcon(iconName,26));
    }
    return b;
  }
  function tideCard(info){
    const c=el("div","hm-card hm-tide");
    const cap=el("div","cap");
    cap.append(nestIcon("star",11),document.createTextNode("OUR TIDE"),nestIcon("star",11));
    c.append(cap);
    const avs=el("div","avs");
    avs.append(avaBox("ai","bot"),avaBox("me","person"));
    c.append(avs);
    c.append(el("div","rule"));
    const A=(window.nestIdent&&window.nestIdent.get().ai)||{};
    const M=(window.nestIdent&&window.nestIdent.get().me)||{};
    c.append(el("div","names",(A.name||"他")+" & "+(M.name||"我")));
    c.append(el("div","poem","Love Like Foam Upon the Sea"));
    c.append(el("div","since",info
      ?("since "+info.since+" · "+info.days+" days of tides together")
      :"since the first word you two said"));
    return c;
  }
  function clockPair(){
    const row=el("div","hm-pair");
    const now=new Date();
    const wd=["SUN","MON","TUE","WED","THU","FRI","SAT"][now.getDay()];
    const mo=["JAN","FEB","MAR","APR","MAY","JUN","JUL","AUG","SEP","OCT","NOV","DEC"][now.getMonth()];
    const c1=el("div","hm-card hm-mini");
    c1.append(el("div","k","LOCAL TIME"),
              el("div","v",pad2(now.getHours())+":"+pad2(now.getMinutes())));
    const c2=el("div","hm-card hm-mini");
    c2.append(el("div","k","TODAY"),
              el("div","v",wd+" "+pad2(now.getDate())+" "+mo));
    row.append(c1,c2);
    return row;
  }

  /* ══ ④ 记忆区块：MEMORY INDEX（横向 scroll-snap）══
     线长按 60/100/140/80 循环 —— 一排看过去是错落的。 */
  const LINE_LEN=[60,100,140,80];
  function memCard(it,ord){
    const c=el("div","hm-mcard");
    c.title=String(it.content||"").slice(0,140);
    const line=el("i","hm-mline");
    line.style.height=LINE_LEN[ord%LINE_LEN.length]+"px";
    c.append(line,el("i","hm-mnode"));
    const txt=el("div","hm-mtxt");
    const title=el("div","hm-mtitle");
    title.textContent=String(it.content||"（空的）").replace(/\s+/g," ").trim().slice(0,16);
    txt.append(title);
    const bits=[dayShort(it.day)];
    /* 定稿那行是「10-08 · 关系 · #122」—— 中间那段优先取标签，
       没有标签才退回层级名（短期 / 长期 / 核心 / 校准）。 */
    const tag=String(it.tags||"").split(",").map(x=>x.trim()).filter(Boolean)[0];
    const mid=tag||LAYER_CN[it.layer]||it.layer;
    if(mid)bits.push(mid);
    if(it.id!=null)bits.push("#"+it.id);
    const meta=el("div","hm-mmeta",bits.filter(Boolean).join(" · "));
    txt.append(meta);
    c.append(txt);
    c.onclick=()=>go("memory-detail",it.id);
    return c;
  }
  function memBlock(){
    const c=el("div","hm-card hm-mem");
    const h=el("div","hm-sec-h");
    h.append(el("i","ln"),el("span","en","MEMORY INDEX"),el("span","sp"));
    const more=el("button","ib");
    more.style.cssText="border:0;background:none;color:var(--tx-3);min-height:22px;padding:0 2px;cursor:pointer";
    more.append(nestIcon("forward",14)); more.title="看全部记忆";
    more.onclick=e=>{ e.stopPropagation(); go("memory"); };
    h.append(more);
    const strip=el("div","hm-scroll");
    strip.append(el("div","hm-mph","读取中…"));
    c.append(h,strip);
    jget("/api/memory/all?limit=40").then(j=>{
      const its=((j&&j.items)||[]).slice();
      /* 按天去重：一天只出一条，新的在前 —— 索引是「这条线上有哪些天」 */
      const seen={}, pick=[];
      its.sort((a,b)=>String(b.day||"").localeCompare(String(a.day||""))).forEach(it=>{
        const d=String(it.day||"");
        if(d&&seen[d])return;
        if(d)seen[d]=1;
        if(pick.length<12)pick.push(it);
      });
      strip.innerHTML="";
      if(!pick.length){ strip.append(el("div","hm-mph","这条线上还没有记忆。")); return; }
      pick.forEach((it,i)=>strip.append(memCard(it,i)));
    }).catch(()=>{ strip.innerHTML=""; strip.append(el("div","hm-mph","记忆读不出来。")); });
    return c;
  }

  /* ══ ⑤ 一起区块 ══ */
  const TOGETHER_ITEMS=[
    ["梗库","meme","memes"],["表情包","sticker","sticker"],["健康","health","health"],
    ["收藏","star","star"],["玩具","toy","toys"]
  ];
  function togetherBlock(){
    const c=el("div","hm-card hm-blk tap");
    /* 定稿：左边是**两环相扣**（画出来的，不是字形） */
    c.append(blockHead(rings(22),"一起","TOGETHER"));
    const g=el("div","hm-grid");
    TOGETHER_ITEMS.forEach(([label,icon])=>{
      /* ★ 点小入口 = 进一起页并直接落到那一档 */
      g.append(sqItem(icon,label,()=>go("together",label)));
    });
    c.append(g);
    c.onclick=e=>{ if(e.target.closest(".it"))return; go("together"); };
    return c;
  }

  /* ══ ⑥ 日历 / 书房 ══ */
  function twoCol(){
    const row=el("div","hm-two");
    const cal=el("div","hm-card hm-blk tap");
    cal.append(blockHead("calendar","日历",null));
    cal.append(el("div","sub","纪念日 · 约好的事"));
    cal.onclick=()=>{ if(window.nestNotesOpen)window.nestNotesOpen("日历"); else go("notes"); };
    const st=el("div","hm-card hm-blk tap");
    st.append(blockHead("book","书房",null));
    st.append(el("div","sub","一起做事的房间"));
    st.onclick=()=>go("study");
    row.append(cal,st);
    return row;
  }

  /* ══ ⑦ 时间线区块 ══ */
  function timelineBlock(){
    const c=el("div","hm-card hm-blk tap");
    c.append(blockHead("timeline","时间线","TIMELINE"));
    const box=el("div","hm-latest");
    box.append(el("div","tt","读取中…"));
    c.append(box);
    c.onclick=()=>go("timeline");
    jget("/api/timeline?limit=1").then(j=>{
      const it=((j&&j.items)||[])[0];
      box.innerHTML="";
      if(!it){ box.append(el("div","hm-empty","还没记过。他做了点什么、你顺手记一笔，都会落在这儿。")); return; }
      box.append(el("div","tt",String(it.content||"").slice(0,80)));
      const bits=[dayShort(it.date)];
      if(it.time)bits.push(it.time);
      if(it.kind)bits.push(it.kind);
      box.append(el("div","mt",bits.filter(Boolean).join(" · ")));
    }).catch(()=>{ box.innerHTML=""; box.append(el("div","hm-empty","时间线读不出来。")); });
    return c;
  }

  /* ══ ⑧ 空间区块 ══ */
  function spaceBlock(){
    const c=el("div","hm-card hm-blk tap");
    c.append(el("div","hm-tag","空间 · 最近一条"));
    const box=el("div","hm-latest");
    box.append(el("div","tt","读取中…"));
    c.append(box);
    c.onclick=()=>{ if(window.nestNotesOpen)window.nestNotesOpen("空间"); else go("notes"); };
    jget("/api/moments").then(j=>{
      const it=((j&&j.items)||[])[0];
      box.innerHTML="";
      if(!it){ box.append(el("div","hm-empty","这一面还空着。")); return; }
      box.append(el("div","tt",String(it.content||"").slice(0,120)));
      const bits=[String(it.t||"").slice(0,11)];
      const n=(it.comments||[]).length;
      bits.push(n+" 条评论");
      box.append(el("div","mt",bits.filter(Boolean).join(" · ")));
    }).catch(()=>{ box.innerHTML=""; box.append(el("div","hm-empty","空间读不出来。")); });
    return c;
  }

  /* ══ 组装 ══ */
  window.NEST_PANES=window.NEST_PANES||{};
  window.NEST_PANES.home=async function(box){
    box.innerHTML="";
    const page=el("div","hm");
    const wrap=el("div","hm-wrap hm-in");
    page.append(topBar(),wrap);
    box.append(page);

    /* 先把骨架摆出来（天数那块等 /api/chat/heat 回来再填），
       这样首屏不会是一片「读取中…」 */
    const days=daysBlock(null);
    const tideHolder=el("div");
    wrap.append(days,tideHolder);
    let info=null;
    try{
      const h=await jget("/api/chat/heat");
      info=daysFromHeat((h&&(h.heatmap||h.heat))||{});
    }catch(e){ info=null; }
    /* 天数区：有真记录才写数字（一条都没有就不编一个数出来） */
    const d2=daysBlock(info);
    days.replaceWith(d2);
    tideHolder.append(tideCard(info),clockPair());

    wrap.append(thread(false),memBlock());
    wrap.append(thread(true),togetherBlock());
    wrap.append(thread(false),twoCol());
    wrap.append(thread(true),timelineBlock());
    wrap.append(thread(false),spaceBlock());

    /* 身份读回来之后，把 OUR TIDE 里的头像和名字刷新一遍 */
    if(window.nestIdent&&window.nestIdent.load){
      window.nestIdent.load().then(()=>{
        const t=wrap.querySelector(".hm-tide"); if(!t)return;
        const A=window.nestIdent.get().ai||{},M=window.nestIdent.get().me||{};
        const n=t.querySelector(".names");
        if(n)n.textContent=(A.name||"他")+" & "+(M.name||"我");
        const avs=t.querySelector(".avs");
        if(avs){ avs.innerHTML=""; avs.append(avaBox("ai","bot"),avaBox("me","person")); }
      }).catch(()=>{});
    }
  };

  /* 给别的模块用：那一枚画出来的四角星（界面里不许出现 ✦ 字形） */
  window.nestSparkle=sparkle;
  window.nestRings=rings;
}catch(e){console.error("nest-home:",e);}
})();
