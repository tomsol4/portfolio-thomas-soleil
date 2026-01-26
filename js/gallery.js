document.addEventListener("DOMContentLoaded", () => {
    const params = new URLSearchParams(window.location.search);
    const albumId = params.get('id');
    
    if (typeof siteConfig === 'undefined' || !albumId) return;

    const album = siteConfig.albums.find(a => a.id === albumId);

    if (album) {
        document.title = `${album.title} | Thomas Soleil`;
        document.getElementById('album-title').innerText = album.title;
        document.getElementById('album-meta').innerText = album.date;
        generateStableGallery(album);
    } else {
        document.getElementById('album-title').innerText = "Album introuvable";
    }
});

function generateStableGallery(album) {
    const container = document.getElementById('gallery-container');
    const extension = album.ext || ".webp";
    container.innerHTML = ""; 

    // Détection mobile pour le nombre de colonnes
    const isMobile = window.innerWidth < 768;
    const colCount = isMobile ? 2 : 3;
    const columns = [];

    // Création des colonnes
    for (let c = 0; c < colCount; c++) {
        const colDiv = document.createElement('div');
        colDiv.className = 'masonry-column';
        container.appendChild(colDiv);
        columns.push(colDiv);
    }

    // Distribution des images
    for (let i = 1; i <= album.count; i++) {
        const src = `${album.folder}/${album.prefix}${i}${extension}`;
        const columnIndex = (i - 1) % colCount;
        
        const div = document.createElement('div');
        div.className = 'photo-item';
        
        const img = document.createElement('img');
        img.src = src;
        img.alt = `Photo ${i} - ${album.title}`;
        img.loading = "lazy";

        // Apparition douce
        img.onload = () => { div.classList.add('loaded'); };
        
        // GESTION D'ERREUR : Si l'image n'existe pas, on cache le bloc entier
        img.onerror = () => { div.style.display = 'none'; };
        
        div.onclick = () => openLightbox(src);
        div.appendChild(img);
        columns[columnIndex].appendChild(div);
    }
}

// --- LIGHTBOX ---
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