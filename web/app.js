'use strict';
const $ = id => document.getElementById(id);
const esc = value => String(value ?? '').replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char]));
const lines = text => String(text || '').split('\n').map(x => x.trim()).filter(Boolean);
const state = { csrf: '', projects: [], project: null, view: 'references', refs: [], activeId: null, total: 0, offset: 0, limit: 60, query: '', decision: '', kind: '', epoch: 0, autoAdvance: true, busy: false, dirty: false, caps: {} };
const decisions = { pending: '未选择', keep: '已保留', maybe: '待定', reject: '已淘汰' };
const statuses = { candidate: '候选 · 未核验', needs_review: '待逐图核验', needs_card: '待写资料卡', draft: '草稿 · 待确认', ready: '已确认现场卡', rejected: '已淘汰', inspiration: '灵感收藏', missing_asset: '图片缺失', blocked: '等待执行／受阻', running: '处理中', succeeded: '处理完成', failed: '执行失败', cancelled: '已取消', queued: '排队中' };
const kinds = { unknown: '尚未分类', cosplay_photo: '真人 cosplay', portrait_photo: '普通真人摄影', illustration: '角色插画', equipment: '器材图', location: '场地图', collage: '拼图', generated: 'AI 生成概念' };
let toastTimer, modalDirty = false;
function toast(message, error = false) { $('toast').textContent = message; $('toast').className = 'toast' + (error ? ' error' : ''); $('toast').hidden = false; clearTimeout(toastTimer); toastTimer = setTimeout(() => $('toast').hidden = true, 5500); }
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
function lockScreen() { closeModal(); $('lightbox').close(); $('lightbox-image')?.removeAttribute('src'); state.dirty = false; modalDirty = false; state.csrf = ''; state.projects = []; state.project = null; state.refs = []; state.epoch++; $('application').hidden = true; $('login-screen').hidden = false; $('view').replaceChildren(); $('login-token').focus(); }
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
function closeModal() { modalDirty = false; $('editor').close(); }
function manualCloseModal() { if (!modalDirty || window.confirm('对话框有未保存的内容，仍然关闭？'))
    closeModal(); }
function requireSaved() { if (state.dirty) {
    toast('请先保存当前审美反馈，再进行核验或制作。');
    return false;
} return true; }
function formSubmit(root, handler) { const form = root.querySelector('form'); form.addEventListener('submit', async (e) => { e.preventDefault(); const button = form.querySelector('[type=submit]'); button.disabled = true; try {
    await handler(values(form), form);
}
catch (error) {
    showError(error);
}
finally {
    button.disabled = false;
} }); }
async function download(path, name, body) { const blob = await api(path, { method: body ? 'POST' : 'GET', body, download: true }); const url = URL.createObjectURL(blob); const a = document.createElement('a'); a.href = url; a.download = name; a.click(); setTimeout(() => URL.revokeObjectURL(url), 15000); }
async function copy(text) { try {
    await navigator.clipboard.writeText(text);
    toast('已复制');
}
catch {
    modal('复制内容', `<pre>${esc(text)}</pre>`);
} }
function safeDiscard() { return !state.dirty || window.confirm('当前审美反馈尚未保存。仍然离开？'); }
function resetFilters() { state.offset = 0; state.query = ''; state.decision = ''; state.kind = ''; state.activeId = null; state.dirty = false; }
async function boot() { const session = await api('/api/session'); if (!session.authenticated) {
    lockScreen();
    return;
} state.csrf = session.csrf; $('version').textContent = 'v' + session.version; state.caps = await api('/api/capabilities'); await loadProjects(); }
async function loadProjects(preferredId) { state.projects = await api('/api/projects'); state.project = state.projects.find(x => x.id === (preferredId || state.project?.id)) || state.projects[0] || null; $('login-screen').hidden = true; $('application').hidden = false; renderSidebar(); renderHeader(); await refreshView(); }
function renderSidebar() { $('project-list').innerHTML = state.projects.length ? state.projects.map(p => `<button class="project-link ${p.id === state.project?.id ? 'selected' : ''}" data-id="${esc(p.id)}"><span class="project-avatar">${esc(p.character.slice(0, 1))}</span><span><strong>${esc(p.character)}</strong><small>${esc(p.costume || p.work || '自由参考项目')}</small></span></button>`).join('') : '<small>从一个喜欢的角色开始。</small>'; listen('project-list', 'button', 'click', async (e, node) => { if (!safeDiscard())
    return; state.project = state.projects.find(x => x.id === node.dataset.id); resetFilters(); renderSidebar(); renderHeader(); await refreshView(); }); }
function renderHeader() {
    const p = state.project;
    $('project-header').innerHTML = p ? `<div><span class="eyebrow">MY REFERENCE COLLECTION</span><h1>${esc(p.character)}${p.costume ? ` <span class="muted">/ ${esc(p.costume)}</span>` : ''}</h1><p>${esc(p.brief || p.work || '把喜欢的作品、可借鉴的动作和自己的拍摄经验连在一起。')}</p></div><div class="header-actions"><button id="edit-project">角色与要求</button><button id="import-reference" class="primary">＋ 导入参考</button><button id="export-pack">离线拍摄包</button></div>` : `<div><span class="eyebrow">YOUR PERSONAL VISUAL LIBRARY</span><h1>自己的审美，自己的参考库。</h1><p>角色名必填，其他要求用你习惯的方式表达。</p></div>`;
    if (p) {
        $('edit-project').onclick = () => projectEditor(p);
        $('import-reference').onclick = () => importDialog();
        $('export-pack').onclick = () => packDialog();
    }
}
async function renderStats(projectId = state.project?.id) { if (!projectId) {
    $('stats').innerHTML = '';
    return;
} const data = await api(`/api/projects/${projectId}/stats`); if (state.project?.id !== projectId)
    return; const values = [['独立候选', data.total], ['等待选择', data.pending], ['人工保留', data.keep], ['已淘汰', data.reject], ['可用现场卡', data.ready]]; $('stats').innerHTML = values.map(([label, value]) => `<div class="stat"><strong>${value}</strong><span>${label}</span></div>`).join(''); }
