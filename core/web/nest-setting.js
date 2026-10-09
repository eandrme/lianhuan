/* ══════════════════════════════════════════════════════════
   巢 · 设置 ⑦：大模型引擎 · 主动消息总闸 · 离线时段 · 推送
   装法：nest.html 里，nest-window.js 那行【下面】再加一行
        <script src="/nest-setting.js?v=1"></script>

   后端全是现成的，一个字没新增（除了给 push/status 补一个 ntfy 字段）：
     /api/engine/config   GET 看现在接的 + 预设    POST 存（顺便切换引擎）
     /api/engine/models   POST 认一下这家有哪些模型（带临时 base/key 就不落盘）
     /api/whisper_freq    GET/POST 「耳语频率」总闸（主动消息的总开关）
     /api/offline         GET 离线时段状态（总闸在 .env 的 OFFLINE_ENABLED）
     /api/push/status · /api/push/test

   ★ 为什么非要有这一页：这一版之前，巢里**根本没法挑引擎** —— 设置那格写着
     「下一批接上」。于是引擎一直是出厂的回声（界面显示「未接模型」），
     而那两枚窗口开关的总闸（耳语频率）也没处可调。
   ══════════════════════════════════════════════════════════ */
(function(){
"use strict";
try{
  window.NEST_PANES=window.NEST_PANES||{};
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
      return {ok:false,status:r.status,err:(d&&(d.error||d.err))||("HTTP "+r.status),raw:d||{}};
    return d;
  };

  const css=document.createElement("style");
  css.textContent=`
.set-sec{border:1px solid var(--line);background:var(--panel);border-radius:var(--r);
  padding:12px;margin-bottom:11px}
.set-sec h4{margin:0 0 4px;font-size:14.5px}
.set-sec .sub{font-size:11.5px;color:var(--dim2);line-height:1.6;margin-bottom:9px}
.set-row{display:flex;gap:7px;align-items:center;flex-wrap:wrap}
.set-row .sp{flex:1}
.set-chips{display:flex;gap:5px;flex-wrap:wrap;margin-bottom:8px}
.set-chips button{padding:5px 10px;border-radius:16px;border:1px solid var(--line);
  background:var(--panel2);font-size:12.5px;color:var(--dim);max-width:100%;
  overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.set-chips button.on{border-color:var(--accent);color:var(--accent)}
.set-chips button.cur{border-color:var(--ok);color:var(--ok)}
.set-in{flex:1;min-width:120px;box-sizing:border-box;padding:9px 11px;border-radius:9px;
  border:1px solid var(--line);background:var(--panel2);color:var(--fg);font:inherit;outline:none}
.set-in.full{width:100%;flex:none;margin-top:7px}
.set-btns{display:flex;gap:7px;margin-top:9px;flex-wrap:wrap}
.set-btns button{padding:9px 13px;border-radius:9px;border:1px solid var(--line);
  background:var(--panel2);color:var(--fg);font:inherit;font-size:13.5px}
.set-btns button.pri{background:var(--accent);color:var(--nest-me-fg,#10131a);
  border-color:transparent;font-weight:600}
.set-btns button:disabled{opacity:.5}
.set-msg{font-size:12.5px;color:var(--dim);margin-top:8px;line-height:1.65;white-space:pre-wrap}
.set-msg.err{color:var(--err)}
.set-msg.ok{color:var(--ok)}
.set-now{font-size:13px;margin-bottom:8px}
.set-now b{color:var(--ok)}
.set-slide{display:flex;align-items:center;gap:9px}
.set-slide input[type=range]{flex:1;accent-color:var(--accent)}
.set-slide .v{flex:0 0 34px;text-align:right;font-family:var(--mono);color:var(--dim)}
.set-list{max-height:210px;overflow:auto;margin-top:8px}
.set-kv{font-size:12.5px;color:var(--dim);line-height:1.9}
.set-kv b{color:var(--fg);font-weight:600}
`;
  document.head.append(css);

  const ENGNAME={echo:"回声（还没接模型）",api:"OpenAI 兼容",anthropic:"Claude",
                 cli:"本机 CLI"};

  window.NEST_PANES.setting=function(box){
    box.innerHTML="";
    secEngine(box);
    secWhisper(box);
    secOffline(box);
    secPush(box);
  };

  /* ═══ 大模型引擎 ═══ */
  async function secEngine(box){
    const sec=el("div","set-sec");
    sec.append(el("h4",null,"大模型引擎"));
    sec.append(el("div","sub","出厂是回声（它老实说自己没接模型）。挑一家、贴 key、"
      +"「连接并识别模型」——认出来之后点一个模型名就存下并切换过去。"
      +"key 只写进这台服务器的 data/secrets.json，界面不回读明文。"));
    const now=el("div","set-now","现在接的：读着…");
    sec.append(now);
    const prot=el("div","set-chips");
    const pre=el("div","set-chips");
    const baseI=el("input","set-in"); baseI.type="text"; baseI.placeholder="接口地址，比如 https://api.deepseek.com";
    const modelI=el("input","set-in full"); modelI.type="text"; modelI.placeholder="模型名，比如 deepseek-chat";
    const keyI=el("input","set-in full"); keyI.type="password"; keyI.placeholder="key（留空＝用已经存着的那把）";
    const btns=el("div","set-btns");
    const bProbe=el("button",null,"连接并识别模型");
    const bSave=el("button","pri","就存这些");
    btns.append(bProbe,bSave);
    const msg=el("div","set-msg");
    const list=el("div","set-list");
    sec.append(prot,pre,baseI,modelI,keyI,btns,msg,list);
    box.append(sec);

    let proto="api";
    let cfg={};
    const paintProto=()=>{
      prot.innerHTML="";
      [["api","OpenAI 兼容（大多数家）"],["anthropic","Claude 官方"]].forEach(p=>{
        const b=el("button",(proto===p[0]?"on":""),p[1]);
        b.onclick=()=>{ proto=p[0]; paintProto(); list.innerHTML=""; };
        prot.append(b);
      });
    };
    paintProto();

    function showNow(){
      const e=cfg.engine||"echo";
      now.innerHTML="";
      now.append(el("span",null,"现在接的："));
      now.append(el("b",null,ENGNAME[e]||e));
      now.append(el("span",null,(cfg.model?(" · "+cfg.model):"")
        +(cfg.key_set?(" · key…"+cfg.key_tail):" · 还没 key")));
    }

    async function loadCfg(){
      try{
        cfg=await jget("/api/engine/config");
      }catch(e){
        msg.textContent="读不到引擎配置："+e.message+"（服务端太旧就得重启一下）";
        msg.className="set-msg err";
        return;
      }
      if(!baseI.value)baseI.value=cfg.base||"";
      if(!modelI.value)modelI.value=cfg.model||"";
      proto=(cfg.engine==="anthropic")?"anthropic":"api";
      paintProto();
      showNow();
      pre.innerHTML="";
      (cfg.presets||[]).forEach(p=>{
        const b=el("button",null,p.name);
        b.title=p.base+" · "+p.model;
        b.onclick=()=>{
          baseI.value=p.base; modelI.value=p.model;
          if(p.engine){ proto=p.engine; paintProto(); }
          list.innerHTML=""; msg.textContent="";
        };
        pre.append(b);
      });
    }

    bProbe.onclick=async()=>{
      bProbe.disabled=true;
      msg.className="set-msg"; msg.textContent="问一下这家有哪些模型…";
      list.innerHTML="";
      const d=await jpost("/api/engine/models",
        {engine:proto,base:baseI.value.trim(),model:modelI.value.trim(),key:keyI.value});
      bProbe.disabled=false;
      if(!d.ok){
        msg.className="set-msg err";
        msg.textContent="没认出来："+(d.err||"?")
          +"\n（地址对不对、key 对不对、这台服务器能不能连出去 —— 这三样挨个看）";
        return;
      }
      const ms=d.models||[];
      if(!ms.length){
        msg.className="set-msg err";
        msg.textContent="这家没告诉我们有哪些模型。模型名直接手打也行，存之前认不出来不代表用不了。";
        return;
      }
      msg.className="set-msg ok";
      msg.textContent="认出来了 "+ms.length+" 个 —— 点一个就当选用它。";
      ms.forEach(m=>{
        const b=el("button",(m.id===modelI.value.trim()?"cur":""),m.name||m.id);
        b.title=m.id;
        b.onclick=async()=>{
          if(b.disabled)return;
          [...list.querySelectorAll("button")].forEach(x=>x.disabled=true);
          msg.className="set-msg"; msg.textContent="存着…";
          const body={engine:proto,base:baseI.value.trim(),model:m.id};
          if(keyI.value)body.key=keyI.value;
          const r=await jpost("/api/engine/config",body);
          [...list.querySelectorAll("button")].forEach(x=>x.disabled=false);
          if(!r.ok){ msg.className="set-msg err"; msg.textContent="没存上："+(r.err||"?"); return; }
          keyI.value="";
          await loadCfg();
          msg.className="set-msg ok";
          msg.textContent="好了，现在用 "+(m.name||m.id)+" 说话。";
          say("换成 "+(m.name||m.id)+" 了");
          checkNow(sec,msg);
        };
        list.append(b);
      });
    };

    bSave.onclick=async()=>{
      const model=modelI.value.trim();
      if(!model){ msg.className="set-msg err"; msg.textContent="模型名得填一个"; return; }
      bSave.disabled=true;
      const body={engine:proto,base:baseI.value.trim(),model:model};
      if(keyI.value)body.key=keyI.value;
      const r=await jpost("/api/engine/config",body);
      bSave.disabled=false;
      if(!r.ok){ msg.className="set-msg err"; msg.textContent="没存上："+(r.err||"?"); return; }
      keyI.value="";
      await loadCfg();
      msg.className="set-msg ok"; msg.textContent="存下了。";
      if(window.__nestWhisperReload)window.__nestWhisperReload();
      checkNow(sec,msg);
    };

    loadCfg();
  }

  /* 存完顺手真连一次（老路：问当前已保存的引擎）—— 「存了」和「连得上」是两件事 */
  async function checkNow(sec,msg){
    if(sec.querySelector(".set-check"))return;
    const line=el("div","set-msg set-check","再连一次确认…");
    sec.append(line);
    const d=await jpost("/api/engine/models",{});
    if(d.ok){
      line.className="set-msg ok set-check";
      line.textContent="连通了，这家有 "+(d.models||[]).length+" 个模型。";
    }else{
      line.className="set-msg err set-check";
      line.textContent="存下了，但这会儿连不上："+(d.err||"?")
        +"\n（key 或地址不对、或者这台服务器连不出去）—— 聊天里发一句话更能确定。";
    }
  }

  /* ═══ 主动消息总闸：耳语频率 ═══ */
  async function secWhisper(box){
    const sec=el("div","set-sec");
    sec.append(el("h4",null,"主动消息（总闸）"));
    sec.append(el("div","sub","这是**所有窗口**的总闸：0 = 彻底安静（出厂就是 0）。"
      +"拨上去之后，还得那一扇窗的「主动消息」开关也开着，它才会真开口。"
      +"每扇窗的开关在聊天顶栏（🔔）和「对话窗口」列表里。"));
    const row=el("div","set-slide");
    const rng=el("input"); rng.type="range"; rng.min="0"; rng.max="100"; rng.step="5";
    const val=el("div","v","0");
    row.append(rng,val);
    const desc=el("div","set-msg","读着…");
    const stubNote=el("div","set-msg");
    sec.append(row,desc,stubNote);
    box.append(sec);

    /* ★ 换算必须跟后端**一模一样**：公式在 core/proactive.daily_max ——
       `int(round(lv / 100 * 9))`。Python 的 round 是「四舍六入五取偶」，
       JS 的 Math.round 是「.5 一律进位」—— 50 的时候两边差一句（4 vs 5）。
       老界面（index.html）用的是 Math.round，也就是在 50 这个点上说的比真的多一句；
       这一页不跟它一起错。 */
    const cap=lv=>{
      const x=lv/100*9, f=Math.floor(x), d=x-f;
      if(d>0.5)return f+1;
      if(d<0.5)return f;
      return (f%2===0)?f:f+1;
    };
    const words=lv=>lv<=0?"彻底安静 —— 它不会主动找你":
      ("一天最多 "+cap(lv)+" 句（两句之间至少隔 90 分钟）");
    async function load(){
      try{
        const d=await jget("/api/whisper_freq");
        rng.value=Number(d.level||0);
        val.textContent=rng.value;
        desc.className="set-msg";
        desc.textContent=words(Number(rng.value))
          +(d.spoken_today!=null?("。今天已经说了 "+d.spoken_today+" 句"):"");
      }catch(e){
        desc.className="set-msg err";
        desc.textContent="读不到："+e.message;
      }
      /* ★ 引擎还是回声那种桩时，滑钮拧到多少它都不会开口 ——
         不说清楚的话，人会以为「拨了没用＝开关是坏的」。 */
      try{
        const c=await jget("/api/engine/config");
        if((c.engine||"echo")==="echo"){
          stubNote.className="set-msg err";
          stubNote.textContent="注意：现在的引擎还是回声（没接模型），它不会主动开口 —— "
            +"上面「大模型引擎」里接上一家，这根滑钮才真的算数。";
        }else stubNote.textContent="";
      }catch(e){ stubNote.textContent=""; }
      /* 引擎换了之后这根滑钮才算数 —— 让 secEngine 存完能叫这一节重画一遍 */
      window.__nestWhisperReload=load;
    }
    let t=0;
    rng.oninput=()=>{
      val.textContent=rng.value;
      desc.textContent=words(Number(rng.value))+"（松手就存）";
      clearTimeout(t);
      t=setTimeout(async()=>{
        const d=await jpost("/api/whisper_freq",{level:Number(rng.value)});
        if(d.ok){ desc.className="set-msg ok"; desc.textContent=words(Number(rng.value))+" —— 存下了"; }
        else{ desc.className="set-msg err"; desc.textContent="没存上："+(d.err||"?"); }
      },450);
    };
    load();
  }

  /* ═══ 离线自由时段 ═══ */
  async function secOffline(box){
    const sec=el("div","set-sec");
    sec.append(el("h4",null,"离线自由时段"));
    sec.append(el("div","sub","它自己的一段时间（你久不在的时候）。"
      +"**服务端总闸在 .env 的 OFFLINE_ENABLED**，这一页只能看状态、不能在这儿拨 —— "
      +"哪扇窗允许它有这段时间，用聊天顶栏那枚 🌙。"));
    const kv=el("div","set-kv","读着…");
    sec.append(kv);
    box.append(sec);
    try{
      const d=await jget("/api/offline");
      kv.innerHTML="";
      kv.append(el("div",null,"服务端总闸："+(d.enabled?"开着":"关着（OFFLINE_ENABLED 没开）")));
      kv.append(el("div",null,"现在："+(d.active?"它正在自己的时间里"
        :(d.last?("上一场 "+new Date(d.last*1000).toLocaleString()):"还没跑过"))));
      kv.append(el("div",null,"你现在这扇窗："+(d.active_window||"main")
        +"（这扇的离线模式 "+(d.window_ok?"开着":"关着")+"）"));
      if(d.engine_ok===false)
        kv.append(el("div",null,"引擎还是回声那种桩，这段时间不会跑 —— 先在上面把引擎接上"));
    }catch(e){
      kv.textContent="读不到："+e.message;
    }
  }

  /* ═══ 推送到手机 ═══ */
  async function secPush(box){
    const sec=el("div","set-sec");
    sec.append(el("h4",null,"推送到手机"));
    sec.append(el("div","sub","他主动说话 / 有事的时候弹到你锁屏上。"
      +"iPhone 要先「添加到主屏幕」再从主屏图标打开，站点还得是 HTTPS（本机除外）。"));
    const kv=el("div","set-kv","读着…");
    const btns=el("div","set-btns");
    const bTest=el("button","pri","推一条试试");
    btns.append(bTest);
    const msg=el("div","set-msg");
    sec.append(kv,btns,msg);
    box.append(sec);

    async function load(){
      try{
        const d=await jget("/api/push/status");
        kv.innerHTML="";
        kv.append(el("div",null,"网页推送订阅："
          +((d.subs!=null?d.subs:0)+" 个端")));
        if(d.ntfy)kv.append(el("div",null,"ntfy 也配着（会同时发一份到你的 ntfy 主题）"));
      }catch(e){ kv.textContent="读不到："+e.message; }
    }
    bTest.onclick=async()=>{
      bTest.disabled=true;
      msg.className="set-msg"; msg.textContent="发着…";
      const d=await jpost("/api/push/test",{});
      bTest.disabled=false;
      if(!d.ok && d.sent==null){
        msg.className="set-msg err"; msg.textContent="没发出去："+(d.err||"?"); return;
      }
      msg.className="set-msg ok";
      msg.textContent="网页推送发出 "+(d.sent||0)+" 条"
        +(d.ntfy?"（ntfy 那份也一起发了）":"")+"。一条没收到的话看上面那两行："
        +"没有订阅端就先在手机浏览器里把这一页「添加到主屏幕」再开通知。";
    };
    load();
  }
}catch(e){console.error("nest-setting:",e);}
})();
