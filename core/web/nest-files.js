/* ══════════════════════════════════════════════════════════
   巢 · 附件 v1：发图片 / 发文件
   装法：nest.html 里最后再加一行
        <script src="/nest-files.js?v=1"></script>
   后端零新增：走 /api/upload（图）和 /api/upload_file（文件）——
   旧界面就在用同一套，没另起一份。

   ★ 设计上跟旧界面一致的三件事（都是踩出来的，别改）：
     1. 挑完**先不发**，停在输入框上头等着配一句话。选好就直接发出去，
        人会来不及反悔，也配不上话。
     2. 图片发之前先压小。手机原图好几兆，不压要等半天。
     3. 有一样没送上去就**整批不发**，暂存原样留着 —— 半批发出去，
        你不知道少了哪一张，比不发更糟。
   ══════════════════════════════════════════════════════════ */
(function(){
"use strict";
try{
  const el=(t,c,x)=>{const e=document.createElement(t);if(c)e.className=c;if(x!=null)e.textContent=x;return e;};
  const say=t=>{try{if(typeof toast==="function")toast(t);}catch(e){}};
  const $=(s,r=document)=>r.querySelector(s);

  const MAXN = 9;                          // 一次最多九样，再多自己也说不清
  const MAXFILE = 25 * 1024 * 1024;        // 跟后端 /api/upload_file 的上限对齐
  const IMG_MAX = 1600;                    // 压到长边 1600
  const IMG_Q = 0.88;

  const css=document.createElement("style");
  css.textContent=`
#attBar{display:flex;gap:7px;flex-wrap:wrap;padding:0 0 8px;
  max-width:var(--colw);margin:0 auto}
.att-chip{position:relative;border:1px solid var(--line);background:var(--panel);
  border-radius:10px;overflow:hidden;display:flex;align-items:center;gap:7px;
  padding:5px 8px 5px 5px;max-width:200px}
.att-chip img{width:44px;height:44px;object-fit:cover;border-radius:7px;display:block}
.att-chip .fic{width:34px;height:34px;border-radius:7px;background:var(--panel2);
  display:flex;align-items:center;justify-content:center;font-size:16px;flex:0 0 auto}
.att-chip .nm{font-size:12.5px;color:var(--dim);overflow:hidden;
  text-overflow:ellipsis;white-space:nowrap;max-width:104px}
.att-chip .x{position:absolute;top:-7px;right:-7px;width:20px;height:20px;border-radius:50%;
  background:var(--err);color:#1a0d0d;font-size:13px;line-height:18px;text-align:center;
  border:2px solid var(--bg)}
.att-chip .pp{position:absolute;left:0;right:0;bottom:0;height:3px;background:var(--accent);
  transform-origin:left;animation:attgo 1.1s linear infinite}
@keyframes attgo{from{transform:scaleX(.05)}to{transform:scaleX(1)}}
#btnAtt{display:inline-flex;align-items:center;justify-content:center;
  width:38px;height:38px;border-radius:var(--r-sm);color:var(--dim);font-size:19px;flex:0 0 auto}
#btnAtt:hover{background:var(--panel2);color:var(--fg)}
#btnAtt.has{color:var(--accent)}
`;
  document.head.append(css);

  /* ── 暂存区 ── */
  const composer=$("#composer"); if(!composer){ return; }
  const bar=el("div"); bar.id="attBar"; bar.hidden=true;
  composer.insertBefore(bar, composer.firstChild);

  let staged=[];                       // [{kind,dataURL,name}]
  let seq=0;

  function draw(){
    bar.hidden = !staged.length;
    bar.innerHTML="";
    staged.forEach((s,i)=>{
      const c=el("div","att-chip");
      if(s.kind==="img"){
        // ★ 已经传上去的（表情包那种：只有 url，没有 dataURL）也画得出来
        const im=el("img"); im.src=s.dataURL||s.url||""; im.alt="";
        c.append(im);
      }else{
        c.append(el("span","fic","📄"));
      }
      c.append(el("span","nm",s.name||"文件"));
      if(s.up) c.append(el("span","pp"));
      const x=el("button","x","✕");
      x.title="不发了";
      x.onclick=()=>{ staged.splice(i,1); draw(); };
      c.append(x);
      bar.append(c);
    });
  }

  /* ── 压图：长边 IMG_MAX，JPEG。压不出来（不是图/解不开）就退回原图 ── */
  function compress(file, cb){
    let done=false;
    const fin=v=>{ if(!done){ done=true; cb(v); } };
    const rd=new FileReader();
    rd.onload=()=>{
      /* ★ 兜底：万一 onload / onerror 一个都没来（个别浏览器碰上看不懂的图会这样），
         不能就这么把它咽了 —— 那这张卡片会永远停在那儿、永远发不出去。
         到点就退回原图，至少发得出去。 */
      const to=setTimeout(()=>fin(rd.result), 8000);
      const im=new Image();
      im.onload=()=>{
        clearTimeout(to);
        try{
          const sc=Math.min(IMG_MAX/im.width, IMG_MAX/im.height, 1);
          const cv=document.createElement("canvas");
          cv.width=Math.round(im.width*sc); cv.height=Math.round(im.height*sc);
          cv.getContext("2d").drawImage(im,0,0,cv.width,cv.height);
          fin(cv.toDataURL("image/jpeg",IMG_Q));
        }catch(e){ fin(rd.result); }     // 画布挂了就发原图，别因此发不出去
      };
      im.onerror=()=>{ clearTimeout(to); fin(rd.result); };
      im.src=rd.result;
    };
    rd.onerror=()=>fin(null);
    rd.readAsDataURL(file);
  }

  function readRaw(file, cb){
    const rd=new FileReader();
    rd.onload=()=>cb(rd.result);
    rd.onerror=()=>cb(null);
    rd.readAsDataURL(file);
  }

  /* ── 挑完先不发，停在上头等配文 ── */
  function take(files, hint){
    const list=[].slice.call(files||[]);
    if(!list.length)return;
    const room=MAXN-staged.length;
    if(room<=0){ say("一次最多 "+MAXN+" 样"); return; }
    const use=list.slice(0,room);
    if(list.length>use.length) say("太多了，先拿了前 "+use.length+" 样");
    let pend=use.length;
    const done=()=>{
      if(--pend>0)return;
      draw();
      try{ $("#ta").focus(); }catch(e){}
      say(staged.length+" 样等着 · 说句话一起发");
    };
    use.forEach(f=>{
      const nm=(f.name||hint||"文件").slice(0,80);
      if(f.size>MAXFILE){ say("「"+nm+"」超过 25MB，没拿"); done(); return; }
      if(f.type && f.type.indexOf("image")===0){
        compress(f,du=>{ if(du) staged.push({kind:"img",dataURL:du,name:nm,k:++seq}); done(); });
      }else{
        readRaw(f,du=>{ if(du) staged.push({kind:"file",dataURL:du,name:nm,k:++seq}); done(); });
      }
    });
  }

  /* ── 一个按钮，点开问你「图片还是文件」──
     ★ 分两个入口是有原因的：平板上不加 accept，相册往往根本不出现在选择器里。 */
  const pic=el("input"); pic.type="file"; pic.accept="image/*"; pic.multiple=true; pic.hidden=true;
  const any=el("input"); any.type="file"; any.multiple=true; any.hidden=true;
  document.body.append(pic, any);
  pic.addEventListener("change",()=>{ take(pic.files); pic.value=""; });
  any.addEventListener("change",()=>{ take(any.files); any.value=""; });

  const btn=el("button",""); btn.id="btnAtt"; btn.type="button";
  btn.title="发图片 / 发文件"; btn.textContent="📎";
  btn.onclick=e=>{
    e.stopPropagation();
    document.querySelectorAll(".menu").forEach(m=>m.remove());
    const m=el("div","menu");
    const mk=(label,fn)=>{
      const b=el("button",null,label);
      b.onclick=()=>{ m.remove(); fn(); };
      m.append(b);
    };
    mk("🖼  图片 / 照片",()=>pic.click());
    mk("📄  文件",()=>any.click());
    if(staged.length) mk("✕  清空这 "+staged.length+" 样",()=>{ staged=[];draw(); });
    document.body.append(m);
    const r=btn.getBoundingClientRect();
    m.style.top=(r.top-6-m.offsetHeight)+"px";
    m.style.left=Math.max(8,Math.min(r.left,innerWidth-m.offsetWidth-8))+"px";
    setTimeout(()=>document.addEventListener("click",()=>m.remove(),{once:true}),0);
  };
  const row=$("#composer .row");
  if(row){ const sb=$("#btnSend"); row.insertBefore(btn, sb||null); }

  /* ── 粘贴进来的图也吃：截图、网页上复制的图、相册里拷的 ── */
  document.addEventListener("paste",e=>{
    const it=(e.clipboardData&&e.clipboardData.items)||[];
    const fs=[];
    for(const x of it){
      if(x.kind==="file"){
        const f=x.getAsFile();
        if(f && f.type && f.type.indexOf("image")===0) fs.push(f);
      }
    }
    if(fs.length){ e.preventDefault(); take(fs,"粘贴的图"); }
  });

  /* ── 送上去 ──
     返回值：成功 → [{kind,url,name}]（暂存已清空）
             失败 → null（暂存原样留着，一个字都不丢） */
  async function collect(){
    if(!staged.length)return [];
    const n=staged.length;
    staged.forEach(s=>{ s.up=true; });
    draw();
    const out=[];
    for(let i=0;i<staged.length;i++){
      const s=staged[i];
      // ★ 已经传上去的（表情包那种只带 url 的）：不再传一遍，直接用。
      if(s.url){ out.push({kind:s.kind,url:s.url,name:s.name}); continue; }
      let d=null;
      try{
        const r=await fetch(s.kind==="img"?"/api/upload":"/api/upload_file",
          {method:"POST",credentials:"same-origin",
           headers:{"Content-Type":"application/json"},
           body:JSON.stringify(s.kind==="img"
             ? {dataURL:s.dataURL}
             : {dataURL:s.dataURL,name:s.name})});
        d=await r.json();
      }catch(e){ d=null; }
      if(!d||!d.url){
        staged.forEach(x=>{ x.up=false; }); draw();
        say("「"+(s.name||"这一样")+"」没送上去，都还留着，再按一次发送");
        return null;
      }
      out.push({kind:s.kind,url:d.url,name:d.name||s.name});
    }
    staged=[]; draw();
    return out;
  }

  /* ── 别处直接塞几样进来（表情包点一下就用到它）──
     只收「已经在服务器上」的：服务器不认外部链接，也不会替你重传一遍。 */
  function stage(items){
    let added=0, full=false;
    (items||[]).forEach(s=>{
      if(!s||!s.url)return;
      if(staged.length>=MAXN){ full=true; return; }
      staged.push({kind:s.kind==="img"?"img":"file",url:s.url,
                   name:(s.name||"文件").slice(0,80),k:++seq});
      added++;
    });
    draw();
    if(full)say("一次最多 "+MAXN+" 样");
    return added;
  }

  window.nestAttach={
    count:()=>staged.length,
    collect,
    stage,
    clear:()=>{ staged=[]; draw(); }
  };
}catch(e){console.error("nest-files:",e);}
})();
