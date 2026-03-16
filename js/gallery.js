let currentAlbum = null;
let photosLoadedCount = 0;
let isLoading = false;
let currentIndex = 1;
const BATCH_SIZE = 20;

document.addEventListener("DOMContentLoaded", () => {
    const params = new URLSearchParams(window.location.search);
    const albumId = params.get('id');
    
    // Si pas de config ou pas d'ID, on arrête tout
    if (typeof siteConfig === 'undefined' || !albumId) return;

    currentAlbum = siteConfig.albums.find(a => a.id === albumId);

    if (currentAlbum) {
        document.title = `${currentAlbum.title} | Thomas Soleil`;
        
        const titleEl = document.getElementById('album-title');
        if(titleEl) titleEl.innerText = currentAlbum.title;

        initGalleryStructure();
        loadNextBatch();
        window.addEventListener('scroll', handleScroll);
    }
});

// Recharge la page si on redimensionne la fenêtre (pour recalculer les colonnes)
let resizeTimer;
window.addEventListener('resize', () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => {
        location.reload(); 
    }, 200);
});

function initGalleryStructure() {
    const container = document.getElementById('gallery-container');
    if(!container) return;

    container.innerHTML = ''; 
    const colCount = window.innerWidth < 768 ? 2 : 3;
    
    for (let c = 0; c < colCount; c++) {
        const colDiv = document.createElement('div');
        colDiv.className = 'masonry-column';
        container.appendChild(colDiv);
    }
}

function loadNextBatch() {
    if (!currentAlbum || isLoading) return;
    isLoading = true;
    
    const columns = Array.from(document.querySelectorAll('.masonry-column'));
    if(columns.length === 0) return;

    // Sécurité pour l'extension et le compteur
    const extension = currentAlbum.ext || ".webp"; 
    const start = photosLoadedCount + 1;
    let end = Math.min(start + BATCH_SIZE - 1, currentAlbum.count);

    if (start > currentAlbum.count) {
        isLoading = false;
        return;
    }

    for (let i = start; i <= end; i++) {
        const src = `${currentAlbum.folder}/${currentAlbum.prefix}${i}${extension}`;
        
        let shortestColumn = columns.reduce((p, c) => p.offsetHeight < c.offsetHeight ? p : c);

        const div = document.createElement('div');
        div.className = 'photo-item';
        
        const img = document.createElement('img');
        img.alt = `Photo ${currentAlbum.title} ${i}`;
        img.loading = "lazy";

        // CORRECTION MAJEURE ICI : On définit l'action AVANT de donner la source
        img.onload = () => { 
            div.classList.add('loaded'); 
        };
        
        // Si l'image a une erreur (ex: n'existe pas), on cache le bloc
        img.onerror = () => {
            div.style.display = 'none';
        };

        img.src = src; // On lance le chargement à la fin
        
        div.onclick = () => openLightbox(i);
        div.appendChild(img);
        shortestColumn.appendChild(div);
    }
    
    photosLoadedCount = end;
    setTimeout(() => { isLoading = false; }, 50); 
}

// --- LIGHTBOX ---
window.openLightbox = function(index) {
    currentIndex = index;
    const lb = document.getElementById('lightbox');
    const lbImg = document.getElementById('lightbox-img');
    
    if(lb && lbImg && currentAlbum) {
        updateLightboxImage();
        lb.style.display = 'flex';
        document.body.style.overflow = 'hidden';
    }
}

window.changePhoto = function(direction) {
    if (!currentAlbum) return;
    currentIndex += direction;
    if (currentIndex > currentAlbum.count) currentIndex = 1;
    if (currentIndex < 1) currentIndex = currentAlbum.count;
    updateLightboxImage();
}

function updateLightboxImage() {
    const lbImg = document.getElementById('lightbox-img');
    const ext = currentAlbum.ext || ".webp";
    lbImg.src = `${currentAlbum.folder}/${currentAlbum.prefix}${currentIndex}${ext}`;
}

window.closeLightbox = function() {
    document.getElementById('lightbox').style.display = 'none';
    document.body.style.overflow = 'auto';
}

document.addEventListener('keydown', (e) => {
    if (document.getElementById('lightbox').style.display === 'flex') {
        if (e.key === "ArrowLeft") changePhoto(-1);
        if (e.key === "ArrowRight") changePhoto(1);
        if (e.key === "Escape") closeLightbox();
    }
});

function handleScroll() {
    if (isLoading) return;
    const { scrollTop, scrollHeight, clientHeight } = document.documentElement;
    if (scrollTop + clientHeight >= scrollHeight - 600) {
        if (photosLoadedCount < currentAlbum.count) {
            loadNextBatch();
        }
    }
}