'use strict';
// Teaching owns its drafts and reading position; the atlas owns routes and writes.
window.LearningGateways = (() => {
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const labels = {unassessed:'尚未自评', unseen:'尚未接触', terms:'了解术语', principles:'理解基本原理', analysis:'能够分析案例', transfer:'能独立迁移到新场景', field:'已经过实际拍摄验证'};
  const notes = {unassessed:'阅读与展开解析不会替你升级。', unseen:'这是你的自评，可以直接跳到有挑战的部分。', terms:'能认出概念名称，还不等于能解释照片。', principles:'能解释变量关系；下一步用具体画面检验。', analysis:'能指出图中证据，也能说清尚不能确定的条件。', transfer:'由你确认能在未讲过的场景中独立判断。', field:'由你确认已经拍摄、比较并验证；可在关联技能中附实拍记录。'};
  const drafts = new Map();
  let catalog = [], sources = new Map(), host, dialog, scroll, current = null, origin = null, busy = false;
  const key = id => `photography-gateway-draft-v2:${id}`;
  const safeURL = value => { try { const u = new URL(value); return u.protocol === 'https:' && !u.username && !u.password ? u.href : ''; } catch { return ''; } };
  const record = id => host.record(id) || {};
  function getDraft(id) {
    if (drafts.has(id)) return drafts.get(id);
    let saved;
    try { saved = JSON.parse(sessionStorage.getItem(key(id)) || 'null'); } catch {}
    const server = record(id);
    const value = saved && saved.answers && typeof saved.answers === 'object' && Number.isInteger(saved.revision)
      ? saved : {stage:server.stage || 'unassessed', answers:{...(server.answers || {})}, revealed:[...(server.revealed || [])], last_section:server.last_section || 'problem', revision:host.revision(), serverSnapshot:JSON.stringify(server), scroll:0, dirty:false};
    if (!Array.isArray(value.revealed)) value.revealed = [];
    if (!(value.stage in labels)) value.stage = 'unassessed';
    drafts.set(id, value);
    return value;
  }
  function remember() {
    if (!current) return;
    const draft = getDraft(current.id);
    draft.scroll = scroll.scrollTop;
    try { sessionStorage.setItem(key(current.id), JSON.stringify(draft)); } catch { /* In-memory draft still survives closing the reader. */ }
  }
  function notice(text, error=false) {
    const node = document.getElementById('gateway-message');
    if (node) { node.textContent = text; node.dataset.error = String(error); }
  }
  function caseHTML(gateway, id) {
    const item = gateway.cases.find(c => c.id === id);
    if (!item) return '';
    const url = safeURL(item.url);
    const images = item.display === 'source_remote' ? item.images || []
      : item.display === 'licensed_remote' && item.rights.allowed === true ? [item] : [];
    const media = images.filter(image=>safeURL(image.src)).map(image=>{
      const dimensions = Number.isInteger(image.width) && Number.isInteger(image.height) ? ` width="${image.width}" height="${image.height}"` : '';
      return `<div class="case-media">${image.label?`<p class="case-media-label">${esc(image.label)}</p>`:''}<div class="case-image"><img src="${esc(safeURL(image.src))}" alt="${esc(image.alt)}" loading="lazy"${dimensions} referrerpolicy="no-referrer"><span class="case-loading" role="status">正在加载原案例照片…</span><span class="case-load-error" hidden>这张图片暂时无法加载。中文要点仍可阅读，原案例链接在下方。</span></div></div>`;
    }).join('');
    const summary = item.source_summary;
    return `<figure class="gateway-case" data-case="${esc(id)}">${media || `<a class="gateway-case-link" href="${esc(url)}" target="_blank" rel="noopener noreferrer">打开原站实拍对照 ↗<span>${esc(item.title)}</span></a>`}<figcaption><strong>${esc(item.title)}</strong><span>${esc(item.author)} · ${esc(item.caption)}</span>${summary?`<details class="case-source-summary"><summary>原文要点 · 中文转述</summary><p>${esc(summary.text)}</p><span class="case-source-locator">原文定位：${esc(summary.locator)} · 核对于 ${esc(summary.checked_at)}</span></details>`:''}<a href="${esc(url)}" target="_blank" rel="noopener noreferrer">原案例与图像出处 ↗</a><details><summary>图像使用与核验范围</summary><p>${esc(item.review.detail)}</p><p>${esc(item.rights.statement)} <a href="${esc(safeURL(item.rights.url))}" target="_blank" rel="noopener noreferrer">权利说明 ↗</a></p></details></figcaption></figure>`;
  }
  function citations(ids) {
    return (ids || []).map(id => sources.get(id)).filter(Boolean).map(source => `<a href="${esc(safeURL(source.url))}" target="_blank" rel="noopener noreferrer">${esc(source.short_title || source.title)} ↗</a>`).join(' · ');
  }
  function blockHTML(block, gateway, draft) {
    switch (block.type) {
      case 'paragraph': return `<p>${esc(block.text)}</p>`;
      case 'heading': return `<h3>${esc(block.text)}</h3>`;
      case 'list': return `<ul>${block.items.map(item=>`<li>${esc(item)}</li>`).join('')}</ul>`;
      case 'comparison': return `<div class="gateway-observations">${block.rows.map(row=>`<div><p class="gateway-small">第一眼可能会问</p><p>${esc(row.novice)}</p><p class="gateway-small">再往下观察</p><p><strong>${esc(row.expert)}</strong></p><p>${esc(row.question)}</p></div>`).join('')}</div>`;
      case 'case': return caseHTML(gateway, block.case_id);
      case 'case_pair': return `<div class="gateway-case-pair">${block.case_ids.map(id=>caseHTML(gateway,id)).join('')}</div>`;
      case 'exercise': return `<div class="gateway-exercise"><h3>${esc(block.title)}</h3><p>${esc(block.prompt)}</p>${block.options?.length?`<div class="gateway-choices" role="group" aria-label="${esc(block.title)}">${block.options.map(option=>`<button type="button" data-gw-choice="${esc(block.id)}" data-value="${esc(option)}" aria-pressed="${draft.answers[block.id]===option}">${esc(option)}</button>`).join('')}</div>`:''}<label for="gw-answer-${esc(block.id)}">${esc(block.label || '先记下你的观察（可跳过）')}</label><textarea id="gw-answer-${esc(block.id)}" data-gw-answer="${esc(block.id)}" maxlength="8000" rows="3" placeholder="${esc(block.placeholder || '图中看见了什么？还有什么不能确定？')}">${esc(draft.answers[block.id] || '')}</textarea></div>`;
      case 'reveal': return `<details class="gateway-reveal" data-gw-reveal="${esc(block.activity_id)}"${draft.revealed.includes(block.activity_id)?' open':''}><summary>${esc(block.title)}</summary><div>${block.paragraphs.map(text=>`<p>${esc(text)}</p>`).join('')}${block.source_ids?.length?`<p class="gateway-citation">分析依据：${citations(block.source_ids)}</p>`:''}</div></details>`;
      default: return '';
    }
  }
  function sourceHTML(gateway) {
    return gateway.source_ids.map(id=>sources.get(id)).filter(Boolean).map(source=>`<article class="gateway-source"><h3><a href="${esc(safeURL(source.url))}" target="_blank" rel="noopener noreferrer">${esc(source.title)} ↗</a></h3><p>${esc(source.author)} · ${esc(source.reading_depth)} · 核对于 ${esc(source.checked_at)}</p><dl><dt>定位</dt><dd>${esc(source.locator)}</dd><dt>支持什么</dt><dd>${esc(source.support)}</dd><dt>边界</dt><dd>${esc(source.limitation)}</dd></dl></article>`).join('');
  }
  function selfAssessment(draft) {
    return `<form id="gateway-form" class="gateway-reflection"><label for="gateway-stage">我目前能做到什么 · 自评</label><select id="gateway-stage">${Object.entries(labels).map(([value,label])=>`<option value="${value}"${draft.stage===value?' selected':''}>${label}</option>`).join('')}</select><p id="gateway-stage-note" class="gateway-small">${esc(notes[draft.stage])}</p><label for="gw-confusion">仍然困惑的部分 / 下次实拍如何验证</label><textarea id="gw-confusion" data-gw-answer="confusion" rows="3" maxlength="8000">${esc(draft.answers.confusion || '')}</textarea><div class="gateway-save-row"><button id="gateway-save" class="primary-button" type="submit"${host.canWrite()&&!busy?'':' disabled'}>保存观察与自评</button><p id="gateway-message" role="status">${host.canWrite() ? (draft.dirty?'有未保存的草稿；关闭抽屉仍会保留在本标签页。':'只有主动保存才会写入私人记录。') : '私人记录当前不可写；可阅读和在本标签页暂存草稿。'}</p></div><button type="button" id="gateway-reload" class="text-link" hidden>加载服务器记录（替换此入口的本页草稿）</button></form>`;
  }
  function render() {
    const gateway = current, draft = getDraft(gateway.id);
    dialog.innerHTML = `<header class="gateway-reader-header"><div><p class="eyebrow">CONCEPTUAL GATEWAY · 认知入口</p><h2 id="gateway-title" tabindex="-1">${esc(gateway.title)}</h2></div><button id="gateway-close" class="close-button" type="button" aria-label="关闭阅读，返回原位置">×</button></header><div class="gateway-scroll"><div class="gateway-reading-layout"><aside class="gateway-outline"><details open><summary>阅读目录</summary><nav aria-label="阅读章节">${gateway.sections.map((section,index)=>`<button type="button" data-gw-section="${esc(section.id)}"><span>${String(index+1).padStart(2,'0')}</span>${esc(section.title)}</button>`).join('')}</nav></details><label for="gateway-switch">切换认知入口</label><select id="gateway-switch">${catalog.map(item=>`<option value="${esc(item.id)}"${gateway.id===item.id?' selected':''}>${esc(item.title)}</option>`).join('')}</select></aside><article class="gateway-reading"><div class="gateway-reading-intro"><p class="gateway-byline">${esc(gateway.author)} · ${esc(gateway.reading_depth)}</p><p>${esc(gateway.outcome)}</p><p class="gateway-small">${esc(gateway.prior_knowledge)}</p><p class="gateway-citation">专业依据：${citations(gateway.source_ids.slice(0,3))}</p></div>${gateway.sections.map(section=>`<section class="gateway-chapter" id="gw-${esc(section.id)}" tabindex="-1"><p class="eyebrow">${esc(section.kicker || section.id.toUpperCase())}</p><h2>${esc(section.title)}</h2>${section.blocks.map(block=>blockHTML(block,gateway,draft)).join('')}${section.source_ids?.length?`<p class="gateway-citation">本节依据：${citations(section.source_ids)}</p>`:''}${section.id==='reflect'?selfAssessment(draft):''}${section.id==='sources'?sourceHTML(gateway):''}</section>`).join('')}<footer class="gateway-reading-footer"><p>继续在技能地图里练习</p>${gateway.skill_ids.map(id=>`<button type="button" data-gw-skill="${esc(id)}">${esc(host.skillName(id))} →</button>`).join('')}</footer></article></div></div>`;
    scroll = dialog.querySelector('.gateway-scroll');
    scroll.scrollTop = draft.scroll || 0;
    dialog.querySelectorAll('img').forEach(img=>{
      const loading=img.parentElement.querySelector('.case-loading'), error=img.parentElement.querySelector('.case-load-error');
      img.addEventListener('load',()=>{loading.hidden=true;});
      img.addEventListener('error',()=>{img.hidden=true;loading.hidden=true;error.hidden=false;});
      if(img.complete) {
        loading.hidden=true;
        if(!img.naturalWidth) {img.hidden=true;error.hidden=false;}
      }
    });
    dialog.querySelectorAll('[data-gw-reveal]').forEach(details=>details.addEventListener('toggle',()=>{
      const active = getDraft(gateway.id), id = details.dataset.gwReveal;
      const before = active.revealed.includes(id);
      if (before === details.open) return;
      active.revealed = details.open ? [...active.revealed,id] : active.revealed.filter(value=>value!==id);
      active.dirty=true; remember();
    }));
    document.getElementById('gateway-form').addEventListener('submit', save);
  }
  function close(restore=true) {
    if (!dialog?.open) return;
    remember();
    const previous = origin;
    current = null; origin = null;
    dialog.close(); document.body.classList.remove('gateway-is-open');
    if (restore && previous?.route === location.hash) {
      window.scrollTo({top:previous.scroll,behavior:'instant'});
      if (previous.focus?.isConnected) previous.focus.focus({preventScroll:true});
    }
  }
  function open(id, button) {
    const gateway = catalog.find(item=>item.id===id);
    if (!gateway) return;
    if (dialog.open) remember();
    else origin = {route:location.hash, scroll:window.scrollY, focus:button || document.activeElement};
    current=gateway; render();
    if (!dialog.open) { dialog.showModal(); document.body.classList.add('gateway-is-open'); }
    document.getElementById('gateway-title').focus({preventScroll:true});
    scroll.scrollTop=getDraft(id).scroll || 0;
  }
  async function save(event) {
    event.preventDefault();
    if (!current || busy || !host.canWrite()) return;
    remember();
    const id=current.id, draft=getDraft(id);
    // Unrelated writes may advance the shared revision without changing this record.
    if (draft.serverSnapshot === JSON.stringify(record(id))) draft.revision=host.revision();
    const payload={stage:draft.stage,answers:{...draft.answers},revealed:[...draft.revealed],last_section:draft.last_section,expected_revision:draft.revision};
    busy=true;
    document.getElementById('gateway-save').disabled=true;
    notice('正在保存…');
    try {
      const revision=await host.save(id,payload);
      draft.revision=revision; draft.serverSnapshot=JSON.stringify(record(id));
      const changedWhileSaving=JSON.stringify([draft.stage,draft.answers,draft.revealed,draft.last_section])!==JSON.stringify([payload.stage,payload.answers,payload.revealed,payload.last_section]);
      draft.dirty=changedWhileSaving;
      try { sessionStorage.setItem(key(id),JSON.stringify(draft)); } catch {}
      if(current?.id===id) notice(changedWhileSaving?'先前内容已保存，保存过程中新增的编辑仍是草稿。':'观察与自评已保存。阅读行为没有改变你的能力等级。');
    } catch(error) {
      if(current?.id===id) {
        notice(error.status===409?'服务器记录已更新；你的草稿仍保留。检查后可加载服务器版本，再重新编辑。':`未保存：${error.message}。本页草稿仍保留。`,true);
        if(error.status===409) document.getElementById('gateway-reload').hidden=false;
      }
    } finally {
      busy=false;
      const button=document.getElementById('gateway-save');
      if(button) button.disabled=!host.canWrite();
    }
  }
  function links(skillId) {
    const matches=catalog.filter(item=>item.skill_ids.includes(skillId));
    return matches.length?`<section class="skill-gateway-entry"><p class="eyebrow">把相关技能连起来理解</p>${matches.map(gateway=>`<button type="button" class="gateway-entry" data-open-gateway="${esc(gateway.id)}"><span><strong>${esc(gateway.title)}</strong><span>${esc(gateway.question)}</span></span><span class="gateway-entry-action">学习原理 ↗</span></button>`).join('')}</section>`:'';
  }
  function init(data, options) {
    catalog=data.gateways || []; sources=new Map((data.gateway_sources || []).map(item=>[item.id,item])); host=options;
    dialog=document.getElementById('gateway-dialog');
    const index=document.getElementById('gateway-index');
    index.hidden=!catalog.length;
    index.innerHTML=`<div class="section-heading"><div><p class="eyebrow">LEARN TO SEE</p><h2>从一个问题，换一种看法</h2></div><p class="section-note">三条深入学习的入口。先试着观察，再展开原理；也可以直接跳到新场景。</p></div><div class="gateway-index-list">${catalog.map((gateway,i)=>`<button type="button" class="gateway-entry" data-open-gateway="${esc(gateway.id)}"><span class="gateway-index-number">0${i+1}</span><span><strong>${esc(gateway.title)}</strong><span>${esc(gateway.question)}</span></span><span aria-hidden="true">↗</span></button>`).join('')}</div>`;
    dialog.addEventListener('cancel',event=>{event.preventDefault();close();});
    dialog.addEventListener('click',event=>{
      const target=event.target;
      if(target.id==='gateway-close') close();
      const chapter=target.closest('[data-gw-section]');
      if(chapter&&current) {
        const draft=getDraft(current.id); draft.last_section=chapter.dataset.gwSection;
        const section=document.getElementById(`gw-${draft.last_section}`);
        section.scrollIntoView({block:'start',behavior:'instant'}); section.focus({preventScroll:true}); remember();
      }
      const choice=target.closest('[data-gw-choice]');
      if(choice&&current) {
        const draft=getDraft(current.id), id=choice.dataset.gwChoice;
        draft.answers[id]=choice.dataset.value; draft.dirty=true;
        document.getElementById(`gw-answer-${id}`).value=choice.dataset.value;
        dialog.querySelectorAll(`[data-gw-choice="${id}"]`).forEach(button=>button.setAttribute('aria-pressed',String(button===choice))); remember();
      }
      const skill=target.closest('[data-gw-skill]');
      if(skill) {const id=skill.dataset.gwSkill;close(false);host.navigate(id);}
      if(target.id==='gateway-reload'&&current) {
        const id=current.id; drafts.delete(id); try{sessionStorage.removeItem(key(id));}catch{}
        render();document.getElementById('gw-reflect').scrollIntoView({block:'start'});notice('已加载服务器记录；请核对后编辑。');
      }
    });
    dialog.addEventListener('input',event=>{
      if(!current)return;
      const draft=getDraft(current.id), target=event.target;
      if(target.dataset.gwAnswer) {draft.answers[target.dataset.gwAnswer]=target.value;draft.dirty=true;remember();notice('有未保存的草稿；关闭或切换入口会保留在本标签页。');}
    });
    dialog.addEventListener('change',event=>{
      if(event.target.id==='gateway-switch') open(event.target.value);
      if(event.target.id==='gateway-stage'&&current) {const draft=getDraft(current.id);draft.stage=event.target.value;draft.dirty=true;document.getElementById('gateway-stage-note').textContent=notes[draft.stage];remember();notice('自评尚未保存。');}
    });
    document.addEventListener('click',event=>{const button=event.target.closest('[data-open-gateway]');if(button)open(button.dataset.openGateway,button);});
    window.addEventListener('pagehide',remember);
  }
  return {init,links,close,onRouteChange:()=>{if(dialog?.open)close(false);},isOpen:()=>!!dialog?.open};
})();
