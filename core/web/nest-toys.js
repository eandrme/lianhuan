/* ══════════════════════════════════════════════════════════
   巢 · 玩具箱 ⑪：他做的小玩意都在这儿

   装法：nest.html 里加一行
        <script src="/nest-toys.js?v=1"></script>

   后端本来就是齐的（原项目那套）：`data/plays/*.html` 就是玩具本身，
     GET  /api/plays            → 清单（读每个文件的 <title> 当名字）
     GET  /plays/<file>         → 那个网页
     write_play / list_plays    → 他自己写、自己看（AI 的手）
   这一版补的是**界面**，外加两件人能做的事：
     POST /api/plays/new        → 戳他现做一个（真用引擎写，写不出来老实说）
     POST /api/plays/<f>/del    → 不喜欢了划掉

   ※ 玩的时候用 `<iframe sandbox="allow-scripts">`：小玩意是**同一个域名**下的网页，
     不给 sandbox 的话它能伸手摸到外层页面（也就摸得到你的会话）。
     副作用：它自己的 localStorage 会被挡（要存档的小玩意用「新窗口打开」）。
   ══════════════════════════════════════════════════════════ */
(function(){
"use strict";
try{
  window.NEST_PANES=window.NEST_PANES||{};
  const el=(t,c,x)=>{const e=document.createElement(t);if(c)e.className=c;if(x!=null)e.textContent=x;return e;};
  const say=t=>{try{if(typeof toast==="function")toast(t);}catch(e){}};
  const jget=async u=>{
    const r=await fetch(u,{credentials:"same-origin"});
    if(!r.ok)throw new Error(r.status===404?"没有这个接口（HTTP 404）":"HTTP "+r.status);
    return r.json();
  };
  const jpost=async(u,b)=>{
    let r;
    try{
      r=await fetch(u,{method:"POST",credentials:"same-origin",
        headers:{"Content-Type":"application/json"},body:JSON.stringify(b||{})});
    }catch(e){ return {ok:false,err:"连不上服务器"}; }
    let d=null; try{ d=await r.json(); }catch(e){}
    if(!r.ok||!d||d.ok===false)
      return {ok:false,status:r.status,err:(d&&(d.err||d.error))||("HTTP "+r.status)};
    return d;
  };

  const css=document.createElement("style");
  css.textContent=`
.ty-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:10px}
.ty-card{border:1px solid var(--line);background:var(--panel);border-radius:var(--r);
  padding:12px;display:flex;flex-direction:column;gap:8px}
.ty-card b{font-size:15px;line-height:1.35}
.ty-card .fn{font:11.5px var(--mono);color:var(--dim2);word-break:break-all}
.ty-card .ops{display:flex;gap:6px;margin-top:auto}
.ty-card .ops button{flex:1;padding:8px 6px;border-radius:9px;border:1px solid var(--line);
  background:var(--panel2);color:var(--dim);font-size:13px}
.ty-card .ops button.play{border-color:var(--accent);color:var(--accent)}
.ty-card .ops button.danger{color:var(--err);border-color:var(--err)}
.ty-frame{position:fixed;inset:0;z-index:70;background:var(--bg);display:flex;flex-direction:column}
.ty-frame .hd{display:flex;align-items:center;gap:8px;padding:10px 12px;
  border-bottom:1px solid var(--line);background:var(--bg)}
.ty-frame .hd b{flex:1;min-width:0;font-size:14px;overflow:hidden;text-overflow:ellipsis;
  white-space:nowrap}
.ty-frame .hd button{padding:6px 10px;border-radius:8px;border:1px solid var(--line);
  color:var(--dim);font-size:12.5px}
.ty-frame iframe{flex:1;width:100%;border:0;background:#fff}
.ty-frame .hint{padding:6px 12px;font-size:11.5px;color:var(--dim2);border-top:1px solid var(--line)}
`;
  document.head.append(css);

  window.NEST_PANES.toys=function(box){
    box.innerHTML="";
    const top=el("div","nt-top");
    const bNew=el("button","pri");
    bNew.append(nestIcon("plus",15),document.createTextNode("让他做一个"));
    const bReload=el("button",null,"刷新");
    const sp=el("div","sp");
    top.append(bNew,sp,bReload);
    const msg=el("div","hint","");
    const list=el("div");
    box.append(top,msg,list);

    async function load(){
      list.innerHTML="";
      list.append(el("div","hint","翻一下…"));
      let j;
      try{ j=await jget("/api/plays"); }
      catch(e){
        list.innerHTML="";
        msg.className="hint";
        msg.textContent="读不出来："+e.message+"（服务端太旧就得重启一下）";
        return;
      }
      const its=j.items||[];
      msg.textContent = its.length
        ? (its.length+" 个小玩意 —— 点「玩」就在这儿打开（同一个域名下的网页，我给它们加了沙箱）")
        : "";
      list.innerHTML="";
      if(!its.length){
        list.append(el("div","hint","玩具箱还空着。点上面「让他做一个」，"
          +"他会现写一个自包含的小网页丢进来。"));
        return;
      }
      const grid=el("div","ty-grid");
      its.forEach(x=>{
        const c=el("div","ty-card");
        c.append(el("b",null,x.title||x.file));
        c.append(el("div","fn",x.file||""));
        const ops=el("div","ops");
        const bPlay=el("button","play","玩");
        const url="/plays/"+encodeURIComponent(x.file||"");
        bPlay.onclick=()=>openToy(x.title||x.file, url);
        const bTab=el("button",null,"新窗口");
        bTab.title="要存档 / 联网的小玩意用这个（沙箱里不让它存东西）";
        bTab.onclick=()=>window.open(url,"_blank","noopener");
        const bDel=el("button","danger","删");
        bDel.onclick=async()=>{
          if(!confirm("把这个小玩意删掉？（"+x.file+"）文件会从 data/plays 里没掉。"))return;
          const r=await jpost("/api/plays/"+encodeURIComponent(x.file||"")+"/del",{});
          if(r.ok){ say("删了"); load(); }
          else{ msg.className="hint"; msg.textContent="删不掉："+(r.err||"?"); }
        };
        ops.append(bPlay,bTab,bDel);
        c.append(ops);
        grid.append(c);
      });
      list.append(grid);
    }

    function openToy(title,url){
      const wrap=el("div","ty-frame");
      const hd=el("div","hd");
      hd.append(el("b",null,title||"小玩意"));
      const bTab=el("button",null,"新窗口");
      bTab.onclick=()=>window.open(url,"_blank","noopener");
      const bX=el("button"); bX.append(nestIcon("close",15));
      bX.onclick=()=>wrap.remove();
      hd.append(bTab,bX);
      const fr=el("iframe");
      fr.src=url;
      /* ※ 沙箱：不给 `allow-same-origin` —— 小玩意是同一个域名下的网页，
         不隔开的话它能摸到外层页面（也就摸得到会话）。代价是它自己的
         localStorage 被挡，要存档的用「新窗口」。 */
      fr.setAttribute("sandbox","allow-scripts");
      fr.setAttribute("referrerpolicy","no-referrer");
      wrap.append(hd,fr,el("div","hint",
        "沙箱里跑：它动不了外面这一页。要存档 / 联网的小玩意，点「新窗口」在真页面里开。"));
      document.body.append(wrap);
    }

    bReload.onclick=load;
    bNew.onclick=()=>{
      const wrap=el("div","sheet"), bx=el("div","box nt-sheet");
      const h=el("div","bh"), t=el("b",null,"让他做一个"), x=el("button","x ibtn");
      x.append(nestIcon("close",15));
      x.onclick=()=>wrap.remove(); h.append(t,x);
      const hint=el("div","hint","他会现写一个自包含的小网页（真用引擎，要花一次调用）。"
        +"想要什么可以写一句，也可以留空让他自己发挥。");
      const inp=el("input","nt-in"); inp.type="text";
      inp.placeholder="比如：一个解压的捏泡泡 / 一个只属于我们的日历";
      const msg=el("div","hint","");
      const row=el("div","nt-btns");
      const ok=el("button","pri","让他做"), no=el("button",null,"算了");
      row.append(ok,no);
      bx.append(h,hint,inp,msg,row);
      wrap.append(bx);
      wrap.onclick=e=>{if(e.target===wrap)wrap.remove();};
      no.onclick=()=>wrap.remove();
      document.body.append(wrap);
      ok.onclick=async()=>{
        ok.disabled=true; ok.textContent="他在做…";
        msg.textContent="正在写（大一点的玩意要等十几秒）…";
        const r=await jpost("/api/plays/new",{hint:inp.value.trim()});
        ok.disabled=false; ok.textContent="让他做";
        if(r.ok){
          msg.textContent="做好了："+(r.title||r.file)+" —— 收下了";
          say("他做了一个："+(r.title||r.file));
          wrap.remove(); load();
        }else{
          msg.textContent="这回没做成："+(r.err||"?");
        }
      };
    };
    load();
  };
}catch(e){console.error("nest-toys:",e);}
})();
