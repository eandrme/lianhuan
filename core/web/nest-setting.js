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
/* MCP 总管理 */
.mcp-list{max-height:none}
.mcp-row{border:1px solid var(--line);border-radius:var(--r-sm);padding:9px 11px;
  margin-bottom:8px;background:var(--panel2)}
.mcp-hd{display:flex;align-items:center;gap:7px}
.mcp-hd b{font-size:14px}
.mcp-hd .sp{flex:1}
.mcp-tag{font-size:11px;color:var(--dim2);border:1px solid var(--line);border-radius:6px;
  padding:1px 6px;white-space:nowrap}
.mcp-sw{font-size:11.5px;border:1px solid var(--line);border-radius:999px;padding:2px 9px;
  color:var(--dim2);white-space:nowrap}
.mcp-sw.on{color:var(--ok);border-color:var(--ok)}
.mcp-url{font:12px/1.5 var(--mono);color:var(--dim);word-break:break-all;margin:5px 0 3px}
.mcp-meta{display:flex;flex-wrap:wrap;gap:4px 10px;font-size:11.5px;color:var(--dim2)}
.mcp-st.ok{color:var(--ok)}
.mcp-st.bad{color:var(--err)}
.mcp-st.dim{color:var(--dim2)}
.mcp-h{word-break:break-all}
.mcp-hds{margin-top:4px}
.mcp-hdrow{display:flex;gap:6px;margin-top:6px;align-items:center}
.mcp-hdrow .set-in{min-width:0}
.mcp-hdrow button{flex:0 0 auto;color:var(--err);border:1px solid var(--line);
  border-radius:7px;padding:6px 10px}
