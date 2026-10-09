/* ══════════════════════════════════════════════════════════
   巢 · 图标 v2：一套自绘的细线图标（**界面里不许再出现 emoji**）
   装法：nest-skin.js 那一行的【下面】再加一行
        <script src="/nest-icon.js?v=1"></script>

   用法：
     nestIcon("chat")              → 一个 <span class="ni"> 里面装着 <svg>
     nestIcon("heart", 20)         → 指定像素大小（不填就跟着字号 1em）
     nestIconHTML("star")          → 字符串，塞 innerHTML 的场合用
     el("span","ic").append(nestIcon("book"))
   规矩（照这套风格定的）：
     · 24×24 网格、**只用线**（fill:none）、线宽 1.5、圆头圆角
     · 颜色一律 currentColor —— 谁在什么底色上自己会变
     · 只为强调才上 accent 色，不拿色块当图标
   原来那个「可以拿一张图片换掉某个图标」的功能留着（文件下半段）。
   ══════════════════════════════════════════════════════════ */
(function(){
"use strict";
try{
  const NS="http://www.w3.org/2000/svg";

  /* ── 图标本体：每条都是 24×24 里的线 ── */
  const P={
    /* 导航 · 房间 */
    home:      "M4 11.2 12 4l8 7.2M6 9.8V20h12V9.8M10 20v-5h4v5",
    chat:      "M4.5 6.5h15v10h-9L6 20.5v-4H4.5z",
    memory:    "M7 20V9.5c0-2.5 2-4.5 5-4.5s5 2 5 4.5V20M9 20v-3.5c0-1.7 1.3-3 3-3s3 1.3 3 3V20",
    tide:      "M3 9c2.2 0 2.2 2 4.4 2S9.6 9 11.8 9s2.2 2 4.4 2 2.2-2 4.4-2M3 14c2.2 0 2.2 2 4.4 2s2.2-2 4.4-2 2.2 2 4.4 2 2.2-2 4.4-2",
    nest:      "M4 13c0-4.4 3.6-8 8-8s8 3.6 8 8M6.5 13c0-3 2.5-5.5 5.5-5.5S17.5 10 17.5 13M9 13c0-1.7 1.3-3 3-3s3 1.3 3 3",
    study:     "M12 6.5C10 5.2 7.6 4.8 4.5 5v13c3.1-.2 5.5.2 7.5 1.5 2-1.3 4.4-1.7 7.5-1.5V5c-3.1-.2-5.5.2-7.5 1.5M12 6.5v13",
    together:  "M9.5 12a3.5 3.5 0 1 0 0-.01M14.5 12a3.5 3.5 0 1 0 0-.01",
    toy:       "M12 5.5a2 2 0 1 0 0-.01M12 7.5v4M6.5 11.5h11v7h-11zM6.5 15h11M10.4 13.2h.01M13.6 13.2h.01",
    mine:      "M12 11.5a3.5 3.5 0 1 0 0-.01M5.5 20c.6-3.2 3.2-5 6.5-5s5.9 1.8 6.5 5",
    setting:   "M5 7h6M15 7h4M5 12h2M11 12h8M5 17h10M13 5v4M9 10v4M17 15v4",
    /* 通用动作 */
    menu:      "M4 7h16M4 12h16M4 17h16",
    close:     "M6 6l12 12M18 6 6 18",
    back:      "M14 6l-6 6 6 6",
    forward:   "M10 6l6 6-6 6",
    search:    "M11 18a7 7 0 1 0 0-14 7 7 0 0 0 0 14M16.2 16.2 20 20",
    plus:      "M12 5.5v13M5.5 12h13",
    send:      "M12 19V6M7.5 10.5 12 6l4.5 4.5",
    attach:    "M8.5 12.5 14 7a3.2 3.2 0 0 1 4.5 4.5l-6.8 6.8a5 5 0 0 1-7-7l6.4-6.4",
    sticker:   "M12 20a8 8 0 1 0-8-8M8.5 10h.01M14.5 10h.01M9 14.5c1.6 1.3 4.4 1.3 6 0M20 12c-4 0-8 4-8 8",
    copy:      "M9 9h9v9H9zM6 15V6h9",
    star:      "M12 4.5l2.4 4.9 5.4.8-3.9 3.8.9 5.4-4.8-2.6-4.8 2.6.9-5.4L4.2 10.2l5.4-.8z",
    dots:      "M6.5 12h.01M12 12h.01M17.5 12h.01",
    trash:     "M5.5 7.5h13M9.5 7.5V5.5h5v2M7.5 7.5 8.5 19h7l1-11.5M11 10.5v5M13 10.5v5",
    edit:      "M5 19h3l9.5-9.5-3-3L5 16zM14 6.5l3 3",
    refresh:   "M19 12a7 7 0 1 1-2-4.9M19 4.5V9h-4.5",
    more:      "M12 5.5v.01M12 12v.01M12 18.5v.01",
    check:     "M5.5 12.5 10 17l8.5-9",
    warn:      "M12 4.5 21 19.5H3zM12 10v4.5M12 17h.01",
    up:        "M6 14l6-6 6 6",
    down:      "M6 10l6 6 6-6",
    external:  "M14 5.5h4.5V10M18.5 5.5 11 13M17 14.5V19H5.5V7.5H10",
    /* 房间里的东西 */
    heart:     "M12 19.5S4.5 15 4.5 10.2A3.7 3.7 0 0 1 12 8a3.7 3.7 0 0 1 7.5 2.2C19.5 15 12 19.5 12 19.5z",
    calendar:  "M5 7.5h14v11H5zM5 11h14M8.5 5.5v3M15.5 5.5v3",
    clock:     "M12 20a8 8 0 1 0 0-16 8 8 0 0 0 0 16M12 8v4.3l3 1.7",
    diary:     "M6.5 4.5h11v15h-11zM9 4.5v15M11 9h4M11 12.5h4",
    notes:     "M6.5 4.5h8l3 3v12h-11zM14 4.5v3.5h3.5M9 12h6M9 15h4",
    letter:    "M4.5 6.5h15v11h-15zM4.5 7.5 12 13l7.5-5.5",
    mood:      "M12 20a8 8 0 1 0 0-16 8 8 0 0 0 0 16M9 10h.01M15 10h.01M8.8 14.5c1.8 1.6 4.6 1.6 6.4 0",
    meme:      "M4.5 6.5h9v7h-9zM15 9.5h4.5v8H10v-4",
    health:    "M4 12.5h3.5l2-4 3 8 2.5-5h5",
    space:     "M4.5 6.5h15v9h-15zM8 18.5h8M12 15.5v3",
    timeline:  "M4 19V5M4 19h16M8 15.5V11M12 15.5V8M16 15.5v-6",
    stickers:  "M4.5 6.5h15v9.5l-3.5 3.5H4.5zM15.5 19.5v-3.5H19",
    book:      "M5 5.5h5.5c1 0 1.5.6 1.5 1.5v12c0-1-.5-1.5-1.5-1.5H5zM19 5.5h-5.5C12.5 5.5 12 6 12 7v12c0-1 .5-1.5 1.5-1.5H19z",
    play:      "M8.5 6.5v11l9-5.5z",
    image:     "M4.5 6.5h15v11h-15zM8.5 11h.01M5 16l4.5-4 3 2.5 3-3.5 3.5 4",
    file:      "M7 4.5h6.5L18 9v10.5H7zM13 4.5V9h5",
    window:    "M4.5 6.5h15v11h-15zM4.5 10h15M8 8.2h.01M10.2 8.2h.01",
    mcp:       "M9 4.5v4M15 4.5v4M6.5 8.5h11v3a5.5 5.5 0 0 1-11 0zM12 17v2.5",
    chip:      "M8.5 8.5h7v7h-7zM5.5 10.5h3M5.5 13.5h3M15.5 10.5h3M15.5 13.5h3M10.5 5.5v3M13.5 5.5v3M10.5 15.5v3M13.5 15.5v3",
    bell:      "M8 16.5V11a4 4 0 0 1 8 0v5.5zM6.5 16.5h11M10.5 19a1.6 1.6 0 0 0 3 0",
    moon:      "M19 14.5A7.5 7.5 0 0 1 9.5 5a7.5 7.5 0 1 0 9.5 9.5z",
    sun:       "M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6M12 3.5v2M12 18.5v2M3.5 12h2M18.5 12h2M6 6l1.4 1.4M16.6 16.6 18 18M18 6l-1.4 1.4M7.4 16.6 6 18",
    palette:   "M12 20a8 8 0 1 1 0-16c4.4 0 8 3 8 6.5 0 2.5-2 3.5-4 3.5h-1.5a2 2 0 0 0-1.4 3.4c.4.5.1 1.6-1.1 1.6M8.5 9.5h.01M12 8h.01M15.5 9.5h.01",
    person:    "M12 11.5a3.5 3.5 0 1 0 0-.01M6 20c.7-3.3 3.2-5.5 6-5.5s5.3 2.2 6 5.5",
    bot:       "M8 8.5h8v8H8zM12 5.5v3M9.5 11.5h.01M14.5 11.5h.01M6 10.5v4M18 10.5v4",
    plug:      "M12 20V13M9 13h6V9.5a3 3 0 0 0-6 0zM10 6.5v3M14 6.5v3",
    leaf:      "M19 5.5c-7 0-11 3-11 8a5 5 0 0 0 1.5 3.5M19 5.5c0 7-3.5 10.5-9.5 11",
    wave:      "M4 12c1.5-2.5 3-2.5 4.5 0s3 2.5 4.5 0 3-2.5 4.5 0",
    mic:       "M12 14.5a2.5 2.5 0 0 0 2.5-2.5V7a2.5 2.5 0 0 0-5 0v5a2.5 2.5 0 0 0 2.5 2.5M7 11.5a5 5 0 0 0 10 0M12 17v2.5",
    phone:     "M8 4.5h3l1 3-2 1.5a9 9 0 0 0 5 5l1.5-2 3 1v3c0 1-1 1.5-2 1.5C11 17.5 6.5 13 6.5 6.5c0-1 .5-2 1.5-2z",
    spark:     "M12 4.5v5M12 14.5v5M4.5 12h5M14.5 12h5M7.2 7.2l3 3M13.8 13.8l3 3M16.8 7.2l-3 3M10.2 13.8l-3 3",
    dot:       "M12 12h.01",
    lock:      "M7 11h10v8.5H7zM9.5 11V9a2.5 2.5 0 0 1 5 0v2",
    pin:       "M12 20.5s5.5-5.5 5.5-9.5a5.5 5.5 0 0 0-11 0c0 4 5.5 9.5 5.5 9.5M12 11h.01",
    gift:      "M5 11.5h14V20H5zM4 8.5h16v3H4zM12 8.5V20M12 8.5c-3 0-4-1-4-2.2S9 4.5 12 8.5M12 8.5c3 0 4-1 4-2.2S15 4.5 12 8.5",
    wand:      "M6 18.5 16 8.5M14.5 5.5l1 2 2 1-2 1-1 2-1-2-2-1 2-1zM6.5 5h.01",
  };

  function svg(name, size){
    const d=P[name]||P.dot;
    const s=document.createElementNS(NS,"svg");
    s.setAttribute("viewBox","0 0 24 24");
    s.setAttribute("fill","none");
    s.setAttribute("stroke","currentColor");
    s.setAttribute("stroke-width","1.5");
    s.setAttribute("stroke-linecap","round");
    s.setAttribute("stroke-linejoin","round");
    s.setAttribute("aria-hidden","true");
    s.setAttribute("focusable","false");
    if(size){ s.setAttribute("width",size); s.setAttribute("height",size); }
    const path=document.createElementNS(NS,"path");
    path.setAttribute("d",d);
    s.append(path);
    return s;
  }

  const css=document.createElement("style");
  css.textContent=`
.ni{display:inline-flex;align-items:center;justify-content:center;width:1em;height:1em;
  line-height:0;flex:0 0 auto;vertical-align:-0.125em}
.ni svg{width:1em;height:1em;display:block}
.ni.acc{color:var(--accent)}
.ni.big{width:1.35em;height:1.35em}
#tabs .ni{width:20px;height:20px}
#tabs .ni svg{width:20px;height:20px}
#bar .ibtn .ni,#composer .row .ibtn .ni{width:19px;height:19px}
#bar .ibtn .ni svg,#composer .row .ibtn .ni svg{width:19px;height:19px}
#bar .ibtn img,#btnSide img{display:block;border-radius:4px}
`;
  document.head.append(css);

  /* 对外：一个元素 / 一段 HTML / 名字表 */
  window.nestIcon=function(name,size,cls){
    const w=document.createElement("span");
    w.className="ni"+(cls?(" "+cls):"");
    w.append(svg(name,size));
    return w;
  };
  window.nestIconHTML=function(name,size,cls){
    return window.nestIcon(name,size,cls).outerHTML;
  };
  window.NEST_ICON_NAMES=Object.keys(P);

  /* ── 老功能留着：允许用一张图片换掉侧栏 / 思考 / 发送那几枚图标 ──
     默认值不再是 emoji，而是自绘图标的名字。 */
  const LS="nest_theme";
  const get=()=>{try{return JSON.parse(localStorage.getItem(LS)||"{}");}catch(e){return {};}};
  const bad=new Set();
  const isUrl=v=>/^(https?:\/\/|data:image\/|\/)/i.test((v||"").trim());

  function paint(host,v,w,defName){
    if(!host)return;
    v=(v||"").trim();
    const hasImg=host.querySelector("img");
    if(!v||!isUrl(v)){
      if(hasImg)hasImg.remove();
      if(!host.querySelector("svg")){ host.textContent=""; host.append(window.nestIcon(defName,w)); }
      return;
    }
    if(bad.has(v))return;
    if(hasImg&&hasImg.getAttribute("src")===v)return;
    host.textContent="";
    const im=document.createElement("img");
    im.alt=""; im.src=v;
    im.style.width=w+"px"; im.style.height=w+"px"; im.style.objectFit="contain";
    im.onerror=()=>{bad.add(v);im.remove();host.append(window.nestIcon(defName,w));};
    host.append(im);
  }

  const sideBtn=()=>document.querySelector("#btnSide");
  const heads=()=>[].slice.call(document.querySelectorAll("details.think > summary .ic"));

  function run(){
    const T=get();
    paint(sideBtn(),T.icSide,18,"menu");
    heads().forEach(h=>paint(h,T.icThink,15,"spark"));
    const s=document.querySelector("#btnSend");
    if(s&&!s.classList.contains("stop")&&!T.send&&!s.querySelector("svg")
       &&s.textContent.trim()==="发送"){
      s.textContent="";
      s.append(window.nestIcon("send",17),document.createTextNode("发送"));
    }
  }
  run();
  let tm=0;
  new MutationObserver(()=>{ if(tm)return; tm=setTimeout(()=>{tm=0;run();},80); })
    .observe(document.body,{childList:true,subtree:true});
}catch(e){console.error("nest-icon:",e);}
})();
