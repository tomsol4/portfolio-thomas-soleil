let currentAlbum = null;
let photosLoadedCount = 0;
let isLoading = false;
const BATCH_SIZE = 15; // Réduit pour plus de fluidité au départ

document.addEventListener("DOMContentLoaded", () => {
    const params = new URLSearchParams(window.location.search);
    const albumId = params.get('id');
    
    if (typeof siteConfig === 'undefined' || !albumId) return;

    currentAlbum = siteConfig.albums.find(a => a.id === albumId);

    if (currentAlbum) {
        document.title = `${currentAlbum.title} | Thomas Soleil`;
        document.getElementById('album-title').innerText = currentAlbum.title;
        
        const meta = document.getElementById('album-meta');
        if(meta) meta.innerText = currentAlbum.date;
        
        initGalleryStructure();
        loadNextBatch();
        window.addEventListener('scroll', handleScroll);
    }
});

function initGalleryStructure() {
    const container = document.getElementById('gallery-container');
    // On définit le nombre de colonnes selon l'écran
    const colCount = window.innerWidth < 768 ? 2 : 3;
    container.innerHTML = '';
    for (let i = 0; i < colCount; i++) {
        const col = document.createElement('div');
        col.className = 'col';
        container.appendChild(col);
    }
}

function loadNextBatch() {
    if (isLoading || !currentAlbum || photosLoadedCount >= currentAlbum.count) return;
    isLoading = true;

    const columns = document.querySelectorAll('.col');
    const start = photosLoadedCount + 1;
    const end = Math.min(start + BATCH_SIZE - 1, currentAlbum.count);

    for (let i = start; i <= end; i++) {
        const div = document.createElement('div');
        div.className = 'gallery-item';
        
        const thumbSrc = `${currentAlbum.folder}/${currentAlbum.prefix}${i}-small.webp`;
        const fullSrc = `${currentAlbum.folder}/${currentAlbum.prefix}${i}.webp`;
        
        const img = document.createElement('img');
        img.src = thumbSrc;
        img.alt = `${currentAlbum.title} - Photographie Thomas Soleil`;
        img.loading = "lazy";

        img.onload = () => {
            div.classList.add('loaded');
        };

        div.onclick = () => openLightbox(fullSrc);
        div.appendChild(img);
        
        // Distribution intelligente dans la colonne la plus courte
        const shortestCol = [...columns].reduce((prev, curr) => 
            prev.offsetHeight <= curr.offsetHeight ? prev : curr
        );
        shortestCol.appendChild(div);
    }

    photosLoadedCount = end;
    isLoading = false;
}

function handleScroll() {
    if ((window.innerHeight + window.scrollY) >= document.body.offsetHeight - 800) {
        loadNextBatch();
    }
}

window.openLightbox = function(src) {
    const lb = document.getElementById('lightbox');
    const lbImg = document.getElementById('lightbox-img');
    lbImg.src = src;
    lb.style.display = 'flex';
    document.body.style.overflow = 'hidden';
};

window.closeLightbox = function() {
    const lb = document.getElementById('lightbox');
    lb.style.display = 'none';
    document.body.style.overflow = 'auto';
};