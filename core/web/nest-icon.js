/* ══════════════════════════════════════════════════════════
   巢 · 图标模块 v1：让「思考 / 侧栏 / 调试 / 发送」支持图片
   装法：在 nest-skin.js 那一行的【下面】再加一行
        <script src="/nest-icon.js?v=1"></script>
   面板里照常填：
     https://…/xx.png   图片直链
     /xx.png            放在 core/web/ 里的文件（最稳）
     data:image/png;base64,…   小图标内嵌
   填文字（💡 ☰ ✦）也照旧能用；图片加载不出来会自动退回默认符号。
   ══════════════════════════════════════════════════════════ */
(function(){
"use strict";
try{
  const LS="nest_theme";
  const get=()=>{try{return JSON.parse(localStorage.getItem(LS)||"{}");}catch(e){return {};}};
  const bad=new Set();
  const isUrl=v=>/^(https?:\/\/|data:image\/|\/)/i.test((v||"").trim());

  const st=document.createElement("style");
  st.textContent=`
#btnSide img,#bar .ibtn img,#btnSend img{display:block;border-radius:4px}
#btnSide,#bar .ibtn{display:inline-flex;align-items:center;justify-content:center}
details.think summary .ic img{display:block;border-radius:3px}
`;
  document.head.append(st);

  function paint(el,v,w,def){
    if(!el)return;
    v=(v||"").trim(); def=def||"";
    const hasImg=el.querySelector("img");
    if(!v){ if(hasImg)hasImg.remove(); if(el.textContent!==def)el.textContent=def; return; }
    if(isUrl(v)){
      if(bad.has(v)){ if(el.textContent!==def)el.textContent=def; return; }
      if(hasImg&&hasImg.getAttribute("src")===v)return;
      el.textContent="";
      const im=document.createElement("img");
      im.alt=""; im.src=v;
      im.style.width=w+"px"; im.style.height=w+"px"; im.style.objectFit="contain";
      im.onerror=()=>{bad.add(v);im.remove();el.textContent=def;};
      el.append(im);
    }else{
      if(hasImg)hasImg.remove();
      if(el.textContent!==v)el.textContent=v;
    }
  }

  const sideBtn=()=>document.querySelector("#btnSide");
  const dbgBtn=()=>[].slice.call(document.querySelectorAll("#bar .ibtn"))
                      .find(b=>(b.title||"").indexOf("看这一轮")===0);
  const heads=()=>[].slice.call(document.querySelectorAll("details.think > summary .ic"));

  function run(){
    const T=get();
    paint(sideBtn(),T.icSide,18,"☰");
    paint(dbgBtn(),T.icDbg,16,"🐞");
    heads().forEach(h=>paint(h,T.icThink,15,"💡"));
    const s=document.querySelector("#btnSend");
    if(s&&!s.classList.contains("stop"))paint(s,T.send,16,"发送");
  }
  run();
  let tm=0;
  new MutationObserver(()=>{ if(tm)return; tm=setTimeout(()=>{tm=0;run();},80); })
    .observe(document.body,{childList:true,subtree:true});
  setInterval(run,3000);
}catch(e){console.error("nest-icon:",e);}
})();
