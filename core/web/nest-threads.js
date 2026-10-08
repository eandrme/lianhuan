/* ══════════════════════════════════════════════════════════
   巢 · 对话窗口 v2：窗口列表可删 + 修「重新生成重复用户话」
   装法：nest.html 再加一行 <script src="/nest-threads.js?v=1"></script>
   不改任何旧文件 —— 用捕获点击接管「＋」和「重新生成」
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

  const css=document.createElement("style");
  css.textContent=`
.thr2{display:flex;align-items:center;gap:8px;padding:10px 8px;border-bottom:1px solid var(--line)}
.thr2 .tt{flex:1;min-width:0;font-size:14px;overflow:hidden;text-overflow:ellipsis;
  white-space:nowrap;cursor:pointer}
.thr2 .tn{font-size:11.5px;color:var(--dim2);flex:0 0 auto}
.thr2.on .tt{color:var(--accent)}
`;
  document.head.append(css);

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
                   tools:it.tools,t:hm2(it.ts),ts:it.ts});
      });
      try{toBottom(true);}catch(e){}
    }catch(e){ S.append(el("div","errbox","历史读不出来："+e.message)); }
  }

  /* ── 静默重发：不画用户气泡，也不让它进模型上下文 ── */
  async function sendQuiet(text){
    try{ if(typeof BUSY!=="undefined"&&BUSY){ say("等它把上一句说完"); return; } }catch(e){}
    let L=null;
    try{ L=liveTurn(); }catch(e){ say("页面状态不对，刷新一下再试"); return; }
    try{ if(typeof setBusy==="function")setBusy(true); }catch(e){}
    try{
      await stream("/chat",
        {method:"POST",headers:{"Content-Type":"application/json"},
         body:JSON.stringify({message:text,
           session_id:gSid()==="main"?undefined:gSid(),
           machine:true})},
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
    say("重新生成中 —— 这次不会把你的话再说一遍");
    await sendQuiet(ask);
  }

  /* ── 窗口列表（带删除）── */
  async function openThreads(){
    const wrap=el("div","sheet"), bx=el("div","box");
    const h=el("div","bh"), b=el("b",null,"对话窗口"), x=el("button","x ibtn","✕");
    x.onclick=()=>wrap.remove(); h.append(b,x); bx.append(h); wrap.append(bx);
    wrap.onclick=e=>{if(e.target===wrap)wrap.remove();};
    document.body.append(wrap);

    const nb=el("button",null,"＋ 新对话");
    nb.style.cssText="padding:8px 12px;border:1px solid var(--accent);border-radius:9px;"+
                     "color:var(--accent);margin-bottom:8px";
    nb.onclick=()=>{
      sSid("t"+Date.now().toString(36));
      const S=document.querySelector("#stream"); if(S)S.innerHTML="";
      wrap.remove(); say("开了一个新窗口");
    };
    bx.append(nb);
    const list=el("div"); bx.append(list);
    list.append(el("div","res","读取中…"));
    try{
      const j=await jget("/api/nest/threads");
      list.innerHTML="";
      const its=j.items||[];
      const cur=gSid();
      if(!its.length)list.append(el("div","res","还没有对话"));
      its.forEach(it=>{
        const r=el("div","thr2"+(it.sid===cur?" on":""));
        r.append(el("div","tt",it.title||"（空窗口）"),el("div","tn",it.n+" 条"));
        const dx=el("button","cp","删");
        dx.style.cssText="color:var(--err);border:1px solid var(--err);border-radius:7px;"+
                         "padding:3px 9px;font-size:12px;margin-left:4px";
        dx.onclick=async(e)=>{
          e.stopPropagation();
          if(it.sid==="main"){ say("主窗口是老记录，不给整个删"); return; }
          if(!confirm("删掉这个窗口的全部聊天记录？删了就没了"))return;
          const rr=await jpost("/api/nest/thread/del",{sid:it.sid});
          if(rr.ok){
            r.remove(); say("删了");
            if(it.sid===cur){ sSid("main"); try{await renderThread();}catch(e){} }
          }else say("删不掉："+(rr.err||"?"));
        };
        r.append(dx);
        r.onclick=async()=>{
          sSid(it.sid); try{await renderThread();}catch(e){}
          wrap.remove(); say("切到这个窗口了");
        };
        list.append(r);
      });
    }catch(e){ list.innerHTML=""; list.append(el("div","res","读不出来："+e.message)); }
  }

  /* ── 捕获点击：接管「＋」和「重新生成」── */
  let LASTTURN=null;
  document.addEventListener("click",e=>{
    const t=e.target; if(!t||!t.closest)return;
    const d=t.closest("#stream .dots");
    if(d)LASTTURN=d.closest(".turn");

    const plus=t.closest("#bar .ibtn");
    if(plus&&plus.title==="新对话"){
      e.preventDefault(); e.stopPropagation(); openThreads(); return;
    }
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
