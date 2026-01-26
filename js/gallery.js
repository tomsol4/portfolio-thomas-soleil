document.addEventListener("DOMContentLoaded", () => {
    // 1. Récupération de l'ID de l'album dans l'URL
    const params = new URLSearchParams(window.location.search);
    const albumId = params.get('id');
    
    // Sécurité : Si pas de config ou pas d'ID, on arrête tout
    if (typeof siteConfig === 'undefined' || !albumId) return;

    // 2. On cherche l'album correspondant dans la config
    const album = siteConfig.albums.find(a => a.id === albumId);

    if (album) {
        // Mise à jour du titre de la page et des textes
        document.title = `${album.title} | Thomas Soleil`;
        document.getElementById('album-title').innerText = album.title;
        const meta = document.getElementById('album-meta');
        if(meta) meta.innerText = album.date;
        
        // Lancement de la galerie
        generateStableGallery(album);
    } else {
        document.getElementById('album-title').innerText = "Album introuvable";
    }
});

function generateStableGallery(album) {
    const container = document.getElementById('gallery-container');
    const extension = album.ext || ".webp";
    
    // On vide le conteneur pour éviter les doublons
    container.innerHTML = ""; 

    // 3. Détection Mobile vs PC pour les colonnes
    const isMobile = window.innerWidth < 768;
    const colCount = isMobile ? 2 : 3;
    const columns = [];

    // Création des colonnes (divs vides qui vont recevoir les images)
    for (let c = 0; c < colCount; c++) {
        const colDiv = document.createElement('div');
        colDiv.className = 'masonry-column';
        container.appendChild(colDiv);
        columns.push(colDiv);
    }

    // 4. Boucle pour créer chaque image
    for (let i = 1; i <= album.count; i++) {
        // Construction du chemin de l'image
        const src = `${album.folder}/${album.prefix}${i}${extension}`;
        
        // Calcul pour savoir dans quelle colonne mettre l'image (0, 1, 2...)
        const columnIndex = (i - 1) % colCount;
        
        const div = document.createElement('div');
        div.className = 'photo-item';
        
        const img = document.createElement('img');
        img.src = src;
        img.alt = `Photo ${i} - ${album.title}`;

        // --- OPTIMISATION VITESSE ---
        // Les 6 premières images chargent en mode "Eager" (Immédiat)
        // Les suivantes en "Lazy" (Différé)
        if (i <= 6) {
            img.loading = "eager"; 
        } else {
            img.loading = "lazy";
        }

        // --- GESTION D'AFFICHAGE ---
        // Quand l'image est prête, on ajoute la classe .loaded pour le fondu
        img.onload = () => { div.classList.add('loaded'); };
        
        // Si l'image est déjà dans le cache (rechargement de page), on force l'affichage
        if (img.complete) { div.classList.add('loaded'); }

        // Si l'image n'existe pas (erreur 404), on cache le bloc pour ne pas avoir de trou
        img.onerror = () => { div.style.display = 'none'; };
        
        // Clic pour ouvrir la Lightbox
        div.onclick = () => openLightbox(src);
        
        div.appendChild(img);
        
        // On place l'image dans la bonne colonne
        columns[columnIndex].appendChild(div);
    }
}

// --- FONCTIONS LIGHTBOX ---
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