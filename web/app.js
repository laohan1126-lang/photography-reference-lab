'use strict';
const $ = id => document.getElementById(id);
const esc = value => String(value ?? '').replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char]));
const lines = text => String(text || '').split('\n').map(x => x.trim()).filter(Boolean);
const state = { csrf: '', projects: [], archivedProjects: [], project: null, view: 'references', refs: [], activeId: null, total: 0, offset: 0, limit: 60, query: '', decision: '', kind: '', epoch: 0, autoAdvance: true, busy: false, dirty: false, caps: {}, jobId: '', recycled: false, selectLast: false, focusId: null, selection: [] };
const decisions = { pending: '未选择', keep: '已保留', maybe: '待定', reject: '已淘汰' };
const statuses = { candidate: '候选 · 未核验', needs_review: '待逐图核验', needs_card: '待写资料卡', draft: '草稿 · 待确认', ready: '已确认现场卡', rejected: '已淘汰', inspiration: '灵感收藏', missing_asset: '图片缺失', blocked: '等待执行／受阻', running: '处理中', succeeded: '处理完成', failed: '执行失败', cancelled: '已取消', queued: '排队中' };
const kinds = { unknown: '尚未分类', cosplay_photo: '真人 cosplay', portrait_photo: '普通真人摄影', illustration: '角色插画', equipment: '器材图', location: '场地图', collage: '拼图', generated: 'AI 生成概念' };
const modalities = { real_person_cosplay:'真人 cosplay', real_person_portrait:'真人普通人像', game_screenshot:'游戏截图 / UI', anime_screenshot:'动画截图', official_illustration:'官方插画', fan_art:'同人插画', costume_display:'服装展示', mannequin:'假人 / 人台', product:'商品图', collage:'拼图 / 九宫格', scenery:'空场景', equipment:'器材图 / 花絮', unknown:'无法可靠判断' };
let toastTimer, modalDirty = false;


function toast(message, error = false) {
    const el = $('toast');
    el.textContent = message;
    el.className = 'toast' + (error ? ' error' : '');
    if ($('editor')?.open) {
        if (el.parentElement !== $('editor')) $('editor').appendChild(el);
    } else if (el.parentElement !== document.body) {
        document.body.appendChild(el);
    }
    el.hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => el.hidden = true, 5500);
}
function listen(root, selector, event, fn) { const target = typeof root === 'string' ? $(root) : root; target.querySelectorAll(selector).forEach(node => node.addEventListener(event, e => Promise.resolve(fn(e, node)).catch(showError))); }
function showError(error) { console.error(error); toast(error.message || '操作失败', true); }
async function api(path, options = {}) {
    const headers = new Headers(options.headers || {});
    if (state.csrf)
        headers.set('X-Lab-CSRF', state.csrf);
    if (options.body && !(options.body instanceof FormData) && typeof options.body !== 'string') {
        headers.set('Content-Type', 'application/json');
        options.body = JSON.stringify(options.body);
    }
    const response = await fetch(path, { ...options, headers, credentials: 'same-origin' });
    if (!response.ok) {
        let data;
        try {
            data = await response.json();
        }
        catch {
            data = { message: `HTTP ${response.status}` };
        }
        ;
        if (response.status === 401 && path !== '/api/session')
            lockScreen();
        const extra = Array.isArray(data.details) ? data.details.map(x => x.message || x.reason || x.code || '').filter(Boolean).join('；') : '';
        throw new Error((data.message || `HTTP ${response.status}`) + (extra ? '：' + extra : ''));
    }
    if (options.download)
        return response.blob();
    return response.json();
}
function lockScreen() { if (state.noAuth) return; LibraryDiscovery.reset(); closeModal(); $('lightbox').close(); $('lightbox-image')?.removeAttribute('src'); state.dirty = false; modalDirty = false; state.csrf = ''; state.projects = []; state.project = null; state.refs = []; state.epoch++; $('application').hidden = true; $('login-screen').hidden = false; $('view').replaceChildren(); $('login-token').focus(); }
function current() { return state.refs.find(x => x.id === state.activeId) || state.refs[0] || null; }
function label(text, name, value = '', type = 'text', extra = '') { return `<label>${esc(text)}<input aria-label="${esc(text)}" name="${name}" type="${type}" value="${esc(value)}" ${extra}></label>`; }
function area(text, name, value = '', extra = '') { return `<label>${esc(text)}<textarea aria-label="${esc(text)}" name="${name}" ${extra}>${esc(value)}</textarea></label>`; }
function select(text, name, choices, value) { return `<label>${esc(text)}<select aria-label="${esc(text)}" name="${name}">${Object.entries(choices).map(([key, caption]) => `<option value="${esc(key)}" ${key === value ? 'selected' : ''}>${esc(caption)}</option>`).join('')}</select></label>`; }
function check(text, name, value = false) { return `<label class="check"><input name="${name}" type="checkbox" ${value ? 'checked' : ''}><span>${esc(text)}</span></label>`; }
function values(form) { const data = Object.fromEntries(new FormData(form)); form.querySelectorAll('input[type=checkbox]').forEach(input => data[input.name] = input.checked); return data; }
function badge(text, style = '') { return `<span class="badge ${esc(style)}">${esc(text)}</span>`; }
function empty(title, message, action = '', actionId = '') { return `<section class="empty-state"><span class="empty-mark">R.</span><h2>${esc(title)}</h2><p>${esc(message)}</p>${action ? `<button class="primary" id="${actionId}">${esc(action)}</button>` : ''}</section>`; }
function modal(title, content) { modalDirty = false; $('editor-title').textContent = title; $('editor-content').innerHTML = content; if (!$('editor').open)
    $('editor').showModal(); return $('editor-content'); }
function closeModal() {
    modalDirty = false;
    $('editor').close();
    if ($('toast') && $('toast').parentElement !== document.body) {
        document.body.appendChild($('toast'));
    }
}
function manualCloseModal() { if ($('editor-content').querySelector('[data-pending]')) { toast('正在保存，请勿重复操作'); return; } if (!modalDirty || window.confirm('对话框有未保存的内容，仍然关闭？'))
    closeModal(); }
function requireSaved() { if (state.dirty) {
    toast('请先保存当前审美反馈，再进行核验或制作。');
    return false;
} return true; }
function formSubmit(root, handler) {
    const form = root.querySelector('form');
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const button = form.querySelector('[type=submit]');
        button.disabled = true;
        form.dataset.pending = "true";
        const progress = form.querySelector('#import-progress');
        if (progress) { progress.textContent = ""; progress.className = ""; }
        try {
            await handler(values(form), form);
        } catch (error) {
            if (progress) {
                progress.textContent = error.message || "操作失败";
                progress.className = "error-text";
            }
            showError(error);
        } finally {
            button.disabled = false;
            delete form.dataset.pending;
        }
    });
}
async function download(path, name, body) { const blob = await api(path, { method: body ? 'POST' : 'GET', body, download: true }); const url = URL.createObjectURL(blob); const a = document.createElement('a'); a.href = url; a.download = name; a.click(); setTimeout(() => URL.revokeObjectURL(url), 15000); }
async function copy(text) { try {
    await navigator.clipboard.writeText(text);
    toast('已复制');
}
catch {
    modal('复制内容', `<pre>${esc(text)}</pre>`);
} }

const projectViews = ['references', 'selected', 'field', 'filtered', 'recycle', 'events'];
const imageViews = ['references', 'selected', 'field', 'filtered', 'recycle', 'inspiration'];
const stages = {candidate:'先选出你喜欢的', selected:'角色参考 · 尚未制卡', waiting_analysis:'待 Agent 接手', analyzing:'Agent 分析中', analyzed:'分析完成 · 请看结论', card_draft:'资料卡草稿 · 待你检查', ready:'已确认现场卡', inspiration:'已存入我的审美库', rejected:'已淘汰 · 可以恢复', detached:'已移出当前项目 · 可以恢复'};
function scopeKey() { return projectViews.includes(state.view) ? `${state.view}:${state.project?.id || ''}` : state.view; }
function rememberNavigation() {
    const q = new URLSearchParams({view:state.view, project:state.project?.id || '', ref:state.activeId || '', offset:state.offset, q:state.query, decision:state.decision, kind:state.kind, job:state.jobId || '', recycled:state.recycled?'1':'0'});
    LibraryDiscovery.navigationParams(q);
    try { history.replaceState(null, '', '#'+q); } catch { /* Sandboxed component tests need no browser history. */ }
}
function resetFilters() { state.offset=0; state.query=''; state.decision=''; state.kind=''; state.jobId=''; state.focusId=null; state.recycled=false; state.activeId=null; state.dirty=false; state.selectLast=false; }
function selectionHas(id){return state.selection.some(item=>item.id===id);}
function updateSelectionUI(){
    const button=$('selection-actions');
    if(button){button.disabled=!state.selection.length;button.textContent=`已选 ${state.selection.length} · 批量/沟通板`;}
    const toggle=$('toggle-selection'), ref=current();
    if(toggle&&ref)toggle.textContent=selectionHas(ref.id)?'移出批量选择':'加入批量选择';
    const strip=$('filmstrip');
    if(strip)[...strip.children].forEach(node=>node.classList.toggle('batch-selected',selectionHas(node.dataset.ref)));
}
function toggleProjectSelection(ref){
    if(ref.detached_at||ref.decision==='reject'){toast('已移出或已淘汰的参考请先恢复');return;}
    const index=state.selection.findIndex(item=>item.id===ref.id);
    if(index>=0)state.selection.splice(index,1);
    else{
        if(state.selection.length>=24){toast('一次最多选择 24 张；沟通板会按每页 4 张分页',true);return;}
        state.selection.push({id:ref.id,title:ref.title,asset_sha:ref.asset_sha});
    }
    updateSelectionUI();
}
function safeDiscard() { return !state.busy && (!state.dirty || window.confirm('当前审美反馈尚未保存。仍然离开？')); }
async function boot() {
    const session = await api('/api/session');
    state.noAuth = Boolean(session.no_auth);
    if (!session.authenticated) { lockScreen(); return; }
    state.csrf=session.csrf; $('version').textContent='v'+session.version;
    if (state.noAuth) {
        const lockBtn = $('lock-library');
        if (lockBtn) lockBtn.hidden = true;
    }
    state.caps=await api('/api/capabilities');
    const q=new URLSearchParams(location.hash.slice(1));
    LibraryDiscovery.restore(q);
    if ([...projectViews,'library','inspiration','jobs','notes','profile'].includes(q.get('view'))) state.view=q.get('view');
    state.activeId=q.get('ref'); state.focusId=state.activeId; state.offset=Math.max(0,Number(q.get('offset'))||0);
    state.query=(q.get('q')||'').slice(0,400); state.decision=q.get('decision')||''; state.kind=q.get('kind')||'';
    state.jobId=q.get('job')||''; state.recycled=q.get('recycled')==='1';
    await loadProjects(q.get('project'));
}
async function loadProjects(preferredId) {
    [state.projects,state.archivedProjects]=await Promise.all([api('/api/projects'),api('/api/projects?archived=true')]);
    state.project=state.projects.find(x=>x.id===(preferredId||state.project?.id))||state.projects[0]||null;
    if (!state.project && projectViews.includes(state.view)) state.view='inspiration';
    await LibraryDiscovery.init();
    $('login-screen').hidden=true; $('application').hidden=false;
    renderSidebar(); renderHeader(); await refreshView();
}
async function navigate(view, projectId=null, focusId=null) {
    if (!safeDiscard()) return;
    const before=state.project?.id;
    if (projectId) state.project=state.projects.find(p=>p.id===projectId)||state.project;
    if (projectId&&state.project?.id!==before) state.selection=[];
    state.view=view; resetFilters(); state.focusId=focusId; state.activeId=focusId;
    renderSidebar(); renderHeader(); await refreshView();
    if(projectId) LibraryDiscovery.visit(projectId).catch(showError);
}
function renderSidebar() {
    LibraryDiscovery.renderProjects();
    $('archived-projects').hidden=!state.archivedProjects.length;
    $('archived-projects').onclick=()=>archivedProjectsDialog();
    document.querySelectorAll('#global-nav [data-view]').forEach(b=>b.classList.toggle('active',b.dataset.view===state.view));
}
function renderHeader() {
    const p=state.project, local=projectViews.includes(state.view);
    $('view-tabs').hidden=!local;
    if (local&&p) {
        $('project-header').innerHTML=`<div><span class="eyebrow">MY SHOOTING PROJECT</span><h1>${esc(p.character)} ${p.costume?`<span class="muted">/ ${esc(p.costume)}</span>`:''}</h1><p>${esc(p.brief||p.work||'先挑喜欢的参考，再把最值得拍的几张做成现场卡。')}</p></div><div class="header-actions"><button id="collect-project" class="primary">找一批参考</button><button id="import-reference">导入参考</button><details class="project-tools"><summary>项目设置与导出</summary><button id="edit-project">角色与要求</button><button id="export-pack">离线拍摄包</button><button id="show-events">变更记录</button><button id="archive-project" class="danger">删除项目</button></details></div>`;
        $('collect-project').onclick=()=>collectionEditor(p.id);
        $('import-reference').onclick=()=>importDialog(); $('edit-project').onclick=()=>projectEditor(p);
        $('export-pack').onclick=()=>packDialog(); $('show-events').onclick=()=>navigate('events');
        $('archive-project').onclick=()=>archiveProject(p).catch(showError);
    } else {
        const titles={library:['MY PHOTO LIBRARY','图库','不必记得图片在哪个项目。按画面特征找图，再回到项目使用。'],inspiration:['MY INSPIRATION LIBRARY','我的审美库','不必属于某个角色。收藏值得反复看的动作、光线、色彩与画面。'],profile:['AESTHETIC PROFILE','我的审美画像','保留人工选择、审美笔记与确认总结；默认和历史权重不是已验证的个人偏好。'],jobs:['AGENT WORKBENCH','采集任务','网站保存要求与结果；Codex / Antigravity 使用 BrowserSkill 执行。'],notes:['PHOTOGRAPHY NOTES','摄影笔记','留下自己的观察、拍摄方法和复盘。']};
        const t=titles[state.view]||titles.inspiration;
        $('project-header').innerHTML=`<div><span class="eyebrow">${t[0]}</span><h1>${t[1]}</h1><p>${t[2]}</p></div>${state.view==='inspiration'?'<div class="header-actions"><button id="add-inspiration" class="primary">＋ 收藏独立图片</button></div>':''}`;
        if ($('add-inspiration')) $('add-inspiration').onclick=()=>importDialog();
    }
}
async function renderStats(projectId=state.project?.id) {
    if (!projectId||!projectViews.includes(state.view)) { $('stats').innerHTML=''; return; }
    const scope=scopeKey(), data=await api(`/api/projects/${projectId}/stats`);
    if (scope!==scopeKey()) return;
    const values=[['候选流',data.visible],['待挑选',data.pending],['预检过滤',data.filtered||0],['角色精选',data.selected],['现场卡',data.ready]];
    $('stats').innerHTML=values.map(([label,value])=>`<div class="stat"><strong>${value}</strong><span>${label}</span></div>`).join('');
}
async function refreshView() {
    state.epoch++; renderSidebar(); renderHeader();
    document.querySelectorAll('#view-tabs [data-view]').forEach(b=>b.classList.toggle('active',b.dataset.view===state.view));
    renderStats().catch(showError); rememberNavigation();
    if (projectViews.includes(state.view)&&!state.project) { $('view').innerHTML=empty('建立一个拍摄项目','只需填写角色名。','建立项目','first-project'); $('first-project').onclick=()=>projectEditor(); return; }
    if (state.view==='library') await LibraryDiscovery.render();
    else if (imageViews.includes(state.view)) await loadReferences();
    else if (state.view==='jobs') await renderJobs();
    else if (state.view==='notes') await renderNotes();
    else if (state.view==='profile') await renderProfile();
    else await renderEvents();
}



