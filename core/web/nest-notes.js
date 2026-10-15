/* ══════════════════════════════════════════════════════════
   巢 · 记事 ⑥：日历 · 梗库 · 表情包 · 健康 · 空间 · 收藏
   装法：nest.html 再加一行 <script src="/nest-notes.js?v=1"></script>

   后端各归各家，前端一处收口：
     /api/calendar · /api/calendar/add  optional/homeplus
     /api/memes · /api/stickers         optional/homelife
     /api/health_recent · /api/health   optional/homelife（一天一条）
     /api/moments · …/mine · …/new · …/{id}/comment · …/{id}/del
                                        optional/homelife（空间：贴一条 + 楼里接话）
     /api/chat/starred · /api/chat/{id}/star   core/views（收藏：点过星的那些话）

   · 七块都带「改」和「删」—— 这是记事，攒着攒着一定要能收拾。
     （原项目的梗库只有录和改、日历只有读和写，都被点过名。）

   · 表情包点一下＝把它放进输入框上头，配句话再发 —— 跟发图片同一条路
     （走 nest-files 的暂存区，不另起一套发送逻辑）。
   ══════════════════════════════════════════════════════════ */
(function(){
"use strict";
try{
  window.NEST_PANES=window.NEST_PANES||{};
  const el=(t,c,x)=>{const e=document.createElement(t);if(c)e.className=c;if(x!=null)e.textContent=x;return e;};
  const say=t=>{try{if(typeof toast==="function")toast(t);}catch(e){}};
  const jget=async u=>{const r=await fetch(u,{credentials:"same-origin"});if(!r.ok)throw new Error("HTTP "+r.status);return r.json();};
  const jpost=async(u,b)=>{
    let r;
    try{
      r=await fetch(u,{method:"POST",credentials:"same-origin",
        headers:{"Content-Type":"application/json"},body:JSON.stringify(b||{})});
    }catch(e){ return {ok:false,err:"连不上服务器"}; }
    let d=null; try{ d=await r.json(); }catch(e){}
    // · 状态码不对＝没成。老服务端回的是 404 {"error":"…"}，没有 ok 字段 ——
    //   只判 d.ok===false 会把它当成功，界面说「存上了」其实一个字没落库。
    if(!r.ok||!d||d.ok===false)
      return {ok:false,status:r.status,err:(d&&(d.err||d.error))||("HTTP "+r.status)};
    return d;
  };
  const $=(s,r=document)=>r.querySelector(s);
  const pad2=n=>String(n).padStart(2,"0");
  const todayISO=()=>{const d=new Date();return d.getFullYear()+"-"+pad2(d.getMonth()+1)+"-"+pad2(d.getDate());};
  /* ★ 底部导航条撤了：跳转一律走 window.nestGo（nest-tabs.js 暴露的路由） */
  const goChat=()=>{ if(window.nestGo)window.nestGo("chat"); };

  const css=document.createElement("style");
  css.textContent=`
.nt-chips{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:12px}
.nt-chips button{padding:6px 12px;border-radius:10px;border:1px solid var(--ink-1);
  background:var(--panel);font-size:13px;color:var(--dim)}
.nt-chips button.on{border-color:var(--accent);color:var(--accent)}
.nt-top{display:flex;gap:7px;align-items:center;margin-bottom:10px;flex-wrap:wrap}
.nt-top button{padding:7px 11px;border-radius:8px;border:1px solid var(--line);
  background:var(--panel);font-size:13px;color:var(--dim)}
.nt-top button.on{border-color:var(--accent);color:var(--accent)}
.nt-top button.pri{border-color:var(--accent);color:var(--accent)}
.nt-top .sp{flex:1}
.nt-top input.q{flex:1;min-width:120px;padding:8px 11px;border-radius:9px;
  border:1px solid var(--line);background:var(--panel2);color:var(--fg);font:inherit;outline:none}
.nt-card{border:1px solid var(--line);background:var(--panel);border-radius:var(--r);padding:12px;margin-bottom:9px}
.nt-txt{white-space:pre-wrap;word-break:break-word;font-size:14.5px;line-height:1.75}
.nt-meta{display:flex;gap:8px;align-items:center;margin-top:8px;font-size:11.5px;
  color:var(--dim2);flex-wrap:wrap}
.nt-meta .tag{background:var(--panel2);border-radius:6px;padding:1px 6px}
.nt-meta .tag.ai{color:var(--warn)}
.nt-meta .tag.me{color:var(--accent)}
.nt-ops{margin-left:auto;display:flex;gap:6px}
.nt-ops button{padding:4px 10px;border-radius:7px;border:1px solid var(--line);
  background:none;font-size:12px;color:var(--dim)}
.nt-ops button.danger{color:var(--err);border-color:var(--err)}
.nt-in{width:100%;box-sizing:border-box;padding:9px 11px;border-radius:9px;
  border:1px solid var(--line);background:var(--panel2);color:var(--fg);font:inherit;
  outline:none;margin-top:8px}
.nt-btns{display:flex;gap:6px;margin-top:10px}
.nt-btns button{flex:1;padding:10px;border-radius:9px;border:1px solid var(--line);
  background:var(--panel2);color:var(--fg);font:inherit}
.nt-btns button.pri{border-color:var(--accent);color:var(--accent);
  background:transparent;font-weight:500}
.nt-sheet textarea{width:100%;min-height:110px;box-sizing:border-box;padding:10px;
  border-radius:9px;border:1px solid var(--line);background:var(--panel2);
  color:var(--fg);font:inherit;outline:none;resize:vertical}
.nt-sheet .lb{font-size:11.5px;color:var(--dim2);margin-top:10px;display:block}
.nt-lb{font-size:11.5px;color:var(--dim2);margin:14px 0 6px}
.nt-sheet .two{display:flex;gap:6px}
.nt-sheet .two>*{flex:1}
.nt-sheet select{width:100%;box-sizing:border-box;padding:9px 11px;border-radius:9px;
  border:1px solid var(--line);background:var(--panel2);color:var(--fg);font:inherit;
  outline:none;margin-top:8px}
/* 日历 */
.cal-grid{display:grid;grid-template-columns:repeat(7,1fr);gap:4px;margin-bottom:10px}
.cal-grid .h{text-align:center;font-size:11px;color:var(--dim2);padding:3px 0}
.cal-grid button{position:relative;aspect-ratio:1/1;border-radius:9px;border:1px solid transparent;
  background:var(--panel);color:var(--dim);font-size:13px}
.cal-grid button.out{opacity:.3}
.cal-grid button.today{border-color:var(--ink-1)}
.cal-grid button.on{border-color:var(--accent);color:var(--accent)}
.cal-grid button b{position:absolute;left:50%;bottom:4px;transform:translateX(-50%);
  width:4px;height:4px;border-radius:50%;background:var(--accent)}
.cal-mo{display:flex;align-items:center;gap:8px;margin-bottom:8px}
.cal-mo .t{flex:1;text-align:center;font-size:14px}
.cal-mo button{padding:6px 12px;border-radius:10px;border:1px solid var(--ink-1);color:var(--dim)}
.crow{display:flex;align-items:center;gap:8px;padding:9px 8px;border-bottom:1px solid var(--line)}
.crow .dt{flex:0 0 82px;font-size:10px;letter-spacing:.14em;color:var(--tx-3);font-family:var(--latin)}
.crow .tt{flex:1;min-width:0;font-size:14px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.crow .tt em{color:var(--dim2);font-style:normal;font-size:11.5px;margin-left:6px}
.crow .kd{font-size:11px;color:var(--dim2);background:var(--panel2);border-radius:6px;padding:1px 6px}
.crow.done .tt{text-decoration:line-through;color:var(--dim2)}
.crow.past .tt{color:var(--dim2)}
.crow button{font-size:12px;color:var(--dim);border:1px solid var(--line);
  border-radius:7px;padding:3px 9px}
.crow button.danger{color:var(--err);border-color:var(--err)}
.crow button.ck{color:var(--ok);border-color:var(--ok)}
/* 梗库 / 表情包 */
.me-card{border:1px solid var(--line);background:var(--panel);border-radius:var(--r);
  padding:12px;margin-bottom:9px}
.me-card .w{font-size:16px;font-weight:500}
.me-card .mn{font-size:13.5px;color:var(--dim);margin-top:5px;white-space:pre-wrap;line-height:1.7}
.me-card .al{font-size:11.5px;color:var(--dim2);margin-top:5px}
.sk-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(96px,1fr));gap:9px}
.sk-cell{border:1px solid var(--line);background:var(--panel);border-radius:var(--r);
  overflow:hidden;position:relative}
.sk-cell img{display:block;width:100%;height:96px;object-fit:cover;cursor:pointer;background:var(--panel2)}
.sk-cell .nm{font-size:11.5px;color:var(--dim);padding:5px 7px;
  overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.sk-cell .ops{display:flex;border-top:1px solid var(--line)}
.sk-cell .ops button{flex:1;padding:6px 0;font-size:11.5px;color:var(--dim)}
.sk-cell .ops button.danger{color:var(--err)}
.sk-cell .send{position:absolute;top:6px;right:6px;width:24px;height:24px;border-radius:50%;
  background:#0b0e13b0;color:#fff;font-size:13px;line-height:24px;text-align:center;
  opacity:0;transition:.15s}
.sk-cell:hover .send{opacity:1}
/* 健康 */
.hl-sum{display:flex;gap:9px;margin-bottom:10px}
.hl-sum .c{flex:1;border:1px solid var(--line);background:var(--panel);border-radius:var(--r);
  padding:11px;text-align:center}
.hl-sum .c b{display:block;font-size:19px}
.hl-sum .c small{font-size:11px;color:var(--dim2)}
.hrow{display:flex;align-items:center;gap:8px;padding:9px 8px;border-bottom:1px solid var(--line);font-size:13px}
.hrow .dt{flex:0 0 82px;color:var(--tx-3);font-family:var(--latin);font-size:10px;
  letter-spacing:.24em}
.hrow .v{flex:1;min-width:0}
.hrow .nt{color:var(--dim2);font-size:11.5px;display:block;margin-top:2px}
.hrow button{font-size:12px;color:var(--dim);border:1px solid var(--line);border-radius:7px;padding:3px 9px}
.hrow button.danger{color:var(--err);border-color:var(--err)}
`;
  document.head.append(css);

  function sheet(title,build){
    const wrap=el("div","sheet"), bx=el("div","box nt-sheet");
    const h=el("div","bh"), b=el("b",null,title), x=el("button","x ibtn");
    x.append(nestIcon("close"));
    x.onclick=()=>wrap.remove(); h.append(b,x); bx.append(h); wrap.append(bx);
    wrap.onclick=e=>{if(e.target===wrap)wrap.remove();};
    document.body.append(wrap); build(bx,()=>wrap.remove()); return wrap;
  }
  const field=(bx,label,ph,val)=>{
    if(label)bx.append(el("span","lb",label));
    const i=el("input","nt-in"); i.type="text"; if(ph)i.placeholder=ph;
    if(val!=null)i.value=val; bx.append(i); return i;
  };
  const pick=(bx,label,opts,val)=>{
    bx.append(el("span","lb",label));
    const s=el("select");
    opts.forEach(o=>{const op=el("option",null,o[1]);op.value=o[0];s.append(op);});
    if(val!=null)s.value=val; bx.append(s); return s;
  };

  let SEC="cal";
  /* ★ 「跳到某一档」的口子必须在**模块作用域**上 ——
     原来它定义在 NEST_PANES.notes 里面，也就是「这一页至少开过一次之后」才有。
     结果全新一次会话里，首页的「日历 / 空间」、一起页点开一条、十一档弹层
     全都只落到默认档（弱回退 go("notes") 不带档位）。
     现在：记下想要哪一档 → 渲染 → 渲染完立刻按上去。 */
  let notesSel=null, wantSec=null;
  window.nestNotesOpen=function(label){
    wantSec=label;
    if(window.nestGo)window.nestGo("notes");   /* 同步渲染，回来时 notesSel 已经装好 */
    if(notesSel)notesSel(label);
    else if(label)setTimeout(()=>{ if(notesSel)notesSel(label); },80);
  };

  window.NEST_PANES.notes=function(box){
    box.innerHTML="";
    const chips=el("div","nt-chips");
    const chipsEl=chips;
    const body=el("div");
    box.append(chips,body);
    const SECS=[
      ["cal","日历",secCal],
      ["memes","梗库",secMemes],
      ["sticker","表情包",secSticker],
      ["health","健康",secHealth],
      ["space","空间",secMoments],
      ["star","收藏",secStar],
    ];
    SECS.forEach(s=>{
      const b=el("button",(s[0]===SEC?"on":""),s[1]);
      b.onclick=()=>{
        SEC=s[0];
        [].slice.call(chips.children).forEach(x=>x.classList.toggle("on",x===b));
        body.innerHTML="";
        s[2](body);
      };
      chips.append(b);
    });
    /* 装上「切到某一档」：别处（首页 / 一起页 / 表情包管理）都靠它落到对的档 */
    notesSel=function(label){
      if(!label)return;
      const chips=[].slice.call(chipsEl.children);
      const b=chips.filter(x=>x.textContent.replace(/\s+\d+$/,"")===label)[0]
            ||chips[SECS.map(x=>x[1]).indexOf(label)];
      if(b)b.click();
    };
    const cur=SECS.filter(s=>s[0]===SEC)[0]||SECS[0];
    cur[2](body);
    /* 进来之前就点了「日历」的话，这一下把它按上 */
    if(wantSec){ const w=wantSec; wantSec=null; notesSel(w); }
  };

  const loading=list=>list.append(el("div","hint","读取中…"));
  const failed=(list,e)=>list.append(el("div","errbox","读不出来："+((e&&e.message)||e)));

  /* ═══ 日历 ═══ */
  async function secCal(body){
    body.innerHTML="";
    /* mode：'upcoming'（往后的，默认）· 'all'（连过去的也翻）· 'day'（点中了某一天） */
    let items=[], cur=new Date(), picked="", mode="upcoming";
    const top=el("div","nt-top");
    const add=el("button","pri");
    add.append(nestIcon("plus"),document.createTextNode(" 记一件"));
    const bUp=el("button",null,"往后"), bAll=el("button",null,"全部");
    top.append(el("div","sp"),bUp,bAll,add);
    const mo=el("div","cal-mo");
    const prev=el("button",null), next=el("button",null), mt=el("div","t");
    prev.append(nestIcon("back",16)); next.append(nestIcon("forward",16));
    prev.title="上个月"; next.title="下个月";
    mo.append(prev,mt,next);
    const grid=el("div","cal-grid");
    const list=el("div");
    body.append(top,mo,grid,list);
    add.onclick=()=>editCal(null);

    prev.onclick=()=>{cur=new Date(cur.getFullYear(),cur.getMonth()-1,1);drawCal();};
    next.onclick=()=>{cur=new Date(cur.getFullYear(),cur.getMonth()+1,1);drawCal();};
    bUp.onclick=()=>{ picked=""; mode="upcoming"; drawCal(); };
    bAll.onclick=()=>{ picked=""; mode="all"; drawCal(); };

    loading(list);
    try{
      const j=await jget("/api/calendar");
      items=j.items||[];
    }catch(e){ list.innerHTML=""; failed(list,e); }
    drawCal();

    function byDay(d){ return items.filter(x=>(x.date||"")===d); }
    function drawCal(){
      bUp.classList.toggle("on",mode==="upcoming");
      bAll.classList.toggle("on",mode==="all");
      mt.textContent=cur.getFullYear()+" 年 "+(cur.getMonth()+1)+" 月";
      grid.innerHTML="";
      ["日","一","二","三","四","五","六"].forEach(h=>grid.append(el("div","h",h)));
      const y=cur.getFullYear(), m=cur.getMonth();
      const first=new Date(y,m,1), lead=first.getDay(), days=new Date(y,m+1,0).getDate();
      const tISO=todayISO();
      for(let i=0;i<lead;i++)grid.append(el("button","out",""));
      for(let d=1;d<=days;d++){
        const iso=y+"-"+pad2(m+1)+"-"+pad2(d);
        const b=el("button",((iso===tISO?"today ":"")+(iso===picked?"on":"")));
        b.append(el("span",null,String(d)));
        if(byDay(iso).length)b.append(el("b"));
        b.onclick=()=>{
          if(picked===iso){ picked=""; mode="upcoming"; }
          else { picked=iso; mode="day"; }
          drawCal();
        };
        grid.append(b);
      }
      drawList();
    }
    function drawList(){
      list.innerHTML="";
      let rows=items.slice();
      if(mode==="day"){
        rows=rows.filter(x=>(x.date||"")===picked);
      }else if(mode==="all"){
        /* 以后在前（越近越靠前），过去在后（也是越近越靠前）—— 两头都看得见 */
        rows.sort((a,b)=>{const pa=a.days<0?1:0, pb=b.days<0?1:0;
          if(pa!==pb)return pa-pb;
          return pa? (b.days-a.days) : (a.days-b.days);});
      }else{
        rows=rows.filter(x=>(x.days==null||x.days>=0));
        rows.sort((a,b)=>(a.days==null?1e9:a.days)-(b.days==null?1e9:b.days));
      }
      rows=rows.slice(0,80);
      if(!rows.length){
        list.append(el("div","hint",mode==="day"?"这一天还没有事"
                       :(mode==="all"?"一件都还没记":"往后还没有记下的事")));
        return;
      }
      rows.forEach(it=>list.append(calRow(it)));
    }
    function calRow(it){
      const past=(it.days!=null&&it.days<0);
      const r=el("div","crow"+(it.done?" done":"")+(past?" past":""));
      r.append(el("span","dt",(it.date||"").slice(5)+(it.time?(" "+it.time):"")));
      const tt=el("div","tt",it.title||"");
      if(it.days!=null&&it.days>=0)tt.append(el("em",null,it.days===0?"就是今天":(it.days+" 天后")));
      if(past)tt.append(el("em",null,(-it.days)+" 天前"));
      r.append(tt);
      if(it.kind)r.append(el("span","kd",it.kind));
      if(it.who==="ai")r.append(el("span","kd","它留的"));
      if(it.years)r.append(el("span","kd","第 "+it.years+" 年"));
      if(it.id>0&&it.kind!=="纪念日"){
        const ck=el("button","ck",it.done?"撤销":"完成");
        ck.onclick=async()=>{
          const rr=await jpost("/api/calendar/toggle",{id:it.id});
          if(rr.ok){it.done=!it.done;drawCal();}else say("没改成");
        };
        r.append(ck);
      }
      const ed=el("button",null,"改");
      ed.onclick=()=>editCal(it);
      const dl=el("button","danger","删");
      dl.onclick=async()=>{
        if(!confirm("删掉这条？"))return;
        const rr=await jpost("/api/calendar/del",{id:it.id});
        if(rr.ok){
          items=items.filter(x=>x.id!==it.id);
          say("删了");drawCal();
        }else say("删不掉");
      };
      r.append(ed,dl);
      return r;
    }
    /* 记一件 / 改一件。后端没有「改」这条 —— 改＝先删旧的再加新的。
       · 纪念日那类 id 是负的（anniversaries 表），删的时候原样传负数，后端认得。 */
    function editCal(it){
      const isNew=!it;
      sheet(isNew?"记一件":"改这件", bx=>{
        const ti=field(bx,"什么事","比如：体检 / 他生日 / 交稿",it?it.title:"");
        const dt=field(bx,"哪天（YYYY-MM-DD）","2025-01-31",(it&&it.date)||(picked||todayISO()));
        const tm=field(bx,"几点（可空）","09:30",(it&&it.time)||"");
        const kd=pick(bx,"哪一类",
          [["","不分"],["待办","待办"],["提醒","提醒"],["约会","约会"],["课程","课程"],["纪念日","纪念日（每年重复）"]],
          (it&&it.kind)||"");
        const row=el("div","nt-btns");
        const ok=el("button","pri","存"), no=el("button",null,"取消");
        row.append(ok,no); bx.append(row);
        no.onclick=()=>bx.parentNode.remove();
        ok.onclick=async()=>{
          const title=ti.value.trim(), date=dt.value.trim();
          if(!title){say("写点是什么事");return;}
          if(!/^\d{4}-\d{2}-\d{2}$/.test(date)){say("日期要写成 2025-01-31 这种");return;}
          if(!isNew){ await jpost("/api/calendar/del",{id:it.id}); }
          const r=await jpost("/api/calendar/add",
            {title:title,date:date,time:tm.value.trim(),kind:kd.value,who:it?it.who:"me"});
          if(r.ok){say(isNew?"记下了":"改好了");bx.parentNode.remove();secCal(body);}
          else say("没存上："+(r.err||"?"));
        };
      });
    }
  }

  /* ═══ 梗库 ═══ */
  async function secMemes(body){
    body.innerHTML="";
    let items=[], q="";
    const top=el("div","nt-top");
    const si=el("input","q"); si.type="text"; si.placeholder="在梗库里找一个词…";
    const add=el("button","pri");
    add.append(nestIcon("plus"),document.createTextNode(" 录一条"));
    top.append(si,add);
    body.append(top);
    const list=el("div"); body.append(list);
    add.onclick=()=>editMeme(body,null);
    loading(list);
    try{
      const j=await jget("/api/memes");
      items=j.items||[];
    }catch(e){ list.innerHTML=""; failed(list,e); return; }
    draw();
    function draw(){
      list.innerHTML="";
      const kw=q.trim();
      const rows=items.filter(x=>!kw||
        ((x.word||"")+ (x.aliases||"") + (x.meaning||"")).indexOf(kw)>=0);
      if(!rows.length){
        list.append(el("div","hint",kw?"没找到这个梗":"梗库还空着 —— 你们之间那些只有你俩懂的词，记在这儿"));
        return;
      }
      rows.forEach(x=>{
        const c=el("div","me-card");
        c.append(el("div","w",x.word||""));
        if(x.meaning)c.append(el("div","mn",x.meaning));
        if(x.aliases)c.append(el("div","al","也叫："+x.aliases));
        const m=el("div","nt-meta");
        if(x.day)m.append(el("span",null,x.day));
        if(x.origin)m.append(el("span","tag",x.origin));
        if(x.ref_count)m.append(el("span","tag","被想起 "+x.ref_count+" 次"));
        const ops=el("div","nt-ops");
        const e1=el("button",null,"改"); e1.onclick=()=>editMeme(body,x);
        const e2=el("button","danger","删"); e2.onclick=async()=>{
          if(!confirm("删掉「"+(x.word||"")+"」？"))return;
          const r=await jpost("/api/memes/"+x.id+"/del",{});
          if(r.ok){say("删了");items=items.filter(y=>y.id!==x.id);draw();}else say("删不掉");
        };
        ops.append(e1,e2); m.append(ops); c.append(m);
        list.append(c);
      });
    }
    si.oninput=()=>{q=si.value;draw();};
  }

  function editMeme(body,m){
    const isNew=!m;
    sheet(isNew?"录一条梗":"改这条梗", bx=>{
      const w=field(bx,"梗本身","你们怎么叫它",m?m.word:"");
      const mn=field(bx,"它是什么意思","只有你们懂的这层意思",m?m.meaning:"");
      const al=field(bx,"别名 / 变体（可空）","逗号隔开",m?m.aliases:"");
      const og=field(bx,"从哪来的（可空）","哪天的什么事",m?m.origin:"");
      const row=el("div","nt-btns");
      const ok=el("button","pri","存"), no=el("button",null,"取消");
      row.append(ok,no); bx.append(row);
      no.onclick=()=>bx.parentNode.remove();
      ok.onclick=async()=>{
        const word=w.value.trim(), meaning=mn.value.trim();
        if(!word||!meaning){say("梗和它是什么意思，两样都得写");return;}
        const r=isNew
          ? await jpost("/api/memes",{word:word,meaning:meaning,aliases:al.value.trim(),origin:og.value.trim()})
          : await jpost("/api/memes/"+m.id+"/edit",
              {word:word,meaning:meaning,aliases:al.value.trim(),origin:og.value.trim()});
        if(r.ok){say(isNew?"录下了":"改好了");bx.parentNode.remove();secMemes(body);}
        else say("没存上："+(r.err||"?"));
      };
    });
  }

  /* ═══ 表情包 ═══ */
  const SK_MAX=1600;
  function shrink(file,cb){
    let done=false;
    const fin=v=>{if(!done){done=true;cb(v);}};
    const rd=new FileReader();
    rd.onload=()=>{
      const to=setTimeout(()=>fin(rd.result),8000);
      const im=new Image();
      im.onload=()=>{
        clearTimeout(to);
        try{
          const sc=Math.min(SK_MAX/im.width,SK_MAX/im.height,1);
          const cv=document.createElement("canvas");
          cv.width=Math.max(1,Math.round(im.width*sc));
          cv.height=Math.max(1,Math.round(im.height*sc));
          cv.getContext("2d").drawImage(im,0,0,cv.width,cv.height);
          fin(cv.toDataURL("image/jpeg",0.88));
        }catch(e){fin(rd.result);}
      };
      im.onerror=()=>{clearTimeout(to);fin(rd.result);};
      im.src=rd.result;
    };
    rd.onerror=()=>fin(null);
    rd.readAsDataURL(file);
  }

  async function secSticker(body){
    body.innerHTML="";
    const top=el("div","nt-top");
    const hint=el("span");
    hint.append(document.createTextNode("这一节是**管**这张表的（传 / 改名字和标签 / 删）。"
      +"要发的时候在聊天输入框边上点 "),
      nestIcon("sticker"),
      document.createTextNode(" —— 助手也能发，他自己照名字和标签挑"));
    hint.style.cssText="font-size:11.5px;color:var(--dim2)";
    const add=el("button","pri");
    add.append(nestIcon("plus"),document.createTextNode(" 传一张"));
    window.nestStickerLibHint=()=>say("表情包在下面 —— 得先传几张");
    top.append(hint,el("div","sp"),add);
    body.append(top);
    const list=el("div"); body.append(list);
    add.onclick=pickFile;
    await load();
    async function load(){
      list.innerHTML="";
      loading(list);
      let j;
      try{ j=await jget("/api/stickers"); }
      catch(e){ list.innerHTML=""; failed(list,e); return; }
      list.innerHTML="";
      const its=j.items||[];
      if(!its.length){
        list.append(el("div","hint","表情包还空着 —— 传几张你们常发的图，以后一句话配一张"));
        return;
      }
      const grid=el("div","sk-grid");
      its.forEach(s=>{
        const c=el("div","sk-cell");
        const im=el("img"); im.src=s.url; im.alt=s.name||""; im.loading="lazy";
        im.title="点一下放进输入框";
        im.onclick=()=>send(s);
        c.append(im);
        const sd=el("div","send"); sd.append(nestIcon("send")); sd.title="发送"; sd.onclick=()=>send(s);
        c.append(sd);
        c.append(el("div","nm",s.name||"（没名字）"));
        const ops=el("div","ops");
        const e1=el("button",null,"改"); e1.onclick=()=>edit(s);
        const e2=el("button","danger","删"); e2.onclick=async()=>{
          if(!confirm("从表情包里删掉这张？聊天记录里用过的那张还在。"))return;
          const r=await jpost("/api/stickers/"+s.id+"/del",{});
          if(r.ok){say("删了");load();}else say("删不掉");
        };
        ops.append(e1,e2); c.append(ops);
        grid.append(c);
      });
      list.append(grid);
    }
    function send(s){
      const A=window.nestAttach;
      if(!A||!A.stage){say("附件模块没装上，这张发不了");return;}
      A.stage([{kind:"img",url:s.url,name:s.name||"表情"}]);
      say("放进去了 —— 说句话一起发");
      goChat();
    }
    function edit(s){
      sheet("改这张", bx=>{
        const nm=field(bx,"叫什么","名字",s.name||"");
        const tg=field(bx,"标签（可空）","开心, 猫",s.tags||"");
        const row=el("div","nt-btns");
        const ok=el("button","pri","存"), no=el("button",null,"取消");
        row.append(ok,no); bx.append(row);
        no.onclick=()=>bx.parentNode.remove();
        ok.onclick=async()=>{
          const r=await jpost("/api/stickers/"+s.id+"/edit",
            {name:nm.value.trim(),tags:tg.value.trim()});
          if(r.ok){say("改好了");bx.parentNode.remove();load();}
          else say("没存上："+(r.err||"?"));
        };
      });
    }
    function pickFile(){
      const inp=el("input"); inp.type="file"; inp.accept="image/*"; inp.hidden=true;
      document.body.append(inp);
      inp.addEventListener("change",()=>{
        const f=(inp.files||[])[0];
        inp.remove();
        if(!f)return;
        const nm=(f.name||"表情").replace(/\.[^.]+$/,"").slice(0,60);
        say("正在压小、传上去…");
        shrink(f,async du=>{
          if(!du){say("这张图读不出来");return;}
          let up=null;
          try{
            up=await jpost("/api/upload",{dataURL:du});
          }catch(e){ up=null; }
          if(!up||!up.url){say("没传上去："+((up&&up.err)||"网络？"));return;}
          const r=await jpost("/api/stickers",{url:up.url,name:nm,tags:""});
          if(r.ok){say("收进表情包了");load();}
          else say("没存上："+(r.err||"?"));
        });
      });
      inp.click();
    }
  }

  /* ═══ 健康 ═══ */
  async function secHealth(body){
    body.innerHTML="";
    const top=el("div","nt-top");
    const add=el("button","pri");
    add.append(nestIcon("plus"),document.createTextNode(" 记一天"));
    top.append(el("div","sp"),add);
    body.append(top);
    const list=el("div"); body.append(list);
    add.onclick=()=>editHealth(body,null);
    loading(list);
    let items=[];
    try{
      const j=await jget("/api/health_recent?days=60");
      items=j.items||[];
    }catch(e){ list.innerHTML=""; failed(list,e); return; }
    list.innerHTML="";
    if(!items.length){
      list.append(el("div","hint","还没有记过。走了一万步、睡得不踏实、今天量了心率 —— 记一天就从这儿开始。"));
      return;
    }
    const last=items[items.length-1];
    const p=payload(last);
    const sum=el("div","hl-sum");
    sum.append(hcell(p.steps!=null?Number(p.steps).toLocaleString():"—","步"));
    sum.append(hcell(p.resting_hr!=null?Math.round(p.resting_hr):"—","静息心率"));
    sum.append(hcell(p.hrv_ms!=null?Math.round(p.hrv_ms):"—","HRV ms"));
    list.append(el("div","nt-lb","最近一条："+(last.t||"")));
    list.append(sum);

    items.slice().reverse().forEach(it=>{
      const d=payload(it);
      const r=el("div","hrow");
      r.append(el("span","dt",it.t||""));
      const v=el("div","v");
      const bits=[];
      if(d.steps!=null)bits.push(Number(d.steps).toLocaleString()+" 步");
      if(d.resting_hr!=null)bits.push("静息 "+Math.round(d.resting_hr));
      if(d.hrv_ms!=null)bits.push("HRV "+Math.round(d.hrv_ms));
      if(d.menstrual)bits.push(String(d.menstrual));
      v.textContent=bits.join(" · ")||"这一天是空的";
      if(d.note)v.append(el("span","nt",d.note));
      r.append(v);
      const ed=el("button",null,"改"); ed.onclick=()=>editHealth(body,it);
      const dl=el("button","danger","删"); dl.onclick=async()=>{
        if(!confirm("删掉 "+(it.t||"")+" 这一条？"))return;
        const rr=await jpost("/api/health/"+it.id+"/del",{});
        if(rr.ok){say("删了");secHealth(body);}else say("删不掉");
      };
      r.append(ed,dl);
      list.append(r);
    });
  }

  function payload(it){
    let p=it&&it.payload;
    if(typeof p==="string"){try{p=JSON.parse(p);}catch(e){p=null;}}
    return p&&typeof p==="object"?p:{};
  }
  function hcell(big,small){
    const c=el("div","c");
    c.append(el("b",null,big),el("small",null,small));
    return c;
  }
  function editHealth(body,it){
    const d=payload(it);
    const isNew=!it;
    sheet(isNew?"记一天":"改这一天", bx=>{
      const day=field(bx,"哪天（YYYY-MM-DD）","2025-01-31",(it&&it.t)||todayISO());
      const st=field(bx,"走了多少步（可空）","8000",d.steps!=null?String(d.steps):"");
      const hr=field(bx,"静息心率（可空）","58",d.resting_hr!=null?String(d.resting_hr):"");
      const hv=field(bx,"HRV ms（可空）","62",d.hrv_ms!=null?String(d.hrv_ms):"");
      const mn=field(bx,"经期备注（可空）","第 2 天 / 结束了",d.menstrual||"");
      const nt=field(bx,"备注（可空）","今天有点累",d.note||"");
      const row=el("div","nt-btns");
      const ok=el("button","pri","存"), no=el("button",null,"取消");
      row.append(ok,no); bx.append(row);
      no.onclick=()=>bx.parentNode.remove();
      ok.onclick=async()=>{
        const dd=day.value.trim();
        if(!/^\d{4}-\d{2}-\d{2}$/.test(dd)){say("日期要写成 2025-01-31 这种");return;}
        const body2={day:dd,steps:st.value.trim(),resting_hr:hr.value.trim(),
                     hrv_ms:hv.value.trim(),menstrual:mn.value.trim(),note:nt.value.trim()};
        if(!body2.steps&&!body2.resting_hr&&!body2.hrv_ms&&!body2.menstrual&&!body2.note){
          say("一天至少记一样");return;
        }
        const r=await jpost("/api/health",body2);
        if(r.ok){say(isNew?"记下了":"改好了");bx.parentNode.remove();secHealth(body);}
        else say("没存上："+(r.err||"?"));
      };
    });
  }
  /* ═══ 空间 ═══
     moments + moment_comments。原项目那一页的排法照搬：分「他发的 / 你发的 / 有评论」，
     一条一张卡（正文+配图+楼里的评论），每条底下留一个「回一句」——
     原项目 0805 就是「能贴不能回」被点名的。 */
  async function secMoments(body){
    body.innerHTML="";
    const top=el("div","nt-top");
    const add=el("button","pri");
    add.append(nestIcon("plus"),document.createTextNode(" 贴一条"));
    const poke=el("button",null,"戳他发一条");
    const sp=el("div","sp");
    const msg=el("div","hint");
    top.append(add,poke,sp);
    const chips=el("div","nt-chips");
    const list=el("div");
    body.append(top,chips,msg,list);
    let ALL=[], FILT="全部";
    const TABS=[["全部","这儿贴的都是随手想给对方看的"],
                ["他发的","他贴上去的"],["你发的","你贴上去的"],
                ["有评论","底下接过话的那些"]];
    function mineOf(x){ return !x.author||x.author==="ai"; }   /* true＝他发的 */
    function paint(){
      const n={"他发的":0,"你发的":0,"有评论":0};
      ALL.forEach(x=>{ n[mineOf(x)?"他发的":"你发的"]++; if((x.comments||[]).length)n["有评论"]++; });
      chips.innerHTML="";
      TABS.forEach(([k,hint])=>{
        const b=el("button",(k===FILT?"on":null),k===FILT?k:(k+" "+(k==="全部"?ALL.length:n[k])));
        b.title=hint;
        b.onclick=()=>{FILT=k;paint();};
        chips.append(b);
      });
      list.innerHTML="";
      const rows=ALL.filter(x=>FILT==="全部"?true:(FILT==="有评论"?((x.comments||[]).length>0)
                                            :(FILT==="他发的"?mineOf(x):!mineOf(x))));
      if(!rows.length){ list.append(el("div","hint","这一档还空着。")); return; }
      rows.forEach(x=>list.append(momentCard(x)));
    }
    function momentCard(x){
      const c=el("div","nt-card");
      const head=el("div","nt-meta");
      head.append(el("span",(mineOf(x)?"tag ai":"tag me"),mineOf(x)?"他":"你"));
      head.append(el("span",null,(x.day||"")+" "+(x.t||"")));
      const ops=el("div","nt-ops");
      const be=el("button",null,"改");
      be.onclick=()=>{
        sheet("改这条",(bx,close)=>{
          const t=el("textarea"); t.value=x.content||"";
          bx.append(t);
          const row=el("div","nt-btns");
          const ok=el("button","pri","存下"), no=el("button",null,"取消");
          row.append(ok,no); bx.append(row);
          no.onclick=close;
          ok.onclick=async()=>{
            const v=t.value.trim(); if(!v){say("正文不能空");return;}
            const r=await jpost("/api/moments/"+x.id+"/edit",{content:v});
            if(r.ok){ say("改好了"); close(); load(); } else say("没改成："+(r.err||"?"));
          };
        });
      };
      const bd=el("button","danger","删");
      bd.onclick=async()=>{
        if(!confirm("删掉这条？楼里的评论也一起没。"))return;
        const r=await jpost("/api/moments/"+x.id+"/del",{});
        if(r.ok){say("删了");load();} else say("删不掉："+(r.err||"?"));
      };
      ops.append(be,bd); head.append(ops);
      c.append(head);
      if(x.content)c.append(el("div","nt-txt",x.content));
      if(x.image){
        const im=el("img"); im.src=x.image; im.loading="lazy";
        im.style.cssText="max-width:100%;border-radius:10px;margin-top:8px;display:block";
        c.append(im);
      }
      (x.comments||[]).forEach(cm=>{
        const d=el("div"); d.style.cssText="margin-top:8px;padding-left:9px;border-left:2px solid var(--line)";
        const h=el("div","nt-meta");
        h.append(el("span",(cm.author==="ai"?"tag ai":"tag me"),cm.author==="ai"?"他":"你"));
        h.append(el("span",null,cm.t||""));
        const o2=el("div","nt-ops");
        const bx=el("button","danger","删");
        bx.onclick=async()=>{
          const r=await jpost("/api/moments/comment/"+cm.id+"/del",{});
          if(r.ok){say("删了");load();} else say("删不掉");
        };
        o2.append(bx); h.append(o2);
        d.append(h,el("div","nt-txt",cm.content||""));
        c.append(d);
      });
      const rep=el("div","nt-btns");
      const bReply=el("button",null,"回一句");
      rep.append(bReply);
      c.append(rep);
      bReply.onclick=()=>{
        const wrap=sheet("回一句",(bx,close)=>{
          const t=el("textarea"); t.placeholder="说点什么…";
          bx.append(t);
          const row=el("div","nt-btns");
          const ok=el("button","pri","发出去"), no=el("button",null,"取消");
          row.append(ok,no); bx.append(row);
          no.onclick=close;
          ok.onclick=async()=>{
            const v=t.value.trim(); if(!v){say("空的");return;}
            ok.disabled=true;
            const r=await jpost("/api/moments/"+x.id+"/comment",{content:v});
            if(r.ok){ say("回了 —— 他看到会接一句"); close(); setTimeout(load,1200); }
            else{ ok.disabled=false; say("没回上："+(r.err||"?")); }
          };
        });
      };
      return c;
    }
    async function load(){
      list.innerHTML="";
      loading(list);
      let j;
      try{ j=await jget("/api/moments"); }
      catch(e){ list.innerHTML=""; failed(list,e); return; }
      ALL=j.items||[];
      msg.textContent = ALL.length? "" : "还没贴过。贴一条，他会接话。";
      paint();
    }
    add.onclick=()=>{
      sheet("贴一条",(bx,close)=>{
        const t=el("textarea"); t.placeholder="随手想给对方看的一句话…";
        bx.append(t);
        bx.append(el("div","lb","配张图（可以不配）"));
        let img="";
        const row=el("div","nt-btns");
        const bPic=el("button",null,"选一张图"), bSend=el("button","pri","贴出去"), bNo=el("button",null,"取消");
        const prev=el("div");
        row.append(bPic,bSend,bNo);
        bx.append(row,prev);
        bPic.onclick=()=>{
          const inp=el("input"); inp.type="file"; inp.accept="image/*"; inp.hidden=true;
          document.body.append(inp);
          inp.addEventListener("change",()=>{
            const f=(inp.files||[])[0]; inp.remove(); if(!f)return;
            bPic.disabled=true; bPic.textContent="传…";
            shrink(f,async du=>{
              if(!du){ bPic.disabled=false; bPic.textContent="选一张图"; say("这张图读不出来"); return; }
              const up=await jpost("/api/upload",{dataURL:du});
              bPic.disabled=false; bPic.textContent="换一张";
              if(!up||!up.url){ say("没传上去："+((up&&up.err)||"网络？")); return; }
              img=up.url; prev.innerHTML="";
              const im=el("img"); im.src=img;
              im.style.cssText="max-width:100%;border-radius:10px;margin-top:8px";
              prev.append(im);
            });
          });
          inp.click();
        };
        bNo.onclick=close;
        bSend.onclick=async()=>{
          const v=t.value.trim();
          if(!v&&!img){ say("写一句，或者配张图"); return; }
          bSend.disabled=true;
          const r=await jpost("/api/moments/mine",{content:v,image:img||null});
          bSend.disabled=false;
          if(r.ok){ say("贴上去了 —— 他可能会在楼里接一句"); close(); setTimeout(load,1500); }
          else say("没贴上："+(r.err||"?"));
        };
      });
    };
    poke.onclick=async()=>{
      if(!confirm("让他自己发一条？他会用自己的引擎写一句（花一次调用）。"))return;
      poke.disabled=true; poke.textContent="他在写…";
      const r=await jpost("/api/moments/new",{});
      poke.disabled=false; poke.textContent="戳他发一条";
      if(r.ok){ say("他贴了一条"); load(); }
      else say("这回没写出来"+((r.err)?("："+r.err):"")+" —— 引擎接上了再试");
    };
    load();
  }

  /* ═══ 收藏 ═══
     点过星的那些话。· 每条都带上文（「你说：…」）—— 原项目 0807 定了这条：
     没有上文，几个月后翻出来不知道当时在聊什么。 */
  async function secStar(body){
    body.innerHTML="";
    const top=el("div","nt-top");
    const hint=el("div","hint","聊天里每条消息右边的「⋯ › 收藏」按一下就存到这儿。");
    top.append(hint);
    const list=el("div");
    body.append(top,list);
    async function load(){
      list.innerHTML=""; loading(list);
      let j;
      try{ j=await jget("/api/chat/starred"); }
      catch(e){ list.innerHTML=""; failed(list,e); return; }
      const its=j.items||[];
      list.innerHTML="";
      if(!its.length){ list.append(el("div","hint","还没收藏过。聊天里按「⋯ › 收藏」，那句话就存到这儿。")); return; }
      its.forEach(x=>{
        const c=el("div","nt-card");
        const head=el("div","nt-meta");
        head.append(el("span",(x.role==="user"?"tag me":"tag ai"),x.role==="user"?"你说的":"他说的"));
        head.append(el("span",null,x.t||""));
        const ops=el("div","nt-ops");
        const bd=el("button","danger","取消收藏");
        bd.onclick=async()=>{
          const r=await jpost("/api/chat/"+x.id+"/star",{});
          if(r.ok){ say(r.starred?"收下了":"取消了"); load(); } else say("没成："+(r.err||"?"));
        };
        const bg=el("button",null,"去聊天");
        bg.onclick=()=>{ if(window.nestGo)window.nestGo("chat"); };
        ops.append(bg,bd); head.append(ops);
        c.append(head);
        if(x.ask){
          const q=el("div","nt-meta");
          q.style.marginTop="2px";
          q.append(el("span",null,"你说："+x.ask));
          c.append(q);
        }
        c.append(el("div","nt-txt",x.content||""));
        if(x.think){
          const d=el("details"); d.style.marginTop="8px";
          const sm=el("summary","nt-meta","当时的思考过程");
          d.append(sm,el("div","nt-txt",x.think));
          c.append(d);
        }
        list.append(c);
      });
    }
    load();
  }
}catch(e){console.error("nest-notes:",e);}
})();
