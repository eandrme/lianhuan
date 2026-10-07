/* ══════════════════════════════════════════════════════════
   巢 · 记事 ⑥-1：日记 + 碎碎念（其余模块逐批接上）
   装法：nest.html 再加一行 <script src="/nest-notes.js?v=1"></script>
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

  const css=document.createElement("style");
  css.textContent=`
.nt-chips{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:12px}
.nt-chips button{padding:6px 12px;border-radius:20px;border:1px solid var(--line);
  background:var(--panel);font-size:13px;color:var(--dim)}
.nt-chips button.on{border-color:var(--accent);color:var(--accent)}
.nt-top{display:flex;gap:7px;align-items:center;margin-bottom:10px}
.nt-top button{padding:7px 11px;border-radius:8px;border:1px solid var(--line);
  background:var(--panel);font-size:13px;color:var(--dim)}
.nt-top button.on{border-color:var(--accent);color:var(--accent)}
.nt-top button.pri{border-color:var(--accent);color:var(--accent)}
.nt-top .sp{flex:1}
.nt-card{border:1px solid var(--line);background:var(--panel);border-radius:var(--r);padding:12px;margin-bottom:9px}
.nt-txt{white-space:pre-wrap;word-break:break-word;font-size:14.5px;line-height:1.75}
.nt-meta{display:flex;gap:8px;align-items:center;margin-top:8px;font-size:11.5px;
  color:var(--dim2);flex-wrap:wrap}
.nt-meta .tag{background:var(--panel2);border-radius:6px;padding:1px 6px}
.nt-ops{margin-left:auto;display:flex;gap:6px}
.nt-ops button{padding:4px 10px;border-radius:7px;border:1px solid var(--line);
  background:none;font-size:12px;color:var(--dim)}
.nt-ops button.danger{color:var(--err);border-color:var(--err)}
.nt-in{width:100%;box-sizing:border-box;padding:9px 11px;border-radius:9px;
  border:1px solid var(--line);background:var(--panel2);color:var(--fg);font:inherit;
  outline:none;margin-top:8px}
.nt-btns{display:flex;gap:6px;margin-top:10px}
.nt-btns button{flex:1;padding:10px;border-radius:9px;border:1px solid var(--line);
  background:var(--panel2);color:var(--fg);font:inherit}
.nt-btns button.pri{background:var(--accent);color:var(--nest-me-fg,#10131a);
  border-color:transparent;font-weight:600}
.nt-sheet textarea{width:100%;min-height:110px;box-sizing:border-box;padding:10px;
  border-radius:9px;border:1px solid var(--line);background:var(--panel2);
  color:var(--fg);font:inherit;outline:none;resize:vertical}
`;
  document.head.append(css);

  function sheet(title,build){
    const wrap=el("div","sheet"), bx=el("div","box nt-sheet");
    const h=el("div","bh"), b=el("b",null,title), x=el("button","x ibtn","✕");
    x.onclick=()=>wrap.remove(); h.append(b,x); bx.append(h); wrap.append(bx);
    wrap.onclick=e=>{if(e.target===wrap)wrap.remove();};
    document.body.append(wrap); build(bx,()=>wrap.remove()); return wrap;
  }

  let SEC="diary", WHO="ai";

  window.NEST_PANES.notes=function(box){
    box.innerHTML="";
    const chips=el("div","nt-chips");
    const body=el("div");
    box.append(chips,body);
    const SECS=[
      ["diary","日记",secDiary],
      ["notes","碎碎念",secNotes],
      ["mood","心情",null],
      ["cal","日历",null],
      ["memes","梗库",null],
      ["sticker","表情包",null],
      ["health","健康",null]
    ];
    SECS.forEach(s=>{
      const b=el("button",(s[0]===SEC?"on":""),s[1]);
      b.onclick=()=>{
        SEC=s[0];
        [].slice.call(chips.children).forEach(x=>x.classList.toggle("on",x===b));
        body.innerHTML="";
        if(s[2])s[2](body); else soon(body,s[1]);
      };
      chips.append(b);
    });
    const cur=SECS.filter(s=>s[0]===SEC)[0]||SECS[0];
    if(cur[2])cur[2](body); else soon(body,cur[1]);
  };

  function soon(body,lb){
    const c=el("div","nt-card");
    c.innerHTML="<b>"+lb+"</b><br>⏳ 这一块正在做，下一批接上。";
    body.append(c);
  }

  /* ═══ 日记 ═══ */
  async function secDiary(body){
    body.innerHTML="";
    const top=el("div","nt-top");
    const t1=el("button",(WHO==="ai"?"on":""),"它写的");
    const t2=el("button",(WHO==="me"?"on":""),"我写的");
    const add=el("button","pri","＋ 写一篇");
    top.append(t1,t2,el("div","sp"),add);
    body.append(top);
    const list=el("div"); body.append(list);
    t1.onclick=()=>{WHO="ai";secDiary(body);};
    t2.onclick=()=>{WHO="me";secDiary(body);};
    add.onclick=()=>editDiary(body,null);
    list.append(el("div","hint","读取中…"));
    try{
      const j=await jget("/api/diary?who="+WHO);
      list.innerHTML="";
      const its=j.items||[];
      if(!its.length)list.append(el("div","hint",WHO==="ai"?"它还没写过日记":"你还没写过日记"));
      its.forEach(d=>{
        const c=el("div","nt-card");
        c.append(el("div","nt-txt",d.content||""));
        const m=el("div","nt-meta");
        m.append(el("span",null,(d.day||"")+" "+(d.tmin||"")));
        if(d.mood)m.append(el("span","tag",d.mood));
        if(d.kind&&d.kind!=="diary")m.append(el("span","tag",d.kind));
        const ops=el("div","nt-ops");
        const e1=el("button",null,"改"); e1.onclick=()=>editDiary(body,d);
        const e2=el("button","danger","删"); e2.onclick=async()=>{
          if(!confirm("删掉这篇日记？"))return;
          const r=await jpost("/api/diary/"+d.id+"/del",{});
          if(r.ok){say("删了");secDiary(body);}else say("删不掉");
        };
        ops.append(e1,e2); m.append(ops);
        c.append(m);
        list.append(c);
      });
    }catch(e){list.innerHTML="";list.append(el("div","errbox","读不出来："+e.message));}
  }

  function editDiary(body,d){
    const isNew=!d;
    sheet(isNew?("写一篇（"+(WHO==="ai"?"它":"我")+"）"):"改日记", bx=>{
      const t=el("textarea"); t.value=(d&&d.content)||""; t.placeholder="今天…";
      const mo=el("input","nt-in"); mo.type="text";
      mo.placeholder="心情（可空，比如 开心 / 有点累）"; mo.value=(d&&d.mood)||"";
      const row=el("div","nt-btns");
      const ok=el("button","pri","存"), no=el("button",null,"取消");
      row.append(ok,no); bx.append(t,mo,row);
      no.onclick=()=>bx.parentNode.remove();
      ok.onclick=async()=>{
        const content=t.value.trim();
        if(!content){say("写点什么");return;}
        const r=isNew
          ? await jpost("/api/diary",{who:WHO,content:content,mood:mo.value.trim()})
          : await jpost("/api/diary/"+d.id+"/edit",{content:content,mood:mo.value.trim()});
        if(r.ok){say(isNew?"写好了":"改好了");bx.parentNode.remove();secDiary(body);}
        else say("没存上："+(r.err||"?"));
      };
    });
  }

  /* ═══ 碎碎念 ═══ */
  async function secNotes(body){
    body.innerHTML="";
    const top=el("div","nt-top");
    const add=el("button","pri","＋ 说一句");
    top.append(el("div","sp"),add);
    body.append(top);
    const list=el("div"); body.append(list);
    add.onclick=()=>editNote(body,null);
    list.append(el("div","hint","读取中…"));
    try{
      const j=await jget("/api/notes?limit=300");
      list.innerHTML="";
      const its=j.items||[];
      if(!its.length)list.append(el("div","hint","还没有碎碎念"));
      its.forEach(d=>{
        const c=el("div","nt-card");
        c.append(el("div","nt-txt",d.content||""));
        const m=el("div","nt-meta");
        m.append(el("span",null,d.t||""));
        if(d.kind)m.append(el("span","tag",d.kind));
        if(d.mood)m.append(el("span","tag",d.mood));
        const ops=el("div","nt-ops");
        const e1=el("button",null,"改"); e1.onclick=()=>editNote(body,d);
        const e2=el("button","danger","删"); e2.onclick=async()=>{
          if(!confirm("删掉这条？"))return;
          const r=await jpost("/api/notes/"+d.id+"/del",{});
          if(r.ok){say("删了");secNotes(body);}else say("删不掉");
        };
        ops.append(e1,e2); m.append(ops);
        c.append(m);
        list.append(c);
      });
    }catch(e){list.innerHTML="";list.append(el("div","errbox","读不出来："+e.message));}
  }

  function editNote(body,d){
    const isNew=!d;
    sheet(isNew?"说一句":"改这条", bx=>{
      const t=el("textarea"); t.value=(d&&d.content)||""; t.placeholder="随便写两句…";
      const kd=el("input","nt-in"); kd.type="text";
      kd.placeholder="类型（可空，比如 note / thought）"; kd.value=(d&&d.kind)||"";
      const mo=el("input","nt-in"); mo.type="text";
      mo.placeholder="心情（可空）"; mo.value=(d&&d.mood)||"";
      const row=el("div","nt-btns");
      const ok=el("button","pri","存"), no=el("button",null,"取消");
      row.append(ok,no); bx.append(t,kd,mo,row);
      no.onclick=()=>bx.parentNode.remove();
      ok.onclick=async()=>{
        const content=t.value.trim();
        if(!content){say("写点什么");return;}
        const r=isNew
          ? await jpost("/api/notes",{content:content,kind:kd.value.trim()||"note",mood:mo.value.trim()})
          : await jpost("/api/notes/"+d.id+"/edit",{content:content,kind:kd.value.trim()||"note",mood:mo.value.trim()});
        if(r.ok){say(isNew?"记下了":"改好了");bx.parentNode.remove();secNotes(body);}
        else say("没存上："+(r.err||"?"));
      };
    });
  }
}catch(e){console.error("nest-notes:",e);}
})();