async function loadReferences(fallbackIndex=0) {
    const scope=scopeKey(), epoch=++state.epoch, global=state.view==='inspiration';
    const q=new URLSearchParams({limit:state.limit,offset:state.offset,q:state.query});
    if (global) q.set('recycled',state.recycled?'true':'false');
    else {
        q.set('decision',state.decision); q.set('kind',state.kind); if(state.focusId)q.set('focus_id',state.focusId);
        if (state.jobId) q.set('job_id',state.jobId);
        if (state.view==='field') q.set('state','ready');
        if (state.view==='selected') { q.set('decision','keep');q.set('lane','field'); }
        if (state.view==='filtered') q.set('view_filtered','true');
        if (state.view==='recycle') q.set('view_recycle','true');
    }
    const data=await api(global?`/api/inspirations?${q}`:`/api/projects/${state.project.id}/references?${q}`);
    if (epoch!==state.epoch||scope!==scopeKey()) return;
    state.refs=data.items; state.total=data.total; state.offset=data.offset; state.focusId=null;
    if (state.offset>=data.total&&state.offset>0) {
        state.offset=data.total?Math.floor((data.total-1)/state.limit)*state.limit:0;
        return loadReferences(fallbackIndex);
    }
    if (state.selectLast) { state.activeId=state.refs.at(-1)?.id||null; state.selectLast=false; }
    if (!state.refs.some(r=>r.id===state.activeId)) state.activeId=state.refs[Math.min(fallbackIndex,state.refs.length-1)]?.id||null;
    state.dirty=false; renderReferenceView(); rememberNavigation();
}
function mountReferenceShell() {
    const view=$('view'), key=scopeKey();
    if (view.dataset.shell===key&&$('filmstrip')) return;
    view.dataset.shell=key;
    const global=state.view==='inspiration';
    view.innerHTML=`<div class="toolbar"><input id="search-ref" aria-label="搜索参考" placeholder="搜索标题、作者、审美反馈" value="${esc(state.query)}"><select id="decision-filter" aria-label="选择状态" ${global||['selected','field','filtered','recycle'].includes(state.view)?'hidden':''}><option value="">全部未淘汰</option>${Object.entries(decisions).map(([k,v])=>`<option value="${k}" ${state.decision===k?'selected':''}>${v}</option>`).join('')}</select><details class="filter-more" ${global?'hidden':''}><summary>图片类型</summary><select id="kind-filter" aria-label="图片类型"><option value="">全部图片类型</option>${Object.entries(kinds).map(([k,v])=>`<option value="${k}" ${state.kind===k?'selected':''}>${v}</option>`).join('')}</select></details>${global?`<button id="toggle-recycled">${state.recycled?'回到审美库':'已移除收藏'}</button>`:''}${!global&&state.view==='references'?'<button id="finish-screening-btn" class="quiet" style="margin-left:8px;border:1px solid var(--line);">结束本轮筛选并总结</button>':''}${!global?'<button id="selection-actions" class="quiet">已选 0 · 批量/沟通板</button>':''}<span class="spacer"></span><small class="desktop-shortcut-hint">${global?'独立收藏 · 可引用到多个项目':'K 角色参考 / I 通用灵感 / M 待定 / X 淘汰'}</small></div><div id="collection-context"></div><div id="reference-empty" hidden></div><div id="reference-content" class="review-layout"><div class="image-column"><div class="stage-and-cues" id="stage-and-cues"><aside class="mobile-cues-panel" id="mobile-cues-panel" hidden></aside><div class="image-stage" id="image-stage"><span class="stage-counter" id="stage-counter"></span><button type="button" class="stage-nav stage-prev" id="stage-prev-btn" aria-label="上一张">‹</button><img id="main-image" alt=""><button type="button" class="stage-nav stage-next" id="stage-next-btn" aria-label="下一张">›</button><div class="missing-image" id="missing-image" hidden>图片文件不可用，请检查资产或重新导入原图。</div></div></div><div class="image-caption"><span id="image-caption-text"></span><button id="view-original">查看独立原图</button></div><div id="filmstrip" class="filmstrip" role="group" aria-label="参考缩略图"></div><div class="image-nav"><button id="previous-image">← 上一张</button><label class="check"><input id="auto-advance" type="checkbox" ${state.autoAdvance?'checked':''}>选择后下一张</label><button id="next-image">下一张 →</button></div><div class="pagination"><button id="previous-page">上一页</button><span id="page-count"></span><button id="next-page">下一页</button></div></div><div class="detail-panel" id="detail-panel"></div></div>`;
    const change=async(key,element)=>{
        if (state[key]===element.value) return;
        if (!safeDiscard()) { element.value=state[key];return; }
        state[key]=element.value;state.offset=0;state.activeId=null;state.dirty=false;
        await loadReferences();
    };
    $('search-ref').onchange=e=>change('query',e.target).catch(showError);
    $('search-ref').onkeydown=e=>{if(e.key==='Enter')change('query',e.target).catch(showError);};
    $('decision-filter').onchange=e=>change('decision',e.target).catch(showError);
    $('kind-filter').onchange=e=>change('kind',e.target).catch(showError);
    if ($('finish-screening-btn')) $('finish-screening-btn').onclick=()=>finishScreeningSessionModal();
    if ($('selection-actions')) $('selection-actions').onclick=()=>selectionActionsDialog();
    updateSelectionUI();

    if ($('toggle-recycled')) $('toggle-recycled').onclick=()=>{if(!safeDiscard())return;state.recycled=!state.recycled;state.offset=0;state.activeId=null;loadReferences().catch(showError);};
    // Delegation is installed once. Selection never rebinds 60 thumbnail handlers.
    $('filmstrip').onclick=e=>{
        const node=e.target.closest('[data-ref]');
        if (!node||!safeDiscard()) return;
        state.activeId=node.dataset.ref;state.dirty=false;renderActiveReference();rememberNavigation();
    };
    $('main-image').onclick=()=>openImage(current());
    const mainImage=$('main-image');
    mainImage.onerror=()=>{if(mainImage.isConnected&&!mainImage.naturalWidth){mainImage.hidden=true;$('missing-image').hidden=false;}};
    mainImage.onload=()=>{if(mainImage.isConnected&&mainImage.naturalWidth>0){mainImage.hidden=false;$('missing-image').hidden=true;}};
    $('view-original').onclick=()=>openImage(current());
    $('auto-advance').onchange=e=>state.autoAdvance=e.target.checked;
    $('previous-image').onclick=()=>moveImage(-1); $('next-image').onclick=()=>moveImage(1);
    if ($('stage-prev-btn')) $('stage-prev-btn').onclick=(e)=>{e.stopPropagation();moveImage(-1);};
    if ($('stage-next-btn')) $('stage-next-btn').onclick=(e)=>{e.stopPropagation();moveImage(1);};

    // Mobile touch swipe gestures on image-stage
    const stage = $('image-stage');
    let touchStartX = 0, touchStartY = 0, touchStartTime = 0;
    stage.addEventListener('touchstart', e => {
        if (e.touches.length === 1) {
            touchStartX = e.touches[0].clientX;
            touchStartY = e.touches[0].clientY;
            touchStartTime = Date.now();
        }
    }, { passive: true });
    stage.addEventListener('touchend', e => {
        if (e.changedTouches.length === 1) {
            const diffX = e.changedTouches[0].clientX - touchStartX;
            const diffY = e.changedTouches[0].clientY - touchStartY;
            const duration = Date.now() - touchStartTime;
            if (duration < 600 && Math.abs(diffX) > 42 && Math.abs(diffX) > Math.abs(diffY) * 1.4) {
                if (diffX < 0) moveImage(1);
                else moveImage(-1);
            }
        }
    }, { passive: true });

    $('previous-page').onclick=()=>pageReferences(-1); $('next-page').onclick=()=>pageReferences(1);
}
function reconcileFilmstrip() {
    const strip=$('filmstrip'), previous=strip.scrollLeft, bounds=strip.getBoundingClientRect();
    const anchor=[...strip.children].find(n=>n.getBoundingClientRect().right>bounds.left+1);
    const anchorId=anchor?.dataset.ref, anchorLeft=anchor?.getBoundingClientRect().left;
    const wanted=new Set(state.refs.map(r=>r.id));
    const existing=new Map([...strip.children].map(n=>[n.dataset.ref,n]));
    for (const [id,node] of existing) if (!wanted.has(id)) node.remove();
    state.refs.forEach((ref,index)=>{
        let node=existing.get(ref.id);
        if (!node) { node=document.createElement('button');node.dataset.ref=ref.id;node.type='button'; }
        const imageKey=ref.asset_sha+':'+ref.file_available;
        if (node.dataset.image!==imageKey) {
            node.innerHTML=ref.asset&&ref.file_available!==false?'<img loading="lazy" alt=""><span class="verdict"></span>':'<span class="thumb-missing">缺图</span><span class="verdict"></span>';
            if (node.querySelector('img')) node.querySelector('img').src=`/api/assets/${ref.asset_sha}/thumb`;
            node.dataset.image=imageKey;
        }
        node.setAttribute('aria-label','查看 '+ref.title);
        if (node.querySelector('img')) node.querySelector('img').alt=ref.title;
        const verdict=node.querySelector('.verdict');
        verdict.className='verdict '+ref.decision;
        verdict.textContent=ref.lane==='inspiration'&&ref.decision==='keep'?'♡':({keep:'✓',maybe:'?',reject:'×'})[ref.decision]||'';
        if (strip.children[index]!==node) strip.insertBefore(node,strip.children[index]||null);
    });
    const keptAnchor=anchorId&&existing.get(anchorId);
    if (keptAnchor?.isConnected) strip.scrollLeft+=keptAnchor.getBoundingClientRect().left-anchorLeft;
    else strip.scrollLeft=previous;
}
function keepActiveThumbnailVisible() {
    const strip=$('filmstrip'), active=[...strip.children].find(n=>n.dataset.ref===state.activeId);
    if (!active) return;
    const outer=strip.getBoundingClientRect(), inner=active.getBoundingClientRect();
    const left=outer.left+strip.clientLeft, right=left+strip.clientWidth;
    // Minimal horizontal adjustment only if the active item is actually clipped.
    // The filmstrip/list nodes remain alive; no scrolling of the page or ancestors.
    if(inner.left<left)strip.scrollLeft-=left-inner.left;
    else if(inner.right>right)strip.scrollLeft+=inner.right-right;
}
function renderReferenceView() {
    mountReferenceShell();
    $('reference-content').hidden=!state.refs.length;
    $('reference-empty').hidden=!!state.refs.length;
    if (!state.refs.length) {
        const titles={field:'还没有已确认的现场卡',selected:'先选出值得拍的参考',filtered:'没有被预检过滤的候选',inspiration:state.recycled?'没有已移除收藏':'这里留给长期喜欢的画面',recycle:'没有已淘汰图片'};
        $('reference-empty').innerHTML=empty(titles[state.view]||'没有匹配的候选','可以改变筛选条件。现场卡只来自你挑选并检查过的独立图片。');
    }
    $('collection-context').textContent=state.jobId?'正在查看一个采集任务的发现结果；不代表已确认图片属于这个角色。':state.view==='filtered'?'这里保留被视觉预检降级的候选。过滤不是 K/I/M/X，也不会删除资产；可以人工恢复后再决定。':state.view==='recycle'?'这里同时包含 X 淘汰和从当前项目移出的引用。两者都只影响本项目；其他项目和全局收藏不会一起删除。':'';
    if($('toggle-recycled'))$('toggle-recycled').textContent=state.recycled?'回到审美库':'已移除收藏';
    $('search-ref').value=state.query;$('decision-filter').value=state.decision;$('kind-filter').value=state.kind;
    reconcileFilmstrip();
    $('page-count').textContent=`${state.total?state.offset+1:0}–${state.offset+state.refs.length} / ${state.total}`;
    $('previous-page').disabled=state.offset===0;
    $('next-page').disabled=state.offset+state.limit>=state.total;
    if(state.refs.length)renderActiveReference();
    updateSelectionUI();
}
function renderActiveReference() {
    const ref=current();if(!ref)return;
    const image=$('main-image'), available=!!ref.asset&&ref.file_available!==false;
    if(image.dataset.asset!==ref.asset_sha+':'+available){
        image.dataset.asset=ref.asset_sha+':'+available;
        image.hidden=!available;$('missing-image').hidden=available;
        if(available)image.src=`/api/assets/${ref.asset_sha}/preview`;else image.removeAttribute('src');
    }
    image.alt=ref.title;
    $('image-caption-text').textContent=ref.asset?`${ref.asset.width} × ${ref.asset.height} · ${(ref.asset.bytes/1024).toFixed(0)} KB · 独立接收版本`:'缺少图像资产';
    $('view-original').disabled=!available;
    [...$('filmstrip').children].forEach(n=>{const chosen=n.dataset.ref===ref.id;n.classList.toggle('selected',chosen);n.setAttribute('aria-current',String(chosen));n.tabIndex=chosen?0:-1;});
    keepActiveThumbnailVisible();
    const index=state.refs.findIndex(r=>r.id===ref.id);
    const atFirst = index===0&&state.offset===0;
    const atLast = index===state.refs.length-1&&state.offset+state.limit>=state.total;
    $('previous-image').disabled=atFirst;
    $('next-image').disabled=atLast;
    if ($('stage-prev-btn')) $('stage-prev-btn').disabled = atFirst;
    if ($('stage-next-btn')) $('stage-next-btn').disabled = atLast;
    const counter = $('stage-counter');
    if (counter) {
        const curNum = state.total ? state.offset + index + 1 : 0;
        counter.textContent = `${curNum} / ${state.total || state.refs.length}`;
    }

    // Mobile split view: if card exists, show 1/3 cues on the left, 2/3 image on the right
    const cuePanel = $('mobile-cues-panel');
    const cueWrapper = $('stage-and-cues');
    if (cuePanel && cueWrapper) {
        const card = ref.card;
        const hasCues = card && (card.pose?.verbal_cues?.length || card.pose?.photographer_steps?.length);
        if (hasCues) {
            cueWrapper.classList.add('has-card');
            cuePanel.hidden = false;
            let html = '';
            if (card.pose?.verbal_cues?.length) {
                html += `<div class="cues-title">🗣️ 现场口令</div><ol class="cues-list">${card.pose.verbal_cues.map(c => `<li>${esc(c)}</li>`).join('')}</ol>`;
            }
            if (card.pose?.photographer_steps?.length) {
                html += `<div class="cues-title" style="margin-top:6px;">📸 摄影动作</div><ul class="cues-steps">${card.pose.photographer_steps.map(s => `<li>${esc(s)}</li>`).join('')}</ul>`;
            }
            if (card.pose?.fallback || card.pose?.safety) {
                html += `<div class="cues-fallback" style="margin-top:6px;">🛡️ ${esc(card.pose.fallback || card.pose.safety)}</div>`;
            }
            cuePanel.innerHTML = html;
        } else {
            cueWrapper.classList.remove('has-card');
            cuePanel.hidden = true;
            cuePanel.innerHTML = '';
        }
    }

    if(state.view==='inspiration')renderInspirationDetail(ref);else renderDetail(ref);
}
function moveImage(delta) {
    if(!safeDiscard())return;
    const index=state.refs.findIndex(x=>x.id===state.activeId), next=index+delta;
    if(next>=0&&next<state.refs.length){state.activeId=state.refs[next].id;state.dirty=false;renderActiveReference();rememberNavigation();}
    else if(delta>0&&state.offset+state.limit<state.total)pageReferences(1);
    else if(delta<0&&state.offset>0)pageReferences(-1,true);
}
function pageReferences(delta,last=false) {
    if(!safeDiscard())return;
    state.offset=Math.max(0,state.offset+delta*state.limit);state.activeId=null;state.selectLast=last;state.dirty=false;
    loadReferences().catch(showError);
}


