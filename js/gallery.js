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

    // 1. CRÉATION DES COLONNES (Structure fixe)
    const isMobile = window.innerWidth < 768;
    const colCount = isMobile ? 2 : 3;
    const columns = [];

    for (let c = 0; c < colCount; c++) {
        const colDiv = document.createElement('div');
        colDiv.className = 'masonry-column';
        container.appendChild(colDiv);
        columns.push(colDiv);
    }

    // 2. DISTRIBUTION IMMÉDIATE (1, 2, 3, 1, 2, 3...)
    // On n'attend pas le chargement de l'image pour lui assigner sa place.
    // Cela empêche tout mouvement ou saut visuel.
    for (let i = 1; i <= album.count; i++) {
        const src = `${album.folder}/${album.prefix}${i}${extension}`;
        
        // Calcul mathématique simple pour choisir la colonne : 0, 1, 2, 0, 1, 2...
        // Image 1 -> Col 1 / Image 2 -> Col 2 / Image 3 -> Col 3 / Image 4 -> Col 1
        const columnIndex = (i - 1) % colCount;
        
        const div = document.createElement('div');
        div.className = 'photo-item';
        
        const img = document.createElement('img');
        img.src = src;
        img.alt = `Photo ${i}`;
        img.loading = "lazy";

        // Juste l'apparition en fondu quand c'est prêt
        img.onload = () => { div.classList.add('loaded'); };
        
        div.onclick = () => openLightbox(src);
        div.appendChild(img);

        // On ajoute directement dans la bonne colonne
        columns[columnIndex].appendChild(div);
    }
}

// --- LIGHTBOX ---
window.openLightbox = function(src) {
    const lb = document.getElementById('lightbox');
    const lbImg = document.getElementById('lightbox-img');
    if(lb && lbImg) { lbImg.src = src; lb.style.display = 'flex'; }
}

window.closeLightbox = function() {
    const lb = document.getElementById('lightbox');
    if(lb) lb.style.display = 'none';
}