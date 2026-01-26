document.addEventListener("DOMContentLoaded", () => {
    
    // --- GESTION DU SCROLL NAV ---
    const nav = document.querySelector("nav");
    window.addEventListener("scroll", () => {
        if (window.scrollY > 50) nav.classList.add("scrolled");
        else nav.classList.remove("scrolled");
    });

    // --- GESTION DU MENU MOBILE ---
    const burger = document.querySelector('.burger');
    const navLinks = document.querySelector('.nav-links');
    const links = document.querySelectorAll('.nav-links a');

    if(burger) {
        burger.addEventListener('click', () => {
            // Basculer le menu
            navLinks.classList.toggle('nav-active');
            
            // Animation du burger (optionnel, transforme les barres en croix)
            burger.classList.toggle('toggle');
        });
        
        // Fermer le menu quand on clique sur un lien
        links.forEach(link => {
            link.addEventListener('click', () => {
                navLinks.classList.remove('nav-active');
                burger.classList.remove('toggle');
            });
        });
    }
});