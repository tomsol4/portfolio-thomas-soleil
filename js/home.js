document.addEventListener("DOMContentLoaded", () => {
    const container = document.getElementById('albums-list');

    if (!container || typeof siteConfig === 'undefined') return;

    siteConfig.albums.forEach((album, index) => {
        const card = document.createElement('a');
        card.href = `galerie.html?id=${album.id}`;
        card.className = 'album-card';
        
// OPTIMISATION VITESSE (SEO) : 
        // On charge immédiatement les 3 premiers (visibles à l'écran),
        // et on retarde le chargement des autres pour accélérer l'affichage mobile.
        const loadingMode = index < 3 ? "eager" : "lazy";

        card.innerHTML = `
            <img src="${album.cover}" alt="${album.title}" loading="${loadingMode}">
            <div class="album-info">
                <h3>${album.title}</h3>
                <span>${album.date}</span>
            </div>
        `;
        container.appendChild(card);
    });
});