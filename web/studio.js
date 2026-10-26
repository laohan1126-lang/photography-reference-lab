/* Shared presentation only: no network, storage or business-state writes. */
'use strict';
(() => {
    const reduced = matchMedia('(prefers-reduced-motion: reduce)');
    const finePointer = matchMedia('(hover: hover) and (pointer: fine)');
    const root = document.documentElement;
    const scenes = [...document.querySelectorAll('[data-studio-scene]')];
    const pointer = document.createElement('span');
    pointer.className = 'studio-pointer';
    pointer.hidden = true;
    pointer.setAttribute('aria-hidden', 'true');
    pointer.innerHTML = '';
    document.body.append(pointer);
    const effects = new WeakMap();
    const activeEffects = new Set();
    const progress = document.createElement('div');
    progress.className = 'studio-progress';
    progress.setAttribute('aria-hidden', 'true');
    document.body.append(progress);
    const navigation = document.getElementById('toggle-project-nav');
    function closeNavigation() {
        document.querySelector('.sidebar')?.classList.remove('nav-open');
        navigation?.setAttribute('aria-expanded','false');
    }
    navigation?.addEventListener('click', () => {
        const open = document.querySelector('.sidebar').classList.toggle('nav-open');
        navigation.setAttribute('aria-expanded',String(open));
    });
    document.addEventListener('keydown', event => {
        if(event.key==='Escape' && navigation?.getAttribute('aria-expanded')==='true') {
            closeNavigation();navigation.focus();event.preventDefault();
        }
    });
    document.addEventListener('click', event => {
        if(event.target.closest('#project-navigation [data-view],#project-navigation [data-project-open]')) closeNavigation();
    });
    function enter(node, distance = 10) {
        if (!node?.isConnected) return;
        effects.get(node)?.cancel();
        if (reduced.matches || document.hidden) return;
        const animation = node.animate([
            { opacity:.4, transform:`translateY(${distance}px)` },
            { opacity:1, transform:'translateY(0)' }
        ], { duration:220, easing:'cubic-bezier(.2,.7,.2,1)' });
        effects.set(node, animation);
        activeEffects.add(animation);
        animation.onfinish = animation.oncancel = () => activeEffects.delete(animation);
    }
    let scheduled = false;
    function scrollFrame() {
        scheduled = false;
        const max = root.scrollHeight - innerHeight;
        root.style.setProperty('--reading', max > 0 ? Math.min(1, scrollY / max) : 0);
        for (const scene of scenes) {
            if (scene.dataset.studioVisible !== 'false') {
                const offset = reduced.matches ? 0 : Math.max(-160, Math.min(400, -scene.getBoundingClientRect().top));
                scene.style.setProperty('--scene-scroll', `${offset}px`);
            }
        }
    }
    function scheduleScroll() {
        if (!scheduled) { scheduled = true; requestAnimationFrame(scrollFrame); }
    }
    const observer = new IntersectionObserver(entries => {
        for (const entry of entries) entry.target.dataset.studioVisible = String(entry.isIntersecting);
        scheduleScroll();
    });
    for (const scene of scenes) {
        observer.observe(scene);
        let pointerFrame = 0;
        scene.addEventListener('pointermove', event => {
            if (reduced.matches || !finePointer.matches) return;
            cancelAnimationFrame(pointerFrame);
            pointerFrame = requestAnimationFrame(() => {
                const rect = scene.getBoundingClientRect();
                scene.style.setProperty('--pointer-x', `${((event.clientX - rect.left) / rect.width - .5) * 12}px`);
                scene.style.setProperty('--pointer-y', `${((event.clientY - rect.top) / rect.height - .5) * 8}px`);
                pointer.hidden = false;
                pointer.style.setProperty('--cursor-x', `${Math.min(event.clientX + 10, innerWidth - 44)}px`);
                pointer.style.setProperty('--cursor-y', `${Math.min(event.clientY + 10, innerHeight - 44)}px`);
                pointer.style.setProperty('--cursor-turn', `${(event.clientX / innerWidth - .5) * 22}deg`);
            });
        });
        scene.addEventListener('pointerleave', () => {
            cancelAnimationFrame(pointerFrame);
            pointer.hidden = true;
            scene.style.setProperty('--pointer-x', '0px');
            scene.style.setProperty('--pointer-y', '0px');
        });
    }
    const search = document.getElementById('studio-collect');
    if (search) {
        for (const type of ['pointerenter','focus']) search.addEventListener(type, () => root.dataset.studioAction = 'search');
        for (const type of ['pointerleave','blur']) search.addEventListener(type, () => delete root.dataset.studioAction);
    }
    document.addEventListener('load', event => {
        if (event.target.id === 'main-image') enter(event.target, 6);
    }, true);
    document.addEventListener('toggle', event => {
        if (event.target.matches('.studio-masthead')) {
            if (event.target.open) enter(event.target.querySelector('.studio-spread'));
            scheduleScroll();
        }
    }, true);
    document.addEventListener('visibilitychange', () => {
        root.dataset.studioHidden = String(document.hidden);
        if (!document.hidden) scheduleScroll();
    });
    reduced.addEventListener('change', () => {
        pointer.hidden = true;
        for (const scene of scenes) {
            scene.style.setProperty('--pointer-x', '0px');
            scene.style.setProperty('--pointer-y', '0px');
        }
        if (reduced.matches) {
            for (const animation of activeEffects) animation.cancel();
        }
        scheduleScroll();
    });
    addEventListener('scroll', scheduleScroll, { passive:true });
    addEventListener('resize', scheduleScroll);
    addEventListener('hashchange', () => {
        requestAnimationFrame(() => enter(document.querySelector('.detail-view:not([hidden]) h1')));
    });
    window.StudioMotion = {
        frame(text) {
            const counter=document.getElementById('studio-take-counter');
            if(counter) counter.textContent=text;
        },
        commit(choice, reference) {
            const words = {keep:'角色参考 K',inspiration:'灵感收藏 I',maybe:'待定 M',reject:'已淘汰，可恢复 X'};
            const stage = document.getElementById('image-stage');
            if (!Object.hasOwn(words,choice) || !stage?.isConnected) return;
            stage.querySelector('.stage-effect')?.remove();
            const effect = document.createElement('div');
            effect.className = 'stage-effect';
            effect.dataset.choice = choice;
            effect.dataset.reference = reference.id;
            if (!reduced.matches && reference.file_available !== false && reference.asset_sha) {
                const snapshot = document.createElement('img');
                snapshot.src = `/api/assets/${reference.asset_sha}/preview`;
                snapshot.alt = '';
                effect.append(snapshot);
            }
            const caption = document.createElement('span');
            caption.textContent = `刚保存 · ${words[choice]}`;
            effect.append(caption);
            stage.append(effect);
            const thumb = [...(document.getElementById('filmstrip')?.children || [])].find(node => node.dataset.ref === reference.id);
            const control = document.querySelector(`.decision-bar [data-decision="${choice}"]`);
            for (const node of [thumb,control]) if (node) node.dataset.lastDecision = choice;
            const cleanup = () => {
                effect.remove();
                for (const node of [thumb,control]) if (node?.dataset.lastDecision === choice) delete node.dataset.lastDecision;
            };
            if (reduced.matches) { setTimeout(cleanup,700); return; }
            const destinations = {
                keep:'translateY(-8px) scale(.94)',
                inspiration:'translate(30px,-20px) rotate(3deg) scale(.86)',
                maybe:'translateY(-12px) rotate(-2deg)',
                reject:'translateX(-38px) scaleX(.82)'
            };
            const animation = effect.animate([
                {opacity:1,transform:'translate(0,0) scale(1)'},
                {opacity:0,transform:destinations[choice]}
            ],{duration:choice==='maybe'?320:280,easing:'cubic-bezier(.2,.7,.2,1)'});
            activeEffects.add(animation);
            animation.onfinish = animation.oncancel = () => {activeEffects.delete(animation);cleanup();};
        },
        setView(view) {
            if (root.dataset.studioView === view) return;
            root.dataset.studioView = view;
            window.StudioMotion.frame('—');
            requestAnimationFrame(() => enter(document.getElementById('project-header')));
        }
    };
    scheduleScroll();
})();
