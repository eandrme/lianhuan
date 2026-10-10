/* ══════════════════════════════════════════════════════════
   巢 · 一起页（TOGETHER）

   装法：nest.html 里放在 nest-home.js 后面
        <script src="/nest-together.js?v=1"></script>

   参考「信息流」那种排版结构，底色仍是和纸米白、强调色仍只有 #6E93B3：

     ① 顶栏      ‹ 返回 · 一起 TOGETHER · 右侧（分区 / ✕）
     ② 引用块    左侧一条 2px accent 竖线 + 宋体 15px 斜体
     ③ 一个下拉  「八维 ∨」
     ④ 标签行    全部 / 梗库 / 表情包 / 健康 / 收藏 / 玩具 / 日记 / 碎碎念
     ⑤ 居中一枚「日报」
     ⑥ 一行      左「十月八日」· 右「No. 155」
     ⑦ 信息流    三列：品类 | 内容 | 时间，行间 1px 细横线

   ★ 「不改功能」：原来那十一档（日记 / 碎碎念 / 心情 / 日历 / 梗库 / 表情包 /
     健康 / 空间 / 时间线 / 收藏 / 玩具箱）的**完整界面一个都没删** ——
     顶栏那颗「分区」按一下就进去，点某一条也能跳到它所属的那一档。
   ══════════════════════════════════════════════════════════ */