`;
  document.head.append(css);

  const ENGNAME={echo:"回声（还没接模型）",api:"OpenAI 兼容",anthropic:"Claude",
                 cli:"本机 CLI"};

  window.NEST_PANES.setting=function(box){
    box.innerHTML="";
    secEngine(box);
    secThink(box);
    secMcp(box);
    /* 助手管理（nest-assistant.js）—— 它不在就跳过，这一节别把整页带塌 */
    if(typeof window.nestAssistantSection==="function"){
      try{ window.nestAssistantSection(box); }
      catch(e){ console.error("nest-assistant section:",e); }
    }
    secWhisper(box);
    secOffline(box);
    secPush(box);
  };

  /* ═══ MCP 工具包（总管理）═══
     三种连接方式（后端 core/mcp_client.py 都实现了，一个字没新增）：
       · Streamable HTTP —— 一个端点，POST JSON-RPC，回包可能是 JSON 也可能是 SSE 流
       · SSE（老的 HTTP+SSE）—— GET 一条流，第一个事件给出 message 端点（就是「短链」）
       · 本机命令（stdio）—— 起子进程。★ 只能在**本机页面**加：它是起进程，
         跟 /api/mcp/add 同一条线（见 gate.LOCAL_ONLY）。
     请求头随便加：Bearer token、自定义 UA……存进 data/mcp.json（0600），
     界面只回显**名字和末四位** —— 明文不回读。 */
  async function secMcp(box){
    const sec=el("div","set-sec"); sec.id="mcp-sec";
    sec.append(el("h4",null,"MCP 工具包"));
    sec.append(el("div","sub","给它的手。手机上加 MCP 用 Streamable HTTP 或 SSE 那种地址；"
      +"「本机命令」会在这台机器上起进程，只能在本机页面加。"
      +"请求头里放 token 也没关系 —— 只写进 data/mcp.json（0600），界面只回名字和末四位。"));
    const btns=el("div","set-btns");
    const bAdd=el("button","pri","＋ 加一个");
    btns.append(bAdd);
    const msg=el("div","set-msg");
    const list=el("div","set-list mcp-list");
    sec.append(btns,msg,list);
    box.append(sec);

    let LOCAL=false, SERVERS=[];
    const KIND_NAME={http:"Streamable HTTP",sse:"SSE",stdio:"本机命令"};

    async function load(){
      list.innerHTML=""; list.append(el("div","set-msg","读着…"));
      let j;
      try{ j=await jget("/api/mcp"); }
      catch(e){
        list.innerHTML="";
        msg.className="set-msg err";
        msg.textContent="读不到（"+e.message+"）—— 服务端太旧就得先重启一下";
        return;
      }
      SERVERS=Array.isArray(j)?j:(j.servers||[]);
      LOCAL=!!j.local;
      draw();
    }

    function draw(){
      list.innerHTML="";
      if(!SERVERS.length){
        list.append(el("div","set-msg","还没登记过。点「＋ 加一个」，把地址粘进来就行。"));
        return;
      }
      SERVERS.forEach(s=>{
        const row=el("div","mcp-row");
        const head=el("div","mcp-hd");
        head.append(el("b",null,s.name));
        head.append(el("span","mcp-tag",KIND_NAME[s.type]||s.type));
        head.append(el("span","sp"));
        const sw=el("button",(s.enabled?"mcp-sw on":"mcp-sw"),s.enabled?"开":"关");
        sw.title=s.enabled?"正拿在它手里（点一下关掉，工具一起收走）":"关着（点一下连上）";
        sw.onclick=async()=>{
          const r=await jpost("/api/mcp/toggle",{name:s.name,enabled:!s.enabled});
          if(r.ok){ say(s.name+(s.enabled?" 关了":" 开了")); load(); }
          else{ msg.className="set-msg err"; msg.textContent="没拨成："+(r.err||"?"); }
        };
        head.append(sw);
        row.append(head);
        row.append(el("div","mcp-url",s.url||s.command||""));

        const meta=el("div","mcp-meta");
        if(s.header_names&&s.header_names.length){
          meta.append(el("span","mcp-h",
            "请求头："+s.header_names.map(n=>n+(s.headers_masked&&s.headers_masked[n]
              ?" "+(s.headers_masked[n]):"")).join(" · ")));
        }
        if(!s.enabled) meta.append(el("span","mcp-st dim","没连（关着）"));
        else if(s.ok) meta.append(el("span","mcp-st ok",(s.tools||[]).length+" 个工具："
          +(s.tools||[]).slice(0,4).join("、")+((s.tools||[]).length>4?"…":"")));
        else meta.append(el("span","mcp-st bad","没连上"+(s.err?("："+s.err):"")));
        row.append(meta);

        const ops=el("div","set-btns");
        const bTest=el("button",null,"测一下");
        bTest.onclick=async()=>{
          bTest.disabled=true; bTest.textContent="连…";
          const r=await jpost("/api/mcp/probe",{kind:s.type,url:s.url,command:s.command});
          bTest.disabled=false; bTest.textContent="测一下";
          if(r.ok) say(s.name+"：连上了，"+(r.tools||[]).length+" 个工具");
          else{
            msg.className="set-msg err";
            msg.textContent=s.name+" 没连上："+(r.err||r.error||"?");
          }
        };
        const bEdit=el("button",null,"改");
        bEdit.onclick=()=>edit(s);
        const bDel=el("button",null,"删");
        bDel.onclick=async()=>{
          if(!confirm("删掉「"+s.name+"」？它会立刻断掉，工具也从它手里收走。"))return;
          const r=await jpost("/api/mcp/save",{name:s.name,kind:s.type,remove:true});
          if(r.ok){ say("删了"); load(); }
          else{
            if(r.status===403){ msg.className="set-msg err"; msg.textContent=r.err; return; }
            msg.className="set-msg err"; msg.textContent="删不掉："+(r.err||"?");
          }
        };
        ops.append(bTest,bEdit,bDel);
        row.append(ops);
        list.append(row);
      });
    }

    bAdd.onclick=()=>edit(null);
    load();

    /* ── 加 / 改：一张表单 ── */
    function edit(s){
      const isNew=!s;
      const cur=s||{type:"http",url:"",command:"",name:"",header_names:[]};
      let kind=cur.type||"http";
      sheetEl(isNew?"加一个 MCP":"改「"+cur.name+"」", (bx,close)=>{
        const nameI=el("input","set-in full"); nameI.type="text";
        nameI.placeholder="名字：字母数字 _-（会变成工具名前缀）"; nameI.value=cur.name||"";
        if(!isNew) nameI.value=cur.name||"";
        const kindBox=el("div","set-chips");
        const urlI=el("input","set-in full"); urlI.type="text";
        const cmdI=el("input","set-in full"); cmdI.type="text";
        cmdI.placeholder="本机命令，比如 npx -y @modelcontextprotocol/server-filesystem /tmp";
        const hint=el("div","set-msg");
        const hdWrap=el("div");
        const hdHead=el("div","set-msg","自定义请求头（Bearer token 那种。值留空＝不改已经存着的那把）");
        const hdList=el("div","mcp-hds");
        const bHdAdd=el("button",null,"＋ 加一行");
        hdWrap.append(hdHead,hdList,bHdAdd);
        const status=el("div","set-msg");
        const row=el("div","set-btns");
        const bProbe=el("button",null,"测试连接");
        const bSave=el("button","pri","存下来");
        const bCancel=el("button",null,"取消");
        row.append(bProbe,bSave,bCancel);
        bx.append(el("div","set-msg","名字"),nameI,kindBox,
                  el("div","set-msg","地址 / 命令"),urlI,cmdI,
                  hint,hdWrap,row,status);
        urlI.placeholder="地址：https://example.com/mcp（Streamable HTTP）或 …/sse（SSE）";

        function headerRow(n,v){
          const r=el("div","mcp-hdrow");
          const ni=el("input","set-in"); ni.type="text"; ni.placeholder="名字，比如 Authorization";
          const vi=el("input","set-in"); vi.type="text";
          vi.placeholder="值，比如 Bearer xxx（留空＝不改）";
          ni.value=n||""; vi.value=v||"";
          const x=el("button",null,"✕"); x.title="删掉这一行";
          x.onclick=()=>r.remove();
          r.append(ni,vi,x);
          hdList.append(r);
          return r;
        }
        (cur.header_names||[]).forEach(n=>headerRow(n,""));

        function paintKind(){
          kindBox.innerHTML="";
          [["http","Streamable HTTP"],["sse","SSE"],["stdio","本机命令"]].forEach(p=>{
            const b=el("button",(kind===p[0]?"on":""),p[1]);
            if(p[0]==="stdio"&&!LOCAL) b.title="只能在本机页面加（它会起进程）";
            b.onclick=()=>{ 
              if(p[0]==="stdio"&&!LOCAL){
                status.className="set-msg err";
                status.textContent="「本机命令」只能在这台机器上用本机页面加 —— 它会起进程。"
                  +"手机上想加 MCP，用 Streamable HTTP 或 SSE 那种地址。";
                return;
              }
              kind=p[0]; paintKind();
            };
            kindBox.append(b);
          });
          const std=(kind==="stdio");
          urlI.hidden=std; cmdI.hidden=!std; hdWrap.hidden=std;
          hint.className="set-msg";
          hint.textContent = std
            ? "本机命令：在这台机器上起一个进程（用户自己贴的命令，等于自己运行程序）。"
            : (kind==="sse"
                ? "SSE（老的 HTTP+SSE）：粘那条 **/sse** 短链。它 GET 一条流，"
                  +"第一个事件会把真正的 message 端点告诉你，之后的请求都发到那儿。"
                : "Streamable HTTP：粘那一个端点（一般长这样 …/mcp）。POST JSON-RPC，"
                  +"回包可能是 JSON，也可能是一条 SSE 流，两种都认。");
        }
        paintKind();

        const payload=()=>({
          name:nameI.value.trim(),
          old_name:(isNew?undefined:(cur.name||"")),
          kind:kind,
          url:urlI.value.trim(),
          command:cmdI.value.trim(),
          headers:[...hdList.querySelectorAll(".mcp-hdrow")].map(r=>({
            name:r.children[0].value.trim(), value:r.children[1].value.trim()})),
        });

        bHdAdd.onclick=()=>headerRow("","");
        bCancel.onclick=close;
        bProbe.onclick=async()=>{
          const p=payload();
          if(!p.name){ status.className="set-msg err"; status.textContent="先起个名字"; return; }
          bProbe.disabled=true; bProbe.textContent="连着…";
          status.className="set-msg"; status.textContent="拿这份还没保存的配置试连一次…";
          const r=await jpost("/api/mcp/probe",p);
          bProbe.disabled=false; bProbe.textContent="测试连接";
          if(r.ok){
            status.className="set-msg ok";
            status.textContent="连上了 —— 它认到 "+(r.tools||[]).length+" 个工具"
              +((r.tools||[]).length?("："+r.tools.slice(0,6).join("、")
                +(r.tools.length>6?"…":"")):"（一个都没报，可能是它那边没开 tools）");
          }else{
            status.className="set-msg err";
            status.textContent="没连上："+(r.err||r.error||"?");
          }
        };
        bSave.onclick=async()=>{
          const p=payload();
          if(!p.name){ status.className="set-msg err"; status.textContent="先起个名字"; return; }
          bSave.disabled=true; bSave.textContent="存…";
          const r=await jpost("/api/mcp/save",p);
          bSave.disabled=false; bSave.textContent="存下来";
          if(r.ok&&r.server&&r.server.ok){
            status.className="set-msg ok";
            status.textContent="存下了，也连上了（"+(r.server.tools||[]).length+" 个工具）";
            say("加好了："+p.name);
            close(); load();
            return;
          }
          if(r.ok){
            status.className="set-msg err";
            status.textContent="存下了，但这会儿没连上："
              +((r.server&&r.server.err)||"（原因没报）")
              +" —— 配置留着，改完再点「测试连接」。";
            load();
            return;
          }
          status.className="set-msg err";
          status.textContent="没存上："+(r.err||r.error||"?");
        };
      });
    }
  }

  /* 设置页自己的 sheet（跟 nest-notes 那个同形；这儿不跨模块借） */
  function sheetEl(title,build){
    const wrap=el("div","sheet"), bx=el("div","box nt-sheet");
    const h=el("div","bh"), b=el("b",null,title), x=el("button","x ibtn","✕");
    x.onclick=()=>wrap.remove(); h.append(b,x); bx.append(h); wrap.append(bx);
    wrap.onclick=e=>{if(e.target===wrap)wrap.remove();};
    document.body.append(wrap); build(bx,()=>wrap.remove()); return wrap;
  }

  /* 从别处（顶栏那把 🔧）跳过来：打开设置页并滚到 MCP 那一节 */
  window.nestOpenMcpManager=function(){
    const t=document.querySelector('#tabs button[data-tab="setting"]');
    if(t)t.click();
    setTimeout(()=>{
      const s=document.getElementById("mcp-sec");
      if(s&&s.scrollIntoView)s.scrollIntoView({block:"start"});
    },400);
  };

  /* ═══ 大模型引擎 ═══ */
  async function secEngine(box){
    const sec=el("div","set-sec");
    sec.append(el("h4",null,"大模型引擎"));
    sec.append(el("div","sub","出厂是回声（它老实说自己没接模型）。挑一家、贴 key、"
      +"「连接并识别模型」——认出来之后点一个模型名就存下并切换过去。"
      +"key 只写进这台服务器的 data/secrets.json，界面不回读明文。"));
    const now=el("div","set-now","现在接的：读着…");
    /* ★ 真机上撞的：「每次关掉页面重新打开都要再配置一遍模型」。
       一份配置就存着（key/base/model 都在 secrets.json 里，也能真聊），
       可引擎那个设置停在回声 —— 人一看「现在接的：回声」，只好从头再填一遍。
       这儿给一颗一次性的按钮：拿已经存着的那份直接接上，一个字都不用重打。 */
    const heal=el("div","set-btns"); heal.hidden=true;
    const bHeal=el("button","pri","接上存着的那份配置");
    heal.append(bHeal);
    const healNote=el("div","set-msg");
    sec.append(now,healNote,heal);
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
      // 存着一份完整配置、引擎却停在回声 —— 这是「要重配一遍」的真正由来
      const stranded=(e==="echo" && cfg.key_set && cfg.base && cfg.model);
      heal.hidden=!stranded;
      if(stranded){
        healNote.className="set-msg err";
        healNote.textContent="你存着一份配置（"+cfg.model+" · key…"+cfg.key_tail
          +"），但当前引擎停在回声 —— 点下面那颗接上就行，不用再填一遍。";
      }else{
        healNote.textContent="";
      }
    }

    bHeal.onclick=async()=>{
      const base=(baseI.value.trim()||cfg.base||"");
      const model=(modelI.value.trim()||cfg.model||"");
      if(!base||!model){ msg.className="set-msg err"; msg.textContent="存着的那份缺地址或模型名，还是得先认一遍"; return; }
      bHeal.disabled=true;
      const r=await jpost("/api/engine/config",
        {engine:/anthropic/i.test(base)?"anthropic":"api", base:base, model:model});
      bHeal.disabled=false;
      if(!r.ok){ msg.className="set-msg err"; msg.textContent="没接上："+(r.err||"?"); return; }
      await loadCfg();
      msg.className="set-msg ok"; msg.textContent="接上了 —— 现在说话的就是这家。";
      if(window.__nestWhisperReload)window.__nestWhisperReload();
      checkNow(sec,msg);
    };

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

  /* ═══ 想多深（深度思考）═══ */
  async function secThink(box){
    const sec=el("div","set-sec");
    sec.append(el("h4",null,"想多深（深度思考）"));
    sec.append(el("div","sub","聊天输入框旁边那枚 🧠 就是它：点一下＝**开（多想一层）/ 关（别想）**。"
      +"这里另外两档也在：「偏快」（少想一点）和「自动」（由这家自己定 —— 它可能默认想得很深）。"
      +"★ 关是真的关：会给这家发 reasoning_effort=none；Claude / 本机 CLI 那两条不吃这个参数，"
      +"那一档在它们那儿只改提示词（下面那行小字会说）。"));
    const chips=el("div","set-chips");
    const note=el("div","set-msg","读着…");
    sec.append(chips,note);
    box.append(sec);
    let cur="auto";
    const NAMES={off:"别想（关）",fast:"偏快",auto:"自动",deep:"偏深（开）"};
    function paint(){
      chips.innerHTML="";
      ["off","fast","auto","deep"].forEach(k=>{
        const b=el("button",(k===cur?"on":""),NAMES[k]);
        b.onclick=()=>set(k);
        chips.append(b);
      });
    }
    async function load(){
      try{
        const j=await jget("/api/think");
        cur=j.mode||"auto";
        paint();
        note.className="set-msg";
        note.textContent="现在是「"+(j.labels&&j.labels[cur]||NAMES[cur])+"」—— "
          +((j.notes&&j.notes[cur])||"")
          +"\n落到两处：一句话进 system（哪家引擎都吃得到）"
          +((j.effort)?("；还会给这家标 reasoning_effort="+j.effort):"（这一档什么都不标）")
          +"。\n现在这家："+(j.engine_note||"（取决于引擎）")
          +((cur==="off"&&j.can_mute===false)
              ?("\n⚠ 这条路上「关」关不掉它的思考（它不吃那个参数）—— 思考过程还会出现。"):"");
      }catch(e){
        note.className="set-msg err";
        note.textContent="读不到："+e.message;
      }
    }
    async function set(k){
      const before=cur; cur=k; paint();
      const r=await jpost("/api/think",{mode:k});
      if(!r.ok){ cur=before; paint(); note.className="set-msg err"; note.textContent="没换成："+(r.err||"?"); return; }
      say("想多深：换成「"+NAMES[k]+"」了");
      load();
    }
    load();
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
