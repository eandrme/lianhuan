/* ══════════════════════════════════════════════════════════
   巢 · 读书小窗 ⑤B
   装法：nest.html 里再加一行 <script src="/nest-bookchat.js?v=1"></script>
   后端：走 /api/books/{bid}/chat（无工具、无 MCP、独立于主聊天）
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

  const css=document.createElement("style");
  css.textContent=`
.bc-fab{position:fixed;right:18px;bottom:88px;z-index:44;width:52px;height:52px;border-radius:50%;
  background:var(--accent);color:var(--nest-me-fg,#10131a);font-size:22px;
  box-shadow:0 8px 22px #0007;display:flex;align-items:center;justify-content:center}
.bc-box{position:fixed;right:16px;bottom:150px;z-index:44;width:min(370px,92vw);height:min(58vh,460px);
  display:flex;flex-direction:column;background:var(--panel);border:1px solid var(--line);
  border-radius:var(--r);box-shadow:0 14px 40px #0009;overflow:hidden}
.bc-head{display:flex;align-items:center;gap:8px;padding:10px 12px;border-bottom:1px solid var(--line)}
.bc-title{flex:1;min-width:0;font-size:13px;color:var(--fg);
  overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.bc-list{flex:1;overflow:auto;padding:10px 12px}
.bc-msg{max-width:88%;padding:8px 11px;border-radius:var(--r-sm);margin:0 0 8px;
  font-size:14px;white-space:pre-wrap;word-break:break-word;line-height:1.6}
.bc-msg.user{margin-left:auto;background:var(--accent);color:var(--nest-me-fg,#10131a)}
.bc-msg.assistant{background:var(--panel2);border:1px solid var(--line)}
.bc-msg.thinking{color:var(--dim2);font-style:italic}
.bc-msg.err{background:#e0716f1a;border:1px solid var(--err);color:#f0b3b1;font-size:13px}
.bc-foot{border-top:1px solid var(--line);padding:8px 10px}
.bc-quote{display:flex;gap:6px;align-items:flex-start;background:var(--panel2);border-left:3px solid var(--accent);
  border-radius:6px;padding:6px 8px;font-size:12.5px;color:var(--dim);margin-bottom:7px}
.bc-quote .x{margin-left:auto;color:var(--dim2)}
.bc-qbtn{font-size:12.5px;color:var(--dim);padding:2px 6px;border-radius:6px;margin-bottom:6px}
.bc-qbtn:hover{background:var(--panel2);color:var(--fg)}
.bc-row{display:flex;gap:7px;align-items:flex-end}
.bc-row textarea{flex:1;resize:none;background:var(--panel2);border:1px solid var(--line);
  border-radius:var(--r-sm);color:var(--fg);font:inherit;font-size:14px;padding:8px 10px;
  outline:none;max-height:30vh}
.bc-send{padding:9px 14px;border-radius:var(--r-sm);background:var(--accent);
  color:var(--nest-me-fg,#10131a);font-weight:600;font-size:14px}
@media(max-width:520px){.bc-box{right:8px;left:8px;width:auto;bottom:140px;height:60vh}}
`;
  document.head.append(css);

  let cur=null, box=null, listEl=null, ta=null, titleEl=null, busy=false, quote="", lastSel="";

  document.addEventListener("selectionchange",()=>{
    try{ const s=(window.getSelection().toString()||"").trim(); if(s)lastSel=s.slice(0,300); }catch(e){}
  });

  const fab=el("button","bc-fab","💬");
  fab.title="读书小窗";
  fab.hidden=true;
  fab.onclick=()=>{ if(box&&!box.hidden){box.hidden=true;} else openWin(); };
  document.body.append(fab);

  function build(){
    box=el("div","bc-box"); box.hidden=true;
    const h=el("div","bc-head");
    titleEl=el("div","bc-title","读书小窗");
    const x=el("button","ibtn","✕"); x.onclick=()=>{box.hidden=true;};
    h.append(titleEl,x);
    listEl=el("div","bc-list");
    const foot=el("div","bc-foot");
    const quoteEl=el("div","bc-quote"); quoteEl.hidden=true; quoteEl.dataset.role="quote";
    const qbtn=el("button","bc-qbtn","📌 引用刚才选中的文字");
    qbtn.onclick=()=>{
      if(!lastSel){ say("先在正文里用手指选一段字"); return; }
      quote=lastSel; drawQuote();
    };
    const row=el("div","bc-row");
    ta=el("textarea"); ta.rows=1; ta.placeholder="跟它聊聊这本书…";
    ta.addEventListener("input",grow);
    ta.addEventListener("keydown",e=>{
      if(e.key==="Enter"&&!e.shiftKey&&!e.isComposing){e.preventDefault();send();}
    });
    const s=el("button","bc-send","→"); s.onclick=send;
    row.append(ta,s);
    foot.append(quoteEl,qbtn,row);
    box.append(h,listEl,foot);
    box._quote=quoteEl;
    document.body.append(box);
  }
  function drawQuote(){
    if(!box)return;
    const q=box._quote;
    q.innerHTML="";
    if(!quote){ q.hidden=true; return; }
    q.hidden=false;
    q.append(el("span",null,"「"+quote.slice(0,80)+(quote.length>80?"…":"")+"」"));
    const x=el("button","x","✕"); x.onclick=()=>{quote="";drawQuote();};
    q.append(x);
  }
  function grow(){ if(!ta)return; ta.style.height="auto"; ta.style.height=Math.min(ta.scrollHeight,innerHeight*0.3)+"px"; }

  function addMsg(role,text){
    const d=el("div","bc-msg "+role,text);
    listEl.append(d); listEl.scrollTop=listEl.scrollHeight;
    return d;
  }

  async function currentBook(){
    try{
      const j=await jget("/api/books");
      return (j.items||[]).find(x=>x.current)||null;
    }catch(e){ return null; }
  }

  async function openWin(){
    if(!box)build();
    box.hidden=false;
    const b=await currentBook();
    if(!b){ cur=null; titleEl.textContent="读书小窗"; listEl.innerHTML="";
      listEl.append(el("div","hint","先在书架点开一本书，再回来聊")); return; }
    cur=b;
    titleEl.textContent="读书小窗 · "+(b.title||"")+" · 第 "+((b.my_idx||0)+1)+" 章";
    await loadChat();
  }

  async function loadChat(){
    listEl.innerHTML=""; listEl.append(el("div","hint","读着…"));
    try{
      const j=await jget("/api/books/"+cur.bid+"/chat");
      listEl.innerHTML="";
      const its=j.items||[];
      if(!its.length)listEl.append(el("div","hint","还没聊过这本书。说点什么？"));
      its.forEach(m=>addMsg(m.role==="user"?"user":"assistant",m.content));
      listEl.scrollTop=listEl.scrollHeight;
    }catch(e){ listEl.innerHTML=""; listEl.append(el("div","hint","读不出来："+e.message)); }
  }

  async function send(){
    if(!cur||busy)return;
    const t=(ta.value||"").trim(); if(!t)return;
    const full=quote?("「"+quote+"」\n\n"+t):t;
    ta.value=""; grow();
    addMsg("user",t);
    quote=""; drawQuote();
    busy=true;
    const th=addMsg("thinking","它在想…");
    try{
      const r=await jpost("/api/books/"+cur.bid+"/chat",{message:full});
      th.remove();
      if(r.ok)addMsg("assistant",r.reply||"");
      else addMsg("err","没接上话："+(r.err||"?"));
    }catch(e){ th.remove(); addMsg("err","断了："+e.message); }
    busy=false;
    listEl.scrollTop=listEl.scrollHeight;
  }

  /* 只在书房里露头 */
  setInterval(()=>{
    const pane=document.querySelector("#pane");
    const on=document.querySelector("#tabs button.on");
    const inStudy=pane&&!pane.hidden&&on&&on.dataset.tab==="study";
    fab.hidden=!inStudy;
    if(!inStudy&&box)box.hidden=true;
  },700);
}catch(e){console.error("nest-bookchat:",e);}
})();
