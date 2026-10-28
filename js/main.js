(() => {
    'use strict';
    // Deter ordinary image saving while keeping clicks, scrolling and zoom available.
    const photoSelector = 'main img, .lightbox img, .photo-link, .art-image-link';
    document.querySelectorAll('main img, .lightbox img, .photo-link, .art-image-link').forEach(photo => {
        photo.setAttribute('draggable', 'false');
    });
    for (const eventName of ['contextmenu', 'dragstart']) {
        document.addEventListener(eventName, event => {
            if (event.target instanceof Element &&
                (event.target.closest(photoSelector) || event.target.matches('.portal-hero'))) event.preventDefault();
        });
    }
    const nav = document.querySelector('.site-nav');
    const toggle = document.querySelector('.menu-toggle');
    const links = document.getElementById('navigation');
    const portal = document.body.classList.contains('portal-page');
    const mobile = matchMedia('(max-width: 760px)');
    const year = document.getElementById('footer-year');
    if (year) year.textContent = new Date().getFullYear();
    const backToTop = document.querySelector('.back-to-top');
    if (backToTop) {
        const updateBackToTop = () => {
            // Keep a focused link available until the visitor moves focus away.
            backToTop.hidden = window.scrollY < 700 && document.activeElement !== backToTop;
        };
        window.addEventListener('scroll', updateBackToTop, { passive: true });
        backToTop.addEventListener('blur', updateBackToTop);
        backToTop.addEventListener('click', () => {
            const content = document.getElementById('contenu');
            content.setAttribute('tabindex', '-1');
            content.focus({ preventScroll: true });
        });
        updateBackToTop();
    }
    if (!nav || !toggle || !links) return;
    document.documentElement.classList.add('js');
    if (document.body.classList.contains('home') || document.querySelector('.life-home')) {
        const updateNav = () => nav.classList.toggle('scrolled', window.scrollY > 50);
        window.addEventListener('scroll', updateNav, { passive: true });
        updateNav();
    }
    function setMenu(open, restore = false) {
        toggle.setAttribute('aria-expanded', String(open));
        toggle.setAttribute('aria-label', open ? 'Fermer le menu' : 'Ouvrir le menu');
        nav.classList.toggle('menu-open', open);
        links.inert = (portal || mobile.matches) && !open;
        if (restore) toggle.focus();
    }
    toggle.addEventListener('click', () => setMenu(toggle.getAttribute('aria-expanded') !== 'true'));
    links.addEventListener('click', e => { if (e.target.closest('a')) setMenu(false); });
    document.addEventListener('keydown', e => {
        if (e.key === 'Escape' && toggle.getAttribute('aria-expanded') === 'true') setMenu(false, true);
    });
    document.addEventListener('click', e => { if (!nav.contains(e.target)) setMenu(false); });
    nav.addEventListener('focusout', () => {
        requestAnimationFrame(() => { if (!nav.contains(document.activeElement)) setMenu(false); });
    });
    mobile.addEventListener('change', () => setMenu(false));
    setMenu(false);
})();
