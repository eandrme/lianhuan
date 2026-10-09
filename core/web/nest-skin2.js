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
/* ── ① 统一材质：纸底上的同一块玻璃 ──
   卡片 / 弹层 / 输入框都是：rgba(255,255,255,.42) + blur(18px) saturate(140%)
   + 1px rgba(255,255,255,.65) 描边 + 圆角。没有第二种材质。 */
.nt-card,.set-sec,.mcp-row,.as-row,.mo-head,.ty-card,.ph-card,.cal-mo,
.mem-card,.st-book,.st-ann,.tl-item,.sk-grid>button,.cal-grid button{
  background:var(--glass-bg)!important;
  backdrop-filter:blur(18px) saturate(140%);-webkit-backdrop-filter:blur(18px) saturate(140%);
  border:1px solid var(--glass-line)!important;border-radius:var(--r)!important;
  box-shadow:var(--shadow)}
/* 玻璃卡 hover：轻轻浮起 2px */
@media (hover:hover){
  .nt-card:hover,.set-sec:hover,.ty-card:hover,.ph-card:hover,.mem-card:hover,
  .st-book:hover,.tide-row>*:hover,.cr-card:hover,.cr-note:hover{transform:translateY(-2px)}
}
.set-sec{padding:14px!important}
.nt-card,.set-sec,.ty-card,.ph-card,.mem-card,.st-book,.tide-row>*,.tvi{
  transition:transform .28s ease,box-shadow .28s ease}
.nt-card,.mo-head,.ty-card{padding:13px}
.crow,.thr,.res{border-radius:14px!important;border:1px solid transparent!important;
  box-shadow:none;background:transparent!important}
.crow:hover,.thr:hover,.res:hover{background:var(--panel2)!important}
/* 分隔一律是细横线：1px、宽 32~64px、透明度 30%（不是粗色块），常与一行字并排 */
.hr,.nt-lb,.set-msg{border-color:var(--line)}
hr,.rule,.nt-hr{height:1px;width:48px;border:0;background:currentColor;opacity:.30;
  margin:14px auto;color:var(--latin-c)}
.nt-hr-inline{display:inline-block;vertical-align:middle;margin:0 10px}
/* 分档 / 芯片 / 按钮：一律 1px 青灰描边，**不做胶囊墙** ——
   选中态（.on / .pri）才换成 accent。没有实心色块。 */
.nt-chips button,.set-chips button,.nt-top button,.set-btns button,
.st-tabs button,.mem-chips button,.st-top button,.st-nav button,.st-row button,
.mem-bar button,.mem-card .ops button{
  border-radius:10px!important;border:1px solid var(--ink-1);background:transparent;
  color:var(--dim);font-size:13px;letter-spacing:.04em;
  display:inline-flex;align-items:center;justify-content:center;gap:5px;
  transition:color .25s ease,border-color .25s ease,background-color .25s ease,transform .2s ease}
.nt-chips button.on,.set-chips button.on{color:var(--accent);border-color:var(--accent);
  background:color-mix(in srgb,var(--accent) 10%,transparent)}
.nt-chips button:active,.set-chips button:active{transform:scale(.97)}
.nt-top button.pri,.set-btns button.pri{color:var(--accent);border-color:var(--accent);
  background:color-mix(in srgb,var(--accent) 10%,transparent)}
/* ── ①B 各模块自己画的那几套控件，一并收编到同一套规矩里 ──
   按钮一律 1px 青灰描边、没有实心色块、不做胶囊；只有 .pri / .on 用 accent。 */
.cr-top button,.cr-row button,.cr-h button,.cr-btns button,.mcp-hdrow button,
.nt-btns button,.sk-btns button,.st-top button,.st-nav button,.st-row button,
.mem-bar button,.mem-card .ops button,.nt-top button{
  border-radius:10px!important;border:1px solid var(--ink-1)!important;
  background:transparent!important;color:var(--dim)}
.cr-top button.pri,.cr-btns button.pri,.nt-btns button.pri,.set-btns button.pri,
.st-row button.pri,.mem-edit .row button.pri,.mcp-hdrow button.pri{
  border-color:var(--accent)!important;color:var(--accent)!important;background:transparent!important}
.cr-row button.danger,.mem-card .ops button.danger{
  color:var(--err)!important;border-color:var(--err)!important}
/* 那几枚「状态胶囊」也放平：1px 青灰，不要 999px 的圆头 */
.mcp-sw,.nest-off{border-radius:10px!important;border:1px solid var(--ink-1)!important;
  background:transparent!important;color:var(--tx-2)!important}
.mcp-sw.on,.mcp-sw.cur{border-color:var(--accent)!important;color:var(--accent)!important}
/* 剩下的卡片：还是那一块玻璃 */
.cr-card,.cr-note,.cr-row,.hrow{border-color:var(--line)}
.cr-card,.cr-note{background:var(--glass-bg)!important;border:1px solid var(--glass-line)!important;
  border-radius:var(--r)!important;box-shadow:var(--shadow)}
