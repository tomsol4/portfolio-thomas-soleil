document.addEventListener("DOMContentLoaded", () => {
    const container = document.getElementById('albums-list');

    // Vérification de sécurité
    if (!container || typeof siteConfig === 'undefined') return;

    // On boucle sur chaque album défini dans config.js
    siteConfig.albums.forEach(album => {
        const card = document.createElement('a');
        card.href = `galerie.html?id=${album.id}`; // Lien vers la page unique
        card.className = 'album-card';
        
        card.innerHTML = `
            <img src="${album.cover}" alt="${album.title}" loading="lazy">
            <div class="album-info">
                <h3>${album.title}</h3>
                <span>${album.date}</span>
            </div>
        `;
        container.appendChild(card);
    });
});