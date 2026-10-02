'use strict';
/* Asset-first discovery; curation stays in the existing project workbench. */
window.LibraryDiscovery = (() => {
    const defaults = {q:'', scope:'all', project_id:'', kind:'', viewpoint:'', framing:'', pose:'', orientation:''};
    const captions = {viewpoint:'视角', framing:'景别', pose:'主动作', orientation:'画幅'};
    let filters = {...defaults}, offset = 0, items = [], saved = [], facetChoices = {};
    let nav = {pinned_ids:[], recent_ids:[]}, requestId = 0, navRequestId = 0, controller;
    let selectedSearch = '';

    function restore(params) {
        filters = {...defaults};
        for (const key of Object.keys(defaults)) {
            if (params.has('library_'+key)) filters[key] = params.get('library_'+key).slice(0,400);
        }
        offset = Math.max(0, Number(params.get('library_offset')) || 0);
    }
    function navigationParams(params) {
        if (state.view !== 'library') return;
        for (const [key,value] of Object.entries(filters)) params.set('library_'+key,value);
        params.set('library_offset',String(offset));
    }
    function reset() {
        controller?.abort(); requestId++; navRequestId++;
        filters={...defaults}; offset=0; items=[]; saved=[]; selectedSearch='';
        nav={pinned_ids:[],recent_ids:[]};
    }
    async function init() {
        const [navigation,config] = await Promise.all([api('/api/library/navigation'),api('/api/library/facets')]);
        nav=navigation; facetChoices=config.facets;
        $('project-search').oninput=renderProjects;
        $('all-projects').onclick=projectDirectory;
    }
    async function visit(id) {
        const stamp=++navRequestId;
        const result=await api(`/api/library/projects/${encodeURIComponent(id)}/visit`,{method:'POST'});
        if(stamp===navRequestId&&!$('application').hidden){nav=result;renderProjects();}
    }
    async function pin(id,button) {
        button.disabled=true;
        try {
            const stamp=++navRequestId;
            const result=await api(`/api/library/projects/${encodeURIComponent(id)}/pin`,{method:'PUT',body:{pinned:!nav.pinned_ids.includes(id)}});
            if(stamp===navRequestId&&!$('application').hidden){nav=result;renderProjects();}
        } finally {button.disabled=false;}
    }
    function matchProjects(query) {
        const needle=query.trim().toLocaleLowerCase();
        return state.projects.filter(p=>`${p.character} ${p.costume||''} ${p.work||''}`.toLocaleLowerCase().includes(needle));
    }
    function projectRows(projects) {
        return projects.map(p=>`<div class="project-nav-row"><button class="project-link ${projectViews.includes(state.view)&&p.id===state.project?.id?'selected':''}" data-project-open="${esc(p.id)}" data-id="${esc(p.id)}"><span class="project-avatar">${esc(p.character.slice(0,1))}</span><span><strong>${esc(p.character)}</strong><small>${esc(p.costume||p.work||'拍摄项目')}</small></span></button><button type="button" class="project-pin icon-button" data-project-pin="${esc(p.id)}" aria-label="${nav.pinned_ids.includes(p.id)?'取消置顶':'置顶'} ${esc(p.character)} ${esc(p.costume||'')}" aria-pressed="${nav.pinned_ids.includes(p.id)}">${nav.pinned_ids.includes(p.id)?'★':'☆'}</button></div>`).join('');
    }
    function bindProjectRows(root,close=false,afterPin=null) {
        listen(root,'[data-project-open]','click',async(e,n)=>{
            if(!safeDiscard())return;
            if(close)closeModal();
            await navigate('references',n.dataset.projectOpen);
        });
        listen(root,'[data-project-pin]','click',async(e,n)=>{await pin(n.dataset.projectPin,n);afterPin?.();});
    }
    function renderProjects() {
        const query=$('project-search')?.value||'';
        const matches=matchProjects(query);
        let shown;
        if(query.trim())shown=matches.slice(0,8);
        else {
            const order=[...(projectViews.includes(state.view)&&state.project?[state.project.id]:[]),...nav.pinned_ids,...nav.recent_ids,...state.projects.map(p=>p.id)];
            const byId=new Map(state.projects.map(p=>[p.id,p]));
            shown=[...new Set(order)].filter(id=>byId.has(id)).slice(0,8).map(id=>byId.get(id));
        }
        $('project-list').innerHTML=projectRows(shown)||'<small>没有匹配的项目。</small>';
        $('project-nav-count').textContent=query.trim()?`匹配 ${matches.length} 个 · 显示 ${shown.length} 个`:`当前、置顶与最近使用 · ${state.projects.length} 个项目`;
        bindProjectRows('project-list');
    }
    function projectDirectory() {
        if(!safeDiscard())return;
        const root=modal('全部拍摄项目','<label>搜索项目<input id="project-directory-search" placeholder="角色、服装或作品" maxlength="400"></label><div id="project-directory-list"></div><div class="pagination"><button id="project-directory-prev">上一页</button><span id="project-directory-count"></span><button id="project-directory-next">下一页</button></div>');
        let page=0;
        const draw=()=>{
            const matches=matchProjects($('project-directory-search').value);
            page=Math.min(page,Math.max(0,Math.ceil(matches.length/30)-1));
            $('project-directory-list').innerHTML=projectRows(matches.slice(page*30,(page+1)*30))||'<p>没有匹配的项目。</p>';
            $('project-directory-count').textContent=`${matches.length? page*30+1:0}–${Math.min((page+1)*30,matches.length)} / ${matches.length}`;
            $('project-directory-prev').disabled=page===0;
            $('project-directory-next').disabled=(page+1)*30>=matches.length;
            bindProjectRows('project-directory-list',true,draw);
        };
        $('project-directory-search').oninput=e=>{e.stopPropagation();page=0;draw();};
        $('project-directory-prev').onclick=()=>{page--;draw();};
        $('project-directory-next').onclick=()=>{page++;draw();};
        draw();root.querySelector('input').focus();
    }
    function choices(key,annotation=false,value='') {
        const values=annotation?{unknown:'尚未分类',...facetChoices[key]}:{'':'全部',unknown:'尚未分类',...facetChoices[key]};
        return select(captions[key],key,values,value);
    }
    function syncControls() {
        const form=$('library-filter-form');if(!form)return;
        for(const [key,value] of Object.entries(filters)) {
            const control=form.elements.namedItem(key);
            if(control?.tagName==='SELECT'&&value&&![...control.options].some(o=>o.value===value)) {
                const option=document.createElement('option');option.value=value;option.textContent='已不可用的筛选条件';control.append(option);
            }
            if(control)control.value=value;
        }
    }
    function drawSaved() {
        const select=$('library-saved-search');if(!select)return;
        select.innerHTML='<option value="">选择常用搜索</option>'+saved.map(s=>`<option value="${esc(s.id)}">${esc(s.name)}</option>`).join('');
        select.value=selectedSearch;
        $('library-delete-search').disabled=!selectedSearch;
    }
    async function render() {
        const view=$('view');delete view.dataset.shell;
        const projects={'':'所有项目',...Object.fromEntries(state.projects.map(p=>[p.id,`${p.character}${p.costume?' / '+p.costume:''}`]))};
        view.innerHTML=`<section class="library-browser"><form id="library-filter-form" class="library-filters"><label class="library-query">找图<input name="q" aria-label="跨项目搜索图片" maxlength="400" placeholder="标题、作者、项目或审美笔记"></label>${select('范围','scope',{all:'全部可浏览图片',kept:'本角色参考（K）',inspiration:'我的审美收藏'},filters.scope)}${choices('viewpoint')}${choices('framing')}<details class="library-more"><summary>更多条件</summary><div class="form-grid">${choices('pose')}${choices('orientation')}${select('图片类型','kind',{'':'全部',...kinds},'')}${select('限定项目','project_id',projects,'')}</div></details><button type="submit" class="primary">查找</button><button type="button" id="library-reset">清空条件</button></form><div class="library-saved-bar"><select id="library-saved-search" aria-label="常用搜索"></select><button id="library-save-search">保存当前搜索</button><button id="library-delete-search" disabled>删除该搜索</button></div><p class="form-help">同图只显示一次；分类是找图线索，不代替核验。未分类的旧图不会被自动猜标签。</p><p id="library-status" role="status"></p><div id="library-grid" class="library-grid"></div><div class="pagination"><button id="library-prev">上一页</button><span id="library-page"></span><button id="library-next">下一页</button></div></section>`;
        syncControls();drawSaved();
        $('library-filter-form').onsubmit=e=>{e.preventDefault();filters={...defaults,...Object.fromEntries(new FormData(e.target))};offset=0;selectedSearch='';drawSaved();load().catch(showError);};
        $('library-reset').onclick=()=>{filters={...defaults};offset=0;selectedSearch='';syncControls();drawSaved();load().catch(showError);};
        $('library-prev').onclick=()=>{offset=Math.max(0,offset-60);load().catch(showError);};
        $('library-next').onclick=()=>{offset+=60;load().catch(showError);};
        $('library-save-search').onclick=saveDialog;
        $('library-saved-search').onchange=e=>{
            const chosen=saved.find(s=>s.id===e.target.value);selectedSearch=chosen?.id||'';drawSaved();
            if(chosen){filters={...defaults,...chosen.filters};offset=0;syncControls();load().catch(showError);}
        };
        $('library-delete-search').onclick=async()=>{
            const chosen=saved.find(s=>s.id===selectedSearch);
            if(!chosen||!window.confirm(`删除常用搜索“${chosen.name}”？不会删除图片。`))return;
            try {await api(`/api/library/searches/${chosen.id}?expected_revision=${chosen.revision}`,{method:'DELETE'});saved=saved.filter(s=>s.id!==chosen.id);selectedSearch='';drawSaved();}catch(e){showError(e);}
        };
        const epoch=state.epoch;
        await load();
        const searches=await api('/api/library/searches');
        if(state.view==='library'&&epoch===state.epoch){saved=searches;drawSaved();}
    }
    async function load() {
        controller?.abort();controller=new AbortController();
        const stamp=++requestId,epoch=state.epoch;
        const currentRequest=()=>stamp===requestId&&state.view==='library'&&state.epoch===epoch;
        $('library-status').textContent='正在查找…';
        $('library-prev').disabled=true;$('library-next').disabled=true;
        try {
            const q=new URLSearchParams({...filters,limit:60,offset});
            const data=await api('/api/library/assets?'+q,{signal:controller.signal});
            if(!currentRequest())return;
            items=data.items;offset=data.offset;
            $('library-status').textContent=data.total?`${data.total} 张独立图片`:'没有符合这些条件的图片。可以清空条件，或先为常用图片补充分类。';
            $('library-grid').innerHTML=items.map(item=>{
                const tags=Object.entries(item.annotation).filter(([key,v])=>facetChoices[key]?.[v]).map(([key,v])=>badge(facetChoices[key][v])).join('');
                const projects=[...new Set(item.uses.filter(u=>u.decision!=='reject'&&!u.filtered).map(u=>u.character))];
                return `<article class="library-tile"><button class="library-preview" data-library-item="${esc(item.id)}" aria-label="查看 ${esc(item.title)}">${item.file_available?`<img loading="lazy" decoding="async" src="/api/assets/${item.id}/thumb" alt="${esc(item.title)}">`:'<span>原图缺失</span>'}</button><h3>${esc(item.title)}</h3><p>${esc(projects.slice(0,3).join(' / '))}${projects.length>3?` 等 ${projects.length} 个项目`:''}${item.inspiration_id?' · 审美收藏':''}</p><div class="library-tile-tags">${tags||badge('尚未分类')}</div></article>`;
            }).join('');
            listen('library-grid','[data-library-item]','click',(e,n)=>detail(n.dataset.libraryItem));
            $('library-page').textContent=`${data.total?offset+1:0}–${offset+items.length} / ${data.total}`;
            $('library-prev').disabled=offset===0;$('library-next').disabled=offset+items.length>=data.total;
            rememberNavigation();
        } catch(error) {
            if(error.name==='AbortError'||!currentRequest())return;
            items=[];$('library-grid').replaceChildren();$('library-page').textContent='';
            $('library-status').textContent='查找失败：'+error.message;
        }
    }
    function saveDialog() {
        const snapshot={...filters};
        const root=modal('保存常用搜索',`<form>${label('搜索名称','name','','text','required maxlength="80"')}<p class="form-help">保存的是查找条件，不是固定图片清单；新图符合条件时会自动出现。</p><div class="form-actions"><button type="submit" class="primary">保存搜索</button></div></form>`);
        formSubmit(root,async data=>{
            const item=await api('/api/library/searches',{method:'POST',body:{name:data.name,filters:snapshot}});
            saved=[item,...saved];selectedSearch=item.id;closeModal();drawSaved();toast('常用搜索已保存');
        });
    }
    function detail(id) {
        const item=items.find(x=>x.id===id);if(!item)return;
        const root=modal(item.title,`<div class="library-detail"><img class="library-detail-image" src="/api/assets/${item.id}/preview" alt="${esc(item.title)}"><button id="library-original" ${item.file_available?'':'disabled'}>查看独立原图</button><h3>这张图的使用关系</h3><div class="library-use-list">${item.uses.map(u=>`<button data-library-use="${esc(u.id)}">${esc(u.character)}${u.costume?' / '+esc(u.costume):''} · ${esc(decisions[u.decision])}${u.filtered?' · 已过滤':''}</button>`).join('')||'<p>没有活跃项目使用关系。</p>'}${item.inspiration_id?'<span class="badge">已独立收藏到我的审美库</span>':''}</div><p class="form-help">这里显示的是项目用途，不代表画面角色身份。项目选择互不覆盖。</p><form><h3>摄影分类</h3><div class="form-grid">${['viewpoint','framing','pose'].map(key=>choices(key,true,item.annotation[key])).join('')}</div><p class="form-help">只为这张图记录找图线索；不会修改保留、淘汰、审美画像或现场卡验收。</p><div class="form-actions"><button type="submit" class="primary" ${item.file_available?'':'disabled'}>保存摄影分类</button></div></form></div>`);
        $('library-original').onclick=()=>openImage(item);
        listen(root,'[data-library-use]','click',async(e,n)=>{
            const ref=await api('/api/references/'+encodeURIComponent(n.dataset.libraryUse));
            if(!state.projects.some(p=>p.id===ref.project_id))throw new Error('项目已归档，请先恢复项目');
            closeModal();
            await navigate(ref.detached_at||ref.decision==='reject'?'recycle':ref.preflight_filtered?'filtered':'references',ref.project_id,ref.id);
        });
        formSubmit(root,async data=>{
            await api(`/api/library/assets/${item.id}/annotation`,{method:'PUT',body:{...data,expected_revision:item.annotation.revision}});
            closeModal();await load();toast('摄影分类已保存');
        });
    }
    return {init,restore,navigationParams,reset,visit,renderProjects,render};
})();
