/* ══════════════════════════════════════════════════════════
   巢 · 创造 ⑤C：世界观 / 角色 / 故事 + 批注 + 一起写
   装法：nest.html 再加一行 <script src="/nest-creation.js?v=1"></script>
   后端：/api/worlds · /api/casts · /api/stories（⑤C-A 已加）
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
.cr-top{display:flex;gap:8px;align-items:center;margin-bottom:10px;flex-wrap:wrap}
.cr-top button{padding:7px 11px;border-radius:8px;border:1px solid var(--line);background:var(--panel);font-size:13px;color:var(--dim)}
.cr-top button.pri{border-color:var(--accent);color:var(--accent)}
.cr-top .sp{flex:1}
.cr-top .nm{font-size:15px;font-weight:600}
.cr-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:10px}
.cr-card{border:1px solid var(--line);background:var(--panel);border-radius:var(--r);padding:12px;cursor:pointer}
.cr-card:hover{border-color:var(--accent)}
.cr-card .nm{font-size:15px;font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.cr-card .nt{font-size:12.5px;color:var(--dim2);margin-top:5px;
  overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.cr-card .ct{font-size:11.5px;color:var(--dim2);margin-top:8px}
.cr-h{font-size:12.5px;color:var(--dim);margin:16px 0 7px;letter-spacing:.5px}
.cr-h button{float:right;padding:3px 9px;border-radius:7px;border:1px solid var(--line);
  background:none;font-size:12px;color:var(--dim);margin-top:-3px}
.cr-row{display:flex;gap:7px;align-items:center;border-bottom:1px solid var(--line);padding:9px 4px}
.cr-row .nm{flex:1;min-width:0;font-size:14px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.cr-row .nt{font-size:12px;color:var(--dim2);flex:0 0 auto;max-width:42%;
  overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.cr-row button{padding:4px 9px;border-radius:7px;border:1px solid var(--line);background:none;font-size:12px;color:var(--dim)}
.cr-row button.danger{color:var(--err);border-color:var(--err)}
.cr-in{width:100%;box-sizing:border-box;padding:9px 11px;border-radius:9px;border:1px solid var(--line);
  background:var(--panel2);color:var(--fg);font:inherit;outline:none;margin-bottom:8px}
#cr-body{width:100%;box-sizing:border-box;min-height:44vh;padding:14px;border-radius:var(--r);
  border:1px solid var(--line);background:var(--panel);color:var(--fg);font:inherit;
  line-height:1.85;outline:none;resize:vertical}
.cr-note{border:1px solid var(--line);background:var(--panel);border-radius:9px;padding:9px 11px;margin-bottom:7px;font-size:13.5px}
.cr-note .q{color:var(--dim);font-size:12.5px;margin-bottom:4px}
.cr-note .who{font-size:11.5px;color:var(--dim2);margin-top:5px}
.cr-btns{display:flex;gap:6px;margin-top:10px}
.cr-btns button{flex:1;padding:10px;border-radius:9px;border:1px solid var(--line);
  background:var(--panel2);color:var(--fg);font:inherit}
.cr-btns button.pri{background:var(--accent);color:var(--nest-me-fg,#10131a);border-color:transparent;font-weight:600}
.cr-sheet textarea{width:100%;min-height:92px;box-sizing:border-box;padding:10px;border-radius:9px;
  border:1px solid var(--line);background:var(--panel2);color:var(--fg);font:inherit;outline:none;resize:vertical}
`;
  document.head.append(css);

  function sheet(title,build){
    const wrap=el("div","sheet"), bx=el("div","box cr-sheet");
    const h=el("div","bh"), b=el("b",null,title), x=el("button","x ibtn","✕");
    x.onclick=()=>wrap.remove(); h.append(b,x); bx.append(h); wrap.append(bx);
    wrap.onclick=e=>{if(e.target===wrap)wrap.remove();};
    document.body.append(wrap); build(bx,()=>wrap.remove()); return wrap;
  }
  const host=()=>document.querySelector("#pane")||document.body;

  let VIEW=null, ACTIVE_BOX=null;
  function clean(){ if(ACTIVE_BOX){ACTIVE_BOX.remove();ACTIVE_BOX=null;} }

  window.NEST_CREATION=function(view){ VIEW=view; clean(); home(); };

  /* ═══ 世界观列表 ═══ */
  async function home(){
    clean(); const view=VIEW; view.innerHTML="";
    const top=el("div","cr-top");
    const add=el("button","pri","＋ 新世界观"); add.onclick=()=>editWorld(0,null);
    const se=el("button",null,"🔍 找故事"); se.onclick=searchStories;
    top.append(add,se); view.append(top);
    const grid=el("div","cr-grid"); view.append(grid);
    grid.append(el("div","hint","读取中…"));
    try{
      const j=await jget("/api/worlds");
      grid.innerHTML="";
      const its=j.items||[];
      if(!its.length)grid.append(el("div","hint","还没有世界观。点「＋ 新世界观」起一个 —— 比如「海边的旧灯塔」。"));
      its.forEach(w=>{
        const c=el("div","cr-card");
        c.append(el("div","nm",w.name||""));
        if(w.note)c.append(el("div","nt",w.note));
        c.append(el("div","ct",(w.casts||0)+" 角色 · "+(w.stories||0)+" 故事"));
        c.onclick=()=>world(w.id);
        grid.append(c);
      });
      if(j.orphan){
        const o=el("div","cr-card");
        o.append(el("div","nm","未归类"),el("div","ct",j.orphan+" 篇故事还没归到世界观"));
        o.onclick=()=>listStories(0,"未归类的故事");
        grid.append(o);
      }
    }catch(e){ grid.innerHTML=""; grid.append(el("div","errbox","读不出来："+e.message)); }
  }

  /* ═══ 一个世界观 ═══ */
  async function world(wid){
    clean(); const view=VIEW; view.innerHTML="";
    let d;
    try{ d=await jget("/api/worlds/"+wid); }
    catch(e){ view.append(el("div","errbox","读不出来："+e.message)); return; }
    const top=el("div","cr-top");
    const back=el("button",null,"← 世界观"); back.onclick=()=>home();
    const rn=el("button",null,"改名"); rn.onclick=()=>editWorld(wid,d.world);
    const dl=el("button","danger","删"); dl.style.color="var(--err)"; dl.style.borderColor="var(--err)";
    dl.onclick=async()=>{
      if(!confirm("删掉这个世界观？里面的角色和故事不会没，会变成「未归类」"))return;
      const r=await jpost("/api/worlds/"+wid+"/del",{});
      if(r.ok){ say("删了"); home(); } else say("删不掉");
    };
    top.append(back,el("div","sp"),rn,dl); view.append(top);
    view.append(el("div","cr-h",d.world.name||""));
    if(d.world.note){ const c=el("div","cr-card"); c.style.cursor="default"; c.append(el("div","nt",d.world.note)); view.append(c); }

    const ch=el("div","cr-h","角色 · "+((d.casts||[]).length));
    const ca=el("button",null,"＋ 角色"); ca.onclick=()=>editCast(wid,0,null);
    ch.append(ca); view.append(ch);
    (d.casts||[]).forEach(c=>{
      const r=el("div","cr-row");
      r.append(el("div","nm",c.name||""),el("div","nt",c.note||""));
      const e1=el("button",null,"改"); e1.onclick=()=>editCast(wid,c.id,c);
      const e2=el("button","danger","删");
      e2.onclick=async()=>{ if(!confirm("删掉角色「"+c.name+"」？"))return;
        await jpost("/api/casts/"+c.id+"/del",{}); world(wid); };
      r.append(e1,e2); view.append(r);
    });

    const sh=el("div","cr-h","故事 · "+((d.stories||[]).length));
    const sa=el("button",null,"＋ 写一篇"); sa.onclick=()=>editor(0,wid);
    sh.append(sa); view.append(sh);
    (d.stories||[]).forEach(s=>{
      const r=el("div","cr-row");
      r.append(el("div","nm",s.title||"没起名"),el("div","nt",s.excerpt||""));
      const o=el("button",null,"打开"); o.onclick=()=>editor(s.id,wid);
      const dd=el("button","danger","删");
      dd.onclick=async()=>{ if(!confirm("删掉《"+(s.title||"")+"》？"))return;
        await jpost("/api/stories/"+s.id+"/del",{}); world(wid); };
      r.append(o,dd); view.append(r);
    });
  }

  /* ═══ 新/改 世界观 ═══ */
  function editWorld(wid,w){
    w=w||{};
    sheet(wid?"改世界观":"新世界观", bx=>{
      const n=el("input","cr-in"); n.type="text";
      n.placeholder="名字（比如：海边的旧灯塔）"; n.value=w.name||"";
      const t=el("textarea"); t.placeholder="一两句设定（可空）"; t.value=w.note||"";
      const row=el("div","cr-btns");
      const ok=el("button","pri","存"), no=el("button",null,"取消");
      row.append(ok,no); bx.append(n,t,row);
      no.onclick=()=>bx.parentNode.remove();
      ok.onclick=async()=>{
        const name=n.value.trim(); if(!name){say("得有个名字");return;}
        const r=await jpost("/api/worlds/save",{id:wid||0,name:name,note:t.value});
        if(r.ok){ say("存好了"); bx.parentNode.remove(); wid?world(wid):home(); }
        else say("没存上："+(r.err||"?"));
      };
    });
  }

  /* ═══ 新/改 角色 ═══ */
  function editCast(wid,cid,c){
    c=c||{};
    sheet(cid?"改角色":"新角色", bx=>{
      const n=el("input","cr-in"); n.type="text"; n.placeholder="角色名"; n.value=c.name||"";
      const t=el("textarea"); t.placeholder="他是谁、什么脾气、跟谁有什么过节…"; t.value=c.note||"";
      const row=el("div","cr-btns");
      const ok=el("button","pri","存"), no=el("button",null,"取消");
      row.append(ok,no); bx.append(n,t,row);
      no.onclick=()=>bx.parentNode.remove();
      ok.onclick=async()=>{
        const name=n.value.trim(); if(!name){say("角色得有个名字");return;}
        const r=await jpost("/api/casts/save",{id:cid||0,wid:wid,name:name,note:t.value});
        if(r.ok){ say("存好了"); bx.parentNode.remove(); world(wid); }
        else say("没存上："+(r.err||"?"));
      };
    });
  }

  /* ═══ 故事列表（未归类 / 搜索） ═══ */
  async function listStories(wid,t){
    clean(); const view=VIEW; view.innerHTML="";
    const top=el("div","cr-top");
    const back=el("button",null,"← 回"); back.onclick=()=>home();
    top.append(back,el("div","sp"),el("div","nm",t||"故事")); view.append(top);
    try{
      const j=await jget("/api/stories?wid="+wid);
      const its=j.items||[];
      if(!its.length)view.append(el("div","hint","这里还没有故事"));
      its.forEach(s=>{
        const r=el("div","cr-row");
        r.append(el("div","nm",s.title||"没起名"),el("div","nt",s.excerpt||""));
        const o=el("button",null,"打开"); o.onclick=()=>editor(s.id,s.wid||0);
        r.append(o); view.append(r);
      });
    }catch(e){ view.append(el("div","errbox","读不出来："+e.message)); }
  }

  async function searchStories(){
    let ws=[];
    try{ ws=(await jget("/api/worlds")).items||[]; }catch(e){}
    sheet("找故事", bx=>{
      const i=el("input","cr-in"); i.type="text"; i.placeholder="打一个字，回车";
      const out=el("div"); bx.append(i,out);
      const run=async()=>{
        const q=i.value.trim(); if(!q){out.innerHTML="";return;}
        try{
          const j=await jget("/api/stories?q="+encodeURIComponent(q));
          out.innerHTML="";
          const its=j.items||[];
          if(!its.length)out.append(el("div","cr-row","没找到"));
          const nm={}; ws.forEach(w=>nm[w.id]=w.name);
          its.forEach(s=>{
            const r=el("div","cr-row"); r.style.cursor="pointer";
            r.append(el("div","nm",s.title||"没起名"),
                     el("div","nt",nm[s.wid]||"未归类"));
            r.onclick=()=>{ bx.parentNode.remove(); editor(s.id,s.wid||0); };
            out.append(r);
          });
        }catch(e){ out.innerHTML=""; out.append(el("div","cr-row","搜不了："+e.message)); }
      };
      i.addEventListener("keydown",e=>{if(e.key==="Enter")run();});
      setTimeout(()=>{try{i.focus();}catch(e){}},60);
    });
  }

  /* ═══ 写作器 ═══ */
  async function editor(sid,wid){
    clean(); const view=VIEW; view.innerHTML="";
    let st={id:sid||0,wid:wid||0,title:"",body:""};
    if(sid){
      try{ const j=await jget("/api/stories/"+sid); st={id:j.id,wid:j.wid,title:j.title,body:j.body}; }
      catch(e){ view.append(el("div","errbox","读不出来："+e.message)); return; }
    }
    const top=el("div","cr-top");
    const back=el("button",null,"← 回"); back.onclick=()=>{ st.wid?world(st.wid):home(); };
    const chat=el("button",null,"💬 一起写"); chat.onclick=()=>openChat();
    const save=el("button","pri","保存"); save.onclick=doSave;
    top.append(back,el("div","sp"),chat,save); view.append(top);

    const ti=el("input","cr-in"); ti.type="text"; ti.placeholder="题目"; ti.value=st.title||"";
    view.append(ti);
    const ta=el("textarea"); ta.id="cr-body"; ta.placeholder="在这儿写…"; ta.value=st.body||"";
    view.append(ta);

    const ops=el("div","cr-top");
    const ann=el("button",null,"批注选中的一段"); ann.onclick=annotate;
    const gw=el("button",null,"归到世界观…"); gw.onclick=pickWorld;
    ops.append(ann,gw); view.append(ops);

    const nh=el("div","cr-h","批注"); view.append(nh);
    const nl=el("div"); view.append(nl);

    async function doSave(){
      const r=await jpost("/api/stories/save",
        {id:st.id||0,wid:st.wid||0,title:ti.value.trim(),body:ta.value});
      if(r.ok){ st.id=r.id; if(!st.title)st.title=ti.value.trim(); say("存好了"); loadNotes(); }
      else say("没存上："+(r.err||"?"));
      return r.ok;
    }
    async function loadNotes(){
      if(!st.id){ nl.innerHTML=""; return; }
      try{
        const j=await jget("/api/stories/"+st.id+"/notes");
        nl.innerHTML="";
        const its=j.items||[];
        if(!its.length)nl.append(el("div","hint","还没有批注"));
        its.forEach(a=>{
          const c=el("div","cr-note");
          if(a.quote)c.append(el("div","q","「"+a.quote.slice(0,90)+"」"));
          c.append(el("div",null,a.note||""));
          c.append(el("div","who",(a.author==="ai"?"它":"你")+" · "+a.t));
          nl.append(c);
        });
      }catch(e){}
    }
    async function annotate(){
      const s=ta.selectionStart, e=ta.selectionEnd;
      const quote=(s!=null&&e>s)?ta.value.slice(s,e).trim():"";
      if(!quote){ say("先在正文里选中一段字"); return; }
      if(!st.id){ const ok=await doSave(); if(!ok)return; }
      sheet("写批注", bx=>{
        bx.append(el("div","cr-note",quote.slice(0,140)+"…"));
        const t=el("textarea"); t.placeholder="你想说什么…";
        const row=el("div","cr-btns");
        const ok=el("button","pri","存"), no=el("button",null,"取消");
        row.append(ok,no); bx.append(t,row);
        no.onclick=()=>bx.parentNode.remove();
        ok.onclick=async()=>{
          const note=t.value.trim(); if(!note){say("写点什么");return;}
          const r=await jpost("/api/stories/"+st.id+"/notes",
            {quote:quote.slice(0,500),note:note,author:"me"});
          if(r.ok){ say("存下了"); bx.parentNode.remove(); loadNotes(); } else say("没存上");
        };
      });
    }
    async function pickWorld(){
      let ws=[];
      try{ ws=(await jget("/api/worlds")).items||[]; }catch(e){}
      sheet("归到哪个世界观", bx=>{
        const mk=(label,val)=>{
          const r=el("div","cr-row"); r.style.cursor="pointer";
          r.append(el("div","nm",label));
          r.onclick=async()=>{ st.wid=val; await doSave(); bx.parentNode.remove();
            say(val?"归到「"+label+"」":"归到「未归类」"); };
          bx.append(r);
        };
        mk("不归类",0);
        ws.forEach(w=>mk(w.name,w.id));
      });
    }

    /* 一起写：小窗 */
    let box=null,listEl=null,tin=null;
    function openChat(){
      if(!st.id){ say("先保存一下再聊"); return; }
      if(!box){
        box=el("div","bc-box"); box.hidden=true; ACTIVE_BOX=box;
        const h=el("div","bc-head");
        const tt=el("div","bc-title","一起写 · "+(st.title||""));
        const x=el("button","ibtn","✕"); x.onclick=()=>{box.hidden=true;};
        h.append(tt,x);
        listEl=el("div","bc-list");
        const foot=el("div","bc-foot");
        const row=el("div","bc-row");
        tin=el("textarea"); tin.rows=1; tin.placeholder="跟它一起想…";
        tin.addEventListener("input",()=>{tin.style.height="auto";
          tin.style.height=Math.min(tin.scrollHeight,innerHeight*0.3)+"px";});
        tin.addEventListener("keydown",e=>{
          if(e.key==="Enter"&&!e.shiftKey&&!e.isComposing){e.preventDefault();send();}
        });
        const s=el("button","bc-send","→"); s.onclick=send;
        row.append(tin,s); foot.append(row);
        box.append(h,listEl,foot);
        host().append(box);
      }
      box.hidden=false; loadChat();
    }
    function add(role,txt){
      const d=el("div","bc-msg "+role,txt);
      listEl.append(d); listEl.scrollTop=listEl.scrollHeight; return d;
    }
    async function loadChat(){
      listEl.innerHTML=""; listEl.append(el("div","hint","读着…"));
      try{
        const j=await jget("/api/stories/"+st.id+"/chat");
        listEl.innerHTML="";
        const its=j.items||[];
        if(!its.length)listEl.append(el("div","hint","还没聊过。说点什么？"));
        its.forEach(m=>add(m.role==="user"?"user":"assistant",m.content));
      }catch(e){ listEl.innerHTML=""; listEl.append(el("div","hint","读不出来："+e.message)); }
    }
    async function send(){
      if(!st.id)return;
      const q=(tin.value||"").trim(); if(!q)return;
      tin.value=""; tin.style.height="auto";
      add("user",q);
      const th=add("thinking","它在想…");
      try{
        const r=await jpost("/api/stories/"+st.id+"/chat",{message:q});
        th.remove();
        if(r.ok)add("assistant",r.reply||"");
        else add("err","没接上话："+(r.err||"?"));
      }catch(e){ th.remove(); add("err","断了："+e.message); }
    }

    loadNotes();
  }
}catch(e){console.error("nest-creation:",e);}
})();
