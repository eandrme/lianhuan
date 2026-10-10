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
  const LAYER_CN={L1:"短期",L2:"长期",L3:"核心",manual:"校准"};

  const css=document.createElement("style");
  css.textContent=`
.mem-bar{display:flex;gap:8px;align-items:center;margin-bottom:10px}
/* 输入框 / 卡片 / 按钮的**材质**统一由 nest-skin2.js 那一层压上去，这里只说形状：
   卡片是玻璃、按钮是 1px 青灰描边（选中态才 accent）、进度条只有 1px。 */
.mem-bar input{flex:1;min-width:0;padding:9px 11px;border-radius:14px;border:1px solid var(--glass-line);
  background:var(--glass-bg);color:var(--fg);font:inherit;outline:none;box-sizing:border-box;
  backdrop-filter:blur(18px) saturate(140%);-webkit-backdrop-filter:blur(18px) saturate(140%)}
.mem-bar button{padding:9px 12px;border-radius:10px;border:1px solid var(--ink-1);color:var(--accent);white-space:nowrap;font-size:13.5px}
.mem-chips{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:12px}
.mem-chips button{padding:6px 11px;border-radius:10px;border:1px solid var(--ink-1);
  background:transparent;font-size:13px;color:var(--dim)}
.mem-chips button.on{border-color:var(--accent);color:var(--accent)}
.mem-card{border:1px solid var(--glass-line);background:var(--glass-bg);border-radius:var(--r);padding:12px;margin-bottom:9px;
  backdrop-filter:blur(18px) saturate(140%);-webkit-backdrop-filter:blur(18px) saturate(140%);box-shadow:var(--shadow)}
.mem-card .txt{white-space:pre-wrap;word-break:break-word;font-size:14.5px;line-height:1.8}
.mem-card .meta{display:flex;gap:8px;align-items:center;margin-top:10px;font-size:10px;
  letter-spacing:.14em;color:var(--tx-3);flex-wrap:wrap}
.mem-card .tag{background:transparent;border:1px solid var(--line);border-radius:6px;padding:1px 6px}
.mem-card .ops{margin-left:auto;display:flex;gap:6px}
.mem-card .ops button{padding:4px 10px;border-radius:8px;border:1px solid var(--ink-1);font-size:12px;color:var(--dim)}
.mem-card .ops button.danger{color:var(--err);border-color:var(--err)}
.mem-edit textarea{width:100%;min-height:96px;padding:10px 11px;border-radius:14px;border:1px solid var(--glass-line);
  background:var(--glass-bg);color:var(--fg);font:inherit;outline:none;box-sizing:border-box;resize:vertical}
.mem-edit select,.mem-edit input{width:100%;padding:9px 10px;margin-top:7px;border-radius:14px;
  border:1px solid var(--glass-line);background:var(--glass-bg);color:var(--fg);font:inherit;outline:none;box-sizing:border-box}
.mem-edit .row{display:flex;gap:6px;margin-top:10px}
.mem-edit .row button{flex:1;padding:10px;border-radius:10px;border:1px solid var(--ink-1);
  background:transparent;color:var(--fg);font:inherit}
.mem-edit .row button.pri{border-color:var(--accent);color:var(--accent);background:transparent;font-weight:500}
/* ── 记忆详情（从主界面的 MEMORY INDEX 点进来）── */
.md-wrap{max-width:720px;margin:0 auto}
.md-card{position:relative;padding:22px 20px 18px;border-radius:24px;
  background:var(--glass-bg);
  backdrop-filter:blur(18px) saturate(140%);-webkit-backdrop-filter:blur(18px) saturate(140%);
  border:1px solid var(--glass-line);box-shadow:0 10px 24px rgba(70,100,130,.10)}
/* 顶上垂下来那条线 + 节点：跟首页索引里那张卡是同一个记号 */
.md-drop{display:flex;flex-direction:column;align-items:center;margin:-22px 0 16px}
.md-drop .ln{width:.5px;height:52px;background:rgba(110,130,150,.45)}
.md-drop .nd{width:7px;height:7px;border-radius:50%;position:relative;
  border:1px solid rgba(110,130,150,.7);background:var(--paper)}
.md-drop .nd::after{content:"";position:absolute;left:50%;top:50%;width:.8px;height:.8px;
  background:rgba(110,130,150,.7);transform:translate(-50%,-50%)}
.md-txt{font-family:var(--font);font-size:15px;line-height:1.8;color:var(--tx-1);
  white-space:pre-wrap;word-break:break-word}
.md-rule{width:56px;height:1px;background:rgba(110,130,150,.30);margin:18px 0}
.md-meta{display:flex;flex-wrap:wrap;gap:8px 14px;align-items:center}
.md-meta .k{font-family:var(--latin);font-size:10px;letter-spacing:.24em;color:var(--latin-c);
  text-transform:uppercase}
.md-meta .tag{border:1px solid rgba(110,130,150,.30);border-radius:8px;padding:2px 8px;
  font-size:11px;color:var(--tx-2)}
.md-ops{display:flex;gap:10px;margin-top:20px}
.md-ops button{flex:1;min-height:44px;border-radius:12px;border:1px solid var(--ink-1);
  background:transparent;color:var(--tx-2);font:inherit;font-size:14px;cursor:pointer;
  transition:transform .3s ease,border-color .3s ease,color .3s ease}
.md-ops button:hover{color:var(--accent);border-color:var(--accent)}
.md-ops button:active{transform:scale(.98)}
.md-ops button.danger:hover{color:var(--err);border-color:var(--err)}
.md-hint{font-size:13px;color:var(--tx-2);margin-top:14px}
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

  /* ═══ 记忆详情 ═══
     主界面 MEMORY INDEX 里点一张卡就进这儿（go("memory-detail", id)）。
     同一套语言：一条垂线 + 节点、玻璃卡、细横线、拉丁小标。 */
  window.NEST_PANES["memory-detail"]=async function(box,id){
    box.innerHTML="";
    const wrap=el("div","md-wrap");
    wrap.append(window.nestPageHead
      ? window.nestPageHead({title:"记忆",en:"MEMORY",right:[{icon:"edit",title:"改这一条",onclick:()=>edit()}]})
      : el("div"));
    const card=el("div","md-card");
    const drop=el("div","md-drop");
    drop.append(el("i","ln"),el("i","nd"));
    card.append(drop);
    const body=el("div");
    card.append(body);
    wrap.append(card);
    box.append(wrap);

    let it=null;
    body.append(el("div","md-hint","读取中…"));
    try{
      const j=await jget("/api/memory/all?limit=500");
      it=((j&&j.items)||[]).filter(x=>String(x.id)===String(id))[0]||null;
    }catch(e){ it=null; }
    if(!it){
      body.innerHTML="";
      body.append(el("div","md-hint","这条记忆找不到了 —— 可能刚被删掉。"));
      return;
    }
    draw();

    function draw(){
      body.innerHTML="";
      body.append(el("div","md-txt",it.content||""));
      body.append(el("div","md-rule"));
      const m=el("div","md-meta");
      m.append(el("span","k",it.day||""));
      if(it.layer)m.append(el("span","tag",(LAYER_CN[it.layer]||it.layer)+" · "+it.layer));
      String(it.tags||"").split(",").filter(Boolean).forEach(t=>m.append(el("span","tag",t)));
      m.append(el("span","k","#"+it.id));
      body.append(m);
      const ops=el("div","md-ops");
      const bEdit=el("button",null,"改这一条");
      const bDel=el("button","danger","删掉");
      const bBack=el("button",null,"回到主界面");
      bEdit.onclick=()=>edit();
      bDel.onclick=async()=>{
        if(!confirm("删掉这条记忆？删了就没了"))return;
        const r=await jpost("/api/memory/del",{id:it.id});
        if(r.ok){ say("删了"); if(window.nestGo)window.nestGo("home"); }
        else say("删不掉："+(r.err||"?"));
      };
      bBack.onclick=()=>{ if(window.nestGo)window.nestGo("home"); };
      ops.append(bEdit,bDel,bBack);
      body.append(ops);
    }
    function edit(){
      body.innerHTML="";
      const ta=el("textarea"); ta.value=it.content||"";
      const sel=el("select");
      LAYERS.slice(1).forEach(p=>{
        const o=el("option",null,p[1]+"（"+p[0]+"）"); o.value=p[0];
        if(p[0]===it.layer)o.selected=true;
        sel.append(o);
      });
      const tg=el("input"); tg.type="text"; tg.placeholder="标签，逗号隔开"; tg.value=it.tags||"";
      ta.style.cssText="width:100%;min-height:140px;padding:12px;border-radius:14px;"+
        "border:1px solid var(--glass-line);background:var(--glass-bg);color:var(--fg);"+
        "font:inherit;font-size:16px;line-height:1.8;outline:none;box-sizing:border-box;resize:vertical";
      [sel,tg].forEach(x=>{ x.style.cssText="width:100%;margin-top:10px;padding:10px 12px;"+
        "border-radius:14px;border:1px solid var(--glass-line);background:var(--glass-bg);"+
        "color:var(--fg);font:inherit;font-size:16px;outline:none;box-sizing:border-box"; });
      const ops=el("div","md-ops");
      const ok=el("button",null,"存下");
      const no=el("button",null,"算了");
      ops.append(ok,no);
      body.append(ta,sel,tg,ops);
      no.onclick=draw;
      ok.onclick=async()=>{
        const content=ta.value.trim();
        if(!content){ say("内容不能为空"); return; }
        const tags=JSON.stringify(tg.value.split(/[,，]/).map(s=>s.trim()).filter(Boolean));
        ok.textContent="存…"; ok.disabled=true;
        const r=await jpost("/api/memory/save",{id:it.id,content:content,layer:sel.value,tags:tags});
        ok.textContent="存下"; ok.disabled=false;
        if(r.ok){ it.content=content; it.layer=sel.value; it.tags=tags; say("改好了"); draw(); }
        else say("没存上："+(r.err||"?"));
      };
    }
  };
}catch(e){console.error("nest-memory:",e);}
})();
