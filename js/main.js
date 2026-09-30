(() => {
    'use strict';
    const nav = document.querySelector('.site-nav');
    const toggle = document.querySelector('.menu-toggle');
    const links = document.getElementById('navigation');
    const mobile = matchMedia('(max-width: 760px)');
    const year = document.getElementById('footer-year');
    if (year) year.textContent = new Date().getFullYear();
    if (!nav || !toggle || !links) return;
    document.documentElement.classList.add('js');
    if (document.body.classList.contains('home')) {
        const updateNav = () => nav.classList.toggle('scrolled', window.scrollY > 50);
        window.addEventListener('scroll', updateNav, { passive: true });
        updateNav();
    }
    function setMenu(open, restore = false) {
        toggle.setAttribute('aria-expanded', String(open));
        toggle.setAttribute('aria-label', open ? 'Fermer le menu' : 'Ouvrir le menu');
        nav.classList.toggle('menu-open', open);
        links.inert = mobile.matches && !open;
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