/* 元信息 / 拉丁小标：10~13px、字距 .24em、#8A95A2 */
.cr-h,.cr-card .ct,.cr-note .who,.st-ann .who,.set-slide .v,.mcp-meta,.mcp-tag,
.mem-card .meta,.st-meta,.mo-row .v,.usage,.nt-meta,.as-mid .mt{
  font-family:var(--latin);font-size:10px;letter-spacing:.24em;color:var(--latin-c)}
/* 次要文字 */
.cr-card .nt,.set-sec .sub,.set-msg,.set-kv,.cr-row .nt{color:var(--tx-2)}
/* 输入框：跟卡片同一块玻璃（同样是 .42 + 泛白描边） */
.nt-in,.set-in,.sheet input[type=text],#pane input[type=text],.sheet textarea,.nt-sheet textarea,
.mem-bar input,.mem-edit textarea,.mem-edit select,.mem-edit input,
.cr-in,#cr-body,.cr-sheet textarea,.sk-row input[type=text]{
  background:var(--glass-bg)!important;border:1px solid var(--glass-line)!important;
  border-radius:14px!important;color:var(--fg);letter-spacing:.02em}
:root[data-moon="1"] .nt-in,:root[data-moon="1"] .set-in,
:root[data-moon="1"] .sheet input[type=text],:root[data-moon="1"] .sheet textarea,
:root[data-moon="1"] .mem-bar input,:root[data-moon="1"] .mem-edit textarea,
:root[data-moon="1"] .mem-edit select,:root[data-moon="1"] .mem-edit input{
  background:var(--glass-bg)!important}
.nt-in:focus,.set-in:focus,.sheet input[type=text]:focus,.sheet textarea:focus{
  outline:1px solid var(--accent);outline-offset:1px;border-color:transparent!important}
/* 弹层：同一块玻璃，不另起一种厚度 */
.sheet .box,.nt-sheet{background:var(--glass-bg)!important;
  backdrop-filter:blur(18px) saturate(140%);-webkit-backdrop-filter:blur(18px) saturate(140%);
  border:1px solid var(--glass-line)!important;box-shadow:var(--shadow)!important}
/* 元信息排版：10px、A7B0BB */
.nt-meta,.mcp-meta,.as-mid .mt,.mo-row .v,.usage{font-family:var(--font);
  font-size:10px;letter-spacing:.14em;color:var(--tx-3)}
/* 拉丁标签：Jost、全大写、字距 .24em、10~13px、#8A95A2 */
.en-cap{font-family:var(--latin)!important;font-size:10px;letter-spacing:.24em;
  text-transform:uppercase;color:var(--latin-c)}
/* 大数字（陪伴天数）：68px、accent、字重 400 */
.big-num{font-family:var(--latin);font-size:68px;line-height:1;font-weight:400;color:var(--accent)}
/* 竖排：空态独白与栏目标签用 */
.vtext{writing-mode:vertical-rl;text-orientation:upright;letter-spacing:.22em}
/* ── ② 记忆那一格顶上那张 OUR TIDE ── */
.tide{margin:0 0 16px;padding:18px 16px;text-align:center;border-radius:26px;
  background:var(--glass-bg);backdrop-filter:blur(18px) saturate(140%);
  -webkit-backdrop-filter:blur(18px) saturate(140%);
  border:1px solid var(--glass-line);box-shadow:var(--shadow)}
.tide .cap{font-family:var(--latin);font-size:11px;letter-spacing:.24em;color:var(--latin-c);
  text-transform:uppercase}
.tide .avs{display:flex;justify-content:center;align-items:center;margin:12px 0 4px}
.tide .avs .a{width:46px;height:46px;border-radius:50%;overflow:hidden;
  border:1px solid var(--glass-line);background:var(--panel2);
  display:flex;align-items:center;justify-content:center;
  color:var(--dim2);animation:breathe 4s ease-in-out infinite;transform-origin:50% 50%}
.tide .avs .a+a{margin-left:-14px}
.tide .avs .a img{width:100%;height:100%;object-fit:cover;display:block}
.tide .num{margin-top:8px}
.tide .names{font-size:15px;letter-spacing:.14em;margin-top:6px}
.tide .poem{font-style:italic;color:var(--dim2);font-size:13px;letter-spacing:.06em;margin-top:6px}
.tide .since{font-family:var(--latin);font-size:10px;letter-spacing:.24em;color:var(--latin-c);margin-top:8px}
/* 两条并排的小玻璃卡（时钟 / 位置那种） */
.tide-row{display:flex;gap:10px;margin:0 0 16px}
.tide-row>*{flex:1;min-width:0;padding:12px;border-radius:20px;text-align:center;
  background:var(--glass-bg);border:1px solid var(--glass-line);box-shadow:var(--shadow)}
