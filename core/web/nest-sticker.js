/* ══════════════════════════════════════════════════════════
   巢 · 表情包 ⑩：发的地方在主聊天界面

   装法：nest.html 里，nest-files.js 那行【下面】再加一行
        <script src="/nest-sticker.js?v=1"></script>

   ※ 这一版把**发送**挪进聊天：输入框边上多一枚表情图标，点开就是「这张表」，
     点一张＝放进暂存区（跟发图同一条路，走 `nestAttach.stage`），配句话一起发。
     记事 › 表情包 那一节还是**管**这张表的地方（传图 / 名字 / 标签 / 改 / 删）。

   ※ 助手那边也一样：他手里也有一张表（system 里带着名字和标签），
     用 `send_sticker` 挑一张，**贴在他说的话末尾**。规矩是他那边的：
     只点缀、不替代该说的话、一轮最多一张、不是每句都带。
   ══════════════════════════════════════════════════════════ */
(function(){
"use strict";
try{
  const $=(s,r=document)=>r.querySelector(s);
  const el=(t,c,x)=>{const e=document.createElement(t);if(c)e.className=c;if(x!=null)e.textContent=x;return e;};
  const say=t=>{try{if(typeof toast==="function")toast(t);}catch(e){}};
  const jget=async u=>{
    const r=await fetch(u,{credentials:"same-origin"});
    if(!r.ok)throw new Error(r.status===404?"没有这个接口（HTTP 404）":"HTTP "+r.status);
    return r.json();
  };

  const css=document.createElement("style");
  css.textContent=`
#skPick{position:fixed;left:0;right:0;bottom:0;z-index:44;background:var(--glass-bg);
  backdrop-filter:blur(18px) saturate(140%);-webkit-backdrop-filter:blur(18px) saturate(140%);
  border-top:1px solid var(--glass-line);border-radius:var(--r) var(--r) 0 0;
  padding:10px 12px calc(10px + env(safe-area-inset-bottom));max-height:46vh;
  display:flex;flex-direction:column;gap:8px;box-shadow:var(--shadow)}
#skPick .hd{display:flex;align-items:center;gap:8px;font-size:12px;color:var(--dim2)}
#skPick .hd .sp{flex:1}
#skPick .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(74px,1fr));
  gap:8px;overflow:auto}
#skPick .cell{position:relative;border:1px solid var(--ink-1);border-radius:10px;
  background:transparent;padding:4px;display:flex;flex-direction:column;gap:3px;align-items:center}
#skPick .cell img{width:100%;height:64px;object-fit:contain;border-radius:7px;display:block}
#skPick .cell .nm{font-size:10.5px;color:var(--dim2);max-width:100%;
  overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
#skPick .cell:active{border-color:var(--accent)}
.att-sticker{max-width:150px}
.att-sticker img{max-width:150px;border-radius:10px;display:block}
.bubble .att-sticker{margin-top:6px}
`;
  document.head.append(css);

  let picker=null, CACHE=null;

  function closePicker(){ if(picker){ picker.remove(); picker=null; } }
  window.nestStickerClose=closePicker;

  async function openPicker(){
    closePicker();
    picker=el("div"); picker.id="skPick";
    const hd=el("div","hd");
    hd.append(el("span",null,"点一张＝放进输入框上头，配句话一起发"));
    hd.append(el("span","sp"));
    const bMore=el("button",null,"管理这张表");
    bMore.style.cssText="font-size:12px;color:var(--accent)";
    bMore.onclick=()=>{ closePicker(); openLibrary(); };
    const bx=el("button"); bx.append(nestIcon("close",15));
    bx.onclick=closePicker;
    hd.append(bMore,bx);
    const grid=el("div","grid");
    picker.append(hd,grid);
    document.body.append(picker);
    grid.append(el("div","nm","读取中…"));
    let j;
    try{ j=await jget("/api/stickers"); CACHE=j; }
    catch(e){ grid.innerHTML=""; grid.append(el("div","nm","读不出来："+e.message)); return; }
    grid.innerHTML="";
    const its=j.items||[];
    if(!its.length){
      const b=el("button","cell");
      b.append(el("div","nm","还空着 —— 去「管理这张表」传几张"));
      b.onclick=()=>{ closePicker(); openLibrary(); };
      grid.append(b);
      return;
    }
    its.forEach(s=>{
      const c=el("button","cell");
      const im=el("img"); im.src=s.url; im.alt=s.name||""; im.loading="lazy";
      c.append(im,el("div","nm",s.name||"没名字"));
      if(s.tags)c.title=s.name+" ｜ "+s.tags;
      c.onclick=()=>{
        const A=window.nestAttach;
        if(!A||!A.stage){ say("附件模块没装上，这张发不了"); return; }
        A.stage([{kind:"img",url:s.url,name:s.name||"表情"}]);
        closePicker();
        const ta=$("#ta"); if(ta)ta.focus();
      };
      grid.append(c);
    });
  }

  /* 去「记事 › 表情包」那一节管表（传图 / 改名字和标签 / 删） */
  function openLibrary(){
    const t=$('#tabs button[data-tab="notes"]');
    if(t)t.click();
    setTimeout(()=>{
      const pane=$("#pane .pb"); if(!pane)return;
      const b=[...pane.querySelectorAll(".nt-chips button")]
        .find(x=>x.textContent.trim()==="表情包");
      if(b)b.click();
      else if(window.nestStickerLibHint)window.nestStickerLibHint();
    },450);
  }

  function mount(){
    const row=$("#composer .row"); if(!row||$("#btnSticker"))return;
    const b=el("button","ibtn"); b.append(nestIcon("sticker",19));
    b.id="btnSticker"; b.title="表情包（点一张放进这次要说的话）";
    b.onclick=e=>{
      e.stopPropagation();
      if(picker)closePicker(); else openPicker();
    };
    const att=$("#btnAtt");
    if(att&&att.parentNode)att.parentNode.insertBefore(b,att);
    else row.insertBefore(b,row.firstChild);
    document.addEventListener("click",e=>{
      if(!picker)return;
      if(picker.contains(e.target))return;
      if(e.target.closest&&e.target.closest("#btnSticker"))return;
      closePicker();
    });
  }
  mount();
  window.nestStickerPicker={open:openPicker,close:closePicker,list:()=>CACHE};
}catch(e){console.error("nest-sticker:",e);}
})();
