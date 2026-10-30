/* Presentation only. Original app.js remains the sole owner of domain state/API writes.
   Original nodes/handlers are moved, never copied; no false success or theme data in library. */
'use strict';
(() => {
  if (!document.body.classList.contains('kana-canvas')) return;
  const byId=id=>document.getElementById(id), reduced=matchMedia('(prefers-reduced-motion: reduce)'), fine=matchMedia('(hover:hover) and (pointer:fine)');
  const paths={heart:'<path d="M20.5 5.5a5 5 0 0 0-7.1 0L12 7l-1.4-1.5a5 5 0 0 0-7.1 7.1L12 21l8.5-8.4a5 5 0 0 0 0-7.1Z"/>',star:'<path d="m12 3 2.8 5.7 6.2.9-4.5 4.4 1.1 6.2-5.6-3-5.6 3 1.1-6.2L3 9.6l6.2-.9Z"/>',maybe:'<circle cx="12" cy="12" r="9"/><path d="M8 15h8"/><circle cx="9" cy="9" r=".6"/><circle cx="15" cy="9" r=".6"/>',bin:'<path d="M3 6h18M9 6V3h6v3M6 6l1 15h10l1-15M10 10v7M14 10v7"/>',card:'<rect x="4" y="3" width="16" height="18" rx="2"/><path d="M8 15h8M8 18h5m-5-7 4-4 4 4M12 7v7"/>',source:'<path d="M14 4h6v6M20 4l-9 9M11 5H4v15h15v-7"/>',copy:'<rect x="8" y="8" width="12" height="13" rx="2"/><path d="M15 8V3H3v13h5"/>',folder:'<path d="M3 6h7l2 3h9v11H3zM3 6V4h7l2 2h8v3"/>',eye:'<path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/>',left:'<path d="m15 5-7 7 7 7"/>',right:'<path d="m9 5 7 7-7 7"/>'};
  function svg(name){const el=document.createElementNS('http://www.w3.org/2000/svg','svg');el.setAttribute('viewBox','0 0 24 24');el.classList.add('ui-icon');el.setAttribute('aria-hidden','true');el.innerHTML=paths[name]||paths.star;return el;}
  const active=new Set();
  function animate(el,frames,options){if(!el?.isConnected||reduced.matches||document.hidden)return;const a=el.animate(frames,options);active.add(a);a.onfinish=a.oncancel=()=>active.delete(a);return a;}
  const nav=byId('toggle-project-nav');
  const globalNav=byId('global-nav'),globalHome=globalNav?.parentNode;
  const sidebar=document.querySelector('.sidebar');
  const projectNavigation=byId('project-navigation');
  const projectHome=projectNavigation?.parentNode;
  const projectAnchor=document.createComment('desktop project navigation');
  if(projectNavigation&&projectHome)projectHome.insertBefore(projectAnchor,projectNavigation);
  if(projectNavigation&&sidebar){sidebar.classList.add('project-nav-in-sidebar');sidebar.append(projectNavigation);}
  const branchNavigation=sidebar?.querySelector(':scope > .photography-branches');
  const branchHome=branchNavigation?.parentNode;
  const branchAnchor=document.createComment('desktop photography branches');
  if(branchNavigation)branchNavigation.after(branchAnchor);
  const globalAnchor=document.createComment('desktop global navigation');
  if(globalNav)globalNav.after(globalAnchor);
  function syncNavigation(){
    if(!globalNav||!globalHome)return;
    sidebar?.classList.toggle('project-nav-in-sidebar',innerWidth>700);
    if(innerWidth<=700){const panel=byId('project-navigation');if(globalNav.parentNode!==panel)panel?.append(globalNav);globalNav.style.display='flex';if(branchNavigation&&panel&&branchNavigation.parentNode!==panel)panel.prepend(branchNavigation);}
    else {
      if(globalNav.parentNode!==globalHome)globalHome.insertBefore(globalNav,globalAnchor);
      if(branchNavigation&&branchHome&&branchNavigation.parentNode!==branchHome)branchHome.insertBefore(branchNavigation,branchAnchor);
      globalNav.style.removeProperty('display');branchNavigation?.style.removeProperty('display');
    }
  }
  syncNavigation();
  document.addEventListener('click',event=>{
    const more=document.querySelector('.global-more');
    if(more?.open&&(event.target.closest('#global-nav [data-view]')||!more.contains(event.target)))more.open=false;
    if(event.target.closest('#global-nav [data-view]'))closeNav();
  });
  function closeNav(restore=false){document.body.classList.remove('nav-open');nav?.setAttribute('aria-expanded','false');if(restore)nav?.focus();}
  nav?.addEventListener('click',()=>{if(innerWidth>700){byId('project-search')?.focus();return;}const open=document.body.classList.toggle('nav-open');nav.setAttribute('aria-expanded',String(open));});
  document.addEventListener('keydown',e=>{if(e.key==='Escape'&&document.body.classList.contains('nav-open')){closeNav(true);e.preventDefault();}});
  document.addEventListener('click',e=>{if(e.target.closest('#project-navigation [data-project-open]'))closeNav();if(document.body.classList.contains('nav-open')&&!e.target.closest('#project-navigation,#toggle-project-nav'))closeNav();});
  const art=byId('kana-theme-image'),notice=byId('kana-asset-notice');
  function artStatus(){const ok=Boolean(art?.complete&&art.naturalWidth);if(art)art.dataset.assetReady=String(ok);if(notice)notice.hidden=ok;document.body.classList.toggle('canvas-art-missing',!ok);}
  art?.addEventListener('load',artStatus);art?.addEventListener('error',artStatus);artStatus();
  const app=byId('application');
  if(app)new MutationObserver(()=>{if(!app.hidden){byId('connection-status').textContent='已载入参考库';document.querySelectorAll('img[src*="/static/private/"]').forEach(n=>{if(n.complete&&!n.naturalWidth)n.src=n.src;});}}).observe(app,{attributes:true,attributeFilter:['hidden']});
  notice?.addEventListener('click',()=>{const editor=byId('editor');if(!editor||editor.open)return;byId('editor-title').textContent='安装原始主题素材';byId('editor-content').replaceChildren();const p=document.createElement('p');p.textContent='当前主题需要你提供的 portrait.webp、summer.webp 和 rain.webp。请使用 tools/install_kana_assets.py 安装到本工作树 web/private/kana/；不要公开私人原画。';byId('editor-content').append(p);editor.showModal();});
  const organized=new WeakMap();
  function organizeInspector(){
    const panel=byId('detail-panel'),heading=panel?.querySelector('.detail-heading');
    if(!heading||organized.get(panel)===heading)return;
    organized.set(panel,heading);
    // Domain-specific study/inspiration views keep their original commands intact.
    if(!panel.querySelector('[data-decision]')&&!panel.querySelector('#edit-card'))return;
    const h=document.createElement('h3');h.className='canvas-inspector-title';h.append(svg('star'),document.createTextNode('开始取景'));heading.prepend(h);
    const error=panel.querySelector('#archive-error');if(error)heading.append(error);
    const decisions=panel.querySelector('.decision-bar');
    decisions?.querySelectorAll('[data-decision]').forEach(button=>{const key=button.dataset.decision;const defs={keep:['保留','K','heart','保留为本角色参考'],inspiration:['通用灵感','I','heart','归入独立审美库并移出项目'],maybe:['待定','M','maybe','标记为待定'],reject:['淘汰','X','bin','淘汰，可恢复']};const d=defs[key];if(!d)return;button.title=d[3];button.setAttribute('aria-label',d[3]);const strong=document.createElement('strong');strong.textContent=d[0];const small=document.createElement('small');small.textContent=d[1];button.replaceChildren(svg(d[2]),strong,small);});
    const tools=document.createElement('div');tools.className='kana-primary-tools';tools.setAttribute('role','group');tools.setAttribute('aria-label','制卡、来源与分享');
    const actionDefs=[['edit-card','card','手动制卡'],['review-reference','eye','修正判断'],['edit-source','source','来源与标题'],['copy-image-btn','copy','复制发微信'],['toggle-selection','heart','批量选择'],['reveal-file-btn','folder','文件位置']];
    for(const [id,glyph,label] of actionDefs){const b=byId(id);if(!b||!panel.contains(b))continue;const old=b.textContent;b.title=old;b.setAttribute('aria-label',old);const span=document.createElement('span');span.textContent=label;b.replaceChildren(svg(glyph),span);tools.append(b);}
    const label=document.createElement('h3');label.className='canvas-operation-title';label.textContent='更多操作';
    const secondary=document.createElement('div');secondary.className='canvas-secondary';
    const reason=heading.querySelector('.preflight-reason');if(reason){const d=document.createElement('details');d.className='advanced-panel';const summary=document.createElement('summary');summary.textContent='预检说明（不等于身份确认）';d.append(summary,reason);secondary.append(d);}
    const keep=new Set([heading,...panel.querySelectorAll(':scope > .decision-bar,:scope > .next-step,:scope > .curation-hint')]);
    const explanation=heading.querySelector('.evidence-origin');if(explanation){explanation.classList.add('advanced-panel');secondary.append(explanation);}
    for(const child of [...panel.children]){
      if(keep.has(child)||child.matches('button,.preflight-actions,.source-link')||child.querySelector('#archive-error'))continue;
      if(child.querySelector('#reference-classification-summary')){const d=document.createElement('details');d.className='advanced-panel';const sm=document.createElement('summary');sm.textContent='摄影分类';d.append(sm);child.querySelector('h3')?.remove();while(child.firstChild)d.append(child.firstChild);child.remove();secondary.append(d);}
      else if(child.classList.contains('export-share-box')){const d=document.createElement('details');d.className='advanced-panel';const sm=document.createElement('summary');sm.textContent='文件与归档';d.append(sm,child);secondary.append(d);}
      else secondary.append(child);
    }
    panel.append(label,tools,secondary);panel.dataset.kanaOrganized='true';
    const title=heading.querySelector('h2');if(title)title.title=title.textContent;
  }
  const sourceBound=new WeakSet();
  function bindImage(){const source=byId('main-image'),stage=byId('image-stage');if(!source||!stage||sourceBound.has(source))return;sourceBound.add(source);const echo=document.createElement('img');echo.className='photo-echo';echo.alt='';echo.setAttribute('aria-hidden','true');stage.prepend(echo);const update=()=>{echo.hidden=!(source.complete&&source.naturalWidth&&!source.hidden);if(!echo.hidden&&echo.getAttribute('src')!==source.getAttribute('src'))echo.src=source.currentSrc||source.src;};source.addEventListener('load',update);source.addEventListener('error',()=>echo.hidden=true);new MutationObserver(update).observe(source,{attributes:true,attributeFilter:['src','hidden']});update();for(const [id,i] of [['stage-prev-btn','left'],['stage-next-btn','right']])byId(id)?.replaceChildren(svg(i));}
  function fitViewport(){
    const stage=byId('image-stage');
    if(!stage)return;
    const top=stage.getBoundingClientRect().top+scrollY;
    const minimum=innerWidth<=700?240:420;
    const available=Math.max(minimum,Math.min(680,innerHeight-top-(innerWidth<=700?100:32)));
    stage.style.setProperty('--photo-height',available+'px');

  }
  function moveFilters(){
    const view=byId('view'),slot=byId('canvas-filter-slot');
    if(!view||!slot)return;
    // Only the review search toolbar belongs in the project index. Notes/jobs
    // also use .toolbar; moving theirs would let a later observer delete it.
    const isReview=Boolean(view.querySelector('#reference-content'));
    const toolbar=view.querySelector(':scope > .toolbar');
    if(isReview&&toolbar?.querySelector('#search-ref'))slot.replaceChildren(toolbar);
    else if(!isReview&&slot.firstChild)slot.replaceChildren();
  }
  let queued=false;const observer=new MutationObserver(()=>{if(queued)return;queued=true;queueMicrotask(()=>{queued=false;observer.disconnect();moveFilters();organizeInspector();bindImage();fitViewport();observer.observe(byId('view'),{childList:true,subtree:true});});});
  if(byId('view'))observer.observe(byId('view'),{childList:true,subtree:true});
  addEventListener('resize',()=>{syncNavigation();fitViewport();if(innerWidth>700)closeNav();});addEventListener('load',fitViewport);document.fonts?.ready.then(fitViewport);
  const orbit=document.createElement('span');orbit.className='canvas-orbit';orbit.hidden=true;orbit.setAttribute('aria-hidden','true');for(let i=0;i<5;i++)orbit.append(svg(i%2?'star':'heart'));document.body.append(orbit);let raf=0,target=null,x=0,y=0;
  function stop(){target=null;orbit.hidden=true;cancelAnimationFrame(raf);raf=0;}
  function tick(t){if(!target?.isConnected||reduced.matches||document.hidden||!fine.matches){stop();return;}orbit.style.transform=`translate(${x}px,${y}px)`;[...orbit.children].forEach((n,i)=>{const a=t/1000+i*1.2566,r=21+3*Math.sin(t/420+i);n.style.transform=`translate(${Math.cos(a)*r-6}px,${Math.sin(a)*r-6}px) rotate(${a*18}deg)`;});raf=requestAnimationFrame(tick);}
  document.addEventListener('pointermove',e=>{if(reduced.matches||!fine.matches||e.pointerType==='touch'){stop();return;}target=e.target.closest('.decision-bar button,.kana-primary-tools button,#canvas-title,.filmstrip button');if(!target||target.disabled){stop();return;}x=e.clientX;y=e.clientY;orbit.hidden=false;if(!raf)raf=requestAnimationFrame(tick);},{passive:true});document.addEventListener('pointerleave',stop);document.addEventListener('pointercancel',stop);
  document.addEventListener('visibilitychange',()=>{if(document.hidden){stop();for(const a of active)a.cancel();}});reduced.addEventListener('change',()=>{stop();if(reduced.matches)for(const a of active)a.cancel();});
  window.StudioMotion={frame(text){const n=byId('studio-take-counter');if(n)n.textContent=text;},setView(view){document.documentElement.dataset.studioView=view;requestAnimationFrame(()=>{moveFilters();organizeInspector();bindImage();fitViewport();});},commit(choice,ref){
    const messages={keep:'已留作角色参考',inspiration:'已存入灵感库',maybe:'已标记待定',reject:'已淘汰，可恢复'};
    const stage=byId('image-stage');if(!stage||!Object.hasOwn(messages,choice))return;
    stage.querySelector('.stage-effect')?.remove();
    const effect=document.createElement('div');effect.className='stage-effect';effect.dataset.choice=choice;effect.dataset.reference=ref.id;Object.assign(effect.style,{position:'absolute',inset:'0',zIndex:'6',pointerEvents:'none',display:'flex',justifyContent:'center',alignItems:'flex-end',padding:'20px'});
    const caption=document.createElement('span');caption.textContent=messages[choice];Object.assign(caption.style,{fontSize:'12px',padding:'8px 16px',borderRadius:'20px',background:'#fffaf5ed',color:'#c52a64',boxShadow:'0 4px 20px #6b3c5825'});effect.append(caption);stage.append(effect);
    if(reduced.matches){setTimeout(()=>effect.remove(),700);return;}
    const destination={keep:'translateY(-18px) scale(.98)',inspiration:'translate(18px,-12px) rotate(2deg)',maybe:'translateY(-8px) rotate(-1deg)',reject:'translateX(-22px) scale(.94)'};
    const motion=animate(effect,[{opacity:1,transform:'translate(0,0)'},{opacity:0,transform:destination[choice]}],{duration:420,easing:'ease-out'});
    if(motion){const done=motion.onfinish;motion.onfinish=motion.oncancel=()=>{done?.();effect.remove();};}else effect.remove();
  }};
  animate(byId('canvas-title'),[{opacity:0,transform:'translateY(8px)'},{opacity:1,transform:'translateY(0)'}],{duration:550,easing:'ease-out'});
})();
