'use strict';
/* Static teaching reader. Routes, revisions and private writes belong to learning.js. */
(() => {
  'use strict';
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const safeId = value => /^[a-z][a-z0-9-]{0,100}$/.test(String(value || ''));
  const url = value => { try { const parsed = new URL(value); return parsed.protocol === 'https:' ? parsed.href : ''; } catch { return ''; } };
  const sourceLink = (source, label) => url(source?.url) ? `<a href="${esc(url(source.url))}" target="_blank" rel="noopener noreferrer">${esc(label || source.author)}</a>` : esc(label || source?.author || '来源');
  let returnFocus = null, wiredDialog = false;
  function contentFor(skill, atlas) {
    const content = atlas.learning_content || {}, allNotes = content.notes || [];
    const trainings = (content.trainings || []).filter(item => item.skill_ids.includes(skill.id));
    const required = new Set(trainings.flatMap(item => item.note_ids));
    const notes = allNotes.filter(item => item.skill_ids.includes(skill.id) || required.has(item.id));
    return {content, notes, trainings, sources:new Map((content.sources || []).map(item => [item.id,item])), media:new Map((content.media || []).map(item => [item.id,item]))};
  }
  function mediaFigure(item, source) {
    if (!item || !safeId(item.id)) return '';
    return `<figure class="learning-media"><button type="button" class="learning-media-open" data-teaching-media="${esc(item.id)}" aria-label="放大：${esc(item.alt)}"><img src="/api/learning-note-media/${esc(item.id)}" alt="${esc(item.alt)}" loading="lazy"></button><p class="learning-media-unavailable" hidden>图片暂不可读 · 可从下方来源回看</p><figcaption>${esc(item.caption)}<span>${sourceLink(source)} · ${esc(item.position)}</span></figcaption></figure>`;
  }
  function noteCard(note, ctx) {
    const related = ctx.trainings.filter(item => item.note_ids.includes(note.id));
    return `<article class="knowledge-note" id="learning-note-${esc(note.id)}" data-learning-note="${esc(note.id)}" tabindex="-1"><h3>${esc(note.title)}</h3><p class="note-lead">${esc(note.lead)}</p><div class="learning-media-grid">${note.media_ids.map(id => mediaFigure(ctx.media.get(id),ctx.sources.get(ctx.media.get(id)?.source_id))).join('')}</div>${note.paragraphs.map(text => `<p>${esc(text)}</p>`).join('')}${note.memory?`<p class="note-memory">${esc(note.memory)}</p>`:''}<div class="related-training">${related.map(item => `<button type="button" data-learning-training-target="${esc(item.id)}">练一遍：${esc(item.title)} <span aria-hidden="true">→</span></button>`).join('')}</div><details class="note-citations"><summary>出处与回看</summary>${note.citations.map(item => { const source=ctx.sources.get(item.source_id); return `<p>${sourceLink(source)} · ${esc(item.position)}<br>${esc(item.detail)}<br><small>${esc(source?.inspection || '')}</small></p>`; }).join('')}</details></article>`;
  }
  function trainingCard(item, ctx) {
    const notes = item.note_ids.map(id => ctx.notes.find(note => note.id===id)).filter(Boolean);
    return `<article class="training-note" id="learning-training-${esc(item.id)}" data-learning-training="${esc(item.id)}" tabindex="-1"><h3>${esc(item.title)}</h3><div class="training-basis"><span>依据笔记</span>${notes.map(note => `<button type="button" data-learning-note-target="${esc(note.id)}">${esc(note.title)} ↗</button>`).join('')}</div><ol>${item.steps.map(text => `<li>${esc(text)}</li>`).join('')}</ol><div class="training-check"><h4>拍完看什么</h4><ul>${item.checks.map(text => `<li>${esc(text)}</li>`).join('')}</ul></div><div class="training-footer"><small>${item.basis==='source_exercise'?'原作者练习':'根据笔记设计的训练'}</small><button type="button" data-training-record="${esc(item.id)}">记下这次训练</button></div></article>`;
  }
  function render(skill, atlas) {
    const ctx = contentFor(skill,atlas);
    const fallback = `<article id="learning-note-existing" class="knowledge-note existing-point" tabindex="-1"><h3>现有要点</h3><p class="note-lead">${esc(skill.capability || '')}</p>${skill.failure_modes?.length?`<h4>留意这些情况</h4><ul>${skill.failure_modes.map(text=>`<li>${esc(text)}</li>`).join('')}</ul>`:''}<button type="button" data-learning-training-target="existing">去训练 →</button><p class="existing-reading-hint">图文笔记待补充。已有教程与出处见下方资料区。</p></article>`;
    const existingTraining = `<article id="learning-training-existing" class="training-note" tabindex="-1"><h3>试拍与比较</h3><div class="training-basis"><span>依据</span><button type="button" data-learning-note-target="existing">本技能现有要点 ↗</button></div><p>${esc(skill.practice || '先阅读本技能要点，选择一个实际画面进行比较。')}</p>${skill.acceptance?.length?`<div class="training-check"><h4>拍完看什么</h4><ul>${skill.acceptance.map(text=>`<li>${esc(text)}</li>`).join('')}</ul></div>`:''}<div class="training-footer"><small>${skill.practice_basis==='source_exercise'?'原作者练习':'原有项目训练'}</small><button type="button" data-training-record="existing">记下这次训练</button></div></article>`;
    return `<div class="learning-reader"><div class="learning-tabs" role="tablist" aria-label="学习与训练"><button id="learning-notes-tab" type="button" role="tab" aria-selected="true" aria-controls="skill-learning-notes" data-learning-panel="notes">学习笔记${ctx.notes.length?` <span>${ctx.notes.length}</span>`:''}</button><button id="learning-training-tab" type="button" role="tab" tabindex="-1" aria-selected="false" aria-controls="skill-practice" data-learning-panel="training">训练${ctx.trainings.length?` <span>${ctx.trainings.length}</span>`:''}</button></div><section id="skill-learning-notes" role="tabpanel" aria-labelledby="learning-notes-tab">${ctx.notes.length?`<nav class="note-index" aria-label="知识点">${ctx.notes.map(note=>`<button type="button" data-learning-note-target="${esc(note.id)}">${esc(note.title)}</button>`).join('')}</nav>${ctx.notes.map(note=>noteCard(note,ctx)).join('')}${ctx.trainings.length?'':fallback}`:fallback}</section><section id="skill-practice" role="tabpanel" aria-labelledby="learning-training-tab" hidden>${ctx.trainings.length?ctx.trainings.map(item=>trainingCard(item,ctx)).join(''):existingTraining}</section></div>`;
  }
  function mount(container, skill, atlas, onRecord) {
    const root = container.querySelector('.learning-reader'), ctx=contentFor(skill,atlas);
    if (!root) return;
    function show(panel, target, focusTab=false) {
      const notes = panel==='notes';
      root.querySelector('#skill-learning-notes').hidden=!notes;
      root.querySelector('#skill-practice').hidden=notes;
      root.querySelectorAll('[role="tab"]').forEach(tab=>{const selected=tab.dataset.learningPanel===panel; tab.setAttribute('aria-selected',String(selected));tab.tabIndex=selected?0:-1;if(selected && focusTab)tab.focus();});
      if (target) { const item=document.getElementById(`learning-${notes?'note':'training'}-${target}`);if(item && root.contains(item)){item.scrollIntoView({behavior:'instant',block:'start'});item.focus({preventScroll:true});} }
    }
    root.addEventListener('click',event=>{
      const tab=event.target.closest('[data-learning-panel]');if(tab){show(tab.dataset.learningPanel);return;}
      const note=event.target.closest('[data-learning-note-target]');if(note){show('notes',note.dataset.learningNoteTarget);return;}
      const training=event.target.closest('[data-learning-training-target]');if(training){show('training',training.dataset.learningTrainingTarget);return;}
      const record=event.target.closest('[data-training-record]');if(record){const item=ctx.trainings.find(item=>item.id===record.dataset.trainingRecord);const title=item?.title || '试拍与比较';const basis=item?item.note_ids.map(id=>ctx.notes.find(note=>note.id===id)?.title).filter(Boolean).join('、'):'本技能现有要点';onRecord({title,basis,trigger:record});return;}
      const photo=event.target.closest('[data-teaching-media]');if(photo){const img=photo.querySelector('img');if(!img?.naturalWidth)return;returnFocus=photo;document.getElementById('learning-image').src=img.src;document.getElementById('learning-image').alt=img.alt;document.getElementById('learning-image-caption').textContent=photo.closest('figure').querySelector('figcaption').textContent;document.getElementById('learning-image-dialog').showModal();document.getElementById('learning-image-close').focus();}
    });
    root.addEventListener('keydown',event=>{const tab=event.target.closest('[role="tab"]');if(!tab || !['ArrowLeft','ArrowRight','Home','End'].includes(event.key))return;event.preventDefault();show(event.key==='Home'?'notes':event.key==='End'?'training':tab.dataset.learningPanel==='notes'?'training':'notes',null,true);});
    root.querySelectorAll('.learning-media img').forEach(img=>{
      const unavailable=()=>{img.hidden=true;img.closest('button').disabled=true;img.closest('figure').querySelector('.learning-media-unavailable').hidden=false;};
      img.addEventListener('error',unavailable);if(img.complete && !img.naturalWidth)unavailable();
    });
    if (!wiredDialog) {
      wiredDialog=true;const dialog=document.getElementById('learning-image-dialog');
      document.getElementById('learning-image-close').addEventListener('click',()=>dialog.close());
      dialog.addEventListener('click',event=>{if(event.target===dialog)dialog.close();});
      dialog.addEventListener('close',()=>{document.getElementById('learning-image').removeAttribute('src');if(returnFocus?.isConnected)returnFocus.focus({preventScroll:true});});
    }
  }
  function onRouteChange() { const dialog=document.getElementById('learning-image-dialog');if(dialog?.open)dialog.close(); }
  window.LearningContent={render,mount,onRouteChange,isOpen:()=>Boolean(document.getElementById('learning-image-dialog')?.open)};
})();

