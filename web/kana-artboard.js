/* Approved Arima Kana artboard. Presentation-only: never owns API, data or decision logic. */
'use strict';
(() => {
  const ready = () => {
    if (!document.body.classList.contains('kana-workbench')) return;
    document.body.classList.add('kana-artboard');
    const hero = document.querySelector('.kana-masthead');
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)');
    if (!hero) return;
    if (!hero.querySelector('.kana-editorial-lettering')) {
      const lettering = document.createElement('div');
      lettering.className='kana-editorial-lettering';
      lettering.setAttribute('aria-label','ARIMA Kana · 有马加奈的摄影参考');
      lettering.innerHTML = `<span class="eyebrow-jp" lang="ja">この一枚、どうする？</span>
      <img class="artboard-arima" src="/static/ui-art/kana-artboard-arima.svg" alt="ARIMA" draggable="false">
      <img class="artboard-kana" src="/static/ui-art/kana-artboard-kana.svg" alt="Kana" draggable="false">
      <span class="artboard-cn">有马加奈 <span aria-hidden="true">♥</span></span>
      <span class="artboard-sub">让心动的瞬间，成为下一次拍摄的灵感。<br><i lang="ja">私だけのフォトダイアリー。</i></span>
      <svg class="artboard-underline" viewBox="0 0 340 55" fill="none" aria-hidden="true"><path d="M7 15Q84 40 175 20T328 10" stroke="#df4381" stroke-width="1.2" stroke-linecap="round"/><path d="M240 7l4 7 9 1-7 5-2 8-5-7-9-1 7-5z" fill="#ffc980" opacity=".75"/></svg>`;
      hero.appendChild(lettering);
    }
    const note=hero.querySelector('.kana-cover-note');
    if(note) note.textContent='いい写真、見つけよっ！';
    if(!hero.querySelector('.kana-decorative-prints')) {
      const prints=document.createElement('div');prints.className='kana-decorative-prints';prints.setAttribute('aria-hidden','true');
      for(const name of ['portrait.webp','rain.webp']) {
        const img=document.createElement('img');img.alt='';img.decoding='async';
        img.src=window.__KANA_OFFLINE_ASSETS?.[name] || `/static/private/kana/${name}`;
        img.addEventListener('error',()=>img.remove());
        prints.append(img);
      }
      hero.append(prints);
      const heart=document.createElement('span');heart.className='kana-floating-heart';heart.setAttribute('aria-hidden','true');heart.textContent='♡';hero.append(heart);
    }
    // One-time live gesture feedback in work areas. All actual action callbacks remain in app.js.
    let last=0, sequence=0;
    document.addEventListener('pointermove',event=>{
      if(reduced.matches || event.pointerType!=='mouse' || !event.isPrimary || document.hidden) return;
      const hot=event.target.closest('.kana-find,.view-tabs button,.decision-bar button,.kana-primary-tools button,.filmstrip button,.image-stage .stage-nav');
      if(!hot || Date.now()-last<165) return;
      last=Date.now();
      const chip=document.createElement('span');chip.className='kana-heart-trace';chip.setAttribute('aria-hidden','true');
      chip.textContent=sequence++%4===0?'✧':(sequence%3===0?'☆':'♡');
      chip.style.left=event.clientX+'px';chip.style.top=event.clientY+'px';
      chip.style.setProperty('--dx',`${Math.round((sequence%5-2)*16)}px`);
      chip.style.setProperty('--dy',`${-25-sequence%4*12}px`);
      document.body.append(chip);setTimeout(()=>chip.remove(),860);
    },{passive:true});
    // Native controls remain unique; no cloning or fake success states.
    document.documentElement.dataset.kanaArtboard = 'approved-concept';
  };
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',ready,{once:true});
  else ready();
})();
