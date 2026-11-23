// Accueil : un univers à la fois. Défilement automatique, aperçu au survol, flèches du clavier et glissement du doigt.
// Le titre de chaque univers ouvre sa page ; sur téléphone, toucher ailleurs que sur un lien passe à l'univers suivant.
(() => {
    'use strict';
    const stage = document.querySelector('[data-home-stage]');
    if (!stage) return;
    const slides = [...stage.querySelectorAll('.home-slide')];
    const copies = [...stage.querySelectorAll('.home-copy')];
    const chapters = [...stage.querySelectorAll('.home-chapter')];
    const copyBox = stage.querySelector('.home-copies');
    const chapterNav = stage.querySelector('.home-chapters');
    const lessMotion = matchMedia('(prefers-reduced-motion: reduce)');
    let current = Math.max(0, slides.findIndex(slide => slide.classList.contains('is-active')));
    // Le défilement automatique s'arrête dès que le visiteur change lui-même d'univers.
    let stopped = lessMotion.matches;
    let hovering = false;
    let focused = false;
    let visible = true;
    let request = 0;

    // Seule la première photo arrive avec la page. Les autres se chargent juste avant d'être montrées,
    // et sont décodées d'avance : une photo cachée ne l'est pas, l'écran resterait noir un instant.
    // On n'attend jamais plus de 0,4 s une photo lente.
    function prepare(index) {
        const slide = slides[index];
        for (const element of slide.querySelectorAll('[data-srcset], [data-src]')) {
            if (element.dataset.srcset) { element.srcset = element.dataset.srcset; delete element.dataset.srcset; }
            if (element.dataset.src) { element.src = element.dataset.src; delete element.dataset.src; }
        }
        const image = slide.querySelector('img');
        if (!image || !image.decode) return Promise.resolve();
        return Promise.race([image.decode().catch(() => {}), new Promise(resolve => setTimeout(resolve, 400))]);
    }

    function apply(index, followFocus) {
        for (const list of [slides, copies, chapters]) {
            list.forEach((item, k) => item.classList.toggle('is-active', k === index));
        }
        chapters.forEach((chapter, k) => chapter.classList.toggle('is-done', k < index));
        if (followFocus) copies[index].querySelector('.home-go').focus({ preventScroll: true });
        prepare((index + 1) % slides.length);
    }

    function show(index, followFocus = false) {
        current = (index + slides.length) % slides.length;
        const target = current;
        const ticket = ++request;
        prepare(target).then(() => { if (ticket === request) apply(target, followFocus); });
    }

    // La barre de l'univers affiché se remplit ; elle s'arrête au survol, au clavier ou quand la scène n'est plus à l'écran.
    function update() {
        stage.classList.toggle('is-playing', !stopped);
        stage.classList.toggle('is-paused', !stopped && (hovering || focused || !visible || document.hidden));
    }

    function choose(index) {
        const followFocus = copies.some(copy => copy.contains(document.activeElement));
        stopped = true;
        copyBox.setAttribute('aria-live', 'polite');
        update();
        show(index, followFocus);
    }

    chapters.forEach((chapter, k) => {
        chapter.querySelector('.home-chapter-bar > span').addEventListener('animationend', () => {
            if (!stopped && k === current) show(current + 1);
        });
        chapter.addEventListener('mouseenter', () => show(k));
        chapter.addEventListener('focus', () => show(k));
    });
    for (const element of [chapterNav, ...stage.querySelectorAll('.home-go')]) {
        element.addEventListener('mouseenter', () => { hovering = true; update(); });
        element.addEventListener('mouseleave', () => { hovering = false; update(); });
    }
    stage.addEventListener('focusin', () => { focused = true; update(); });
    stage.addEventListener('focusout', () => {
        requestAnimationFrame(() => { focused = stage.contains(document.activeElement); update(); });
    });

    // Flèches gauche et droite du clavier, tant que la scène est à l'écran et qu'on n'écrit pas dans un champ.
    document.addEventListener('keydown', event => {
        if (event.key !== 'ArrowLeft' && event.key !== 'ArrowRight') return;
        if (event.defaultPrevented || event.altKey || event.ctrlKey || event.metaKey || event.shiftKey || !visible) return;
        if (event.target instanceof Element && event.target.closest('input, textarea, select, [contenteditable]')) return;
        event.preventDefault();
        choose(current + (event.key === 'ArrowRight' ? 1 : -1));
    });

    // Glisser le doigt vers la gauche montre l'univers suivant, vers la droite le précédent.
    let touch = null;
    let swiped = false;
    stage.addEventListener('touchstart', event => {
        swiped = false;
        touch = event.touches.length === 1 ? { x: event.touches[0].clientX, y: event.touches[0].clientY } : null;
    }, { passive: true });
    stage.addEventListener('touchend', event => {
        if (!touch) return;
        const end = event.changedTouches[0];
        const dx = end.clientX - touch.x;
        const dy = end.clientY - touch.y;
        touch = null;
        if (Math.abs(dx) >= 40 && Math.abs(dx) > Math.abs(dy) * 1.2) {
            swiped = true;
            choose(current + (dx < 0 ? 1 : -1));
        }
    }, { passive: true });
    stage.addEventListener('touchcancel', () => { touch = null; }, { passive: true });

    // Sur téléphone, toucher la photo ou le texte (pas un lien) passe à l'univers suivant.
    const phone = matchMedia('(max-width: 760px)');
    stage.addEventListener('click', event => {
        if (!phone.matches) return;
        if (swiped) { swiped = false; return; }
        if (event.target instanceof Element && event.target.closest('a, button')) return;
        choose(current + 1);
    });

    if ('IntersectionObserver' in window) {
        new IntersectionObserver(([entry]) => {
            visible = entry.intersectionRatio >= .5;
            update();
        }, { threshold: [0, .5, 1] }).observe(stage);
    }
    document.addEventListener('visibilitychange', update);
    lessMotion.addEventListener('change', () => {
        if (lessMotion.matches) { stopped = true; update(); }
    });
    update();
    window.addEventListener('load', () => prepare((current + 1) % slides.length), { once: true });
})();
