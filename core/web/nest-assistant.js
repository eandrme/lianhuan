/* ══════════════════════════════════════════════════════════
   巢 · 助手 ⑨：一位助手下面挂几扇窗
   装法：nest.html 里，nest-think.js 那行【下面】再加一行
        <script src="/nest-assistant.js?v=1"></script>

   两处：
     · **设置 › 助手管理**（`window.nestAssistantSection`，由 nest-setting.js 要一节）
       一位助手＝头像 ＋ 名字 ＋ 名字下面那行小字 ＋ 系统提示词 ＋ 它能用的 MCP ＋
       挂在他名下的窗口 ＋ 他写的信。
     · **聊天顶栏那颗身份牌**（`#nestAsstBadge`）—— 你现在这个窗口是谁在说话。
       点一下能看到他的小字、他名下的窗、以及通往助手管理的门。

   后端全在 `core/assistants.py`（语义一处定义）+ `/api/assistants*`。
   ★ 没配过助手时这一层整个不出现 —— 老行为一字不差。
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
  const jpost=async(u,b)=>{
    let r;
    try{
      r=await fetch(u,{method:"POST",credentials:"same-origin",
        headers:{"Content-Type":"application/json"},body:JSON.stringify(b||{})});
    }catch(e){ return {ok:false,err:"连不上服务器"}; }
    let d=null; try{ d=await r.json(); }catch(e){}
    if(!r.ok||!d||d.ok===false)
      return {ok:false,status:r.status,err:(d&&(d.err||d.error))||("HTTP "+r.status)};
    return d;
  };
  const gSid=()=>{
    try{ return (typeof SID!=="undefined"&&SID)||localStorage.getItem("nest_sid")||"main"; }
    catch(e){ return localStorage.getItem("nest_sid")||"main"; }
  };

  const css=document.createElement("style");
  css.textContent=`
.as-row{display:flex;align-items:center;gap:10px;border:1px solid var(--line);
  border-radius:var(--r-sm);padding:9px 11px;margin-bottom:8px;background:var(--panel2)}
.as-av{width:38px;height:38px;border-radius:50%;flex:0 0 38px;object-fit:cover;
  background:var(--panel);border:1px solid var(--line);display:flex;align-items:center;
  justify-content:center;font-size:17px;color:var(--dim2)}
.as-mid{flex:1;min-width:0}
.as-mid b{font-size:14.5px}
.as-mid .sg{font-size:11.5px;color:var(--dim2);margin-top:1px;
  overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.as-mid .mt{font-size:11px;color:var(--dim2);margin-top:3px}
.as-av-big{width:64px;height:64px;border-radius:50%;object-fit:cover;background:var(--panel2);
  border:1px solid var(--line);display:flex;align-items:center;justify-content:center;
  font-size:26px;color:var(--dim2)}
.as-line{display:flex;align-items:center;gap:9px;margin:6px 0}
.as-chk{display:flex;align-items:center;gap:7px;padding:5px 0;font-size:13px;color:var(--dim)}
.as-chk input{width:16px;height:16px;accent-color:var(--accent);flex:0 0 auto}
.as-chk .sp{flex:1}
.as-chk .tiny{font-size:11px;color:var(--dim2)}
.as-box{border:1px solid var(--line);border-radius:var(--r-sm);padding:8px 10px;margin-top:4px;
  max-height:190px;overflow:auto;background:var(--panel2)}
.as-mail{border-bottom:1px solid var(--line);padding:7px 0;font-size:13px}
.as-mail:last-child{border-bottom:0}
.as-mail .hd{font-size:11px;color:var(--dim2);display:flex;gap:8px;align-items:center}
.as-mail .hd .sp{flex:1}
.as-mail .tx{white-space:pre-wrap;margin-top:4px;line-height:1.6}
#nestAsstBadge{display:flex;align-items:center;gap:6px;padding:3px 8px 3px 3px;border-radius:999px;
  border:1px solid var(--line);color:var(--dim);max-width:44vw}
#nestAsstBadge:hover{background:var(--panel2)}
#nestAsstBadge img,#nestAsstBadge .ph{width:22px;height:22px;border-radius:50%;object-fit:cover;
  background:var(--panel2);display:flex;align-items:center;justify-content:center;font-size:13px;flex:0 0 22px}
#nestAsstBadge .nm{font-size:13px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
`;
  document.head.append(css);

  /* ── 小工具 ── */
  function sheet(title,build){
    const wrap=el("div","sheet"), bx=el("div","box nt-sheet");
    const h=el("div","bh"), b=el("b",null,title), x=el("button","x ibtn","✕");
    x.onclick=()=>wrap.remove(); h.append(b,x); bx.append(h); wrap.append(bx);
    wrap.onclick=e=>{if(e.target===wrap)wrap.remove();};
    document.body.append(wrap); build(bx,()=>wrap.remove()); return wrap;
  }
  const input=(bx,label,ph,val)=>{
    if(label)bx.append(el("span","lb",label));
    const i=el("input","nt-in"); i.type="text"; if(ph)i.placeholder=ph; if(val!=null)i.value=val;
    bx.append(i); return i;
  };
  const AV_MAX=320;
  function shrink(file,cb){                     /* 头像：压到 320 就够，别把原图塞进去 */
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
  const avEl=(a,big)=>{
    if(a&&a.avatar){
      const im=el("img",big?"as-av-big":"as-av"); im.src=a.avatar; im.alt="";
      return im;
    }
    const d=el("div",big?"as-av-big":"as-av","🪺");
    return d;
  };

  /* ══════════ 设置 › 助手管理 ══════════ */
  window.nestAssistantSection=async function(box){
    const sec=el("div","set-sec"); sec.id="as-sec";
    sec.append(el("h4",null,"助手管理"));
    sec.append(el("div","sub","一位助手下面挂几扇窗。他自己有：头像 · 名字 · 名字下面那行小字 · "
      +"系统提示词 · 他能用的 MCP · 他写的信。"
      +"★ MCP 是**分人**的：新助手默认一个都不给，要哪个在下面手动勾 —— 别的助手不受影响。"));
    const head=el("div","set-btns");
    const bNew=el("button","pri","＋ 新建一位");
    head.append(bNew);
    const msg=el("div","set-msg");
    const list=el("div");
    sec.append(head,msg,list);
    box.append(sec);

    let ITEMS=[], WINDOWS=[], MCP=[];
    async function load(){
      list.innerHTML=""; list.append(el("div","set-msg","读着…"));
      try{
        const j=await jget("/api/assistants");
        ITEMS=j.items||[];
        const w=await jget("/api/nest/threads?with_assistant=1");
        WINDOWS=w.items||[];
        // ★ 还没有聊天记录的窗口不在那份名单里（名单是从 turns 里分的）——
        //   可人就是想现在把「当前这个窗口」挂过去。缺的话补一条。
        const sid0=gSid();
        if(!WINDOWS.some(x=>x.sid===sid0))
          WINDOWS=[{sid:sid0,title:"（当前窗口，还没说话）",n:0,assistant:""}].concat(WINDOWS);
        const m=await jget("/api/mcp");
        MCP=m.servers||[];
      }catch(e){
        list.innerHTML="";
        msg.className="set-msg err";
        msg.textContent="读不到（"+e.message+"）—— 服务端太旧就得重启一下";
        return;
      }
      msg.className="set-msg";
      msg.textContent = ITEMS.length
        ? ("现在有 "+ITEMS.length+" 位助手、"+WINDOWS.length+" 个窗口。"
           +"没挂到任何一位名下的窗口，算第一位（"+ITEMS[0].name+"）的。")
        : "还没建过助手 —— 现在整台机器是一位（全局那份人设）。建一位之后，"
          +"人设、工具、信都按人分。";
      draw();
    }
    function windowsOf(id){ return WINDOWS.filter(w=>w.assistant===id); }
    function draw(){
      list.innerHTML="";
      ITEMS.forEach((a,i)=>{
        const row=el("div","as-row");
        row.append(avEl(a));
        const mid=el("div","as-mid");
        mid.append(el("b",null,a.name||"（没名字）"));
        mid.append(el("div","sg",a.sign||"（名字下面那行小字还没写）"));
        const n=windowsOf(a.id).length;
        mid.append(el("div","mt",(i===0?"第一位 · 默认":"")+(i===0&&n?" · ":"")
          +(n?(n+" 个窗口"):"（没有单独挂着窗口）")
          +(a.mcp===null?" · MCP 不限":(a.mcp&&a.mcp.length?(" · MCP "+a.mcp.length+" 个"):" · MCP 一个都没给"))));
        row.append(mid);
        const ops=el("div","set-btns");
        const bM=el("button",null,"管理"); bM.onclick=()=>edit(a);
        const bW=el("button",null,"把当前窗口挂过来");
        bW.onclick=async()=>{
          const r=await jpost("/api/assistants/window",{sid:gSid(),id:a.id});
          if(r.ok){ say("这个窗口现在是「"+(a.name||"?")+"」的"); load(); peekBadge(); }
          else{ msg.className="set-msg err"; msg.textContent="没挂上："+(r.err||"?"); }
        };
        ops.append(bM,bW);
        if(ITEMS.length>1){
          const bD=el("button",null,"删");
          bD.onclick=async()=>{
            if(!confirm("删掉「"+(a.name||"?")+"」？他的窗口会退回第一位助手，聊天记录一条都不删。"))return;
            const r=await jpost("/api/assistants/del",{id:a.id});
            if(r.ok){ say("删了"); load(); peekBadge(); }
            else{ msg.className="set-msg err"; msg.textContent="删不掉："+(r.err||"?"); }
          };
          ops.append(bD);
        }
        row.append(ops);
        list.append(row);
      });
    }

    bNew.onclick=()=>{
      sheet("新建一位助手",(bx,close)=>{
        const nm=input(bx,"名字","比如：阿澈","");
        const hint=el("div","set-msg","新助手默认**一个 MCP 都不给** —— 建好之后在「管理」里勾。");
        const row=el("div","set-btns");
        const ok=el("button","pri","建"), no=el("button",null,"取消");
        row.append(ok,no); bx.append(hint,row);
        no.onclick=close;
        ok.onclick=async()=>{
          const r=await jpost("/api/assistants/save",{name:nm.value.trim()||"新的助手"});
          if(r.ok){ say("建好了"); close(); load(); peekBadge(); }
          else{ hint.className="set-msg err"; hint.textContent="没建成："+(r.err||"?"); }
        };
      });
    };

    /* ── 管理某一位 ── */
    function edit(a){
      const isNew=!a;
      let avatar=(a&&a.avatar)||"";
      let mcp=(a&&a.mcp===null)||!a ? null : (a.mcp||[]);   /* null＝不限 */
      sheet("管理："+((a&&a.name)||"新的助手"),(bx,close)=>{
        /* 头像 + 名字 + 小字 */
        const line=el("div","as-line");
        const avBox=el("div"); avBox.append(avEl({avatar}));
        const bPick=el("button",null,"换一张图");
        const bClear=el("button",null,"去掉");
        line.append(avBox,bPick,bClear);
        bx.append(el("span","lb","头像"),line);
        const nameI=input(bx,"名字","他叫什么",""+(a&&a.name||""));
        const signI=input(bx,"名字下面那行小字","比如：今天也在 / 刚睡醒",""+(a&&a.sign||""));
        /* 系统提示词 */
        bx.append(el("span","lb","系统提示词（这一段会顶掉全局人设里「你是谁」那半截）"));
        const pr=el("textarea"); pr.value=(a&&a.prompt)||"";
        pr.placeholder="你是……。说话短，别客套。";
        bx.append(pr);
        /* MCP */
        bx.append(el("span","lb","他能用的 MCP（★ 分人的：别的助手不受这里影响）"));
        const mcpBox=el("div","as-box");
        const rowAll=el("label","as-chk");
        const ckAll=el("input"); ckAll.type="checkbox";
        rowAll.append(ckAll,el("span",null,"全部（不限 —— 以后新加的 MCP 也给）"));
        mcpBox.append(rowAll);
        const mcpNote=el("div","set-msg");
        const boxes=MCP.map(m=>{
          const l=el("label","as-chk");
          const c=el("input"); c.type="checkbox"; c.dataset.name=m.name;
          l.append(c,el("span",null,m.name));
          l.append(el("span","sp"));
          l.append(el("span","tiny",(m.type==="sse"?"SSE":(m.type==="stdio"?"本机命令":"Streamable HTTP"))
            +(m.enabled?"":" · 关着")+(m.ok?(""):" · 没连上")));
          mcpBox.append(l);
          return {c,m};
        });
        function paintMcp(){
          const all=(mcp===null);
          ckAll.checked=all;
          // ★ 「全部」开着时，下面每一条**画成没勾**：那才是实情 ——「没有单独勾过谁」。
          //   画成勾上的话，人点一下是「取消」，结果存成「一个都不给」，正好反了
          //   （真机上就是这么撞的）。
          boxes.forEach(({c,m})=>{
            c.checked=!all&&(mcp||[]).includes(m.name);
          });
          mcpNote.textContent = all
            ? "现在是不限：所有连上的 MCP 都给。点下面任何一条，就变成「只给勾上的那几个」。"
            : ("只给勾上的这几个" + ((mcp||[]).length?("（"+mcp.length+" 个）"):"（现在一个都没给）"));
        }
        ckAll.onchange=()=>{ mcp=ckAll.checked?null:[]; paintMcp(); };
        boxes.forEach(({c,m})=>{
          c.onchange=()=>{
            // 「全部」开着时点一条 ＝ 从「全部」落成「就这一个」（从空名单开始数）
            const set=new Set(mcp===null?[]:(mcp||[]));
            c.checked?set.add(m.name):set.delete(m.name);
            mcp=[...set];
            paintMcp();
          };
        });
        bx.append(mcpBox,mcpNote);
        if(!MCP.length) bx.append(el("div","set-msg","（还没登记过 MCP —— 上面「MCP 工具包」那一节里加）"));
        paintMcp();
        /* 窗口 */
        bx.append(el("span","lb","挂在他名下的窗口"));
        const wBox=el("div","as-box");
        WINDOWS.forEach(w=>{
          const l=el("label","as-chk");
          const c=el("input"); c.type="checkbox"; c.dataset.sid=w.sid;
          c.checked=(a&&(a.windows||[]).includes(w.sid))||false;
          const nm=el("span",null,w.title||w.sid);
          const tiny=el("span","tiny",w.sid==="main"?"主窗口":w.sid);
          l.append(c,nm,el("span","sp"),tiny);
          wBox.append(l);
        });
        if(!WINDOWS.length) wBox.append(el("div","set-msg","（还没有别的窗口）"));
        bx.append(wBox);
        bx.append(el("div","set-msg","没勾的窗口算第一位的。一个窗口只能属于一位。"));
        /* 信 */
        bx.append(el("span","lb","他写的信"));
        const mailBox=el("div","as-box");
        const bWrite=el("button",null,"替他写一封");
        bx.append(mailBox);
        const mailRow=el("div","set-btns"); mailRow.append(bWrite);
        bx.append(mailRow);
        async function loadMail(){
          mailBox.innerHTML="";
          if(isNew){ mailBox.append(el("div","set-msg","（先把他建出来，信才有地方放）")); return; }
          try{
            const j=await jget("/api/letters?who="+encodeURIComponent(a.id));
            const its=j.items||[];
            if(!its.length){ mailBox.append(el("div","set-msg","（他还没写过信）")); return; }
            its.forEach(m=>{
              const d=el("div","as-mail");
              const hd=el("div","hd");
              hd.append(el("span",null,m.day||""));
              hd.append(el("span","sp"));
              const bd=el("button",null,"删");
              bd.style.cssText="color:var(--err);font-size:11.5px";
              bd.onclick=async()=>{
                if(!confirm("删掉这封信？"))return;
                const r=await jpost("/api/letters/"+m.id+"/del",{});
                if(r.ok){ say("删了"); loadMail(); } else say("删不掉");
              };
              hd.append(bd);
              d.append(hd,el("div","tx",m.content||""));
              mailBox.append(d);
            });
          }catch(e){ mailBox.append(el("div","set-msg","读不到："+e.message)); }
        }
        bWrite.onclick=()=>{
          const wrap=sheet("替他写一封",(bx2,close2)=>{
            const t=el("textarea"); t.placeholder="以他的口吻写……";
            const row2=el("div","set-btns");
            const ok=el("button","pri","放进信箱"), no=el("button",null,"取消");
            row2.append(ok,no); bx2.append(t,row2);
            no.onclick=close2;
            ok.onclick=async()=>{
              const c=t.value.trim();
              if(!c){ say("空的信寄不出去"); return; }
              const r=await jpost("/api/letters",{content:c,who:a.id});
              if(r.ok){ say("放进信箱了"); close2(); loadMail(); }
              else say("没寄出去："+(r.err||"?"));
            };
          });
        };
        loadMail();
        /* 按钮 */
        const foot=el("div","set-btns");
        const bSave=el("button","pri","存下"), bCancel=el("button",null,"取消");
        foot.append(bSave,bCancel);
        const status=el("div","set-msg");
        bx.append(foot,status);
        bCancel.onclick=close;
        bPick.onclick=()=>{
          const inp=el("input"); inp.type="file"; inp.accept="image/*"; inp.hidden=true;
          document.body.append(inp);
          inp.addEventListener("change",()=>{
            const f=(inp.files||[])[0]; inp.remove();
            if(!f)return;
            status.className="set-msg"; status.textContent="压一下、传上去…";
            shrink(f,async du=>{
              if(!du){ status.className="set-msg err"; status.textContent="这张图读不出来"; return; }
              const up=await jpost("/api/upload",{dataURL:du});
              if(!up||!up.url){ status.className="set-msg err"; status.textContent="没传上去："+((up&&up.err)||"网络？"); return; }
              avatar=up.url;
              avBox.innerHTML=""; avBox.append(avEl({avatar}));
              status.className="set-msg ok"; status.textContent="头像换好了（还没存）";
            });
          });
          inp.click();
        };
        bClear.onclick=()=>{ avatar=""; avBox.innerHTML=""; avBox.append(avEl({avatar})); };
        bSave.onclick=async()=>{
          const wins=[...wBox.querySelectorAll("input[data-sid]")].filter(c=>c.checked).map(c=>c.dataset.sid);
          const body={name:nameI.value.trim()||"新的助手",sign:signI.value.trim(),
                      avatar:avatar,prompt:pr.value,
                      mcp:(mcp===null?"all":mcp)};
          if(!isNew)body.id=a.id;
          bSave.disabled=true;
          const r=await jpost("/api/assistants/save",body);
          bSave.disabled=false;
          if(!r.ok){ status.className="set-msg err"; status.textContent="没存上："+(r.err||"?"); return; }
          const id=r.item.id;
          for(const w of WINDOWS){
            const want=wins.includes(w.sid);
            const has=w.assistant===id;
            if(want!==has) await jpost("/api/assistants/window",{sid:w.sid,id:want?id:""});
          }
          say("存好了"); close(); load(); peekBadge();
        };
      });
    }
    load();
  };

  /* ══════════ 聊天顶栏那颗身份牌 ══════════ */
  let curAsst=null, curSid=null, badge=null;
  /* 设置那边改完，顶栏那颗牌子要立刻跟上（不然得等切窗口才变） */
  const peekBadge=()=>{ try{ window.nestAssistantBadge.reload(true); }catch(e){} };
  function mountBadge(){
    const bar=$("#bar"); if(!bar||badge)return;
    badge=el("button",""); badge.id="nestAsstBadge"; badge.hidden=true;
    badge.onclick=()=>{
      if(!curAsst)return;
      sheet("这个窗口是谁在说话",(bx,close)=>{
        const line=el("div","as-line");
        line.append(avEl(curAsst,true));
        const mid=el("div","as-mid");
        mid.append(el("b",null,curAsst.name||"（没名字）"));
        mid.append(el("div","sg",curAsst.sign||""));
        line.append(mid);
        bx.append(line);
        const w=curAsst.windows||[];
        bx.append(el("div","set-msg",w.length
          ? ("挂在他名下的窗口："+w.map(x=>x==="main"?"主窗口":x).join("、"))
          : "（没有单独挂着窗口 —— 没挂过的窗口都算第一位的）"));
        bx.append(el("div","set-msg",curAsst.prompt
          ? "他有自己的系统提示词。" : "他没写自己的系统提示词，用的是全局那份。"));
        bx.append(el("div","set-msg",curAsst.mcp===null
          ? "MCP：不限（所有连上的都给）"
          : (curAsst.mcp&&curAsst.mcp.length?("MCP："+curAsst.mcp.join("、")):"MCP：一个都没给")));
        const row=el("div","set-btns");
        const bGo=el("button","pri","去助手管理");
        bGo.onclick=()=>{ close(); if(window.nestOpenAsstManager)window.nestOpenAsstManager(); };
        row.append(bGo);
        bx.append(row);
      });
    };
    const sp=bar.querySelector(".sp");
    if(sp)bar.insertBefore(badge,sp); else bar.append(badge);
  }
  async function loadBadge(force){
    mountBadge(); if(!badge)return;
    const sid=gSid();
    if(!force&&sid===curSid&&curAsst!==null)return;
    curSid=sid;
    try{
      const j=await jget("/api/assistants/who?sid="+encodeURIComponent(sid));
      curAsst=j.enabled?j.assistant:null;
    }catch(e){
      curAsst=null;                   // 读不到就**不显示** —— 宁可没有，也不报一个假身份
    }
    if(!curAsst){ badge.hidden=true; return; }
    badge.hidden=false;
    badge.innerHTML="";
    badge.append(avEl(curAsst));
    badge.append(el("span","nm",curAsst.name||"助手"));
    badge.title=(curAsst.name||"助手")+(curAsst.sign?(" · "+curAsst.sign):"")
      +"\n点一下看他是谁 / 他名下的窗口";
  }
  window.nestOpenAsstManager=function(){
    const t=document.querySelector('#tabs button[data-tab="setting"]');
    if(t)t.click();
    setTimeout(()=>{
      const s=document.getElementById("as-sec");
      if(s&&s.scrollIntoView)s.scrollIntoView({block:"start"});
    },400);
  };
  mountBadge();
  document.addEventListener("click",e=>{
    const b=e.target&&e.target.closest&&e.target.closest("#tabs button");
    if(b&&(b.dataset.tab||"chat")!=="setting")loadBadge(true);
  },true);
  setInterval(()=>{ if(gSid()!==curSid)loadBadge(); },900);
  setInterval(()=>{
    if(document.visibilityState!=="visible")return;
    if(document.querySelector("#pane .pb"))return;      // 在设置那一栏就别打扰
    loadBadge(true);
  },10000);
  const app=$("#app");
  if(app){
    new MutationObserver(()=>{ if(!app.hidden)loadBadge(); })
      .observe(app,{attributes:true,attributeFilter:["hidden"]});
  }
  loadBadge();
  window.nestAssistantBadge={reload:loadBadge};
}catch(e){console.error("nest-assistant:",e);}
})();
