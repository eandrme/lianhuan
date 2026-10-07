/* ══════════════════════════════════════════════════════════
   巢 · 书房 ⑤A：书架 + 放书 + 阅读器 + 批注
   装法：nest.html 里再加一行
        <script src="/nest-study.js?v=1"></script>
   后端零改动（optional/reading 那个包已经全有了）
   ⑤B 读书小窗 / ⑤C 创造 之后再加
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
.st-top{display:flex;gap:8px;align-items:center;margin-bottom:10px}
.st-top button{padding:7px 11px;border-radius:8px;border:1px solid var(--line);background:var(--panel);font-size:13px;color:var(--dim)}
.st-tabs{display:flex;gap:6px;flex:1}
.st-tabs button{padding:7px 12px;border-radius:20px;border:1px solid var(--line);background:var(--panel);font-size:13px;color:var(--dim)}
.st-tabs button.on{border-color:var(--accent);color:var(--accent)}
.st-up{border-color:var(--accent)!important;color:var(--accent)!important;white-space:nowrap}
.st-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:10px}
.st-book{border:1px solid var(--line);background:var(--panel);border-radius:var(--r);padding:11px;cursor:pointer}
.st-book.on{border-color:var(--accent)}
.st-cover{width:100%;height:74px;border-radius:9px;display:flex;align-items:center;justify-content:center;
  font-size:30px;font-weight:600;color:#fff;background:linear-gradient(140deg,var(--accent),var(--panel2))}
.st-title{font-size:14px;margin:8px 0 6px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.st-bar{display:flex;align-items:center;gap:6px;font-size:11px;color:var(--dim2);margin:3px 0}
.st-bar .lb{flex:0 0 16px}
.st-bar .track{flex:1;height:5px;border-radius:3px;background:var(--panel2);overflow:hidden}
.st-bar .fill{height:100%;border-radius:3px}
.st-bar .fill.me{background:var(--accent)}
.st-bar .fill.ai{background:var(--warn)}
.st-meta{font-size:11.5px;color:var(--dim2);margin-top:6px}
.st-nav{display:flex;gap:6px;margin-bottom:10px}
.st-nav button{flex:1;padding:8px;border-radius:8px;border:1px solid var(--line);background:var(--panel);font-size:13px;color:var(--dim)}
.st-ch{font-size:16px;font-weight:600;margin:6px 0 12px}
.st-p{position:relative;padding:6px 0;line-height:1.85;font-size:15px;cursor:pointer;border-left:2px solid transparent}
.st-p.mk{padding-left:14px;border-left-color:var(--line)}
.st-p.mk:hover{background:var(--panel2)}
.st-dot{position:absolute;left:-5px;top:9px;font-size:11px;line-height:1;background:none;padding:0}
.st-dot.me{color:var(--accent)}
.st-dot.ai{color:var(--warn)}
.st-dot.both{color:var(--ok)}
.st-h{font-size:12.5px;color:var(--dim);margin:16px 0 6px;letter-spacing:.5px}
.st-quote{border-left:3px solid var(--line);padding:6px 10px;color:var(--dim);font-size:13px;margin-bottom:8px}
.st-row{display:flex;gap:6px;margin-top:9px}
.st-row button{flex:1;padding:10px;border-radius:9px;border:1px solid var(--line);background:var(--panel2);color:var(--fg);font:inherit}
.st-row button.pri{background:var(--accent);color:var(--nest-me-fg,#10131a);border-color:transparent;font-weight:600}
.st-ann{border:1px solid var(--line);background:var(--panel);border-radius:9px;padding:9px 11px;margin-bottom:7px;font-size:13.5px}
.st-ann .q{color:var(--dim);font-size:12.5px;margin-bottom:4px}
.st-ann .who{font-size:11.5px;color:var(--dim2);margin-top:5px}
.st-ann.clk{cursor:pointer}
.st-ann.clk:hover{background:var(--panel2)}
.sheet textarea{width:100%;min-height:92px;box-sizing:border-box;padding:10px;border-radius:9px;
  border:1px solid var(--line);background:var(--panel2);color:var(--fg);font:inherit;outline:none;resize:vertical}
`;
  document.head.append(css);

  /* 自己的弹层（tabs 那个 helper 拿不到） */
  function sheet(title,build){
    const wrap=el("div","sheet"), bx=el("div","box");
    const h=el("div","bh"), b=el("b",null,title), x=el("button","x ibtn","✕");
    x.onclick=()=>wrap.remove(); h.append(b,x); bx.append(h); wrap.append(bx);
    wrap.onclick=e=>{if(e.target===wrap)wrap.remove();};
    document.body.append(wrap); build(bx,()=>wrap.remove()); return wrap;
  }

  window.NEST_PANES.study=function(box){
    box.innerHTML="";
    const view=el("div"); box.append(view);

    /* ═══ 书架 ═══ */
    async function shelf(){
      view.innerHTML="";
      const top=el("div","st-top");
      const tabs=el("div","st-tabs");
            const b1=el("button","on","书架");
      b1.onclick=()=>shelf();
      const b2=el("button",null,"创造");
      b2.onclick=()=>{ b1.classList.remove("on"); b2.classList.add("on");
        if(window.NEST_CREATION)window.NEST_CREATION(view); else say("「创造」还没接上"); };
      tabs.append(b1,b2);
      const up=el("button","st-up","＋ 放书");
      up.onclick=pickFile;
      top.append(tabs,up);
      const grid=el("div","st-grid");
      view.append(top,grid);
      grid.append(el("div","hint","读取中…"));
      try{
        const j=await jget("/api/books");
        const its=j.items||[];
        grid.innerHTML="";
        if(!its.length){
          grid.append(el("div","hint","书架还空着 —— 点右上「＋ 放书」，选一个 .txt 文件"));
          return;
        }
        its.forEach(b=>grid.append(bookCard(b)));
      }catch(e){ grid.innerHTML=""; grid.append(el("div","errbox","书架读不出来："+e.message)); }
    }

    function bar(lb,pct,cls){
      const w=el("div","st-bar");
      w.append(el("span","lb",lb));
      const t=el("div","track"), f=el("div","fill "+cls);
      f.style.width=Math.max(3,Math.min(100,pct||0))+"%";
      t.append(f); w.append(t);
      return w;
    }
    function bookCard(b){
      const c=el("div","st-book"+(b.current?" on":""));
      c.append(el("div","st-cover",(b.title||"书").slice(0,1)));
      c.append(el("div","st-title",b.title||""));
      c.append(bar("我",b.pct||0,"me"));
      const aiPct=b.chapters?Math.round(100*((b.ai_idx||0)+1)/b.chapters):0;
      c.append(bar("它",aiPct,"ai"));
      c.append(el("div","st-meta",(b.chapters||0)+" 章"));
             const ops=el("div"); ops.style.cssText="display:flex;gap:6px;margin-top:8px";
      const rn=el("button",null,"改名");
      rn.style.cssText="flex:1;padding:4px;border-radius:7px;border:1px solid var(--line);background:none;font-size:12px;color:var(--dim)";
      rn.onclick=(e)=>{e.stopPropagation();
        const t=prompt("新书名：",b.title||"");if(!t||!t.trim())return;
        jpost("/api/books/"+b.id+"/rename",{title:t.trim()}).then(r=>{if(r.ok){say("改好了");shelf();}else say("改不了："+(r.err||"?"));});
      };
      const dl=el("button",null,"删");
      dl.style.cssText="padding:4px 9px;border-radius:7px;border:1px solid var(--err);background:none;font-size:12px;color:var(--err)";
      dl.onclick=(e)=>{e.stopPropagation();
        if(!confirm("删掉《"+(b.title||"")+"》？书、批注、聊天记录都会一起没"))return;
        jpost("/api/books/"+b.id+"/del",{}).then(r=>{if(r.ok){say("删了");shelf();}else say("删不掉");});
      };
      ops.append(rn,dl); c.append(ops);
      c.onclick=async()=>{
        await jpost("/api/books/"+b.id+"/current");
        open(b,Math.max(0,b.my_idx||0));
      };
      return c;
    }

    function pickFile(){
      const i=el("input"); i.type="file"; i.accept=".txt,text/plain";
      i.onchange=()=>{
        const f=i.files&&i.files[0]; if(!f)return;
        const fr=new FileReader();
        fr.onload=async()=>{
          say("正在切章…");
          const r=await jpost("/api/books/upload",
            {title:(f.name||"").replace(/\.txt$/i,""),dataURL:fr.result});
          if(r.ok){ say("收进来了："+r.chapters+" 章"); shelf(); }
          else say("没传上："+(r.err||"?"));
        };
        fr.readAsDataURL(f);
      };
      i.click();
    }

    /* ═══ 阅读器 ═══ */
    async function open(b,idx){
      view.innerHTML="";
      let chs=[];
      try{ chs=(await jget("/api/books/"+b.id+"/chapters")).items||[]; }catch(e){}
      const top=el("div","st-top");
      const back=el("button",null,"← 书架"); back.onclick=()=>shelf();
      const tt=el("div","st-title",b.title||""); tt.style.flex="1";
      const annBtn=el("button",null,"批注");
      top.append(back,tt,annBtn);
      const nav=el("div","st-nav");
      const prev=el("button",null,"上一章"), toc=el("button",null,"目录"), next=el("button",null,"下一章");
      nav.append(prev,toc,next);
      const body=el("div");
      view.append(top,nav,body);
      let cur=Math.max(0,Math.min(idx,(chs.length||1)-1));

      prev.onclick=()=>{ if(cur>0){cur--;load();} else say("已经是第一章了"); };
      next.onclick=()=>{ if(cur<chs.length-1){cur++;load();} else say("已经是最后一章了"); };
      toc.onclick=()=>{
        sheet("目录", bx=>{
          chs.forEach(c=>{
            const r=el("div","thr"+(c.idx===cur?" on":""));
            r.append(el("div","tt",(c.idx+1)+". "+(c.title||"")));
            r.onclick=()=>{ cur=c.idx; bx.parentNode.remove(); load(); };
            bx.append(r);
          });
        });
      };
      annBtn.onclick=()=>allAnnos(b,chs,(i)=>{cur=i;load();});

      function marks(paras,annos){
        const m={};
        annos.forEach(a=>{
          const q=String(a.quote||"");
          let pi=paras.findIndex(p=>q&&p.indexOf(q.slice(0,12))>=0);
          if(pi<0&&q)pi=paras.findIndex(p=>p.indexOf(q.slice(0,6))>=0);
          a._pi=pi<0?null:pi;
          if(pi<0)return;
          const s=m[pi]||(m[pi]={me:0,ai:0,list:[]});
          if(a.author==="ai")s.ai++; else s.me++;
          s.list.push(a);
        });
        return m;
      }
      function dot(mk,list){
        const kind=(mk.me&&mk.ai)?"both":(mk.ai?"ai":"me");
        const d=el("button","st-dot "+kind, kind==="both"?"◉":(kind==="ai"?"○":"●"));
        d.title="这里有批注";
        d.onclick=e=>{e.stopPropagation();showNotes(list);};
        return d;
      }
      function showNotes(list){
        sheet("这一处的批注", bx=>{
          list.forEach(a=>{
            const c=el("div","st-ann");
            if(a.quote)c.append(el("div","q","「"+a.quote+"」"));
            c.append(el("div",null,a.note||"（没写正文）"));
            c.append(el("div","who",(a.author==="ai"?"它":"你")+" · "+a.t));
            bx.append(c);
          });
        });
      }
      function askAnnotate(txt){
        const quote=String(txt||"").slice(0,500);
        sheet("写一条批注", bx=>{
          bx.append(el("div","st-quote",quote.slice(0,140)+"…"));
          const ta=el("textarea"); ta.placeholder="你想说什么…";
          const row=el("div","st-row");
          const ok=el("button","pri","存");
          const no=el("button",null,"取消");
          row.append(ok,no); bx.append(ta,row);
          no.onclick=()=>bx.parentNode.remove();
          ok.onclick=async()=>{
            const note=ta.value.trim(); if(!note){say("写点什么再存");return;}
            const r=await jpost("/api/books/"+b.id+"/annotations",
              {chapter_idx:cur,quote:quote,note:note,author:"me"});
            if(r.ok){ say("批注存下了"); bx.parentNode.remove(); load(); }
            else say("没存上："+(r.err||"?"));
          };
        });
      }

      async function load(){
        body.innerHTML=el("div","hint","读取中…");
        let ch;
        try{ ch=await jget("/api/books/"+b.id+"/chapter/"+cur); }
        catch(e){ body.innerHTML=""; body.append(el("div","errbox","这一章读不出来："+e.message)); return; }
        jpost("/api/books/"+b.id+"/progress",{idx:cur});
        let annos=[];
        try{ annos=(await jget("/api/books/"+b.id+"/annotations")).items||[]; }catch(e){}
        const mine=annos.filter(a=>a.chapter_idx===cur);
        body.innerHTML="";
        body.append(el("div","st-ch",ch.title||("第 "+(cur+1)+" 章")));
        const paras=String(ch.content||"").split(/\n+/).map(s=>s.trim()).filter(Boolean);
        const mk=marks(paras,mine);
        paras.forEach((p,i)=>{
          const d=el("div","st-p");
          if(mk[i]){ d.classList.add("mk"); d.append(dot(mk[i],mk[i].list)); }
          d.append(el("span",null,p));
          d.onclick=()=>askAnnotate(p);
          body.append(d);
        });
        const orphan=mine.filter(a=>a._pi==null);
        body.append(el("div","st-h","本章批注 "+mine.length+" 条（点正文任意一句就能写）"));
        if(orphan.length){
          orphan.forEach(a=>{
            const c=el("div","st-ann");
            if(a.quote)c.append(el("div","q","「"+a.quote+"」"));
            c.append(el("div",null,a.note||""));
            c.append(el("div","who",(a.author==="ai"?"它":"你")+" · "+a.t));
            body.append(c);
          });
        }else{
          mine.forEach(a=>{
            const c=el("div","st-ann");
            if(a.quote)c.append(el("div","q","「"+a.quote+"」"));
            c.append(el("div",null,a.note||""));
            c.append(el("div","who",(a.author==="ai"?"它":"你")+" · "+a.t));
            body.append(c);
          });
        }
        try{ body.scrollIntoView({block:"start"}); }catch(e){}
      }
      load();
    }

    async function allAnnos(b,chs,go){
      let annos=[];
      try{ annos=(await jget("/api/books/"+b.id+"/annotations")).items||[]; }catch(e){}
      sheet("这本书的批注（"+annos.length+"）", bx=>{
        if(!annos.length){ bx.append(el("div","hint","还没有批注")); }
        annos.forEach(a=>{
          const c=el("div","st-ann clk");
          if(a.quote)c.append(el("div","q","「"+a.quote+"」"));
          c.append(el("div",null,a.note||""));
          c.append(el("div","who",(a.author==="ai"?"它":"你")+" · 第 "+(a.chapter_idx+1)+" 章 · "+a.t));
          c.onclick=()=>{ bx.parentNode.remove(); go(a.chapter_idx||0); };
          bx.append(c);
        });
      });
    }

    shelf();
  };
}catch(e){console.error("nest-study:",e);}
})();