function selectionActionsDialog(){
    if(!state.selection.length){toast('先选择几张参考');return;}
    const root=modal(`已选 ${state.selection.length} 张`,`<p class="form-help">这只是项目内的临时选择篮，不改变 K/I/M/X。可以批量复制/转移，也可以按当前选择顺序导出模特沟通板。</p><div class="guide-section">${state.selection.map((item,index)=>`<p><strong>${index+1}.</strong> ${esc(item.title)}</p>`).join('')}</div><div class="form-actions"><button id="selection-transfer">复制 / 转移到项目</button><button id="selection-board" class="primary">导出沟通板</button><button id="selection-clear" class="quiet">清空选择</button></div>`);
    $('selection-transfer').onclick=()=>transferReferencesDialog(state.selection);
    $('selection-board').onclick=()=>contactBoardDialog(state.selection);
    $('selection-clear').onclick=()=>{state.selection=[];closeModal();updateSelectionUI();};
}
async function freshTransferItems(items){
    const refs=await Promise.all(items.map(item=>api(`/api/references/${item.id}`)));
    return refs.map(ref=>({reference_id:ref.id,expected_revision:ref.revision}));
}
function transferReferencesDialog(items){
    const selected=(items||[]).filter(Boolean);
    if(!selected.length){toast('没有可操作的参考');return;}
    const targets=state.projects.filter(p=>p.id!==state.project?.id);
    const targetOptions=Object.fromEntries(targets.map(p=>[p.id,p.character+(p.costume?' / '+p.costume:'')]));
    const transferForm=targets.length?`<form id="transfer-form"><p class="notice">复制：当前项目保留；转移：目标项目建立/复用引用后，从当前项目移出。目标项目默认“未选择”，不会继承当前角色判断、preflight、资料卡或验收。</p>${select('目标项目','target_project_id',targetOptions,targets[0]?.id||'')}${select('操作','mode',{copy:'复制到目标项目',move:'转移到目标项目'},'copy')}${select('目标项目初始状态','target_decision',{pending:'未选择（推荐）',keep:'K · 本角色参考',maybe:'M · 待定'},'pending')}<div class="form-actions"><button type="submit" class="primary">执行</button></div></form>`:'<p class="notice">还没有其他可用拍摄项目。可以先建立目标项目，或仅从当前项目移出。</p>';
    const root=modal(`项目复用 · ${selected.length} 张`,`${transferForm}<hr><button id="detach-current" class="danger">仅从当前项目移出</button><p class="form-help">“移出”不是 X 淘汰：图片资产和历史记录保留，可在“已淘汰 / 恢复”里恢复当前项目引用。</p>`);
    if($('transfer-form'))formSubmit(root,async data=>{
        const transferItems=await freshTransferItems(selected);
        const result=await api(`/api/projects/${state.project.id}/references/transfer`,{method:'POST',body:{items:transferItems,mode:data.mode,target_project_id:data.target_project_id,target_decision:data.target_decision}});
        if(data.mode==='move')state.selection=state.selection.filter(item=>!selected.some(chosen=>chosen.id===item.id));
        closeModal();await loadReferences();await renderStats();updateSelectionUI();
        toast(data.mode==='move'?`已转移 ${result.items.length} 张；目标项目未继承角色判断`:`已复制 ${result.items.length} 张；当前项目保持不变`);
    });
    $('detach-current').onclick=async()=>{
        if(!window.confirm(`从当前项目移出这 ${selected.length} 张？图片不会删除，可从项目回收入口恢复。`))return;
        const transferItems=await freshTransferItems(selected);
        await api(`/api/projects/${state.project.id}/references/transfer`,{method:'POST',body:{items:transferItems,mode:'remove',target_project_id:'',target_decision:'pending'}});
        state.selection=state.selection.filter(item=>!selected.some(chosen=>chosen.id===item.id));
        closeModal();await loadReferences();await renderStats();updateSelectionUI();toast('已从当前项目移出；没有作为 X 学习');
    };
}
function contactBoardDialog(items){
    const selected=(items||[]).filter(Boolean);
    if(!selected.length){toast('先选择几张参考');return;}
    const rows=selected.map((item,index)=>`<div class="event-card board-item" data-board-ref="${esc(item.id)}"><div class="compact-row"><strong>${index+1}. ${esc(item.title)}</strong><button type="button" data-move="-1">↑</button><button type="button" data-move="1">↓</button></div><div class="compact-row"><img src="/api/assets/${esc(item.asset_sha)}/thumb" alt="" style="width:72px;height:72px;object-fit:contain"><input data-board-note maxlength="400" hidden></div></div>`).join('');
    const root=modal('导出多宫格拼图',`<form id="contact-board-form"><p class="notice">纯净多宫格拼图，保留完整画面不强裁切；每页最多 4 张或合并为整张宫格大图。无多余文字与格式修饰。</p><div id="board-items">${rows}</div><div class="form-actions"><button type="submit" class="primary">生成并下载拼图</button></div></form>`);
    listen(root,'[data-move]','click',(e,n)=>{
        const row=n.closest('[data-board-ref]'), direction=Number(n.dataset.move);
        const sibling=direction<0?row.previousElementSibling:row.nextElementSibling;
        if(!sibling)return;
        if(direction<0)row.parentElement.insertBefore(row,sibling);else row.parentElement.insertBefore(sibling,row);
    });
    formSubmit(root,async(data,form)=>{
        const ordered=[...form.querySelectorAll('[data-board-ref]')].map(node=>({reference_id:node.dataset.boardRef,note:''}));
        await download(`/api/projects/${state.project.id}/contact-board`,`${state.project.character}-多宫格拼图.png`,{title:'',items:ordered,single_image:true});
        closeModal();toast('多宫格拼图已生成');
    });
}


async function archiveProject(project) {
    if(!safeDiscard())return;
    if(!window.confirm(`删除项目“${project.character}”？项目会移到回收区；图片、全局审美收藏、其他项目引用和历史记录不会物理删除。`))return;
    await api(`/api/projects/${project.id}`,{method:'DELETE',body:{expected_revision:project.revision}});
    state.project=null;state.selection=[];resetFilters();await loadProjects();toast('项目已移到回收区，可恢复');
}
function archivedProjectsDialog() {
    const body=state.archivedProjects.length
        ? `<p class="form-help">恢复项目不会复制图片，也不会改变其他项目或全局审美库。</p>${state.archivedProjects.map(p=>`<div class="event-card"><strong>${esc(p.character)}</strong><small>${esc(p.costume||p.work||'拍摄项目')}</small><button data-restore-project="${esc(p.id)}">恢复项目</button></div>`).join('')}`
        : '<p>没有已删除项目。</p>';
    const root=modal('已删除项目',body);
    listen(root,'[data-restore-project]','click',async(e,n)=>{
        const p=state.archivedProjects.find(x=>x.id===n.dataset.restoreProject);if(!p)return;
        await api(`/api/projects/${p.id}/restore`,{method:'POST',body:{expected_revision:p.revision}});
        closeModal();await loadProjects(p.id);toast('项目已恢复');
    });
}
function projectEditor(project = null) { if (!safeDiscard())
    return; const root = modal(project ? '角色、要求与器材' : '新建角色项目', `<form><p class="form-help">只有角色名是必填。额外要求直接写成自然语言，不需要套固定分类。修改要求会让旧资料卡重新等待核对。</p><div class="form-grid">${label('角色名 *', 'character', project?.character || '', 'text', 'required maxlength="120"')}${label('出自作品（选填）', 'work', project?.work || '', 'text', 'maxlength="400"')}${label('服装／皮肤版本（选填）', 'costume', project?.costume || '', 'text', 'maxlength="400"')}<div class="full">${area('补充要求', 'brief', project?.brief || '', 'placeholder="例如：漫展拍摄，想多看站姿和回眸，不要复杂布景；要自然，但保留角色的疏离感。" maxlength="12000"')}</div><div class="full"><details><summary>我的器材与拍摄条件</summary>${area('设备／环境限制', 'gear', project?.gear || '', 'placeholder="留空则使用当前预设：A7M4、50mm、24–240mm、V100 一灯与柔光附件。" maxlength="12000"')}</details></div></div><div class="form-actions"><button class="primary" type="submit">${project ? '保存修改' : '建立项目'}</button></div></form>`); formSubmit(root, async (data) => { if (!project && !data.gear)
    delete data.gear; const p = await api(project ? `/api/projects/${project.id}` : '/api/projects', { method: project ? 'PUT' : 'POST', body: project ? { ...data, expected_revision: project.revision } : data }); closeModal(); resetFilters(); state.view="references"; await loadProjects(p.id); toast('角色项目已保存'); }); }
function openImage(ref) { if (!ref?.asset || ref.file_available === false)
    return; $('lightbox-title').textContent = `${ref.title} · ${ref.asset.width} × ${ref.asset.height}`; $('lightbox-image').src = `/api/assets/${ref.asset_sha}/original`; $('lightbox').classList.remove('actual'); $('lightbox').showModal(); }