async function refreshView() { state.epoch++; document.querySelectorAll('[data-view]').forEach(b => b.classList.toggle('active', b.dataset.view === state.view)); if (!state.project) {
    $('stats').innerHTML = '';
    $('view').innerHTML = empty('先建立一个角色项目', '可以只填写角色名。作品、服装版本、想拍的动作、场地与设备要求都可以以后补充。', '建立第一个项目', 'first-project');
    $('first-project').onclick = () => projectEditor();
    return;
} renderStats().catch(showError); if (['references', 'field', 'inspiration'].includes(state.view))
    await loadReferences();
else if (state.view === 'jobs')
    await renderJobs();
else if (state.view === 'notes')
    await renderNotes();
else
    await renderEvents(); }
function projectEditor(project = null) { if (!safeDiscard())
    return; const root = modal(project ? '角色、要求与器材' : '新建角色项目', `<form><p class="form-help">只有角色名是必填。额外要求直接写成自然语言，不需要套固定分类。修改要求会让旧资料卡重新等待核对。</p><div class="form-grid">${label('角色名 *', 'character', project?.character || '', 'text', 'required maxlength="120"')}${label('出自作品（选填）', 'work', project?.work || '', 'text', 'maxlength="400"')}${label('服装／皮肤版本（选填）', 'costume', project?.costume || '', 'text', 'maxlength="400"')}<div class="full">${area('补充要求', 'brief', project?.brief || '', 'placeholder="例如：漫展拍摄，想多看站姿和回眸，不要复杂布景；要自然，但保留角色的疏离感。" maxlength="12000"')}</div><div class="full"><details><summary>我的器材与拍摄条件</summary>${area('设备／环境限制', 'gear', project?.gear || '', 'placeholder="留空则使用当前预设：A7M4、50mm、24–240mm、V100 一灯与柔光附件。" maxlength="12000"')}</details></div></div><div class="form-actions"><button class="primary" type="submit">${project ? '保存修改' : '建立项目'}</button></div></form>`); formSubmit(root, async (data) => { if (!project && !data.gear)
    delete data.gear; const p = await api(project ? `/api/projects/${project.id}` : '/api/projects', { method: project ? 'PUT' : 'POST', body: project ? { ...data, expected_revision: project.revision } : data }); closeModal(); resetFilters(); await loadProjects(p.id); toast('角色项目已保存'); }); }
async function loadReferences() { const projectId = state.project.id, epoch = ++state.epoch; const q = new URLSearchParams({ limit: state.limit, offset: state.offset, q: state.query, decision: state.decision, kind: state.kind }); if (state.view === 'field')
    q.set('state', 'ready'); if (state.view === 'inspiration') {
    q.set('lane', 'inspiration');
    q.set('decision', 'keep');
} const data = await api(`/api/projects/${projectId}/references?${q}`); if (epoch !== state.epoch || state.project?.id !== projectId)
    return; state.refs = data.items; state.total = data.total; if (state.offset >= data.total && data.total > 0) {
    state.offset = Math.floor((data.total - 1) / state.limit) * state.limit;
    await loadReferences();
    return;
} if (!state.refs.some(r => r.id === state.activeId))
    state.activeId = state.refs[0]?.id || null; state.dirty = false; renderReferenceView(); }
