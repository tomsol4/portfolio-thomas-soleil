(() => {
    'use strict';
    const gallery = document.querySelector('.photo-grid');
    const dialog = document.getElementById('lightbox');
    if (!gallery || !dialog || typeof dialog.showModal !== 'function') return;
    const photos = [...gallery.querySelectorAll('.photo-link')];
    const image = dialog.querySelector('img');
    const counter = document.getElementById('photo-counter');
    const status = document.getElementById('photo-status');
    const original = document.getElementById('photo-original');
    const close = dialog.querySelector('.lightbox-close');
    let position = 0, request = 0;
    let opener = null, touch = null;
    let previousOverflow = '';
    function show(index) {
        position = (index + photos.length) % photos.length;
        const link = photos[position];
        const id = ++request;
        counter.textContent = `${position + 1} / ${photos.length}`;
        status.textContent = 'Chargement de la photo…';
        image.hidden = true;
        original.href = link.href;
        image.alt = link.querySelector('img').alt;
        image.onload = () => {
            if (id !== request) return;
            image.hidden = false;
            status.textContent = '';
            for (const offset of [-1, 1]) {
                const next = new Image();
                next.src = photos[(position + offset + photos.length) % photos.length].href;
            }
        };
        image.onerror = () => {
            if (id === request) status.textContent = 'Cette photo ne peut pas être chargée. Essayez la suivante ou ouvrez le fichier.';
        };
        image.src = link.href;
    }
    gallery.addEventListener('click', e => {
        const link = e.target.closest('.photo-link');
        if (!link || e.ctrlKey || e.metaKey || e.shiftKey || e.altKey || e.button !== 0) return;
        e.preventDefault();
        opener = link;
        previousOverflow = document.body.style.overflow;
        dialog.showModal();
        document.body.style.overflow = 'hidden';
        show(photos.indexOf(link));
        close.focus();
    });
    close.addEventListener('click', () => dialog.close());
    dialog.querySelector('.lightbox-prev').addEventListener('click', () => show(position - 1));
    dialog.querySelector('.lightbox-next').addEventListener('click', () => show(position + 1));
    dialog.addEventListener('keydown', e => {
        if (e.key === 'Tab') {
            const controls = [...dialog.querySelectorAll('button, a[href]')];
            const first = controls[0];
            const last = controls[controls.length - 1];
            if (e.shiftKey && document.activeElement === first) {
                e.preventDefault();
                last.focus();
            } else if (!e.shiftKey && document.activeElement === last) {
                e.preventDefault();
                first.focus();
            }
        }
        if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
            e.preventDefault();
            show(position + (e.key === 'ArrowRight' ? 1 : -1));
        }
    });
    dialog.addEventListener('click', e => { if (e.target === dialog) dialog.close(); });
    dialog.addEventListener('close', () => {
        document.body.style.overflow = previousOverflow;
        if (opener) opener.focus({ preventScroll: true });
    });
    image.addEventListener('touchstart', e => {
        touch = e.touches.length === 1 ? { x: e.touches[0].clientX, y: e.touches[0].clientY } : null;
    }, { passive: true });
    image.addEventListener('touchend', e => {
        if (!touch || !e.changedTouches.length) return;
        const dx = e.changedTouches[0].clientX - touch.x;
        const dy = e.changedTouches[0].clientY - touch.y;
        if (Math.abs(dx) > 60 && Math.abs(dx) > Math.abs(dy) * 1.5) show(position + (dx < 0 ? 1 : -1));
        touch = null;
    }, { passive: true });
})();
