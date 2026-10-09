/* ══════════════════════════════════════════════════════════
   巢 · 想多深 ⑧：聊天输入框旁边那枚「深度思考」开关
   装法：nest.html 里，nest-setting.js 那行【下面】再加一行
        <script src="/nest-think.js?v=1"></script>

   三档（后端 core/think.py 是唯一的语义出处）：偏快 / 自动 / 偏深。
   `/api/think` GET 读、POST 写。

   ★ 这枚开关**不是摆设** —— 后端把它接到两处：
     ① 一句话进 system（哪家引擎都吃得到）
     ② 档位交给引擎：OpenAI 兼容那条翻成 reasoning_effort（fast→低档、deep→这家
        支持的最高一档），认这个字段的家真会少想/多想；不认的家会被读取报错里的
        可选值、去掉字段重来一次。
   菜单底下那行小字说的就是「你现在这家能照办到什么程度」，不吹。
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
    if(!r.ok||!d||d.ok===false)
      return {ok:false,status:r.status,err:(d&&(d.error||d.err))||("HTTP "+r.status)};
    return d;
  };

  /* ★ 这枚是**开关**：开＝偏深（多想一层），**关＝真的别想**。
     ⚠ 「关」必须真的发 `reasoning_effort:"none"`，不能是「什么都不发」——
       后者是「由这家自己定」，而 DeepSeek 这类默认就是 high：人明明关了，
       屏幕上照样满屏思考过程（真机上撞的，就是这个）。
     「偏快」「自动」是另外两种状态，按钮上照实写（快 / 自动），
     点一下是打开深度思考；想选回它们：长按（或右键）出菜单，设置页里也有同一份。 */
  const ON_MODE="deep", OFF_MODE="off";
  const SHORT={off:"关",fast:"快",auto:"自动",deep:"开"};
  const ORDER=["off","fast","auto","deep"];
  const FALLBACK_LABEL={off:"别想",fast:"偏快",auto:"自动",deep:"偏深"};
  const FALLBACK_NOTE={off:"关掉：让它别再想（真的把推理档打到最低）",
                       fast:"少想一点，答得快些",
                       auto:"不动它，由这家自己定 —— 它可能默认想得很深",
                       deep:"多想一层再答，慢一些"};
  const DONE={off:"好，我不兜圈子了",fast:"好，我说快些",
              auto:"好，我自己看着办",deep:"好，我多想一层"};

  const css=document.createElement("style");
  css.textContent=`
#btnThink{display:inline-flex;align-items:center;justify-content:center;gap:2px;
  height:38px;padding:0 9px;border-radius:var(--r-sm);color:var(--dim);
  font-size:13.5px;flex:0 0 auto;white-space:nowrap}
#btnThink:hover{background:var(--panel2);color:var(--fg)}
#btnThink[data-on="1"]{color:var(--accent);background:color-mix(in srgb,var(--accent) 16%,transparent);
  border:1px solid color-mix(in srgb,var(--accent) 45%,transparent)}
#btnThink[data-m="fast"]{color:var(--warn);background:color-mix(in srgb,var(--warn) 14%,transparent)}
#btnThink[data-m="unknown"]{color:var(--dim2)}
.tk-hd{font-size:11.5px;color:var(--dim2);padding:6px 10px 4px}
.tk-b{display:flex;align-items:flex-start;gap:8px;padding:8px 10px;border-radius:7px;
  font-size:14px;width:100%;text-align:left}
.tk-b:hover{background:var(--panel2)}
.tk-b .ck{flex:0 0 15px;color:var(--accent);font-size:13px;line-height:1.5}
.tk-b .tx{flex:1;min-width:0}
.tk-b .s{display:block;font-size:11.5px;color:var(--dim2);margin-top:2px;line-height:1.5}
.tk-ft{font-size:11.5px;color:var(--dim2);border-top:1px solid var(--line);
  margin-top:4px;padding:6px 10px 2px;line-height:1.6}
`;
  document.head.append(css);

  let cur="auto", labels={}, notes={}, engNote="", canMute=null, loaded=false, menu=null;
  let warned=false;

  const btn=el("button",""); btn.id="btnThink"; btn.type="button";
  const row=$("#composer .row");
  if(row){
    const att=$("#btnAtt"), send=$("#btnSend");
    row.insertBefore(btn, att||send||null);
  }else{
    // 找不到输入框（老页面）就不硬塞 —— 但也不能静默：说一句
    console.warn("nest-think: 没找到 #composer .row，开关没装上");
  }

  function paint(){
    const on=(cur===ON_MODE);
    btn.dataset.m=loaded?cur:"unknown";
    btn.dataset.on=(loaded&&on)?"1":"0";
    btn.textContent="🧠"+(loaded?(SHORT[cur]||"关"):"…");
    const label=(labels[cur]||FALLBACK_LABEL[cur]||cur);
    const note=(notes[cur]||FALLBACK_NOTE[cur]||"");
    btn.title=loaded
      ? ("深度思考："+(on?"开":"关")+"（现在是「"+label+"」—— "+note+"）\n点一下"
         +(on?"关掉（真的别想）":"打开（多想一层）")
         +((cur!=="off"&&cur!=="deep")?("（现在是「"+label+"」那一档，点一下就是打开深度思考）"):"")
         +"\n长按（或右键）可以选：别想 / 偏快 / 自动 / 偏深"
         +(engNote?("\n现在这家："+engNote):"")
         +((cur==="off"&&canMute===false)?("\n⚠ 这条引擎路上「关」关不掉它的思考 —— "+engNote):""))
      : "深度思考：还没读到服务端的档位（点一下试试）";
    btn.setAttribute("aria-label",btn.title);
  }

  async function load(){
    try{
      const j=await jget("/api/think");
      if(j&&j.mode in SHORT){
        cur=j.mode;
        labels=j.labels||{}; notes=j.notes||{}; engNote=j.engine_note||"";
        canMute=j.can_mute;
        loaded=true;
      }
    }catch(e){
      // ★ 读不到就**不画一个假的档位**：按钮上写「…」，菜单里说实话
      loaded=false;
      if(!warned){ warned=true; }
    }
    paint();
  }

  async function pick(m){
    if(m===cur&&loaded){ return; }
    const before=cur;
    cur=m; loaded=true; paint();          // 先动，手感要跟手
    const r=await jpost("/api/think",{mode:m});
    if(!r.ok){
      cur=before; paint();                // 没存上就退回原样，别骗人
      say("没换成："+(r.err||"?"));
      return;
    }
    say(DONE[m]||("换成「"+(labels[m]||FALLBACK_LABEL[m])+"」了"));
    if(menu){ menu.remove(); menu=null; }
    load();                               // 回头再问一次服务端（比如引擎换了，那行小字要变）
  }

  function openMenu(){
    document.querySelectorAll(".menu").forEach(x=>x.remove());
    const m=el("div","menu");
    m.style.minWidth="236px";
    m.append(el("div","tk-hd","想多深（这一句起生效）"));
    ORDER.forEach(k=>{
      const b=el("button","tk-b");
      const tx=el("span","tx");
      tx.append(el("b",null,labels[k]||FALLBACK_LABEL[k]));
      tx.append(el("span","s",notes[k]||FALLBACK_NOTE[k]));
      b.append(el("span","ck",(k===cur&&loaded)?"✓":""),tx);
      b.onclick=()=>pick(k);
      m.append(b);
    });
    m.append(el("div","tk-ft", loaded
      ? ("现在这家："+(engNote||"（这一档怎么落地，取决于引擎）"))
      : "读不到服务端的档位 —— 可能还没登录，或者服务端是旧版本"));
    document.body.append(m);
    const r=btn.getBoundingClientRect();
    m.style.top=Math.max(8,(r.top-8-m.offsetHeight))+"px";
    m.style.left=Math.max(8,Math.min(r.left,innerWidth-m.offsetWidth-8))+"px";
    menu=m;
    setTimeout(()=>document.addEventListener("click",()=>{ if(menu){menu.remove();menu=null;} },{once:true}),0);
  }

  /* ── 开关本身：点一下就是开/关 ──
     开＝偏深、关＝自动（自动这一档什么参数都不发、什么话都不加，跟从前一字不差）。
     三档菜单留给长按 / 右键 —— 偏快那一档平时用不到，但别把它藏没了。 */
  async function toggle(){
    if(!loaded){
      await load();
      if(!loaded){ say("读不到服务端的档位，先别拨 —— 可能是旧版服务端或者没登录"); return; }
    }
    await pick(cur===ON_MODE ? OFF_MODE : ON_MODE);
  }

  let lpTimer=null, lpFired=false;
  btn.addEventListener("pointerdown",()=>{
    lpFired=false;
    lpTimer=setTimeout(()=>{ lpTimer=null; lpFired=true; openMenu(); },550);
  });
  ["pointerup","pointerleave","pointercancel"].forEach(ev=>
    btn.addEventListener(ev,()=>{ if(lpTimer){ clearTimeout(lpTimer); lpTimer=null; } }));
  btn.addEventListener("contextmenu",e=>{ e.preventDefault(); openMenu(); });
  btn.onclick=e=>{
    e.stopPropagation();
    if(lpFired){ lpFired=false; return; }        // 长按已经开过菜单了，别再顺手拨一下
    if(menu){ menu.remove(); menu=null; return; }
    toggle();
  };

  /* 刚进页面时口令还没登录，这一问会 401 —— 门一开重读一遍 */
  const app=$("#app");
  if(app){
    new MutationObserver(()=>{ if(!app.hidden)load(); })
      .observe(app,{attributes:true,attributeFilter:["hidden"]});
  }
  load();
}catch(e){console.error("nest-think:",e);}
})();
