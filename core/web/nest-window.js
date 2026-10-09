/* ══════════════════════════════════════════════════════════
   巢 · 窗口开关 v2：每一个对话窗口的「主动消息 / 离线模式」
   装法：nest.html 里，nest-files.js 那行【下面】再加一行
        <script src="/nest-window.js?v=1"></script>

   语义（后端 core/windows.py 一个地方定义，别在这儿另说一套）：
     · 每扇窗各两枚开关，默认都开。
     · 主动消息：关掉＝**别在这个窗口里主动找我**。
     · 离线模式：关掉＝这扇窗名下不给它自己那段时间。
     · 书房小窗**不在其列** —— 那是纯粹的读书助手，走 book_chat，跟这儿无关。

   v2 修的两件事（都是真机上撞出来的）：
     ① 切了窗口之后，读不到服务端就把**上一扇窗**的状态画到这一扇上 ——
        看着就像「关了一个，另一个也跟着关」。现在读不到就画「未知」并且说实话，
        绝不用上一扇窗的数字冒充这一扇的。
     ② 只看回包的 body、不看 HTTP 状态码：老服务端回 404 {"error":"没有这个东西"}，
        没有 ok 字段，于是被当成「存上了」，界面翻过去、其实一个字没落库。
        现在状态码不对就是失败，并且直说「服务端可能是旧的，重启一下再用」。

   放了两处：聊天顶栏（当前这扇窗）和「对话窗口」列表里每一行。
   ══════════════════════════════════════════════════════════ */
