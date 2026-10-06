'use strict';
(() => {
    const $ = id => document.getElementById(id);
    const escape = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
    // Topic content and case annotations are explicit UI examples, not image observations.
    const topics = [
        {id:'composition', title:'构图与画面组织', description:'先看画面的秩序，再看人物的位置。', hint:'线条、留白与层次，怎样引导视线？', cover:['P97'], shape:'wide', cases:['P97','P317','P339','P107'],
            question:'人物之外的空间，怎样成为画面的一部分？', rules:['先找画面里最吸引视线的位置。','比较人物、前景和背景的关系。','试着保留一种清晰的画面秩序。'], problem:'拍摄时只盯着人物，忘记检查画面边缘。', conclusion:'先整理背景与边缘，再决定把人物放在哪里。', next:'在同一个场景里，分别尝试居中、偏置与大量留白。'},
        {id:'perspective', title:'机位、焦段与透视', description:'把相机放在哪里，比“蹲得多低”更重要。', hint:'把高度、俯仰与距离，分开看。', cover:['P338','P332'], shape:'tall duo', cases:['P338','P94','P104','P97','P332','P336','P359','P339','P92'],
            question:'为什么低机位并不天然产生威严感，有时反而会让人物出现头大身小、画面倾斜和比例怪异？',
            rules:['相机高度与镜头俯仰是两个变量。','广角近距离会强化前后距离差。','仰拍是否产生气势，与人物姿态、画面垂直线、焦段和主体占比共同相关。','低机位不等于必须让相机剧烈上仰。'],
            problem:'想拍出气势时，只顾着降低机位；靠近人物后，没有重新检查脸、身体与道具的前后关系。',
            conclusion:'先确定人物比例与姿态，再分别调整相机高度、距离和俯仰。',
            next:'固定姿态，分别拍平视、低机位微仰、低机位明显仰拍；再换远一点的位置，比较人物比例与背景垂直线。'},
        {id:'pose', title:'人物姿态与重心', description:'让身体有落点，让动作有方向。', hint:'从肩、手与支撑点开始观察。', cover:['P359','P104'], shape:'square duo', cases:['P359','P104','P364','P348'],
            question:'同样的姿势，为什么有时自然，有时像在用力摆拍？', rules:['先观察支撑身体的落点。','分开看肩、胯与视线的方向。','让手的动作服务于人物正在做的事。'], problem:'只模仿手的位置，没有交代身体重心。', conclusion:'从稳定的站姿或坐姿开始，再添加一个小动作。', next:'保持机位，让人物分别改变支撑腿、肩向与视线，比较差异。'},
        {id:'props', title:'人物与武器 / 道具空间', description:'道具不是附件，它也参与画面的结构。', hint:'看清手、道具与脸的前后关系。', cover:['P364'], shape:'tall', cases:['P338','P332','P364','P104','P336'],
            question:'怎样让道具进入画面，又不遮挡人物的表达？', rules:['检查道具和身体的轮廓是否重叠。','观察道具指向哪里。','比较靠近镜头和贴近身体的不同关系。'], problem:'只确认道具入镜，没有留意它与脸部的重叠。', conclusion:'先理清空间关系，再强调道具的存在感。', next:'固定身体姿态，只改变道具方向与前后距离，拍三张对照。'},
        {id:'light', title:'光线与人物塑形', description:'沿着明暗的边界，读出人物的体积。', hint:'光落在哪里，视线就去哪里。', cover:['P291','P360'], shape:'square duo', cases:['P291','P360','P327','P92'],
            question:'光已经够亮了，人物为什么还是显得平？', rules:['观察主光从哪一个方向进入。','同时看亮部的形状与阴影的落点。','比较人物与背景的明暗关系。'], problem:'关注亮度多于光的方向与层次。', conclusion:'先找能描述脸部和身体的光，再决定曝光。', next:'在同一扇窗边缓慢转身，比较三个朝向的光影。'},
        {id:'scale', title:'景别与人物比例', description:'靠近或退后，都在改变故事的重点。', hint:'人物在画面里，应该占多大？', cover:['P336','P317'], shape:'square stack', cases:['P336','P97','P317','P339','P332'],
            question:'环境值得保留多少，人物才不会被淹没？', rules:['先决定此刻最想让人看见什么。','比较全身、半身和近景的叙述重点。','留意头顶、脚下与画面边缘的空间。'], problem:'每张照片都用相近的主体占比。', conclusion:'让景别回应内容，而不是习惯。', next:'在同一个场景完成环境、全身、半身和细节四张照片。'},
        {id:'expression', title:'角色表达与气势', description:'让眼神、姿态与环境说同一句话。', hint:'画面里的情绪，是否指向同一个方向？', cover:['P92'], shape:'tall', cases:['P92','P338','P291','P327'],
            question:'服装与道具都到位后，角色感还来自哪里？', rules:['先说清这张画面里的情绪。','检查视线、肩向与手部动作是否一致。','把背景也纳入角色的情境。'], problem:'动作很多，但情绪并不明确。', conclusion:'先确定一个意图，再让画面元素支持它。', next:'只改变视线与呼吸节奏，尝试安静、警觉、坚定三种表达。'},
        {id:'direction', title:'现场执行与调度', description:'把脑海里的画面，变成清楚的现场沟通。', hint:'一次只给一个可以执行的动作。', cover:['P363','P94'], shape:'wide stack', cases:['P363','P94','P348','P359'],
            question:'怎样让对方听懂指令，又保留自然的反应？', rules:['先说明站位与动作的起点。','用具体方向替代模糊的形容词。','每次调整一个地方，并观察反馈。'], problem:'连续给出太多要求，让动作变得僵硬。', conclusion:'减少同时变化的条件，让沟通有节奏。', next:'用三条短指令完成一次站位、视线和手部动作的调整。'},
        {id:'post', title:'后期与最终呈现', description:'让处理后的画面，仍然服务于最初的意图。', hint:'保留什么，比加上什么更重要。', cover:['P327'], shape:'wide', cases:['P327','P336','P97','P107'],
            question:'怎样判断一次调整是在强化表达，还是在分散注意？', rules:['先确定希望保留的画面感受。','比较调整前后的视线落点。','在一组照片里检查色彩与明暗关系。'], problem:'对局部反复调整，却忘记回看整体。', conclusion:'每一步处理都应有一个明确的视觉目的。', next:'先写下一句画面意图，再比较两种克制的处理方向。'},
        {id:'motion', title:'运镜与动态画面', description:'让人物的动作和相机的移动发生关系。', hint:'从动作开始之前，看到动作结束之后。', cover:['P348','P94'], shape:'square duo', cases:['P94','P348','P92','P104'],
            question:'相机该跟着人物走，还是留在原地等动作发生？', rules:['先观察动作的起点与终点。','分别考虑人物移动和相机移动。','留意进入、经过和离开画面的节奏。'], problem:'追着动作走，却没有预留结束的位置。', conclusion:'先设计一个完整的小动作，再决定相机的路线。', next:'用固定机位和缓慢跟随各拍一次相同动作，比较叙述感。'}
    ];
    const byTopic = id => topics.find(topic => topic.id === id);
    const storageKey = 'reference-lab.learning-map.v2';
    let assets = [], icons = {}, recent = [], lastRoute = '', activeTopic = null, activeCase = null;
    let returnTarget = null, returnTopicId = '', mapScroll = 0, searchTimer, ready = false;
    let ignoreDialogClose = false, initialRoute = true, openedFromTopic = false;
    try {
        const raw = JSON.parse(sessionStorage.getItem(storageKey) || '{}');
        recent = Array.isArray(raw.recent) ? [...new Set(raw.recent.filter(id => byTopic(id)))].slice(0,5) : [];
        lastRoute = typeof raw.route === 'string' && raw.route.startsWith('#') && raw.route.length < 1000 ? raw.route : '';
    } catch { /* The two pages also work when tab storage is unavailable. */ }
    const icon = name => '<span class="icon" aria-hidden="true">' + (icons[name] || '') + '</span>';
    function hydrate(root = document) {
        root.querySelectorAll('i[data-icon]').forEach(node => { node.outerHTML = icon(node.dataset.icon); });
    }
    function remember() {
        try { sessionStorage.setItem(storageKey, JSON.stringify({recent, route:location.hash})); }
        catch { /* No server writes or fake persistent-save confirmation. */ }
    }
    function safeSource(value) {
        try { const url = new URL(value); return ['http:','https:'].includes(url.protocol) ? url.href : ''; }
        catch { return ''; }
    }
    function topicHash(id) { return '#topic=' + encodeURIComponent(id); }
    function caseItems(topic) {
        const preferred = topic.cases.map(id => assets.find(item => item.id === id)).filter(Boolean);
        return [...preferred, ...assets.filter(item => !preferred.includes(item))].slice(0,9);
    }
    function layoutMap() {
        if ($('map-view').hidden) return;
        const style = getComputedStyle($('topic-grid'));
        const unit = parseFloat(style.getPropertyValue('--masonry-unit')) || 4;
        const gap = parseFloat(style.getPropertyValue('--map-row-gap')) || 32;
        $('topic-grid').querySelectorAll('.topic-entry').forEach(entry => {
            const span = Math.ceil((entry.firstElementChild.getBoundingClientRect().height + gap) / unit);
            const value = 'span ' + span;
            if (entry.style.gridRowEnd !== value) entry.style.gridRowEnd = value;
        });
    }
    function fitStickyNote() {
        const note = $('research-note');
        const header = document.querySelector('.site-header').getBoundingClientRect().height;
        note.classList.toggle('can-stick', innerWidth > 850 && note.scrollHeight < innerHeight - header - 48);
    }
    function renderMap(query) {
        const matches = topics.filter(topic => (topic.title + topic.description + topic.hint).includes(query.trim()));
        $('topic-grid').innerHTML = matches.map(topic => {
            const index = topics.indexOf(topic);
            const covers = topic.cover.map((id, n) => assets.find(item => item.id === id) || assets[(index * 2 + n) % assets.length]).filter(Boolean);
            const classes = topic.shape.split(' ').map(shape => 'cover-' + shape).join(' ');
            return '<article class="topic-entry"><a class="topic-link" data-topic="' + topic.id + '" href="' + topicHash(topic.id) + '" aria-label="' + escape(topic.title) + '"><div class="topic-cover ' + classes + '">' +
                (covers.length ? covers.map(item => '<img src="' + escape(item.src) + '" alt="" width="' + item.width + '" height="' + item.height + '" loading="' + (index < 4 ? 'eager' : 'lazy') + '">').join('') : '<span class="cover-placeholder">专题封面</span>') +
                '<span class="cover-hint">' + escape(topic.hint) + '</span></div><div class="topic-label"><h2>' + escape(topic.title) + '</h2>' + icon('arrow-up-right') + '</div></a></article>';
        }).join('');
        $('empty-state').hidden = matches.length !== 0;
        $('topic-grid').hidden = matches.length === 0;
        requestAnimationFrame(layoutMap);
    }
    function caseAnnotation(index) {
        // Mock labels explicitly marked in hover, gallery note and lightbox.
        const labels = [
            ['成功案例', '低机位 · 35mm · 人物占比高', '相机高度改变时，人物轮廓与背景垂直线会怎样变化？'],
            ['失败案例', '镜头俯仰 · 画面倾斜', '画面倾斜是在帮助表达，还是让你忽略了人物比例？'],
            ['成功案例', '身体方向 · 空间层次', '人物、道具与环境分别处在怎样的前后关系里？'],
            ['成功案例', '环境比例 · 留白', '如果靠近人物一些，画面的重点会发生什么变化？'],
            ['失败案例', '近距离 · 透视关系', '靠近镜头的部位是否吸引了过多注意？'],
            ['成功案例', '人物占比 · 景别', '这张照片保留了多少环境，又让你看见了多少人物？']
        ];
        const [kind, tags, question] = labels[index % labels.length];
        return {kind, tags, question};
    }
    function renderTopic(topic) {
        $('topic-view').dataset.topic = topic.id;
        $('research-note').innerHTML = '<header class="note-heading"><h1 id="topic-title" tabindex="-1">' + escape(topic.title) + '</h1><p>' + escape(topic.description) + '</p></header>' +
            '<section data-section="question"><h2>当前核心问题</h2><p class="core-question">' + escape(topic.question) + '</p></section>' +
            '<section data-section="rules" class="ruled"><h2>关键规律</h2><ul>' + topic.rules.map(rule => '<li>' + escape(rule) + '</li>').join('') + '</ul></section>' +
            '<section data-section="problems"><h2>我目前容易出现的问题</h2><p>' + escape(topic.problem) + '</p></section>' +
            '<section data-section="conclusion" class="conclusion"><h2>当前结论</h2><p>' + escape(topic.conclusion) + '</p></section>' +
            '<section data-section="next"><h2>下一次实拍需要验证什么</h2><p>' + escape(topic.next) + '</p></section>' +
            '<p class="note-meta">示例研究笔记 · ' + (topic.id === 'perspective' ? '核心问题与关键规律采用本轮给定内容' : '用于体验同一套专题模板') + '</p>';
        const items = caseItems(topic);
        $('case-gallery').innerHTML = items.length ? items.map((item, index) => {
            const label = caseAnnotation(index);
            return '<figure class="case-figure"><button class="case-open" data-case="' + index + '" aria-label="查看案例：' + escape(item.originalTitle || item.title) + '"><img src="' + escape(item.src) + '" width="' + item.width + '" height="' + item.height + '" alt="' + escape(item.originalTitle || item.title) + '" loading="' + (index < 4 ? 'eager' : 'lazy') + '"><span class="case-overlay">' + icon('arrows-maximize') + '<strong>' + label.kind + ' · 示例</strong><small>' + label.tags + '</small></span></button></figure>';
        }).join('') : '<p class="asset-notice">案例图片暂时不可用，研究笔记仍可浏览。</p>';
        $('case-gallery').querySelectorAll('[data-case]').forEach(button => button.onclick = () => {
            returnTarget = button;
            openedFromTopic = true;
            navigate(topicHash(topic.id) + '&case=' + button.dataset.case, false, false);
        });
        requestAnimationFrame(fitStickyNote);
    }
    function renderRecent() {
        $('recent-panel').innerHTML = '<h2>最近学习</h2>' + (recent.length ? recent.map(id => '<a data-recent="' + id + '" href="' + topicHash(id) + '">' + escape(byTopic(id).title) + '</a>').join('') : '<p>还没有最近学习。打开一个专题，从这里继续。</p>');
    }
    function closeRecent() {
        $('recent-panel').hidden = true;
        $('recent-toggle').setAttribute('aria-expanded', 'false');
    }
    function showCase(index) {
        const items = caseItems(activeTopic);
        const item = items[index];
        if (!item) return;
        activeCase = index;
        const label = caseAnnotation(index);
        $('viewer-title').textContent = item.originalTitle || item.title;
        $('viewer-kind').textContent = label.kind + ' · 示例标注';
        $('viewer-tags').textContent = label.tags;
        $('viewer-note').textContent = label.question;
        $('viewer-author').textContent = item.author || '摄影署名待补充';
        $('viewer-source').hidden = !safeSource(item.sourceUrl);
        if (safeSource(item.sourceUrl)) $('viewer-source').href = safeSource(item.sourceUrl);
        else $('viewer-source').removeAttribute('href');
        $('viewer-rights').open = false;
        $('viewer-restrictions').textContent = item.restrictions || '沿用本地素材的原始出处，仅用于私人视觉原型，不代表新增使用许可。';
        $('viewer-position').textContent = (index + 1) + ' / ' + items.length;
        $('viewer-prev').disabled = index === 0;
        $('viewer-next').disabled = index === items.length - 1;
        $('viewer-image-error').hidden = true;
        $('viewer-image').alt = item.originalTitle || item.title;
        $('viewer-image').src = item.src;
        if (!$('case-viewer').open) $('case-viewer').showModal();
    }
    function hideCase() {
        if (!$('case-viewer').open) return;
        ignoreDialogClose = true;
        $('case-viewer').close();
        activeCase = null;
        if (returnTarget?.isConnected) returnTarget.focus({preventScroll:true});
    }
    function renderRoute(focus = false) {
        if (!ready) return;
        const params = new URLSearchParams(location.hash.slice(1));
        const topic = byTopic(params.get('topic'));
        const query = (params.get('q') || '').slice(0,100);
        const changedTopic = activeTopic?.id !== topic?.id;
        const wasTopic = !!activeTopic;
        if (changedTopic || !topic) hideCase();
        activeTopic = topic || null;
        $('map-view').hidden = !!topic;
        $('topic-view').hidden = !topic;
        $('search').value = topic ? '' : query;
        closeRecent();
        if (topic) {
            if (changedTopic) {
                returnTopicId = topic.id;
                renderTopic(topic);
                recent = [topic.id, ...recent.filter(id => id !== topic.id)].slice(0,5);
            }
            document.title = topic.title + ' · 摄影学习';
            const value = params.get('case');
            const index = value !== null && /^\d+$/.test(value) ? Number(value) : -1;
            if (index >= 0 && index < caseItems(topic).length) showCase(index);
            else { hideCase(); activeCase = null; }
            if (changedTopic) {
                window.scrollTo(0,0);
                if (focus) $('topic-title').focus({preventScroll:true});
            }
        } else {
            document.title = '摄影能力地图 · 摄影学习';
            renderMap(query);
            if (wasTopic && focus) {
                requestAnimationFrame(() => {
                    window.scrollTo(0,mapScroll);
                    const target = $('topic-grid').querySelector('[data-topic="' + returnTopicId + '"]');
                    (target || $('map-title')).focus({preventScroll:true});
                });
            } else if (focus) window.scrollTo(0,0);
        }
        if (initialRoute) { initialRoute = false; openedFromTopic = false; }
        remember();
    }
    function navigate(hash, replace = false, focus = true) {
        clearTimeout(searchTimer);
        if (location.hash !== hash) history[replace ? 'replaceState' : 'pushState'](null,'',hash);
        renderRoute(focus);
    }
    function closeViewer() {
        if (!$('case-viewer').open) return;
        if (openedFromTopic) {
            openedFromTopic = false;
            history.back();
        } else navigate(topicHash(activeTopic.id), true, false);
    }
    function nextCase(delta) {
        const next = activeCase + delta;
        if (activeTopic && next >= 0 && next < caseItems(activeTopic).length)
            navigate(topicHash(activeTopic.id) + '&case=' + next, true, false);
    }
    function wire() {
        document.addEventListener('click', event => {
            const link = event.target.closest('a[href^="#"]');
            if (link && !event.ctrlKey && !event.metaKey && !event.shiftKey && !event.altKey && event.button === 0) {
                if (link.classList.contains('skip-link')) {
                    event.preventDefault(); $('main').focus(); return;
                }
                event.preventDefault();
                if (link.dataset.topic) mapScroll = scrollY;
                navigate(link.getAttribute('href'));
            }
            if (!event.target.closest('.recent-wrap')) closeRecent();
        });
        $('search').oninput = () => {
            clearTimeout(searchTimer);
            searchTimer = setTimeout(() => {
                const query = $('search').value.slice(0,100);
                const hash = query ? '#' + new URLSearchParams({q:query}) : '#map';
                navigate(hash, !activeTopic, false);
            },120);
        };
        $('clear-search').onclick = () => { navigate('#map'); $('search').focus(); };
        $('recent-toggle').onclick = () => {
            renderRecent();
            const open = $('recent-panel').hidden;
            $('recent-panel').hidden = !open;
            $('recent-toggle').setAttribute('aria-expanded', String(open));
        };
        $('viewer-close').onclick = closeViewer;
        $('viewer-prev').onclick = () => nextCase(-1);
        $('viewer-next').onclick = () => nextCase(1);
        $('viewer-image').onerror = () => { $('viewer-image-error').hidden = false; };
        $('case-viewer').addEventListener('cancel', event => { event.preventDefault(); closeViewer(); });
        $('case-viewer').addEventListener('close', () => {
            if (ignoreDialogClose) { ignoreDialogClose = false; return; }
            if (activeCase !== null && activeTopic) navigate(topicHash(activeTopic.id), true, false);
        });
        $('case-viewer').onclick = event => { if (event.target === $('case-viewer')) closeViewer(); };
        document.addEventListener('keydown', event => {
            if (event.ctrlKey || event.metaKey || event.altKey) return;
            if ($('case-viewer').open) {
                if (event.key === 'ArrowRight' || event.key === 'ArrowLeft') { event.preventDefault(); nextCase(event.key === 'ArrowRight' ? 1 : -1); }
                return;
            }
            if (event.key === 'Escape' && !$('recent-panel').hidden) { closeRecent(); $('recent-toggle').focus(); }
            if (event.key === '/' && !/INPUT|TEXTAREA/.test(document.activeElement?.tagName)) { event.preventDefault(); $('search').focus(); }
        });
        window.addEventListener('popstate', () => renderRoute(true));
        window.addEventListener('hashchange', () => renderRoute(true));
        window.addEventListener('pagehide', remember);
        new ResizeObserver(() => requestAnimationFrame(layoutMap)).observe($('topic-grid'));
        new ResizeObserver(fitStickyNote).observe($('research-note'));
        window.addEventListener('resize', fitStickyNote);
    }
    async function boot() {
        wire();
        const results = await Promise.allSettled([
            fetch('/static/learning-icons.json').then(response => response.ok ? response.json() : {}),
            fetch('/api/learning-preview', {credentials:'same-origin'}).then(response => {
                if (!response.ok) throw new Error(response.status === 401 ? '请先在拍摄参考中打开私人工作区，专题文字仍可预览。' : '暂时无法读取本地案例图片，专题文字仍可预览。');
                return response.json();
            })
        ]);
        if (results[0].status === 'fulfilled') icons = results[0].value;
        hydrate();
        if (results[1].status === 'fulfilled') {
            const items = results[1].value?.items;
            assets = (Array.isArray(items) ? items : []).filter(item => typeof item.id === 'string' && /^P\d+$/.test(item.id)
                && typeof item.src === 'string' && /^\/api\/learning-preview\/P\d+\.(jpg|jpeg|png|webp|avif)$/.test(item.src)
                && Number.isFinite(item.width) && item.width > 0 && Number.isFinite(item.height) && item.height > 0);
        }
        if (!assets.length) {
            $('asset-notice').hidden = false;
            $('asset-notice').textContent = results[1].status === 'rejected' ? results[1].reason.message : '尚无本地示例图片，先用封面占位预览专题结构。';
        }
        if (!location.hash) history.replaceState(null,'',lastRoute || '#map');
        ready = true;
        renderRoute();
    }
    boot();
})();