function renderReferenceView() {
    const view = $('view');
    view.innerHTML = `<div class="toolbar"><input id="search-ref" aria-label="搜索参考" placeholder="搜索标题、作者、审美反馈" value="${esc(state.query)}"><select id="decision-filter" aria-label="选择状态"><option value="">全部选择状态</option>${Object.entries(decisions).map(([key, val]) => `<option value="${key}" ${state.decision === key ? 'selected' : ''}>${val}</option>`).join('')}</select><select id="kind-filter" aria-label="图片类型"><option value="">全部图片类型</option>${Object.entries(kinds).map(([key, val]) => `<option value="${key}" ${state.kind === key ? 'selected' : ''}>${val}</option>`).join('')}</select><span class="spacer"></span><small>独立大图 · K 保留 / M 待定 / X 淘汰</small></div><div id="reference-content"></div>`;
    const filterChange = async (key, element) => { if (state[key] === element.value)
        return; if (!safeDiscard()) {
        element.value = state[key];
        return;
    } state[key] = element.value; state.offset = 0; state.dirty = false; await loadReferences().catch(showError); };
    $('search-ref').addEventListener('keydown', e => { if (e.key === 'Enter')
        filterChange('query', e.target); });
    $('search-ref').addEventListener('change', e => filterChange('query', e.target));
    $('decision-filter').onchange = e => filterChange('decision', e.target);
    $('kind-filter').onchange = e => filterChange('kind', e.target);
    if (!state.refs.length) {
        const title = state.view === 'field' ? '还没有已确认的现场卡' : state.view === 'inspiration' ? '这里留给你喜欢的灵感' : '候选池还没有匹配的参考';
        $('reference-content').innerHTML = empty(title, state.view === 'field' ? '保留图片后，完成逐图核验、来源确认和资料卡确认，才能进入这里。不会自动把未核验图片算作成品。' : '导入图片或候选包，逐张选出真正想借鉴的部分。历史素材可用迁移命令导入。', '导入参考', 'empty-import');
        $('empty-import').onclick = () => importDialog();
        return;
    }
    const ref = current();
    $('reference-content').innerHTML = `<div class="review-layout"><div class="image-column"><div class="image-stage ${!ref.asset ? 'empty' : ''}" id="image-stage">${ref.asset ? `<img id="main-image" src="/api/assets/${ref.asset_sha}/preview" alt="${esc(ref.title)}">` : '<div class="missing-image">图片文件尚未找到<br><small>历史条目已保留，缺图不会被算作有效参考。</small></div>'}</div><div class="image-caption"><span>${ref.asset ? `${ref.asset.width} × ${ref.asset.height} · ${(ref.asset.bytes / 1024).toFixed(0)} KB · 接收版本保留` : '缺少图像资产'}</span><button id="view-original" ${!ref.asset ? 'disabled' : ''}>查看独立原图</button></div><div id="filmstrip" class="filmstrip">${state.refs.map(r => `<button data-ref="${r.id}" class="${r.id === ref.id ? 'selected' : ''}" aria-label="查看 ${esc(r.title)}">${r.asset ? `<img src="/api/assets/${r.asset_sha}/thumb" alt="${esc(r.title)}" loading="lazy">` : '缺图'}<span class="verdict ${r.decision}">${({ keep: '✓', maybe: '?', reject: '×' })[r.decision] || ''}</span></button>`).join('')}</div><div class="image-nav"><button id="previous-image">← 上一张</button><label class="check"><input id="auto-advance" type="checkbox" ${state.autoAdvance ? 'checked' : ''}>选择后下一张</label><button id="next-image">下一张 →</button></div><div class="pagination"><button id="previous-page" ${state.offset === 0 ? 'disabled' : ''}>上一页</button><span>${state.offset + 1}–${state.offset + state.refs.length} / ${state.total}</span><button id="next-page" ${state.offset + state.limit >= state.total ? 'disabled' : ''}>下一页</button></div></div><div class="detail-panel" id="detail-panel"></div></div>`;
    if (ref.asset) {
        $('main-image').onclick = () => openImage(ref);
        $('main-image').onerror = () => { $('image-stage').innerHTML = '<div class="missing-image">图片加载失败。请检查本地资产并运行 doctor。</div>'; };
    }
    $('view-original').onclick = () => openImage(ref);
    $('auto-advance').onchange = e => state.autoAdvance = e.target.checked;
    listen('filmstrip', '[data-ref]', 'click', (e, node) => { if (safeDiscard()) {
        state.activeId = node.dataset.ref;
        state.dirty = false;
        renderReferenceView();
    } });
    $('previous-image').onclick = () => moveImage(-1);
    $('next-image').onclick = () => moveImage(1);
    $('previous-page').onclick = () => pageReferences(-1);
    $('next-page').onclick = () => pageReferences(1);
    renderDetail(ref);
}
function openImage(ref) { if (!ref.asset)
    return; $('lightbox-title').textContent = `${ref.title} · ${ref.asset.width} × ${ref.asset.height}`; $('lightbox-image').src = `/api/assets/${ref.asset_sha}/original`; $('lightbox').classList.remove('actual'); $('lightbox').showModal(); }
function moveImage(delta) { if (state.busy || !safeDiscard())
    return; const index = state.refs.findIndex(x => x.id === state.activeId); const next = index + delta; if (next >= 0 && next < state.refs.length) {
    state.activeId = state.refs[next].id;
    state.dirty = false;
    renderReferenceView();
}
else if (delta > 0 && state.offset + state.limit < state.total) {
    state.offset += state.limit;
    state.activeId = null;
    loadReferences().catch(showError);
}
else if (delta < 0 && state.offset > 0) {
    state.offset -= state.limit;
    state.activeId = null;
    loadReferences().catch(showError);
} }
function pageReferences(delta) { if (!safeDiscard())
    return; state.offset = Math.max(0, state.offset + state.limit * delta); state.activeId = null; loadReferences().catch(showError); }
function paragraphs(text) { return `<p>${esc(text)}</p>`; }
function ordered(items) { return `<ol>${(items || []).map(x => `<li>${esc(x)}</li>`).join('')}</ol>`; }
function cardMarkup(card, field = false) { if (!card)
    return ''; return `<section class="guide-section"><h3>${field ? '现场口令' : '资料卡草稿'} <small>先沟通，再调整</small></h3>${ordered(card.pose.verbal_cues)}<h4>摄影师动作</h4>${ordered(card.pose.photographer_steps)}<h4>安全与降级</h4>${paragraphs(card.pose.safety + '\n' + card.pose.fallback)}<details ${field ? '' : 'open'}><summary>静态摆姿、动作引导与布光</summary><h4>静态摆姿</h4>${ordered(card.pose.static_steps)}<h4>动作引导</h4>${paragraphs(card.pose.action_directing)}<h4>图中光线证据</h4>${ordered(card.lighting.visible_evidence)}<h4>布光推测 · ${esc(card.lighting.confidence)}</h4>${paragraphs(card.lighting.interpretation)}<h4>现有器材可尝试方案</h4>${paragraphs(card.lighting.available_gear_plan)}</details><details><summary>PS 路线：${esc(({ none: '不换背景', cleanup: '轻量清理', composite: '明确合成' })[card.retouch.route])}</summary>${ordered(card.retouch.steps)}<h4>拍摄准备</h4>${paragraphs(card.retouch.capture_preparation)}${card.retouch.background_prompt ? '<h4>AI 背景需求</h4>' + paragraphs(card.retouch.background_prompt) : ''}</details></section>`; }
