let currentAlbum = null;
let photosLoadedCount = 0;
let isLoading = false;
let currentPhotoPosition = 0;
let loadedPhotos = [];
const BATCH_SIZE = 30;

document.addEventListener("DOMContentLoaded", () => {
    const params = new URLSearchParams(window.location.search);
    const albumId = params.get('id');
    
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

function initGalleryStructure() {
    const container = document.getElementById('gallery-container');
    if(!container) return;

    container.innerHTML = ''; 
    const colCount = window.innerWidth < 768 ? 2 : 4;
    
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

    const extension = currentAlbum.ext || ".webp"; 
    const start = photosLoadedCount + 1;
    let end = Math.min(start + BATCH_SIZE - 1, currentAlbum.count);

    if (start > currentAlbum.count) {
        isLoading = false;
        return;
    }

    for (let i = start; i <= end; i++) {
        const src = `${currentAlbum.folder}/${currentAlbum.prefix}${i}${extension}`;
        
        let targetColumn = columns[i % columns.length];

        const div = document.createElement('div');
        div.className = 'photo-item';
        
        const img = document.createElement('img');
        img.alt = `Photo ${currentAlbum.title} ${i}`;
        img.loading = "lazy";
        const photo = {
            index: i,
            src
        };
        
        img.onload = () => { 
            div.classList.add('loaded'); 
            loadedPhotos.push(photo);
            loadedPhotos.sort((a, b) => a.index - b.index);
        };
        
        img.onerror = () => {
            div.remove();
        };

        img.src = src; 
        
        div.onclick = () => openLightbox(photo);
        div.appendChild(img);
        targetColumn.appendChild(div);
    }
    
    photosLoadedCount = end;
    setTimeout(() => { isLoading = false; }, 50); 
}

// --- LIGHTBOX ---
window.openLightbox = function(index) {
    const lb = document.getElementById('lightbox');
    const lbImg = document.getElementById('lightbox-img');

    if (lb && lbImg && currentAlbum && loadedPhotos.length > 0) {
        const photoPosition = typeof index === 'object'
            ? loadedPhotos.findIndex(photo => photo.index === index.index)
            : loadedPhotos.findIndex(photo => photo.index === index);

        if (photoPosition === -1) return;

        currentPhotoPosition = photoPosition;
        updateLightboxImage();
        lb.style.display = 'flex';
        document.body.style.overflow = 'hidden';
    }
}

window.changePhoto = function(direction) {
    if (!currentAlbum || loadedPhotos.length === 0) return;

    currentPhotoPosition += direction;
    if (currentPhotoPosition >= loadedPhotos.length) currentPhotoPosition = 0;
    if (currentPhotoPosition < 0) currentPhotoPosition = loadedPhotos.length - 1;

    updateLightboxImage();
}

function updateLightboxImage() {
    const lbImg = document.getElementById('lightbox-img');
    const currentPhoto = loadedPhotos[currentPhotoPosition];

    if (!lbImg || !currentPhoto) return;

    lbImg.src = currentPhoto.src;
    lbImg.alt = `Photo ${currentAlbum.title} ${currentPhoto.index}`;
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
    if (scrollTop + clientHeight >= scrollHeight - 2000) {
        if (photosLoadedCount < currentAlbum.count) {
            loadNextBatch();
        }
    }
}