function paragraphs(text) { return `<p>${esc(text)}</p>`; }
function ordered(items) { return `<ol>${(items || []).map(x => `<li>${esc(x)}</li>`).join('')}</ol>`; }
function cardMarkup(card, field = false) {
    if (!card) return '';
    return `<section class="guide-section ${field ? 'field-mode' : ''}">
        <div class="field-card-banner">
            <h3>${field ? '🎯 现场拍摄指引' : '📋 资料卡草稿'} <small>先沟通，再调整</small></h3>
        </div>
        ${card.pose.verbal_cues?.length ? `<div class="verbal-cues-card">
            <span class="cue-label">🗣️ 现场口令（沟通引导词）</span>
            ${ordered(card.pose.verbal_cues)}
        </div>` : ''}
        ${card.pose.photographer_steps?.length ? `<div class="photographer-steps-card">
            <span class="cue-label">📸 摄影师机位与动作</span>
            ${ordered(card.pose.photographer_steps)}
        </div>` : ''}
        ${card.pose.safety || card.pose.fallback ? `<div class="safety-fallback-card">
            <span class="cue-label">🛡️ 安全与降级方案</span>
            ${paragraphs((card.pose.safety ? '【安全】' + card.pose.safety + '\n' : '') + (card.pose.fallback ? '【降级】' + card.pose.fallback : ''))}
        </div>` : ''}
        <details ${field ? '' : 'open'} class="field-tech-details">
            <summary>📐 静态摆姿、动作引导与布光推测</summary>
            <h4>静态摆姿</h4>${ordered(card.pose.static_steps)}
            ${card.pose.action_directing ? `<h4>动作引导</h4>${paragraphs(card.pose.action_directing)}` : ''}
            <h4>图中光线证据</h4>${ordered(card.lighting.visible_evidence)}
            <h4>布光推测 · ${esc(card.lighting.confidence)}</h4>${paragraphs(card.lighting.interpretation)}
            <h4>现有器材可尝试方案</h4>${paragraphs(card.lighting.available_gear_plan)}
        </details>
        <details class="field-tech-details">
            <summary>🎨 后期路线：${esc(({ none: '不换背景', cleanup: '轻量清理', composite: '明确合成' })[card.retouch.route] || card.retouch.route)}</summary>
            ${ordered(card.retouch.steps)}
            ${card.retouch.capture_preparation ? `<h4>拍摄准备</h4>${paragraphs(card.retouch.capture_preparation)}` : ''}
            ${card.retouch.background_prompt ? `<h4>AI 背景需求</h4>${paragraphs(card.retouch.background_prompt)}` : ''}
        </details>
    </section>`;
}
async function updateAction(ref, action, body, message) { await api(`/api/references/${ref.id}/${action}`, { method: 'POST', body }); state.activeId = ref.id; state.dirty = false; closeModal(); await loadReferences(); await renderStats(); toast(message); }
function sourceEditor(ref) { const s = ref.source; const root = modal('来源、权利状态与标题', `<form><p class="form-help">原发布页与图片 CDN 不是一回事。搜索结果页也不能代替原出处。来源不明仍可收藏，但不能伪装成已经确认的实拍资料卡。</p>${label('条目标题', 'title', ref.title, 'text', 'maxlength="400"')}${label('原发布页', 'page_url', s.page_url, 'url', 'maxlength="4000"')}${label('图片来源地址（只作追溯）', 'image_url', s.image_url, 'url', 'maxlength="4000"')}${label('作者', 'author', s.author, 'text', 'maxlength="400"')}${select('权利状态', 'rights', { unknown: '未确认', personal_reference: '私人参考，不代表公开转载许可', owned: '我拥有此图片的使用权', licensed: '已获授权' }, s.rights)}${area('使用权／来源说明', 'rights_note', s.rights_note, 'placeholder="自有作品请注明；授权请记录范围。" maxlength="12000"')}${check('我已检查原发布页，或确认这是我的自有作品', 'source_confirmed', s.source_confirmed)}<div class="form-actions"><button type="submit" class="primary">保存来源</button></div></form>`); formSubmit(root, async (data) => { const title = data.title; delete data.title; await api(`/api/references/${ref.id}`, { method: 'PATCH', body: { expected_revision: ref.revision, title, source: { ...s, ...data } } }); closeModal(); await loadReferences(); toast('来源信息已保存；旧发布确认已撤销'); }); }
function reviewEditor(ref) { const r = ref.review || { kind: 'unknown', visible_person: false, pose_readable: false, single_image: false, sufficiently_clear: false, character_match: 'unknown', observations: [], critical_uncertainties: [] }; const root = modal('逐图人工核验', `<form><p class="form-help">请实际打开独立图片后填写。器材、场地、插画和拼图不能成为真人姿势主卡。没有把握就保留“未知”与疑点。</p><div class="form-grid">${select('图片实际类型', 'kind', kinds, r.kind)}${select('与目标角色的关系', 'character_match', { unknown: '未确认', exact: '目标角色／版本匹配', adapted: '不是同角色，仅借鉴指定方面', irrelevant: '不相关' }, r.character_match)}</div>${check('图中有明确可见的人物', 'visible_person', r.visible_person)}${check('需要借鉴的肢体／动作看得清', 'pose_readable', r.pose_readable)}${check('这是独立画面，不是多个画面的拼图', 'single_image', r.single_image)}${check('实际清晰度足以支持动作分析', 'sufficiently_clear', r.sufficiently_clear)}${area('看得见的事实（每行一条）*', 'observations', r.observations.join('\n'), 'required placeholder="只写图中可见的内容，不依据标题猜动作。"')}${area('仍未解决的关键疑点（没有则留空）', 'critical_uncertainties', r.critical_uncertainties.join('\n'))}<small>核验绑定图片 SHA：${esc(ref.asset_sha?.slice(0, 20))}…</small><div class="form-actions"><button type="submit" class="primary">保存人工核验</button></div></form>`); formSubmit(root, data => updateAction(ref, 'review', { expected_revision: ref.revision, review: { ...data, asset_sha: ref.asset_sha, observations: lines(data.observations), critical_uncertainties: lines(data.critical_uncertainties) } }, '逐图核验已保存')); }
function cardEditor(ref) { const c = ref.card || { title: ref.title, intent: '', pose: { verbal_cues: [], static_steps: [], action_directing: '', photographer_steps: [], safety: '', fallback: '' }, lighting: { visible_evidence: [], interpretation: '', confidence: 'low', available_gear_plan: '' }, retouch: { route: 'none', steps: [], capture_preparation: '', background_prompt: '' } }; const root = modal(ref.card ? '编辑资料卡' : '编写资料卡', `<form><p class="form-help">不知道原作者怎么拍，就写你可尝试的方案。这里保存的是草稿，最后还需要你确认。每行一条的字段会按顺序显示。</p>${label('资料卡标题 *', 'title', c.title, 'text', 'required')}${area('这张图值得借鉴什么 *', 'intent', c.intent, 'required')}<h3 class="form-heading">现场引导 · 第一优先级</h3>${area('可以直接说出口的口令（每行一条）*', 'verbal_cues', c.pose.verbal_cues.join('\n'), 'required')}${area('静态摆姿步骤（每行一条）*', 'static_steps', c.pose.static_steps.join('\n'), 'required')}${area('动作／情境引导版本', 'action_directing', c.pose.action_directing)}${area('摄影师自己要做什么（每行一条）*', 'photographer_steps', c.pose.photographer_steps.join('\n'), 'required')}${area('安全与舒适性 *', 'safety', c.pose.safety, 'required')}${area('动作做不到时的降级方案 *', 'fallback', c.pose.fallback, 'required')}<h3 class="form-heading">光线 · 事实与推测分开</h3>${area('图中可见的光线证据（每行一条）*', 'visible_evidence', c.lighting.visible_evidence.join('\n'), 'required')}${area('可能的布光解释 *', 'interpretation', c.lighting.interpretation, 'required')}${select('推测把握', 'confidence', { low: '低', medium: '中', high: '高' }, c.lighting.confidence)}${area('用我的器材可以尝试的方案 *', 'available_gear_plan', c.lighting.available_gear_plan, 'required')}<h3 class="form-heading">PS 与 AI 背景</h3>${select('后期路线', 'route', { none: '不换背景', cleanup: '轻量清理', composite: '明确合成' }, c.retouch.route)}${area('后期步骤（每行一条）', 'steps', c.retouch.steps.join('\n'))}${area('拍摄前的准备（合成路线必填）', 'capture_preparation', c.retouch.capture_preparation)}${area('AI 背景需求／提示词（合成路线必填）', 'background_prompt', c.retouch.background_prompt, 'placeholder="机位、地平线、光向、人物留位与地面关系；不要生成替代人物。"')}<div class="form-actions"><button type="submit" class="primary">保存资料卡草稿</button></div></form>`); formSubmit(root, data => updateAction(ref, 'card', { expected_revision: ref.revision, card: { title: data.title, intent: data.intent, pose: { verbal_cues: lines(data.verbal_cues), static_steps: lines(data.static_steps), action_directing: data.action_directing, photographer_steps: lines(data.photographer_steps), safety: data.safety, fallback: data.fallback }, lighting: { visible_evidence: lines(data.visible_evidence), interpretation: data.interpretation, confidence: data.confidence, available_gear_plan: data.available_gear_plan }, retouch: { route: data.route, steps: lines(data.steps), capture_preparation: data.capture_preparation, background_prompt: data.background_prompt } } }, '资料卡草稿已保存，尚未自动发布')); }
function reflectionEditor(ref) { const root = modal('把实拍经验接回参考', `<form>${check('我已经实际尝试过', 'tried', true)}${area('什么引导／方法有效', 'worked')}${area('哪里不自然，或现场做不到', 'failed')}${area('下次如何调整', 'next_time')}<div class="form-actions"><button type="submit" class="primary">保存拍摄复盘</button></div></form>`); formSubmit(root, data => updateAction(ref, 'reflection', { ...data, expected_revision: ref.revision }, '实拍经验已保存')); }
function replaceEditor(ref) { const root = modal('替换参考图片', `<form><p class="notice">替换后会重置选择、图片核验与资料卡确认。旧文件仍保留用于追溯，不会被覆盖。</p><label>新的独立图片<input type="file" name="file" accept="image/jpeg,image/png,image/webp" required></label><div class="form-actions"><button type="submit" class="primary">替换并重新审核</button></div></form>`); formSubmit(root, async (data, form) => { const body = new FormData(form); body.set('expected_revision', ref.revision); await api(`/api/references/${ref.id}/replace`, { method: 'POST', body }); closeModal(); await loadReferences(); await renderStats(); toast('已替换；旧核验不再沿用'); }); }
async function similarDialog(ref) { const matches = await api(`/api/references/${ref.id}/similar`); const root = modal('相似图线索', `<p class="form-help">这是图像指纹的粗略相似度，不是重复判决。相邻动作也可能有价值，系统不会自动淘汰。</p><div class="filmstrip">${matches.map(x => `<button data-id="${x.id}"><img src="/api/assets/${x.asset_sha}/thumb" alt="相似参考"><span class="verdict">差异 ${x.distance}</span></button>`).join('') || '<p>当前项目没有发现近似指纹。</p>'}</div>`); listen(root, '[data-id]', 'click', async (e, n) => { const found = await api(`/api/references/${n.dataset.id}`); closeModal(); openImage(found); }); }
function packDialog() { const mode = state.view === 'inspiration' ? 'inspiration' : 'field'; const root = modal('下载离线拍摄包', `<form><p class="notice">解压 ZIP 后直接打开 index.html。独立大图、来源文件和说明都包含在包里，不需要现场联网。</p>${select('导出范围', 'mode', { field: '本项目全部已确认现场卡', inspiration: '本项目全部已保留灵感' }, mode)}<p class="form-help">现场卡不满足门槛时会阻止导出。灵感包明确标为灵感，不充当现场指令。包内可能包含他人作品及 EXIF，请仅按相应权限使用。每包最多 200 张。</p><div class="form-actions"><button type="submit" class="primary">生成并下载</button></div></form>`); formSubmit(root, async (data) => { await download(`/api/projects/${state.project.id}/pack`, `${state.project.character}-${data.mode}.zip`, { mode: data.mode, reference_ids: [] }); closeModal(); toast('离线包已生成'); }); }
function noteEditor(note = null) { const root = modal(note ? '编辑摄影笔记' : '写摄影笔记', `<form>${label('笔记标题 *', 'title', note?.title || '', 'text', 'required maxlength="400"')}${area('正文（支持保留 Markdown）', 'body', note?.body || '', 'required style="min-height:300px" maxlength="200000"')}<div class="form-actions"><button type="submit" class="primary">保存笔记</button></div></form>`); formSubmit(root, async (data) => { await api(note ? `/api/notes/${note.id}` : '/api/notes', { method: note ? 'PUT' : 'POST', body: note ? { ...data, expected_revision: note.revision } : data }); closeModal(); await renderNotes(); toast('摄影笔记已保存'); }); }
function openNote(note) { const root = modal(note.title, `<div class="compact-row"><small>${esc(note.source_path || '本地笔记')}</small><button id="edit-note">编辑笔记</button></div><div class="note-content" id="note-body"></div><details><summary>查看原 Markdown 文本</summary><pre>${esc(note.body)}</pre></details>`); $('edit-note').onclick = () => noteEditor(note); const container = root.querySelector('#note-body'); for (const line of note.body.split('\n')) {
    const image = line.match(/^!\[([^\]]*)\]\((\/api\/assets\/[a-f0-9]{64}\/preview)\)$/);
    if (image) {
        const img = document.createElement('img');
        img.src = image[2];
        img.alt = image[1];
        img.loading = 'lazy';
        container.append(img);
        continue;
    }
    const heading = line.match(/^#{1,3}\s+(.+)/);
    const el = document.createElement(heading ? 'h2' : 'p');
    el.textContent = heading ? heading[1] : line;
    container.append(el);
} }
async function renderEvents() { const id = state.project.id, epoch = ++state.epoch; const events = await api(`/api/projects/${id}/events?limit=100`); if (epoch !== state.epoch)
    return; $('view').innerHTML = `<div class="notice">显示最近 100 条项目事件。这里记录导入、选择、核验、草稿与确认；代码改动的意图和验收以仓库 docs/tasks 为底稿，Notion 同步是可选视图。</div>${events.map(event => `<details class="event-card"><summary>${esc(event.action)} <small>${esc(event.actor)} · ${esc(event.at.slice(0, 19).replace('T', ' '))}</small></summary><pre>${esc(JSON.stringify(event.data, null, 2))}</pre></details>`).join('') || empty('尚无变更记录', '后续操作会留下实际事件，不会生成虚构的完成日志。')}`; }

function preflightBadge(ref) {
    const status = ref.preflight_status || ref.preflight?.status;
    if (!status) return '';
    const badges = {
        unreviewed: '<span class="badge">尚未逐图核验</span>',
        passed: '<span class="badge badge-success">预检推断匹配</span>',
        uncertain: '<span class="badge badge-warning">预检身份存疑</span>',
        transferable: '<span class="badge badge-info">可迁移动作</span>',
        filtered: '<span class="badge badge-danger">已过滤</span>',
        restored: '<span class="badge badge-info">人工恢复</span>'
    };
    const b = badges[status] || `<span class="badge">${esc(status)}</span>`;
    const reason = ref.preflight_reason || ref.preflight?.status_reason || '';
    return `<div class="preflight-badge-row">${b} ${reason ? `<small class="preflight-reason">${esc(reason)}</small>` : ''}</div>`;
}

function recommendationBadges(ref) {
    const rec = ref.recommendation;
    if (!rec) return '';
    const e = rec.evidence || {}, observation = e.visual_observations || {}, pf = e.preflight || {};
    const labels = {unreviewed:'尚未逐图核验',human_visual_review:'人工图像判断',ai_visual_inference:'AI 图像推断，待核对',unknown_producer:'来源未核实的历史判断',local_heuristic:'本地规则线索，不能证明图像内容',deterministic_file_check:'文件与尺寸检查，未做视觉判断',legacy_unverified:'历史预检未核实',stale_context:'项目要求已改变，旧判断待复核',agent_prediction:'Agent 预检推断，待核对'};
    const list = items => (items || []).map(x => `<li>${esc(x)}</li>`).join('');
    return `<div class="recommendation-tags">${(rec.photographic_points || []).map(x => `<span class="tag tag-dim">${esc(x)}</span>`).join('')}</div>
        <details class="evidence-origin"><summary>判断来自哪里</summary>
        <p>来源标题与搜索词只用于发现，不是图片事实：${esc(e.discovery_context?.title || '')} · ${esc(e.discovery_context?.search_query || '')}</p>
        <p>${esc(labels[observation.origin] || '尚无逐图观察')} · ${esc(observation.producer || '')}</p>
        <ul>${list(observation.items)}</ul>
        <p>${esc(labels[pf.origin] || '预检未知')} · ${esc(pf.producer || '')}</p><ul>${list(pf.items)}</ul>
        <p>拍摄方案 / 布光解释（${esc(e.shooting_plan?.producer || '尚无方案')}）：${esc(e.shooting_plan?.interpretation || '')}。这是方案或推断，不是原片光位事实；${e.shooting_plan?.current_context ? '项目条件对应当前版本' : '当前项目条件尚未核验'}。</p>
        <p>你的选择与审美笔记属于个人判断（${e.human_feedback?.preference_origin === 'human_curation' ? '本应用人工填写' : '历史来源未核实'}）：${esc(e.human_feedback?.preference || '')}。K 表示项目用途，X 不自动表示审美不喜欢。</p>
        <p>${esc((rec.unknowns || []).join('；'))}</p></details>`;
}

