(() => {
    'use strict';
    const data = document.getElementById('album-encrypted-data');
    if (!data) return;
    const payload = JSON.parse(data.textContent);
    const dialog = document.getElementById('album-access-dialog');
    const form = document.getElementById('album-access-form');
    const field = document.getElementById('album-password');
    const status = document.getElementById('album-access-status');
    const submit = form.querySelector('[type="submit"]');
    const opener = document.getElementById('album-access-open');
    let opening = false;
    const decode = value => Uint8Array.from(atob(value), character => character.charCodeAt(0));
    function openPrompt() {
        if (!dialog.open) dialog.showModal();
        field.focus();
    }
    dialog.removeAttribute('open');
    opener.addEventListener('click', openPrompt);
    form.querySelector('.album-access-cancel').addEventListener('click', () => dialog.close());
    dialog.addEventListener('close', () => opener.focus({ preventScroll: true }));
    if (!window.crypto?.subtle) {
        status.textContent = 'Ouvrez cette page en HTTPS avec un navigateur récent pour accéder à l’album.';
        openPrompt();
        return;
    }
    submit.disabled = false;
    function loadScript(name) {
        return new Promise((resolve, reject) => {
            const script = document.createElement('script');
            script.src = `../js/${name}.js`;
            script.onload = resolve;
            script.onerror = reject;
            document.head.appendChild(script);
        });
    }
    form.addEventListener('submit', async event => {
        event.preventDefault();
        if (opening || !form.reportValidity()) return;
        opening = true;
        submit.disabled = true;
        submit.textContent = 'Ouverture…';
        form.setAttribute('aria-busy', 'true');
        status.textContent = '';
        let markup;
        try {
            const encoder = new TextEncoder();
            const material = await crypto.subtle.importKey('raw', encoder.encode(field.value), 'PBKDF2', false, ['deriveKey']);
            const key = await crypto.subtle.deriveKey({name:'PBKDF2', salt:decode(payload.salt),
                iterations:payload.iterations, hash:'SHA-256'}, material, {name:'AES-GCM', length:256}, false, ['decrypt']);
            const plaintext = await crypto.subtle.decrypt({name:'AES-GCM', iv:decode(payload.iv),
                additionalData:encoder.encode(`album:${payload.id}`)}, key, decode(payload.ciphertext));
            markup = new TextDecoder().decode(plaintext);
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
        const template = document.createElement('template');
        template.innerHTML = markup;
        dialog.close();
        document.getElementById('contenu').replaceWith(template.content);
        document.dispatchEvent(new CustomEvent('album:unlocked'));
        const title = document.querySelector('main h1');
        title.setAttribute('tabindex', '-1');
        title.focus({ preventScroll: true });
        try {
            await loadScript('masonry');
            await loadScript('gallery');
        } catch (_) {
            // Native image links still work if an enhancement cannot be loaded.
            const note = document.createElement('p');
            note.className = 'album-access-note';
            note.textContent = 'La visionneuse n’a pas pu être chargée. Les photographies restent accessibles en cliquant dessus.';
            document.querySelector('.photo-grid').before(note);
        }
    });
    field.addEventListener('input', () => field.removeAttribute('aria-invalid'));
    openPrompt();
})();
