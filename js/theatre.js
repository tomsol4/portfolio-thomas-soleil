(() => {
    'use strict';
    const stage = document.querySelector('[data-theatre]');
    if (!stage) return;
    const motion = matchMedia('(prefers-reduced-motion: reduce)');
    const finePointer = matchMedia('(hover: hover) and (pointer: fine)');
    const replay = stage.querySelector('.theatre-replay');
    const entry = stage.querySelector('.theatre-entry');
    const enter = stage.querySelector('.theatre-enter');
    const content = stage.querySelector('.concert-stage-content');
    const curtains = [...stage.querySelectorAll('.theatre-curtain')];
    const glow = stage.querySelector('.theatre-glow');
    const reveals = [...document.querySelectorAll('.concert-reportages .collection-link, .concert-invitation')];
    let curtainAnimations = [];
    let sequence = 0;
    let pointerFrame = 0;
    let observer;
    const entranceKey = 'concerts.theatre.entered';
    function entranceRemembered() {
        try {
            if (sessionStorage.getItem(entranceKey) === 'yes') return true;
        } catch (_) { /* History still preserves the entrance when storage is unavailable. */ }
        return Boolean(history.state?.concertTheatreEntered);
    }
    function rememberEntrance() {
        try { sessionStorage.setItem(entranceKey, 'yes'); } catch (_) { /* Private storage can be unavailable. */ }
        try { history.replaceState({ ...history.state, concertTheatreEntered: true }, ''); } catch (_) { /* Keep the entrance usable. */ }
    }
    let entered = Boolean(location.hash || window.scrollY > 50 || entranceRemembered());

    function settleCurtains() {
        sequence += 1;
        curtainAnimations.forEach(animation => animation.cancel());
        curtainAnimations = [];
        stage.classList.remove('theatre-is-moving');
        stage.classList.toggle('is-open', entered);
        stage.classList.toggle('theatre-closed', !entered);
        entry.hidden = entered;
        content.inert = !entered;
        replay.disabled = false;
    }

    function openCurtains(replaying = false) {
        const moveFocus = !replaying && entry.contains(document.activeElement);
        entered = true;
        rememberEntrance();
        settleCurtains();
        const finish = () => {
            settleCurtains();
            if (moveFocus) stage.querySelector('.concert-scroll').focus({ preventScroll: true });
        };
        if (motion.matches || !curtains.every(curtain => typeof curtain.animate === 'function')) {
            finish();
            return;
        }
        const currentSequence = sequence;
        stage.classList.remove('is-open');
        stage.classList.add('theatre-is-moving');
        content.inert = true;
        replay.disabled = true;
        curtainAnimations = curtains.map(curtain => {
            const gathered = parseFloat(getComputedStyle(curtain).getPropertyValue('--curtain-gather'));
            const left = curtain.classList.contains('theatre-curtain--left');
            const side = left ? 1 : -1;
            const rows = [0, 8, 18, 30, 43, 56, 70, 84, 100];
            const edge = values => {
                const points = [[0, 0], ...values.map((x, i) => [x, rows[i]]), [0, 100]];
                return `polygon(${points.map(([x, y]) => `${left ? x : 100 - x}% ${y}%`).join(',')})`;
            };
            const closed = edge(rows.map(() => 100));
            const restingEdge = [100, 97, 91, 82, 76, 74, 77, 85, 100];
            const fabricLag = [-36, -29, -21, -12, -5, 0, 2, 1, 0];
            const resting = getComputedStyle(curtain).clipPath;
            const pose = (gather, sway = 0) => `scaleX(${gather}) skewX(${side * sway}deg)`;
            // Sample one continuous curve instead of stopping and restarting at
            // each pose. Gathering stays monotonic; the lighter upper fabric leads.
            const sweep = Array.from({ length: 49 }, (_, index) => {
                const time = index / 48;
                const progress = time ** 3 * (time * (time * 6 - 15) + 10);
                const wave = Math.sin(Math.PI * progress);
                const gather = 1 - (1 - gathered) * progress;
                const sway = Math.sin(2 * Math.PI * progress) * wave * .7;
                return {
                    transform: pose(gather, sway),
                    clipPath: edge(restingEdge.map((x, row) =>
                        100 + (x - 100) * progress + fabricLag[row] * wave)),
                    offset: time
                };
            });
            const frames = replaying ? [
                { transform: pose(gathered), clipPath: resting, offset: 0, easing: 'ease-in-out' },
                { transform: pose(1), clipPath: closed, offset: .3 },
                ...sweep.map(frame => ({ ...frame, offset: .4 + frame.offset * .6 }))
            ] : sweep;
            return curtain.animate(frames, {
                duration: replaying ? 3600 : 2400,
                easing: 'linear'
            });
        });
        Promise.all(curtainAnimations.map(animation => animation.finished)).then(() => {
            if (sequence === currentSequence) finish();
        }).catch(() => {
            // Unexpected cancellation must not leave the scene's controls inert.
            if (sequence === currentSequence) finish();
        });
    }

    function configureMotion() {
        settleCurtains();
        cancelAnimationFrame(pointerFrame);
        observer?.disconnect();
        stage.classList.toggle('theatre-ready', !motion.matches);
        replay.hidden = motion.matches;
        replay.disabled = false;
        glow.style.removeProperty('--glow-x');
        glow.style.removeProperty('--glow-y');
        reveals.forEach(item => item.classList.remove('theatre-reveal', 'is-visible'));
        if (motion.matches) return;
        if ('IntersectionObserver' in window) {
            observer = new IntersectionObserver(entries => {
                entries.forEach(entry => {
                    if (!entry.isIntersecting) return;
                    entry.target.classList.add('is-visible');
                    observer.unobserve(entry.target);
                });
            }, { threshold: 0.08 });
            reveals.forEach(item => {
                item.classList.add('theatre-reveal');
                observer.observe(item);
            });
        }
    }

    enter.addEventListener('click', () => openCurtains());
    replay.addEventListener('click', () => openCurtains(true));
    stage.addEventListener('pointermove', event => {
        if (motion.matches || !finePointer.matches) return;
        cancelAnimationFrame(pointerFrame);
        pointerFrame = requestAnimationFrame(() => {
            const bounds = stage.getBoundingClientRect();
            glow.style.setProperty('--glow-x', `${(event.clientX - bounds.left - bounds.width * .5) * .35}px`);
            glow.style.setProperty('--glow-y', `${(event.clientY - bounds.top - bounds.height * .24) * .35}px`);
        });
    }, { passive: true });
    stage.addEventListener('pointerleave', () => {
        cancelAnimationFrame(pointerFrame);
        glow.style.removeProperty('--glow-x');
        glow.style.removeProperty('--glow-y');
    });
    document.addEventListener('focusin', event => {
        event.target.closest('.theatre-reveal')?.classList.add('is-visible');
    });
    motion.addEventListener('change', configureMotion);
    window.addEventListener('hashchange', () => {
        if (location.hash && !entered) {
            entered = true;
            settleCurtains();
        }
    });
    window.addEventListener('pagehide', settleCurtains);
    window.addEventListener('pageshow', () => {
        if (entranceRemembered()) entered = true;
        settleCurtains();
    });
    window.addEventListener('resize', () => {
        // Finish before breakpoint changes alter the curtain's resting position.
        if (curtainAnimations.length) settleCurtains();
    }, { passive: true });
    configureMotion();
})();
