document.addEventListener("DOMContentLoaded", () => {
    
    // 1. INJECTION DU HEADER, FOOTER ET META THEME
    injectCommonElements();
    injectMetaThemeColor(); // Force la barre d'adresse en noir sur mobile

    // 2. GESTION DU SCROLL NAV
    const nav = document.querySelector("nav");
    window.addEventListener("scroll", () => {
        if (window.scrollY > 50) nav.classList.add("scrolled");
        else nav.classList.remove("scrolled");
    });

    // 3. GESTION DU MENU MOBILE (Burger)
    initMobileMenu();
});

/* --- FONCTION : MENU MOBILE --- */
function initMobileMenu() {
    const burger = document.querySelector('.burger');
    const navLinks = document.querySelector('.nav-links');
    const nav = document.querySelector('nav');
    const links = document.querySelectorAll('.nav-links a');

    if (burger) {
        burger.addEventListener('click', () => {
            // Bascule l'animation du burger et l'affichage du menu
            navLinks.classList.toggle('nav-active');
            burger.classList.toggle('toggle');
            
            // FIX MOBILE : Force le fond noir quand le menu est ouvert
            nav.classList.toggle('menu-open');
        });
        
        // Ferme le menu quand on clique sur un lien
        links.forEach(link => {
            link.addEventListener('click', () => {
                navLinks.classList.remove('nav-active');
                burger.classList.remove('toggle');
                nav.classList.remove('menu-open');
            });
        });
    }
}

/* --- FONCTION : GÉNÉRATION DU HTML COMMUN --- */
function injectCommonElements() {
    const nav = document.querySelector('nav');
    const footer = document.querySelector('footer');

    // A. Injection du Menu
    if (nav) {
        nav.innerHTML = `
            <a href="index.html" class="logo">T.S</a>
            <div class="burger"><div></div><div></div><div></div></div>
            <div class="nav-links">
                <a href="index.html">Albums</a>
                <a href="a-propos.html">À Propos</a>
                <a href="contact.html">Contact</a>
            </div>
        `;
        highlightActiveLink(); // Souligne la page en cours
    }

    // B. Injection du Footer (Avec Instagram & Année auto)
    if (footer) {
        const year = new Date().getFullYear();
        footer.innerHTML = `
            <p>&copy; ${year} Thomas Soleil. Tous droits réservés.</p>
            <p style="margin-top: 10px;">
                <a href="mentions.html">Mentions Légales</a> | 
                <a href="contact.html">Contact</a> |
                <a href="https://www.instagram.com/tomsol_photo/" target="_blank">Instagram</a>
            </p>
        `;
    }
}

/* --- FONCTION : SOULIGNER LE LIEN ACTIF --- */
function highlightActiveLink() {
    let path = window.location.pathname.split("/").pop();
    if (path === "") path = "index.html";
    
    // Si on est dans une galerie, on active "Albums"
    if (path.includes("galerie.html")) path = "index.html";

    const activeLink = document.querySelector(`.nav-links a[href="${path}"]`);
    if (activeLink) activeLink.classList.add("active");
}

/* --- FONCTION : FORCER LA COULEUR DU NAVIGATEUR MOBILE --- */
function injectMetaThemeColor() {
    let meta = document.querySelector("meta[name='theme-color']");
    if (!meta) {
        meta = document.createElement('meta');
        meta.name = "theme-color";
        document.head.appendChild(meta);
    }
    meta.content = "#1c1c1c"; // Noir profond
}