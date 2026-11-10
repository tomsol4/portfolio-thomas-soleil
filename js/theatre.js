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
    let introAnimation;
    let sequence = 0;
    let pointerFrame = 0;
    let observer;
    const entranceKey = 'concerts.theatre.entered';

    function entranceRemembered() {
        try {
            if (sessionStorage.getItem(entranceKey) === 'yes') return true;
        } catch (_) {}
        return Boolean(history.state?.concertTheatreEntered);
    }

    function rememberEntrance() {
        try { sessionStorage.setItem(entranceKey, 'yes'); } catch (_) {}
        try { history.replaceState({ ...history.state, concertTheatreEntered: true }, ''); } catch (_) {}
    }

    let entered = Boolean(location.hash || window.scrollY > 50 || entranceRemembered() || motion.matches);

    function settleCurtains() {
        sequence += 1;
        const moveFocus = entered && entry.contains(document.activeElement);
        curtainAnimations.forEach(animation => animation.cancel());
        introAnimation?.cancel();
        curtainAnimations = [];
        introAnimation = undefined;
        stage.classList.remove('theatre-is-moving', 'theatre-opening');
        stage.classList.toggle('is-open', entered);
        stage.classList.toggle('theatre-closed', !entered);
        entry.hidden = entered;
        content.inert = !entered;
        replay.disabled = false;
        if (moveFocus) stage.querySelector('.concert-scroll').focus({ preventScroll: true });
    }

    function openCurtains(replaying = false) {
        entered = true;
        rememberEntrance();
        settleCurtains();
        if (motion.matches || !curtains.every(curtain => typeof curtain.animate === 'function')) return;

        const currentSequence = sequence;
        const duration = replaying ? 3200 : 2300;
        const delay = replaying ? 0 : 260;
        stage.classList.remove('is-open');
        stage.classList.add('theatre-is-moving');
        if (!replaying) {
            stage.classList.add('theatre-opening');
            entry.hidden = false;
        }
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
            const fabricLag = [-28, -24, -18, -10, -4, 0, 2, 1, 0];
            const resting = getComputedStyle(curtain).clipPath;
            const pose = (gather, sway = 0) => `scaleX(${gather}) skewX(${side * sway}deg)`;
            const sweep = Array.from({ length: 61 }, (_, index) => {
                const time = index / 60;
                const progress = time ** 3 * (time * (time * 6 - 15) + 10);
                const wave = Math.sin(Math.PI * progress);
                return {
                    transform: pose(1 - (1 - gathered) * progress,
                        Math.sin(2 * Math.PI * progress) * wave * .45),
                    clipPath: edge(restingEdge.map((x, row) =>
                        100 + (x - 100) * progress + fabricLag[row] * wave)),
                    offset: time
                };
            });
            const frames = replaying ? [
                { transform: pose(gathered), clipPath: resting, offset: 0, easing: 'cubic-bezier(.45,0,.25,1)' },
                { transform: pose(1), clipPath: closed, offset: .28 },
                ...sweep.map(frame => ({ ...frame, offset: .38 + frame.offset * .62 }))
            ] : sweep;
            return curtain.animate(frames, { duration, delay, easing: 'linear', fill: 'both' });
        });

        if (!replaying) {
            introAnimation = stage.querySelector('.theatre-intro').animate([
                { opacity: 1, transform: 'translateY(0)' },
                { opacity: 0, transform: 'translateY(-16px)' }
            ], { duration: 500, delay: 360, easing: 'cubic-bezier(.22,1,.36,1)', fill: 'both' });
        }

        Promise.all(curtainAnimations.map(animation => animation.finished)).then(() => {
            if (sequence === currentSequence) settleCurtains();
        }).catch(() => {
            if (sequence === currentSequence) settleCurtains();
        });
    }

    function resetLight() {
        cancelAnimationFrame(pointerFrame);
        pointerFrame = 0;
        glow.style.removeProperty('--glow-x');
        glow.style.removeProperty('--glow-y');
    }

    function configureMotion() {
        if (motion.matches) entered = true;
        settleCurtains();
        resetLight();
        observer?.disconnect();
        stage.classList.toggle('theatre-ready', !motion.matches);
        replay.hidden = motion.matches;
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

    enter.addEventListener('click', settleCurtains);
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
    stage.addEventListener('pointerleave', resetLight);
    document.addEventListener('focusin', event => {
        event.target.closest('.theatre-reveal')?.classList.add('is-visible');
    });
    document.addEventListener('visibilitychange', () => {
        if (document.hidden) {
            settleCurtains();
            resetLight();
        }
    });
    motion.addEventListener('change', configureMotion);
    finePointer.addEventListener('change', resetLight);
    window.addEventListener('hashchange', () => {
        if (location.hash) {
            entered = true;
            settleCurtains();
        }
    });
    window.addEventListener('pagehide', () => {
        settleCurtains();
        resetLight();
    });
    window.addEventListener('pageshow', event => {
        if (event.persisted) {
            entered = true;
            settleCurtains();
        }
    });
    window.addEventListener('resize', () => {
        if (curtainAnimations.length) settleCurtains();
        resetLight();
    }, { passive: true });
    window.addEventListener('scroll', () => {
        if (curtainAnimations.length && stage.getBoundingClientRect().bottom < innerHeight * .5) {
            settleCurtains();
        }
    }, { passive: true });
    configureMotion();
    if (!entered) openCurtains();
})();
