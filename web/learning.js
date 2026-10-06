'use strict';
(() => {
    const $ = id => document.getElementById(id);
    const escape = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
    const topics = ['全部', '光影', '构图', '姿态', '色彩', '场景'];
    const descriptions = {
        光影: ['沿着光的方向看', '画面里最亮的地方在哪里？试着顺着明暗的边界，观察视线怎样被带到人物身上。'],
        构图: ['先看画面，再看人物', '把目光从主体移到画面边缘。前景、线条与留白，分别给人物留出了怎样的空间？'],
        姿态: ['从一个小动作开始', '留意手的落点、肩的方向和身体重心。选一个自己想尝试的小动作，不必复刻整张照片。'],
        色彩: ['找到画面的颜色关系', '先找面积最大的颜色，再找最吸引注意的小色块。它们靠相近的色调连接，还是用反差相互突出？'],
        场景: ['让环境参与画面', '想一想，如果换掉背景，这张照片的感觉会改变多少？环境是在交代故事，还是在组织构图？']
    };
    const views = {
        discover: ['把喜欢的画面，看懂一点。', '从一张照片出发，慢慢建立自己的拍摄语言。'],
        topics: ['换一个角度，重新看照片。', '从光影到场景，带着一个问题开始观察。'],
        saved: ['留住想反复看的画面。', '你的原型收藏，每一张都可以成为下一次观察的起点。'],
        practice: ['把看见的，试着拍出来。', '一次只练一个小地方，让观察慢慢变成自己的经验。']
    };
    const key = 'reference-lab.learning-prototype.v1';
    let demo = [], icons = {}, storageAvailable = true, toastTimer, searchTimer;
    let state = {view:'discover', topic:'全部', query:'', spacious:false, active:null, tab:'notes', wallScroll:0, returnFocus:null};
    let saved = new Set(), practice = {}, notes = {}, lastRoute = '';
    try {
        const raw = JSON.parse(sessionStorage.getItem(key) || '{}');
        saved = new Set(Array.isArray(raw.saved) ? raw.saved.filter(x => typeof x === 'string') : []);
        practice = raw.practice && typeof raw.practice === 'object' && !Array.isArray(raw.practice) ? raw.practice : {};
        notes = raw.notes && typeof raw.notes === 'object' && !Array.isArray(raw.notes) ? raw.notes : {};
        lastRoute = typeof raw.route === 'string' && raw.route.startsWith('#') && raw.route.length < 4096 ? raw.route : '';
    } catch { storageAvailable = false; }

    function persist() {
        try { sessionStorage.setItem(key, JSON.stringify({saved:[...saved], practice, notes, route:location.hash})); storageAvailable = true; }
        catch { storageAvailable = false; }
    }
    function icon(name) { return `<span class="icon" aria-hidden="true">${icons[name] || ''}</span>`; }
    function hydrate(root = document) {
        root.querySelectorAll('i[data-icon]').forEach(node => { node.outerHTML = icon(node.dataset.icon); });
    }
    function toast(message) {
        $('toast').textContent = message;
        $('toast').hidden = false;
        clearTimeout(toastTimer);
        toastTimer = setTimeout(() => $('toast').hidden = true, 2800);
    }
    function safeLink(url) {
        try { const parsed = new URL(url); return ['http:','https:'].includes(parsed.protocol) ? parsed.href : ''; }
        catch { return ''; }
    }
    function matching() {
        const terms = state.query.trim().toLocaleLowerCase().split(/\s+/).filter(Boolean);
        return demo.filter(item => {
            const text = `${item.id} ${item.title} ${item.originalTitle} ${item.topic} ${item.author}`.toLocaleLowerCase();
            return (state.topic === '全部' || item.topic === state.topic)
                && (state.view !== 'saved' || saved.has(item.id))
                && (state.view !== 'practice' || Object.hasOwn(practice,item.id))
                && terms.every(term => text.includes(term));
        });
    }
    function storeNote() {
        const input = $('study-note');
        if (input && state.active) {
            notes[state.active] = input.value.slice(0,3000);
            persist();
        }
    }
    function updateCounts() {
        $('saved-count').textContent = demo.filter(item => saved.has(item.id)).length;
        $('practice-count').textContent = demo.filter(item => Object.hasOwn(practice,item.id)).length;
    }
    function setView(view) {
        if (!views[view]) return;
        storeNote();
        state.active = null;
        state.view = view;
        state.topic = '全部'; state.query = ''; $('search').value = '';
        renderWall(); updateHistory(); window.scrollTo(0,0);
    }
    function updateHistory(replace = false) {
        const params = new URLSearchParams({view:state.view});
        if (state.topic !== '全部') params.set('topic', state.topic);
        if (state.query) params.set('q',state.query);
        if (state.active) params.set('photo',state.active);
        const target = '#'+params.toString();
        if (location.hash !== target) history[replace ? 'replaceState' : 'pushState'](null,'',target);
        persist();
    }
    function setTopic(topic) {
        state.topic = topics.includes(topic) ? topic : '全部';
        if (state.view === 'topics') state.view = 'discover';
        state.active = null;
        renderWall(); updateHistory(); window.scrollTo(0,0);
    }
    function card(item, related = false) {
        const isSaved = saved.has(item.id);
        const status = state.view === 'practice' && !related ? `<div class="practice-state"><label><input type="checkbox" data-complete="${escape(item.id)}" ${practice[item.id] ? 'checked' : ''}>${practice[item.id] ? '这次练过了' : '找机会试试'}</label><button data-remove-practice="${escape(item.id)}" aria-label="移出练习 ${escape(item.title)}">移出</button></div>` : '';
        return `<article class="photo-card ${isSaved?'is-saved':''}" data-card="${escape(item.id)}">
            <button class="image-open" data-open="${escape(item.id)}" aria-label="打开 ${escape(item.title)}"><img src="${escape(item.src)}" width="${item.width}" height="${item.height}" loading="lazy" decoding="async" alt="${escape(item.originalTitle || item.title)}"></button>
            <div class="card-actions"><button class="save-btn" data-save="${escape(item.id)}" aria-label="${isSaved?'取消收藏':'收藏'} ${escape(item.title)}" aria-pressed="${isSaved}">${icon('bookmark')}</button></div>
            <div class="card-caption"><div><button class="card-title" data-open="${escape(item.id)}">${escape(item.title)}</button><div class="card-meta"><span>${escape(item.topic)}</span><span class="separator">·</span><span>摄影参考</span></div></div><button class="icon-btn" data-open="${escape(item.id)}" aria-label="查看笔记 ${escape(item.title)}" title="查看与记录">${icon('arrow-up-right')}</button></div>${status}</article>`;
    }
    function bindCards(root) {
        root.querySelectorAll('[data-open]').forEach(button => button.onclick = () => openDetail(button.dataset.open));
        root.querySelectorAll('[data-save]').forEach(button => button.onclick = () => toggleSave(button.dataset.save));
        root.querySelectorAll('[data-complete]').forEach(input => input.onchange = () => {
            practice[input.dataset.complete] = input.checked; persist();
            renderWall(); toast(input.checked ? '记下这次练习了' : '已改回待练习');
        });
        root.querySelectorAll('[data-remove-practice]').forEach(button => button.onclick = () => {
            delete practice[button.dataset.removePractice]; persist(); renderWall(); toast('已移出原型练习清单');
        });
        root.querySelectorAll('img').forEach(img => img.onerror = () => {
            img.parentElement.classList.add('media-error');
            img.replaceWith(Object.assign(document.createElement('span'), {textContent:'图片暂时无法显示'}));
        });
    }
    function toggleSave(id) {
        saved.has(id) ? saved.delete(id) : saved.add(id);
        persist(); updateCounts();
        // Update only the affected card, preserving image decode and keyboard focus.
        document.querySelectorAll('[data-save]').forEach(button => {
            if (button.dataset.save !== id) return;
            const yes = saved.has(id), item = demo.find(x => x.id === id);
            button.setAttribute('aria-pressed',String(yes));
            button.setAttribute('aria-label',`${yes?'取消收藏':'收藏'} ${item?.title || ''}`);
            if (button.id === 'detail-save') button.innerHTML = icon('bookmark') + (yes ? '已收藏' : '收藏');
            button.closest('.photo-card')?.classList.toggle('is-saved',yes);
        });
        if (!state.active && state.view === 'saved') renderWall();
        toast(saved.has(id) ? '已加入原型收藏 · 仅当前标签页' : '已取消原型收藏');
    }
    function renderWall() {
        $('browse-view').hidden = false; $('detail-view').hidden = true;
        $('page-title').textContent = views[state.view][0]; $('page-subtitle').textContent = views[state.view][1];
        document.querySelectorAll('[data-view]').forEach(button => {
            button.classList.toggle('active',button.dataset.view === state.view);
            if (button.dataset.view === state.view) button.setAttribute('aria-current','page'); else button.removeAttribute('aria-current');
        });
        $('topic-filters').innerHTML = topics.map(topic => `<button class="topic-chip ${state.topic===topic?'active':''}" data-topic="${topic}" aria-pressed="${state.topic===topic}">${topic==='全部'?'全部灵感':topic}</button>`).join('');
        $('topic-filters').querySelectorAll('[data-topic]').forEach(button => button.onclick = () => setTopic(button.dataset.topic));
        const items = matching(), topicView = state.view === 'topics' && !state.query;
        $('gallery').classList.toggle('spacious',state.spacious);
        $('gallery').hidden = topicView;
        $('topic-overview').hidden = !topicView;
        $('result-count').textContent = `${items.length} 张参考`;
        if (topicView) {
            $('topic-overview').innerHTML = `<p class="topic-intro">这里的主题是原型演示分组，你可以先试试这样的学习入口。</p><div class="topic-grid">${topics.slice(1).map(topic => {
                const group = demo.filter(x => x.topic === topic), first = group[0];
                return `<button class="topic-tile" data-topic="${topic}" ${first?'':'disabled'}>${first?`<img src="${escape(first.src)}" alt="" loading="lazy">`:''}<span class="topic-title"><strong>${topic}</strong><small>${descriptions[topic][0]} · ${group.length} 张参考</small></span></button>`;
            }).join('')}</div>`;
            $('topic-overview').querySelectorAll('[data-topic]').forEach(button => button.onclick = () => setTopic(button.dataset.topic));
        } else {
            $('gallery').innerHTML = items.map(item => card(item)).join(''); bindCards($('gallery'));
        }
        $('empty-state').hidden = topicView ? demo.length > 0 : items.length > 0;
        $('gallery-footer').hidden = !items.length;
        $('random-study').disabled = !demo.length;
        if (!items.length) {
            const messages = state.query || state.topic !== '全部' ? ['还没找到这样的画面','试试换一个关键词，或回到全部灵感。','清除筛选'] : state.view === 'saved' ? ['喜欢的画面，先留在这里','点击照片上的收藏图标，再回来慢慢看。','去发现'] : state.view === 'practice' ? ['下一次拍摄，从一个小练习开始','打开一张照片，加入练习清单。想练什么，由你决定。','去发现'] : ['还没有载入示例图片','这个原型需要本地私有示例素材；你的正式参考库没有变化。',''];
            $('empty-title').textContent = messages[0]; $('empty-copy').textContent = messages[1];
            $('empty-action').textContent = messages[2]; $('empty-action').hidden = !messages[2];
        }
        updateCounts();
    }
    function detailContent(item) {
        const [question,prompt] = descriptions[item.topic] || descriptions.构图;
        if (state.tab === 'source') {
            const url = safeLink(item.sourceUrl);
            return `<dl class="source-details"><dt>原素材标题 / 来源标注</dt><dd>${escape(item.originalTitle)}</dd><dt>原记录摄影署名</dt><dd>${escape(item.author || '原记录未注明')}</dd><dt>原记录发布者</dt><dd>${escape(item.publisher || '原记录未注明')}</dd><dt>公开出处</dt><dd>${url?`<a href="${escape(url)}" target="_blank" rel="noopener noreferrer">查看原发布页面 ${icon('external-link')}</a>`:'暂无可打开的来源链接'}</dd><dt>使用范围</dt><dd>${escape(item.restrictions || '仅本地私人参考。')}</dd></dl><p class="source-details source-note">来源信息沿用已有记录，未在这轮重新核验。图片用于 UI 展示，不代表已通过审美筛选；演示主题也不会写入正式分类。</p>`;
        }
        const value = typeof notes[item.id] === 'string' ? notes[item.id] : '';
        return `<div class="observation-prompt"><strong>${icon('focus-2')}${question}</strong><p>${prompt}</p></div>
            <label class="note-label" for="study-note">我的观察<span>只记录你自己的发现</span></label><textarea class="note-input" id="study-note" maxlength="3000" placeholder="哪里吸引了我？\n下一次拍摄，我想试试什么？">${escape(value)}</textarea><div class="note-footer"><span id="note-state">${storageAvailable?'笔记暂存在当前标签页':'浏览器暂存不可用，仅本次页面内保留'}</span><button id="save-note">记下这一点 ${icon('check')}</button></div>
            <div class="practice-callout">${icon('checkbox')}<div><strong>从观察，走到一次实践</strong><p>不必复刻整张照片，先试一个小地方。</p></div><button id="add-practice">${Object.hasOwn(practice,item.id)?'已加入练习':'加入练习'}</button></div>`;
    }
    function bindDetailPanel(item) {
        if ($('study-note')) {
            $('study-note').oninput = () => {
                storeNote(); $('note-state').textContent = storageAvailable ? '已暂存 · 仅当前标签页' : '暂存不可用 · 仅本次页面内保留';
            };
            $('save-note').onclick = () => { storeNote(); toast(storageAvailable ? '这点观察记下了 · 仅当前标签页' : '浏览器暂存不可用，请先复制笔记'); };
            $('add-practice').onclick = () => {
                const exists = Object.hasOwn(practice,item.id);
                if (exists) delete practice[item.id]; else practice[item.id] = false;
                persist(); updateCounts(); $('add-practice').textContent = exists ? '加入练习' : '已加入练习';
                toast(exists ? '已移出原型练习清单' : '已加入练习清单，下次拍摄试试看');
            };
        }
    }
    function openDetail(id, historyUpdate = true) {
        const item = demo.find(x => x.id === id); if (!item) return;
        storeNote();
        if (!state.active) { state.wallScroll = window.scrollY; state.returnFocus = document.activeElement; }
        state.active = id; state.tab = 'notes';
        $('browse-view').hidden = true; $('detail-view').hidden = false;
        const sequence = matching().length ? matching() : demo;
        const index = sequence.findIndex(x => x.id === id);
        const ordered = [...demo.filter(x => x.id !== id && x.topic === item.topic), ...demo.filter(x => x.id !== id && x.topic !== item.topic)].slice(0,10);
        const url = safeLink(item.sourceUrl);
        $('detail-view').innerHTML = `<div class="detail-enter"><div class="detail-top"><button class="back-button" id="back-to-wall">${icon('arrow-left')}返回图片墙</button><div class="detail-position"><span>${index >= 0 ? index+1 : '·'} / ${sequence.length}</span><button class="icon-btn" id="prev-photo" aria-label="上一张" ${index<=0?'disabled':''}>${icon('chevron-left')}</button><button class="icon-btn" id="next-photo" aria-label="下一张" ${index<0||index>=sequence.length-1?'disabled':''}>${icon('chevron-right')}</button></div></div>
            <div class="detail-layout"><div class="detail-visual"><div class="detail-photo"><button id="enlarge-photo" aria-label="放大完整图片"><img src="${escape(item.src)}" width="${item.width}" height="${item.height}" alt="${escape(item.originalTitle || item.title)}"></button><span class="enlarge-hint">${icon('arrows-maximize')}</span></div><div class="image-foot"><span>${escape(item.id)} · 私有原型素材</span><span>${item.width} × ${item.height} · 完整画面</span></div></div>
            <div class="detail-copy"><div class="detail-actions"><button class="topic-chip" id="detail-topic">${escape(item.topic)} / 学习参考</button><button class="primary" id="detail-save" data-save="${escape(id)}" aria-label="${saved.has(id)?'取消收藏':'收藏'} ${escape(item.title)}" aria-pressed="${saved.has(id)}">${icon('bookmark')}${saved.has(id)?'已收藏':'收藏'}</button></div><h1 tabindex="-1" id="detail-title">${escape(item.title)}</h1><p class="detail-lead">给自己一点时间，看看这个画面里有哪些值得再看一眼的细节。</p>
            <div class="source-line"><span class="source-initial">${escape(item.id.replace('P',''))}</span><div><strong>${escape(item.author || '本地已有参考')}</strong><small>摄影署名沿用来源记录</small></div>${url?`<a href="${escape(url)}" target="_blank" rel="noopener noreferrer" aria-label="打开原发布页面" title="打开原发布页面">${icon('external-link')}</a>`:''}</div>
            <nav class="detail-tabs" aria-label="详情内容"><button data-detail-tab="notes" class="active" aria-current="page">观察与笔记</button><button data-detail-tab="source">素材来源</button></nav><div id="detail-panel">${detailContent(item)}</div></div></div>
            <div class="related-header"><h2>换一张，接着看</h2><span>同主题优先 · 原型示例</span></div><div id="related-gallery" class="related-gallery">${ordered.map(x => card(x,true)).join('')}</div></div>`;
        $('back-to-wall').onclick = closeDetail;
        $('prev-photo').onclick = () => index > 0 && openDetail(sequence[index-1].id);
        $('next-photo').onclick = () => index >= 0 && index < sequence.length-1 && openDetail(sequence[index+1].id);
        $('detail-topic').onclick = () => { storeNote(); setTopic(item.topic); };
        $('detail-save').onclick = () => toggleSave(id);
        $('enlarge-photo').onclick = () => { $('viewer-image').src = item.src; $('viewer-image').alt = item.originalTitle || item.title; $('viewer').showModal(); };
        document.querySelectorAll('[data-detail-tab]').forEach(button => button.onclick = () => {
            storeNote(); state.tab = button.dataset.detailTab;
            document.querySelectorAll('[data-detail-tab]').forEach(x => {
                x.classList.toggle('active',x === button);
                if (x===button) x.setAttribute('aria-current','page'); else x.removeAttribute('aria-current');
            });
            $('detail-panel').innerHTML = detailContent(item); bindDetailPanel(item);
        });
        bindDetailPanel(item); bindCards($('related-gallery'));
        const photo = $('enlarge-photo').querySelector('img');
        photo.onerror = () => { photo.alt = '原图暂时无法显示，请返回图片墙重试'; $('enlarge-photo').disabled = true; };
        if (historyUpdate) updateHistory();
        window.scrollTo(0,0); $('detail-title').focus({preventScroll:true});
    }
    function closeDetail() {
        storeNote(); state.active = null; renderWall(); updateHistory();
        requestAnimationFrame(() => {
            window.scrollTo(0,state.wallScroll);
            const id = state.returnFocus?.dataset?.open;
            const target = id ? [...$('gallery').querySelectorAll('[data-open]')].find(x => x.dataset.open === id) : $('page-title');
            target?.focus({preventScroll:true});
        });
    }
    function restoreRoute() {
        storeNote(); const q = new URLSearchParams(location.hash.slice(1));
        state.view = views[q.get('view')] ? q.get('view') : 'discover';
        state.topic = topics.includes(q.get('topic')) ? q.get('topic') : '全部';
        state.query = (q.get('q') || '').slice(0,150); $('search').value = state.query;
        const photo = q.get('photo'); state.active = null; renderWall();
        if (photo && demo.some(x => x.id === photo)) openDetail(photo,false);
        persist();
    }
    function wire() {
        document.querySelector('.skip-link').onclick = event => {
            event.preventDefault(); $('main').focus({preventScroll:true}); $('main').scrollIntoView();
        };
        document.querySelectorAll('[data-view]').forEach(button => button.onclick = () => setView(button.dataset.view));
        ['about-prototype','prototype-info'].forEach(id => $(id).onclick = () => $('info-dialog').showModal());
        ['info-close','info-done'].forEach(id => $(id).onclick = () => $('info-dialog').close());
        $('viewer-close').onclick = () => $('viewer').close();
        $('viewer').addEventListener('close',() => $('viewer-image').removeAttribute('src'));
        $('empty-action').onclick = () => {
            if (state.query || state.topic !== '全部') {
                state.query = ''; state.topic = '全部'; $('search').value = '';
                renderWall(); updateHistory();
            } else setView('discover');
        };
        $('random-study').onclick = () => { const items = matching().length ? matching() : demo; if(items.length) openDetail(items[Math.floor(Math.random()*items.length)].id); };
        $('density-toggle').onclick = () => {
            state.spacious = !state.spacious; $('gallery').classList.toggle('spacious',state.spacious);
            $('density-toggle').setAttribute('aria-label',state.spacious ? '切换为紧凑布局' : '切换为宽松布局');
        };
        $('search').oninput = () => {
            clearTimeout(searchTimer);
            searchTimer = setTimeout(() => {
                storeNote(); state.active = null; state.query = $('search').value;
                renderWall(); updateHistory(true); window.scrollTo(0,0);
            },160);
        };
        document.addEventListener('keydown',event => {
            if (document.querySelector('dialog[open]') || event.ctrlKey || event.metaKey || event.altKey) return;
            const editing = /INPUT|TEXTAREA|SELECT/.test(document.activeElement?.tagName);
            if (event.key === '/' && !editing) { event.preventDefault(); $('search').focus(); }
            if (event.key === 'Escape' && state.active) { event.preventDefault(); closeDetail(); }
            if (!editing && state.active && ['ArrowLeft','ArrowRight'].includes(event.key)) {
                event.preventDefault(); $(event.key === 'ArrowLeft'?'prev-photo':'next-photo')?.click();
            }
        });
        window.addEventListener('popstate',restoreRoute);
        window.addEventListener('pagehide',storeNote);
    }
    async function boot() {
        wire(); $('empty-state').hidden = false;
        try {
            const result = await fetch('/static/learning-icons.json'); if (!result.ok) throw new Error('icons'); icons = await result.json();
        } catch { /* Accessible text controls remain usable if decorative icons fail. */ }
        hydrate();
        try {
            const response = await fetch('/api/learning-preview',{credentials:'same-origin'});
            if (!response.ok) {
                if (response.status === 401) throw new Error('请先返回拍摄参考，解锁私人工作区后再打开摄影学习。');
                throw new Error('示例图片暂时无法读取，请确认本地预览服务仍在运行。');
            }
            const payload = await response.json();
            demo = (Array.isArray(payload.items)?payload.items:[]).filter(item =>
                typeof item.id==='string' && /^P\d+$/.test(item.id) && typeof item.src==='string'
                && /^\/api\/learning-preview\/P\d+\.(jpg|jpeg|png|webp|avif)$/.test(item.src)
                && Number.isFinite(item.width) && item.width>0 && Number.isFinite(item.height) && item.height>0);
            if (!location.hash && lastRoute) history.replaceState(null,'',lastRoute);
            restoreRoute(); updateHistory(true);
        } catch (error) {
            renderWall(); $('empty-state').hidden=false; $('empty-title').textContent='暂时没能打开图片墙';
            $('empty-copy').textContent=error.message; $('empty-action').hidden=true;
        }
    }
    boot();
})();