(function(){
"use strict";
try{
  const $=(s,r=document)=>r.querySelector(s);
  const el=(t,c,x)=>{const e=document.createElement(t);if(c)e.className=c;if(x!=null)e.textContent=x;return e;};
  const say=t=>{try{if(typeof toast==="function")toast(t);}catch(e){}};
  const jget=async u=>{
    let r;
    try{ r=await fetch(u,{credentials:"same-origin"}); }
    catch(e){ throw new Error("连不上服务器"); }   // 网络层就失败了（DNS/连不上/断网）
    if(!r.ok)throw new Error(r.status===404?"服务端没有这个接口（HTTP 404）"
      :(r.status===401?"登录过期了（HTTP 401）":"HTTP "+r.status));
    return r.json();
  };
  /* 读不到要分清是**哪一种** —— 网络不通和服务端是旧版本，该让人做的事
     完全不一样（一个去查地址/网络，一个去重启服务端）。混成一句话，
     会把人往错的方向支使半天。 */
  const WHY_TEXT={
    net:"连不上服务端 —— 查一下地址和网络（这一条不是版本问题）",
    old:"服务端是旧版本，没有这两枚开关的接口 —— 重启一下 core.server",
    auth:"登录过期了 —— 重新进一次",
    other:"读不到服务端"
  };
  const whyKind=why=>/连不上服务器/.test(why)?"net"
    :(/404/.test(why)?"old":(/401/.test(why)?"auth":"other"));
  const jpost=async(u,b)=>{
    let r;
    try{
      r=await fetch(u,{method:"POST",credentials:"same-origin",
        headers:{"Content-Type":"application/json"},body:JSON.stringify(b||{})});
    }catch(e){ return {ok:false,err:"连不上服务器"}; }
    let d=null; try{ d=await r.json(); }catch(e){}
    // 状态码不对＝没成。老服务端回 404 的 {"error":"…"} 里没有 ok 字段，
    //   只判 `d.ok!==false` 会把它当成功 —— 界面翻了，库里一个字没有。
    if(!r.ok||!d||d.ok===false){
      const why=(d&&(d.err||d.error))||("HTTP "+r.status);
      return {ok:false,status:r.status,err:why};
    }
    return d;
  };
  const gSid=()=>{
    try{ return (typeof SID!=="undefined"&&SID)||localStorage.getItem("nest_sid")||"main"; }
    catch(e){ return localStorage.getItem("nest_sid")||"main"; }
  };

  const META={
    push:{
      label:"主动消息", on:"bell", off:"bell",
      hint:"它想你了会在这个窗口里凑过来说一句（还要总闸「耳语频率」不为 0、"
          +"引擎不是回声那种桩）",
      off_hint:"这个窗口里它不会主动开口"
    },
    offline:{
      label:"离线模式", on:"moon", off:"sun",
      hint:"你久不在的时候，它可以在这扇窗名下有一段自己的时间",
      off_hint:"这扇窗名下不给它自己那段时间"
    }
  };
  const KEYS=["push","offline"];

  /* 图标：清掉按钮原来的内容，再塞一枚自绘细线图标（名字见 META） */
  const putIcon=(host,name,size)=>{
    if(!host||typeof nestIcon!=="function")return;
    host.textContent="";
    host.append(nestIcon(name,size));
  };

  const css=document.createElement("style");
  css.textContent=`
#winFlags{display:flex;gap:3px;align-items:center;margin-left:2px}
.wf{width:30px;height:30px;border-radius:9px;font-size:15px;line-height:1;
  display:flex;align-items:center;justify-content:center;color:var(--dim);
  border:1px solid transparent;transition:.15s}
.wf:hover{background:var(--panel2)}
.wf[data-on="1"]{border-color:var(--line);background:var(--panel2)}
.wf[data-on="0"]{opacity:.5}
.wf[data-on="?"]{opacity:.75;color:var(--warn);border-color:var(--warn);border-style:dashed}
.wf-row{display:flex;gap:4px;flex:0 0 auto}
.wf-mini{display:flex;align-items:center;gap:3px;font-size:11px;padding:3px 7px;
  border-radius:8px;border:1px solid var(--line);color:var(--dim2);white-space:nowrap}
.wf-mini[data-on="1"]{border-color:var(--accent);color:var(--accent)}
.wf-mini[data-on="0"]{opacity:.55}
.wf-mini[data-on="?"]{opacity:.75;color:var(--warn);border-color:var(--warn);border-style:dashed}
`;
  document.head.append(css);

  /* 当前这扇窗的两枚开关（顶栏用）
     known=false = 服务端的真值没读到。这时画「未知」，**绝不用别的窗口的数冒充**。 */
  let cur={push:true,offline:true}, curSid=null, busy=false, known=true, why="", warned=false;
  const btns={};

  const tip=(k)=>{
    if(!known)return META[k].label+"："+WHY_TEXT[whyKind(why)]+"（"+why+"）";
    const on=!!cur[k];
    return META[k].label+"（这个窗口）·"+(on?"开":"关")+"："+(on?META[k].hint:META[k].off_hint)
      +"　—— 点一下"+(on?"关掉":"打开");
  };

  function paintBar(){
    KEYS.forEach(k=>{
      const b=btns[k]; if(!b)return;
      b.dataset.k=k;
      if(!known){
        b.dataset.on="?";
        putIcon(b,"warn");
      }else{
        b.dataset.on=cur[k]?"1":"0";
        putIcon(b,cur[k]?META[k].on:META[k].off);
      }
      b.title=tip(k);
      b.setAttribute("aria-label",b.title);
    });
  }

  /* 读不到时说实话，但只说一次，别每 800 毫秒念一遍 */
  function warnOnce(){
    if(warned)return;
    warned=true;
    say("读不到服务端的窗口开关 —— "+WHY_TEXT[whyKind(why)]+"（"+why+"）");
  }

  async function load(force){
    const sid=gSid();
    if(!force&&sid===curSid&&known)return;
    curSid=sid;
    reportFocus(sid);
    try{
      const j=await jget("/api/nest/window?sid="+encodeURIComponent(sid));
      if(j&&j.ok!==false){
        cur={push:j.push!==false,offline:j.offline!==false};
        known=true; why="";
      }else{
        known=false; why=(j&&(j.err||j.error))||"回了个看不懂的东西";
        cur={push:true,offline:true};
        warnOnce();
      }
    }catch(e){
      // 读不到就退回默认值 + 「未知」，**不保留上一扇窗的状态** ——
      //   「关了一个，另一个也跟着关」就是这么来的。
      known=false;
      why=String((e&&e.message)||e);
      cur={push:true,offline:true};
      warnOnce();
    }
    paintBar();
  }

  /* 告诉后端「我现在停在这扇窗」—— 那两枚开关才真的按这一扇算。
     报不上来（老服务端）也不影响别的：后端会退回按最后说话的地方猜。 */
  let focusSent=null;
  function reportFocus(sid){
    if(focusSent===sid)return;
    focusSent=sid;
    jpost("/api/nest/focus",{sid:sid}).catch(()=>{});
  }

  async function set(sid,k,want){
    if(busy)return false;
    busy=true;
    let ok=false;
    try{
      const w=await jpost("/api/nest/window",Object.assign({sid:sid}, {[k]:want}));
      if(w&&w.ok!==false){
        ok=true; known=true; why="";
        if(sid===curSid||sid===(curSid||gSid())){ cur[k]=want; paintBar(); }
        say(META[k].label+(want?"开了":"关了")
            +(want?"":("（"+((sid==="main")?"主窗口":sid)+"）")));
        if(want&&k==="offline")checkOfflineMaster();
        if(want&&k==="push")checkPushMaster();
      }else{
        const msg=String((w&&w.err)||"?");
        if(w&&w.status===404){
          known=false; paintBar(); warnOnce();
        }else say("没拨动："+msg.slice(0,60));
      }
    }catch(e){ say("没拨动："+String((e&&e.message)||e).slice(0,60)); }
    busy=false;
    return ok;
  }

  /* 说实话：这扇窗拨开了，但「耳语频率」那把总闸还是 0 ——
     它照样一句都不会主动说。不说的话，人会以为这枚开关是坏的。 */
  async function checkPushMaster(){
    try{
      const j=await jget("/api/whisper_freq");
      if(Number(j&&j.level||0)<=0){
        say("这个窗口记下了；但总闸「耳语频率」现在是 0，它暂时不会真的开口");
      }
    }catch(e){}
  }

  /* 同样说实话：总闸开着、这扇窗也开着，但引擎还是回声那种桩 ——
     它不会主动开口（回了也只是把机器诊断当话发出去）。 */
  async function checkOfflineMaster(){
    try{
      const j=await jget("/api/offline");
      if(j&&j.enabled===false){
        say("这个窗口记下了；但服务端总闸（OFFLINE_ENABLED）没开，暂时不会有它自己的一段时间");
      }else if(j&&j.engine_ok===false){
        say("这个窗口记下了；但现在的引擎是回声那种桩，它暂时不会有自己的一段时间");
      }
    }catch(e){}
  }

  /* ── 顶栏：插在窗口名旁边（在那组按钮左边）── */
  const bar=$("#bar");
  if(bar){
    const wrap=el("div"); wrap.id="winFlags";
    KEYS.forEach(k=>{
      const b=el("button","wf");
      b.onclick=e=>{ e.stopPropagation(); set(gSid(),k,!cur[k]); };
      btns[k]=b; wrap.append(b);
    });
    const sp=bar.querySelector(".sp");
    if(sp)bar.insertBefore(wrap,sp); else bar.append(wrap);
    paintBar();
    /* 切窗口：别处只改 localStorage，没有事件 —— 轻量轮询一下就好（读盘，不联网） */
    setInterval(()=>{ if(gSid()!==curSid)load(); },800);
    /* 刚进页面时口令还没登录，这一问会 401 —— 门一开（#app 露出来）重读一遍真值 */
    const app=$("#app");
    if(app){
      new MutationObserver(()=>{ if(!app.hidden)load(true); })
        .observe(app,{attributes:true,attributeFilter:["hidden"]});
      if(!app.hidden)load(true);
    }
    load();
  }

  /* ── 给「对话窗口」列表用的：一行的两枚小开关 ── */
  function row(sid,state,stateKnown){
    const kn=(stateKnown!==false);
    const w=el("div","wf-row");
    KEYS.forEach(k=>{
      const on=(state&&state[k]!==false);
      const b=el("button","wf-mini");
      b.dataset.k=k;
      if(kn){
        b.dataset.on=on?"1":"0";
        const ic=el("span"); ic.append(nestIcon(on?META[k].on:META[k].off));
        b.append(ic,el("span",null,META[k].label.slice(0,2)));
      }else{
        b.dataset.on="?";
        const ic=el("span"); ic.append(nestIcon("warn"));
        b.append(ic,el("span",null,META[k].label.slice(0,2)));
      }
      b.title=kn
        ? (META[k].label+"（这扇窗）·"+(on?"开":"关")+"　点一下"+(on?"关掉":"打开"))
        : (META[k].label+"："+WHY_TEXT[whyKind(why)]);
      b.onclick=async e=>{
        e.stopPropagation();
        const now=!(b.dataset.on==="1");
        if(await set(sid,k,now)){
          b.dataset.on=now?"1":"0";
          putIcon(b.firstChild,now?META[k].on:META[k].off);
        }
      };
      w.append(b);
    });
    return w;
  }

  window.nestWinFlags={
    reload:()=>load(true),
    current:()=>({sid:curSid||gSid(),known:known,push:!!cur.push,offline:!!cur.offline}),
    row:row
  };
}catch(e){console.error("nest-window:",e);}
})();
