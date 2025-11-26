/* =========================================
   SCRIPT JAVASCRIPT - PORTFOLIO THOMAS SOLEIL
   ========================================= */

   document.addEventListener('DOMContentLoaded', () => {
    
    // --- 1. EFFET D'APPARITION AU SCROLL (SCROLL REVEAL) ---
    // On cible tous les éléments qu'on veut animer
// Ajoutez .horizontal-section
    const elementsToReveal = document.querySelectorAll('.gallery-item, .masonry-item, .horizontal-section, .section-title, .about-text, .pricing-card');    // On configure l'observateur (l'oeil du navigateur)
    const observerOptions = {
        threshold: 0.2 // L'animation se lance quand 10% de l'objet est visible
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

/* =========================================
   CARROUSEL TURBO (AUTO + ACCÉLÉRATION)
   ========================================= */

const scrollContainer = document.getElementById('auto-scroll-container');

// Vitesse normale de croisière
const baseSpeed = 1; 

// Vitesse actuelle (qui va changer)
let currentSpeed = baseSpeed;
let animationId;

function autoScrollLoop() {
    if (scrollContainer) {
        // On avance selon la vitesse actuelle
        scrollContainer.scrollLeft += currentSpeed;

        // --- BOUCLE INFINIE (Gère les deux sens) ---
        
        // Si on arrive à la fin (vers la droite) -> Retour au début
        if (scrollContainer.scrollLeft >= (scrollContainer.scrollWidth / 2)) {
            scrollContainer.scrollLeft = 0;
        }
        // Si on arrive au début (vers la gauche en reculant) -> Saut à la fin
        else if (scrollContainer.scrollLeft <= 0) {
            scrollContainer.scrollLeft = (scrollContainer.scrollWidth / 2);
        }
    }
    // On relance la boucle
    animationId = requestAnimationFrame(autoScrollLoop);
}

// Lancer le défilement
if (scrollContainer) {
    animationId = requestAnimationFrame(autoScrollLoop);

    // --- GESTION DU TACTILE (MOBILE) ---
    // Sur mobile, on arrête tout quand on touche pour laisser le doigt gérer
    scrollContainer.addEventListener('touchstart', () => { currentSpeed = 0; });
    
    // Quand on lâche le doigt, on remet la vitesse normale
    scrollContainer.addEventListener('touchend', () => { 
        setTimeout(() => { currentSpeed = baseSpeed; }, 500);
    });
}

// --- FONCTIONS D'ACCÉLÉRATION (POUR LES BOUTONS) ---

// Appelée quand on appuie sur la flèche
function boostSpeed(speed) {
    // On change la vitesse instantanément (ex: 15 ou -15)
    currentSpeed = speed;
}

// Appelée quand on relâche la souris
function resetSpeed() {
    // On remet la vitesse douce normale
    currentSpeed = baseSpeed;
}