// --- VARIABLES ---
const BATCH_SIZE = 10;   // Nombre d'images chargées par vague
let currentIndex = 1;
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
        
        loadBatch(); // Premier chargement
        setupInfiniteScroll();
    } else {
        document.getElementById('album-title').innerText = "Album introuvable";
        const loader = document.getElementById('loader-indicator');
        if(loader) loader.style.display = 'none';
    }
});

// 2. Chargement progressif des images
function loadBatch() {
    if (isLoading || currentIndex > album.count) return;
    
    isLoading = true;
    document.getElementById('loader-indicator').classList.add('active');

    const limit = Math.min(currentIndex + BATCH_SIZE, album.count + 1);
    const container = document.getElementById('gallery-container');

    for (let i = currentIndex; i < limit; i++) {
        // On crée l'élément
        const item = createPhotoItem(i);
        container.appendChild(item);
        
        // Petit délai pour l'animation d'apparition
        // (i - currentIndex) * 50 = délai progressif très rapide
        setTimeout(() => {
            item.classList.add('visible');
        }, (i - currentIndex) * 50 + 100);
    }

    currentIndex = limit;

    // Délai de sécurité avant de permettre le prochain chargement
    setTimeout(() => {
        isLoading = false;
        document.getElementById('loader-indicator').classList.remove('active');
    }, 500);
}

function createPhotoItem(index) {
    const extension = album.ext || ".webp";
    const div = document.createElement('div');
    div.className = 'photo-item';
    
    const img = document.createElement('img');
    const smallSrc = `${album.folder}/${album.prefix}${index}-small${extension}`;
    const bigSrc = `${album.folder}/${album.prefix}${index}${extension}`;

    // Chargement de l'image
    img.src = smallSrc;
    img.loading = "lazy";
    img.alt = `${album.title} ${index}`;
    
    // Si la petite image n'existe pas, on charge la grande
    img.onerror = function() { 
        if (this.src !== bigSrc) this.src = bigSrc; 
    };

    // Lightbox au clic
    div.onclick = () => openLightbox(bigSrc);

    div.appendChild(img);
    return div;
}

// 3. Scroll Infini
function setupInfiniteScroll() {
    const trigger = document.getElementById('loader-indicator');
    
    const observer = new IntersectionObserver((entries) => {
        if (entries[0].isIntersecting) {
            loadBatch();
        }
    }, { rootMargin: "200px" }); // On charge 200px avant d'arriver en bas

    observer.observe(trigger);
}

// 4. Gestion de la Lightbox
window.openLightbox = function(src) {
    const lb = document.getElementById('lightbox');
    const lbImg = document.getElementById('lightbox-img');
    lbImg.src = src;
    lb.style.display = 'flex';
}

window.closeLightbox = function() {
    document.getElementById('lightbox').style.display = 'none';
}