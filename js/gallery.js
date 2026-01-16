// --- VARIABLES ---
const BATCH_SIZE = 10;
let currentIndex = 1;
let album = null;
let isLoading = false;
let msnry; // Variable pour stocker l'instance Masonry

document.addEventListener("DOMContentLoaded", () => {
    // 1. Initialisation
    const params = new URLSearchParams(window.location.search);
    const albumId = params.get('id');
    const container = document.getElementById('gallery-container');
    
    // Initialiser Masonry sur le conteneur vide
    msnry = new Masonry( container, {
        itemSelector: '.photo-item',
        columnWidth: '.photo-item', // Utilise la largeur de l'élément pour la grille
        percentPosition: true,      // Responsive
        gutter: 20                  // Espace entre les images (si besoin d'ajuster le CSS)
    });

    if (typeof siteConfig !== 'undefined') {
        album = siteConfig.albums.find(a => a.id === albumId);
    }

    if (album) {
        document.title = `${album.title} | Thomas Soleil`;
        document.getElementById('album-title').innerText = album.title;
        document.getElementById('album-meta').innerText = album.date;
        
        loadBatch(); 
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
    
    // Tableau pour stocker les nouveaux éléments créés
    let newItems = [];

    for (let i = currentIndex; i < limit; i++) {
        const item = createPhotoItem(i);
        container.appendChild(item); // On ajoute au DOM
        newItems.push(item);         // On garde en mémoire
    }

    // 3. IMPORTANT : On attend que les images soient chargées pour que Masonry calcule la hauteur
    imagesLoaded( container, function() {
        // Dire à Masonry que de nouveaux éléments sont arrivés
        msnry.appended( newItems );
        msnry.layout(); // Recalculer la grille

        // Animation d'apparition
        newItems.forEach((item, index) => {
            setTimeout(() => {
                item.classList.add('visible');
            }, index * 100);
        });

        isLoading = false;
        document.getElementById('loader-indicator').classList.remove('active');
    });

    currentIndex = limit;
}

function createPhotoItem(index) {
    const extension = album.ext || ".webp";
    const div = document.createElement('div');
    div.className = 'photo-item';
    
    const img = document.createElement('img');
    const smallSrc = `${album.folder}/${album.prefix}${index}-small${extension}`;
    const bigSrc = `${album.folder}/${album.prefix}${index}${extension}`;

    img.src = smallSrc;
    // img.loading = "lazy"; // ATTENTION : Avec Masonry, mieux vaut éviter le lazy loading natif agressif au début pour le calcul des hauteurs, ou bien gérer height fixe.
    img.alt = `${album.title} ${index}`;
    
    img.onerror = function() { 
        if (this.src !== bigSrc) this.src = bigSrc; 
    };

    div.onclick = () => openLightbox(bigSrc);
    div.appendChild(img);
    return div;
}

// 4. Scroll Infini
function setupInfiniteScroll() {
    const trigger = document.getElementById('loader-indicator');
    
    const observer = new IntersectionObserver((entries) => {
        if (entries[0].isIntersecting) {
            loadBatch();
        }
    }, { rootMargin: "200px" });

    observer.observe(trigger);
}

// 5. Lightbox (inchangé)
window.openLightbox = function(src) {
    const lb = document.getElementById('lightbox');
    const lbImg = document.getElementById('lightbox-img');
    lbImg.src = src;
    lb.style.display = 'flex';
}

window.closeLightbox = function() {
    document.getElementById('lightbox').style.display = 'none';
}