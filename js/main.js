document.addEventListener("DOMContentLoaded", () => {
    
    // 1. INJECTION DU HEADER ET FOOTER
    injectCommonElements();

    // 2. GESTION DU SCROLL NAV (Ton ancien code)
    const nav = document.querySelector("nav");
    window.addEventListener("scroll", () => {
        if (window.scrollY > 50) nav.classList.add("scrolled");
        else nav.classList.remove("scrolled");
    });

    // 3. GESTION DU MENU MOBILE (Ton ancien code, adapté aux éléments dynamiques)
    const burger = document.querySelector('.burger');
    const navLinks = document.querySelector('.nav-links');
    const links = document.querySelectorAll('.nav-links a');

    if(burger) {
        burger.addEventListener('click', () => {
            navLinks.classList.toggle('nav-active');
            burger.classList.toggle('toggle');
        });
        
        links.forEach(link => {
            link.addEventListener('click', () => {
                navLinks.classList.remove('nav-active');
                burger.classList.remove('toggle');
            });
        });
    }
});

// --- FONCTION POUR GÉNÉRER LE HTML COMMUN ---
function injectCommonElements() {
    const nav = document.querySelector('nav');
    const footer = document.querySelector('footer');

    // A. Le HTML du Menu
    if (nav) {
        nav.innerHTML = `
            <a href="index.html" class="logo">T.S</a>
            <div class="burger"><div></div><div></div><div></div></div>
            <div class="nav-links">
                <a href="index.html" data-link="albums">Albums</a>
                <a href="a-propos.html" data-link="a-propos">À Propos</a>
                <a href="contact.html" data-link="contact">Contact</a>
            </div>
        `;
        highlightActiveLink();
    }

    // B. Le HTML du Footer (AVEC INSTAGRAM)
    if (footer) {
        // On récupère l'année actuelle automatiquement
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

// --- FONCTION POUR ACTIVER LE LIEN COURANT ---
function highlightActiveLink() {
    // Récupère le nom du fichier actuel (ex: "contact.html")
    let path = window.location.pathname.split("/").pop();
    
    // Si on est à la racine (tsoleil.fr/), path est vide, donc on force index.html
    if (path === "") path = "index.html";

    // Cas spécial : Si on est sur "galerie.html", on veut activer "Albums" (index.html)
    if (path.includes("galerie.html")) path = "index.html";

    const activeLink = document.querySelector(`.nav-links a[href="${path}"]`);
    if (activeLink) {
        activeLink.classList.add("active");
    }
}