// VARIABLES GLOBALES
let currentAlbum = null;
let photosLoadedCount = 0;
let isLoading = false;
const BATCH_SIZE = 20; 

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
    } else {
        document.getElementById('album-title').innerText = "Album introuvable";
    }
});

function initGalleryStructure() {
    const container = document.getElementById('gallery-container');
    container.innerHTML = ""; 

    const isMobile = window.innerWidth < 768;
    const colCount = isMobile ? 2 : 3;
    
    for (let c = 0; c < colCount; c++) {
        const colDiv = document.createElement('div');
        colDiv.className = 'masonry-column';
        container.appendChild(colDiv);
    }
}

function handleScroll() {
    if (isLoading || !currentAlbum || photosLoadedCount >= currentAlbum.count) return;
    
    // On charge la suite quand on arrive un peu avant le bas
    const scrollPosition = window.innerHeight + window.scrollY;
    const threshold = document.body.offsetHeight - 800; 

    if (scrollPosition >= threshold) {
        loadNextBatch();
    }
}

function loadNextBatch() {
    if (!currentAlbum) return;
    isLoading = true;

    const container = document.getElementById('gallery-container');
    const extension = currentAlbum.ext || ".webp";
    
    // On récupère les colonnes pour les mesurer
    const columns = Array.from(document.querySelectorAll('.masonry-column'));
    
    const start = photosLoadedCount + 1;
    let end = start + BATCH_SIZE - 1;
    if (end > currentAlbum.count) end = currentAlbum.count;

    for (let i = start; i <= end; i++) {
        const src = `${currentAlbum.folder}/${currentAlbum.prefix}${i}${extension}`;
        
        // --- ALGORITHME D'ÉQUILIBRAGE ---
        // On cherche la colonne la plus petite (en hauteur de pixels)
        // Grâce au CSS (min-height), même une photo non chargée prend de la place
        let shortestColumn = columns[0];
        
        columns.forEach(col => {
            if (col.offsetHeight < shortestColumn.offsetHeight) {
                shortestColumn = col;
            }
        });

        // CRÉATION DE LA CARTE PHOTO
        const div = document.createElement('div');
        div.className = 'photo-item';
        div.style.opacity = '0'; 
        div.style.transition = 'opacity 0.4s ease';

        const img = document.createElement('img');
        img.src = src;
        img.alt = `Photo ${i}`;
        
        // Optimisation chargement
        if (i <= 6) img.loading = "eager"; 
        else img.loading = "lazy";

        // Affichage fluide
        const showImage = () => {
            div.classList.add('loaded');
            div.style.opacity = '1';
            // Une fois chargée, on enlève la contrainte de hauteur min pour que ce soit parfait
            div.style.minHeight = '0'; 
        };

        img.onload = showImage;
        if (img.complete) showImage();
        
        img.onerror = () => { div.style.display = 'none'; };
        div.onclick = () => openLightbox(src);
        
        div.appendChild(img);
        
        // --- INSERTION DANS LA COLONNE LA PLUS COURTE ---
        shortestColumn.appendChild(div);
    }

    photosLoadedCount = end;
    
    // Petit délai pour laisser le navigateur recalculer les hauteurs avant la prochaine vague
    setTimeout(() => {
        isLoading = false;
        // Si on n'a pas encore rempli l'écran (grands écrans), on en charge d'autres
        if(document.body.offsetHeight < window.innerHeight) {
            handleScroll();
        }
    }, 100);
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