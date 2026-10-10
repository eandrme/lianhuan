/* ══════════════════════════════════════════════════════════
   巢 · 皮肤 ⑫：和纸墨晕 × 海沫玻璃（最后一层，压在所有模块之上）

   装法：nest.html 里放在**最后一行**（要能压过各模块自己注入的样式）
        <script src="/nest-skin2.js?v=1"></script>

   这一层做两件事：
     ① 把各模块自己画的那堆卡片 / 弹层 / 按钮 / 输入框，统一成**同一种材质**：
        纸底上的半透明玻璃 —— 描边泛白、极淡青灰阴影，绝不用纯黑阴影。
     ② 「我的」里加一节**头像与名字**：他和我的都能传图（走 /api/upload，
        存 /api/config），两边的名字也都能改。
   ★ OUR TIDE 那张卡和 MEMORY INDEX 现在长在**主界面**上（nest-home.js）——
     它们是首页的内容，不再往记忆那一格里塞。
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
  .st-book:hover,.cr-card:hover,.cr-note:hover{transform:translateY(-2px)}
}
.set-sec{padding:14px!important}
.nt-card,.set-sec,.ty-card,.ph-card,.mem-card,.st-book{
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
    sec.append(el("h4",null,"头像与名字"));
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
    /* ── 名字：**他和我的都能改** ──
       ★ 两边都走同一条路（nestIdent.save → POST /api/config），
         顶栏那行字、OUR TIDE 里的「A & B」都跟着变。 */
    [["ai","他叫什么","顶栏中间那行字；OUR TIDE 里「… & 我」的左边那位"],
     ["me","我叫什么","OUR TIDE 里「他 & …」的右边那位"]].forEach(([who,ph,tip])=>{
      const row=el("div","ava-row");
      const mid=el("div","mid");
      mid.append(el("b",null,(who==="ai"?"他的名字":"我的名字")),el("div",null,tip));
      const inp=el("input","set-in"); inp.type="text";
      inp.value=((window.nestIdent.get()[who]||{}).name)||"";
      inp.placeholder=ph;
      const save=el("button",null,"存");
      save.onclick=async()=>{
        const ok=await window.nestIdent.save(who,{name:inp.value.trim()});
        say(ok?"改好了":"没改成");
      };
      row.append(mid,inp,save);
      sec.append(row);
    });
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

  function boot(){ wrapSetting(); }
  if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",boot);
  else boot();
  setTimeout(boot,1200);
  window.nestSkin2={avatarSection:avatarSection};
}catch(e){console.error("nest-skin2:",e);}
})();
