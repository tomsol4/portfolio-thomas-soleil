/* =========================================
   CARROUSEL TURBO (AUTO + ACCÉLÉRATION)
   ========================================= */

const scrollContainer = document.getElementById('auto-scroll-container');

// VITESSE INTELLIGENTE :
// Sur mobile (< 768px), on met 0.4 pour que ce soit doux.
// Sur PC, on met 1 pour que ça avance bien.
const baseSpeed = window.innerWidth < 768 ? 0.4 : 1; 

// Vitesse actuelle (qui va changer)
let currentSpeed = baseSpeed;
let animationId;

function autoScrollLoop() {
    if (scrollContainer) {
        // On avance selon la vitesse actuelle
        scrollContainer.scrollLeft += currentSpeed;

        // --- BOUCLE INFINIE ---
        // Si on arrive à la fin (vers la droite) -> Retour au début
        if (scrollContainer.scrollLeft >= (scrollContainer.scrollWidth / 2)) {
            scrollContainer.scrollLeft = 0;
        }
        // Si on arrive au début (vers la gauche) -> Saut à la fin
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
    
    // Quand on lâche le doigt, on remet la vitesse douce
    scrollContainer.addEventListener('touchend', () => { 
        setTimeout(() => { currentSpeed = baseSpeed; }, 500);
    });
}

// --- FONCTIONS D'ACCÉLÉRATION (POUR LES BOUTONS PC) ---

function boostSpeed(speed) {
    currentSpeed = speed;
}

function resetSpeed() {
    currentSpeed = baseSpeed;
}   