(function(){
"use strict";
try{
  const el=(t,c,x)=>{const e=document.createElement(t);if(c)e.className=c;if(x!=null)e.textContent=x;return e;};
  const say=t=>{try{if(typeof toast==="function")toast(t);}catch(e){}};
  const jget=async u=>{const r=await fetch(u,{credentials:"same-origin"});if(!r.ok)throw new Error("HTTP "+r.status);return r.json();};
  const pad2=n=>String(n).padStart(2,"0");

  /* ── 七档（就是标签行那一排；「全部」在最前）── */
  const CATS=[["全部",null],
              ["梗库","meme"],["表情包","sticker"],["健康","health"],["收藏","star"],
              ["玩具","toy"],["日记","diary"],["碎碎念","notes"]];

  const css=document.createElement("style");
  css.textContent=`
.tg-wrap{max-width:720px;margin:0 auto;padding:0 16px}
.tg-wrap .pg-head{margin:0 -16px}
/* ② 引用块 */
.tg-quote{position:relative;margin:0 0 20px;padding:2px 0 2px 16px;
  font-family:var(--font);font-size:15px;font-style:italic;line-height:1.8;
  color:var(--tx-2);letter-spacing:.02em}
.tg-quote::before{content:"";position:absolute;left:0;top:2px;bottom:2px;width:2px;
  background:var(--accent);opacity:.75;border-radius:1px}
/* ③ 下拉 */
.tg-sel{display:inline-flex;align-items:center;gap:6px;margin:0 0 14px;
  min-height:44px;font-size:13px;color:var(--tx-2)}
.tg-sel select{-webkit-appearance:none;appearance:none;border:0;background:transparent;
  font:inherit;font-size:13px;color:var(--tx-2);outline:none;padding:8px 4px;
  font-family:var(--font);cursor:pointer}
.tg-sel .cv{color:var(--tx-3);display:flex;pointer-events:none;margin-left:-18px}
/* ④ 标签行：横向可滑，选中态才用 accent */
.tg-chips{display:flex;gap:8px;overflow-x:auto;padding:2px 0 4px;margin:0 0 16px;
  scrollbar-width:none;-webkit-overflow-scrolling:touch}
.tg-chips::-webkit-scrollbar{display:none}
.tg-chips button{flex:0 0 auto;min-height:44px;padding:0 14px;border-radius:12px;
  border:1px solid var(--ink-1);background:transparent;color:var(--tx-2);
  font-family:var(--font);font-size:13px;letter-spacing:.06em;cursor:pointer;
  transition:color .3s ease,border-color .3s ease,background-color .3s ease,transform .3s ease}
.tg-chips button.on{color:var(--accent);border-color:var(--accent);
  background:color-mix(in srgb,var(--accent) 10%,transparent)}
.tg-chips button:active{transform:scale(.98)}
/* ⑤ 日报：居中一枚（就这一枚，不是一排胶囊） */
.tg-daily{display:flex;justify-content:center;margin:0 0 18px}
.tg-daily button{min-height:44px;padding:0 22px;border-radius:999px;
  border:1px solid var(--ink-1);background:transparent;color:var(--tx-2);
  font-family:var(--font);font-size:13px;letter-spacing:.16em;cursor:pointer;
  transition:color .3s ease,border-color .3s ease,transform .3s ease}
.tg-daily button:hover{color:var(--accent);border-color:var(--accent)}
.tg-daily button:active{transform:scale(.98)}
/* ⑥ 一行：左日期 · 右总数 */
.tg-dayline{display:flex;align-items:baseline;gap:10px;margin:0 0 6px}
.tg-dayline .d{font-family:var(--font);font-size:16px;letter-spacing:.1em;color:var(--tx-1)}
.tg-dayline .sp{flex:1}
.tg-dayline .n{font-family:var(--latin);font-size:12px;letter-spacing:.2em;color:var(--tx-3)}
/* ⑦ 信息流：三列 */
.tg-feed{margin-top:6px}
.tg-grp{font-family:var(--latin);font-size:10px;letter-spacing:.26em;color:var(--latin-c);
  text-transform:uppercase;margin:18px 0 4px}
.tg-grp:first-child{margin-top:0}
.tg-row{display:flex;align-items:flex-start;gap:12px;padding:13px 2px;min-height:44px;
  border-bottom:1px solid rgba(110,130,150,.22);cursor:pointer;
  transition:background-color .3s ease}
.tg-row:hover{background:rgba(110,130,150,.05)}
.tg-row:active{transform:scale(.995)}
.tg-row .cat{flex:0 0 68px;font-family:var(--font);font-size:14px;color:var(--accent);
  letter-spacing:.06em;padding-top:1px}
.tg-row .tx{flex:1;min-width:0;font-family:var(--font);font-size:15px;line-height:1.8;
  color:var(--tx-1);display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;
  overflow:hidden;word-break:break-word}
.tg-row .tm{flex:0 0 auto;font-family:var(--latin);font-size:11px;letter-spacing:.14em;
  color:var(--tx-3);text-align:right;padding-top:2px;min-width:44px}
.tg-empty{padding:26px 2px;font-size:13px;color:var(--tx-3);line-height:1.8}
/* 日报那张弹层里的小表 */
.tg-dig{margin:0}
.tg-dig .k{display:flex;align-items:center;gap:10px;padding:9px 2px;
  border-bottom:1px solid rgba(110,130,150,.22);font-family:var(--font);font-size:14px;
  color:var(--tx-1)}
.tg-dig .k .sp{flex:1}
.tg-dig .k .n{font-family:var(--latin);font-size:12px;color:var(--tx-3);letter-spacing:.14em}
.tg-dig .hd{font-family:var(--latin);font-size:10px;letter-spacing:.26em;color:var(--latin-c);
  text-transform:uppercase;margin-bottom:8px}
.tg-sec{display:flex;flex-direction:column;gap:2px}
.tg-sec button{min-height:44px;text-align:left;padding:0 12px;border-radius:12px;
  border:1px solid transparent;background:transparent;color:var(--tx-1);font:inherit;
  font-size:14px;cursor:pointer}
.tg-sec button:hover{background:var(--panel2)}
`;
  document.head.append(css);

  /* ── 各档 → 信息流的一行 ──
     一行统一成 {cat, icon, text, ts, raw}；ts 是秒，用来排序和显示时间。 */
  const CAT_ICON={"梗库":"meme","表情包":"sticker","健康":"health","收藏":"star",
                  "玩具":"toy","日记":"diary","碎碎念":"notes"};
  function toTs(v){
    if(v==null)return 0;
    if(typeof v==="number")return v>1e11?v/1000:v;      /* 有的字段是毫秒 */
    const s=String(v);
    if(/^\d+$/.test(s))return toTs(parseInt(s,10));
    const t=Date.parse(s.replace(" ","T"));
    return isNaN(t)?0:t/1000;
  }
  function ts2hm(ts){
    if(!ts)return "";
    const d=new Date(ts*1000), now=new Date();
    const same=d.getFullYear()===now.getFullYear()&&d.getMonth()===now.getMonth()
             &&d.getDate()===now.getDate();
    const hm=pad2(d.getHours())+":"+pad2(d.getMinutes());
    return same?hm:(pad2(d.getMonth()+1)+"-"+pad2(d.getDate())+" "+hm);
  }
  function clip(s,n){ s=String(s||"").replace(/\s+/g," ").trim(); return s.length>n?(s.slice(0,n)+"…"):s; }

  async function gather(){
    const out=[];
    const add=(cat,text,ts,raw)=>{ if(String(text||"").trim())out.push({cat,icon:CAT_ICON[cat],text:String(text),ts:toTs(ts),raw:raw}); };
    const soft=async(u,fn)=>{ try{ const j=await jget(u); fn(j&&(j.items||j)); }catch(e){} };
    await Promise.all([
      soft("/api/memes",its=>(its||[]).forEach(x=>add("梗库",x.word+(x.meaning?("："+x.meaning):""),x.ts,x))),
      soft("/api/stickers",its=>(its||[]).forEach(x=>add("表情包",(x.name||"一张表情包")+(x.tags?(" · "+x.tags):""),x.ts,x))),
      soft("/api/health_recent?days=60",its=>(its||[]).forEach(x=>{
        const bits=[];
        if(x.steps)bits.push(x.steps+" 步");
        if(x.resting_hr)bits.push("静息 "+x.resting_hr);
        if(x.hrv_ms)bits.push("HRV "+x.hrv_ms);
        if(x.note)bits.push(x.note);
        add("健康",bits.join(" · ")||"记了一天",toTs(x.day||x.ts),x);
      })),
      soft("/api/chat/starred",its=>(its||[]).forEach(x=>add("收藏",x.content,x.ts,x))),
      soft("/api/plays",its=>(its||[]).forEach(x=>add("玩具",x.name||x.title||"一个小玩具",x.ts,x))),
      soft("/api/diary?who=ai",its=>(its||[]).forEach(x=>add("日记",x.content,toTs(x.day||x.ts),x))),
      soft("/api/diary?who=me",its=>(its||[]).forEach(x=>add("日记",x.content,toTs(x.day||x.ts),x))),
      soft("/api/notes?limit=300",its=>(its||[]).forEach(x=>add("碎碎念",x.content,x.ts,x))),
    ]);
    out.sort((a,b)=>b.ts-a.ts);
    return out;
  }

  /* ── 日报：今天这一天，各档各几条 ── */
  function dailySheet(items){
    window.nestSheet("今天这一天",(bx)=>{
      const now=new Date();
      const today=items.filter(x=>{
        const d=new Date((x.ts||0)*1000);
        return x.ts&&d.getFullYear()===now.getFullYear()&&d.getMonth()===now.getMonth()
               &&d.getDate()===now.getDate();
      });
      bx.append(el("div","hd",zhDay(now)+" · No. "+today.length));
      const dig=el("div","tg-dig");
      const cnt={};
      today.forEach(x=>{cnt[x.cat]=(cnt[x.cat]||0)+1;});
      const keys=Object.keys(cnt);
      if(!keys.length){
        dig.append(el("div","tg-empty","今天还没有记下什么。"));
      }else{
        keys.sort().forEach(k=>{
          const r=el("div","k");
          r.append(el("span",null,k),el("span","sp"),el("span","n",cnt[k]+" 条"));
          dig.append(r);
        });
      }
      bx.append(dig);
      /* 今天那几条原文也摆出来，省得还要一档一档翻 */
      if(today.length){
        const list=el("div","tg-feed");
        today.slice(0,20).forEach(x=>list.append(row(x,()=>{})));
        bx.append(el("div","grp","TODAY"),list);
      }
    });
  }
  /* 中文日期：十月八日 */
  const CN_M=["一","二","三","四","五","六","七","八","九","十","十一","十二"];
  const CN_D=["一","二","三","四","五","六","七","八","九","十",
              "十一","十二","十三","十四","十五","十六","十七","十八","十九","二十",
              "二十一","二十二","二十三","二十四","二十五","二十六","二十七","二十八",
              "二十九","三十","三十一"];
  function zhDay(d){ return CN_M[d.getMonth()]+"月"+CN_D[d.getDate()-1]+"日"; }

  /* ── 一行 ── */
  function row(it,onOpen){
    const r=el("div","tg-row");
    r.append(el("div","cat",it.cat));
    r.append(el("div","tx",clip(it.text,90)));
    r.append(el("div","tm",ts2hm(it.ts)));
    r.onclick=()=>{ if(onOpen)onOpen(); detail(it); };
    return r;
  }
  /* 点开一条：全文 + 去它那一档（原来那些界面一个都没丢） */
  function detail(it){
    window.nestSheet(it.cat,(bx)=>{
      bx.append(el("div","tg-quote",it.text));
      const meta=el("div","k");
      meta.style.cssText="display:flex;align-items:center;gap:10px;font-family:var(--latin);"+
        "font-size:10px;letter-spacing:.24em;color:var(--latin-c);margin:6px 0 14px";
      meta.append(el("span",null,it.cat.toUpperCase()),el("span",null,ts2hm(it.ts)||""));
      bx.append(meta);
      const sec=el("div","tg-sec");
      const b=el("button",null,"");
      b.append(document.createTextNode("去「一起 › "+it.cat+"」那一档（改 / 删 / 再记一条）"));
      b.onclick=()=>{
        const w=bx.closest(".sheet"); if(w)w.remove();
        if(window.nestNotesOpen)window.nestNotesOpen(it.cat);
        else if(window.nestGo)window.nestGo("notes");
      };
      sec.append(b);
      bx.append(sec);
    });
  }

  window.NEST_PANES=window.NEST_PANES||{};
  window.NEST_PANES.together=async function(box){
    box.innerHTML="";
    const wrap=el("div","tg-wrap");
    const head=window.nestPageHead
      ? window.nestPageHead({title:"一起",en:"TOGETHER",right:[
          {icon:"more",title:"十一档的完整界面都在这儿",onclick:openSections},
          {icon:"close",title:"回主界面",onclick:()=>{ if(window.nestGo)window.nestGo("home"); }},
        ]})
      : el("div");
    const quote=el("div","tg-quote");
    const selWrap=el("div","tg-sel");
    const sel=el("select");
    [["dim","八维"],["time","时间"]].forEach(([v,n])=>{
      const o=el("option",null,n); o.value=v; sel.append(o);
    });
    const cv=el("span","cv"); cv.append(nestIcon("down",14));
    selWrap.append(sel,cv);
    const chips=el("div","tg-chips");
    const daily=el("div","tg-daily");
    const bDaily=el("button",null,"日报");
    daily.append(bDaily);
    const dayline=el("div","tg-dayline");
    const feed=el("div","tg-feed");
    wrap.append(head,quote,selWrap,chips,daily,dayline,feed);
    box.append(wrap);

    let ALL=[], FILTER="全部", GROUP="dim";

    chips.append(...CATS.map(([label])=>{
      const b=el("button",(label===FILTER?"on":""),label);
      b.onclick=()=>{
        FILTER=label;
        [].slice.call(chips.children).forEach(x=>x.classList.toggle("on",x===b));
        paint();
      };
      return b;
    }));
    sel.onchange=()=>{ GROUP=sel.value; paint(); };

    function paint(){
      daily.style.display="";
      bDaily.onclick=()=>dailySheet(ALL);
      const rows=ALL.filter(x=>FILTER==="全部"||x.cat===FILTER);
      const now=new Date();
      dayline.innerHTML="";
      dayline.append(el("div","d",zhDay(now)),el("div","sp"));
      dayline.append(el("div","n","NO. "+rows.length));
      feed.innerHTML="";
      if(!rows.length){
        feed.append(el("div","tg-empty",ALL.length
          ? "这一档还空着。"
          : "还没有记下什么。日记、碎碎念、梗库、表情包、健康、收藏、玩具 —— 记下的都会汇总到这儿。"));
        return;
      }
      if(GROUP==="dim"){
        /* 八维：一档一摞，摞头上一个拉丁小标 */
        const by={};
        rows.forEach(x=>{ (by[x.cat]=by[x.cat]||[]).push(x); });
        Object.keys(by).sort().forEach(cat=>{
          feed.append(el("div","tg-grp",cat.toUpperCase()+" · "+by[cat].length));
          by[cat].forEach(it=>feed.append(row(it)));
        });
      }else{
        rows.forEach(it=>feed.append(row(it)));
      }
    }

    /* ② 引用块：最新那条碎碎念（没有就退到最新一篇日记）；都没有就不摆 */
    async function fillQuote(list){
      let line=list.filter(x=>x.cat==="碎碎念")[0]||list.filter(x=>x.cat==="日记")[0];
      if(!line){ quote.remove(); return; }
      quote.textContent=clip(line.text,120);
    }

    /* 十一档的完整界面：一个入口都不藏 */
    function openSections(){
      const SECS=["日记","碎碎念","心情","日历","梗库","表情包","健康","空间","时间线","收藏","玩具"];
      window.nestSheet("一起 · 十一档",(bx)=>{
        bx.append(el("div","hd","原本那十一档，一个都没少"));
        const sec=el("div","tg-sec");
        SECS.forEach(label=>{
          const b=el("button",null,label);
          b.onclick=()=>{
            const w=bx.closest(".sheet"); if(w)w.remove();
            if(window.nestNotesOpen)window.nestNotesOpen(label);
            else if(window.nestGo)window.nestGo("notes");
          };
          sec.append(b);
        });
        bx.append(sec);
      });
    }
    window.nestTogetherSections=openSections;

    feed.append(el("div","tg-empty","读取中…"));
    ALL=await gather();
    await fillQuote(ALL);
    paint();
  };
}catch(e){console.error("nest-together:",e);}
})();