function renderDetail(ref) {
    const selected=ref.selected_for_project, stage=stages[ref.workflow_stage]||statuses[ref.state];
    const detached=!!ref.detached_at;
    const recycled=ref.decision==='reject';
    const preflightFiltered=state.view==='filtered'&&ref.preflight_filtered;
    const next=ref.analysis_job?'查看制卡任务':ref.card?'检查草稿并确认':'制作现场卡';
    const blockers=(ref.blockers||[]).filter(b=>b.code!=='not_accepted');
    $('detail-panel').innerHTML=`<div class="detail-heading"><span class="eyebrow">${state.view==='field'?'FIELD GUIDE':'YOUR CHOICE'}</span><h2>${esc(ref.title)}</h2><p class="detail-meta">${esc(stage)}${ref.inspiration_id?' · 已有全局收藏':''}</p>${preflightBadge(ref)}${recommendationBadges(ref)}</div>
    ${detached?`<button id="restore-project-use" class="primary">恢复到当前项目</button><p class="muted">这张图只是从当前项目移出，不是 X 淘汰；其他项目和全局收藏不受影响。</p>`:preflightFiltered?`<div class="preflight-actions"><button id="restore-preflight" class="primary">恢复为普通候选</button><button id="make-transferable" class="quiet" style="margin-left:8px;border:1px solid var(--line);">降级为通用灵感</button><p class="muted" style="margin-top:6px;">恢复只解除预检过滤，不自动设为 K/I/M/X；降级直接移入灵感库。</p></div>`:recycled?'<button id="restore-reference" class="primary">恢复这张图片</button><p class="muted">恢复原来的选择，不自动恢复现场卡确认。</p>':`<div class="decision-bar" aria-label="第一轮筛选"><button data-decision="keep" class="${selected?'chosen':''}"><strong>本角色参考</strong><small>K · 值得用于这个项目</small></button><button data-decision="inspiration"><strong>通用灵感</strong><small>I · 归档审美库并移出项目</small></button><button data-decision="maybe" class="${ref.decision==='maybe'?'chosen':''}">待定 <small>M</small></button><button data-decision="reject" class="danger">淘汰 <small>X</small></button></div>`}
    ${!detached&&!recycled&&!selected?'<p class="curation-hint">现在只挑喜欢的。选入项目不等于图中就是这个角色，也不会自动制作现场卡。</p>':''}
    ${selected?`<section class="next-step"><span class="eyebrow">${esc(stage)}</span>${ref.field_ready?'<p>这张卡已由你确认，可从现场卡页或离线包查看。</p>':`<p>${ref.analysis_job?'任务已建立，尚需交给本地 Agent 执行并导回结果。':ref.card?'先看口令、图像判断与来源。确认后才进入现场卡。':ref.review?'分析已有结论；并非每张参考都适合做现场卡。':'只给真正想拍的几张制卡，不必处理全部精选。'}</p><button id="make-card" class="primary" ${!ref.file_available?'disabled':''}>${next}</button>`}</section>`:''}
    ${ref.card?cardMarkup(ref.card,ref.field_ready):ref.review?`<section class="guide-section"><h3>分析结论</h3>${ordered(ref.review.observations)}${ref.review.critical_uncertainties.length?`<p>待确认：${esc(ref.review.critical_uncertainties.join('；'))}</p>`:''}<p>${ref.card?'':'尚未生成资料卡。可保留作审美参考，不强行凑拍摄指令。'}</p></section>`:''}
    ${ref.asset_sha?`<section class="export-share-box">
        <div class="button-row">
            ${ref.archive_path?`<button id="reveal-file-btn" class="primary" title="在 Windows 资源管理器中定位此已确认的 JPG 图片">📂 定位归档 JPG</button>`:`<button id="reveal-file-btn" class="quiet" title="定位底层母图文件">📂 打开文件位置</button>`}
            ${state.projectId?`<button id="reveal-folder-btn" class="${ref.archive_path?'quiet':'primary'}" title="打开此角色已确认文件夹（统一存放所有确认的 JPG 参考图）">📁 打开已确认文件夹</button>`:''}
            <button id="copy-image-btn" class="quiet" title="将原画复制到系统剪贴板，打开微信按 Ctrl+V 即可直接发送给模特">📋 复制发微信</button>
        </div>
        ${ref.archive_path?`<div class="file-path-hint archive-success"><strong>📁 已归档至：</strong><code>${esc(ref.archive_path)}</code></div>`:
          `<div class="file-path-hint"><strong>📁 归档目标：</strong><code>${esc(ref.archive_dir||ref.export_dir||'')} (确认后自动归位)</code></div>`}
        ${ref.archive_error?`<p id="archive-error" class="notice" role="status">选择已保存，归档未完成：${esc(ref.archive_error)}</p>`:''}
        ${ref.local_path?`<div class="file-path-secondary"><small>母本CAS底层：<code>${esc(ref.local_path)}</code></small> ${ref.archive_path?`<button id="reveal-cas-btn" class="tiny-link-btn" title="在资源管理器中查看底层CAS原图">打开母图文件夹</button>`:''}</div>`:''}
        <div id="reveal-status-hint" class="reveal-status-hint" hidden></div>
    </section>`:''}
    <details class="advanced-panel"><summary>审美笔记与借鉴点（选填）</summary><form id="preference-form">${area('喜欢什么／准备借鉴什么','preference',ref.preference,'maxlength="12000"')}${label('借鉴维度（逗号分隔）','borrow',(ref.borrow||[]).join('，'),'text','placeholder="动作、眼神、构图、色彩、光线…"')}<button type="submit">保存审美笔记</button><small id="dirty-indicator"></small></form>${!ref.inspiration_id?'<button id="save-global">同时收藏到我的审美库</button>':'<button id="open-global">打开我的审美库</button>'}</details>
    ${!detached&&!recycled?`<details class="advanced-panel"><summary>跨项目复用与模特沟通</summary><p class="form-help">同一图片文件可以被多个项目引用，不会复制资产。转移只移除当前项目关系，不会把它当成 X。</p><div class="compact-row"><button id="toggle-selection">加入/移出批量选择</button><button id="transfer-reference">复制 / 转移到其他项目</button></div></details>`:""}
    <details class="advanced-panel"><summary>来源、判断修正与手动制卡</summary><p class="form-help">只有需要纠错时才填写。搜索来源不等于角色事实，人工修正不会自动确认现场卡。</p><div class="compact-row"><button id="review-reference">修正图片判断</button><button id="edit-source">来源与标题</button><button id="edit-card">手动编辑资料卡</button><button id="context-reference">发现上下文</button><button id="similar-images">相似图线索</button><button id="replace-image">替换图片</button></div>${blockers.length?`<div class="gate-box"><strong>制卡仍需检查</strong><ul>${blockers.map(b=>`<li>${esc(b.message)}</li>`).join('')}</ul></div>`:''}${ref.legacy_notes?`<details><summary>历史说明（未验证）</summary><pre>${esc(ref.legacy_notes)}</pre></details>`:''}<p class="detail-meta">修订 ${ref.revision} · ${esc(ref.id.slice(0,12))}</p></details>
    ${selected?`<details class="advanced-panel"><summary>拍摄复盘</summary><button id="add-reflection">＋ 记录实拍经验</button>${(ref.reflections||[]).slice(-3).map(x=>`<p>${esc(x.worked||x.failed||x.next_time||'已记录')}</p>`).join('')}</details>`:''}
    ${ref.source.page_url?`<a class="source-link" href="${esc(ref.source.page_url)}" target="_blank" rel="noopener noreferrer">打开来源页 ↗</a>`:''}`;
    listen('detail-panel','[data-decision]','click',(e,n)=>triggerDecision(n.dataset.decision, e.shiftKey));
    if($('copy-image-btn'))$('copy-image-btn').onclick=()=>copyImageToClipboard(ref);
    if($('reveal-file-btn'))$('reveal-file-btn').onclick=()=>revealReferenceFile(ref);
    if($('reveal-folder-btn'))$('reveal-folder-btn').onclick=()=>revealProjectExport();
    if($('reveal-cas-btn'))$('reveal-cas-btn').onclick=()=>revealAssetSha(ref.asset_sha);
    if($('restore-project-use'))$('restore-project-use').onclick=()=>restoreProjectUse(ref).catch(showError);
    if($('restore-preflight'))$('restore-preflight').onclick=()=>restorePreflight(ref).catch(showError);
    if($('make-transferable'))$('make-transferable').onclick=()=>makeTransferable(ref).catch(showError);
    if($('restore-reference'))$('restore-reference').onclick=()=>restoreReference(ref).catch(showError);
    if($('toggle-selection'))$('toggle-selection').onclick=()=>toggleProjectSelection(ref);
    if($('transfer-reference'))$('transfer-reference').onclick=()=>transferReferencesDialog([{id:ref.id,title:ref.title,asset_sha:ref.asset_sha}]);
    if($('make-card'))$('make-card').onclick=()=>{if(!requireSaved())return; (ref.analysis_job?jobHandoff(ref.analysis_job.id):ref.card?Promise.resolve(acceptanceEditor(ref)):newAnalysis([ref.id])).catch(showError);};
    $('preference-form').oninput=()=>{state.dirty=true;$('dirty-indicator').textContent='尚未保存';};
    $('preference-form').onsubmit=e=>{e.preventDefault();savePreference().catch(showError);};
    if($('save-global'))$('save-global').onclick=()=>saveGlobal(ref).catch(showError);
    if($('open-global'))$('open-global').onclick=()=>navigate('inspiration');
    $('review-reference').onclick=()=>{if(requireSaved())reviewEditor(ref);};
    $('edit-source').onclick=()=>{if(requireSaved())sourceEditor(ref);};
    $('edit-card').onclick=()=>{if(requireSaved())cardEditor(ref);};
    $('replace-image').onclick=()=>{if(requireSaved())replaceEditor(ref);};
    $('context-reference').onclick=()=>contextDialog(ref).catch(showError);
    $('similar-images').onclick=()=>similarDialog(ref).catch(showError);
    if($('add-reflection'))$('add-reflection').onclick=()=>{if(requireSaved())reflectionEditor(ref);};
}

function preferenceValues() {
    const form=$('preference-form');if(!form)return{};
    const data=values(form);return {preference:data.preference,borrow:data.borrow.split(/[,，\n]/).map(x=>x.trim()).filter(Boolean)};
}
async function savePreference() {
    const ref=current();if(!ref||state.busy)return;
    const body={expected_revision:ref.revision,...preferenceValues()};state.busy=true;
    try { await api(`/api/${state.view==='inspiration'?'inspirations':'references'}/${ref.id}`,{method:'PATCH',body});state.dirty=false;await loadReferences();toast('审美笔记已保存'); }
    finally {state.busy=false;}
}
async function copyImageToClipboard(ref) {
    if (!ref || !ref.asset_sha) return;
    try {
        toast('正在读取图片并准备复制...');
        const imgUrl = `/api/assets/${ref.asset_sha}/original`;
        const res = await fetch(imgUrl);
        if (!res.ok) throw new Error('无法读取图片文件');
        const blob = await res.blob();
        let pngBlob = blob;
        if (blob.type !== 'image/png') {
            const imgBitmap = await createImageBitmap(blob);
            const canvas = document.createElement('canvas');
            canvas.width = imgBitmap.width;
            canvas.height = imgBitmap.height;
            const ctx = canvas.getContext('2d');
            ctx.drawImage(imgBitmap, 0, 0);
            pngBlob = await new Promise((resolve, reject) => {
                canvas.toBlob(b => b ? resolve(b) : reject(new Error('Canvas 转换 PNG 失败')), 'image/png');
            });
        }
        await navigator.clipboard.write([
            new ClipboardItem({ 'image/png': pngBlob })
        ]);
        toast('✅ 图片已复制到剪贴板！可直接在微信聊天框中 Ctrl+V 粘贴发送给模特');
    } catch (err) {
        showError('复制图片失败: ' + (err.message || err));
    }
}
async function copyTextToClipboard(text) {
    if (!text) return;
    try {
        if (navigator.clipboard && navigator.clipboard.writeText) {
            await navigator.clipboard.writeText(text);
        } else {
            const ta = document.createElement('textarea');
            ta.value = text;
            ta.style.position = 'fixed';
            ta.style.opacity = '0';
            document.body.appendChild(ta);
            ta.select();
            document.execCommand('copy');
            document.body.removeChild(ta);
        }
    } catch (e) {}
}
async function revealReferenceFile(ref) {
    if (!ref) return;
    try {
        let res;
        if (ref.id && !ref.used_in_projects) {
            res = await api(`/api/references/${ref.id}/reveal`, { method: 'POST' });
        } else if (ref.asset_sha) {
            res = await api(`/api/assets/${ref.asset_sha}/reveal`, { method: 'POST' });
        }
        if (res && res.path) {
            await copyTextToClipboard(res.path);
            const hint = $('reveal-status-hint');
            if (hint) {
                hint.hidden = false;
                hint.innerHTML = `📂 <strong>已在电脑中打开所在文件夹：</strong><br><code>${esc(res.folder || res.path)}</code><br><small style="color:var(--muted)">目标文件：<code>${esc(res.filename || '')}</code>（完整路径已复制到剪贴板，可随时粘贴）</small>`;
            }
            toast(`📂 已打开文件夹，路径已复制: ${res.path}`);
        } else {
            toast('📂 已在资源管理器中打开该文件夹');
        }
    } catch (err) {
        showError(err);
    }
}
async function revealAssetSha(sha) {
    if (!sha) return;
    try {
        const res = await api(`/api/assets/${sha}/reveal`, { method: 'POST' });
        if (res && res.path) {
            await copyTextToClipboard(res.path);
            const hint = $('reveal-status-hint');
            if (hint) {
                hint.hidden = false;
                hint.innerHTML = `📂 <strong>已在电脑中打开底层母图文件夹：</strong><br><code>${esc(res.folder || res.path)}</code><br><small style="color:var(--muted)">母图文件：<code>${esc(res.filename || '')}</code>（路径已复制）</small>`;
            }
            toast(`📂 已打开底层母图文件夹，路径已复制: ${res.path}`);
        } else {
            toast('📂 已在资源管理器中打开底层母图文件夹');
        }
    } catch (err) {
        showError(err);
    }
}
async function revealProjectExport() {
    if (!state.projectId) return;
    try {
        const res = await api(`/api/projects/${state.projectId}/reveal-export`, { method: 'POST' });
        if (res && res.path) {
            await copyTextToClipboard(res.path);
            const hint = $('reveal-status-hint');
            if (hint) {
                hint.hidden = false;
                hint.innerHTML = `📁 <strong>已在电脑中打开已确认文件夹：</strong><br><code>${esc(res.path)}</code><br><small style="color:var(--muted)">（此处汇集了本角色所有已确认的 JPG 参考图，路径已复制）</small>`;
            }
            toast(`📁 已打开已确认文件夹，路径已复制: ${res.path}`);
        } else {
            toast('📁 已在资源管理器中打开导出文件夹');
        }
    } catch (err) {
        showError(err);
    }
}
function matchesCurrentView(ref) {
    if(state.view==='recycle')return ref.decision==='reject'||!!ref.detached_at;
    if(ref.detached_at)return false;
    if(state.view==='filtered')return !!ref.preflight_filtered;
    if(ref.decision==='reject'&&state.decision!=='reject')return false;
    if(state.view==='selected')return ref.selected_for_project;
    if(state.view==='field')return ref.field_ready;
    if(state.decision==='keep')return ref.decision==='keep'&&ref.lane==='field';
    return !state.decision||ref.decision===state.decision;
}
async function decide(choice, rejectionReason = null, aestheticNegative = false) {
    const ref=current();if(!ref||state.busy||state.view==='inspiration')return;
    const index=state.refs.findIndex(x=>x.id===ref.id), hasNextPage=state.offset+state.limit<state.total;
    state.busy=true;
    try {
        let updated;
        if(choice==='inspiration'){
            const body={expected_revision:ref.revision,...(state.dirty?preferenceValues():{})};
            updated=await api(`/api/references/${ref.id}/archive-inspiration`,{method:'POST',body});
        }else{
            const body={expected_revision:ref.revision,decision:choice,...(state.dirty?preferenceValues():{})};
            if(choice==='keep')body.lane='field';
            if(choice==='reject'){body.rejection_reason=rejectionReason || '';body.is_aesthetic_negative=aestheticNegative;}
            updated=await api(`/api/references/${ref.id}`,{method:'PATCH',body});
        }
        const next=state.autoAdvance?state.refs[index+1]?.id:ref.id;
        const removed=!matchesCurrentView(updated);
        state.refs=state.refs.map(r=>r.id===ref.id?updated:r).filter(matchesCurrentView);
        // Choose a surviving neighbour BEFORE rendering; a deleted active ID must
        // never make current() fall back to the first thumbnail for one frame.
        state.activeId=state.refs.some(r=>r.id===next)?next:
            state.refs[Math.min(index,state.refs.length-1)]?.id||null;
        state.dirty=false;
        if(state.autoAdvance&&!removed&&!next&&hasNextPage){
            state.offset+=state.limit;state.activeId=null;
            // The next page is an intentional list change, not an intermediate
            // render of this page with its first image accidentally selected.
        }else{
            renderReferenceView(); // Reconcile membership without remounting the strip.
        }
        await loadReferences(removed?index:0);await renderStats();
        toast(choice==='inspiration'?'已直接归档至审美库，不占用角色参考位':choice==='reject'?'已淘汰；可从回收入口恢复':choice==='keep'?(updated.archive_error?'已选为本角色参考；归档未完成：'+updated.archive_error:updated.archive_path?'已选为本角色参考，已归档至角色已确认文件夹':'已选为本角色参考'):'已标为待定');
    } finally {state.busy=false;}
}

