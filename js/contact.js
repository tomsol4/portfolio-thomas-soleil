(() => {
    'use strict';
    const form = document.getElementById('contact-form');
    if (!form) return;
    const project = document.getElementById('project');
    const requested = new URLSearchParams(location.search).get('projet');
    if ([...project.options].some(option => option.value === requested)) project.value = requested;
    const status = document.getElementById('form-status');
    const submit = form.querySelector('[type="submit"]');
    let sending = false;
    form.addEventListener('submit', async e => {
        e.preventDefault();
        if (sending || !form.reportValidity()) return;
        if (form.elements.namedItem('_gotcha').value) return;
        sending = true;
        submit.disabled = true;
        form.setAttribute('aria-busy', 'true');
        submit.textContent = 'Envoi en cours…';
        status.textContent = '';
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 20000);
        try {
            const response = await fetch(form.action, {
                method: 'POST', body: new FormData(form), headers: { Accept: 'application/json' },
                signal: controller.signal
            });
            if (!response.ok) throw new Error('submission-failed');
            form.reset();
            status.textContent = 'Merci, votre message a bien été envoyé. Je vous réponds sous 24 h.';
            status.dataset.state = 'success';
        } catch (error) {
            status.textContent = error.name === 'AbortError'
                ? 'La confirmation prend trop de temps. Votre message a peut-être été envoyé. Vous pouvez me contacter directement par email ci-dessous.'
                : 'L’envoi n’a pas pu être confirmé. Votre texte est conservé : réessayez ou contactez-moi par email ci-dessous.';
            status.dataset.state = 'error';
        } finally {
            clearTimeout(timeout);
            sending = false;
            submit.disabled = false;
            submit.textContent = 'Envoyer ma demande';
            form.removeAttribute('aria-busy');
            status.focus();
        }
    });
})();
