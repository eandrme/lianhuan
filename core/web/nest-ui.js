/* ══════════════════════════════════════════════════════════
   巢 · 主界面图标 v1
   装法：nest.html 里，nest-tabs.js 那行【下面】再加一行
        <script src="/nest-ui.js?v=1"></script>
   作用：给侧栏【外观】面板追加一节「主界面图标」。
   底部五个格子 + 新对话 / 搜索 / MCP 都能填图标名、字符或图片链接。
   ══════════════════════════════════════════════════════════ */
(function(){
"use strict";
try{
  const LS="nest_theme";
  const get=()=>{try{return JSON.parse(localStorage.getItem(LS)||"{}");}catch(e){return {};}};
  const set=(k,v)=>{const T=get();T[k]=v;try{localStorage.setItem(LS,JSON.stringify(T));}catch(e){}};
  const el=(t,c,x)=>{const e=document.createElement(t);if(c)e.className=c;if(x!=null)e.textContent=x;return e;};
  const say=t=>{try{if(typeof toast==="function")toast(t);}catch(e){}};
  const isUrl=v=>/^(https?:\/\/|data:image\/|\/)/i.test((v||"").trim());
  const bad=new Set();

  const DEF={icChat:"chat",icMemory:"memory",icStudy:"study",icNotes:"notes",icSetting:"setting",
             icNew:"plus",icSearch:"search",icMcp:"mcp"};
  const FIELDS=[["icChat","聊天格"],["icMemory","记忆格"],["icStudy","书房格"],
                ["icNotes","记事格"],["icSetting","设置格"],
                ["icNew","新对话"],["icSearch","搜索"],["icMcp","MCP"]];

  /* 值可以是：自绘图标名 / 图片直链 / 任意字符。旧存档里留下的符号不再画出来。 */
  const isIcon=v=>(window.NEST_ICON_NAMES||[]).indexOf((v||"").trim())>=0;
  const isEmoji=v=>/[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}\u{2B00}-\u{2BFF}\u{FE0F}]/u.test(v||"");

  function draw(elm,v,w){
    if(!isIcon(v)){
      delete elm.dataset.ni;
      if(elm.textContent!==v)elm.textContent=v;
      return;
    }
    if(elm.dataset.ni===v&&elm.querySelector("svg"))return;
    elm.textContent=""; elm.dataset.ni=v;
    elm.append(nestIcon(v,w));
  }

  function paint(elm,v,w,def){
    if(!elm)return;
    v=(v||"").trim(); def=def||"";
    if(isEmoji(v))v="";
    if(!v)v=def;
    const hasImg=elm.querySelector("img");
    if(isUrl(v)){
      if(bad.has(v)){if(hasImg)hasImg.remove(); draw(elm,def,w); return;}
      if(hasImg&&hasImg.getAttribute("src")===v)return;
      elm.textContent=""; delete elm.dataset.ni;
      const im=document.createElement("img"); im.src=v; im.alt="";
      im.style.width=w+"px"; im.style.height=w+"px"; im.style.objectFit="contain"; im.style.display="block";
      im.onerror=()=>{bad.add(v);im.remove();draw(elm,def,w);};
      elm.append(im);
    }else{
      if(hasImg)hasImg.remove();
      draw(elm,v,w);
    }
  }

  /* ★ 底部导航条撤了：这几个「格子」图标现在长在**抽屉**那一列房间上 */
  const navIcon=k=>document.querySelector('#drawer .room[data-tab="'+k+'"] .ic');
  const barByTitle=t=>[].slice.call(document.querySelectorAll("#bar .ibtn")).find(b=>(b.title||"")===t);

  function run(){
    const F=Object.assign({},DEF,get());
    paint(navIcon("chat"),F.icChat,18,DEF.icChat);
    paint(navIcon("memory"),F.icMemory,18,DEF.icMemory);
    paint(navIcon("study"),F.icStudy,18,DEF.icStudy);
    paint(navIcon("notes"),F.icNotes,18,DEF.icNotes);
    paint(navIcon("setting"),F.icSetting,18,DEF.icSetting);
    paint(barByTitle("新对话"),F.icNew,16,DEF.icNew);
    paint(barByTitle("搜索历史"),F.icSearch,16,DEF.icSearch);
    paint(barByTitle("MCP 工具包"),F.icMcp,16,DEF.icMcp);
  }

  function buildSection(){
    const wrap=el("div"); wrap.id="ui-icons";
    wrap.append(Object.assign(el("div","sk-h"),{textContent:"主界面图标"}));
    FIELDS.forEach(f=>{
      const T=get();
      const i=el("input"); i.type="text";
      const v=(T[f[0]]!=null?String(T[f[0]]):DEF[f[0]]);
      i.value=isEmoji(v)?DEF[f[0]]:v;
      i.style.maxWidth="70px";
      i.oninput=()=>{set(f[0],i.value);run();};
      const r=el("div","sk-row");
      r.append(Object.assign(el("span","lb"),{textContent:f[1]}),i);
      wrap.append(r);
    });
    const b=el("button",null,"复原这八个图标");
    b.style.cssText="padding:7px 11px;border-radius:10px;border:1px solid var(--ink-1);"+
                    "background:transparent;font-size:13px;margin-top:6px";
    b.onclick=()=>{
      FIELDS.forEach(f=>set(f[0],DEF[f[0]]));
      const s=document.querySelector("#ui-icons"); if(s)s.remove();
      ensure(); run(); say("主界面图标复原了");
    };
    wrap.append(b);
    return wrap;
  }

  function ensure(){
    const side=document.querySelector("#side"); if(!side)return;
    if(!side.firstElementChild)return;
    if(side.querySelector("#ui-icons"))return;
    side.append(buildSection());
  }

  const side=document.querySelector("#side");
  if(side)new MutationObserver(()=>{ensure();run();}).observe(side,{childList:true});
  ensure(); run();

  let tm=0;
  new MutationObserver(()=>{if(tm)return;tm=setTimeout(()=>{tm=0;run();},100);})
    .observe(document.body,{childList:true,subtree:true});
  setInterval(run,3000);
}catch(e){console.error("nest-ui:",e);}
})();
