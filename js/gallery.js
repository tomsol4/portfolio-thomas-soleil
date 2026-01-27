// VARIABLES GLOBALES
let currentAlbum = null;
let photosLoadedCount = 0;
let isLoading = false;

// REGLAGE 1 : On charge 40 photos d'un coup (au lieu de 20)
// Cela crée un gros tampon d'avance.
const BATCH_SIZE = 40; 

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
    
    // REGLAGE 2 : On charge BEAUCOUP plus tôt.
    // Dès qu'on est à 2000px du bas (environ 2 écrans de hauteur), on lance la suite.
    const scrollPosition = window.innerHeight + window.scrollY;
    const threshold = document.body.offsetHeight - 2000; 

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
        // On cherche la colonne la plus petite
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
        
        // Comme on précharge beaucoup, on laisse en lazy loading pour ne pas bloquer le navigateur
        // Mais comme on déclenche 2000px en avance, le navigateur a le temps de les traiter.
        if (i <= 6) img.loading = "eager"; 
        else img.loading = "lazy";

        // Affichage fluide
        const showImage = () => {
            div.classList.add('loaded');
            div.style.opacity = '1';
            div.style.minHeight = '0'; 
        };

        img.onload = showImage;
        if (img.complete) showImage();
        
        img.onerror = () => { div.style.display = 'none'; };
        div.onclick = () => openLightbox(src);
        
        div.appendChild(img);
        
        // Insertion intelligente
        shortestColumn.appendChild(div);
    }

    photosLoadedCount = end;
    
    // Petit délai de sécurité
    setTimeout(() => {
        isLoading = false;
        // Si l'écran est très grand et n'est pas rempli, on charge encore
        if(document.body.offsetHeight < window.innerHeight + 1000) {
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