function triggerDecision(choice, skipPrompt = false) {
    if (choice === 'reject' && !skipPrompt) {
        showRejectReasonDialog((reason, aesthetic) => decide('reject', reason, aesthetic).catch(showError));
    } else {
        decide(choice).catch(showError);
    }
}

function showRejectReasonDialog(onConfirm) {
    const dlg = $('reject-dialog');
    if (!dlg) {
        onConfirm('');
        return;
    }
    const input = $('reject-reason-input');
    input.value = '';
    $('reject-aesthetic').checked = false;
    dlg.querySelectorAll('.quick-tag').forEach(t => t.classList.remove('active'));

    const cleanup = () => {
        try { dlg.close(); } catch(e){}
        $('reject-skip-btn').onclick = null;
        $('reject-confirm-btn').onclick = null;
        $('reject-cancel-btn').onclick = null;
        input.onkeydown = null;
    };

    $('reject-skip-btn').onclick = () => {
        cleanup();
        onConfirm('');
    };

    $('reject-confirm-btn').onclick = () => {
        const val = input.value.trim();
        cleanup();
        onConfirm(val, $('reject-aesthetic').checked);
    };

    $('reject-cancel-btn').onclick = () => {
        cleanup();
    };

    input.onkeydown = (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            const val = input.value.trim();
            cleanup();
            onConfirm(val, $('reject-aesthetic').checked);
        } else if (e.key === 'Escape') {
            e.preventDefault();
            cleanup();
        }
    };

    dlg.querySelectorAll('.quick-tag').forEach(tagBtn => {
        tagBtn.onclick = () => {
            const tag = tagBtn.dataset.tag;
            if (input.value) {
                if (!input.value.includes(tag)) input.value += '，' + tag;
            } else {
                input.value = tag;
            }
            tagBtn.classList.add('active');
            input.focus();
        };
    });

    dlg.showModal();
    input.focus();
}

async function optimizeSkillFromRejectionReasons() {
    try {
        state.busy = true;
        toast('正在整理人工淘汰理由...');
        const res = await api('/api/skills/curator/refine', { method: 'POST' });

        const content = `
            <div class="optimize-summary-card">
                <span class="eyebrow">REJECTION NOTES · 人工淘汰理由</span>
                <h3>${esc(res.summary)}</h3>
                <p class="muted">按关键词分组 ${res.total_reasons_collected} 条人工淘汰理由。分组不是视觉分析；未更新 Skill 或长期偏好：</p>
                <div class="rules-categories">
                    ${(res.categories || []).map(cat => `
                        <div class="rule-cat-block">
                            <h4>🏷️ ${esc(cat.category)} <small>(${cat.count}条案例)</small></h4>
                            <ul>
                                ${cat.core_principles.map(p => `<li>${esc(p)}</li>`).join('')}
                            </ul>
                        </div>
                    `).join('')}
                </div>
                <div class="dialog-actions" style="margin-top:16px;">
                    <button id="close-opt-dialog" class="primary">关闭理由汇总</button>
                </div>
            </div>
        `;
        modal('人工淘汰理由汇总', content);
        if ($('close-opt-dialog')) $('close-opt-dialog').onclick = closeModal;
    } catch (err) {
        showError('整理淘汰理由失败: ' + (err.message || err));
    } finally {
        state.busy = false;
    }
}

async function restoreReference(ref) {
    if(state.busy)return;state.busy=true;
    try{await api(`/api/references/${ref.id}/restore`,{method:'POST',body:{expected_revision:ref.revision}});await loadReferences();await renderStats();toast('已恢复原选择；现场卡确认仍需重新检查');}
    finally{state.busy=false;}
}
async function restoreProjectUse(ref) {
    if(state.busy)return;state.busy=true;
    try{await api(`/api/references/${ref.id}/restore-project-use`,{method:"POST",body:{expected_revision:ref.revision}});await loadReferences();await renderStats();toast("已恢复到当前项目；K/I/M/X 没有被自动修改");}
    finally{state.busy=false;}
}
async function restorePreflight(ref) {
    if(state.busy)return;state.busy=true;
    try{await api(`/api/references/${ref.id}/preflight-override`,{method:'POST',body:{expected_revision:ref.revision,action:'restore'}});await loadReferences();await renderStats();toast('已恢复为普通候选；仍需你决定 K/I/M/X');}
    finally{state.busy=false;}
}
async function makeTransferable(ref) {
    if(state.busy)return;state.busy=true;
    try{
        const index=state.refs.findIndex(x=>x.id===ref.id);
        await api(`/api/references/${ref.id}/make-transferable`,{method:'POST',body:{expected_revision:ref.revision}});
        await loadReferences(index);
        await renderStats();
        toast('已降级归档至审美库，不占用角色参考位');
    }
    finally{state.busy=false;}
}

async function saveGlobal(ref) {
    if(!requireSaved()||state.busy)return;state.busy=true;
    try{await api(`/api/references/${ref.id}/inspiration`,{method:'POST',body:{expected_revision:ref.revision}});await loadReferences();toast('已独立收藏；本角色选择保持不变');}
    finally{state.busy=false;}
}
function acceptanceEditor(ref) {
    const s=ref.source;
    const root=modal('检查这张现场卡',`<p class="notice">一张图对应一张卡。确认的是这张图、当前要求和下面的草稿；AI 不会代替你验收。</p><h3>图片判断</h3><p>${esc(kinds[ref.review?.kind]||'未知')} · 角色关系：${esc(({exact:'判断为同角色',adapted:'跨角色／普通人像借鉴',unknown:'未知',irrelevant:'不相关'})[ref.review?.character_match]||'未知')}</p>${ordered(ref.review?.observations||[])}${ref.review?.critical_uncertainties?.length?`<p class="error-text">疑点：${esc(ref.review.critical_uncertainties.join('；'))}</p>`:''}${cardMarkup(ref.card,false)}<div class="compact-row"><button id="correct-review">判断错了，修正</button><button id="correct-card">修改口令／方案</button><button id="reanalyze-card">重新交给 Agent</button></div><form><h3>确认来源与适用性</h3>${label('原发布页','page_url',s.page_url,'url')}${select('来源／权利说明','rights',{unknown:'未确认',personal_reference:'仅私人参考',owned:'我拥有此图使用权',licensed:'已获授权'},s.rights)}${area('自有作品或来源说明','rights_note',s.rights_note)}${check('允许跨角色／普通人像借鉴（不冒充同角色）','allow_cross_domain',ref.allow_cross_domain)}<label class="check"><input type="checkbox" name="source_confirmed" required><span>我已核对图片、口令、安全与来源；不是仅依据搜索标题</span></label><div class="form-actions"><button id="accept-card" type="submit" class="primary">我已核对，确认为现场卡</button></div></form>`);
    $('correct-review').onclick=()=>reviewEditor(ref);$('correct-card').onclick=()=>cardEditor(ref);
    $('reanalyze-card').onclick=()=>newAnalysis([ref.id]).catch(showError);
    formSubmit(root,data=>updateAction(ref,'accept',{expected_revision:ref.revision,allow_cross_domain:data.allow_cross_domain,source:{...s,page_url:data.page_url,rights:data.rights,rights_note:data.rights_note,source_confirmed:data.source_confirmed}},'现场卡已由你确认'));
}
async function contextDialog(ref) {
    if(!ref.asset_sha)return;
    const data=await api(`/api/assets/${ref.asset_sha}/context`);
    modal('图片事实与发现上下文',`<p class="notice">发现意图不是图片事实；为某角色搜索到，不代表已确认图中是这个角色。</p><h3>发现记录</h3>${data.discoveries.map(d=>`<section><strong>${esc(({exact_character:'A 角色精准方向',transferable_pose:'B 动作迁移方向',aesthetic:'C 审美拓展',unknown:'未记录意图'})[d.intent]||d.intent)}</strong><p>${esc(d.reason||'未写借鉴原因')}</p><small>${esc(d.source.search_query||'无检索词')} · ${esc(d.project_snapshot?.character||'没有可靠的历史项目快照')}</small><p>${esc(d.source.page_url||d.discovery_url||'未记录来源')}</p></section>`).join('')||'<p>没有发现上下文；可能是独立收藏或主动引用。</p>'}<details><summary>独立图像观察历史（不继承角色判断或卡片确认）</summary><pre>${esc(JSON.stringify(data.observations,null,2))}</pre></details>`);
}


