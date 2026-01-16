// --- VARIABLES ---
const BATCH_SIZE = 10;   // Nombre d'images chargées par vague
let currentIndex = 1;
let columnWrappers = [];
let album = null;
let isLoading = false;   // Sécurité pour éviter le double chargement

document.addEventListener("DOMContentLoaded", () => {
    // 1. Initialisation
    const params = new URLSearchParams(window.location.search);
    const albumId = params.get('id');
    
    // On cherche l'album dans config.js
    if (typeof siteConfig !== 'undefined') {
        album = siteConfig.albums.find(a => a.id === albumId);
    }

    if (album) {
        // Mise à jour des textes
        document.title = `${album.title} | Thomas Soleil`;
        document.getElementById('album-title').innerText = album.title;
        document.getElementById('album-meta').innerText = album.date;
        
        initGalleryLayout();
        loadBatch(); // Premier chargement
        setupInfiniteScroll();
    } else {
        document.getElementById('album-title').innerText = "Album introuvable";
        const loader = document.getElementById('loader-indicator');
        if(loader) loader.style.display = 'none';
    }
});

// 2. Création des colonnes (Layout)
function initGalleryLayout() {
    const container = document.getElementById('gallery-container');
    container.innerHTML = "";
    
    // Détection Mobile ou PC
    const isMobile = window.innerWidth <= 1024;
    const nbColumns = isMobile ? 2 : 3;

    for (let c = 0; c < nbColumns; c++) {
        let col = document.createElement('div');
        col.className = 'masonry-column';
        container.appendChild(col);
        columnWrappers.push(col);
    }
}

// 3. Chargement progressif des images
function loadBatch() {
    if (isLoading || currentIndex > album.count) return;
    
    isLoading = true;
    document.getElementById('loader-indicator').classList.add('active');

    const limit = Math.min(currentIndex + BATCH_SIZE, album.count + 1);
    const totalImagesInBatch = limit - currentIndex;

    if (totalImagesInBatch <= 0) {
        isLoading = false;
        document.getElementById('loader-indicator').classList.remove('active');
        return;
    }

    for (let i = currentIndex; i < limit; i++) {
        // (i - currentIndex) * 100 permet un délai en cascade (0ms, 100ms, 200ms...)
        createPhotoItem(i, (i - currentIndex) * 100); 
    }

    currentIndex = limit;

    // Petit délai pour permettre au DOM de respirer
    setTimeout(() => {
        isLoading = false;
        document.getElementById('loader-indicator').classList.remove('active');
    }, 500);
}

function createPhotoItem(index, delay) {
    const extension = album.ext || ".webp";
    const div = document.createElement('div');
    div.className = 'photo-item';
    
    const img = document.createElement('img');
    const smallSrc = `${album.folder}/${album.prefix}${index}-small${extension}`;
    const bigSrc = `${album.folder}/${album.prefix}${index}${extension}`;

    // On charge l'image (petite par défaut si elle existait, sinon grande via onerror)
    // Note : Pour l'instant, ton code charge direct la petite. 
    // Si tu n'as pas généré de miniatures (-small), le onerror chargera la grande.
    img.src = smallSrc;
    img.loading = "lazy";
    img.alt = `${album.title} ${index}`;
    
    img.onerror = function() { 
        if (this.src !== bigSrc) this.src = bigSrc; 
    };

    // L'ANIMATION MAGIQUE : Quand l'image est chargée
    img.onload = () => {
        setTimeout(() => {
            div.classList.add('visible');
        }, delay); 
    };

    // Fallback : si l'image est déjà en cache, le onload peut ne pas se déclencher
    if (img.complete) {
        setTimeout(() => {
            div.classList.add('visible');
        }, delay);
    }

    // Lightbox au clic
    div.onclick = () => openLightbox(bigSrc);

    div.appendChild(img);

    // Distribution "Round Robin" (Colonne 1, puis 2, puis 3...)
    const colIndex = (index - 1) % columnWrappers.length;
    columnWrappers[colIndex].appendChild(div);
}

// 4. Scroll Infini (Intersection Observer)
function setupInfiniteScroll() {
    const trigger = document.getElementById('loader-indicator');
    
    const observer = new IntersectionObserver((entries) => {
        if (entries[0].isIntersecting) {
            loadBatch();
        }
    }, { rootMargin: "100px" }); 

    observer.observe(trigger);
}

// 5. Gestion de la Lightbox
// Note : Ces fonctions doivent être accessibles globalement (window) pour le HTML onclick, 
// ou attachées via JS. Ici, on les attache via JS dans createPhotoItem, 
// mais on garde les fonctions globales pour le bouton de fermeture HTML.
window.openLightbox = function(src) {
    const lb = document.getElementById('lightbox');
    const lbImg = document.getElementById('lightbox-img');
    lbImg.src = src;
    lb.style.display = 'flex';
}

window.closeLightbox = function() {
    document.getElementById('lightbox').style.display = 'none';
}