(() => {
  const $ = id => document.getElementById(id);
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const STATUSES = ['unassessed','unstarted','learning','practicing','field_verified','mastered'];
  const STATUS_LABEL = {unassessed:'未评估',unstarted:'未开始',learning:'学习中',practicing:'正在练',field_verified:'实拍验证',mastered:'已掌握',unavailable:'状态不可读'};
  const STATUS_NOTE = {unassessed:'状态尚未由你评估。',unstarted:'由你标记为尚未开始。',learning:'由你标记为正在学习。',practicing:'由你标记为正在练习。',field_verified:'由你确认已在实拍中验证。',mastered:'由你确认已掌握。'};
  const api = {
    atlas:'/static/learning-atlas.json', state:'/api/learning-state', session:'/api/session',
    preview:'/api/learning-preview', photos:'/api/learning-state'
  };
  let atlas = null, state = {revision:0,skills:{}}, csrf = '', sessionReady = false, stateReady = false;
  let assets = [], activeSkill = null, returnFocus = null, photoReturnFocus = null, searchTimer = 0, recent = [];
  let profileWriteInFlight = false, recordWriteInFlight = false, dialogPhotoSaved = '', recordDialogSkill = null;
  let gatewayWriteInFlight = false;
  let profileBasis = null;
  const gateways = window.LearningGateways;
  const learningContent = window.LearningContent;
  const profileValues = record => ({status:record.status || 'unassessed', weak:!!record.weak, focus:!!record.focus, notes:record.notes || ''});
  const maps = {domains:new Map(),modules:new Map(),skills:new Map(),sources:new Map()};
  const canWrite = () => stateReady && sessionReady && !!csrf;
  const canEditProfile = () => canWrite() && !profileWriteInFlight && !recordWriteInFlight && !gatewayWriteInFlight;

  function errorText(body, fallback) {
    return typeof body?.detail === 'string' ? body.detail : typeof body?.message === 'string' ? body.message : fallback;
  }
  async function responseJson(response) {
    let body = {};
    try { body = await response.json(); } catch {}
    if (!response.ok) throw Object.assign(new Error(errorText(body, `请求失败（${response.status}）`)), {status:response.status});
    return body;
  }
  function statusOf(skillId) { return stateReady ? (state.skills?.[skillId]?.status || 'unassessed') : 'unavailable'; }
  function recordOf(skillId) { return state.skills?.[skillId] || {status:'unassessed',weak:false,focus:false,logs:[],photos:[]}; }
  function statusSelect(value, id='skill-status') {
    if (!canWrite()) return `<select id="${id}" aria-label="我的学习状态" disabled><option value="${value}">${stateReady?STATUS_LABEL[value]:'个人记录不可读'}</option></select>`;
    return `<select id="${id}" aria-label="我的学习状态"${canEditProfile()?'':' disabled'}>${STATUSES.map(status => `<option value="${status}"${status===value?' selected':''}>${STATUS_LABEL[status]}</option>`).join('')}</select>`;
  }
  function safeExternal(url) {
    try { const parsed = new URL(url); return ['http:','https:'].includes(parsed.protocol) ? parsed.href : ''; } catch { return ''; }
  }
  function sourceAccess(value) {
    return ({full_text:'已读全文',partial_text:'已读部分正文',index_only:'仅目录/索引',metadata_only:'仅元数据',syllabus:'课程目录',video_unwatched:'未观看视频',unavailable:'无法访问'})[value] || value || '';
  }
  function evidenceScope(value) {
    return ({direct:'直接文本依据',adapted:'有限迁用',discovery_only:'发现线索（不支持技能结论）',method:'方法说明',inferred:'推断'})[value] || value || '';
  }
  function claimRelation(value) {
    if (value === 'direct') return '直接支持';
    if (value === 'discovery_only') return '发现线索，不支持技能结论';
    if (typeof value === 'string' && value.startsWith('adapted')) return '有限迁用，不能视为同一专题的交叉印证';
    return value || '';
  }
  function route(kind, id='') { return kind === 'map' ? '#map' : `#${kind}=${encodeURIComponent(id)}`; }
  function findSkill(id) { return maps.skills.get(id); }
  function readRecent() {
    try { const value = JSON.parse(sessionStorage.getItem('learning-atlas-recent') || '[]');
      return Array.isArray(value) ? [...new Set(value.filter(id => maps.skills.has(id) || maps.modules.has(id) || maps.domains.has(id)))].slice(0,8) : [];
    } catch { return []; }
  }
  function saveRecent(id) {
    recent = [id,...recent.filter(item => item !== id)].slice(0,8);
    try { sessionStorage.setItem('learning-atlas-recent', JSON.stringify(recent)); } catch {}
  }
  function allModules(domain) { return (domain.module_ids || []).map(id => maps.modules.get(id)).filter(Boolean); }
  function moduleSkills(module) { return (module.skill_ids || []).map(id => maps.skills.get(id)).filter(Boolean); }
  function currentDomainForModule(module) { return maps.domains.get(module.domain_id); }
  function domainCover(domain) {
    if (!assets.length || !Number.isInteger(domain.cover_index)) return null;
    return assets[((domain.cover_index % assets.length) + assets.length) % assets.length];
  }
  function stateNotice(message, kind='') {
    const node = $('state-notice');
    node.textContent = message;
    node.dataset.kind = kind;
  }
  function detailNotice(message, isError=false) {
    const node = $('skill-save-message');
    if (node) { node.textContent = message; node.dataset.error = String(isError); }
  }
  function setProfileControlsDisabled(disabled) {
    ['skill-status','skill-weak','skill-focus','skill-notes','notes-save','record-open'].forEach(id=>{
      const control=$(id); if(control) control.disabled=disabled || !canEditProfile();
    });
    document.querySelectorAll('[data-training-record]').forEach(control=>{control.disabled=disabled || !canEditProfile();});
  }
  function showMainError(message) {
    $('load-error').hidden = false;
    $('load-error').textContent = message;
  }
  function buildMaps() {
    maps.domains = new Map((atlas.domains || []).map(item => [item.id,item]));
    maps.modules = new Map((atlas.modules || []).map(item => [item.id,item]));
    maps.skills = new Map((atlas.skills || []).map(item => [item.id,item]));
    maps.sources = new Map((atlas.sources || []).map(item => [item.id,item]));
  }
  function renderDomainGrid() {
    $('domain-grid').innerHTML = (atlas.domains || []).map((domain,index) => {
      const image = domainCover(domain);
      const count = allModules(domain).reduce((sum,module) => sum + (module.skill_ids || []).length,0);
      return `<article class="domain-card" data-domain-card="${esc(domain.id)}">
        <a class="domain-link" data-domain="${esc(domain.id)}" href="${route('domain',domain.id)}" aria-label="浏览领域：${esc(domain.name)}">
          <div class="domain-image">${image ? `<img src="${esc(image.src)}" width="${Number(image.width)||0}" height="${Number(image.height)||0}" alt="" loading="${index<4?'eager':'lazy'}">` : '<span class="domain-placeholder">FIELD IMAGE</span>'}</div>
          <div class="domain-label"><h3>${esc(domain.name)}</h3><span>${String(index+1).padStart(2,'0')} / ${allModules(domain).length}</span></div>
          <p class="domain-desc">${esc(domain.description || '')}</p>
        </a>
        <span class="sr-only">${count} 项能力</span>
      </article>`;
    }).join('');
  }
  function renderNextPractice() {
    if (!stateReady) {
      $('next-practice').innerHTML = '<p class="eyebrow">NEXT PRACTICE</p><h2>个人学习记录暂不可读</h2><p>现在不能安全地依据你的重点或薄弱项推荐练习。解锁私人参考库后再查看。</p><a href="/">打开拍摄参考</a>';
      return;
    }
    const focused = (atlas.skills || []).find(skill => recordOf(skill.id).focus);
    const weak = (atlas.skills || []).find(skill => !focused && recordOf(skill.id).weak);
    const firstCore = (atlas.skills || []).find(skill => skill.relevance === 'core' && statusOf(skill.id) === 'unassessed');
    const candidate = focused || weak || firstCore;
    const box = $('next-practice');
    if (!candidate) {
      box.innerHTML = '<p class="eyebrow">NEXT PRACTICE</p><h2>从一个具体问题开始</h2><p>可以搜索现场遇到的困难，或打开一个领域，自己选择想研究的能力。</p><a href="#map">浏览能力领域</a>';
      return;
    }
    const reason = focused ? '按你标记的当前重点推荐' : weak ? '按你标记的薄弱项推荐' : '首次评估邀请，尚未判断你的水平。';
    box.innerHTML = `<p class="eyebrow">NEXT PRACTICE · ${focused?'你的重点':weak?'你的薄弱项':'核心能力邀请'}</p><h2>${esc(candidate.skill_name)}</h2><p>${esc(reason)}</p><a class="skill-open" data-skill="${esc(candidate.id)}" href="${route('skill',candidate.id)}">打开能力记录</a>`;
  }
  function renderMine(filter = '') {
    const value = filter.startsWith('status:') ? filter.slice(7) : filter;
    $('mine-status-filter').value = value;
    $('mine-status-filter').disabled = !stateReady;
    document.querySelectorAll('[data-mine-filter]').forEach(button => {
      button.disabled = !stateReady;
      button.setAttribute('aria-pressed',String(button.dataset.mineFilter === value));
    });
    if (!stateReady) {
      $('mine-results').innerHTML = '<p class="empty-result">个人记录暂不可读；请解锁私人参考库后再查看这些筛选。</p>';
      return;
    }
    const records = (atlas.skills || []).filter(skill => {
      const record = recordOf(skill.id);
      if (value === 'focus') return !!record.focus;
      if (value === 'weak') return !!record.weak;
      if (STATUSES.includes(value)) return statusOf(skill.id) === value;
      return false;
    });
    $('mine-results').innerHTML = records.length ? records.map(skill => skillResult(skill)).join('') : '<p class="empty-result">这里还没有符合条件的项目。个人标记只按你的选择更新。</p>';
  }
  function skillResult(skill) {
    const record = recordOf(skill.id);
    return `<a class="result-row skill-open" data-skill="${esc(skill.id)}" href="${route('skill',skill.id)}"><span class="result-kind">${esc(STATUS_LABEL[statusOf(skill.id)])}${record.focus?' · 当前重点':''}${record.weak?' · 薄弱项':''}</span><span><strong>${esc(skill.skill_name)}</strong><p>${esc(skill.capability || '')}</p></span><span aria-hidden="true">↗</span></a>`;
  }
  function renderRecent() {
    const items = recent.map(id => findSkill(id)).filter(Boolean);
    $('recent-list').innerHTML = items.length ? items.map(skill => `<a class="recent-link skill-open" data-skill="${esc(skill.id)}" href="${route('skill',skill.id)}">${esc(skill.skill_name)}</a>`).join('') : '<p>打开一个技能页后，会在这里保留最近访问入口。</p>';
  }
  function renderDomain(id) {
    const domain = maps.domains.get(id);
    if (!domain) return false;
    $('domain-crumb').textContent = domain.name;
    $('domain-module-count').textContent = `${allModules(domain).length} 个模块`;
    const cover = domainCover(domain);
    $('domain-hero').innerHTML = `<div><p class="eyebrow">FIELD ${String((atlas.domains||[]).indexOf(domain)+1).padStart(2,'0')} / ${String(atlas.domains.length).padStart(2,'0')}</p><h1 id="domain-title" tabindex="-1">${esc(domain.name)}</h1><p>${esc(domain.description || '')}</p></div><p class="domain-hero-meta">${cover ? '图片用于视觉导航<br>未作像素核验，不作技能证据' : '尚无可用的图片预览'}</p>`;
    $('module-list').innerHTML = allModules(domain).map((module,index) => `<a class="module-row module-link" data-module="${esc(module.id)}" href="${route('module',module.id)}"><span class="module-number">${String(index+1).padStart(2,'0')}</span><span><h3>${esc(module.name)}</h3><p>${moduleSkills(module).length} 项技能</p></span><span class="arrow" aria-hidden="true">→</span></a>`).join('');
    return true;
  }
  function renderModule(id) {
    const module = maps.modules.get(id);
    const domain = module && currentDomainForModule(module);
    if (!module || !domain) return false;
    $('module-domain-link').textContent = domain.name;
    $('module-domain-link').href = route('domain',domain.id);
    $('module-crumb').textContent = module.name;
    $('module-title').textContent = module.name;
    $('module-intro').textContent = `${domain.name} · 选一项技能，看笔记或开始训练。`;
    renderSkillList(module);
    return true;
  }
  function renderSkillList(module) {
    let skills = moduleSkills(module);
    $('status-filter').disabled = !stateReady;
    const filter = $('status-filter').value;
    if (filter && stateReady) skills = skills.filter(skill => statusOf(skill.id) === filter);
    $('skill-count').textContent = `${skills.length} 项能力`;
    $('skill-list').innerHTML = skills.length ? skills.map(skill => {
      const record = recordOf(skill.id), status = statusOf(skill.id);
      return `<article class="skill-row" data-status="${esc(status)}" data-skill-row="${esc(skill.id)}">
        <a class="skill-open" data-skill="${esc(skill.id)}" href="${route('skill',skill.id)}"><h3>${esc(skill.skill_name)}</h3><p>${esc(skill.capability || '')}</p></a>
        <div class="skill-markers">${record.weak?'<span class="marker active">薄弱项</span>':''}${record.focus?'<span class="marker active">当前重点</span>':''}</div>
        <span class="status-label">${esc(STATUS_LABEL[status])}</span>
      </article>`;
    }).join('') : '<p class="empty-result">这个状态下暂时没有技能。</p>';
  }
  function renderEvidence(skill) {
    const evidence = Array.isArray(skill.evidence) ? skill.evidence : [];
    if (!evidence.length) return '<p>此技能没有可展示的直接证据记录。</p>';
    return `<div class="evidence-list">${evidence.map(item => {
      const source = maps.sources.get(item.source_id) || {};
      const href = safeExternal(source.url);
      const title = source.title || item.source_id || '来源记录';
      const text = typeof item.support === 'string' ? item.support : item.summary || '';
      return `<article class="evidence-item"><p>${esc(text)}</p><div class="evidence-meta"><span>${esc(item.locator || '')}</span><span>${esc(evidenceScope(item.scope))}</span></div><div class="evidence-meta">${href ? `<a class="source-link" href="${esc(href)}" target="_blank" rel="noopener noreferrer">${esc(title)}</a>` : `<span>${esc(title)}</span>`}${source.author?`<span>${esc(source.author)}</span>`:''}${source.access?`<span>来源访问：${esc(sourceAccess(source.access))}</span>`:''}${source.read_depth?`<details><summary>来源阅读范围</summary><p>${esc(source.read_depth)}</p></details>`:''}</div></article>`;
    }).join('')}</div>`;
  }
  function renderTutorials(skill) {
    const kinds = {article:'图文教程',video:'视频教程',course:'课程章节',paper:'研究论文',case_study:'实拍解析'};
    const access = {free:'公开免费',paid:'付费内容',preview:'仅公开预览',login_required:'需要登录'};
    const checked = {full_text:'已核对正文',page_and_description:'已核对简介，未观看',transcript:'已核对文字稿',watched:'已观看所标范围'};
    const lessons = (atlas.tutorials || []).filter(item => item.skill_ids.includes(skill.id));
    lessons.sort((a,b) => Number(a.verification.level==='page_and_description')-Number(b.verification.level==='page_and_description') || Number(a.kind==='paper')-Number(b.kind==='paper'));
    const lessonRow = (item,index) => `<article class="tutorial-row" data-tutorial="${esc(item.id)}">
      <span class="tutorial-number" aria-hidden="true">${String(index+1).padStart(2,'0')}</span><div>
      <p class="tutorial-meta">${esc(kinds[item.kind])} · ${esc(item.language)} · ${esc(access[item.access])}</p>
      <h3><a href="${esc(safeExternal(item.url))}" target="_blank" rel="noopener noreferrer">${esc(item.title)} <span aria-hidden="true">↗</span></a></h3>
      <p class="tutorial-author">${esc(item.author)}</p><p>${esc(item.summary)}</p>
      <dl class="tutorial-guide"><dt>从这里开始</dt><dd>${esc(item.start_here)}</dd><dt>看完试一遍</dt><dd>${esc(item.study_task)}</dd></dl>
      <details class="tutorial-check"><summary>${esc(checked[item.verification.level])} · 推荐理由与范围</summary><p>${esc(item.trust_reason)}</p><p>${esc(item.limitations)}</p><p>${esc(item.verification.locator)} · ${esc(item.verification.checked_at)}</p></details>
      </div></article>`;
    let content;
    if (lessons.length) {
      content=lessons.slice(0,2).map(lessonRow).join('')+(lessons.length>2?`<details class="more-tutorials"><summary>再看 ${lessons.length-2} 份延伸材料</summary>${lessons.slice(2).map((item,index)=>lessonRow(item,index+2)).join('')}</details>`:'');
    } else {
      const readings=(skill.evidence || []).map(e=>({e,source:maps.sources.get(e.source_id)})).filter(({source})=>source?.access==='full_text'&&source.eligible_for_skills!==false&&safeExternal(source.url)).slice(0,2);
      content=`<p class="tutorial-intro">这项能力尚未精选到专门教程，先从研究引用的原文读起。</p>${readings.map(({e,source},index)=>`<article class="tutorial-row original-reading"><span class="tutorial-number">${String(index+1).padStart(2,'0')}</span><div><p class="tutorial-meta">原文阅读 · ${esc(source.language || '')}</p><h3><a href="${esc(safeExternal(source.url))}" target="_blank" rel="noopener noreferrer">${esc(source.title)} ↗</a></h3><p class="tutorial-author">${esc(source.author || '')}</p><dl class="tutorial-guide"><dt>找到这一段</dt><dd>${esc(e.locator)}</dd><dt>带着问题读</dt><dd>${esc(e.support)}</dd></dl></div></article>`).join('')}`;
    }
    return `<section class="dossier-section tutorial-section" id="skill-tutorials"><p class="eyebrow">STUDY COMPANION</p><h2>配套教程</h2><p class="tutorial-intro">先学一个具体方法，再用下面的最小训练验证。推荐材料不改变你的学习状态。</p>${content}</section>`;
  }
  function renderVisualExamples(skill) {
    const examples = Array.isArray(skill.visual_examples) ? skill.visual_examples : [];
    if (!examples.length) return '<p>当前没有关联的专业图例链接。</p>';
    return `<div class="visual-examples">${examples.map(item => {
      const source = maps.sources.get(item.source_id) || {};
      const href = safeExternal(item.url || source.url);
      const review=({linked_text_only_no_pixel_review:'仅关联文本与图注；未作像素核验',pixel_reviewed:'已作像素核验'})[item.review_state] || item.review_state || '';
      return `<article class="visual-example">${href?`<a class="visual-link" href="${esc(href)}" target="_blank" rel="noopener noreferrer">${esc(source.title || item.source_id || '打开来源页面')}</a>`:`<span>${esc(source.title || item.source_id || '来源记录')}</span>`}<p>${esc(item.description || '')}</p><div class="evidence-meta"><span>${esc(review)}</span></div></article>`;
    }).join('')}</div><p class="example-warning">研究图例链接不表示已检查图片像素；封面照片也不用于支撑专业结论。</p>`;
  }
  function renderConflicts(skill) {
    const conflicts = (atlas.conflicts || []).filter(item => item.skill_ids?.includes(skill.id));
    if (!conflicts.length) return '';
    return `<section class="dossier-section"><h2>来源之间的分歧与适用范围</h2><div class="evidence-list">${conflicts.map(item => {
      const record = item.record || {};
      const positions = item.positions || record.positions || [];
      const title = item.title || record.topic || '来源范围提示';
      const description = item.description || record.description || record.detail || '';
      const resolution = item.resolution || record.resolution || record.handling || '';
      const limitation = item.limitation || record.limitation || '';
      const sources = item.source_ids || item.sources || record.source_ids || record.sources || [];
      const sourceRows = sources.map(sourceId=>{
        const source=maps.sources.get(sourceId)||{}, href=safeExternal(source.url);
        return `<li>${href?`<a class="source-link" href="${esc(href)}" target="_blank" rel="noopener noreferrer">${esc(source.title || sourceId)}</a>`:esc(source.title || sourceId)}${source.access?` · 来源访问：${esc(source.access)}`:''}${source.read_depth?` · <details><summary>阅读范围</summary><p>${esc(source.read_depth)}</p></details>`:''}</li>`;
      }).join('');
      return `<article class="evidence-item"><strong>${esc(title)}</strong>${description?`<p>${esc(description)}</p>`:''}${positions.length?`<ul>${positions.map(position=>{const sourceId=typeof position==='string'?'':position.source_id;const source=maps.sources.get(sourceId)||{};const href=safeExternal(source.url);return `<li>${typeof position==='string'?esc(position):esc(position.text || position.summary || position.position || '')}${href?` · <a class="source-link" href="${esc(href)}" target="_blank" rel="noopener noreferrer">${esc(source.title || sourceId)}</a>`:''}</li>`;}).join('')}</ul>`:''}${sourceRows?`<details><summary>关联来源</summary><ul>${sourceRows}</ul></details>`:''}${resolution?`<p>${esc(resolution)}</p>`:''}${limitation?`<p class="example-warning">${esc(limitation)} 未据此扩展为完整理论或统一规则。</p>`:''}</article>`;
    }).join('')}</div></section>`;
  }
  function renderWorkflow(skill) {
    const prereqs = Array.isArray(skill.workflow_prerequisites) ? skill.workflow_prerequisites : [];
    if (!prereqs.length) return '';
    const wanted = new Set(prereqs);
    const checklists = (atlas.project_checklists || []).filter(checklist =>
      (checklist.prerequisite_mapping?.removed_or_demoted_candidate_ids || []).some(id => wanted.has(id)));
    const checklistHtml = checklists.map(checklist => {
      const design = checklist.project_designed || {};
      const claims = (checklist.source_claims || []).map(claim => {
        const source = maps.sources.get(claim.source_id) || {}, href=safeExternal(source.url);
        return `<li>${href?`<a class="source-link" href="${esc(href)}" target="_blank" rel="noopener noreferrer">${esc(source.title || claim.source_id)}</a>`:esc(source.title || claim.source_id || '')} · ${esc(claimRelation(claim.relation))}${claim.claim?`<p>${esc(claim.claim)}</p>`:''}${claim.limitation?`<small>${esc(claim.limitation)}</small>`:''}</li>`;
      }).join('');
      return `<article class="evidence-item"><strong>${esc(checklist.title || checklist.id)}</strong>${checklist.when?`<p>${esc(checklist.when)}</p>`:''}${checklist.items?.length?`<ul>${checklist.items.map(item=>`<li>${esc(item)}</li>`).join('')}</ul>`:''}${design.sequence?`<p>项目流程：${esc(design.sequence)}</p>`:''}${design.acceptance_checks?.length?`<ul>${design.acceptance_checks.map(item=>`<li>${esc(item)}</li>`).join('')}</ul>`:''}${design.not_a_source_claim?`<p>${esc(design.not_a_source_claim)}</p>`:''}${claims?`<details><summary>来源声明与关系</summary><ul>${claims}</ul></details>`:''}</article>`;
    }).join('');
    return checklistHtml ? `<details class="dossier-section research-notes"><summary>拍摄前的流程核对</summary><p class="example-warning">以下为项目流程建议，并非统一专业标准。</p><div class="evidence-list">${checklistHtml}</div></details>` : '';
  }
  function safePhotoSrc(src) { return typeof src === 'string' && /^\/api\/learning-photos\/[0-9a-f]{64}\.(?:jpg|png|webp)$/.test(src) ? src : ''; }
  function personalPhoto(photo) {
    const src=safePhotoSrc(photo.src);
    return src?`<figure class="record-photo-figure"><button class="photo-open personal-photo-open" data-photo-id="${esc(photo.id)}" type="button" aria-label="放大个人练习照片"><img src="${esc(src)}" alt="" loading="lazy"></button><figcaption>${esc(photo.caption || '')}</figcaption></figure>`:'';
  }
  function renderRecordList(skill) {
    const record = recordOf(skill.id), logs = Array.isArray(record.logs) ? record.logs : [], photos = Array.isArray(record.photos) ? record.photos : [];
    const photoFor = id => photos.find(photo => photo.id === id);
    if (!stateReady) return '<p class="empty-records">个人记录暂不可读；解锁后才能查看已保存的内容。</p>';
    const loggedPhotoIds = new Set(logs.flatMap(log => log.photo_ids || []));
    const unlinkedPhotos = photos.filter(photo => !loggedPhotoIds.has(photo.id));
    const logHtml = logs.length ? logs.slice().reverse().map(log => {
      const date = new Date(log.created_at);
      const display = Number.isNaN(date.getTime()) ? '' : date.toLocaleString('zh-CN',{dateStyle:'medium',timeStyle:'short'});
      const attached = (log.photo_ids || []).map(photoFor).filter(Boolean);
      return `<article class="record-entry"><time>${esc(display)}</time><p>${esc(log.text)}</p>${attached.length?`<div class="record-photos">${attached.map(personalPhoto).join('')}</div>`:''}</article>`;
    }).join('') : '<p class="empty-records">还没有个人练习记录。</p>';
    const photoHtml = unlinkedPhotos.length ? `<section class="record-entry"><p>尚未关联到练习记录的个人照片</p><div class="record-photos">${unlinkedPhotos.map(personalPhoto).join('')}</div></section>` : '';
    return logHtml + photoHtml;
  }
  function renderSkill(id, options={}) {
    const skill = maps.skills.get(id);
    if (!skill) return false;
    activeSkill = skill;
    saveRecent(skill.id);
    renderRecent();
    const module = maps.modules.get(skill.module_id);
    const domain = module && currentDomainForModule(module);
    const record = recordOf(skill.id), status = statusOf(skill.id);
    profileBasis = {id:skill.id, values:profileValues(record)};
    const prereqs = (skill.prerequisites || []).map(prereq => maps.skills.get(prereq) || {id:prereq,skill_name:prereq});
    const confidence = ({high:'高',medium:'中',low:'低'})[skill.confidence] || skill.confidence || '未提供';
    const basis = ({professional_consensus:'专业来源共识',photographer_method:'摄影师方法',project_adaptation:'项目适配'})[skill.basis] || '未提供';
    $('skill-view').innerHTML = `<nav class="breadcrumbs" aria-label="面包屑"><a href="#map">能力地图</a>${domain?`<span aria-hidden="true">/</span><a href="${route('domain',domain.id)}">${esc(domain.name)}</a>`:''}${module?`<span aria-hidden="true">/</span><a href="${route('module',module.id)}">${esc(module.name)}</a>`:''}<span aria-hidden="true">/</span><span>${esc(skill.skill_name)}</span></nav>
      <header class="skill-heading"><div><p class="eyebrow">${esc(module?.name || '摄影学习')}</p><h1 id="skill-title" tabindex="-1">${esc(skill.skill_name)}</h1></div>
        <aside class="skill-controls" aria-label="我的自评"><label>我的状态${statusSelect(status)}</label><div class="toggle-row"><button id="skill-weak" class="toggle-button" type="button" aria-pressed="${Boolean(record.weak)}"${canEditProfile()?'':' disabled'}>${record.weak?'✓ ':''}薄弱项</button><button id="skill-focus" class="toggle-button" type="button" aria-pressed="${Boolean(record.focus)}"${canEditProfile()?'':' disabled'}>${record.focus?'✓ ':''}当前重点</button></div><p class="saved-indicator" id="skill-save-message">${esc(stateReady?(STATUS_NOTE[status] || ''):'个人状态暂不可读。')}</p></aside>
      </header>
      <nav class="skill-jump-links" aria-label="技能内容"><button type="button" data-section-target="skill-tutorials">资料与完整教程</button><button type="button" data-section-target="skill-research">研究依据</button><button type="button" data-section-target="skill-records">我的记录</button></nav>
      <div class="skill-columns"><div class="skill-dossier">
        ${learningContent.render(skill,atlas)}
        <details class="skill-materials"><summary>资料与完整教程</summary>
        ${gateways.links(skill.id)}
        ${renderTutorials(skill)}
        ${renderWorkflow(skill)}
        ${skill.why_it_matters?`<p class="skill-why">${esc(skill.why_it_matters)}</p>`:''}
        ${atlas.learning_content?.trainings?.some(item=>item.skill_ids.includes(skill.id)) && skill.practice?`<section class="dossier-section"><h2>原有训练</h2><p>${esc(skill.practice)}</p><p class="evidence-meta">${esc(skill.practice_basis==='source_exercise'?'原作者练习':'项目设计')}</p>${skill.acceptance?.length?`<ul>${skill.acceptance.map(item=>`<li>${esc(item)}</li>`).join('')}</ul>`:''}</section>`:''}
        <details class="dossier-section research-notes" id="skill-research"><summary>研究依据 <span>${(skill.evidence || []).length} 个来源</span></summary><p class="evidence-meta">置信度：${esc(confidence)} · 依据：${esc(basis)}</p><p class="evidence-meta">来源共识仅指所收录资料一致；项目验收不是职业认证。</p>${renderEvidence(skill)}</details>
        ${renderConflicts(skill)}
        <section class="dossier-section"><h2>关联图例与案例链接</h2>${renderVisualExamples(skill)}</section>
        <section class="dossier-section"><h2>先修能力</h2>${prereqs.length?`<ul>${prereqs.map(item=>`<li><a class="skill-open source-link" data-skill="${esc(item.id)}" href="${route('skill',item.id)}">${esc(item.skill_name)}</a></li>`).join('')}</ul>`:'<p>研究树未列出先修能力。</p>'}</section></details>
      </div><aside class="my-records" id="skill-records"><h2>我的记录</h2><p>只记录你的练习与自评，不改写专业依据。</p><form class="notes-form" id="notes-form"><label for="skill-notes">技能备注</label><textarea id="skill-notes" maxlength="12000" placeholder="记录自己的观察。"${canEditProfile()?'':' disabled'}>${esc(record.notes || '')}</textarea><button class="secondary-button" id="notes-save" type="submit"${canEditProfile()?'':' disabled'}>保存备注</button></form><button id="record-open" class="add-record" type="button"${canEditProfile()?'':' disabled'}>＋ 写一条练习记录</button><div id="record-list" class="record-list">${renderRecordList(skill)}</div></aside></div>`;
    $('skill-status').addEventListener('change', event => updateProfile(skill.id,{status:event.target.value},'状态已保存。'));
    $('skill-weak').addEventListener('click', event => updateProfile(skill.id,{weak:!recordOf(skill.id).weak},'薄弱项标记已保存。'));
    $('skill-focus').addEventListener('click', event => updateProfile(skill.id,{focus:!recordOf(skill.id).focus},'当前重点标记已保存。'));
    $('notes-form').addEventListener('submit', event => { event.preventDefault(); updateProfile(skill.id,{notes:$('skill-notes').value},'备注已保存。'); });
    $('record-open').addEventListener('click', () => openRecordDialog(skill));
    learningContent.mount($('skill-view'),skill,atlas,training=>openRecordDialog(skill,training));
    $('skill-view').querySelectorAll('[data-training-record]').forEach(button=>{button.disabled=!canEditProfile();});
    const reload = document.createElement('button');
    reload.id='skill-record-reload'; reload.type='button'; reload.className='text-link'; reload.hidden=true;
    reload.textContent='载入服务器版本（替换此技能的本页草稿）';
    $('notes-form').append(reload);
    reload.addEventListener('click',()=>{renderSkill(skill.id);$('skill-notes').focus({preventScroll:true});detailNotice('已载入服务器版本，请核对后编辑。',false);});
    if (options.focus === 'record-open') $('record-open').focus({preventScroll:true});
    return true;
  }
  function renderProblem(index) {
    const list = atlas.problem_index || [];
    const item = /^\d+$/.test(String(index)) ? list[Number(index)] : list.find(problem=>problem.id===String(index));
    if (!item) return false;
    const skillIds = Array.isArray(item.skill_ids) ? item.skill_ids : [];
    const related = skillIds.map(id => maps.skills.get(id)).filter(Boolean);
    const gapIds = Array.isArray(item.gap_ids) ? item.gap_ids : [];
    const gaps = (atlas.gaps || []).filter((gap, i) => gapIds.includes(gap.id) || gapIds.includes(String(i)));
    $('problem-view').innerHTML = `<nav class="breadcrumbs"><a href="#map">能力地图</a><span>/</span><a href="#q=${encodeURIComponent(item.problem || '')}">问题搜索</a></nav><article class="problem-panel"><p class="eyebrow">PROBLEM INDEX</p><h1 id="problem-title" tabindex="-1">${esc(item.problem || '实际问题')}</h1>${item.synonyms?.length?`<p>相关说法：${item.synonyms.map(esc).join('、')}</p>`:''}<section class="problem-matches"><p class="eyebrow">关联技能</p>${related.length?related.map(skill=>skillResult(skill)).join(''):'<p class="empty-result">研究索引未关联技能。</p>'}</section>${gaps.length?`<section class="problem-matches"><p class="eyebrow">尚待补足的资料</p>${gaps.map(gap=>`<article class="result-gap"><span class="gap-label">资料不足</span><span><strong>${esc(gap.title || gap.problem || '研究缺口')}</strong><p>${esc(gap.description || '')}</p></span></article>`).join('')}</section>`:''}<p class="problem-disclaimer">问题与技能的关联来自研究索引；当资料不足时会明确标出，不以相邻技能替代答案。</p></article>`;
    return true;
  }
  function normalized(value) { return String(value || '').toLocaleLowerCase('zh-CN'); }
  function search(query) {
    const q = normalized(query.trim());
    if (!q) { $('search-view').hidden = true; return; }
    $('search-view').hidden = false;
    $('search-summary').textContent = `搜索问题、失败表现、能力与研究缺口：${query.trim()}`;
    const results = [];
    (atlas.problem_index || []).forEach((item,index) => {
      const haystack = normalized([item.problem,...(item.synonyms || [])].join(' '));
      if (haystack.includes(q)) results.push({type:'problem',item,index});
    });
    (atlas.gaps || []).forEach((item,index) => {
      if (normalized([item.title,item.description,...(item.synonyms || [])].join(' ')).includes(q)) results.push({type:'gap',item,index});
    });
    (atlas.skills || []).forEach(item => {
      if (normalized([item.skill_name,item.capability,item.why_it_matters,...(item.failure_modes || []),...(item.search_terms || [])].join(' ')).includes(q)) results.push({type:'skill',item});
    });
    (atlas.modules || []).forEach(item => {
      if (normalized(item.name).includes(q)) results.push({type:'module',item});
    });
    (atlas.domains || []).forEach(item => {
      if (normalized([item.name,item.description].join(' ')).includes(q)) results.push({type:'domain',item});
    });
    const problems = results.filter(item=>item.type==='problem');
    const gaps = results.filter(item=>item.type==='gap');
    const skills = results.filter(item=>item.type==='skill');
    const other = results.filter(item=>['module','domain'].includes(item.type));
    const group = (name,items,render) => items.length?`<section class="result-group"><h3>${name} · ${items.length}</h3>${items.slice(0,60).map(render).join('')}</section>`:'';
    const gapRow = ({item,index}) => `<a class="result-gap" href="#gap=${index}"><span class="gap-label">资料不足</span><span><strong>${esc(item.title || item.problem || '研究缺口')}</strong><p>${esc(item.description || (item.synonyms || []).join('、'))}</p></span></a>`;
    const otherRow = entry => entry.type==='module' ? `<a class="result-row" href="${route('module',entry.item.id)}"><span class="result-kind">模块</span><span><strong>${esc(entry.item.name)}</strong></span><span>↗</span></a>` : `<a class="result-row" href="${route('domain',entry.item.id)}"><span class="result-kind">领域</span><span><strong>${esc(entry.item.name)}</strong><p>${esc(entry.item.description || '')}</p></span><span>↗</span></a>`;
    $('search-results').innerHTML = group('问题索引（优先匹配）',problems,({item,index})=>`<a class="result-row" data-problem="${index}" href="#problem=${index}"><span class="result-kind">问题 → ${item.skill_ids?.length || 0} 项技能</span><span><strong>${esc(item.problem)}</strong><p>${esc((item.synonyms || []).join(' · '))}</p></span><span>↗</span></a>`) +
      group('资料不足',gaps,gapRow) + group('技能',skills,({item})=>skillResult(item)) + group('领域与模块',other,otherRow) || '<p class="empty-result">没有匹配结果。试试缩短问题，或改用失败表现中的关键词。</p>';
  }
  async function refreshState() {
    try {
      state = await responseJson(await fetch(api.state,{credentials:'same-origin',cache:'no-store'}));
      stateReady = true;
      if (profileBasis && parseRoute().kind === 'skill' && parseRoute().id === profileBasis.id) {
        const latest=profileValues(recordOf(profileBasis.id));
        if(Object.keys(latest).some(key=>latest[key]!==profileBasis.values[key])) showProfileConflict();
      }
      stateNotice('个人学习记录已读取。','ok');
    } catch (error) {
      stateReady = false;
      stateNotice(error.status === 401 ? '请先解锁私人参考库；当前仅可浏览研究内容。' : `个人记录暂不可用：${error.message}`,'error');
      throw error;
    }
  }
  function showProfileConflict() {
    detailNotice('该技能的服务器记录已变化；请先核对服务器版本。本页草稿仍保留，未覆盖新记录。',true);
    const reload=$('skill-record-reload'); if(reload) reload.hidden=false;
  }
  async function updateProfile(skillId, updates, success) {
    if (!canWrite()) { detailNotice('私人记录尚未解锁，未保存。',true); return; }
    if (profileWriteInFlight || recordWriteInFlight || gatewayWriteInFlight) return;
    // A newer shared revision does not mean this form has seen the newer fields.
    const latest=profileValues(recordOf(skillId));
    if(profileBasis?.id===skillId && Object.keys(updates).some(key=>latest[key]!==profileBasis.values[key])) {
      showProfileConflict(); return;
    }
    profileWriteInFlight = true;
    setProfileControlsDisabled(true);
    try {
      const result = await responseJson(await fetch(`${api.state}/${encodeURIComponent(skillId)}`,{
        method:'PUT',credentials:'same-origin',headers:{'Content-Type':'application/json','X-Lab-CSRF':csrf},
        body:JSON.stringify({expected_revision:state.revision,...updates})
      }));
      state = result;
      renderNextPractice();
      const current = parseRoute();
      if (current.kind === 'skill' && current.id === skillId) {
        const profile = recordOf(skillId);
        const weakButton = $('skill-weak'), focusButton = $('skill-focus'), status = $('skill-status');
        if (weakButton) { weakButton.setAttribute('aria-pressed',String(!!profile.weak)); weakButton.textContent=`${profile.weak?'✓ ':''}薄弱项`; }
        if (focusButton) { focusButton.setAttribute('aria-pressed',String(!!profile.focus)); focusButton.textContent=`${profile.focus?'✓ ':''}当前重点`; }
        if (status && status.value !== profile.status) status.value = profile.status;
        if(profileBasis?.id===skillId) {
          const values=profileValues(profile);
          for(const key of ['status','weak','focus',...Object.keys(updates)]) profileBasis.values[key]=values[key];
        }
        detailNotice(success,false);
      }
      stateNotice('个人学习记录已保存。','ok');
      renderMine(parseRoute().kind === 'mine' ? parseRoute().id : '');
    } catch (error) {
      if (error.status === 409) {
        await refreshState().catch(()=>{});
        renderNextPractice();
        const current=parseRoute();
        if(current.kind==='skill' && current.id===skillId) showProfileConflict();
      } else {
        const current=parseRoute();
        if(current.kind==='skill' && current.id===skillId) detailNotice(`${error.message} 未覆盖当前记录。`,true);
      }
    } finally { profileWriteInFlight=false; setProfileControlsDisabled(false); }
  }
  function openRecordDialog(skill, training=null) {
    if (!canEditProfile()) { detailNotice('私人记录暂不可写，请稍后再试。',true); return; }
    recordDialogSkill = skill;
    returnFocus = training?.trigger || $('record-open');
    $('record-skill-name').textContent = skill.skill_name;
    $('record-text').value = training ? `训练：${training.title}\n依据笔记：${training.basis}\n\n我的观察：` : '';
    $('record-photo').value = '';
    $('record-caption').value = '';
    dialogPhotoSaved = '';
    $('record-message').textContent = '';
    $('record-save').disabled = false;
    $('record-dialog').showModal();
    $('record-text').focus();
  }
  function openPhotoViewer(photo, trigger) {
    const src = safePhotoSrc(photo?.src);
    if (!src) return;
    photoReturnFocus = trigger;
    $('photo-view-image').src = src;
    $('photo-view-image').alt = photo.caption || '个人练习照片';
    $('photo-caption').textContent = photo.caption || '个人练习照片';
    $('photo-dialog').showModal();
    $('photo-close').focus();
  }
  function closePhotoViewer() {
    if ($('photo-dialog').open) $('photo-dialog').close();
  }
  async function saveRecord(event) {
    event.preventDefault();
    const skill = recordDialogSkill;
    if (!skill || !stateReady || !csrf) return;
    if (recordWriteInFlight || profileWriteInFlight || gatewayWriteInFlight) return;
    const text = $('record-text').value.trim();
    if (!text) { $('record-message').textContent = '请先写下练习内容。'; $('record-text').focus(); return; }
    recordWriteInFlight = true;
    setProfileControlsDisabled(true);
    const save = $('record-save'); save.disabled = true;
    $('record-message').textContent = '正在保存…';
    let photoId = dialogPhotoSaved;
    try {
      const photo = $('record-photo').files?.[0];
      if (photo && !photoId) {
        const form = new FormData();
        form.append('expected_revision',String(state.revision));
        form.append('caption',$('record-caption').value);
        form.append('file',photo);
        state = await responseJson(await fetch(`${api.photos}/${encodeURIComponent(skill.id)}/photos`,{method:'POST',credentials:'same-origin',headers:{'X-Lab-CSRF':csrf},body:form}));
        photoId = state.skills?.[skill.id]?.photos?.at(-1)?.id || '';
        dialogPhotoSaved = photoId;
      }
      const logBody = {expected_revision:state.revision,text,...(photoId?{photo_ids:[photoId]}:{})};
      state = await responseJson(await fetch(`${api.photos}/${encodeURIComponent(skill.id)}/logs`,{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','X-Lab-CSRF':csrf},body:JSON.stringify(logBody)}));
      dialogPhotoSaved = '';
      closeRecordDialog(false);
      const current = parseRoute();
      if (current.kind === 'skill' && current.id === skill.id) {
        $('record-list').innerHTML = renderRecordList(skill);
        $('record-open').focus({preventScroll:true});
      }
      renderNextPractice();
      renderMine(parseRoute().kind === 'mine' ? parseRoute().id : '');
      stateNotice('练习记录已保存；状态仍由你单独评估。','ok');
    } catch (error) {
      if (error.status === 409) {
        await refreshState().catch(()=>{});
        $('record-message').textContent = `${dialogPhotoSaved?'照片已保存并保留，不会重复上传。':''}记录已在其他页面更新；已重新读取，请核对后再次提交。`;
      } else $('record-message').textContent = `${error.message}。未覆盖较新的记录。`;
    } finally { recordWriteInFlight=false; setProfileControlsDisabled(false); if ($('record-dialog').open) save.disabled = false; }
  }
  function closeRecordDialog(restore=true) {
    if (!$('record-dialog').open) return;
    $('record-dialog').close();
    const current = parseRoute();
    if (dialogPhotoSaved && recordDialogSkill && current.kind === 'skill' && current.id === recordDialogSkill.id && $('record-list')) {
      $('record-list').innerHTML = renderRecordList(recordDialogSkill);
    }
    if (restore && returnFocus?.isConnected) returnFocus.focus({preventScroll:true});
  }
  function parseRoute() {
    const raw = location.hash.slice(1);
    if (raw.startsWith('topic=')) {
      const legacy = new URLSearchParams(raw).get('topic');
      if (maps.domains.has(legacy)) { history.replaceState(null,'',route('domain',legacy)); return {kind:'domain',id:legacy}; }
      return {kind:'map',id:''};
    }
    if (!raw || raw === 'map') return {kind:'map',id:''};
    if (raw.startsWith('q=')) return {kind:'search',id:new URLSearchParams(raw).get('q') || ''};
    if (raw.startsWith('gap=')) return {kind:'gap',id:new URLSearchParams(raw).get('gap') || ''};
    const [kind,...rest] = raw.split('=');
    if (['domain','module','skill','problem','mine'].includes(kind)) {
      try { return {kind,id:decodeURIComponent(rest.join('='))}; } catch { return {kind:'map',id:''}; }
    }
    return {kind:'map',id:''};
  }
  function renderRoute(focus=false) {
    if (!atlas) return;
    gateways.onRouteChange();
    learningContent.onRouteChange();
    const current = parseRoute();
    const inMap = ['map','search','mine'].includes(current.kind);
    $('map-view').hidden = !inMap;
    $('map-view').setAttribute('aria-labelledby',current.kind === 'search' ? 'search-title' : current.kind === 'mine' ? 'mine-title' : 'map-title');
    document.querySelector('.masthead').hidden = current.kind !== 'map';
    document.querySelector('.mine-strip').hidden = !['map','mine'].includes(current.kind);
    $('domain-view').hidden = current.kind !== 'domain';
    $('module-view').hidden = current.kind !== 'module';
    $('skill-view').hidden = current.kind !== 'skill';
    $('problem-view').hidden = current.kind !== 'problem' && current.kind !== 'gap';
    $('home-view').hidden = current.kind !== 'map';
    $('search-view').hidden = current.kind !== 'search';
    $('mine-view').hidden = current.kind !== 'mine';
    renderMine(current.kind === 'mine' ? current.id : '');
    $('search').value = current.kind === 'search' ? current.id : '';
    let valid = true;
    if (current.kind === 'domain') valid = renderDomain(current.id);
    if (current.kind === 'module') valid = renderModule(current.id);
    if (current.kind === 'skill') valid = renderSkill(current.id);
    if (current.kind === 'problem') valid = renderProblem(current.id);
    if (current.kind === 'gap') valid = renderGap(current.id);
    if (current.kind === 'search') search(current.id);
    if (!valid) { history.replaceState(null,'','#map'); renderRoute(focus); return; }
    $('recent-panel').hidden = true;
    $('recent-toggle').setAttribute('aria-expanded','false');
    if (focus) {
      const target = current.kind==='domain' ? $('domain-title') : current.kind==='module' ? $('module-title') : current.kind==='skill' ? $('skill-title') : current.kind==='problem'||current.kind==='gap' ? $('problem-title') : current.kind==='search' ? $('search-title') : current.kind==='mine' ? $('mine-title') : $('map-title');
      // A new route begins at its heading, not at the previous page's scroll offset.
      window.scrollTo({top:0,behavior:'instant'});
      requestAnimationFrame(()=>{ if (!$('record-dialog').open) target?.focus({preventScroll:true}); });
    }
    const title = current.kind==='skill' ? `${findSkill(current.id)?.skill_name || '技能'} · 摄影学习` : current.kind==='domain' ? `${maps.domains.get(current.id)?.name || '领域'} · 摄影学习` : current.kind==='module' ? `${maps.modules.get(current.id)?.name || '模块'} · 摄影学习` : '摄影能力地图 · 摄影学习';
    document.title = title;
  }
  function renderGap(index) {
    const list = atlas.gaps || [];
    const gap = /^\d+$/.test(String(index)) ? list[Number(index)] : list.find(item=>item.id===String(index) || item.gap_id===String(index));
    if (!gap) return false;
    const ids = gap.related_skill_ids || [];
    const skills = ids.map(id=>maps.skills.get(id)).filter(Boolean);
    $('problem-view').innerHTML = `<nav class="breadcrumbs"><a href="#map">能力地图</a><span>/</span><a href="#q=${encodeURIComponent(gap.title || '')}">问题搜索</a></nav><article class="problem-panel"><p class="eyebrow">RESEARCH GAP</p><h1 id="problem-title" tabindex="-1">${esc(gap.title || '研究缺口')}</h1><p>${esc(gap.description || '')}</p>${gap.synonyms?.length?`<p>相关说法：${gap.synonyms.map(esc).join('、')}</p>`:''}<p class="problem-disclaimer">资料不足。此缺口不会自动转为相邻方法或未经证实的操作建议。</p><section class="problem-matches"><p class="eyebrow">关联技能</p>${skills.length?skills.map(skill=>skillResult(skill)).join(''):'<p class="empty-result">暂未关联技能。</p>'}</section></article>`;
    return true;
  }
  function wire() {
    document.addEventListener('click',event=>{
      const sectionLink=event.target.closest('[data-section-target]');
      if(sectionLink) {
        const section=$(sectionLink.dataset.sectionTarget);
        let ancestor=section?.parentElement;while(ancestor){if(ancestor.tagName==='DETAILS')ancestor.open=true;ancestor=ancestor.parentElement;}
        if(section?.tagName==='DETAILS') section.open=true;
        section?.scrollIntoView({behavior:'instant',block:'start'});
        section?.querySelector('textarea,summary')?.focus({preventScroll:true});
        return;
      }
      const photoButton=event.target.closest('[data-photo-id]');
      if(photoButton && activeSkill) {
        const photo=recordOf(activeSkill.id).photos?.find(item=>item.id===photoButton.dataset.photoId);
        if(photo){event.preventDefault();openPhotoViewer(photo,photoButton);return;}
      }
      const link = event.target.closest('a[href^="#"]');
      if (link && !event.ctrlKey && !event.metaKey && !event.shiftKey && !event.altKey && event.button===0) {
        if (link.classList.contains('skip-link')) { event.preventDefault(); $('main').focus(); return; }
        event.preventDefault();
        if (location.hash !== link.getAttribute('href')) history.pushState(null,'',link.getAttribute('href'));
        renderRoute(true);
        return;
      }
      const mine = event.target.closest('[data-mine-filter]');
      if (mine) { const current=parseRoute(); const same=current.kind==='mine' && current.id===mine.dataset.mineFilter; history.pushState(null,'',same?'#map':route('mine',mine.dataset.mineFilter)); renderRoute(true); }
      if (event.target.id === 'clear-search') { event.preventDefault(); history.pushState(null,'','#map'); renderRoute(true); $('search').focus(); }
      if (event.target.id === 'clear-mine') { history.pushState(null,'','#map'); renderRoute(true); }
      if (event.target.id === 'recent-toggle') {
        const panel = $('recent-panel'), opening = panel.hidden;
        if (opening) renderRecent();
        panel.hidden = !opening;
        event.target.setAttribute('aria-expanded',String(opening));
      } else if (!event.target.closest('#recent-panel')) {
        $('recent-panel').hidden = true; $('recent-toggle').setAttribute('aria-expanded','false');
      }
    });
    $('search').addEventListener('input',()=>{
      clearTimeout(searchTimer);
      searchTimer=setTimeout(()=>{
        const value=$('search').value.trim();
        history.replaceState(null,'',value?`#q=${encodeURIComponent(value)}`:'#map');
        renderRoute(false);
        window.scrollTo({top:0,behavior:'instant'});
        $('search').focus({preventScroll:true});
      },100);
    });
    $('status-filter').addEventListener('change',()=>{const routeNow=parseRoute();if(routeNow.kind==='module')renderModule(routeNow.id);});
    $('mine-status-filter').addEventListener('change',event=>{history.pushState(null,'',event.target.value?route('mine',event.target.value):'#map');renderRoute(true);});
    $('record-form').addEventListener('submit',saveRecord);
    $('record-close').addEventListener('click',closeRecordDialog);
    $('record-cancel').addEventListener('click',closeRecordDialog);
    $('record-dialog').addEventListener('close',()=>{if(returnFocus?.isConnected)returnFocus.focus({preventScroll:true});});
    $('record-dialog').addEventListener('click',event=>{if(event.target===$('record-dialog'))closeRecordDialog();});
    $('photo-close').addEventListener('click',closePhotoViewer);
    $('photo-dialog').addEventListener('close',()=>{if(photoReturnFocus?.isConnected)photoReturnFocus.focus({preventScroll:true});});
    $('photo-dialog').addEventListener('click',event=>{if(event.target===$('photo-dialog'))closePhotoViewer();});
    document.addEventListener('keydown',event=>{
      if (gateways.isOpen() || learningContent.isOpen()) return;
      if (event.key==='/' && !/INPUT|TEXTAREA|SELECT/.test(document.activeElement?.tagName)) {event.preventDefault();$('search').focus();}
      if (event.key==='Escape' && !$('recent-panel').hidden) { $('recent-panel').hidden=true;$('recent-toggle').setAttribute('aria-expanded','false');$('recent-toggle').focus(); }
    });
    window.addEventListener('popstate',()=>renderRoute(true));
    window.addEventListener('hashchange',()=>renderRoute(true));
  }
  async function boot() {
    wire();
    stateNotice('正在读取个人学习记录…');
    const [atlasResult,sessionResult,stateResult,previewResult] = await Promise.allSettled([
      fetch(api.atlas,{credentials:'same-origin',cache:'no-store'}).then(responseJson),
      fetch(api.session,{credentials:'same-origin',cache:'no-store'}).then(responseJson),
      fetch(api.state,{credentials:'same-origin',cache:'no-store'}).then(responseJson),
      fetch(api.preview,{credentials:'same-origin',cache:'no-store'}).then(responseJson)
    ]);
    if (atlasResult.status !== 'fulfilled' || !atlasResult.value || atlasResult.value.schema_version !== 1 || !Array.isArray(atlasResult.value.skills)) {
      showMainError(atlasResult.status==='rejected' ? `研究数据暂不可用：${atlasResult.reason.message}` : '研究数据格式无效。请在构建并验证学习数据包后重新加载。');
      $('home-view').hidden=true; return;
    }
    atlas=atlasResult.value; buildMaps(); recent=readRecent(); renderDomainGrid(); renderRecent();
    if (sessionResult.status==='fulfilled') { csrf=sessionResult.value.csrf || ''; sessionReady=!!csrf; }
    if (stateResult.status==='fulfilled') { state=stateResult.value; stateReady=true; stateNotice('个人学习记录已读取。','ok'); }
    else { stateReady=false; stateNotice(stateResult.reason.status===401?'请先解锁私人参考库；当前仅可浏览研究内容。':`个人记录暂不可用：${stateResult.reason.message}`,'error'); }
    if (!sessionReady && stateReady) stateNotice('个人记录可读取，但会话校验暂不可用，暂不能写入。','error');
    gateways.init(atlas, {
      record:id=>stateReady ? state.gateways?.[id] : undefined,
      revision:()=>state.revision,
      canWrite:canEditProfile,
      skillName:id=>maps.skills.get(id)?.skill_name || id,
      navigate:id=>{history.pushState(null,'',route('skill',id));renderRoute(true);},
      save:async (id,payload)=>{
        if (!canEditProfile()) throw new Error('另一个记录正在保存，或私人记录尚未解锁');
        gatewayWriteInFlight=true; setProfileControlsDisabled(true);
        try {
          state=await responseJson(await fetch(`/api/learning-gateways/${encodeURIComponent(id)}`,{
            method:'PUT',credentials:'same-origin',headers:{'Content-Type':'application/json','X-Lab-CSRF':csrf},body:JSON.stringify(payload)
          }));
          return state.revision;
        } catch(error) {
          if(error.status===409) await refreshState().catch(()=>{});
          throw error;
        } finally {gatewayWriteInFlight=false;setProfileControlsDisabled(false);}
      }
    });
    if (previewResult.status==='fulfilled' && Array.isArray(previewResult.value.items)) {
      assets=previewResult.value.items.filter(item=>typeof item.src==='string'&&/^\/api\/learning-preview\/P\d+\.(?:jpg|jpeg|png|webp|avif)$/.test(item.src)&&Number.isFinite(item.width)&&Number.isFinite(item.height));
      renderDomainGrid();
    }
    renderNextPractice();
    if (atlas.domains.length) { $('load-error').hidden=true; renderRoute(); }
    else showMainError('研究数据中没有能力领域。');
  }
  boot();
})();
