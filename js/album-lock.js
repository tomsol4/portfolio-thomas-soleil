(() => {
    'use strict';
    // Sur une liste de reportages, un album protégé demande son mot de passe au clic : on n'arrive sur la page
    // de l'album qu'avec le bon. Le mot de passe est vérifié ici, dans le navigateur, sur le contenu chiffré de la page ;
    // la clé de la page est ensuite retenue par l'onglet (album-access.js la relit) : tant que l'onglet reste ouvert,
    // l'album s'ouvre sans redemander le mot de passe. Fermer l'onglet l'oublie.
    const STORE = 'album-access-keys';
    const links = document.querySelectorAll('a[data-album-locked]');
    const dialog = document.getElementById('album-access-dialog');
    // Sans ces outils, le lien mène à la page de l'album, qui demande elle-même le mot de passe.
    if (!links.length || !dialog || typeof dialog.showModal !== 'function' || !window.crypto?.subtle
        || location.protocol === 'file:') return;
    const form = document.getElementById('album-access-form');
    const field = document.getElementById('album-password');
    const status = document.getElementById('album-access-status');
    const title = document.getElementById('album-access-title');
    const submit = form.querySelector('[type="submit"]');
    const pages = new Map();
    let link = null;
    let opening = false;
    const decode = value => Uint8Array.from(atob(value), character => character.charCodeAt(0));
    const encode = bytes => btoa(String.fromCharCode(...new Uint8Array(bytes)));

    function remembered() {
        try { return JSON.parse(sessionStorage.getItem(STORE)) || {}; } catch (_) { return {}; }
    }
    function store(keys) {
        try { sessionStorage.setItem(STORE, JSON.stringify(keys)); } catch (_) {
            // Sans stockage pour l'onglet, la page de l'album redemandera le mot de passe.
        }
    }

    // Le contenu chiffré de l'album se charge dès que la fenêtre s'ouvre, pendant que le visiteur tape.
    function encryptedPage(href) {
        if (!pages.has(href)) {
            const pending = fetch(href).then(response => {
                if (!response.ok) throw new Error('Album indisponible');
                return response.text();
            }).then(html => {
                const data = new DOMParser().parseFromString(html, 'text/html').getElementById('album-encrypted-data');
                if (!data) throw new Error('Album indisponible');
                return JSON.parse(data.textContent);
            });
            pages.set(href, pending);
            pending.catch(() => pages.delete(href));
        }
        return pages.get(href);
    }
    function ready() {
        opening = false;
        submit.disabled = false;
        submit.textContent = 'Ouvrir l’album';
        form.removeAttribute('aria-busy');
    }
    function fail(message) {
        status.textContent = message;
        ready();
        field.focus();
        field.select();
    }
    function open(target) {
        link = target;
        title.textContent = target.dataset.albumLocked;
        status.textContent = '';
        field.value = '';
        field.removeAttribute('aria-invalid');
        ready();
        encryptedPage(target.href).catch(() => {});
        dialog.showModal();
        field.focus();
    }
    // Album déjà ouvert dans cet onglet : on y va directement, si sa clé vaut toujours (elle change quand l'album est refait).
    async function openRemembered(target) {
        try {
            const payload = await encryptedPage(target.href);
            const known = remembered()[payload.id];
            if (known && known.salt === payload.salt) return location.assign(target.href);
            if (known) {
                const keys = remembered();
                delete keys[payload.id];
                store(keys);
            }
        } catch (_) {}
        open(target);
    }
    links.forEach(target => {
        target.setAttribute('aria-haspopup', 'dialog');
        target.addEventListener('click', event => {
            // Ctrl, Cmd, Maj ou la molette : nouvel onglet ou nouvelle fenêtre, sur la page de l'album qui demande le mot de passe.
            if (event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
            event.preventDefault();
            if (Object.keys(remembered()).length) openRemembered(target);
            else open(target);
        });
    });
    form.querySelector('.album-access-cancel').addEventListener('click', () => dialog.close());
    dialog.addEventListener('close', () => link?.focus({ preventScroll: true }));
    field.addEventListener('input', () => field.removeAttribute('aria-invalid'));
    form.addEventListener('submit', async event => {
        event.preventDefault();
        if (opening || !form.reportValidity()) return;
        opening = true;
        submit.disabled = true;
        submit.textContent = 'Ouverture…';
        form.setAttribute('aria-busy', 'true');
        status.textContent = '';
        let payload;
        try {
            payload = await encryptedPage(link.href);
        } catch (_) {
            fail('L’album n’a pas pu être chargé. Vérifiez votre connexion, puis réessayez.');
            return;
        }
        let bits;
        try {
            const encoder = new TextEncoder();
            const material = await crypto.subtle.importKey('raw', encoder.encode(field.value), 'PBKDF2', false, ['deriveBits']);
            bits = await crypto.subtle.deriveBits({name:'PBKDF2', salt:decode(payload.salt),
                iterations:payload.iterations, hash:'SHA-256'}, material, 256);
            const key = await crypto.subtle.importKey('raw', bits, 'AES-GCM', false, ['decrypt']);
            await crypto.subtle.decrypt({name:'AES-GCM', iv:decode(payload.iv),
                additionalData:encoder.encode(`album:${payload.id}`)}, key, decode(payload.ciphertext));
        } catch (_) {
            field.setAttribute('aria-invalid', 'true');
            fail('Mot de passe incorrect. Réessayez.');
            return;
        }
        field.value = '';
        const keys = remembered();
        keys[payload.id] = {salt:payload.salt, key:encode(bits)};
        store(keys);
        location.assign(link.href);
    });
    // Retour sur la liste avec le bouton Précédent : la fenêtre se referme ; l'onglet garde les albums déjà ouverts.
    addEventListener('pageshow', event => {
        if (!event.persisted) return;
        ready();
        if (dialog.open) dialog.close();
    });
})();
