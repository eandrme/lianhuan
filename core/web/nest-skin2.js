/* ══════════════════════════════════════════════════════════
   巢 · 皮肤 ⑫：和纸墨晕 × 海沫玻璃（最后一层，压在所有模块之上）

   装法：nest.html 里放在**最后一行**（要能压过各模块自己注入的样式）
        <script src="/nest-skin2.js?v=1"></script>

   这一层做三件事：
     ① 把各模块自己画的那堆卡片 / 弹层 / 按钮 / 输入框，统一成**同一种材质**：
        纸底上的半透明玻璃 —— 描边泛白、极淡青灰阴影，绝不用纯黑阴影。
     ② 记忆那一格顶上那张 **✦ OUR TIDE ✦**：两个头像轻轻交叠、陪伴天数、
        名字、一句斜体诗、since …。数字是从真实的聊天记录里算的（没有就老实不显示）。
     ③ 「我的」里加一节**头像**：他和我的都要能传图（走 /api/upload，存 /api/config）。
   ══════════════════════════════════════════════════════════ */
(function(){
"use strict";
try{
  const $=(s,r=document)=>r.querySelector(s);
  const el=(t,c,x)=>{const e=document.createElement(t);if(c)e.className=c;if(x!=null)e.textContent=x;return e;};
  const say=t=>{try{if(typeof toast==="function")toast(t);}catch(e){}};
  const jget=async u=>{
    const r=await fetch(u,{credentials:"same-origin"});
    if(!r.ok)throw new Error("HTTP "+r.status);
    return r.json();
  };
  const jpost=async(u,b)=>{
    let r;
    try{
      r=await fetch(u,{method:"POST",credentials:"same-origin",
        headers:{"Content-Type":"application/json"},body:JSON.stringify(b||{})});
    }catch(e){ return {ok:false,err:"连不上服务器"}; }
    let d=null; try{ d=await r.json(); }catch(e){}
    if(!r.ok||!d||d.ok===false)return {ok:false,status:r.status,err:(d&&(d.err||d.error))||("HTTP "+r.status)};
    return d;
  };

  const css=document.createElement("style");
  css.textContent=`
/* ── ① 统一材质：纸底上的玻璃 ── */
.nt-card,.set-sec,.mcp-row,.as-row,.mo-head,.ty-card,.ph-card,.cal-mo,
.sk-grid>button,.cal-grid button,.crow,.thr,.res,.tl-item{
  background:var(--glass-bg)!important;
  backdrop-filter:blur(16px) saturate(140%);-webkit-backdrop-filter:blur(16px) saturate(140%);
  border:1px solid var(--glass-line)!important;border-radius:var(--r)!important;
  box-shadow:var(--shadow)}
.set-sec{padding:14px!important}
.nt-card,.mo-head,.ty-card{padding:13px}
.crow,.thr,.res{border-radius:14px!important;border:1px solid transparent!important;
  box-shadow:none;background:transparent!important}
.crow:hover,.thr:hover,.res:hover{background:var(--panel2)!important}
/* 分隔就用细横线：1px、短、透明（不是粗色块） */
.hr,.nt-lb,.set-msg{border-color:var(--line)}
hr,.rule{height:1px;width:48px;border:0;background:currentColor;opacity:.28;margin:14px auto;color:var(--dim2)}
/* 药丸（分档 / 芯片） */
.nt-chips button,.set-chips button,.nt-top button,.set-btns button{
  border-radius:999px!important;border:1px solid var(--line);background:var(--panel2);
  color:var(--dim);font-size:13px;letter-spacing:.04em;
  display:inline-flex;align-items:center;justify-content:center;gap:5px;
  transition:color .25s ease,border-color .25s ease,transform .2s ease}
.nt-chips button.on,.set-chips button.on{color:var(--accent);border-color:var(--accent);
  background:color-mix(in srgb,var(--accent) 10%,transparent)}
.nt-chips button:active,.set-chips button:active{transform:scale(.97)}
.nt-top button.pri,.set-btns button.pri{color:var(--accent);border-color:var(--accent);
  background:color-mix(in srgb,var(--accent) 10%,transparent)}
/* 输入框：纸上的浅槽 */
.nt-in,.set-in,.sheet input[type=text],#pane input[type=text],.sheet textarea,.nt-sheet textarea{
  background:rgba(255,255,255,.30)!important;border:1px solid var(--line)!important;
  border-radius:14px!important;color:var(--fg);letter-spacing:.02em}
:root[data-moon="1"] .nt-in,:root[data-moon="1"] .set-in,
:root[data-moon="1"] .sheet input[type=text],:root[data-moon="1"] .sheet textarea{
  background:rgba(255,255,255,.06)!important}
.nt-in:focus,.set-in:focus,.sheet input[type=text]:focus,.sheet textarea:focus{
  outline:1px solid var(--accent);outline-offset:1px;border-color:transparent!important}
/* 弹层 */
.sheet .box,.nt-sheet{background:var(--glass-bg)!important;
  backdrop-filter:blur(22px) saturate(150%);-webkit-backdrop-filter:blur(22px) saturate(150%);
  border:1px solid var(--glass-line)!important;box-shadow:var(--shadow)!important}
/* 元信息排版：小、宽字距、全大写那种安静感 */
.nt-meta,.mcp-meta,.as-mid .mt,.mo-row .v,.usage,.turn .meta{
  font-family:var(--mono);letter-spacing:.10em}
/* 大数字（陪伴天数那种） */
.big-num{font-family:var(--mono);font-size:58px;line-height:1;font-weight:400;color:var(--accent)}
.en-cap{font-family:var(--mono);font-size:9.5px;letter-spacing:.24em;text-transform:uppercase;
  color:var(--var-dim2,var(--dim2))}
.vtext{writing-mode:vertical-rl;text-orientation:upright;letter-spacing:.22em}
/* ── ② 记忆那一格顶上那张 OUR TIDE ── */
.tide{margin:0 0 16px;padding:18px 16px;text-align:center;border-radius:26px;
  background:var(--glass-bg);backdrop-filter:blur(18px) saturate(140%);
  -webkit-backdrop-filter:blur(18px) saturate(140%);
  border:1px solid var(--glass-line);box-shadow:var(--shadow)}
.tide .cap{font-family:var(--mono);font-size:9.5px;letter-spacing:.3em;color:var(--dim2);
  text-transform:uppercase}
.tide .avs{display:flex;justify-content:center;align-items:center;margin:12px 0 4px}
.tide .avs .a{width:46px;height:46px;border-radius:50%;overflow:hidden;
  border:1px solid var(--glass-line);background:var(--panel2);
  display:flex;align-items:center;justify-content:center;
  color:var(--dim2);animation:breathe 4s ease-in-out infinite}
.tide .avs .a+a{margin-left:-14px}
.tide .avs .a img{width:100%;height:100%;object-fit:cover;display:block}
.tide .num{margin-top:8px}
.tide .names{font-size:15px;letter-spacing:.14em;margin-top:6px}
.tide .poem{font-style:italic;color:var(--dim2);font-size:13px;letter-spacing:.06em;margin-top:6px}
.tide .since{font-family:var(--mono);font-size:9.5px;letter-spacing:.18em;color:var(--dim2);margin-top:8px}
/* 两条并排的小玻璃卡（时钟 / 位置那种） */
.tide-row{display:flex;gap:10px;margin:0 0 16px}
.tide-row>*{flex:1;min-width:0;padding:12px;border-radius:20px;text-align:center;
  background:var(--glass-bg);border:1px solid var(--glass-line);box-shadow:var(--shadow)}
.tide-row .k{font-family:var(--mono);font-size:9.5px;letter-spacing:.2em;color:var(--dim2);
  text-transform:uppercase}
.tide-row .v{font-size:15px;margin-top:6px;letter-spacing:.08em}
/* ── ③ 头像那一节 ── */
.ava-row{display:flex;align-items:center;gap:14px;margin:10px 0}
.ava-pick{width:64px;height:64px;border-radius:50%;overflow:hidden;flex:0 0 64px;
  border:1px solid var(--glass-line);background:var(--panel2);
  display:flex;align-items:center;justify-content:center;color:var(--dim2)}
.ava-pick img{width:100%;height:100%;object-fit:cover;display:block}
.ava-row .mid{flex:1;min-width:0}
.ava-row .mid b{font-size:14px;font-weight:500;letter-spacing:.08em}
.ava-row .mid div{font-size:11.5px;color:var(--dim2);margin-top:3px}
`;
  document.head.append(css);

  /* ── ✦ OUR TIDE ✦ ──────────────────────────────────────
     天数从**真的聊天记录**里算：/api/chat/heat 给的是「每天几句」，
     取最早的那天当「在一起的第一天」。一条记录都没有就不显示那个数字 ——
     宁可少一块，也不编一个数出来。 */
  const pad2=n=>String(n).padStart(2,"0");
  function daysFrom(heat){
    const days=Object.keys(heat||{}).filter(d=>/^\d{4}-\d{2}-\d{2}$/.test(d)).sort();
    if(!days.length)return null;
    const first=new Date(days[0]+"T00:00:00");
    const now=new Date();
    const d0=new Date(now.getFullYear(),now.getMonth(),now.getDate());
    return {days:Math.max(1,Math.round((d0-first)/86400000)+1), since:days[0]};
  }
  function avBox(who,iconName){
    const b=el("div","a");
    const A=(window.nestIdent&&window.nestIdent.get&&window.nestIdent.get()[who])||{};
    const u=(A.avatar||"").trim();
    if(/^(\/|https?:|data:image)/i.test(u)){
      const im=el("img"); im.src=u; im.alt="";
      im.onerror=()=>{ b.innerHTML=""; b.append(nestIcon(iconName,20)); };
      b.append(im);
    }else{
      b.append(nestIcon(iconName,20));
    }
    return b;
  }
  async function buildTide(){
    const card=el("div","tide");
    const cap=el("div","cap");
    cap.append(nestIcon("star",11),document.createTextNode(" OUR TIDE "),nestIcon("star",11));
    card.append(cap);
    const avs=el("div","avs");
    avs.append(avBox("ai","bot"),avBox("me","person"));
    card.append(avs);
    let info=null;
    try{ const h=await jget("/api/chat/heat"); info=daysFrom(h.heatmap||h.heat||{}); }
    catch(e){ info=null; }
    if(info){
      card.append(el("div","num big-num",String(info.days)));
      card.append(el("div","cap","DAYS TOGETHER"));
    }
    const A=(window.nestIdent&&window.nestIdent.get().ai)||{};
    const M=(window.nestIdent&&window.nestIdent.get().me)||{};
    card.append(el("div","names",(A.name||"他")+" & "+(M.name||"我")));
    card.append(el("div","poem","Love Like Foam Upon the Sea"));
    card.append(el("div","since",info?("since "+info.since+" · "+info.days+" days of tides together")
                                     :"since the first word you two said"));
    return card;
  }
  const clockRow=()=>{
    const row=el("div","tide-row");
    const c1=el("div"), c2=el("div");
    const now=new Date();
    const wd=["SUN","MON","TUE","WED","THU","FRI","SAT"][now.getDay()];
    c1.append(el("div","k","LOCAL TIME"),
              el("div","v",pad2(now.getHours())+":"+pad2(now.getMinutes())));
    c2.append(el("div","k","TODAY"),
              el("div","v",wd+" · "+pad2(now.getDate())+" "+["JAN","FEB","MAR","APR","MAY","JUN",
                "JUL","AUG","SEP","OCT","NOV","DEC"][now.getMonth()]));
    row.append(c1,c2);
    return row;
  };

  /* 记忆那一格：在它画完之后，把 OUR TIDE 插到最前面 */
  function wrapMemory(){
    const P=window.NEST_PANES;
    if(!P||P.__tide||typeof P.memory!=="function")return;
    const orig=P.memory;
    P.memory=async function(box){
      await orig(box);
      try{
        const head=el("div");
        head.append(await buildTide(),clockRow());
        box.insertBefore(head,box.firstChild);
      }catch(e){ console.error("tide:",e); }
    };
    P.__tide=true;
  }

  /* ── 我的 › 头像：他和我的都要能传图 ──────────────────── */
  const AV_MAX=320;
  function shrink(file,cb){
    let done=false; const fin=v=>{if(!done){done=true;cb(v);}};
    const rd=new FileReader();
    rd.onload=()=>{
      const to=setTimeout(()=>fin(rd.result),8000);
      const im=new Image();
      im.onload=()=>{
        clearTimeout(to);
        try{
          const sc=Math.min(AV_MAX/im.width,AV_MAX/im.height,1);
          const cv=document.createElement("canvas");
          cv.width=Math.max(1,Math.round(im.width*sc)); cv.height=Math.max(1,Math.round(im.height*sc));
          cv.getContext("2d").drawImage(im,0,0,cv.width,cv.height);
          fin(cv.toDataURL("image/jpeg",0.9));
        }catch(e){fin(rd.result);}
      };
      im.onerror=()=>{clearTimeout(to);fin(rd.result);};
      im.src=rd.result;
    };
    rd.onerror=()=>fin(null);
    rd.readAsDataURL(file);
  }
  function avatarSection(box){
    if(box.querySelector("#ava-sec"))return;
    const sec=el("div","set-sec"); sec.id="ava-sec";
    sec.append(el("h4",null,"头像"));
    const sub=el("div","sub");
    sub.append(document.createTextNode("他和我的都传一张。压到 320 再传，存进 "
      +"data/uploads/，配置里只记一条地址（他那位在「助手管理」里也能单独换）。"));
    sec.append(sub);
    [["ai","他","bot","顶栏左边那位；对话里他的气泡那头"],
     ["me","我","person","顶栏右边那颗圆；你说的话那头"]].forEach(([who,label,icon,tip])=>{
      const row=el("div","ava-row");
      const pick=el("div","ava-pick");
      const draw=()=>{
        const A=(window.nestIdent&&window.nestIdent.get()[who])||{};
        pick.innerHTML="";
        const u=(A.avatar||"").trim();
        if(/^(\/|https?:|data:image)/i.test(u)){
          const im=el("img"); im.src=u; im.alt="";
          im.onerror=()=>{ pick.innerHTML=""; pick.append(nestIcon(icon,26)); };
          pick.append(im);
        }else pick.append(nestIcon(icon,26));
      };
      const mid=el("div","mid");
      mid.append(el("b",null,label),el("div",null,tip));
      const ops=el("div","set-btns");
      const bPick=el("button",null,"传一张");
      const bClear=el("button",null,"去掉");
      ops.append(bPick,bClear);
      const msg=el("div","set-msg");
      bPick.onclick=()=>{
        const inp=el("input"); inp.type="file"; inp.accept="image/*"; inp.hidden=true;
        document.body.append(inp);
        inp.addEventListener("change",()=>{
          const f=(inp.files||[])[0]; inp.remove();
          if(!f)return;
          msg.className="set-msg"; msg.textContent="压一下、传上去…";
          shrink(f,async du=>{
            if(!du){ msg.className="set-msg err"; msg.textContent="这张图读不出来"; return; }
            const up=await jpost("/api/upload",{dataURL:du});
            if(!up||!up.url){ msg.className="set-msg err";
              msg.textContent="没传上去："+((up&&up.err)||"网络？"); return; }
            const ok=await window.nestIdent.save(who,{avatar:up.url});
            if(ok){ draw(); msg.className="set-msg ok"; msg.textContent="换好了"; }
            else{ msg.className="set-msg err"; msg.textContent="存不上（服务端太旧？）"; }
          });
        });
        inp.click();
      };
      bClear.onclick=async()=>{
        const ok=await window.nestIdent.save(who,{avatar:""});
        draw();
        msg.className=ok?"set-msg":"set-msg err";
        msg.textContent=ok?"去掉了":"没去掉";
      };
      row.append(pick,mid,ops,msg);
      sec.append(row);
      draw();
    });
    /* 名字也可以在这儿改（跟头像挨着最顺手） */
    const nmRow=el("div","ava-row");
    const nmMid=el("div","mid");
    nmMid.append(el("b",null,"名字"),el("div",null,"顶栏中间那行字"));
    const nmIn=el("input","set-in"); nmIn.type="text";
    nmIn.value=((window.nestIdent.get().ai||{}).name)||"";
    nmIn.placeholder="他叫什么";
    const nmSave=el("button",null,"存");
    nmSave.onclick=async()=>{
      const ok=await window.nestIdent.save("ai",{name:nmIn.value.trim()});
      say(ok?"改好了":"没改成");
    };
    nmRow.append(nmMid,nmIn,nmSave);
    sec.append(nmRow);
    box.append(sec);
  }

  /* 「我的」那一格画完就把头像那一节塞进去（在助手管理后面） */
  function wrapSetting(){
    const P=window.NEST_PANES;
    if(!P||P.__ava||typeof P.setting!=="function")return;
    const orig=P.setting;
    P.setting=function(box){
      orig(box);
      try{ avatarSection(box); }catch(e){ console.error("ava:",e); }
    };
    P.__ava=true;
  }

  function boot(){
    wrapMemory(); wrapSetting();
    /* 身份读回来之后，把记忆卡里的头像/名字也跟上 */
    if(window.nestIdent&&window.nestIdent.load){
      window.nestIdent.load().then(()=>{
        const t=$(".tide");
        if(t){ const n=t.querySelector(".names");
          const A=window.nestIdent.get().ai||{},M=window.nestIdent.get().me||{};
          if(n)n.textContent=(A.name||"他")+" & "+(M.name||"我");
          const avs=t.querySelector(".avs");
          if(avs){ avs.innerHTML=""; avs.append(avBox("ai","bot"),avBox("me","person")); }
        }
      }).catch(()=>{});
    }
  }
  if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",boot);
  else boot();
  setTimeout(boot,1200);
  window.nestSkin2={tide:buildTide,avatarSection:avatarSection};
}catch(e){console.error("nest-skin2:",e);}
})();
