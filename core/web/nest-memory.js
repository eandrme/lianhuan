/* ══════════════════════════════════════════════════════════
   巢 · 记忆页 v1：分层浏览 · 搜索 · 增 / 删 / 改
   装法：nest.html 里最后再加一行
        <script src="/nest-memory.js?v=1"></script>
   可见性开关等「多助手」那批一起上。
   ══════════════════════════════════════════════════════════ */
(function(){
"use strict";
try{
  window.NEST_PANES=window.NEST_PANES||{};
  const el=(t,c,x)=>{const e=document.createElement(t);if(c)e.className=c;if(x!=null)e.textContent=x;return e;};
  const say=t=>{try{if(typeof toast==="function")toast(t);}catch(e){}};
  const jget=async u=>{const r=await fetch(u,{credentials:"same-origin"});if(!r.ok)throw new Error("HTTP "+r.status);return r.json();};
  const jpost=async(u,b)=>{
    const r=await fetch(u,{method:"POST",credentials:"same-origin",
      headers:{"Content-Type":"application/json"},body:JSON.stringify(b||{})});
    try{return await r.json();}catch(e){return {ok:false,err:"HTTP "+r.status};}
  };

  const LAYERS=[["","全部"],["L3","核心"],["L2","长期"],["L1","短期"],["manual","校准"]];

  const css=document.createElement("style");
  css.textContent=`
.mem-bar{display:flex;gap:8px;align-items:center;margin-bottom:10px}
.mem-bar input{flex:1;min-width:0;padding:9px 11px;border-radius:9px;border:1px solid var(--line);
  background:var(--panel2);color:var(--fg);font:inherit;outline:none;box-sizing:border-box}
.mem-bar button{padding:9px 12px;border-radius:9px;border:1px solid var(--accent);color:var(--accent);white-space:nowrap;font-size:13.5px}
.mem-chips{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:12px}
.mem-chips button{padding:6px 11px;border-radius:20px;border:1px solid var(--line);
  background:var(--panel);font-size:13px;color:var(--dim)}
.mem-chips button.on{border-color:var(--accent);color:var(--accent)}
.mem-card{border:1px solid var(--line);background:var(--panel);border-radius:var(--r);padding:12px;margin-bottom:9px}
.mem-card .txt{white-space:pre-wrap;word-break:break-word;font-size:14.5px}
.mem-card .meta{display:flex;gap:8px;align-items:center;margin-top:8px;font-size:11.5px;color:var(--dim2);flex-wrap:wrap}
.mem-card .tag{background:var(--panel2);border-radius:6px;padding:1px 6px}
.mem-card .ops{margin-left:auto;display:flex;gap:6px}
.mem-card .ops button{padding:4px 10px;border-radius:7px;border:1px solid var(--line);font-size:12px;color:var(--dim)}
.mem-card .ops button.danger{color:var(--err);border-color:var(--err)}
.mem-edit textarea{width:100%;min-height:96px;padding:10px 11px;border-radius:9px;border:1px solid var(--line);
  background:var(--panel2);color:var(--fg);font:inherit;outline:none;box-sizing:border-box;resize:vertical}
.mem-edit select,.mem-edit input{width:100%;padding:9px 10px;margin-top:7px;border-radius:8px;
  border:1px solid var(--line);background:var(--panel2);color:var(--fg);font:inherit;outline:none;box-sizing:border-box}
.mem-edit .row{display:flex;gap:6px;margin-top:10px}
.mem-edit .row button{flex:1;padding:10px;border-radius:9px;border:1px solid var(--line);
  background:var(--panel2);color:var(--fg);font:inherit}
.mem-edit .row button.pri{background:var(--accent);color:var(--nest-me-fg,#10131a);border-color:transparent;font-weight:600}
`;
  document.head.append(css);

  window.NEST_PANES.memory=function(box){
    box.innerHTML="";
    const st={layer:"",q:"",items:[]};
    const bar=el("div","mem-bar");
    const qi=el("input"); qi.type="text"; qi.placeholder="在记忆里搜一个词…";
    const add=el("button",null,"＋ 加一条");
    bar.append(qi,add);
    const chips=el("div","mem-chips");
    const list=el("div");
    box.append(bar,chips,list);

    function chips_draw(counts){
      chips.innerHTML="";
      LAYERS.forEach(p=>{
        const n=counts?counts[p[0]]:null;
        const b=el("button",(st.layer===p[0]?"on":""),p[1]+(n!=null?(" "+n):""));
        b.onclick=()=>{st.layer=p[0];load();};
        chips.append(b);
      });
    }
    async function load(){
      try{
        const j=await jget("/api/memory/all?limit=500"+(st.layer?("&layer="+st.layer):""));
        st.items=j.items||[];
      }catch(e){ st.items=[]; say("记忆读不出来："+e.message); }
      try{
        const o=await jget("/api/memory/overview");
        const c={}; c[""]=o.total||0;
        (o.layers||[]).forEach(l=>{c[l.key]=l.count;});
        chips_draw(c);
      }catch(e){ chips_draw(null); }
      draw();
    }
    function draw(){
      const kw=st.q.trim();
      list.innerHTML="";
      const its=st.items.filter(it=>!kw||((it.content||"").indexOf(kw)>=0)||((it.tags||"").indexOf(kw)>=0));
      if(!its.length){ list.append(el("div","hint",kw?"没找到":"这条线上还没有记忆")); return; }
      its.forEach(it=>list.append(card(it)));
    }
    function card(it){
      const c=el("div","mem-card");
      c.append(el("div","txt",it.content||""));
      const m=el("div","meta");
      m.append(el("span",null,it.layer||""));
      m.append(el("span",null,it.day||""));
      String(it.tags||"").split(",").filter(Boolean).forEach(t=>m.append(el("span","tag",t)));
      const ops=el("div","ops");
      const ed=el("button",null,"改");
      const de=el("button","danger","删");
      ed.onclick=()=>{ c.replaceWith(editor(it)); };
      de.onclick=async()=>{
        if(!confirm("删掉这条记忆？删了就没了"))return;
        const r=await jpost("/api/memory/del",{id:it.id});
        if(r.ok){ say("删了"); load(); } else say("删不掉："+(r.err||"?"));
      };
      ops.append(ed,de); m.append(ops); c.append(m);
      return c;
    }
    function editor(it){
      const c=el("div","mem-card mem-edit");
      const ta=el("textarea"); ta.value=(it&&it.content)||"";
      const sel=el("select");
      LAYERS.slice(1).forEach(p=>{const o=el("option",null,p[1]+"（"+p[0]+"）");o.value=p[0];sel.append(o);});
      sel.value=(it&&it.layer)||"L1";
      const tg=el("input"); tg.type="text"; tg.placeholder="标签，逗号隔开";
      tg.value=(it&&it.tags)||"";
      const row=el("div","row");
      const ok=el("button","pri","保存");
      const no=el("button",null,"取消");
      row.append(ok,no);
      c.append(ta,sel,tg,row);
      no.onclick=()=>{ if(it&&it.id)load(); else c.remove(); };
      ok.onclick=async()=>{
        const content=ta.value.trim();
        if(!content){ say("内容不能为空"); return; }
        const tags=JSON.stringify(tg.value.split(/[,，]/).map(s=>s.trim()).filter(Boolean));
        const body={content:content,layer:sel.value,tags:tags};
        if(it&&it.id)body.id=it.id;
        ok.textContent="存…"; ok.disabled=true;
        const r=await jpost("/api/memory/save",body);
        ok.textContent="保存"; ok.disabled=false;
        if(r.ok){ say(it&&it.id?"改好了":"加上了"); load(); }
        else say("没存上："+(r.err||"?"));
      };
      return c;
    }

    qi.oninput=()=>{ st.q=qi.value; draw(); };
    add.onclick=()=>{ list.prepend(editor(null)); qi.blur(); };
    load();
  };
}catch(e){console.error("nest-memory:",e);}
})();
