/* ══════════════════════════════════════════════════════════
   巢 · 导航模块 v2：视图路由 + 多窗口 + 搜索 + MCP

   装法：nest.html 里，nest-icon.js 那行【下面】再加一行
        <script src="/nest-tabs.js?v=1"></script>

   ★ v2 起**没有底部导航条了**（用户定的：主界面把入口全部平铺出来，
     靠点卡片进子页）。原来那排六格 + 正中间凸起的心一并撤掉。
     `TABS` 这张表留着 —— 它现在是**视图注册表**（id / 图标 / 中文名 / 拉丁名），
     抽屉、「我的」里的跳转、以及图标设置都读它。

   对外只暴露两样东西给别的模块用：
     window.nestGo(k)   跳到一个视图（'chat' 就是回到聊天）
     window.nestView()  现在是哪个视图
   ══════════════════════════════════════════════════════════ */
(function(){
"use strict";
try{
  const $=(s,r=document)=>r.querySelector(s);
  const el=(t,c,x)=>{const e=document.createElement(t);if(c)e.className=c;if(x!=null)e.textContent=x;return e;};
  const say=t=>{try{if(typeof toast==="function")toast(t);}catch(e){}};
  const jget=async u=>{const r=await fetch(u,{credentials:"same-origin"});if(!r.ok)throw new Error("HTTP "+r.status);return r.json();};
  /* ★ 只看 body 不看状态码是不行的：老服务端回 404 {"error":"…"} 里没有 ok 字段，
     会被当成功 —— 界面翻了，库里一个字没动。状态码不对就是没成。 */
  const jpost=async(u,b)=>{
    let r;
    try{
      r=await fetch(u,{method:"POST",credentials:"same-origin",
        headers:{"Content-Type":"application/json"},body:JSON.stringify(b||{})});
    }catch(e){ return {ok:false,err:"连不上服务器"}; }
    let d=null; try{ d=await r.json(); }catch(e){}
    if(!r.ok||!d||d.ok===false)
      return {ok:false,status:r.status,err:(d&&(d.err||d.error))||("HTTP "+r.status)};
    return d;
  };
  const hm=ts=>{const d=new Date((ts||0)*1000);const p=n=>String(n).padStart(2,"0");
    return p(d.getMonth()+1)+"-"+p(d.getDate())+" "+p(d.getHours())+":"+p(d.getMinutes());};
  const getSid=()=>{try{return (typeof SID!=="undefined"&&SID)||localStorage.getItem("nest_sid")||"main";}
                    catch(e){return localStorage.getItem("nest_sid")||"main";}};
  const setSid=v=>{v=v||"main";try{if(typeof SID!=="undefined")SID=(v==="main"?"":v);}catch(e){}
                   localStorage.setItem("nest_sid",v==="main"?"":v);};

  const css=document.createElement("style");
  css.textContent=`
/* ── 视图容器 ──
   ★ 没有底部导航条了，所以铺满整屏（原来底下要让出一格 --nest-tabs-h）。
     内容自己带安全区留白，见 .pb 的 padding。 */
#pane{position:fixed;inset:0;z-index:40;
  /* ★ 必须**有底**：视图只是盖在聊天上面的一层，底要是透明的，
     底下那套 #chatCol（顶栏 / 消息流 / 输入框）会整个透出来。
     用和纸色带一点透 —— 既盖得住聊天，又还看得见纸纹和墨晕。 */
  background:color-mix(in srgb,var(--paper) 92%,transparent);
  display:flex;flex-direction:column;animation:pageIn 420ms cubic-bezier(.22,.8,.3,1)}
/* 子页自己那条顶栏（返回 / 标题 / 拉丁小标 / 右侧动作） */
#pane .ph{display:flex;align-items:center;gap:10px;
  padding:calc(12px + env(safe-area-inset-top)) 16px 12px;
  background:var(--glass-bg);
  backdrop-filter:blur(18px) saturate(140%);-webkit-backdrop-filter:blur(18px) saturate(140%);
  border-bottom:1px solid var(--glass-line)}
#pane .ph .ic{color:var(--ink-1);display:flex}
#pane .ph .t{font-family:var(--font);font-weight:500;font-size:20px;letter-spacing:.15em;color:var(--tx-1)}
#pane .ph .en{font-family:var(--latin);font-size:10px;letter-spacing:.24em;color:var(--latin-c);
  text-transform:uppercase}
#pane .ph .x{margin-left:auto}
#pane .ph .back,#pane .ph .x{width:44px;height:44px;display:flex;align-items:center;justify-content:center;
  color:var(--tx-2);margin-left:-10px}
#pane .ph .back:active,#pane .ph .x:active{transform:scale(.94)}
#pane .ph .x{margin-left:auto;margin-right:-10px}
#pane .pb{flex:1;overflow:auto;-webkit-overflow-scrolling:touch;
  padding:18px 16px calc(28px + env(safe-area-inset-bottom))}
/* 主界面自己管顶栏和留白，不要再套一层 */
#pane .pb.bare{padding:0}
/* ── 首页那张顶栏（☰ · HOME · ⚙）── */
#pane .ph.home{padding:calc(10px + env(safe-area-inset-top)) 12px 10px;
  border-bottom:1px solid transparent}
#pane .ph.home .mid{flex:1;text-align:center;display:flex;flex-direction:column;align-items:center;gap:1px}
#pane .ph.home .mid b{font-family:var(--latin);font-size:13px;letter-spacing:.32em;color:var(--tx-1);
  font-weight:400}
#pane .ph.home .mid span{font-family:var(--latin);font-size:9px;letter-spacing:.24em;color:var(--latin-c)}
#pane .ph.home .ibtn{width:44px;height:44px;display:flex;align-items:center;justify-content:center;
  color:var(--tx-2);border-radius:50%}
#pane .ph.home .ibtn:active{transform:scale(.94);background:var(--panel2)}
/* ── 弹层（对话窗口 / 搜索 / MCP …）── */
.sheet{position:fixed;inset:0;z-index:45;background:rgba(70,100,130,.22);
  backdrop-filter:blur(3px);display:flex;align-items:flex-end;justify-content:center}
.sheet .box{width:min(660px,100%);max-height:76vh;overflow:auto;
  background:var(--glass-bg);backdrop-filter:blur(18px) saturate(140%);
  -webkit-backdrop-filter:blur(18px) saturate(140%);
  border:1px solid var(--glass-line);border-radius:24px 24px 0 0;padding:14px;
  padding-bottom:calc(14px + env(safe-area-inset-bottom));box-shadow:var(--shadow);
  animation:msgIn 320ms cubic-bezier(.22,.8,.3,1)}
.sheet .bh{display:flex;align-items:center;gap:8px;margin-bottom:10px}
.sheet .bh b{font-size:15px;font-weight:500;letter-spacing:.1em}
.sheet .bh .x{margin-left:auto;width:44px;height:44px;display:flex;align-items:center;justify-content:center}
.sheet input[type=text]{width:100%;padding:10px 12px;border-radius:14px;border:1px solid var(--glass-line);
  background:var(--glass-bg);color:var(--fg);font:inherit;outline:none;box-sizing:border-box;margin-bottom:8px}
.thr,.res{display:flex;align-items:center;gap:9px;padding:11px 9px;border-bottom:1px solid var(--line);cursor:pointer;
  min-height:44px}
.thr:hover,.res:hover{background:var(--panel2)}
.thr .tt,.res .tt{flex:1;min-width:0;font-size:14.5px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.thr .tn{font-family:var(--latin);font-size:10px;letter-spacing:.24em;color:var(--latin-c);flex:0 0 auto}
.thr.on .tt{color:var(--accent)}
.thr .tt,.res .tt{color:var(--tx-1)}
.res{display:block}
.res .k{font-family:var(--latin);font-size:10px;letter-spacing:.24em;color:var(--latin-c);
  text-transform:uppercase;margin-bottom:2px}
.ph-card{border:1px solid var(--glass-line);background:var(--glass-bg);border-radius:var(--r);
  padding:16px;color:var(--dim);box-shadow:var(--shadow)}
.ph-card b{color:var(--fg);font-size:15px;font-weight:500;letter-spacing:.08em}
pre.js{margin:6px 0 0;font:12px/1.5 var(--mono);color:var(--dim);white-space:pre-wrap;word-break:break-all}
/* 每扇窗右边那颗「删」（44×44 触控目标，线稿垃圾桶） */
.thr .thr-del{width:44px;height:44px;min-width:44px;flex:0 0 44px;display:flex;
  align-items:center;justify-content:center;background:none;border:1px solid transparent;
  border-radius:10px;color:var(--tx-3);cursor:pointer;
  transition:color .3s ease,border-color .3s ease,transform .3s ease}
.thr .thr-del:hover{color:var(--err);border-color:var(--err)}
.thr .thr-del:active{transform:scale(.94)}
.thr .thr-del[disabled]{opacity:.4;cursor:default}
/* 主窗口那条：删不了，就别画成一个能按的样子 */
.thr .thr-del.off{opacity:.35;cursor:default}
.thr .thr-del.off:hover{color:var(--tx-3);border-color:transparent}
/* ── 子页共用顶栏（‹ 返回 / 标题 / 拉丁小标 / 右侧动作）── */
.pg-head{position:sticky;top:0;z-index:6;display:flex;align-items:center;gap:8px;
  padding:calc(8px + env(safe-area-inset-top)) 8px 8px;
  background:var(--glass-bg);
  backdrop-filter:blur(18px) saturate(140%);-webkit-backdrop-filter:blur(18px) saturate(140%);
  border-bottom:1px solid var(--glass-line)}
.pg-back,.pg-act{width:44px;height:44px;min-width:44px;display:flex;align-items:center;
  justify-content:center;color:var(--tx-2);background:none;border:0;cursor:pointer;
  transition:transform .3s ease,color .3s ease}
.pg-back:hover,.pg-act:hover{color:var(--tx-1)}
.pg-back:active,.pg-act:active{transform:scale(.94)}
.pg-act{width:auto;min-width:44px;padding:0 8px;gap:6px;font-size:13px;color:var(--accent)}
.pg-mid{flex:1;min-width:0;display:flex;flex-direction:column;align-items:center;gap:1px}
.pg-mid b{font-family:var(--font);font-weight:500;font-size:20px;letter-spacing:.15em;
  color:var(--tx-1);line-height:1.2}
.pg-en{font-family:var(--latin);font-size:10px;letter-spacing:.24em;color:var(--latin-c);
  text-transform:uppercase}
.pg-sub{font-size:12px;color:var(--tx-2);letter-spacing:.04em}
.pg-right{display:flex;align-items:center;gap:2px;min-width:44px;justify-content:flex-end}

/* ── 页面切换：内容横向淡入 420ms；背景那层慢一点，做出景深 ── */
@keyframes bgShift{
  0%{transform:scale(1.015) translateX(-7px);opacity:.86}
  100%{transform:none;opacity:1}
}
/* 聊天顶栏那颗「回主界面」 */
#bar .ibtn.home{color:var(--tx-2)}
`;

  document.head.append(css);

  /* ★ 视图注册表。顺序是定下的：聊天 · 记忆 · 巢 · 书房 · 一起 · 我的。
     「一起」＝记事（日记/碎碎念/日历/梗库/表情包/健康/空间/时间线/收藏）
     ＋ **玩具箱**（他写的小网页）—— 玩具箱不再单独占一格。
     ★ 主界面（home）不在这张表里：它不是「一格」，是这一页本身。 */
  const TABS=[["chat","chat","聊天","CHAT"],
              ["memory","tide","记忆","TIDE"],
              ["rooms","nest","巢","NEST"],
              ["study","study","书房","STUDY"],
              ["notes","together","一起","TOGETHER"],
              ["setting","mine","我的","MINE"]];

  /* ── 抽屉：所有房间 + 所有动作，一个都不藏 ── */
  const drawer=el("div"); drawer.id="drawer";
  const dpanel=el("div","panel");
  const dclose=()=>drawer.classList.remove("open");
  drawer.onclick=e=>{ if(e.target===drawer)dclose(); };
  /* 第一行永远是「主界面」—— 底部导航条撤了之后，它是唯一的回家路 */
  const HOME_ROW=["home","home","主界面","HOME"];
  dpanel.append(el("div","h","ROOMS"));
  [HOME_ROW].concat(TABS).forEach(t=>{
    const b=el("button","room");
    b.dataset.tab=t[0];
    const ic=el("span","ic"); ic.append(nestIcon(t[1],18));
    b.append(ic,el("span",null,t[2]),el("span","sp"),el("span","en",t[3]));
    b.onclick=()=>{ dclose(); go(t[0]); };
    dpanel.append(b);
  });
  const r2=el("div","rule"); dpanel.append(r2,el("div","h","ACTIONS"));
  const acts=el("div"); dpanel.append(acts);
  function drawerBtn(iconName,label,fn,en){
    const b=el("button","room");
    /* ★ .title 不是装饰：「主界面图标」那一节靠它认按钮（原来在 #bar 上找，
       底部导航条撤了之后这些动作搬进抽屉，找不到了 —— 那三个图标槽就死了）。 */
    b.title=label; b.dataset.act=en||label;
    const ic=el("span","ic"); ic.append(nestIcon(iconName,18));
    b.append(ic,el("span",null,label),el("span","sp"));
    if(en)b.append(el("span","en",en));
    b.onclick=()=>{ fn(); };
    acts.append(b);
    return b;
  }
  drawer.append(dpanel); document.body.append(drawer);

  /* ── 视图容器 ── */
  const pane=el("div"); pane.id="pane"; pane.hidden=true;
  const ptitle=el("div","t");
  const pen=el("div","en");
  const picon=el("div","ic");
  const pclose=el("button","x ibtn"); pclose.append(nestIcon("close",19));
  pclose.title="回到主界面";
  pclose.onclick=()=>go("home");
  /* ★ 默认顶栏也要有一条**返回箭头**（不只是一个 ✕）——
     记忆 / 巢 / 我的这几页用的就是这条顶栏，只有 ✕ 的话
     「回主界面」这件事在手机上看不出来。 */
  const pback=el("button","back ibtn"); pback.append(nestIcon("back",20));
  pback.title="回主界面";
  pback.onclick=()=>go("home");
  const phead=el("div","ph"); phead.append(pback,picon,ptitle,pen,pclose);
  const pbody=el("div","pb"); pane.append(phead,pbody);

  /* ★ 有几个视图自己画顶栏（首页那条 ☰·HOME·⚙、书房的 THE STUDY、
     时间线的「‹ 时间线 TIMELINE 搜索」…）—— 它们不要默认那条。 */
  const BARE={home:1,"memory-detail":1,together:1,study:1,timeline:1};

  /* ★ 视图状态。别的模块要跳转一律走 window.nestGo，
     不要再去找 `#tabs button[data-tab=…]` —— 那排按钮已经不存在了。 */
  let CUR="home";
  const LISTENERS=[];
  function go(k,arg){
    k=k||"home";
    /* 聊天不是「一张面板」—— 它就是把面板收起来，露出底下的 #chatCol */
    if(k==="chat"){ CUR="chat"; pane.hidden=true; }
    else{
      CUR=k;
      pane.hidden=false;
      /* 自己画顶栏的那几个视图，把默认那条藏起来 */
      const bare=!!BARE[k];
      phead.hidden=bare;
      pbody.classList.toggle("bare",bare);
      const T=TABS.find(x=>x[0]===k)||[];
      ptitle.textContent=T[2]||"";
      pen.textContent=T[3]||"";
      picon.textContent=""; picon.append(nestIcon(T[1]||"dot",18));
      pbody.innerHTML="";
      const fn=(window.NEST_PANES&&window.NEST_PANES[k]);
      if(typeof fn==="function"){
        try{ fn(pbody,arg); }
        catch(e){ console.error("pane:",e); pbody.append(el("div","errbox","这一页没画出来："+e.message)); }
      }else{
        const info={memory:["记忆库","L1/L2/L3 分层浏览 · 搜索 · 增删改 · 可见性"],
                    study:["书房","书架 · 在读进度 · 边读边聊的小窗"],
                    notes:["一起","日记 · 碎碎念 · 日历 · 梗库 · 表情包 · 健康 · 空间 · 时间线 · 收藏 · 玩具箱"],
                    setting:["我的","美化 · MCP 工具包 · 头像 · 消息推送 · 大模型 API · 助手管理"]}[k];
        if(info){
          const c=el("div","ph-card");
          c.append(el("b",null,info[0]),el("div",null,info[1]));
          pbody.append(c);
        }
      }
      /* 新开的页面从顶上开始看 */
      try{ pbody.scrollTop=0; }catch(e){}
      /* ★ 切页时把「横向淡入」重跑一遍 —— 面板是同一个元素，
         不重放的话从主界面切到子页是**硬切**，一点过渡都没有。 */
      pane.style.animation="none";
      void pane.offsetWidth;
      pane.style.animation="pageIn 420ms cubic-bezier(.22,.8,.3,1)";
    }
    /* ★ 背景比内容慢一拍（620ms vs 420ms）—— 这一点错位就是「景深」。
       同一个动画要能重跑：先摘掉、强制一次重排、再挂回去。 */
    const bg=document.getElementById("bg");
    if(bg){
      bg.style.animation="none";
      void bg.offsetWidth;
      bg.style.animation="bgShift 620ms cubic-bezier(.22,.8,.3,1)";
    }
    LISTENERS.forEach(f=>{ try{ f(CUR); }catch(e){} });
  }
  window.nestGo=go;
  window.nestView=()=>CUR;
  window.nestOnView=fn=>{ if(typeof fn==="function")LISTENERS.push(fn); };

  /* ── 子页那条顶栏：‹ 返回 · 标题 · 拉丁小标 · 右侧动作 ──
     所有子页共用，省得每个模块各写一套（也保证返回永远回得到主界面）。 */
  function pageHead(o){
    o=o||{};
    const h=el("div","pg-head");
    const back=el("button","pg-back");
    back.append(nestIcon("back",20));
    back.title=o.backTitle||"回主界面";
    back.onclick=()=>go(o.backTo||"home");
    h.append(back);
    const mid=el("div","pg-mid");
    if(o.title)mid.append(el("b",null,o.title));
    if(o.en)mid.append(el("span","pg-en",o.en));
    if(o.sub)mid.append(el("span","pg-sub",o.sub));
    h.append(mid);
    const right=el("div","pg-right");
    (o.right||[]).forEach(r=>{
      const b=el("button","pg-act");
      if(r.icon)b.append(nestIcon(r.icon,19));
      if(r.text)b.append(el("span",null,r.text));
      b.title=r.title||r.text||"";
      b.onclick=r.onclick;
      right.append(b);
    });
    h.append(right);
    return h;
  }
  window.nestPageHead=pageHead;

  function sheet(title,build){
    const wrap=el("div","sheet"), box=el("div","box");
    const h=el("div","bh"), b=el("b",null,title), x=el("button","x ibtn");
    x.append(nestIcon("close",19));
    x.onclick=()=>wrap.remove(); h.append(b,x); box.append(h); wrap.append(box);
    wrap.onclick=e=>{if(e.target===wrap)wrap.remove();};
    document.body.append(wrap); build(box,()=>wrap.remove()); return wrap;
  }
  window.nestSheet=sheet;

  /* ── 多窗口：一份列表，两处用（对话窗口 sheet ＋「巢」这一格）──
     ★ 每扇窗的两枚开关（主动消息 / 离线模式）就在列表里拨，语义在后端 core/windows.py；
       读不到（老服务端）就画一个「问号」，别拿默认值冒充真值。 */
  /* 删一扇窗（连它名下所有聊天记录）。后端也有这道门
     （`POST /api/nest/thread/del`），主窗口它自己也拦着。 */
  async function delThread(it, row, reload){
    if(it.sid==="main"){ say("主窗口是老记录，不能整个删 —— 点进去逐条删可以"); return; }
    if(!confirm("删掉这扇窗的全部聊天记录？\n\n「"+(it.title||"（空窗口）")+"」 · "+it.n+" 条\n\n"
               +"删了就没了（它自己写进记忆/日记的东西不受影响）。")) return;
    const d=await jpost("/api/nest/thread/del",{sid:it.sid});
    if(!d.ok){ say("删不掉："+(d.err||"?")); return; }
    say("删了这扇窗的 "+((d.n!=null)?d.n:it.n)+" 条");
    /* ★ 删的正好是**现在这扇**：退回主窗口。
       不退回的话，会话 id 还指着一扇已经不存在的窗 —— 下一条主动消息
       会拿这个 id 重新落库，那扇窗就**又冒出来了**，人会以为没删掉。 */
    if(it.sid===getSid()){
      setSid("main");
      try{
        await fetch("/api/nest/focus",{method:"POST",credentials:"same-origin",
          headers:{"Content-Type":"application/json"},body:JSON.stringify({sid:"main"})});
      }catch(e){}
      await renderThread();
      say("这扇是当前窗口，已经退回主窗口了");
    }
    await reload();
  }

  async function threadsInto(container, close){
    const bt=el("button","pri");
    bt.style.cssText="display:inline-flex;align-items:center;gap:7px;padding:9px 14px;"
      +"border:1px solid var(--accent);border-radius:12px;color:var(--accent);margin:2px 0 10px";
    bt.append(nestIcon("plus",17),document.createTextNode("新对话"));
    bt.onclick=async()=>{ if(close)close(); newThread(); };
    container.append(bt);
    const list=el("div"); container.append(list);
    let WFLAGS={}, WFLAGS_OK=true;

    async function load(){
      try{ const f=await jget("/api/nest/windows"); WFLAGS=(f&&f.items)||{}; WFLAGS_OK=true; }
      catch(e){ WFLAGS={}; WFLAGS_OK=false; }
      list.innerHTML=""; list.append(el("div","res","读取中…"));
      let its;
      try{ its=((await jget("/api/nest/threads")).items)||[]; }
      catch(e){ list.innerHTML=""; list.append(el("div","res","读不出来："+e.message)); return; }
      list.innerHTML="";
      if(!its.length){ list.append(el("div","res","还没有任何对话")); return; }
      its.forEach(it=>{
        const r=el("div","thr"+(it.sid===getSid()?" on":""));
        r.append(el("div","tt",it.title||"（空窗口）"),el("div","tn",it.n+" 条"));
        if(window.nestWinFlags&&window.nestWinFlags.row){
          r.append(window.nestWinFlags.row(it.sid,
                   Object.assign({push:true,offline:true},WFLAGS[it.sid]||{}),WFLAGS_OK));
        }
        /* ── 删掉这扇窗 ──
           44×44 的触控目标；线稿垃圾桶，不用字形。主窗口画成灰的：
           后端也拦着它，与其点了挨一句拒绝，不如一开始就看得出删不了。 */
        const dx=el("button","thr-del"+(it.sid==="main"?" off":""));
        dx.append(nestIcon("trash",17));
        const dlabel=(it.sid==="main")
          ? "主窗口是老记录，不能整个删（可以进去逐条删）"
          : "删除这扇窗口的全部聊天记录";
        dx.title=dlabel;
        dx.setAttribute("aria-label",dlabel);
        dx.onclick=async(e)=>{
          e.preventDefault(); e.stopPropagation();     // 别顺手把窗口也切过去
          await delThread(it, r, load);
        };
        r.append(dx);
        /* ★ 选了窗就**进聊天**（原来只 renderThread，人还停在主界面上看着没动） */
        r.onclick=async()=>{ setSid(it.sid); go("chat"); await renderThread();
          if(close)close(); say("切到这个窗口了"); };
        list.append(r);
      });
    }
    await load();
  }

  async function openThreads(){
    sheet("对话窗口", async(box,close)=>{ await threadsInto(box, close); });
  }
  window.nestOpenThreads=openThreads;

  /* ── 「巢」这一格：这扇窗现在是什么脾气 ──
     ★ 这一行个头小、要命：nest-tabs 是第一个跑的房间模块，别处的
       `window.NEST_PANES=window.NEST_PANES||{}` 都还没执行 —— 少了它，
       往 undefined 上挂 rooms 会当场抛，整个抽屉 / 首页都建不起来。 */
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
  window.nestNewThread=newThread;
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
  window.nestRenderThread=renderThread;

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
      bar.style.cssText="padding:8px 12px;border:1px solid var(--accent);border-radius:10px;"+
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
  document.body.append(pane);
  /* 聊天顶栏最左边补一颗「回主界面」：底部导航条撤了之后，
     从聊天回首页总得有个看得见的路（抽屉里那条当然也还在）。 */
  const bar=document.querySelector("#bar");
  if(bar){
    const bHome=el("button","ibtn tap home"); bHome.id="btnHome";
    bHome.title="回主界面"; bHome.append(nestIcon("home",19));
    bHome.onclick=()=>go("home");
    bar.insertBefore(bHome,bar.firstChild);
  }
  barBtn("plus","新对话",newThread,"新对话","NEW");
  barBtn("window","对话窗口",openThreads,"对话窗口","WINDOWS");
  barBtn("search","搜索历史",openSearch,"搜索聊天与记忆","SEARCH");
  barBtn("mcp","MCP 工具包",openMcp,"MCP 工具包","MCP");
  function barBtn(iconName,title,fn,label,en){
    return drawerBtn(iconName,label||title,()=>{ dclose(); fn(); },en);
  }
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

  /* 开局先在主界面（口令那关过完 #app 才显示）。
     ★ 必须等一拍：这一行跑的时候 nest-home.js 还没轮到 —— 立刻 go 的话
       NEST_PANES.home 还不存在，会画出一张空的占位卡。 */
  setTimeout(()=>{ try{ go("home"); }catch(e){ console.error("home:",e); } },0);
  let inited=false;
  function maybeInit(){
    if(inited)return;
    const app=document.querySelector("#app");
    if(app&&!app.hidden){
      inited=true;
      // ★ 这里原来还会调 renderThread() 再画一遍历史。基础那份（nest.html 里的
      //   loadHistory）现在自己会认窗口了，两个画手抢同一块 #stream 会把今天的
      //   消息重出一截、还会抹掉正在流的回复。初次进入只切到主界面。
      setTimeout(()=>{ try{ go(CUR||"home"); }catch(e){} },500);
    }
  }
  new MutationObserver(maybeInit).observe(document.body,{attributes:true,subtree:true,attributeFilter:["hidden"]});
  setTimeout(maybeInit,1800);
}catch(e){console.error("nest-tabs:",e);}
})();
