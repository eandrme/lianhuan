/* ══════════════════════════════════════════════════════════
   巢 · 对话窗口 v2：修「重新生成重复用户话」+（原）窗口列表
   装法：nest.html 再加一行 <script src="/nest-threads.js?v=1"></script>

   现在这儿只剩一件事：接管「⋯ › 重新生成」，保证**你的话只发一遍**、
   旧的那条不再记得它。
   窗口列表（含删除按钮）统一在 nest-tabs.js 的 threadsInto()。
   ══════════════════════════════════════════════════════════ */
(function(){
"use strict";
try{
  const el=(t,c,x)=>{const e=document.createElement(t);if(c)e.className=c;if(x!=null)e.textContent=x;return e;};
  const say=t=>{try{if(typeof toast==="function")toast(t);}catch(e){}};
  const jget=async u=>{const r=await fetch(u,{credentials:"same-origin"});if(!r.ok)throw new Error("HTTP "+r.status);return r.json();};
  const jpost=async(u,b)=>{
    const r=await fetch(u,{method:"POST",credentials:"same-origin",
      headers:{"Content-Type":"application/json"},body:JSON.stringify(b||{})});
    try{return await r.json();}catch(e){return {ok:false,err:"HTTP "+r.status};}
  };
  const pad=n=>String(n).padStart(2,"0");
  const hm2=ts=>{const d=new Date((ts||0)*1000);
    return pad(d.getMonth()+1)+"-"+pad(d.getDate())+" "+pad(d.getHours())+":"+pad(d.getMinutes());};
  const gSid=()=>{
    try{ return (typeof SID!=="undefined"&&SID)||localStorage.getItem("nest_sid")||"main"; }
    catch(e){ return localStorage.getItem("nest_sid")||"main"; }
  };
  const sSid=v=>{
    v=v||"main";
    try{ if(typeof SID!=="undefined") SID=(v==="main"?"":v); }catch(e){}
    localStorage.setItem("nest_sid",v==="main"?"":v);
  };
  const turnText=w=>[...w.querySelectorAll(":scope > .bubbles > .bubble")]
                     .map(b=>b.textContent).join("|||");

  /* ── 重画某个窗口的历史 ── */
  async function renderThread(){
    const S=document.querySelector("#stream"); if(!S)return;
    S.innerHTML="";
    try{
      const j=await jget("/api/nest/thread?sid="+encodeURIComponent(gSid())+"&limit=120");
      const its=(j.items||[]).filter(x=>(x.role==="user"||x.role==="assistant")&&!x.hidden);
      if(!its.length)S.append(el("div","hint","这个窗口还是空的。说点什么吧。"));
      its.forEach(it=>{
        if(typeof addTurn==="function")
          addTurn({id:it.id,role:it.role,content:it.content,think:it.think,
                   tools:it.tools,t:hm2(it.ts),ts:it.ts,
                   files:it.files,superseded:it.superseded,starred:it.starred});
      });
      try{toBottom(true);}catch(e){}
    }catch(e){ S.append(el("div","errbox","历史读不出来："+e.message)); }
  }

  /* ── 静默重发：不画用户气泡，也不让那句重复进模型上下文 ── */
  async function sendQuiet(text, regenOf){
    try{ if(typeof BUSY!=="undefined"&&BUSY){ say("等它把上一句说完"); return; } }catch(e){}
    let L=null;
    try{ L=liveTurn(); }catch(e){ say("页面状态不对，刷新一下再试"); return; }
    try{ if(typeof setBusy==="function")setBusy(true); }catch(e){}
    try{
      await stream("/chat",
        {method:"POST",headers:{"Content-Type":"application/json"},
         body:JSON.stringify({message:text,
           session_id:gSid()==="main"?undefined:gSid(),
           machine:true,
           // 这条 id 是关键：后端靠它把上文切到「用户那句话之前」，
           //   并把这条旧回复折起来（见 core/server.py 里那段注释）。
           //   不带的话就是老毛病：同一句话进模型两遍，旧答案也还在。
           regen_of:regenOf||undefined})},
        ev=>handle(ev,L));
    }catch(e){
      if(String(e.message)!=="unauthorized"){
        try{ L.bs.append(el("div","errbox","断了："+e.message)); }catch(_){}
      }
    }
    try{ if(typeof setBusy==="function")setBusy(false); }catch(e){}
    try{ settle(L); }catch(e){}
    try{ toBottom(); }catch(e){}
  }

  async function regen(w){
    if(!w){ say("没找到要重新生成的那条"); return; }
    let p=w.previousElementSibling;
    while(p&&!p.classList.contains("me"))p=p.previousElementSibling;
    if(!p){ say("找不到它回应的那句话"); return; }
    const ask=turnText(p).split("|||").join("\n");
    if(!ask){ say("那句话是空的"); return; }
    /* 先问出「要被换掉的这条回复」在库里是第几行。
       问不出来就别硬来 —— 硬来的话后端拿不到 id，又会把你那句话发两遍、
       旧答案也留在它脑子里，等于白点一次。 */
    let rid=0;
    if(typeof window.nestEnsureId==="function"){
      try{ if(await window.nestEnsureId(w)) rid=Number(w.dataset.id)||0; }catch(e){}
      if(!rid){ say("这条还没落库，等它说完再来"); return; }
    }
    say("重新生成中 —— 你的话只发一遍，旧的那条它不再记得");
    await sendQuiet(ask, rid);
  }

  /* ── 捕获点击：接管「重新生成」──
     ★ 窗口列表（含「删」那颗按钮）已经统一到 nest-tabs.js 的 threadsInto() ——
       抽屉 / 主界面中间那颗 HOME / 「巢」那一格走的都是它。
       这里原来还有一份自己的列表，后来它的入口（#bar 上那颗「新对话」）没了，
       就成了够不着的死代码，两份还会越走越不一样 —— 一并删了。 */
  let LASTTURN=null;
  document.addEventListener("click",e=>{
    const t=e.target; if(!t||!t.closest)return;
    const d=t.closest("#stream .dots");
    if(d)LASTTURN=d.closest(".turn");

    const rb=t.closest(".menu button");
    if(rb&&(rb.textContent||"").trim()==="重新生成"){
      e.preventDefault(); e.stopPropagation();
      document.querySelectorAll(".menu").forEach(m=>m.remove());
      regen(LASTTURN);
      return;
    }
  },true);
}catch(e){console.error("nest-threads:",e);}
})();
