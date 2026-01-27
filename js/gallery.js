let currentAlbum = null;
let photosLoadedCount = 0;
let isLoading = false;
let currentIndex = 1; // On suit la photo active
const BATCH_SIZE = 40; 

document.addEventListener("DOMContentLoaded", () => {
    const params = new URLSearchParams(window.location.search);
    const albumId = params.get('id');
    if (typeof siteConfig === 'undefined' || !albumId) return;

    currentAlbum = siteConfig.albums.find(a => a.id === albumId);

    if (currentAlbum) {
        document.title = `${currentAlbum.title} | Thomas Soleil`;
        document.getElementById('album-title').innerText = currentAlbum.title;
        initGalleryStructure();
        loadNextBatch();
        window.addEventListener('scroll', handleScroll);
    }
});

function initGalleryStructure() {
    const container = document.getElementById('gallery-container');
    const colCount = window.innerWidth < 768 ? 2 : 3;
    for (let c = 0; c < colCount; c++) {
        const colDiv = document.createElement('div');
        colDiv.className = 'masonry-column';
        container.appendChild(colDiv);
    }
}

function loadNextBatch() {
    if (!currentAlbum) return;
    isLoading = true;
    const columns = Array.from(document.querySelectorAll('.masonry-column'));
    const extension = currentAlbum.ext || ".webp";
    
    const start = photosLoadedCount + 1;
    let end = Math.min(start + BATCH_SIZE - 1, currentAlbum.count);

    for (let i = start; i <= end; i++) {
        const src = `${currentAlbum.folder}/${currentAlbum.prefix}${i}${extension}`;
        let shortestColumn = columns.reduce((p, c) => p.offsetHeight < c.offsetHeight ? p : c);

        const div = document.createElement('div');
        div.className = 'photo-item';
        const img = document.createElement('img');
        img.src = src;
        img.loading = i <= 6 ? "eager" : "lazy";

        img.onload = () => { div.classList.add('loaded'); };
        
        // IMPORTANT : On passe l'index "i" à la lightbox
        div.onclick = () => openLightbox(i);
        
        div.appendChild(img);
        shortestColumn.appendChild(div);
    }
    photosLoadedCount = end;
    setTimeout(() => { isLoading = false; }, 100);
}

// --- SYSTÈME DE LIGHTBOX ---
window.openLightbox = function(index) {
    currentIndex = index;
    const lb = document.getElementById('lightbox');
    const lbImg = document.getElementById('lightbox-img');
    if(lb && lbImg && currentAlbum) {
        const ext = currentAlbum.ext || ".webp";
        lbImg.src = `${currentAlbum.folder}/${currentAlbum.prefix}${currentIndex}${ext}`;
        lb.style.display = 'flex';
        document.body.style.overflow = 'hidden';
    }
}

window.changePhoto = function(direction) {
    if (!currentAlbum) return;
    currentIndex += direction;
    if (currentIndex > currentAlbum.count) currentIndex = 1;
    if (currentIndex < 1) currentIndex = currentAlbum.count;
    
    const lbImg = document.getElementById('lightbox-img');
    lbImg.src = `${currentAlbum.folder}/${currentAlbum.prefix}${currentIndex}${currentAlbum.ext}`;
}

window.closeLightbox = function() {
    document.getElementById('lightbox').style.display = 'none';
    document.body.style.overflow = 'auto';
}

// Navigation clavier
document.addEventListener('keydown', (e) => {
    if (document.getElementById('lightbox').style.display === 'flex') {
        if (e.key === "ArrowLeft") changePhoto(-1);
        if (e.key === "ArrowRight") changePhoto(1);
        if (e.key === "Escape") closeLightbox();
    }
});

// Ajoute ceci à la fin de ton fichier gallery.js

function handleScroll() {
    // Si on est déjà en train de charger, on ne fait rien
    if (isLoading) return;

    // Calcul de la position de scroll
    // On vérifie si on est à moins de 800px du bas de la page
    const { scrollTop, scrollHeight, clientHeight } = document.documentElement;
    
    if (scrollTop + clientHeight >= scrollHeight - 800) {
        // On vérifie s'il reste des photos à charger
        if (photosLoadedCount < currentAlbum.count) {
            loadNextBatch();
        }
    }
}