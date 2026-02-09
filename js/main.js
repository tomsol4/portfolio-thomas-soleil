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
// Dans main.js
function injectCommonElements() {
    const navHTML = `
        <a href="index.html" class="logo">T.S</a>
        <div class="burger"><div></div><div></div><div></div></div>
        <div class="nav-links">
            <a href="index.html">Albums</a>
            <a href="a-propos.html">À Propos</a>
            <a href="contact.html">Contact</a>
        </div>
    `;
    document.querySelector('nav').innerHTML = navHTML;
    
    // Code pour mettre la classe .active sur le bon lien
    const currentPath = window.location.pathname.split('/').pop() || 'index.html';
    document.querySelectorAll('.nav-links a').forEach(link => {
        if (link.getAttribute('href') === currentPath) link.classList.add('active');
    });
}
// Appeler cette fonction au début du DOMContentLoaded