function renderDetail(ref) {
    $('detail-panel').innerHTML = `<div class="detail-top">${badge(statuses[ref.state] || ref.state, ref.state)}${badge(kinds[ref.review?.kind || 'unknown'])}</div><h2>${esc(ref.title)}</h2><div class="detail-meta">${esc(ref.source.author || '作者尚未记录')} · ${ref.source.search_category ? '检索线索：' + esc(ref.source.search_category) + '（非图像事实）' : '来源与角色匹配需单独核验'}</div><div class="decision-bar">${[['keep', '✓ 保留 K'], ['maybe', '? 待定 M'], ['reject', '× 淘汰 X']].map(([d, t]) => `<button data-decision="${d}" class="${d === 'keep' ? 'primary' : d === 'reject' ? 'danger' : ''} ${ref.decision === d ? 'chosen' : ''}">${t}</button>`).join('')}</div><form id="preference-form">${area('我喜欢／不喜欢的地方', 'preference', ref.preference, 'placeholder="例如：只喜欢回眸动作，不喜欢服装和后期色调。" maxlength="12000"')}${label('只借鉴这些方面（逗号分隔）', 'borrow', ref.borrow.join('，'), 'text', 'placeholder="动作，眼神，构图"')}${select('归档位置', 'lane', { field: '现场参考方向', inspiration: '仅作为审美灵感' }, ref.lane)}${check('允许跨角色／普通人像借鉴；不冒充同角色参考', 'allow_cross_domain', ref.allow_cross_domain)}<div class="compact-row"><button type="submit">保存审美反馈</button><span id="dirty-indicator" class="muted"></span></div></form><div class="gate-box">${ref.field_ready ? '已通过入库门槛，并由你确认。可加入离线拍摄包。' : `<details><summary>尚不能作为现场卡 · ${ref.blockers.length} 项待处理</summary><ul>${ref.blockers.map(x => `<li>${esc(x.message)}</li>`).join('')}</ul></details>`}</div><section class="guide-section"><h3>逐图核验与制作</h3><div class="compact-row"><button id="review-reference" ${!ref.asset ? 'disabled' : ''}>人工核验</button><button id="analyze-reference" ${ref.decision !== 'keep' || !ref.asset ? 'disabled' : ''}>建立 AI 分析任务</button><button id="edit-card" ${ref.decision !== 'keep' ? 'disabled' : ''}>${ref.card ? '编辑资料卡' : '编写资料卡'}</button></div>${ref.review ? `<small>核验来源：${esc(ref.review_actor)} / ${esc(ref.review_producer)}</small><details><summary>图片观察记录</summary>${ordered(ref.review.observations)}${ref.review.critical_uncertainties.length ? '<h4>关键疑点</h4>' + ordered(ref.review.critical_uncertainties) : ''}</details>` : '<p class="muted">尚无逐图核验记录。不会根据搜索词补写动作。</p>'}${ref.card && !ref.field_ready ? '<button id="accept-card" class="primary">我已核对，确认为现场卡</button>' : ''}</section>${cardMarkup(ref.card, ref.field_ready)}<section class="guide-section"><h3>拍摄后的经验 <button id="add-reflection" class="quiet">＋ 复盘</button></h3>${ref.reflections.slice(-3).map(x => `<p><small>${esc(x.at.slice(0, 10))} · ${x.tried ? '已尝试' : '尚未尝试'}</small><br>${esc(x.worked || x.failed || x.next_time || '已记录')}</p>`).join('') || '<p class="muted">把实拍中真正有效的引导留在这里。</p>'}</section><div class="source-mini"><div class="compact-row"><button id="edit-source">来源与标题</button><button id="similar-images">相似图线索</button><button id="replace-image">替换图片</button></div>${ref.source.page_url ? `<a href="${esc(ref.source.page_url)}" target="_blank" rel="noopener noreferrer">打开来源页 ↗</a>` : ''}${ref.legacy_notes ? `<details><summary>历史说明（未验证）</summary><pre>${esc(ref.legacy_notes)}</pre></details>` : ''}<p>修订 ${ref.revision} · ${esc(ref.id.slice(0, 12))}</p></div>`;
    listen('detail-panel', '[data-decision]', 'click', (e, n) => decide(n.dataset.decision));
    $('preference-form').oninput = () => { state.dirty = true; $('dirty-indicator').textContent = '尚未保存'; };
    $('preference-form').onsubmit = e => { e.preventDefault(); savePreference().catch(showError); };
    $('review-reference').onclick = () => { if (requireSaved())
        reviewEditor(ref); };
    $('analyze-reference').onclick = () => newAnalysis([ref.id]).catch(showError);
    $('edit-card').onclick = () => { if (requireSaved())
        cardEditor(ref); };
    if ($('accept-card'))
        $('accept-card').onclick = () => { if (requireSaved())
            updateAction(ref, 'accept', { expected_revision: ref.revision }, '现场卡已确认').catch(showError); };
    $('edit-source').onclick = () => { if (requireSaved())
        sourceEditor(ref); };
    $('add-reflection').onclick = () => { if (requireSaved())
        reflectionEditor(ref); };
    $('replace-image').onclick = () => { if (requireSaved())
        replaceEditor(ref); };
    $('similar-images').onclick = () => similarDialog(ref).catch(showError);
}
function preferenceValues() { const form = $('preference-form'); if (!form)
    return {}; const data = values(form); data.borrow = data.borrow.split(/[,，\n]/).map(x => x.trim()).filter(Boolean); return data; }