function renderInspirationDetail(item) {
    $('detail-panel').innerHTML=`<span class="eyebrow">INSPIRATION · INDEPENDENT ASSET</span><h2>${esc(item.title)}</h2><p class="curation-hint">这是独立收藏，不归属于任何角色。动作、表情、光影或电影画面都可以先留下来。</p><div class="compact-row">${item.active?`<button id="use-inspiration" class="primary" ${!item.file_available?'disabled':''}>引用到拍摄项目</button><button id="remove-inspiration" class="quiet">移出审美库</button>`:'<button id="restore-inspiration" class="primary">恢复收藏</button>'}</div>${item.asset_sha?`<section class="export-share-box"><div class="button-row"><button id="copy-image-btn" class="primary" title="将原画复制到系统剪贴板，打开微信按 Ctrl+V 即可直接发送给模特">📋 复制图片发微信 (Ctrl+V)</button><button id="reveal-file-btn" class="quiet" title="在 Windows 资源管理器中打开此文件夹">📂 打开文件位置</button></div><div id="reveal-status-hint" class="reveal-status-hint" hidden></div></section>`:''}<section class="guide-section"><form id="preference-form">${area('喜欢什么／准备借鉴什么','preference',item.preference,'maxlength="12000"')}${label('借鉴维度（逗号分隔）','borrow',(item.borrow||[]).join('，'),'text','placeholder="动作、眼神、构图、色彩、光线…"')}<button type="submit">保存审美笔记</button><small id="dirty-indicator"></small></form></section><section class="guide-section"><h3>已被这些项目选作参考</h3>${item.used_in_projects.map(p=>`<button data-use-project="${esc(p.project_id)}" data-reference="${esc(p.reference_id)}">${esc(p.character)}</button>`).join('')||'<p>还没有角色引用它，也可以一直独立收藏。</p>'}</section><details class="advanced-panel"><summary>来源与收藏上下文</summary>${item.source.page_url?`<a href="${esc(item.source.page_url)}" target="_blank" rel="noopener noreferrer">打开来源页 ↗</a>`:'<p>未记录原发布页</p>'}<button id="inspiration-source">修改标题与来源</button><button id="context-reference">发现上下文</button>${item.context_notes.map(n=>`<p>${esc(state.projects.find(p=>p.id===n.project_id)?.character||'历史项目')}：${esc(n.preference)} ${esc(n.borrow.join('、'))}</p>`).join('')}</details>`;
    if($('copy-image-btn'))$('copy-image-btn').onclick=()=>copyImageToClipboard(item);
    if($('reveal-file-btn'))$('reveal-file-btn').onclick=()=>revealReferenceFile(item);
    $('preference-form').oninput=()=>{state.dirty=true;$('dirty-indicator').textContent='尚未保存';};
    $('preference-form').onsubmit=e=>{e.preventDefault();savePreference().catch(showError);};
    if($('use-inspiration'))$('use-inspiration').onclick=()=>{if(requireSaved())useInspirationDialog(item);};
    if($('remove-inspiration'))$('remove-inspiration').onclick=()=>toggleInspiration(item,false).catch(showError);
    if($('restore-inspiration'))$('restore-inspiration').onclick=()=>toggleInspiration(item,true).catch(showError);
    $('context-reference').onclick=()=>contextDialog(item).catch(showError);
    $('inspiration-source').onclick=()=>inspirationEditor(item);
    listen('detail-panel','[data-use-project]','click',async(e,n)=>openProjectReference(n.dataset.useProject,n.dataset.reference));
}
async function toggleInspiration(item,active) {
    if(!safeDiscard())return;state.busy=true;
    try{await api(`/api/inspirations/${item.id}`,{method:'PATCH',body:{expected_revision:item.revision,active}});state.dirty=false;await loadReferences();toast(active?'收藏已恢复':'已移出审美库；项目中的引用仍然保留');}
    finally{state.busy=false;}
}
function inspirationEditor(item) {
    if(!requireSaved())return;
    const root=modal('修改收藏标题与来源',`<form>${label('标题','title',item.title)}${label('原发布页','page_url',item.source.page_url,'url')}${label('作者','author',item.source.author)}<div class="form-actions"><button type="submit" class="primary">保存</button></div></form>`);
    formSubmit(root,async data=>{await api(`/api/inspirations/${item.id}`,{method:'PATCH',body:{expected_revision:item.revision,title:data.title,source:{...item.source,page_url:data.page_url,author:data.author,source_confirmed:false}}});closeModal();await loadReferences();});
}
async function openProjectReference(projectId,referenceId) {
    if(!safeDiscard())return;
    const ref=await api(`/api/references/${referenceId}`);
    state.project=state.projects.find(p=>p.id===projectId);
    resetFilters();state.view=ref.detached_at?'recycle':ref.preflight_filtered?'filtered':ref.decision==='reject'?'recycle':ref.selected_for_project?'selected':'references';
    state.activeId=ref.id;state.focusId=ref.id;await refreshView();
}
function useInspirationDialog(item) {
    if(!state.projects.length){toast('先建立一个拍摄项目，独立收藏会留在这里');projectEditor();return;}
    const root=modal('同一图片，引用到另一个项目',`<form><p class="notice">不会复制图片文件，也不会继承其他项目的角色判断、资料卡或人工确认。已有选择（包括淘汰）保持不变。</p>${select('拍摄项目','project_id',Object.fromEntries(state.projects.map(p=>[p.id,p.character+(p.costume?' / '+p.costume:'')])),state.project?.id)}<div class="form-actions"><button type="submit" class="primary">引用并查看</button></div></form>`);
    formSubmit(root,async data=>{const result=await api(`/api/inspirations/${item.id}/use`,{method:'POST',body:{expected_revision:item.revision,project_id:data.project_id}});closeModal();await openProjectReference(data.project_id,result.reference.id);toast(result.preserved_existing_choice?'已打开现有引用；没有改掉历史选择':'已选为这个项目的参考；尚未核验角色或制卡');});
}
async function newAnalysis(ids) {
    if(state.busy)return;
    if(state.dirty)await savePreference();
    state.busy=true;
    try{const job=await api(`/api/projects/${state.project.id}/jobs`,{method:'POST',body:{kind:'analysis',reference_ids:ids}});await loadReferences();await jobHandoff(job.id);return job;}
    finally{state.busy=false;}
}
async function jobHandoff(jobId) {
    const job=await api(`/api/jobs/${jobId}`), bundle=await api(`/api/jobs/${jobId}/bundle`);
    const prompt=`请在 Photography Reference Lab 项目中处理任务 ${job.id}。先执行 python -m ref_lab export-job --job ${job.id} --output job-${job.id.slice(0,8)}.zip（已有包则直接读取，不覆盖）。解压后读取 AGENT_TASK.md 与完整 job.json，按协议使用 ${job.kind==='collection'?'BrowserSkill 搜图':'独立图片逐张分析制卡'}，交回结果并用 import-job 导入。不要改用户的选择或代替确认；没有独立 API 费用。受阻如实报告。若本机不是同一 LAB_DATA_DIR，改用我交给你的任务 ZIP。`;
    const isAnalysis = job.kind === 'analysis';
    const actionBtnText = isAnalysis ? '✨ 本地 Antigravity 一键分析' : '启动已配置的本地采集 Agent';
    const actionHelp = isAnalysis ? '直接调用本机已登录的 Antigravity，自动解析图片并生成现场卡草稿；无需下载和手动导入。' : '需预先配置 LAB_COLLECTION_COMMAND 本地适配器。Agent 自主选择来源；未配置或受阻时不会改用备用抓图。也可使用下面的任务包交接。';
    const root=modal(isAnalysis?'制作现场卡 · 本地 Agent':'让 Agent 搜一批好参考',`<p id="agent-run-status" class="notice" role="status">${esc(statuses[job.status])} · ${esc(job.detail)}</p><div class="action-banner"><button id="run-antigravity" class="primary" style="width:100%;font-size:14px;padding:10px 16px;margin-bottom:6px">${esc(actionBtnText)}</button><p class="form-help" style="margin-bottom:14px">${esc(actionHelp)}</p></div><h3>1 · 取得完整任务</h3><p>包含角色、完整自由要求、器材、任务快照${isAnalysis?'和独立原图':'及三层检索策略'}。</p><button id="download-task" class="primary">下载任务 ZIP</button><h3>2 · 交给 Codex / Antigravity</h3><button id="copy-agent-task">复制执行提示词</button><details><summary>查看本轮协议</summary><pre>${esc(bundle.agent_instructions)}</pre></details><h3>3 · 导回结果，由你检查</h3><button id="import-task-result">${isAnalysis?'导入分析结果':'导入候选包'}</button><p class="form-help">也可让 Agent 在同一数据目录运行 import-job；导入的图片仍待你挑选，资料卡仍是草稿。</p>`);
    if ($('run-antigravity')) {
        $('run-antigravity').disabled = ['running','succeeded','cancelled'].includes(job.status);
        $('run-antigravity').onclick = async () => {
            const btn = $('run-antigravity');
            btn.disabled = true;
            btn.textContent = isAnalysis ? '本地 Antigravity 正在分析…' : '本地采集 Agent 执行中；等待真实回执…';
            try {
                const result = await api(`/api/jobs/${job.id}/run-antigravity`, { method: 'POST' });
                const ownsDialog = $('run-antigravity') === btn && $('editor').open;
                if (ownsDialog) $('agent-run-status').textContent = `${statuses[result.status]||'未知状态'} · ${result.detail||'没有执行详情'}`;
                if (result.status === 'succeeded') {
                    toast(isAnalysis ? '分析结果已导入；仍需逐张检查，不能代替人工确认' : '候选包已导入；角色、摄影质量和个人喜好尚待核验');
                    if (ownsDialog) closeModal();
                } else {
                    const label = {blocked:'采集或分析受阻',failed:'执行失败',cancelled:'任务已取消',running:'任务仍在执行'}[result.status]||'未确认完成';
                    toast(`${label}：${result.detail||'请检查任务状态'}`, result.status !== 'running');
                    if (ownsDialog) {
                        btn.disabled = ['running','succeeded','cancelled'].includes(result.status);
                        btn.textContent = actionBtnText;
                    }
                }
                await loadReferences();
                await renderStats();
                if (state.view === 'jobs') await renderJobs();
            } catch (error) {
                showError(error);
                btn.disabled = false;
                btn.textContent = actionBtnText;
            }
        };
    }
    $('download-task').onclick=()=>download(`/api/jobs/${job.id}/download`,`job-${job.id.slice(0,8)}.zip`).catch(showError);
    $('copy-agent-task').onclick=()=>copy(prompt);
    $('import-task-result').onclick=()=>importDialog(job.kind==='collection'?'candidates':'analyses',job.id,job.project_id);
    return root;
}
function collectionEditor(projectId=state.project?.id) {
    if(!state.projects.length){projectEditor();return;}
    const root=modal('这次想找什么参考？',`<form>${select('拍摄项目','project_id',Object.fromEntries(state.projects.map(p=>[p.id,p.character+(p.costume?' / '+p.costume:'')])),projectId)}${area('本轮自由要求','notes','','placeholder="例如：先找同皮肤真人正片；多找坐姿、回眸和衣摆动态，再补电影光影参考。" maxlength="12000"')}${label('期望候选数量（质量优先，不凑数）','target_count',80,'number','min="1" max="500" required')}<p class="form-help">角色、作品、版本、器材和项目完整要求一并保存。来源由 Agent 根据角色、任务质量与实际可用性选择；不限定站点顺序，登录或访问受阻应停止并报告。</p><div class="form-actions"><button type="submit" class="primary">建立采集任务</button></div></form>`);
    formSubmit(root,async data=>{const job=await api(`/api/projects/${data.project_id}/jobs`,{method:'POST',body:{kind:'collection',notes:data.notes,target_count:Number(data.target_count)}});closeModal();await jobHandoff(job.id);});
}
async function renderJobs() {
    const epoch=++state.epoch,jobs=await api('/api/jobs');if(epoch!==state.epoch)return;
    $('view').dataset.shell='';
    $('view').innerHTML=`<div class="notice">默认使用 BrowserSkill + Codex / Antigravity。先建立任务，再交给 Agent；网页不会把“待执行”显示成已搜完。</div><div class="toolbar"><button id="create-collection" class="primary">＋ 建立采集任务</button><button id="refresh-jobs">刷新结果</button></div><div class="job-grid">${jobs.map(j=>`<article class="job-card" data-job="${j.id}"><div class="compact-row">${badge(j.kind==='collection'?'搜图':'制卡')}${badge(statuses[j.status],j.status)}</div><h3>${esc(j.project_snapshot?.character||state.projects.find(p=>p.id===j.project_id)?.character||'历史项目')}</h3><p>${esc(j.detail)}</p><p>${j.kind==='collection'?`实际导入 ${j.imported_ids.length} 个候选`:`完成 ${j.completed_ids.length} / ${j.reference_ids.length} 张分析 · 尚需你确认现场卡`}</p><small>${esc(j.created_at.slice(0,16).replace('T',' '))}</small><div class="compact-row"><button data-action="handoff">任务与结果</button>${j.kind==='collection'&&j.imported_ids.length?'<button data-action="candidates">挑这批图片</button>':''}${j.kind==='analysis'&&j.reference_ids.length?'<button data-action="reference">查看这张参考</button>':''}${!['succeeded','cancelled'].includes(j.status)?'<button data-action="cancel" class="quiet">取消</button>':''}</div><details><summary>要求、来源检查与缺口</summary><pre>${esc(JSON.stringify({project:j.project_snapshot,notes:j.notes,report:j.execution_report},null,2))}</pre></details></article>`).join('')||empty('从一轮具体需求开始','任务保存完整要求和真实执行回执；制卡从某张角色精选中的“制作现场卡”开始。')}</div>`;
    $('create-collection').onclick=()=>collectionEditor();$('refresh-jobs').onclick=()=>renderJobs().catch(showError);
    listen('view','[data-action]','click',async(e,n)=>{
        const job=jobs.find(j=>j.id===n.closest('[data-job]').dataset.job);
        if(n.dataset.action==='handoff')return jobHandoff(job.id);
        if(n.dataset.action==='reference')return openProjectReference(job.project_id,job.reference_ids[0]);
        if(n.dataset.action==='candidates'){if(!safeDiscard())return;state.project=state.projects.find(p=>p.id===job.project_id);resetFilters();state.jobId=job.id;state.view='references';return refreshView();}
        if(n.dataset.action==='cancel'){await api(`/api/jobs/${job.id}/status`,{method:'POST',body:{expected_revision:job.revision,status:'cancelled',detail:'用户取消，已有结果保留'}});await renderJobs();}
    });
}


function importDialog(mode='images',jobId='',explicitProject=null) {
    const global=state.view==='inspiration'&&!jobId;
    const projectId=explicitProject||state.project?.id;
    const names=jobId?{[mode]:mode==='analyses'?'Agent 分析 JSON':'候选 ZIP 包'}:global?{images:'独立图片（直接收藏）'}:{images:'独立图片',candidates:'候选 ZIP 包',notion:'Notion 导出 ZIP',analyses:'Agent 分析 JSON'};
    if(!global&&!projectId&&mode!=='notion'){toast('先建立拍摄项目');return;}
    const root=modal(global?'收藏独立图片':'导入结果',`<form>${select('导入类型','import_type',names,mode)}<div class="drop-zone"><strong>每张图独立保存；相同字节只存一份</strong><input id="import-files" type="file" name="file" ${mode==='images'?'multiple accept="image/jpeg,image/png,image/webp"':mode==='analyses'?'accept=".json"':'accept=".zip"'} required></div>${mode==='images'?label('原发布页（选填）','page_url','','url')+label('作者（选填）','author'):''}<p class="form-help">${global?'直接进入我的审美库，不需要角色。':'候选仍待你筛选，AI 资料卡仍是草稿。'} ${jobId?'本次任务：'+esc(jobId):''}</p><div class="form-actions"><button type="submit" class="primary">开始导入</button></div><p id="import-progress"></p></form>`);
    root.querySelector('[name=import_type]').onchange=e=>importDialog(e.target.value,jobId,projectId);
    formSubmit(root,async(data,form)=>{
        const files=[...form.querySelector('[type=file]').files],report={created:0,existing:0,errors:[]};
        if(mode==='images'){
            for(let i=0;i<files.length;i++){
                $('import-progress').textContent=`正在保存 ${i+1} / ${files.length}`;
                try{
                    const body=new FormData();body.set('file',files[i]);
                    const asset=await api('/api/assets',{method:'POST',body});
                    const result=await api(global?'/api/inspirations':`/api/projects/${projectId}/references`,{method:'POST',body:{asset_sha:asset.id,title:files[i].name.slice(0,400),source:{page_url:data.page_url,author:data.author,obtained_as:'as_received'},...(global?{}:{job_id:jobId})}});
                    report[result.created?'created':'existing']++;
                }catch(error){report.errors.push({file:files[i].name,error:error.message});}
            }
        }else{
            const body=new FormData();body.set('file',files[0]);if(jobId)body.set('job_id',jobId);
            Object.assign(report,await api(mode==='notion'&&state.view==='notes'?'/api/imports/notion':`/api/projects/${projectId}/imports/${mode}`,{method:'POST',body}));
        }
        closeModal();await refreshView();
        const imported=Array.isArray(report.imported)?report.imported.length:null;
        modal('导入结果',`<h3>${report.errors.length?'有条目未通过，请检查':'结果已保存'}</h3><p>${imported!==null?`成功分析 ${imported} 张，仍待你检查`:`新增 ${report.created}，已有 ${report.existing}`} · 错误 ${report.errors.length}</p><details ${report.errors.length?'open':''}><summary>详细回执</summary><pre>${esc(JSON.stringify(report,null,2))}</pre></details><button id="close-receipt" class="primary">回到图片检查</button>`);
        $('close-receipt').onclick=closeModal;
    });
}
async function renderNotes() {
    const epoch=++state.epoch,notes=await api('/api/notes');if(epoch!==state.epoch)return;
    $('view').dataset.shell='';
    $('view').innerHTML=`<div class="toolbar"><button id="new-note" class="primary">＋ 写摄影笔记</button><button id="import-notion">导入 Notion</button><small>独立笔记与历史项目笔记都在这里。</small></div><div class="note-grid">${notes.map(n=>`<article class="note-card" data-note="${n.id}" tabindex="0"><span class="eyebrow">${esc(state.projects.find(p=>p.id===n.project_id)?.character||'我的摄影笔记')}</span><h3>${esc(n.title)}</h3><p>${esc(n.body.slice(0,300))}</p><small>${esc(n.source_path||n.created_at.slice(0,10))}</small></article>`).join('')||empty('留住自己的拍摄方法','可以写下观察和复盘，或导入 Notion Markdown & CSV ZIP。')}</div>`;
    $('new-note').onclick=()=>noteEditor();$('import-notion').onclick=()=>importDialog('notion');
    listen('view','[data-note]','click',(e,n)=>openNote(notes.find(x=>x.id===n.dataset.note)));
    listen('view','[data-note]','keydown',(e,n)=>{if(e.key==='Enter')openNote(notes.find(x=>x.id===n.dataset.note));});
}

