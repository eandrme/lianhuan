/* ══════════════════════════════════════════════════════════
   巢 · 时间线页

   装法：nest.html 里放在 nest-home.js 后面
        <script src="/nest-timeline.js?v=1"></script>

   一条列表：每条是一张「异形卡片」——
     左边一个大号编号（01 / 02 / 03…）、一条 1px 竖线、右边主标题 + 小字。
   卡片形状**交替变化**（四种轮着来），全是 1px 细描边、没有色块：
     a 普通圆角矩形   b 右侧一个 45° 尖角（像书签）
     c 左侧中间凹进一个小弧口   d 上下两端中间各凸出一个小三角（邮票齿）

   ★ 数据走的是现成的 /api/timeline（时间线事件）。卡下面那行小字用的是
     真实字段（分道名 · 日期 时间）—— 原来的时间线里没有「谁开的」这一栏，
     所以不编一个人名上去。
   ══════════════════════════════════════════════════════════ */
(function(){
"use strict";
try{
  const el=(t,c,x)=>{const e=document.createElement(t);if(c)e.className=c;if(x!=null)e.textContent=x;return e;};
  const jget=async u=>{const r=await fetch(u,{credentials:"same-origin"});if(!r.ok)throw new Error("HTTP "+r.status);return r.json();};

  /* 分道名：跟「一起 › 时间线」那一节同一套（早期那批英文 kind 按意思归） */
  const TL_LANE={"装修":"装修","一起做的事":"一起做的事","intimate":"一起做的事",
    "milestone":"一起做的事","和好":"一起做的事","meal":"一起做的事","饮食":"一起做的事",
    "order":"一起做的事","conversation":"一起做的事","relationship":"一起做的事",
    "night_talk":"一起做的事","日常":"一起做的事","daily":"一起做的事","event":"一起做的事",
    "夜":"一起做的事","我一个人":"我一个人","travel":"我一个人","errand":"我一个人",
    "对方的事":"你的事","学业纠结":"你的事","情绪事件":"你的事","情绪":"你的事","sleep":"你的事"};
  const TL_NAME={travel:"出门走走",errand:"跑腿",auto:"随手记",note:"手记",intimate:"亲密",
    conversation:"聊了很久",milestone:"里程碑",meal:"吃饭",order:"点单",event:"事件",
    daily:"日常",relationship:"我们俩",night_talk:"夜谈",sleep:"睡"};

  const css=document.createElement("style");
  css.textContent=`
.tl-wrap{max-width:720px;margin:0 auto;padding:0 16px}
.tl-wrap .pg-head{margin:0 -16px}
.tl-count{font-family:var(--latin);font-size:10px;letter-spacing:.24em;color:var(--latin-c);
  text-transform:uppercase;margin:0 0 14px 2px}
.tl-list{display:flex;flex-direction:column;gap:12px}
/* ── 异形卡片本体 ── */
.tl-c{position:relative;display:flex;align-items:center;gap:14px;
  min-height:84px;padding:14px 18px;box-sizing:border-box;
  background:rgba(255,255,255,.35);
  border:1px solid rgba(110,130,150,.30);
  backdrop-filter:blur(18px) saturate(140%);-webkit-backdrop-filter:blur(18px) saturate(140%);
  transition:transform .3s ease,box-shadow .3s ease}
@media (hover:hover){.tl-c:hover{transform:translateY(-2px);
  box-shadow:0 10px 24px rgba(70,100,130,.10)}}
.tl-c:active{transform:scale(.98)}
.tl-c .no{font-family:var(--latin);font-size:26px;line-height:1;color:var(--tx-3);
  flex:0 0 auto;min-width:38px;letter-spacing:.02em}
.tl-c .vr{width:1px;height:40px;background:rgba(110,130,150,.30);flex:0 0 1px}
.tl-c .bd{flex:1;min-width:0}
.tl-c .tt{font-family:var(--font);font-size:15px;line-height:1.6;color:var(--tx-1);
  display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.tl-c .mt{font-family:var(--latin);font-size:10px;letter-spacing:.2em;color:var(--tx-3);
  margin-top:6px;text-transform:uppercase}
/* a 普通圆角矩形 */
.tl-c.s-a{border-radius:20px}
/* b 右侧一个 45° 尖角（书签 / 旗子）—— 一个转 45° 的方块贴在半边 */
.tl-c.s-b{border-radius:20px 4px 20px 20px}
.tl-c.s-b::after{content:"";position:absolute;right:-7px;top:50%;width:13px;height:13px;
  margin-top:-6.5px;background:rgba(255,255,255,.35);
  border-top:1px solid rgba(110,130,150,.30);border-right:1px solid rgba(110,130,150,.30);
  transform:rotate(45deg);border-radius:0 3px 0 0}
/* c 左侧中间凹进一个小弧口
   ★ 用 mask **真的挖掉**一块，不是拿一个纸色小圆盖上去 —— 盖上去的话那一小块
     墨晕就透不过来了，而这一套皮的规矩是「卡片下要看得见纸纹和墨晕」。 */
.tl-c.s-c{border-radius:20px;
  -webkit-mask:radial-gradient(circle 7px at 0 50%,transparent 97%,#000 100%);
  mask:radial-gradient(circle 7px at 0 50%,transparent 97%,#000 100%)}
/* d 上下两端中间各凸出一个小三角（邮票齿）
   ★ 也是**真凸出来**的一小块卡片：一个转 45° 的小方块探出边缘，
     填色和描边都跟卡片一致（不是一块实心深色三角）。 */
.tl-c.s-d{border-radius:6px;padding-top:16px;padding-bottom:16px}
.tl-c.s-d::before,.tl-c.s-d::after{content:"";position:absolute;left:50%;
  width:11px;height:11px;margin-left:-5.5px;border-radius:1px;
  background:rgba(255,255,255,.35);transform:rotate(45deg)}
.tl-c.s-d::before{top:-6px;border-top:1px solid rgba(110,130,150,.30);
  border-left:1px solid rgba(110,130,150,.30)}
.tl-c.s-d::after{bottom:-6px;border-bottom:1px solid rgba(110,130,150,.30);
  border-right:1px solid rgba(110,130,150,.30)}
/* ── 搜索行 ── */
.tl-search{display:none;margin:0 0 14px}
.tl-search.on{display:block}
.tl-search input{width:100%;box-sizing:border-box;padding:12px 14px;border-radius:14px;
  border:1px solid var(--glass-line);background:var(--glass-bg);color:var(--fg);
  font:inherit;font-size:16px;outline:none}
.tl-empty{padding:24px 2px;font-size:13px;color:var(--tx-3)}
`;
  document.head.append(css);

  const SHAPES=["s-a","s-b","s-c","s-d"];
  function card(it,ord){
    const c=el("article","tl-c "+SHAPES[ord%SHAPES.length]);
    c.append(el("span","no",String(ord+1).padStart(2,"0")));
    c.append(el("i","vr"));
    const bd=el("div","bd");
    bd.append(el("div","tt",it.text||"（空）"));
    const bits=[];
    if(it.name)bits.push(it.name);
    if(it.day)bits.push(it.date||it.day);
    if(it.time)bits.push(it.time);
    bd.append(el("div","mt",bits.filter(Boolean).join(" · ")));
    c.append(bd);
    return c;
  }

  window.NEST_PANES=window.NEST_PANES||{};
  window.NEST_PANES.timeline=async function(box){
    box.innerHTML="";
    const wrap=el("div","tl-wrap");
    const head=window.nestPageHead
      ? window.nestPageHead({
          title:"时间线", en:"TIMELINE",
          right:[{icon:"search",title:"在这一条条里找",onclick:()=>{
            const s=wrap.querySelector(".tl-search");
            s.classList.toggle("on");
            if(s.classList.contains("on"))s.querySelector("input").focus();
          }}]})
      : el("div");
    const search=el("div","tl-search");
    const inp=el("input"); inp.type="text"; inp.placeholder="在这条时间线里找一个词…";
    search.append(inp);
    const count=el("div","tl-count");
    const list=el("div","tl-list");
    list.append(el("div","tl-empty","读取中…"));
    wrap.append(head,search,count,list);
    box.append(wrap);

    let ALL=[];
    try{
      const j=await jget("/api/timeline?limit=200");
      ALL=(j.items||[]).map(x=>{
        const m=(x.meta&&typeof x.meta==="object")?x.meta:{};
        return {id:x.id, day:x.date||"", time:x.time||"",
                name:TL_NAME[x.kind]||TL_LANE[x.kind]||x.kind||"",
                text:x.content||"",
                ctx:[m.weather,m.sky,m.where,m.project].filter(Boolean).join(" · "),
                days:x.days};
      });
    }catch(e){
      list.innerHTML="";
      list.append(el("div","tl-empty","时间线读不出来："+e.message));
      return;
    }
    /* 新的排前面：编号 01 是最近那一条 */
    ALL.sort((a,b)=>String(b.day+b.time).localeCompare(String(a.day+a.time)));

    function paint(kw){
      list.innerHTML="";
      const rows=ALL.filter(x=>!kw||((x.text||"")+(x.name||"")+(x.ctx||"")).indexOf(kw)>=0);
      count.textContent=rows.length?("NO. "+rows.length+" · 时间线"):"";
      if(!rows.length){
        list.append(el("div","tl-empty",kw?"没找到这一条。":"还没记过。他做了点什么、你顺手记一笔，都会落在这儿。"));
        return;
      }
      rows.forEach((it,i)=>list.append(card(it,i)));
    }
    let t=0;
    inp.oninput=()=>{ clearTimeout(t); t=setTimeout(()=>paint(inp.value.trim()),220); };
    paint("");
  };
}catch(e){console.error("nest-timeline:",e);}
})();
