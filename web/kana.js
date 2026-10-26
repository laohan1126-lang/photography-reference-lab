/* Presentation adapter only. app.js owns every decision, API and revision.
 * Move existing controls, never clone handlers or synthesize successful saves.
 */
'use strict';
(() => {
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  const fine = matchMedia('(hover: hover) and (pointer: fine)');
  const root = document.documentElement;
  const kana = document.body.classList.contains('kana-workbench');
  if (!kana) return;
  const inheritedMotion = window.StudioMotion;
  const active = new Set();
  const byId = id => document.getElementById(id);
  const navigation = byId('toggle-project-nav');
  const nav = byId('project-navigation');
  function closeNav(restore = false) {
    document.querySelector('.sidebar')?.classList.remove('nav-open');
    navigation?.setAttribute('aria-expanded', 'false');
    if (restore) navigation?.focus();
  }
  if (!inheritedMotion) navigation?.addEventListener('click', () => {
    const open = document.querySelector('.sidebar')?.classList.toggle('nav-open');
    navigation.setAttribute('aria-expanded', String(Boolean(open)));
  });
  document.addEventListener('click', event => {
    if (event.target.closest('#project-navigation [data-view],#project-navigation [data-project-open]')) closeNav();
    else if (navigation?.getAttribute('aria-expanded') === 'true' && !nav?.contains(event.target) && !navigation.contains(event.target)) closeNav();
    const menu = document.querySelector('.project-tools[open]');
    if (menu && !menu.contains(event.target)) menu.open = false;
  });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && navigation?.getAttribute('aria-expanded') === 'true') {
      closeNav(true); event.preventDefault();
    }
  });
  function animate(node, frames, options, cleanup) {
    if (!node?.isConnected || reduced.matches || document.hidden || !node.animate) { cleanup?.(); return null; }
    const motion = node.animate(frames, options);
    active.add(motion);
    motion.onfinish = motion.oncancel = () => { active.delete(motion); cleanup?.(); };
    return motion;
  }
  function enter(node, distance = 8) {
    animate(node, [{opacity:.65,transform:`translateY(${distance}px)`}, {opacity:1,transform:'translateY(0)'}],
      {duration:280,easing:'cubic-bezier(.2,.7,.2,1)'});
  }
  let view = '';
  const art = byId('kana-theme-image');
  const masthead = document.querySelector('.kana-masthead');
  const notice = byId('kana-asset-notice');
  function assetState() {
    const loaded = Boolean(art?.complete && art.naturalWidth > 0);
    if (notice) notice.hidden = loaded;
    masthead?.classList.toggle('kana-asset-missing', !loaded);
    if (art) art.dataset.assetReady = String(loaded);
  }
  art?.addEventListener('load', assetState);
  art?.addEventListener('error', assetState);
  if (art?.complete) assetState();
  notice?.addEventListener('click', () => {
    const editor = byId('editor');
    if (!editor || editor.open) return;
    byId('editor-title').textContent = '安装私有主题素材';
    const content = byId('editor-content');
    content.replaceChildren();
    const text = document.createElement('p');
    text.textContent = '将私有素材包中的 summer.webp、portrait.webp、rain.webp 安装至 web/private/kana/，刷新即可。素材不进入公开 Git；图片缺失不会阻止搜图和筛选。';
    content.append(text); editor.showModal();
  });

  // Soft, bounded echo of the current, untouched source photo.
  const auraBound = new WeakSet();
  function syncPhotoAtmosphere() {
    const stage=byId('image-stage'), source=byId('main-image');
    if (!stage || !source || auraBound.has(source)) return;
    auraBound.add(source);
    const echo=document.createElement('img');
    echo.className='kana-photo-atmosphere';
    echo.alt=''; echo.setAttribute('aria-hidden','true');
    echo.decoding='async'; echo.hidden=true;
    stage.prepend(echo);
    function update() {
      if (source.isConnected && source.complete && source.naturalWidth>0 && !source.hidden) {
        const url=source.currentSrc||source.src;
        if (echo.src!==url) echo.src=url;
        echo.hidden=false;
      } else echo.hidden=true;
    }
    source.addEventListener('load',update);
    source.addEventListener('error',()=>{echo.hidden=true;});
    new MutationObserver(update).observe(source,{attributes:true,attributeFilter:['src','hidden']});
    update();
  }
  // The adapter deliberately moves the original nodes AFTER app.js binds them.
  // The WeakMap identifies each renderer incarnation, not an arbitrary flag.
  const arranged = new WeakMap();
  function arrangeInspector() {
    if (!kana) return;
    const panel = byId('detail-panel');
    if (!panel) return;
    const heading = panel.querySelector('.detail-heading');
    if (!heading || arranged.get(panel) === heading) return;
    arranged.set(panel, heading);
    // Study / global inspiration have their own domain-specific controls.
    if (!panel.querySelector('[data-decision]') && !panel.querySelector('#edit-card')) return;
    const tools = document.createElement('div');
    tools.className = 'kana-primary-tools';
    tools.setAttribute('role', 'group');
    tools.setAttribute('aria-label', '判断、制卡与分享工具');
    for (const id of ['review-reference','edit-card','edit-source','copy-image-btn','toggle-selection','reveal-file-btn']) {
      const node = byId(id);
      if (node && panel.contains(node)) tools.append(node);
    }
    panel.append(tools);
    const secondary = document.createElement('div');
    secondary.className = 'kana-secondary';
    // Explanations and advanced forms remain available; never hide errors/gates.
    const keep = new Set([heading,tools,...panel.querySelectorAll(':scope > .decision-bar,:scope > .next-step,:scope > .curation-hint')]);
    const explanation = heading.querySelector('.evidence-origin');
    if (explanation) secondary.append(explanation);
    for (const child of [...panel.children]) {
      if (keep.has(child) || child.matches(':scope > button')) continue;
      if (child.matches('button,.preflight-actions,.source-link')) continue;
      // Turn the detailed classification block into an unboxed disclosure.
      if (child.querySelector('#reference-classification-summary')) {
        const detail = document.createElement('details');
        detail.className = 'advanced-panel kana-classification';
        const summary = document.createElement('summary');
        summary.textContent = '摄影分类'; detail.append(summary);
        const title = child.querySelector('h3'); title?.remove();
        while (child.firstChild) detail.append(child.firstChild);
        child.remove(); secondary.append(detail);
      } else if (child.classList.contains('export-share-box')) {
        const detail = document.createElement('details');
        detail.className = 'advanced-panel kana-file-details';
        const summary = document.createElement('summary'); summary.textContent = '文件与归档';
        detail.append(summary, child); secondary.append(detail);
      } else {
        secondary.append(child);
      }
    }
    panel.append(secondary);
    const title = heading.querySelector('h2');
    if (title) title.title = title.textContent;
    panel.dataset.kanaOrganized = 'true';
  }
  function fitViewport() {
    if (!kana) return;
    const stage = byId('image-stage');
    const panel = byId('detail-panel');
    if (innerWidth > 900 && stage) {
      const documentTop = stage.getBoundingClientRect().top + scrollY;
      const available = Math.max(240, Math.min(720, innerHeight-documentTop-115));
      stage.style.setProperty('--kana-stage-height', `${available}px`);
      if(panel)panel.style.setProperty('--kana-panel-height',`${Math.max(300,innerHeight-panel.getBoundingClientRect().top-scrollY-16)}px`);
    } else {
      stage?.style.removeProperty('--kana-stage-height');panel?.style.removeProperty('--kana-panel-height');
      if(stage && innerWidth<=700)stage.style.setProperty('--kana-mobile-stage-height',`${Math.max(190,Math.min(440,innerHeight-stage.getBoundingClientRect().top-scrollY-100))}px`);
    }
  }
  addEventListener('resize', fitViewport);
  addEventListener('load', fitViewport);
  document.fonts?.ready.then(fitViewport);
  let queued = false;
  const observer = new MutationObserver(() => {
    if (queued) return;
    queued = true;
    queueMicrotask(() => {
      queued = false;
      observer.disconnect();
      arrangeInspector();
      syncPhotoAtmosphere();
      fitViewport();
      byId('project-header')?.querySelectorAll('p').forEach(p => p.title = p.textContent);
      if (byId('view')) observer.observe(byId('view'), {subtree:true, childList:true});
    });
  });
  if (kana && byId('view')) { observer.observe(byId('view'), {subtree:true,childList:true}); arrangeInspector(); syncPhotoAtmosphere(); }

  // A bounded, visible visual response. Decorative geometry, not a fake mascot.
  const orbit = document.createElement('span');
  orbit.className = 'kana-pointer-orbit'; orbit.hidden = true; orbit.setAttribute('aria-hidden','true');
  const shapes = [
    '<path d="M12 20S2 14 2 7c0-5 7-7 10-2 3-5 10-3 10 2 0 7-10 13-10 13Z"/>',
    '<path d="m12 2 2.6 6.8L22 12l-7.4 3.2L12 22l-2.6-6.8L2 12l7.4-3.2Z"/>'
  ];
  if (kana) { orbit.innerHTML = Array.from({length:5},(_,i)=>`<svg viewBox="0 0 24 24">${shapes[i%2]}</svg>`).join(''); document.body.append(orbit); }
  let pointerFrame = 0, pointerX = 0, pointerY = 0, hoverTarget = null, last = 0;
  function stopOrbit() { hoverTarget = null; orbit.hidden = true; cancelAnimationFrame(pointerFrame); pointerFrame=0; }
  function orbitFrame(time) {
    if (!hoverTarget?.isConnected || reduced.matches || document.hidden || !fine.matches) { stopOrbit(); return; }
    if (time - last > 25) {
      last = time;
      orbit.style.left = `${pointerX}px`; orbit.style.top = `${pointerY}px`;
      [...orbit.children].forEach((node,i) => {
        const angle = time/1050 + i*Math.PI*2/5;
        const radius = 23 + 3*Math.sin(time/450+i);
        node.style.transform = `translate(${32+Math.cos(angle)*radius}px,${32+Math.sin(angle)*radius}px) rotate(${Math.sin(angle)*20}deg)`;
      });
    }
    pointerFrame = requestAnimationFrame(orbitFrame);
  }
  if (kana) {
    document.addEventListener('pointermove', event => {
      if (reduced.matches || !fine.matches || document.hidden || event.pointerType === 'touch') { stopOrbit(); return; }
      const target = event.target.closest('.kana-find,.decision-bar button,.kana-primary-tools button,.filmstrip button,.kana-signature');
      if (!target || target.disabled) { stopOrbit(); return; }
      hoverTarget = target; pointerX=event.clientX; pointerY=event.clientY; orbit.hidden=false;
      if (!pointerFrame) pointerFrame=requestAnimationFrame(orbitFrame);
    }, {passive:true});
    document.addEventListener('pointerleave', stopOrbit);
    document.addEventListener('pointercancel', stopOrbit);
    document.addEventListener('pointerdown', () => {
      if (!orbit.hidden && !reduced.matches) animate(orbit, [{opacity:1,scale:1},{opacity:0,scale:1.5}],{duration:240},stopOrbit);
    }, {passive:true});
    masthead?.addEventListener('pointermove', event => {
      if (reduced.matches || !fine.matches) return;
      const rect = masthead.getBoundingClientRect();
      masthead.style.setProperty('--kana-x', `${((event.clientX-rect.left)/rect.width-.5)*7}px`);
      masthead.style.setProperty('--kana-y', `${((event.clientY-rect.top)/rect.height-.5)*4}px`);
    }, {passive:true});
    masthead?.addEventListener('pointerleave',()=>{masthead.style.setProperty('--kana-x','0px');masthead.style.setProperty('--kana-y','0px');});
  }
  function scrollFrame() {
    if (!kana) return;
    const y = Math.min(120, Math.max(0, scrollY));
    root.style.setProperty('--kana-scroll', reduced.matches ? '0' : String(y));
  }
  addEventListener('scroll',scrollFrame,{passive:true});
  document.addEventListener('load',event=>{if(event.target.id==='main-image')enter(event.target,5);},true);
  document.addEventListener('visibilitychange',()=>{
    root.dataset.studioHidden=String(document.hidden);
    if (document.hidden) {stopOrbit();for(const animation of [...active])animation.cancel();}
  });
  reduced.addEventListener('change',()=>{
    stopOrbit(); if(reduced.matches)for(const animation of [...active])animation.cancel(); scrollFrame();
  });
  fine.addEventListener('change',stopOrbit);
  window.StudioMotion = {
    frame(text) { const counter=byId('studio-take-counter'); if(counter)counter.textContent=text; },
    setView(next) {
      root.dataset.studioView=next;
      if(next===view)return; view=next;
      this.frame('—');
      if(art){
        const file=next==='inspiration'?'rain.webp':'summer.webp';
        const path=window.__KANA_OFFLINE_ASSETS?.[file] || `/static/private/kana/${file}`;
        if(art.getAttribute('src')!==path){art.dataset.assetReady='false';art.src=path;}
      }
      requestAnimationFrame(()=>{enter(byId('project-header'));arrangeInspector();});
    },
    commit(choice, reference) {
      const words={keep:'已留作角色参考',inspiration:'已存入灵感库',maybe:'已标记待定',reject:'已淘汰，可恢复'};
      const stage=byId('image-stage');
      if(!Object.hasOwn(words,choice)||!stage?.isConnected)return;
      stage.querySelector('.stage-effect')?.remove();
      const effect=document.createElement('div');effect.className='stage-effect';effect.dataset.choice=choice;effect.dataset.reference=reference.id;
      if(!reduced.matches&&reference.file_available!==false&&reference.asset_sha){
        const snapshot=document.createElement('img');snapshot.src=`/api/assets/${reference.asset_sha}/preview`;snapshot.alt='';effect.append(snapshot);
      }
      const caption=document.createElement('span');caption.textContent=`刚保存 · ${words[choice]}`;effect.append(caption);stage.append(effect);
      const thumb=[...(byId('filmstrip')?.children||[])].find(n=>n.dataset.ref===reference.id);
      const control=document.querySelector(`.decision-bar [data-decision="${choice}"]`);
      for(const node of [thumb,control])if(node)node.dataset.lastDecision=choice;
      const cleanup=()=>{effect.remove();for(const node of [thumb,control])if(node?.dataset.lastDecision===choice)delete node.dataset.lastDecision;};
      if(reduced.matches){setTimeout(cleanup,700);return;}
      const destinations={keep:'translateY(-8px) scale(.94)',inspiration:'translate(30px,-20px) rotate(3deg) scale(.86)',maybe:'translateY(-12px) rotate(-2deg)',reject:'translateX(-38px) scaleX(.82)'};
      animate(effect,[{opacity:1,transform:'translate(0,0) scale(1)'},{opacity:0,transform:destinations[choice]}],{duration:choice==='maybe'?420:380,easing:'cubic-bezier(.2,.7,.2,1)'},cleanup);
    }
  };
  scrollFrame();
  requestAnimationFrame(fitViewport);
})();