async function finishScreeningSessionModal() {
    if (!state.project) return;
    try {
        const currentSess = await api(`/api/projects/${state.project.id}/screening-sessions/current`);
        const summary = await api(`/api/screening-sessions/${currentSess.id}/finish`, { method: 'POST' });
        const stats = summary.stats || {};
        const hypotheses = summary.hypotheses || [];
        const content = `
        <div class="session-summary-dialog">
            <p class="form-help">已汇总本轮记录的最终选择。保留与淘汰不自动推导光线、机位或长期偏好；确认后保存可追溯的反馈与总结。</p>
            <div class="stats-grid" style="display:flex;gap:12px;margin:12px 0;">
                <div class="stat-box" style="flex:1;background:var(--soft);padding:8px 12px;border-radius:6px;text-align:center;">
                    <div style="font-size:20px;font-weight:bold;">${stats.viewed || 0}</div>
                    <small>有选择记录的图片</small>
                </div>
                <div class="stat-box" style="flex:1;background:var(--soft);padding:8px 12px;border-radius:6px;text-align:center;">
                    <div style="font-size:20px;font-weight:bold;color:var(--accent);">${stats.keep || 0}</div>
                    <small>保留(K)</small>
                </div>
                <div class="stat-box" style="flex:1;background:var(--soft);padding:8px 12px;border-radius:6px;text-align:center;">
                    <div style="font-size:20px;font-weight:bold;color:var(--gold);">${stats.inspiration || 0}</div>
                    <small>灵感(I)</small>
                </div>
                <div class="stat-box" style="flex:1;background:var(--soft);padding:8px 12px;border-radius:6px;text-align:center;">
                    <div style="font-size:20px;font-weight:bold;">${stats.maybe || 0}</div>
                    <small>待定(M)</small>
                </div>
                <div class="stat-box" style="flex:1;background:var(--soft);padding:8px 12px;border-radius:6px;text-align:center;">
                    <div style="font-size:20px;font-weight:bold;color:var(--danger);">${stats.reject || 0}</div>
                    <small>淘汰(X)</small>
                </div>
            </div>

            <form id="session-confirm-form">
                <h3 style="margin-top:16px;">本轮选择总结（勾选你愿意保存的记录）</h3>
                ${hypotheses.length ? hypotheses.map(h => `
                    <label class="check" style="margin-bottom:8px;align-items:flex-start;">
                        <input type="checkbox" name="hypothesis" value="${esc(h.text)}">
                        <span>
                            <strong>${esc(h.text)}</strong><br>
                            <small class="muted">依据: ${esc(h.rationale)} · 置信度: ${esc(h.confidence)}</small>
                        </span>
                    </label>
                `).join('') : '<p class="muted">本轮动作量较少，尚未形成显著的统计倾向假说。</p>'}

                <div style="margin:16px 0;padding:12px;background:#f9f9f9;border-radius:8px;border:1px solid var(--line);">
                    <label class="check">
                        <input type="radio" name="apply_choice" value="true">
                        <span><strong>保存到长期反馈记录</strong>（保留总结与样本，不自动改数值权重）</span>
                    </label>
                    <label class="check" style="margin-top:6px;">
                        <input type="radio" name="apply_choice" value="false" checked>
                        <span><strong>这轮不学习</strong>（仅记录筛选完成，不影响全局画像与后续推荐权重）</span>
                    </label>
                </div>

                <div class="form-actions">
                    <button type="submit" class="primary">确认完成本轮筛选</button>
                </div>
            </form>
        </div>`;
        const root = modal('本轮筛选总结与偏好确认', content);
        root.querySelector('#session-confirm-form').onsubmit = async (e) => {
            e.preventDefault();
            const checkedHypotheses = [...root.querySelectorAll('input[name=hypothesis]:checked')].map(input => input.value);
            const applyChoice = root.querySelector('input[name=apply_choice]:checked').value === 'true';
            const result = await api(`/api/screening-sessions/${currentSess.id}/confirm`, {
                method: 'POST',
                body: {
                    accepted_hypotheses: checkedHypotheses,
                    apply_to_profile: applyChoice
                }
            });
            closeModal();
            toast(result.status === 'completed_feedback_saved' ? '本轮总结与反馈已保存；权重未自动调整' : '本轮筛选已完成（未更新画像）');
            await loadReferences();
            await renderStats();
        };
    } catch (err) {
        showError(err);
    }
}

async function renderProfile() {
    const epoch = ++state.epoch;
    $('view').dataset.shell = '';
    const [profile, history] = await Promise.all([
        api('/api/profile'),
        api('/api/profile/history')
    ]);
    if (epoch !== state.epoch) return;

    const dims = profile.dimensions || {};
    const dimensionRows = Object.entries(dims).map(([category, weights]) => {
        const catNames = { angles: '视角偏好', framing: '景别偏好', lighting: '光线偏好', composition: '构图偏好', environment: '场景偏好' };
        const labelMap = {
            low_angle: '低角度仰拍', eye_level: '平视', high_angle: '高角度俯拍', dramatic_tilt: '动态倾斜',
            full_body: '全身', medium_shot: '半身/七分', close_up: '特写',
            rim_light: '轮廓光/逆光', high_contrast: '高对比侧光', diffuse_soft: '漫射柔光', natural_window: '自然窗光',
            dynamic_diagonal: '对角线/动态构图', rule_of_thirds: '三分法则', clean_negative_space: '干净留白',
            studio_clean: '影棚纯色/纯净', textured_location: '实景肌理', crowded_scene: '复杂杂乱背景'
        };
        const bars = Object.entries(weights).map(([k, w]) => {
            const pct = Math.round(w * 100);
            return `
            <div style="display:flex;align-items:center;margin-bottom:6px;gap:8px;">
                <span style="width:110px;font-size:13px;">${esc(labelMap[k] || k)}</span>
                <div style="flex:1;background:var(--line);height:8px;border-radius:4px;overflow:hidden;">
                    <div style="background:var(--accent);height:100%;width:${pct}%;"></div>
                </div>
                <span style="width:36px;font-size:12px;text-align:right;color:var(--muted);">${w.toFixed(2)}</span>
            </div>`;
        }).join('');
        return `
        <div class="dimension-card" style="background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:12px;margin-bottom:12px;">
            <h4 style="margin:0 0 10px 0;font-size:14px;color:var(--ink);">${esc(catNames[category] || category)}</h4>
            ${bars}
        </div>`;
    }).join('');

    const hypothesesHtml = (profile.accepted_hypotheses || []).map(h => `
        <li style="margin-bottom:6px;">${esc(typeof h === 'string' ? h : h.text)}</li>
    `).join('') || '<p class="muted">尚未确认选择总结。结束筛选后可以选择保存；不会自动推导偏好。</p>';

    const historyHtml = (history || []).map(h => `
        <div style="display:flex;justify-content:space-between;align-items:center;padding:10px 0;border-bottom:1px solid var(--line);">
            <div>
                <strong>v${h.version}</strong> · <small class="muted">${esc(h.at ? h.at.slice(0, 19).replace('T', ' ') : '')}</small>
                <div style="font-size:13px;color:var(--muted);">${esc(h.summary)}</div>
            </div>
            ${h.version !== profile.version ? `
                <button class="rollback-btn quiet" data-version="${h.version}" style="border:1px solid var(--line);">回滚至此版本</button>
            ` : '<span class="badge badge-success">当前生效</span>'}
        </div>
    `).join('') || '<p class="muted">暂无历史版本记录。</p>';

    $('view').innerHTML = `
    <div class="profile-view-layout" style="display:flex;gap:20px;padding:10px 0;">
        <div style="flex:1.2;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;">
                <h3 style="margin:0;">默认 / 历史维度权重 (版本 v${profile.version})</h3>
                <small class="muted">样本数: ${profile.positive_exemplars?.length || 0} 历史/兴趣收藏 / ${profile.explicit_aesthetic_negatives?.length || 0} 明确负反馈</small>
            </div>
            <p class="form-help">这些数值为默认或历史启发式权重，尚未验证为你的偏好，当前不用于个性化排序。新总结仅保留反馈，不按关键词改权重。</p>
            ${dimensionRows}
            <div style="background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:14px;margin-top:14px;">
                <h4 style="margin:0 0 8px 0;">已确认的选择总结</h4>
                <ul style="margin:0;padding-left:18px;">${hypothesesHtml}</ul>
            </div>
        </div>
        <div style="flex:1;background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:16px;align-self:flex-start;">
            <h3 style="margin:0 0 10px 0;">版本历史与可审计回滚</h3>
            <p class="form-help">历史画像绝不丢失。如果某轮筛选改变过大，随时可以安全回滚到任意历史版本。</p>
            <div class="history-list">${historyHtml}</div>
        </div>
    </div>`;

    listen('view', '.rollback-btn', 'click', async (e, n) => {
        const ver = Number(n.dataset.version);
        if (!window.confirm(`确定要将审美画像回滚到 v${ver} 吗？`)) return;
        try {
            await api('/api/profile/rollback', { method: 'POST', body: { target_version: ver } });
            toast(`已成功回滚至画像版本 v${ver}`);
            await renderProfile();
        } catch (err) {
            showError(err);
        }
    });
}



$('login-form').addEventListener('submit',async e=>{
    e.preventDefault();const button=e.target.querySelector('button');button.disabled=true;$('login-error').textContent='';
    try{
        const tokenVal = $('login-token').value.trim();
        const session=await api('/api/session',{method:'POST',body:{token:tokenVal}});
        state.csrf=session.csrf;
        try { localStorage.setItem('ref_lab_token', tokenVal); } catch(_) {}
        $('login-token').value='';
        await boot();
    }
    catch(error){$('login-error').textContent=error.message;}finally{button.disabled=false;}
});
$('new-project').onclick=()=>projectEditor();
if ($('optimize-skill-btn')) $('optimize-skill-btn').onclick = optimizeSkillFromRejectionReasons;
$('lock-library').onclick=async()=>{
    if (state.noAuth) { toast('当前已开启完全免密模式，无需锁定'); return; }
    if(!safeDiscard())return;
    try { localStorage.removeItem('ref_lab_token'); } catch(_) {}
    try{await api('/api/session',{method:'DELETE'});lockScreen();}catch(error){showError(error);}
};
listen(document,'[data-view]','click',(e,n)=>navigate(n.dataset.view));
$('editor-close').onclick=manualCloseModal;
$('editor').addEventListener('input',()=>modalDirty=true);
$('editor').addEventListener('cancel',event=>{event.preventDefault();manualCloseModal();});
$('lightbox-close').onclick=()=>$('lightbox').close();
$('lightbox-zoom').onclick=()=>$('lightbox').classList.toggle('actual');
window.addEventListener('beforeunload',event=>{if(state.dirty||modalDirty){event.preventDefault();event.returnValue='';}});
document.addEventListener('keydown',event=>{
    if($('editor').open||$('lightbox').open||$('reject-dialog')?.open||$('application').hidden||state.busy||event.isComposing||event.ctrlKey||event.metaKey||event.altKey)return;
    if(['INPUT','TEXTAREA','SELECT'].includes(document.activeElement?.tagName)||document.activeElement?.isContentEditable)return;
    if(!imageViews.includes(state.view))return;
    const key=event.key.toLowerCase();
    if(['k','i','m','x'].includes(key)&&state.view!=='inspiration'&&state.view!=='recycle'){
        event.preventDefault();if(!event.repeat)triggerDecision({k:'keep',i:'inspiration',m:'maybe',x:'reject'}[key], event.shiftKey);
    }else if(event.key==='ArrowRight'){event.preventDefault();moveImage(1);}
    else if(event.key==='ArrowLeft'){event.preventDefault();moveImage(-1);}
});
(async()=>{
    const searchParams = new URLSearchParams(window.location.search);
    const tokenFromUrl = searchParams.get('token');
    let savedToken = '';
    try { savedToken = localStorage.getItem('ref_lab_token') || ''; } catch(_) {}
    const tokenToUse = tokenFromUrl || savedToken;

    if (tokenFromUrl) {
        try { localStorage.setItem('ref_lab_token', tokenFromUrl); } catch(_) {}
        searchParams.delete('token');
        const newSearch = searchParams.toString() ? '?' + searchParams.toString() : '';
        window.history.replaceState({}, document.title, window.location.pathname + newSearch + window.location.hash);
    }

    if (tokenToUse) {
        try {
            const session = await api('/api/session', { method: 'POST', body: { token: tokenToUse } });
            state.csrf = session.csrf;
        } catch(e) {
            console.warn('Auto-login with token failed', e);
            try { localStorage.removeItem('ref_lab_token'); } catch(_) {}
        }
    }
    boot().catch(error => {
        if (state.noAuth) return;
        lockScreen();
        $('login-error').textContent = '无法连接参考库：' + error.message;
        try {
            const remembered = localStorage.getItem('ref_lab_token');
            if (remembered && !$('login-token').value) $('login-token').value = remembered;
        } catch(_) {}
    });
})();
