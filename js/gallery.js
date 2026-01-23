document.addEventListener("DOMContentLoaded", () => {
    // 1. Récupération de l'album via l'URL
    const params = new URLSearchParams(window.location.search);
    const albumId = params.get('id');
    
    // Vérification de sécurité
    if (typeof siteConfig === 'undefined' || !albumId) {
        document.getElementById('album-title').innerText = "Album introuvable";
        return;
    }

    const album = siteConfig.albums.find(a => a.id === albumId);

    if (album) {
        // 2. Mise à jour des textes
        document.title = `${album.title} | Thomas Soleil`;
        document.getElementById('album-title').innerText = album.title;
        document.getElementById('album-meta').innerText = album.date;
        
        // 3. Génération des images
        generateGallery(album);
    } else {
        document.getElementById('album-title').innerText = "Album introuvable";
    }
});

function generateGallery(album) {
    const container = document.getElementById('gallery-container');
    const extension = album.ext || ".webp";

    // On cache le loader texte s'il existe encore dans le HTML
    const loader = document.getElementById('loader-indicator');
    if(loader) loader.style.display = 'none';

    for (let i = 1; i <= album.count; i++) {
        // Création de la div conteneur
        const div = document.createElement('div');
        div.className = 'photo-item';

        // Création de l'image
        const img = document.createElement('img');
        // Construction du chemin : images/dossier/prefixe-numero.webp
        const src = `${album.folder}/${album.prefix}${i}${extension}`;
        
        img.src = src;
        img.alt = `Photo ${i} - ${album.title}`;
        img.loading = "lazy"; // Important pour la performance

        // QUAND L'IMAGE EST CHARGÉE :
        img.onload = () => {
            // On ajoute la classe qui la fait apparaître en douceur (géré par CSS)
            div.classList.add('loaded');
        };

        // GESTION D'ERREUR (Si une photo n'existe pas, on cache le bloc)
        img.onerror = () => {
            div.style.display = 'none';
        };

        // Clic pour Lightbox
        div.onclick = () => openLightbox(src);

        div.appendChild(img);
        container.appendChild(div);
    }
}

// --- LIGHTBOX (Fonctionnement simple) ---
window.openLightbox = function(src) {
    const lb = document.getElementById('lightbox');
    const lbImg = document.getElementById('lightbox-img');
    if(lb && lbImg) {
        lbImg.src = src;
        lb.style.display = 'flex';
    }
}

window.closeLightbox = function() {
    const lb = document.getElementById('lightbox');
    if(lb) lb.style.display = 'none';
}