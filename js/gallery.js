// --- VARIABLES ---
const BATCH_SIZE = 12; // On charge par 12 pour que ça se divise bien par 2 ou 3
let currentIndex = 1;
let album = null;
let isLoading = false;
let allLoadedItems = []; // Stocke tous les éléments DOM créés pour pouvoir les réorganiser au resize
let columnsElements = []; // Références aux divs des colonnes

document.addEventListener("DOMContentLoaded", () => {
    // 1. Initialisation
    const params = new URLSearchParams(window.location.search);
    const albumId = params.get('id');
    
    if (typeof siteConfig !== 'undefined') {
        album = siteConfig.albums.find(a => a.id === albumId);
    }

    if (album) {
        document.title = `${album.title} | Thomas Soleil`;
        document.getElementById('album-title').innerText = album.title;
        document.getElementById('album-meta').innerText = album.date;
        
        // Initialiser la structure des colonnes
        initColumns();

        // Lancer le premier chargement
        loadBatch();
        setupInfiniteScroll();

        // Écouter le redimensionnement pour réorganiser si besoin
        let resizeTimeout;
        window.addEventListener('resize', () => {
            clearTimeout(resizeTimeout);
            resizeTimeout = setTimeout(() => {
                reorganizeGallery();
            }, 200);
        });

    } else {
        document.getElementById('album-title').innerText = "Album introuvable";
        const loader = document.getElementById('loader-indicator');
        if(loader) loader.style.display = 'none';
    }
});

// Crée les colonnes (divs) dans le conteneur
function initColumns() {
    const container = document.getElementById('gallery-container');
    container.innerHTML = ''; // Reset total
    columnsElements = [];

    // Déterminer le nombre de colonnes selon la largeur d'écran
    const width = window.innerWidth;
    let colCount = 3;
    if (width <= 768) colCount = 1;
    else if (width <= 1024) colCount = 2;

    // Création des DIV colonnes
    for (let i = 0; i < colCount; i++) {
        const col = document.createElement('div');
        col.className = 'gallery-col';
        container.appendChild(col);
        columnsElements.push(col);
    }
}

// Fonction pour tout réorganiser lors d'un resize
function reorganizeGallery() {
    const oldCols = columnsElements.length;
    const width = window.innerWidth;
    let newColCount = 3;
    
    if (width <= 768) newColCount = 1;
    else if (width <= 1024) newColCount = 2;

    // Si le nombre de colonnes change, on refait tout
    if (oldCols !== newColCount) {
        initColumns(); // Recrée les colonnes vides
        // Redistribue toutes les images déjà chargées
        allLoadedItems.forEach((item, index) => {
            const colIndex = index % newColCount;
            columnsElements[colIndex].appendChild(item);
        });
    }
}

function loadBatch() {
    if (isLoading || currentIndex > album.count) return;
    
    isLoading = true;
    const loader = document.getElementById('loader-indicator');
    loader.classList.add('active');

    const limit = Math.min(currentIndex + BATCH_SIZE, album.count + 1);
    
    // On récupère le nombre actuel de colonnes
    const colCount = columnsElements.length;

    for (let i = currentIndex; i < limit; i++) {
        // Création de l'élément
        const item = createPhotoItem(i);
        allLoadedItems.push(item); // On le garde en mémoire

        // Distribution "Round Robin" : 1->Col1, 2->Col2, 3->Col3, 4->Col1...
        // C'est ce qui garantit l'équilibre sans calcul complexe
        const colIndex = (i - 1) % colCount; 
        columnsElements[colIndex].appendChild(item);

        // Animation d'apparition
        setTimeout(() => {
            item.classList.add('visible');
        }, 50 + (i - currentIndex) * 50);
    }

    currentIndex = limit;

    // On débloque immédiatement, pas besoin d'attendre le chargement des images
    setTimeout(() => {
        isLoading = false;
        // Si on a tout chargé, on cache le loader définitivement
        if (currentIndex > album.count) {
            loader.style.display = 'none';
        } else {
            loader.classList.remove('active');
        }
    }, 200);
}

function createPhotoItem(index) {
    const extension = album.ext || ".webp";
    const div = document.createElement('div');
    div.className = 'photo-item';
    
    const img = document.createElement('img');
    const smallSrc = `${album.folder}/${album.prefix}${index}-small${extension}`;
    const bigSrc = `${album.folder}/${album.prefix}${index}${extension}`;

    // On met la grande image directement si pas de small, ou logique de fallback
    img.src = smallSrc;
    img.loading = "lazy"; 
    img.alt = `${album.title} - Photo ${index}`;
    
    // Fallback erreur
    img.onerror = function() { 
        if (this.src !== bigSrc) this.src = bigSrc; 
    };

    // Lightbox
    div.onclick = () => openLightbox(bigSrc);

    div.appendChild(img);
    return div;
}

function setupInfiniteScroll() {
    const trigger = document.getElementById('loader-indicator');
    
    // Observer simple
    const observer = new IntersectionObserver((entries) => {
        if (entries[0].isIntersecting) {
            loadBatch();
        }
    }, { rootMargin: "400px" }); // Charge bien en avance

    observer.observe(trigger);
}

// --- LIGHTBOX (Inchangée) ---
window.openLightbox = function(src) {
    const lb = document.getElementById('lightbox');
    const lbImg = document.getElementById('lightbox-img');
    lbImg.src = src;
    lb.style.display = 'flex';
}
window.closeLightbox = function() {
    document.getElementById('lightbox').style.display = 'none';
}