async function savePreference() { const ref = current(); if (!ref || state.busy)
    return; state.busy = true; try {
    await api(`/api/references/${ref.id}`, { method: 'PATCH', body: { expected_revision: ref.revision, ...preferenceValues() } });
    state.dirty = false;
    await loadReferences();
    renderStats().catch(showError);
    toast('审美反馈已保存到数据库');
}
finally {
    state.busy = false;
} }
async function decide(decision) { const ref = current(); if (!ref || state.busy)
    return; state.busy = true; document.querySelectorAll('[data-decision]').forEach(x => x.disabled = true); try {
    const index = state.refs.findIndex(x => x.id === ref.id), next = state.autoAdvance ? state.refs[index + 1]?.id : ref.id;
    await api(`/api/references/${ref.id}`, { method: 'PATCH', body: { expected_revision: ref.revision, ...preferenceValues(), decision } });
    state.activeId = next || ref.id;
    state.dirty = false;
    await loadReferences();
    await renderStats();
    toast(decisions[decision] + ' · 已持久保存');
}
finally {
    state.busy = false;
    document.querySelectorAll('[data-decision]').forEach(x => x.disabled = false);
} }
async function updateAction(ref, action, body, message) { await api(`/api/references/${ref.id}/${action}`, { method: 'POST', body }); state.activeId = ref.id; state.dirty = false; closeModal(); await loadReferences(); await renderStats(); toast(message); }
function sourceEditor(ref) { const s = ref.source; const root = modal('来源、权利状态与标题', `<form><p class="form-help">原发布页与图片 CDN 不是一回事。搜索结果页也不能代替原出处。来源不明仍可收藏，但不能伪装成已经确认的实拍资料卡。</p>${label('条目标题', 'title', ref.title, 'text', 'maxlength="400"')}${label('原发布页', 'page_url', s.page_url, 'url', 'maxlength="4000"')}${label('图片来源地址（只作追溯）', 'image_url', s.image_url, 'url', 'maxlength="4000"')}${label('作者', 'author', s.author, 'text', 'maxlength="400"')}${select('权利状态', 'rights', { unknown: '未确认', personal_reference: '私人参考，不代表公开转载许可', owned: '我拥有此图片的使用权', licensed: '已获授权' }, s.rights)}${area('使用权／来源说明', 'rights_note', s.rights_note, 'placeholder="自有作品请注明；授权请记录范围。" maxlength="12000"')}${check('我已检查原发布页，或确认这是我的自有作品', 'source_confirmed', s.source_confirmed)}<div class="form-actions"><button type="submit" class="primary">保存来源</button></div></form>`); formSubmit(root, async (data) => { const title = data.title; delete data.title; await api(`/api/references/${ref.id}`, { method: 'PATCH', body: { expected_revision: ref.revision, title, source: { ...s, ...data } } }); closeModal(); await loadReferences(); toast('来源信息已保存；旧发布确认已撤销'); }); }
function reviewEditor(ref) { const r = ref.review || { kind: 'unknown', visible_person: false, pose_readable: false, single_image: false, sufficiently_clear: false, character_match: 'unknown', observations: [], critical_uncertainties: [] }; const root = modal('逐图人工核验', `<form><p class="form-help">请实际打开独立图片后填写。器材、场地、插画和拼图不能成为真人姿势主卡。没有把握就保留“未知”与疑点。</p><div class="form-grid">${select('图片实际类型', 'kind', kinds, r.kind)}${select('与目标角色的关系', 'character_match', { unknown: '未确认', exact: '目标角色／版本匹配', adapted: '不是同角色，仅借鉴指定方面', irrelevant: '不相关' }, r.character_match)}</div>${check('图中有明确可见的人物', 'visible_person', r.visible_person)}${check('需要借鉴的肢体／动作看得清', 'pose_readable', r.pose_readable)}${check('这是独立画面，不是多个画面的拼图', 'single_image', r.single_image)}${check('实际清晰度足以支持动作分析', 'sufficiently_clear', r.sufficiently_clear)}${area('看得见的事实（每行一条）*', 'observations', r.observations.join('\n'), 'required placeholder="只写图中可见的内容，不依据标题猜动作。"')}${area('仍未解决的关键疑点（没有则留空）', 'critical_uncertainties', r.critical_uncertainties.join('\n'))}<small>核验绑定图片 SHA：${esc(ref.asset_sha?.slice(0, 20))}…</small><div class="form-actions"><button type="submit" class="primary">保存人工核验</button></div></form>`); formSubmit(root, data => updateAction(ref, 'review', { expected_revision: ref.revision, review: { ...data, asset_sha: ref.asset_sha, observations: lines(data.observations), critical_uncertainties: lines(data.critical_uncertainties) } }, '逐图核验已保存')); }
function cardEditor(ref) { const c = ref.card || { title: ref.title, intent: '', pose: { verbal_cues: [], static_steps: [], action_directing: '', photographer_steps: [], safety: '', fallback: '' }, lighting: { visible_evidence: [], interpretation: '', confidence: 'low', available_gear_plan: '' }, retouch: { route: 'none', steps: [], capture_preparation: '', background_prompt: '' } }; const root = modal(ref.card ? '编辑资料卡' : '编写资料卡', `<form><p class="form-help">不知道原作者怎么拍，就写你可尝试的方案。这里保存的是草稿，最后还需要你确认。每行一条的字段会按顺序显示。</p>${label('资料卡标题 *', 'title', c.title, 'text', 'required')}${area('这张图值得借鉴什么 *', 'intent', c.intent, 'required')}<h3 class="form-heading">现场引导 · 第一优先级</h3>${area('可以直接说出口的口令（每行一条）*', 'verbal_cues', c.pose.verbal_cues.join('\n'), 'required')}${area('静态摆姿步骤（每行一条）*', 'static_steps', c.pose.static_steps.join('\n'), 'required')}${area('动作／情境引导版本', 'action_directing', c.pose.action_directing)}${area('摄影师自己要做什么（每行一条）*', 'photographer_steps', c.pose.photographer_steps.join('\n'), 'required')}${area('安全与舒适性 *', 'safety', c.pose.safety, 'required')}${area('动作做不到时的降级方案 *', 'fallback', c.pose.fallback, 'required')}<h3 class="form-heading">光线 · 事实与推测分开</h3>${area('图中可见的光线证据（每行一条）*', 'visible_evidence', c.lighting.visible_evidence.join('\n'), 'required')}${area('可能的布光解释 *', 'interpretation', c.lighting.interpretation, 'required')}${select('推测把握', 'confidence', { low: '低', medium: '中', high: '高' }, c.lighting.confidence)}${area('用我的器材可以尝试的方案 *', 'available_gear_plan', c.lighting.available_gear_plan, 'required')}<h3 class="form-heading">PS 与 AI 背景</h3>${select('后期路线', 'route', { none: '不换背景', cleanup: '轻量清理', composite: '明确合成' }, c.retouch.route)}${area('后期步骤（每行一条）', 'steps', c.retouch.steps.join('\n'))}${area('拍摄前的准备（合成路线必填）', 'capture_preparation', c.retouch.capture_preparation)}${area('AI 背景需求／提示词（合成路线必填）', 'background_prompt', c.retouch.background_prompt, 'placeholder="机位、地平线、光向、人物留位与地面关系；不要生成替代人物。"')}<div class="form-actions"><button type="submit" class="primary">保存资料卡草稿</button></div></form>`); formSubmit(root, data => updateAction(ref, 'card', { expected_revision: ref.revision, card: { title: data.title, intent: data.intent, pose: { verbal_cues: lines(data.verbal_cues), static_steps: lines(data.static_steps), action_directing: data.action_directing, photographer_steps: lines(data.photographer_steps), safety: data.safety, fallback: data.fallback }, lighting: { visible_evidence: lines(data.visible_evidence), interpretation: data.interpretation, confidence: data.confidence, available_gear_plan: data.available_gear_plan }, retouch: { route: data.route, steps: lines(data.steps), capture_preparation: data.capture_preparation, background_prompt: data.background_prompt } } }, '资料卡草稿已保存，尚未自动发布')); }
function reflectionEditor(ref) { const root = modal('把实拍经验接回参考', `<form>${check('我已经实际尝试过', 'tried', true)}${area('什么引导／方法有效', 'worked')}${area('哪里不自然，或现场做不到', 'failed')}${area('下次如何调整', 'next_time')}<div class="form-actions"><button type="submit" class="primary">保存拍摄复盘</button></div></form>`); formSubmit(root, data => updateAction(ref, 'reflection', { ...data, expected_revision: ref.revision }, '实拍经验已保存')); }
function replaceEditor(ref) { const root = modal('替换参考图片', `<form><p class="notice">替换后会重置选择、图片核验与资料卡确认。旧文件仍保留用于追溯，不会被覆盖。</p><label>新的独立图片<input type="file" name="file" accept="image/jpeg,image/png,image/webp" required></label><div class="form-actions"><button type="submit" class="primary">替换并重新审核</button></div></form>`); formSubmit(root, async (data, form) => { const body = new FormData(form); body.set('expected_revision', ref.revision); await api(`/api/references/${ref.id}/replace`, { method: 'POST', body }); closeModal(); await loadReferences(); await renderStats(); toast('已替换；旧核验不再沿用'); }); }
async function similarDialog(ref) { const matches = await api(`/api/references/${ref.id}/similar`); const root = modal('相似图线索', `<p class="form-help">这是图像指纹的粗略相似度，不是重复判决。相邻动作也可能有价值，系统不会自动淘汰。</p><div class="filmstrip">${matches.map(x => `<button data-id="${x.id}"><img src="/api/assets/${x.asset_sha}/thumb" alt="相似参考"><span class="verdict">差异 ${x.distance}</span></button>`).join('') || '<p>当前项目没有发现近似指纹。</p>'}</div>`); listen(root, '[data-id]', 'click', async (e, n) => { const found = await api(`/api/references/${n.dataset.id}`); closeModal(); openImage(found); }); }
function importDialog(mode = 'images', jobId = '') { const names = { images: '独立图片', candidates: '候选 ZIP 包', notion: 'Notion 导出 ZIP', analyses: 'AI 分析 JSON' }; const root = modal('导入资料', `<form>${select('导入类型', 'import_type', names, mode)}<div class="drop-zone"><strong id="import-hint">${mode === 'images' ? '每张原图单独保存，不会拼成九宫格' : '候选包见 docs/WORKER_PROTOCOL.md'}</strong><input id="import-files" type="file" name="file" ${mode === 'images' ? 'multiple accept="image/jpeg,image/png,image/webp"' : mode === 'analyses' ? 'accept=".json"' : 'accept=".zip"'} required></div><div id="import-source" ${mode !== 'images' ? 'hidden' : ''}>${label('这批图片的原发布页（可之后逐张补齐）', 'page_url', '', 'url')}${label('作者（选填）', 'author')}</div>${jobId ? `<p class="muted">归入采集任务：${esc(jobId)}</p>` : ''}<p class="form-help">导入只创建候选／草稿，不会自动替你选择或确认。Notion 请使用 Markdown & CSV 导出，包含子页面与图片。</p><div class="form-actions"><button class="primary" type="submit">开始导入</button></div><p id="import-progress" class="muted"></p></form>`); root.querySelector('[name=import_type]').onchange = e => importDialog(e.target.value, jobId); formSubmit(root, async (data, form) => { const files = [...form.querySelector('[type=file]').files]; const projectId = state.project.id; const report = { created: 0, existing: 0, errors: [] }; if (mode === 'images') {
    for (let i = 0; i < files.length; i++) {
        $('import-progress').textContent = `正在保存 ${i + 1} / ${files.length} 张独立图片`;
        try {
            const body = new FormData();
            body.set('file', files[i]);
            const asset = await api('/api/assets', { method: 'POST', body });
            const result = await api(`/api/projects/${projectId}/references`, { method: 'POST', body: { asset_sha: asset.id, title: files[i].name.slice(0, 400), source: { page_url: data.page_url, author: data.author, obtained_as: 'as_received' }, job_id: jobId } });
            report[result.created ? 'created' : 'existing']++;
        }
        catch (error) {
            report.errors.push({ file: files[i].name, error: error.message });
        }
    }
}
else {
    const body = new FormData();
    body.set('file', files[0]);
    if (jobId)
        body.set('job_id', jobId);
    Object.assign(report, await api(`/api/projects/${projectId}/imports/${mode}`, { method: 'POST', body }));
} closeModal(); await refreshView(); modal('导入结果', `<p>以下是实际导入结果。错误或缺失项未被算成成功。</p><pre>${esc(JSON.stringify(report, null, 2))}</pre>`); toast('导入已结束；请检查结果明细'); }); }
function packDialog() { const mode = state.view === 'inspiration' ? 'inspiration' : 'field'; const root = modal('下载离线拍摄包', `<form><p class="notice">解压 ZIP 后直接打开 index.html。独立大图、来源文件和说明都包含在包里，不需要现场联网。</p>${select('导出范围', 'mode', { field: '本项目全部已确认现场卡', inspiration: '本项目全部已保留灵感' }, mode)}<p class="form-help">现场卡不满足门槛时会阻止导出。灵感包明确标为灵感，不充当现场指令。包内可能包含他人作品及 EXIF，请仅按相应权限使用。每包最多 200 张。</p><div class="form-actions"><button type="submit" class="primary">生成并下载</button></div></form>`); formSubmit(root, async (data) => { await download(`/api/projects/${state.project.id}/pack`, `${state.project.character}-${data.mode}.zip`, { mode: data.mode, reference_ids: [] }); closeModal(); toast('离线包已生成'); }); }
async function newAnalysis(ids) { if (state.dirty)
    await savePreference(); const job = await api(`/api/projects/${state.project.id}/jobs`, { method: 'POST', body: { kind: 'analysis', reference_ids: ids } }); state.view = 'jobs'; state.dirty = false; await refreshView(); toast('分析任务已建立，等待本地执行或导入结果'); return job; }
