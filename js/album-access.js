(() => {
    'use strict';
    const data = document.getElementById('album-encrypted-data');
    if (!data) return;
    const payload = JSON.parse(data.textContent);
    const scripts = {masonry:data.dataset.masonry, gallery:data.dataset.gallery};
    const dialog = document.getElementById('album-access-dialog');
    const form = document.getElementById('album-access-form');
    const field = document.getElementById('album-password');
    const status = document.getElementById('album-access-status');
    const submit = form.querySelector('[type="submit"]');
    const opener = document.getElementById('album-access-open');
    let opening = false;
    const decode = value => Uint8Array.from(atob(value), character => character.charCodeAt(0));
    const encode = bytes => btoa(String.fromCharCode(...new Uint8Array(bytes)));
    // Clés des albums déjà ouverts dans cet onglet (ici ou depuis une liste, par album-lock.js) : tant que l'onglet
    // reste ouvert, recharger la page ou revenir sur l'album ne redemande pas le mot de passe. Fermer l'onglet les oublie.
    const STORE = 'album-access-keys';
    function remembered() {
        try { return JSON.parse(sessionStorage.getItem(STORE)) || {}; } catch (_) { return {}; }
    }
    function remember(bits) {
        try {
            const keys = remembered();
            if (bits) keys[payload.id] = {salt:payload.salt, key:encode(bits)};
            else delete keys[payload.id];
            sessionStorage.setItem(STORE, JSON.stringify(keys));
        } catch (_) {}
    }
    const known = remembered()[payload.id];
    function openDialog() {
        document.documentElement.classList.remove('album-opening');
        if (!dialog.open) dialog.showModal();
        field.focus();
    }
    dialog.removeAttribute('open');
    opener.addEventListener('click', openDialog);
    form.querySelector('.album-access-cancel').addEventListener('click', () => dialog.close());
    dialog.addEventListener('close', () => opener.focus({ preventScroll: true }));
    if (location.protocol === 'file:') {
        // Un fichier ouvert directement depuis le disque ne peut pas lire les images chiffrées.
        status.textContent = 'Cet album ne s’ouvre pas depuis un fichier de l’ordinateur. Lancez « apercu.bat » à la racine du projet, ou ouvrez le site en ligne.';
        openDialog();
        return;
    }
    if (!window.crypto?.subtle) {
        status.textContent = 'Ouvrez cette page en HTTPS avec un navigateur récent pour accéder à l’album.';
        openDialog();
        return;
    }
    submit.disabled = false;
    function loadScript(name) {
        return new Promise((resolve, reject) => {
            const script = document.createElement('script');
            script.src = scripts[name] || `../js/${name}.js`;
            script.onload = resolve;
            script.onerror = reject;
            document.head.appendChild(script);
        });
    }
    // Les images de l'album sont publiées chiffrées (.bin) : elles sont déchiffrées ici, à la demande.
    function secureImages(key) {
        const associated = new TextEncoder().encode(`album-image:${payload.id}`);
        const thumbnails = new Map();
        const viewer = new Map();
        async function decrypt(url) {
            const response = await fetch(url);
            if (!response.ok) throw new Error('Image indisponible');
            const bytes = await response.arrayBuffer();
            const image = await crypto.subtle.decrypt({name:'AES-GCM', iv:bytes.slice(0, 12), additionalData:associated},
                key, bytes.slice(12));
            return URL.createObjectURL(new Blob([image], {type:'image/webp'}));
        }
        function choose(srcset, fallback, width) {
            const candidates = (srcset || '').split(',').map(candidate => candidate.trim().split(/\s+/))
                .filter(candidate => candidate[0])
                .map(([url, size]) => ({url, width:parseInt(size, 10) || 0}))
                .sort((first, second) => first.width - second.width);
            if (!candidates.length) return fallback;
            return (candidates.find(candidate => candidate.width >= width) || candidates[candidates.length - 1]).url;
        }
        function resolve(srcset, fallback, width, store, limit) {
            const url = choose(srcset, fallback, width);
            if (!url || !/\.bin$/.test(url)) return Promise.resolve(url);
            if (store.has(url)) {
                const cached = store.get(url);
                store.delete(url);
                store.set(url, cached);
                return cached;
            }
            const pending = decrypt(url);
            store.set(url, pending);
            pending.catch(() => store.delete(url));
            if (limit && store.size > limit) {
                const [oldest, released] = store.entries().next().value;
                store.delete(oldest);
                released.then(address => URL.revokeObjectURL(address), () => {});
            }
            return pending;
        }
        function load(image) {
            const width = Math.ceil((image.clientWidth || 480) * Math.min(devicePixelRatio || 1, 2));
            resolve(image.dataset.secureSrcset, image.dataset.secureSrc, width, thumbnails, 0)
                .then(url => { image.src = url; }, () => {});
        }
        const pending = document.querySelectorAll('img[data-secure-src]');
        if (typeof IntersectionObserver === 'function') {
            const observer = new IntersectionObserver(entries => entries.forEach(entry => {
                if (!entry.isIntersecting) return;
                observer.unobserve(entry.target);
                load(entry.target);
            }), {rootMargin:'800px 0px'});
            pending.forEach(image => observer.observe(image));
        } else {
            pending.forEach(load);
        }
        window.albumSecureImages = {resolve:(srcset, fallback, width) => resolve(srcset, fallback, width, viewer, 12)};
    }
    async function decryptPage(key) {
        const plaintext = await crypto.subtle.decrypt({name:'AES-GCM', iv:decode(payload.iv),
            additionalData:new TextEncoder().encode(`album:${payload.id}`)}, key, decode(payload.ciphertext));
        return new TextDecoder().decode(plaintext);
    }
    const pageKey = bits => crypto.subtle.importKey('raw', bits, 'AES-GCM', false, ['decrypt']);
    form.addEventListener('submit', async event => {
        event.preventDefault();
        if (opening || !form.reportValidity()) return;
        opening = true;
        submit.disabled = true;
        submit.textContent = 'Ouverture…';
        form.setAttribute('aria-busy', 'true');
        status.textContent = '';
        let markup, bits;
        try {
            const material = await crypto.subtle.importKey('raw', new TextEncoder().encode(field.value), 'PBKDF2', false, ['deriveBits']);
            bits = await crypto.subtle.deriveBits({name:'PBKDF2', salt:decode(payload.salt),
                iterations:payload.iterations, hash:'SHA-256'}, material, 256);
            markup = await decryptPage(await pageKey(bits));
        } catch (_) {
            status.textContent = 'Mot de passe incorrect. Réessayez.';
            field.setAttribute('aria-invalid', 'true');
            field.focus();
            field.select();
            opening = false;
            submit.disabled = false;
            submit.textContent = 'Ouvrir l’album';
            form.removeAttribute('aria-busy');
            return;
        }
        field.value = '';
        remember(bits);
        await showAlbum(markup);
    });
    async function showAlbum(markup) {
        const template = document.createElement('template');
        template.innerHTML = markup;
        dialog.close();
        const content = template.content.getElementById('contenu');
        const imageKey = content.dataset.imageKey;
        content.removeAttribute('data-image-key');
        document.getElementById('contenu').replaceWith(template.content);
        document.documentElement.classList.remove('album-opening');
        window.scrollTo(0, 0);
        if (imageKey) secureImages(await crypto.subtle.importKey('raw', decode(imageKey), 'AES-GCM', false, ['decrypt']));
        document.dispatchEvent(new CustomEvent('album:unlocked'));
        const title = document.querySelector('main h1');
        title.setAttribute('tabindex', '-1');
        title.focus({ preventScroll: true });
        const grid = document.querySelector('.photo-grid');
        grid.inert = true;
        try {
            await loadScript('masonry');
            await loadScript('gallery');
        } catch (_) {
            const note = document.createElement('p');
            note.className = 'album-access-note';
            note.textContent = 'La visionneuse n’a pas pu être chargée. Les photographies restent accessibles en cliquant dessus.';
            document.querySelector('.photo-grid').before(note);
        } finally {
            grid.inert = false;
            document.getElementById('contenu').dataset.albumReady = 'true';
        }
    }
    field.addEventListener('input', () => field.removeAttribute('aria-invalid'));
    if (known && known.salt === payload.salt) {
        // Album déjà ouvert dans cet onglet : il s'ouvre sans redemander le mot de passe.
        opening = true;
        Promise.resolve().then(() => pageKey(decode(known.key))).then(decryptPage).then(showAlbum, () => {
            remember(null);
            opening = false;
            openDialog();
        });
    } else {
        if (known) remember(null);  // clé d'une ancienne version de l'album
        openDialog();
    }
})();
