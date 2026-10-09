/* ══════════════════════════════════════════════════════════
   巢 · 导航模块 v1：几个格子 + 多窗口 + 搜索 + MCP 按钮
   装法：nest.html 里，nest-icon.js 那行【下面】再加一行
        <script src="/nest-tabs.js?v=1"></script>
   ══════════════════════════════════════════════════════════ */
(function(){
"use strict";
try{
  const $=(s,r=document)=>r.querySelector(s);
  const el=(t,c,x)=>{const e=document.createElement(t);if(c)e.className=c;if(x!=null)e.textContent=x;return e;};
  const say=t=>{try{if(typeof toast==="function")toast(t);}catch(e){}};
  const jget=async u=>{const r=await fetch(u,{credentials:"same-origin"});if(!r.ok)throw new Error("HTTP "+r.status);return r.json();};
  const hm=ts=>{const d=new Date((ts||0)*1000);const p=n=>String(n).padStart(2,"0");
    return p(d.getMonth()+1)+"-"+p(d.getDate())+" "+p(d.getHours())+":"+p(d.getMinutes());};
  const getSid=()=>{try{return (typeof SID!=="undefined"&&SID)||localStorage.getItem("nest_sid")||"main";}
                    catch(e){return localStorage.getItem("nest_sid")||"main";}};
  const setSid=v=>{v=v||"main";try{if(typeof SID!=="undefined")SID=(v==="main"?"":v);}catch(e){}
                   localStorage.setItem("nest_sid",v==="main"?"":v);};

  const css=document.createElement("style");
  css.textContent=`
#tabs{display:flex;align-items:stretch;padding-bottom:env(safe-area-inset-bottom)}
#tabs button{flex:1;padding:9px 0 10px;display:flex;flex-direction:column;align-items:center;gap:4px;
  color:var(--dim2);transition:color .25s ease,transform .2s ease}
#tabs button .lb{font-size:10.5px;letter-spacing:.14em;font-family:var(--font)}
#tabs button.on{color:var(--accent)}
#tabs button:active{transform:scale(.96)}
/* 正中间给那枚凸起的心留一格缺口：它住在这儿，谁也不挡 */
#tabs .fab-slot{flex:0 0 60px;pointer-events:none}
/* ★ 面板不盖住底部导航：留出它那一格（--nest-tabs-h 是量出来的高度） */
#pane{position:fixed;inset:0 0 var(--nest-tabs-h,0px) 0;z-index:40;
  background:var(--glass-bg);
  backdrop-filter:blur(18px) saturate(140%);-webkit-backdrop-filter:blur(18px) saturate(140%);
  display:flex;flex-direction:column;animation:pageIn 420ms cubic-bezier(.22,.8,.3,1)}
#pane .ph{display:flex;align-items:center;gap:10px;padding:calc(10px + env(safe-area-inset-top)) 14px 10px;
  border-bottom:1px solid var(--line)}
#pane .ph .ic{color:var(--accent)}
#pane .ph .t{font-weight:500;letter-spacing:.1em}
#pane .ph .en{font-family:var(--latin);font-size:10px;letter-spacing:.24em;color:var(--latin-c);
  text-transform:uppercase}
#pane .ph .x{margin-left:auto}
#pane .pb{flex:1;overflow:auto;padding:16px 14px calc(18px + var(--nest-tabs-h,0px))}
.sheet{position:fixed;inset:0;z-index:45;background:rgba(70,100,130,.22);
  backdrop-filter:blur(3px);display:flex;align-items:flex-end;justify-content:center}
.sheet .box{width:min(660px,100%);max-height:76vh;overflow:auto;
  background:var(--glass-bg);backdrop-filter:blur(18px) saturate(140%);
  -webkit-backdrop-filter:blur(18px) saturate(140%);
  border:1px solid var(--glass-line);border-radius:26px 26px 0 0;padding:14px;
  padding-bottom:calc(14px + env(safe-area-inset-bottom));box-shadow:var(--shadow);
  animation:msgIn 320ms cubic-bezier(.22,.8,.3,1)}
.sheet .bh{display:flex;align-items:center;gap:8px;margin-bottom:10px}
.sheet .bh b{font-size:15px;font-weight:500;letter-spacing:.1em}
.sheet .bh .x{margin-left:auto}
.sheet input[type=text]{width:100%;padding:10px 12px;border-radius:14px;border:1px solid var(--glass-line);
  background:var(--glass-bg);color:var(--fg);font:inherit;outline:none;box-sizing:border-box;margin-bottom:8px}
.thr,.res{display:flex;align-items:center;gap:9px;padding:11px 9px;border-bottom:1px solid var(--line);cursor:pointer}
.thr:hover,.res:hover{background:var(--panel2)}
.thr .tt,.res .tt{flex:1;min-width:0;font-size:14.5px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.thr .tn{font-family:var(--latin);font-size:10px;letter-spacing:.24em;color:var(--latin-c);flex:0 0 auto}
.thr.on .tt{color:var(--accent)}
.res{display:block}
.res .k{font-family:var(--latin);font-size:10px;letter-spacing:.24em;color:var(--latin-c);
  text-transform:uppercase;margin-bottom:2px}
.ph-card{border:1px solid var(--glass-line);background:var(--glass-bg);border-radius:var(--r);
  padding:16px;color:var(--dim);box-shadow:var(--shadow)}
.ph-card b{color:var(--fg);font-size:15px;font-weight:500;letter-spacing:.08em}
pre.js{margin:6px 0 0;font:12px/1.5 var(--mono);color:var(--dim);white-space:pre-wrap;word-break:break-all}
`;

  document.head.append(css);

  /* ★ 顺序是定下的：聊天 · 记忆 · 巢 · 书房 · 一起 · 我的。
     「一起」＝记事（日记/碎碎念/心情/日历/梗库/表情包/健康/空间/时间线/收藏）
     ＋ **玩具箱**（他写的小网页）—— 玩具箱不再单独占一格。 */
  const TABS=[["chat","chat","聊天","CHAT"],
              ["memory","tide","记忆","TIDE"],
              ["rooms","nest","巢","NEST"],
              ["study","study","书房","STUDY"],
              ["notes","together","一起","TOGETHER"],
              ["setting","mine","我的","MINE"]];

  const nav=el("nav"); nav.id="tabs";
  TABS.forEach(t=>{
    const b=el("button"); b.dataset.tab=t[0];
    const ic=el("span","ic"); ic.append(nestIcon(t[1],20));
    b.append(ic,el("span","lb",t[2]));
    b.title=t[2]+" · "+t[3];
    b.onclick=()=>{ go(t[0]); };
    nav.append(b);
  });

  /* ★ 六格的正中间挖一个 60px 的缺口（第 3、4 格之间）—— 那枚凸起的心住在这儿。
     不留缺口的话它会正好压住「巢」和「书房」两个字，看得见但点不着。 */
  const slot=el("span"); slot.className="fab-slot";
  nav.insertBefore(slot, nav.children[Math.floor(TABS.length/2)]);

  /* ── 中间那个凸起的圆：开一扇新窗 ──
     从缺口里向上凸起 26px（半个身子在导航条里），心的形状是强调，不是装饰。 */
  const fab=el("button"); fab.id="newChatFab"; fab.title="开一扇新窗";
  fab.append(nestIcon("heart",24));
  fab.onclick=()=>newThread();

  /* ── 抽屉：所有房间 + 所有动作，一个都不藏 ── */
  const drawer=el("div"); drawer.id="drawer";
  const dpanel=el("div","panel");
  const dclose=()=>drawer.classList.remove("open");
  drawer.onclick=e=>{ if(e.target===drawer)dclose(); };
  dpanel.append(el("div","h","ROOMS"));
  TABS.forEach(t=>{
    const b=el("button","room");
    const ic=el("span","ic"); ic.append(nestIcon(t[1],18));
    b.append(ic,el("span",null,t[2]),el("span","sp"),el("span","en",t[3]));
    b.onclick=()=>{ dclose(); go(t[0]); };
    dpanel.append(b);
  });
  const r2=el("div","rule"); dpanel.append(r2,el("div","h","ACTIONS"));
  const acts=el("div"); dpanel.append(acts);
  function drawerBtn(iconName,label,fn,en){
    const b=el("button","room");
    const ic=el("span","ic"); ic.append(nestIcon(iconName,18));
    b.append(ic,el("span",null,label),el("span","sp"));
    if(en)b.append(el("span","en",en));
    b.onclick=()=>{ fn(); };
    acts.append(b);
    return b;
  }
  drawer.append(dpanel); document.body.append(drawer);

  const pane=el("div"); pane.id="pane"; pane.hidden=true;
  const ptitle=el("div","t");
  const pen=el("div","en");
  const picon=el("div","ic");
  const pclose=el("button","x ibtn"); pclose.append(nestIcon("close",19));
  pclose.onclick=()=>go("chat");
  const phead=el("div","ph"); phead.append(picon,ptitle,pen,pclose);
  const pbody=el("div","pb"); pane.append(phead,pbody);

  function go(k){
    [].slice.call(nav.children).forEach(b=>b.classList.toggle("on",b.dataset.tab===k));
    if(k==="chat"){ pane.hidden=true; return; }
    pane.hidden=false;
    const T=TABS.find(x=>x[0]===k)||[];
    ptitle.textContent=T[2]||"";
    pen.textContent=T[3]||"";
    picon.textContent=""; picon.append(nestIcon(T[1]||"dot",18));
    pbody.innerHTML="";
         if(window.NEST_PANES&&window.NEST_PANES[k]){try{window.NEST_PANES[k](pbody);}catch(e){console.error("pane:",e);}return;}
    const info={memory:["记忆库","L1/L2/L3 分层浏览 · 搜索 · 增删改 · 可见性"],
                study:["书房","书架 · 在读进度 · 边读边聊的小窗"],
                notes:["一起","日记 · 碎碎念 · 心情 · 日历 · 梗库 · 表情包 · 健康 · 空间 · 时间线 · 收藏 · 玩具箱"],
                setting:["我的","美化 · MCP 工具包 · 头像 · 消息推送 · 大模型 API · 助手管理"]}[k];
    if(info){
      const c=el("div","ph-card");
      c.append(el("b",null,info[0]),el("div",null,info[1]));
      pbody.append(c);
    }
  }

  function sheet(title,build){
    const wrap=el("div","sheet"), box=el("div","box");
    const h=el("div","bh"), b=el("b",null,title), x=el("button","x ibtn");
    x.append(nestIcon("close",19));
    x.onclick=()=>wrap.remove(); h.append(b,x); box.append(h); wrap.append(box);
    wrap.onclick=e=>{if(e.target===wrap)wrap.remove();};
    document.body.append(wrap); build(box,()=>wrap.remove()); return wrap;
  }
  /* 顶栏不放一排按钮了（手机上挤）—— 这些动作统一进抽屉 */
  function barBtn(iconName,title,fn,label,en){
    return drawerBtn(iconName,label||title,()=>{ dclose(); fn(); },en);
  }

  /* ── 多窗口：一份列表，两处用（抽屉里的速览 sheet ＋「巢」这一格）──
     ★ 每扇窗的两枚开关（主动消息 / 离线模式）就在列表里拨，语义在后端 core/windows.py；
       读不到（老服务端）就画一个「问号」，别拿默认值冒充真值。 */
  async function threadsInto(container, close){
    const bt=el("button","pri");
    bt.style.cssText="display:inline-flex;align-items:center;gap:7px;padding:9px 14px;"
      +"border:1px solid var(--accent);border-radius:14px;color:var(--accent);margin:2px 0 10px";
    bt.append(nestIcon("plus",17),document.createTextNode("新对话"));
    bt.onclick=async()=>{ if(close)close(); newThread(); };
    container.append(bt);
    const list=el("div"); container.append(list);
    list.append(el("div","res","读取中…"));
    let WFLAGS={}, WFLAGS_OK=true;
    try{ const f=await jget("/api/nest/windows"); WFLAGS=(f&&f.items)||{}; }
    catch(e){ WFLAGS={}; WFLAGS_OK=false; }
    try{
      const j=await jget("/api/nest/threads");
      list.innerHTML="";
      const its=j.items||[];
      if(!its.length)list.append(el("div","res","还没有任何对话"));
      its.forEach(it=>{
        const r=el("div","thr"+(it.sid===getSid()?" on":""));
        r.append(el("div","tt",it.title||"（空窗口）"),el("div","tn",it.n+" 条"));
        if(window.nestWinFlags&&window.nestWinFlags.row){
          r.append(window.nestWinFlags.row(it.sid,
                   Object.assign({push:true,offline:true},WFLAGS[it.sid]||{}),WFLAGS_OK));
        }
        r.onclick=async()=>{ setSid(it.sid); await renderThread();
          if(close)close(); say("切到这个窗口了"); };
        list.append(r);
      });
    }catch(e){ list.innerHTML=""; list.append(el("div","res","读不出来："+e.message)); }
  }

  async function openThreads(){
    sheet("对话窗口", async(box,close)=>{ await threadsInto(box, close); });
  }

  /* ── 「巢」这一格：这扇窗现在是什么脾气 ──
     ★ 这一行个头小、要命：nest-tabs 是第一个跑的房间模块，别处的
       `window.NEST_PANES=window.NEST_PANES||{}` 都还没执行 —— 少了它，
       往 undefined 上挂 rooms 会当场抛，**整个导航条（格子/凸起的心/抽屉）都建不起来**。 */
  window.NEST_PANES=window.NEST_PANES||{};
  window.NEST_PANES.rooms=async function(box){
    box.innerHTML="";
    const intro=el("div","hint");
    intro.append(nestIcon("nest",16),document.createTextNode(
      " 一位助手下面可以挂几扇窗。每扇窗有自己的主动消息 / 离线模式开关；"
      +"点一下窗口名字就切过去。"));
    box.append(intro);
    const holder=el("div");
    box.append(holder);
    await threadsInto(holder, null);
  };

  function newThread(){
    setSid("t"+Date.now().toString(36));
    const S=document.querySelector("#stream");
    if(S)S.innerHTML="";
    go("chat"); say("开了一个新窗口 —— 它还记得你们所有事，只是这窗是干净的");
  }
  async function renderThread(){
    const S=document.querySelector("#stream"); if(!S)return;
    const sid=getSid();
    S.innerHTML="";
    try{
      const j=await jget("/api/nest/thread?sid="+encodeURIComponent(sid)+"&limit=120");
      const its=(j.items||[]).filter(x=>(x.role==="user"||x.role==="assistant")&&!x.hidden);
      if(!its.length){
        if(typeof emptyVerse==="function")S.append(emptyVerse("这扇窗还空着"));
        else S.append(el("div","hint","这个窗口还是空的。说点什么吧。"));
      }
      its.forEach(it=>{
        if(typeof addTurn==="function")
          addTurn({id:it.id,role:it.role,content:it.content,think:it.think,
                   tools:it.tools,t:hm(it.ts),ts:it.ts,
                   files:it.files,superseded:it.superseded,starred:it.starred});
      });
      try{toBottom(true);}catch(e){}
    }catch(e){ S.append(el("div","errbox","历史读不出来："+e.message)); }
  }

  /* ── 搜索 ── */
  function openSearch(){
    sheet("搜索聊天与记忆", box=>{
      const i=el("input"); i.type="text"; i.placeholder="打一个词，回车";
      const out=el("div"); box.append(i,out);
      let t=0;
      const run=async()=>{
        const q=i.value.trim(); out.innerHTML="";
        if(!q)return;
        try{
          const j=await jget("/api/search?q="+encodeURIComponent(q));
          const its=j.items||[];
          if(!its.length)out.append(el("div","res","没找到"));
          its.forEach(r=>{
            const d=el("div","res");
            d.append(el("div","k",r.kind||""));
            d.append(el("div","tt",(r.content||"").slice(0,140)));
            d.onclick=async()=>{try{await navigator.clipboard.writeText(r.content||"");say("复制了这一条");}catch(e){}};
            out.append(d);
          });
        }catch(e){ out.append(el("div","res","搜索失败："+e.message)); }
      };
      i.oninput=()=>{clearTimeout(t);t=setTimeout(run,320);};
      i.addEventListener("keydown",e=>{if(e.key==="Enter")run();});
      setTimeout(()=>{try{i.focus();}catch(e){}},60);
    });
  }

  /* ── MCP ── */
  function openMcp(){
    sheet("MCP 工具包", async box=>{
      const out=el("div"); box.append(out); out.append(el("div","res","读取中…"));
      let j;
      try{ j=await jget("/api/mcp"); }
      catch(e){ out.innerHTML=""; out.append(el("div","res","读不出来："+e.message)); return; }
      out.innerHTML="";
      const list=Array.isArray(j)?j:(j.servers||j.items||j.list||null);
      if(Array.isArray(list)&&list.length){
        list.forEach(s=>{
          const nm=(typeof s==="string")?s:(s.name||s.id||s.title||"?");
          let on=(typeof s==="object")?(s.enabled!==false&&s.on!==false):true;
          const tn=el("div","tn",on?"已启用":"已关闭");
          const r=el("div","thr"); r.append(el("div","tt",nm),tn);
          r.onclick=async()=>{
            try{
              const resp=await fetch("/api/mcp/toggle",{method:"POST",credentials:"same-origin",
                headers:{"Content-Type":"application/json"},body:JSON.stringify({name:nm,enabled:!on})});
              // ★ 后端拨失败时回的也是 HTTP 200，只是 body 里 ok:false
              //   —— 只看 resp.ok 的话，没拨成界面照样翻过去，人会以为已经开了。
              let d=null; try{ d=await resp.json(); }catch(_){}
              if(resp.ok&&d&&d.ok!==false){
                on=!on; tn.textContent=on?"已启用":"已关闭"; say(nm+(on?" 开":" 关"));
              }else{
                say("没拨成："+String((d&&d.err)||("HTTP "+resp.status)).slice(0,60));
              }
            }catch(e){ say("切换失败："+String((e&&e.message)||e).slice(0,60)); }
          };
          out.append(r);
        });
      }else{
        out.append(el("div","res","还没登记过。"));
      }
      /* 这一格只管拨开关；加/删/改在设置页那一节（那边才是总管理） */
      const bar=el("button",null,"＋ 加一个 / 管理");
      bar.style.cssText="padding:8px 12px;border:1px solid var(--accent);border-radius:9px;"+
                        "color:var(--accent);margin-top:8px";
      bar.onclick=()=>{
        const wrap=out.closest(".sheet"); if(wrap)wrap.remove();
        if(typeof window.nestOpenMcpManager==="function")window.nestOpenMcpManager();
        else say("去 设置 › MCP 工具包");
      };
      out.append(bar);
    });
  }

  /* ── 挂上去 ── */
  const col=document.querySelector("#chatCol");
  if(col)col.append(nav); else document.body.append(nav);
  /* ★ 心挂进**导航条里**（nav 是 position:relative 的），不再 fixed 到屏幕上 ——
     它跟着导航条走，永远压在输入框上的那个毛病从结构上就没了。 */
  nav.append(fab);
  document.body.append(pane);
  /* 量出标签栏真正占多高，交给 #pane 让位（含安全区 —— 所以补一次 + 转屏也补） */
  const measure=()=>{
    try{
      const h=nav.getBoundingClientRect().height||0;
      if(h>0)document.documentElement.style.setProperty("--nest-tabs-h",h+"px");
    }catch(e){}
  };
  /* ★ 开局 #app 是 hidden（还没过口令那关）—— 这会儿量出来是 0，量了也白量。
     所以：进站之后补量一次（#app 一显示就量），转屏 / 改窗口大小再量。 */
  const appEl=document.querySelector("#app");
  if(appEl){
    new MutationObserver(()=>{ if(!appEl.hidden)measure(); })
      .observe(appEl,{attributes:true,attributeFilter:["hidden"]});
  }
  measure();
  setTimeout(measure,400);
  window.addEventListener("resize",measure);
  window.addEventListener("orientationchange",()=>setTimeout(measure,300));
  barBtn("plus","新对话",newThread,"新对话","NEW");
  barBtn("window","对话窗口",openThreads,"对话窗口","WINDOWS");
  barBtn("search","搜索历史",openSearch,"搜索聊天与记忆","SEARCH");
  barBtn("mcp","MCP 工具包",openMcp,"MCP 工具包","MCP");
  /* 和纸 / 月光 */
  drawerBtn("moon","换个月光版 / 回到和纸",()=>{
    const on=document.documentElement.getAttribute("data-moon")==="1";
    document.documentElement.setAttribute("data-moon",on?"0":"1");
    try{localStorage.setItem("nest_moon",on?"0":"1");}catch(e){}
    say(on?"回到和纸":"换上月光");
  },"MOON");
  try{
    if(localStorage.getItem("nest_moon")==="1")
      document.documentElement.setAttribute("data-moon","1");
  }catch(e){}
  const bDrawer=document.querySelector("#btnDrawer");
  if(bDrawer)bDrawer.onclick=()=>drawer.classList.add("open");
  go("chat");

  let inited=false;
  function maybeInit(){
    if(inited)return;
    const app=document.querySelector("#app");
    if(app&&!app.hidden){
      inited=true;
      // ★ 这里原来还会调 renderThread() 再画一遍历史。基础那份（nest.html 里的
      //   loadHistory）现在自己会认窗口了，两个画手抢同一块 #stream 会把今天的
      //   消息重出一截、还会抹掉正在流的回复。初次进入只切到「聊天」格；
      //   切窗口时才走 renderThread。
      setTimeout(()=>{ try{ go("chat"); }catch(e){} measure(); },500);
    }
  }
  new MutationObserver(maybeInit).observe(document.body,{attributes:true,subtree:true,attributeFilter:["hidden"]});
  setTimeout(maybeInit,1800);
}catch(e){console.error("nest-tabs:",e);}
})();
