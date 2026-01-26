document.addEventListener("DOMContentLoaded", () => {
    const container = document.getElementById('albums-list');

    if (!container || typeof siteConfig === 'undefined') return;

    siteConfig.albums.forEach((album, index) => {
        const card = document.createElement('a');
        card.href = `galerie.html?id=${album.id}`;
        card.className = 'album-card';
        
        // OPTIMISATION : Pas de lazy loading pour les albums sur l'accueil
        // (il y en a peu, on veut qu'ils soient là tout de suite)
        const loadingMode = "eager"; 

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