async function renderJobs() {
    const projectId = state.project.id, epoch = ++state.epoch;
    const jobs = await api(`/api/projects/${projectId}/jobs`);
    if (epoch !== state.epoch)
        return;
    $('view').innerHTML = `<div class="notice">网站不伪装成已经运行的搜索引擎。先建立任务，再用本地浏览器／Codex 执行，或导入候选包。AI 分析可导出独立原图任务包，也可显式启用独立计费的 OpenAI API 执行器。</div><div class="toolbar"><button id="create-collection" class="primary">＋ 建立采集任务</button><button id="analyze-kept">分析已保留参考</button><button id="import-analysis">导入分析结果</button><button id="refresh-jobs">刷新状态</button></div><div class="job-grid">${jobs.map(job => { const count = job.kind === 'analysis' ? job.completed_ids.length : job.imported_ids.length; const total = job.kind === 'analysis' ? job.reference_ids.length : 0; return `<article class="job-card" data-job="${job.id}"><div class="compact-row">${badge(job.kind === 'analysis' ? '逐图分析' : '参考采集')}${badge(statuses[job.status], job.status)}</div><h3>${esc(job.detail)}</h3><small>${esc(job.created_at.slice(0, 16).replace('T', ' '))} · ${esc(job.id.slice(0, 12))}</small><p>${job.kind === 'analysis' ? `已完成 ${count} / ${total} 张分析（仍需用户验收）` : `实际导入 ${count} 个独立候选（不等于已经选中）`}</p>${total ? `<div class="progress"><span style="width:${Math.min(100, count / total * 100)}%"></span></div>` : ''}<div class="compact-row"><button data-action="download">下载任务包</button><button data-action="command">复制本地命令</button>${job.kind === 'collection' && !['succeeded', 'cancelled'].includes(job.status) ? '<button data-action="import">导入此任务候选</button>' : ''}${['blocked', 'failed'].includes(job.status) ? '<button data-action="start">标记开始人工处理</button>' : ''}${job.status === 'running' ? '<button data-action="finish">核对结果并结束</button><button data-action="pause">暂停</button>' : ''}${!['succeeded', 'cancelled'].includes(job.status) ? '<button data-action="cancel" class="quiet">取消任务</button>' : ''}</div><details><summary>检索计划／要求与实际进度</summary><pre>${esc(JSON.stringify({ queries: job.queries, brief: job.brief, notes: job.notes, imported_ids: job.imported_ids, completed_ids: job.completed_ids }, null, 2))}</pre></details></article>`; }).join('') || empty('从一轮具体需求开始', '采集任务保存角色、自由要求和搜索计划；分析任务只处理你已经保留的图。')}</div>`;
    $('create-collection').onclick = () => { const root = modal('建立采集任务', `<form><p class="form-help">角色、服装版本与项目要求会一起交给执行器。这里补充本轮需要，不会把它自动当成图片分类。</p>${area('本轮补充要求', 'notes', '', 'placeholder="例如：先多找同角色的真人 cosplay，坐姿与自然互动优先，不要为了凑数量重复同一套连拍。"')}<div class="form-actions"><button class="primary" type="submit">建立待执行任务</button></div></form>`); formSubmit(root, async (data) => { await api(`/api/projects/${projectId}/jobs`, { method: 'POST', body: { kind: 'collection', notes: data.notes } }); closeModal(); await renderJobs(); toast('采集任务已建立；尚未执行搜索'); }); };
    $('analyze-kept').onclick = async () => { try {
        const refs = await api(`/api/projects/${projectId}/references?decision=keep&limit=200`);
        const candidates = refs.items.filter(r => r.asset && !r.field_ready);
        if (!candidates.length) {
            toast('没有待分析的已保留图片');
            return;
        }
        const root = modal('选择本轮分析图片', `<form><p class="form-help">本轮最多 50 张；有已确认现场卡的条目默认不再分析。这里只列当前前 200 张保留参考。</p>${candidates.slice(0, 50).map(r => `<label class="check"><input type="checkbox" name="${r.id}" checked><span>${esc(r.title)} · ${esc(statuses[r.state])}</span></label>`).join('')}<div class="form-actions"><button type="submit" class="primary">建立分析任务</button></div></form>`);
        formSubmit(root, async (data, form) => { const ids = [...form.querySelectorAll('input:checked')].map(x => x.name); if (!ids.length)
            throw new Error('至少选择一张图片'); await newAnalysis(ids); closeModal(); });
    }
    catch (error) {
        showError(error);
    } };
    $('import-analysis').onclick = () => importDialog('analyses');
    $('refresh-jobs').onclick = () => renderJobs().catch(showError);
    listen('view', '[data-action]', 'click', async (e, node) => { const job = jobs.find(x => x.id === node.closest('[data-job]').dataset.job); const action = node.dataset.action; if (action === 'download') {
        await download(`/api/jobs/${job.id}/download`, `job-${job.id.slice(0, 8)}.zip`);
        return;
    } if (action === 'command') {
        await copy(job.kind === 'analysis' ? `python -m ref_lab analyze --job ${job.id} --confirm-external-images` : `python -m ref_lab collect --job ${job.id} --cdp http://127.0.0.1:9222 --search`);
        return;
    } if (action === 'import') {
        importDialog('candidates', job.id);
        return;
    } const status = { start: 'running', finish: 'succeeded', pause: 'blocked', cancel: 'cancelled' }[action]; const detail = { start: '用户开始人工处理任务；并非自动执行器已启动', finish: '用户结束处理；服务器已核对实际导入／分析记录', pause: '用户暂停任务，已完成结果保留', cancel: '用户取消任务，已完成结果保留' }[action]; if (status) {
        await api(`/api/jobs/${job.id}/status`, { method: 'POST', body: { expected_revision: job.revision, status, detail } });
        await renderJobs();
    } });
}
async function renderNotes() { const projectId = state.project.id, epoch = ++state.epoch; const notes = await api(`/api/projects/${projectId}/notes`); if (epoch !== state.epoch)
    return; $('view').innerHTML = `<div class="toolbar"><button id="new-note" class="primary">＋ 写摄影笔记</button><button id="import-notion">导入 Notion</button><small>文字与本地图片保留；不执行导入 HTML 或脚本。</small></div><div class="note-grid">${notes.map(note => `<article class="note-card" data-note="${note.id}" tabindex="0"><span class="eyebrow">PHOTOGRAPHY NOTES</span><h3>${esc(note.title)}</h3><p>${esc(note.body.slice(0, 300))}</p><small>${esc(note.source_path || note.created_at.slice(0, 10))}</small></article>`).join('') || empty('让摄影笔记回到图像旁边', '可以写下观察、拍摄方法和复盘，也可以导入 Notion 的 Markdown & CSV 导出包。')}</div>`; $('new-note').onclick = () => noteEditor(); $('import-notion').onclick = () => importDialog('notion'); listen('view', '[data-note]', 'click', (e, n) => openNote(notes.find(x => x.id === n.dataset.note))); listen('view', '[data-note]', 'keydown', (e, n) => { if (e.key === 'Enter')
    openNote(notes.find(x => x.id === n.dataset.note)); }); }
