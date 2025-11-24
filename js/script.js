/* =========================================
   SCRIPT JAVASCRIPT - PORTFOLIO THOMAS SOLEIL
   ========================================= */

   document.addEventListener('DOMContentLoaded', () => {
    
    // --- 1. EFFET D'APPARITION AU SCROLL (SCROLL REVEAL) ---
    // On cible tous les éléments qu'on veut animer
        const elementsToReveal = document.querySelectorAll('.gallery-item, .masonry-item, .section-title, .about-text, .pricing-card');
    // On configure l'observateur (l'oeil du navigateur)
    const observerOptions = {
        threshold: 0.3 // L'animation se lance quand 10% de l'objet est visible
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                // Ajoute la classe 'visible' quand l'élément entre dans l'écran
                entry.target.classList.add('visible');
                // Arrête d'observer une fois animé (pour ne pas le rejouer)
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);

    // On active l'observation sur chaque élément
    elementsToReveal.forEach(el => {
        el.classList.add('reveal-hidden'); // On les cache au départ
        observer.observe(el);
    });


    // --- 2. MENU NAVIGATION DYNAMIQUE ---
    const nav = document.querySelector('.main-nav');
    
    window.addEventListener('scroll', () => {
        if (window.scrollY > 200) {
            nav.classList.add('scrolled');
        } else {
            nav.classList.remove('scrolled');
        }
    });


    // --- 3. PROTECTION CLIC DROIT (Optionnel) ---
    // Empêche le clic droit sur les images pour limiter le vol
    document.addEventListener('contextmenu', function (e) {
        if (e.target.tagName === 'IMG') {
            e.preventDefault();
        }
    });

});