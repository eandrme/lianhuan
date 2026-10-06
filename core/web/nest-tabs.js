/* ══════════════════════════════════════════════════════════
   巢 · 导航模块 v1：五个格子 + 多窗口 + 搜索 + MCP 按钮
   装法：nest.html 里，nest-icon.js 那行【下面】再加一行
        <script src="/nest-tabs.js?v=1"></script>
   ══════════════════════════════════════════════════════════ */
(function(){
"use strict";
try{
  const $=(s,r=document)=>r.querySelector(s);
  const el=(t,c,x)=>{const e=document.createElement(t);if(c)e.className=c;if(x!=null)e.textContent=x;return e;};
  const say=t=>{try{if(typeof toast==="function")toast(t);}catch(e){}};
  const jget=async u=>{const r=await fetch(u,{credentials:"same-origin"});if(!r.ok)throw new Error("HTTP "+r.status);return r.json();};
  const hm=ts=>{const d=new Date((ts||0)*1000);const p=n=>String(n).padStart(2,"0");
    return p(d.getMonth()+1)+"-"+p(d.getDate())+" "+p(d.getHours())+":"+p(d.getMinutes());};
  const getSid=()=>{try{return (typeof SID!=="undefined"&&SID)||localStorage.getItem("nest_sid")||"main";}
                    catch(e){return localStorage.getItem("nest_sid")||"main";}};
  const setSid=v=>{v=v||"main";try{if(typeof SID!=="undefined")SID=(v==="main"?"":v);}catch(e){}
                   localStorage.setItem("nest_sid",v==="main"?"":v);};

  const css=document.createElement("style");
  css.textContent=`
#tabs{display:flex;border-top:1px solid var(--line);background:var(--bg)}
#tabs button{flex:1;padding:8px 0 10px;font-size:11.5px;color:var(--dim2);display:flex;flex-direction:column;align-items:center;gap:3px}
#tabs button .ic{font-size:17px;line-height:1}
#tabs button.on{color:var(--accent)}
#pane{position:fixed;inset:0;z-index:40;background:var(--bg);display:flex;flex-direction:column}
#pane .ph{display:flex;align-items:center;gap:10px;padding:12px 14px;border-bottom:1px solid var(--line)}
#pane .ph .t{font-weight:600}
#pane .ph .x{margin-left:auto}
#pane .pb{flex:1;overflow:auto;padding:14px}
.sheet{position:fixed;inset:0;z-index:45;background:#0008;display:flex;align-items:flex-end;justify-content:center}
.sheet .box{width:min(660px,100%);max-height:76vh;overflow:auto;background:var(--panel);
  border:1px solid var(--line);border-radius:var(--r) var(--r) 0 0;padding:12px}
.sheet .bh{display:flex;align-items:center;gap:8px;margin-bottom:8px}
.sheet .bh b{font-size:15px}
.sheet .bh .x{margin-left:auto}
.sheet input[type=text]{width:100%;padding:9px 11px;border-radius:9px;border:1px solid var(--line);
  background:var(--panel2);color:var(--fg);font:inherit;outline:none;box-sizing:border-box;margin-bottom:8px}
.thr,.res{display:flex;align-items:center;gap:8px;padding:10px 8px;border-bottom:1px solid var(--line);cursor:pointer}
.thr:hover,.res:hover{background:var(--panel2)}
.thr .tt,.res .tt{flex:1;min-width:0;font-size:14px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.thr .tn{font-size:11.5px;color:var(--dim2);flex:0 0 auto}
.thr.on .tt{color:var(--accent)}
.res{display:block}
.res .k{font-size:11.5px;color:var(--dim2);margin-bottom:2px}
.ph-card{border:1px solid var(--line);background:var(--panel);border-radius:var(--r);padding:14px;color:var(--dim)}
.ph-card b{color:var(--fg);font-size:15px}
pre.js{margin:6px 0 0;font:12px/1.5 var(--mono);color:var(--dim);white-space:pre-wrap;word-break:break-all}
`;
  document.head.append(css);

  const TABS=[["chat","💬","聊天"],["memory","🧠","记忆"],["study","📖","书房"],
              ["notes","📝","记事"],["setting","⚙️","设置"]];

  const nav=el("nav"); nav.id="tabs";
  TABS.forEach(t=>{
    const b=el("button"); b.dataset.tab=t[0];
    b.append(el("span","ic",t[1]),el("span","lb",t[2]));
    b.onclick=()=>go(t[0]); nav.append(b);
  });

  const pane=el("div"); pane.id="pane"; pane.hidden=true;
  const ptitle=el("div","t");
  const pclose=el("button","x ibtn","✕"); pclose.onclick=()=>go("chat");
  const phead=el("div","ph"); phead.append(ptitle,pclose);
  const pbody=el("div","pb"); pane.append(phead,pbody);

  function go(k){
    [].slice.call(nav.children).forEach(b=>b.classList.toggle("on",b.dataset.tab===k));
    if(k==="chat"){ pane.hidden=true; return; }
    pane.hidden=false;
    ptitle.textContent=(TABS.find(x=>x[0]===k)||[])[2]||"";
    pbody.innerHTML="";
         if(window.NEST_PANES&&window.NEST_PANES[k]){try{window.NEST_PANES[k](pbody);}catch(e){console.error("pane:",e);}return;}
    const info={memory:["🧠 记忆库","L1/L2/L3 分层浏览 · 搜索 · 增删改 · 可见性（仅某助手 / 全部助手）"],
                study:["📖 书房","书架 · 在读进度 · 边读边聊的小窗"],
                notes:["📝 记事","日记 · 碎碎念 · 心情 · 日历 · 梗库 · 表情包（都要带编辑 / 删除）"],
                setting:["⚙️ 设置","美化 · MCP 工具包 · 消息推送 · 大模型 API · 助手设置"]}[k];
    if(info){
      const c=el("div","ph-card");
      c.innerHTML="<b>"+info[0]+"</b><br>"+info[1]+"<br><br>⏳ 这个板块下一批接上。";
      pbody.append(c);
    }
  }

  function sheet(title,build){
    const wrap=el("div","sheet"), box=el("div","box");
    const h=el("div","bh"), b=el("b",null,title), x=el("button","x ibtn","✕");
    x.onclick=()=>wrap.remove(); h.append(b,x); box.append(h); wrap.append(box);
    wrap.onclick=e=>{if(e.target===wrap)wrap.remove();};
    document.body.append(wrap); build(box,()=>wrap.remove()); return wrap;
  }
  function barBtn(txt,title,fn){
    const b=el("button","ibtn",txt); b.title=title; b.onclick=fn;
    const side=document.querySelector("#btnSide");
    if(side&&side.parentNode)side.parentNode.insertBefore(b,side);
    else{const bar=document.querySelector("#bar"); if(bar)bar.append(b);}
  }

  /* ── 多窗口 ── */
  async function openThreads(){
    sheet("对话窗口", async(box,close)=>{
      const bt=el("button",null,"＋ 新对话");
      bt.style.cssText="padding:8px 12px;border:1px solid var(--accent);border-radius:9px;color:var(--accent);margin-bottom:8px";
      bt.onclick=async()=>{ newThread(); close(); };
      box.append(bt);
      const list=el("div"); box.append(list);
      list.append(el("div","res","读取中…"));
      try{
        const j=await jget("/api/nest/threads");
        list.innerHTML="";
        const its=j.items||[];
        if(!its.length)list.append(el("div","res","还没有任何对话"));
        its.forEach(it=>{
          const r=el("div","thr"+(it.sid===getSid()?" on":""));
          r.append(el("div","tt",it.title||"（空窗口）"),el("div","tn",it.n+" 条"));
          r.onclick=async()=>{ setSid(it.sid); await renderThread(); close(); say("切到这个窗口了"); };
          list.append(r);
        });
      }catch(e){ list.innerHTML=""; list.append(el("div","res","读不出来："+e.message)); }
    });
  }
  function newThread(){
    setSid("t"+Date.now().toString(36));
    const S=document.querySelector("#stream");
    if(S)S.innerHTML="";
    go("chat"); say("开了一个新窗口 —— 它还记得你们所有事，只是这窗是干净的");
  }
  async function renderThread(){
    const S=document.querySelector("#stream"); if(!S)return;
    const sid=getSid();
    S.innerHTML="";
    try{
      const j=await jget("/api/nest/thread?sid="+encodeURIComponent(sid)+"&limit=120");
      const its=(j.items||[]).filter(x=>(x.role==="user"||x.role==="assistant")&&!x.hidden);
      if(!its.length)S.append(el("div","hint","这个窗口还是空的。说点什么吧。"));
      its.forEach(it=>{
        if(typeof addTurn==="function")
          addTurn({id:it.id,role:it.role,content:it.content,think:it.think,
                   tools:it.tools,t:hm(it.ts),ts:it.ts});
      });
      try{toBottom(true);}catch(e){}
    }catch(e){ S.append(el("div","errbox","历史读不出来："+e.message)); }
  }

  /* ── 搜索 ── */
  function openSearch(){
    sheet("搜索聊天与记忆", box=>{
      const i=el("input"); i.type="text"; i.placeholder="打一个词，回车";
      const out=el("div"); box.append(i,out);
      let t=0;
      const run=async()=>{
        const q=i.value.trim(); out.innerHTML="";
        if(!q)return;
        try{
          const j=await jget("/api/search?q="+encodeURIComponent(q));
          const its=j.items||[];
          if(!its.length)out.append(el("div","res","没找到"));
          its.forEach(r=>{
            const d=el("div","res");
            d.append(el("div","k",r.kind||""));
            d.append(el("div","tt",(r.content||"").slice(0,140)));
            d.onclick=async()=>{try{await navigator.clipboard.writeText(r.content||"");say("复制了这一条");}catch(e){}};
            out.append(d);
          });
        }catch(e){ out.append(el("div","res","搜索失败："+e.message)); }
      };
      i.oninput=()=>{clearTimeout(t);t=setTimeout(run,320);};
      i.addEventListener("keydown",e=>{if(e.key==="Enter")run();});
      setTimeout(()=>{try{i.focus();}catch(e){}},60);
    });
  }

  /* ── MCP ── */
  function openMcp(){
    sheet("MCP 工具包", async box=>{
      const out=el("div"); box.append(out); out.append(el("div","res","读取中…"));
      let j;
      try{ j=await jget("/api/mcp"); }
      catch(e){ out.innerHTML=""; out.append(el("div","res","读不出来："+e.message)); return; }
      out.innerHTML="";
      const list=Array.isArray(j)?j:(j.servers||j.items||j.list||null);
      if(Array.isArray(list)&&list.length){
        list.forEach(s=>{
          const nm=(typeof s==="string")?s:(s.name||s.id||s.title||"?");
          let on=(typeof s==="object")?(s.enabled!==false&&s.on!==false):true;
          const tn=el("div","tn",on?"已启用":"已关闭");
          const r=el("div","thr"); r.append(el("div","tt",nm),tn);
          r.onclick=async()=>{
            try{
              const rr=await fetch("/api/mcp/toggle",{method:"POST",credentials:"same-origin",
                headers:{"Content-Type":"application/json"},body:JSON.stringify({name:nm,enabled:!on})});
              if(rr.ok){ on=!on; tn.textContent=on?"已启用":"已关闭"; say(nm+(on?" 开":" 关")); }
              else say("开关键失败："+(await rr.text()).slice(0,60));
            }catch(e){ say("切换失败"); }
          };
          out.append(r);
        });
      }else{
        out.append(el("div","res","（下面是后端真实返回，我照它改界面）"));
        out.append(el("pre","js",JSON.stringify(j,null,1).slice(0,2500)));
      }
    });
  }

  /* ── 挂上去 ── */
  const col=document.querySelector("#chatCol");
  if(col)col.append(nav); else document.body.append(nav);
  document.body.append(pane);
  barBtn("＋","新对话",openThreads);
  barBtn("🔍","搜索历史",openSearch);
  barBtn("🔧","MCP 工具包",openMcp);
  go("chat");

  let inited=false;
  function maybeInit(){
    if(inited)return;
    const app=document.querySelector("#app");
    if(app&&!app.hidden){
      inited=true;
      setTimeout(()=>{ try{ go("chat"); renderThread(); }catch(e){} },500);
    }
  }
  new MutationObserver(maybeInit).observe(document.body,{attributes:true,subtree:true,attributeFilter:["hidden"]});
  setTimeout(maybeInit,1800);
}catch(e){console.error("nest-tabs:",e);}
})();