function noteEditor(note = null) { const root = modal(note ? '编辑摄影笔记' : '写摄影笔记', `<form>${label('笔记标题 *', 'title', note?.title || '', 'text', 'required maxlength="400"')}${area('正文（支持保留 Markdown）', 'body', note?.body || '', 'required style="min-height:300px" maxlength="200000"')}<div class="form-actions"><button type="submit" class="primary">保存笔记</button></div></form>`); formSubmit(root, async (data) => { await api(note ? `/api/notes/${note.id}` : `/api/projects/${state.project.id}/notes`, { method: note ? 'PUT' : 'POST', body: note ? { ...data, expected_revision: note.revision } : data }); closeModal(); await renderNotes(); toast('摄影笔记已保存'); }); }
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
$('login-form').addEventListener('submit', async (e) => { e.preventDefault(); const button = e.target.querySelector('button'); button.disabled = true; $('login-error').textContent = ''; try {
    const session = await api('/api/session', { method: 'POST', body: { token: $('login-token').value } });
    $('login-token').value = '';
    state.csrf = session.csrf;
    await boot();
}
catch (error) {
    $('login-error').textContent = error.message;
}
finally {
    button.disabled = false;
} });
$('new-project').onclick = () => projectEditor();
$('lock-library').onclick = async () => { try {
    await api('/api/session', { method: 'DELETE' });
    lockScreen();
}
catch (error) {
    showError(error);
} };
listen('view-tabs', '[data-view]', 'click', async (e, node) => { if (!safeDiscard())
    return; state.view = node.dataset.view; resetFilters(); await refreshView(); });
