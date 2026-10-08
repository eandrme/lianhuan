/* ══════════════════════════════════════════════════════════
   巢 · 窗口开关 v1：每一个对话窗口的「主动消息 / 离线模式」
   装法：nest.html 里，nest-files.js 那行【下面】再加一行
        <script src="/nest-window.js?v=1"></script>

   语义（后端 core/windows.py 一个地方定义，别在这儿另说一套）：
     · 每扇窗各两枚开关，默认都开。
     · 主动消息：关掉＝**别在这个窗口里主动找我**。它只会往「你最近待的那扇窗」
       说话，所以关掉你最近这扇，它就是安静下来。
     · 离线模式：关掉＝你最近待的这扇窗名下，不给它自己那段时间。
     · 书房小窗**不在其列** —— 那是纯粹的读书助手，走 book_chat，跟这儿无关。

   放了两处：聊天顶栏（当前这扇窗）＋「对话窗口」列表里每一行。
   ══════════════════════════════════════════════════════════ */
(function(){
"use strict";
try{
  const $=(s,r=document)=>r.querySelector(s);
  const el=(t,c,x)=>{const e=document.createElement(t);if(c)e.className=c;if(x!=null)e.textContent=x;return e;};
  const say=t=>{try{if(typeof toast==="function")toast(t);}catch(e){}};
  const jget=async u=>{const r=await fetch(u,{credentials:"same-origin"});if(!r.ok)throw new Error("HTTP "+r.status);return r.json();};
  const jpost=async(u,b)=>{
    const r=await fetch(u,{method:"POST",credentials:"same-origin",
      headers:{"Content-Type":"application/json"},body:JSON.stringify(b||{})});
    try{return await r.json();}catch(e){return {ok:false,err:"HTTP "+r.status};}
  };
  const gSid=()=>{
    try{ return (typeof SID!=="undefined"&&SID)||localStorage.getItem("nest_sid")||"main"; }
    catch(e){ return localStorage.getItem("nest_sid")||"main"; }
  };

  const META={
    push:{
      label:"主动消息", on:"🔔", off:"🔕",
      hint:"它想你了会在这个窗口里凑过来说一句（还要总闸「耳语频率」不为 0）",
      off_hint:"这个窗口里它不会主动开口"
    },
    offline:{
      label:"离线模式", on:"🌙", off:"☀️",
      hint:"你久不在的时候，它可以在这扇窗名下有一段自己的时间",
      off_hint:"这扇窗名下不给它自己那段时间"
    }
  };
  const KEYS=["push","offline"];

  const css=document.createElement("style");
  css.textContent=`
#winFlags{display:flex;gap:3px;align-items:center;margin-left:2px}
.wf{width:30px;height:30px;border-radius:9px;font-size:15px;line-height:1;
  display:flex;align-items:center;justify-content:center;color:var(--dim);
  border:1px solid transparent;transition:.15s}
.wf:hover{background:var(--panel2)}
.wf[data-on="1"]{border-color:var(--line);background:var(--panel2)}
.wf[data-on="0"]{opacity:.5}
.wf-row{display:flex;gap:4px;flex:0 0 auto}
.wf-mini{display:flex;align-items:center;gap:3px;font-size:11px;padding:3px 7px;
  border-radius:8px;border:1px solid var(--line);color:var(--dim2);white-space:nowrap}
.wf-mini[data-on="1"]{border-color:var(--accent);color:var(--accent)}
.wf-mini[data-on="0"]{opacity:.55}
`;
  document.head.append(css);

  /* 当前这扇窗的两枚开关（顶栏用） */
  let cur={push:true,offline:true}, curSid=null, busy=false;
  const btns={};

  function paintBar(){
    KEYS.forEach(k=>{
      const b=btns[k]; if(!b)return;
      const on=!!cur[k];
      b.dataset.on=on?"1":"0";
      b.dataset.k=k;
      b.textContent=on?META[k].on:META[k].off;
      b.title=META[k].label+"（这个窗口）·"+(on?"开":"关")+"："+(on?META[k].hint:META[k].off_hint)
              +"　—— 点一下"+(on?"关掉":"打开");
      b.setAttribute("aria-label",b.title);
    });
  }

  async function load(force){
    const sid=gSid();
    if(!force&&sid===curSid)return;
    curSid=sid;
    try{
      const j=await jget("/api/nest/window?sid="+encodeURIComponent(sid));
      if(j&&j.ok!==false)cur={push:j.push!==false,offline:j.offline!==false};
    }catch(e){ /* 读不出来就按默认「开」画 —— 按钮不能因为一次网络抖动消失 */ }
    paintBar();
  }

  async function set(sid,k,want){
    if(busy)return false;
    busy=true;
    let ok=false;
    try{
      const w=await jpost("/api/nest/window",Object.assign({sid:sid}, {[k]:want}));
      if(w&&w.ok!==false){
        ok=true;
        if(sid===curSid||sid===(curSid||gSid())){ cur[k]=want; paintBar(); }
        say(META[k].label+(want?"开了":"关了")
            +(want?"":("（"+((sid==="main")?"主窗口":sid)+"）")));
        if(want&&k==="offline")checkOfflineMaster();
        if(want&&k==="push")checkPushMaster();
      }else say("没拨动："+((w&&w.err)||"?"));
    }catch(e){ say("没拨动："+String((e&&e.message)||e).slice(0,60)); }
    busy=false;
    return ok;
  }

  /* ★ 同样说实话：这扇窗拨开了，但「耳语频率」那把总闸还是 0 ——
     它照样一句都不会主动说。不说的话，人会以为这枚开关是坏的。 */
  async function checkPushMaster(){
    try{
      const j=await jget("/api/whisper_freq");
      if(Number(j&&j.level||0)<=0){
        say("这个窗口记下了；但总闸「耳语频率」现在是 0，它暂时不会真的开口");
      }
    }catch(e){}
  }

  /* ★ 说实话：这扇窗拨开了，但服务端那把总闸（OFFLINE_ENABLED）没开 ——
     那就暂时不会有它自己那段时间。不说的话人会以为开关坏了。 */
  async function checkOfflineMaster(){
    try{
      const j=await jget("/api/offline");
      if(j&&j.enabled===false){
        say("这个窗口记下了；但服务端总闸（OFFLINE_ENABLED）没开，暂时不会有它自己的一段时间");
      }
    }catch(e){}
  }

  /* ── 顶栏：插在窗口名旁边（在 🐞＋🔍🔧 那一组左边）── */
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
    /* 切窗口：别处只改 localStorage，没有事件 —— 轻量轮询一下就好（一次读盘，不联网） */
    setInterval(()=>{ if(gSid()!==curSid)load(); },800);
    /* 刚进页面时口令还没登录，这一问会 401 —— 门一开（#app 露出来）重读一遍真值，
       不然关过的开关会在顶栏上骗人地显示成「开」。 */
    const app=$("#app");
    if(app){
      new MutationObserver(()=>{ if(!app.hidden)load(true); })
        .observe(app,{attributes:true,attributeFilter:["hidden"]});
      if(!app.hidden)load(true);
    }
    load();
  }

  /* ── 给「对话窗口」列表用的：一行的两枚小开关 ── */
  function row(sid,state){
    const w=el("div","wf-row");
    KEYS.forEach(k=>{
      const on=(state&&state[k]!==false);
      const b=el("button","wf-mini");
      b.dataset.on=on?"1":"0";
      b.dataset.k=k;
      b.append(el("span",null,on?META[k].on:META[k].off),el("span",null,META[k].label.slice(0,2)));
      b.title=META[k].label+"（这扇窗）·"+(on?"开":"关")+"　点一下"+(on?"关掉":"打开");
      b.onclick=async e=>{
        e.stopPropagation();
        const now=!(b.dataset.on==="1");
        if(await set(sid,k,now)){ b.dataset.on=now?"1":"0"; state[k]=now;
          b.firstChild.textContent=now?META[k].on:META[k].off; }
      };
      w.append(b);
    });
    return w;
  }

  window.nestWinFlags={
    reload:()=>load(true),
    current:()=>({sid:curSid||gSid(),push:!!cur.push,offline:!!cur.offline}),
    row:row
  };
}catch(e){console.error("nest-window:",e);}
})();
