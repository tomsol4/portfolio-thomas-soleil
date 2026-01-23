document.addEventListener("DOMContentLoaded", () => {
    const container = document.getElementById('albums-list');

    // Sécurité
    if (!container || typeof siteConfig === 'undefined') return;

    siteConfig.albums.forEach(album => {
        const card = document.createElement('a');
        card.href = `galerie.html?id=${album.id}`;
        card.className = 'album-card';
        
        // Structure HTML pour correspondre à ton style "Capture 1"
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