document.addEventListener("DOMContentLoaded", () => {
    
    const nav = document.querySelector("nav");

    // On écoute le défilement de la page
    window.addEventListener("scroll", () => {
        if (window.scrollY > 50) {
            // Si on a descendu de plus de 50px, on ajoute la classe "scrolled"
            nav.classList.add("scrolled");
        } else {
            // Sinon, on l'enlève pour redevenir transparent
            nav.classList.remove("scrolled");
        }
    });

});