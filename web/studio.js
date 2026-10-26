/* Shared presentation only: no network, storage or business-state writes. */
'use strict';
(() => {
    const reduced = matchMedia('(prefers-reduced-motion: reduce)');
    const finePointer = matchMedia('(hover: hover) and (pointer: fine)');
    const root = document.documentElement;
    const scenes = [...document.querySelectorAll('[data-studio-scene]')];
    const effects = new WeakMap();
    const activeEffects = new Set();
    const progress = document.createElement('div');
    progress.className = 'studio-progress';
    progress.setAttribute('aria-hidden', 'true');
    document.body.append(progress);
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
            });
        });
        scene.addEventListener('pointerleave', () => {
            cancelAnimationFrame(pointerFrame);
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
        setView(view) {
            if (root.dataset.studioView === view) return;
            root.dataset.studioView = view;
            requestAnimationFrame(() => enter(document.getElementById('project-header')));
        }
    };
    scheduleScroll();
})();