$('editor-close').onclick = manualCloseModal;
$('editor').addEventListener('input', () => modalDirty = true);
$('editor').addEventListener('cancel', event => { if (modalDirty) {
    event.preventDefault();
    manualCloseModal();
} });
$('lightbox-close').onclick = () => $('lightbox').close();
$('lightbox-zoom').onclick = () => $('lightbox').classList.toggle('actual');
window.addEventListener('beforeunload', event => { if (state.dirty || modalDirty) {
    event.preventDefault();
    event.returnValue = '';
} });
document.addEventListener('keydown', event => { if ($('editor').open || $('lightbox').open || $('application').hidden || state.busy)
    return; if (['INPUT', 'TEXTAREA', 'SELECT', 'BUTTON'].includes(document.activeElement?.tagName) || document.activeElement?.isContentEditable)
    return; if (!['references', 'field', 'inspiration'].includes(state.view))
    return; const key = event.key.toLowerCase(); if (['k', 'm', 'x'].includes(key)) {
    event.preventDefault();
    decide({ k: 'keep', m: 'maybe', x: 'reject' }[key]).catch(showError);
}
else if (event.key === 'ArrowRight') {
    event.preventDefault();
    moveImage(1);
}
else if (event.key === 'ArrowLeft') {
    event.preventDefault();
    moveImage(-1);
} });
boot().catch(error => { lockScreen(); $('login-error').textContent = '无法连接参考库：' + error.message; });
