let currentAlbum = null;
let photosLoadedCount = 0;
let isLoading = false;
const BATCH_SIZE = 24; 

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
    container.innerHTML = '<div class="col"></div><div class="col"></div><div class="col"></div>';
    if(window.innerWidth < 768) {
        container.innerHTML = '<div class="col"></div><div class="col"></div>';
    }
}

function loadNextBatch() {
    if (isLoading || !currentAlbum) return;
    isLoading = true;

    const container = document.getElementById('gallery-container');
    const columns = container.getElementsByClassName('col');
    
    const start = photosLoadedCount + 1;
    const end = Math.min(start + BATCH_SIZE - 1, currentAlbum.count);

    for (let i = start; i <= end; i++) {
        const div = document.createElement('div');
        div.className = 'gallery-item';
        
        // Utilisation de la version SMALL pour la grille
        const thumbSrc = `${currentAlbum.folder}/${currentAlbum.prefix}${i}-small.webp`;
        const fullSrc = `${currentAlbum.folder}/${currentAlbum.prefix}${i}.webp`;
        
        const img = document.createElement('img');
        img.src = thumbSrc;
        img.alt = `${currentAlbum.title} - Photo ${i}`;
        img.loading = "lazy";

        img.onload = () => div.classList.add('loaded');
        div.onclick = () => openLightbox(fullSrc);
        
        div.appendChild(img);
        
        // Trouver la colonne la plus courte
        let shortest = columns[0];
        for(let col of columns) {
            if(col.offsetHeight < shortest.offsetHeight) shortest = col;
        }
        shortest.appendChild(div);
    }

    photosLoadedCount = end;
    isLoading = false;
}

function handleScroll() {
    if ((window.innerHeight + window.scrollY) >= document.body.offsetHeight - 1000) {
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