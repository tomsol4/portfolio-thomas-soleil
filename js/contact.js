(() => {
    'use strict';
    const form = document.getElementById('contact-form');
    if (!form) return;
    const project = document.getElementById('project');
    const requested = new URLSearchParams(location.search).get('projet');
    if (project?.options && [...project.options].some(option => option.value === requested)) project.value = requested;
    // Reset clears the message while retaining the project selected by the incoming link.
    if (project?.options) for (const option of project.options) option.defaultSelected = option.selected;
    const offer = document.getElementById('wedding-offer');
    const offerGroup = document.getElementById('wedding-offer-group');
    if (offer && offerGroup) {
        const requestedOffer = new URLSearchParams(location.search).get('offre');
        if (requested === 'mariage' && [...offer.options].some(option => option.value === requestedOffer)) offer.value = requestedOffer;
        for (const option of offer.options) option.defaultSelected = option.selected;
        const updateOffer = () => {
            const wedding = project.value === 'mariage';
            offerGroup.hidden = !wedding;
            offer.disabled = !wedding;
        };
        project.addEventListener('change', updateOffer);
        form.addEventListener('reset', () => requestAnimationFrame(updateOffer));
        updateOffer();
    }
    const status = document.getElementById('form-status');
    const submit = form.querySelector('[type="submit"]');
    const submitLabel = submit.textContent;
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
        delete status.dataset.state;
        const payload = new FormData(form);
        const submittedValues = JSON.stringify([...payload]);
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 20000);
        try {
            const response = await fetch(form.action, {
                method: 'POST', body: payload, headers: { Accept: 'application/json' },
                signal: controller.signal
            });
            if (!response.ok) throw new Error('submission-failed');
            const edited = JSON.stringify([...new FormData(form)]) !== submittedValues;
            if (!edited) form.reset();
            status.textContent = form.dataset.successMessage || 'Merci, votre message a bien été envoyé. Je vous réponds personnellement pour échanger sur votre projet.';
            if (edited) status.textContent += ' Vos modifications récentes sont conservées dans le formulaire et n’ont pas été envoyées.';
            status.dataset.state = 'success';
        } catch (error) {
            status.textContent = error.name === 'AbortError'
                ? 'La confirmation prend trop de temps. Votre message a peut-être été envoyé. Vous pouvez me contacter sur Instagram.'
                : 'L’envoi n’a pas pu être confirmé. Votre texte est conservé : réessayez ou contactez-moi sur Instagram.';
            status.dataset.state = 'error';
        } finally {
            clearTimeout(timeout);
            sending = false;
            submit.disabled = false;
            submit.textContent = submitLabel;
            form.removeAttribute('aria-busy');
            if (!form.contains(document.activeElement) || document.activeElement === submit) status.focus();
        }
    });
})();