.tide-row .k{font-family:var(--latin);font-size:10px;letter-spacing:.24em;color:var(--latin-c);
  text-transform:uppercase}
.tide-row .v{font-size:15px;margin-top:6px;letter-spacing:.08em}
/* ── ②B 垂线索引 ─────────────────────────────────────────
   从顶上垂下一条 1px 细线，末端一颗小圆圈节点，旁边是**竖排**标题 + 竖排日期。
   每一条的线长不一样（错落），横着排开，装不下就横向滑。 */
.tvi{display:flex;gap:6px;overflow-x:auto;padding:14px 12px 16px;margin:0 0 16px;
  border-radius:var(--r);background:var(--glass-bg);
  backdrop-filter:blur(18px) saturate(140%);-webkit-backdrop-filter:blur(18px) saturate(140%);
  border:1px solid var(--glass-line);box-shadow:var(--shadow);scrollbar-width:none}
.tvi::-webkit-scrollbar{display:none}
.tvi-cap{display:flex;align-items:center;gap:10px;margin:0 0 8px;padding:0 2px}
.tvi-cap .ln{height:1px;width:48px;background:currentColor;opacity:.30;color:var(--latin-c);
  flex:0 0 auto}
.tvi-cap .en{font-family:var(--latin);font-size:10px;letter-spacing:.24em;color:var(--latin-c);
  text-transform:uppercase}
.tvi-col{flex:0 0 auto;display:flex;flex-direction:column;align-items:center;
  min-width:30px;padding:0 5px;cursor:default}
.tvi-line{width:1px;background:var(--ink-3);opacity:.55}
.tvi-node{width:6px;height:6px;border-radius:50%;border:1px solid var(--ink-1);
  background:var(--paper);margin:-1px 0 8px;flex:0 0 auto}
.tvi-txt{display:flex;align-items:flex-start;gap:7px}
.tvi-title{writing-mode:vertical-rl;text-orientation:upright;
  font-size:13px;letter-spacing:.18em;line-height:1;color:var(--tx-1);max-height:96px;
  overflow:hidden}
.tvi-date{writing-mode:vertical-rl;text-orientation:upright;font-family:var(--latin);
  font-size:10px;letter-spacing:.24em;line-height:1;color:var(--latin-c);max-height:96px}
.tvi-empty{padding:4px 8px;font-size:12px;color:var(--dim2)}
/* ── ③ 头像那一节 ── */
.ava-row{display:flex;align-items:center;gap:14px;margin:10px 0}
.ava-pick{width:64px;height:64px;border-radius:50%;overflow:hidden;flex:0 0 64px;
  animation:breathe 4s ease-in-out infinite;transform-origin:50% 50%;
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

  /* ── ②B 垂线索引 ──────────────────────────────────────
     记忆页在 OUR TIDE 下面多一条索引：一串从顶上垂下来的细线。
     每一条＝一条真记过的记忆（内容当竖排标题、记下它的日子当竖排日期），
     线长各不相同，所以一排看过去是**错落**的。一条记忆都没有就不画这一块。 */
  const LINE_LEN=[30,58,16,74,40,64,22,52];   /* 每条线垂下来多长：错落感就在这儿 */
  function indexCol(it,ord){
    const col=el("div","tvi-col");
    const line=el("div","tvi-line");
    line.style.height=LINE_LEN[ord%LINE_LEN.length]+"px";
    const node=el("div","tvi-node");
    const txt=el("div","tvi-txt");
    const title=el("div","tvi-title");
    title.textContent=String(it.content||it.title||"（空的）").replace(/\s+/g," ").trim().slice(0,14);
    txt.append(title);
    const day=String(it.day||it.date||"").trim();
    if(day){
      const d=el("div","tvi-date");
      d.textContent=day.replace(/-/g,".");
      txt.append(d);
    }
    col.append(line,node,txt);
    if(it.content)col.title=String(it.content).slice(0,120);
    return col;
  }
  async function tideIndex(){
    let items=[];
    try{
      const j=await jget("/api/memory/all?limit=40");
      items=(j&&j.items)||[];
    }catch(e){ return null; }
    /* 按天去重：一天只出一条，日期新的排前面 —— 索引是「这条线上有哪些天」 */
    const seen={}, pick=[];
    items.slice().sort((a,b)=>String(b.day||"").localeCompare(String(a.day||"")))
      .forEach(it=>{
        const d=String(it.day||it.date||"");
        if(d&&seen[d])return;
        if(d)seen[d]=1;
        if(pick.length<8)pick.push(it);
      });
    if(!pick.length)return null;
    const wrap=el("div");
    const cap=el("div","tvi-cap");
    cap.append(el("span","ln"),el("span","en","MEMORY INDEX"));
    const strip=el("div","tvi");
    pick.forEach((it,i)=>strip.append(indexCol(it,i)));
    wrap.append(cap,strip);
    return wrap;
  }

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
        const idx=await tideIndex();
        if(idx)head.append(idx);
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
