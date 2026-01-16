// --- VARIABLES ---
const BATCH_SIZE = 12; // On charge par paquets de 12
let currentIndex = 1;
let album = null;
let isLoading = false;
let columnsElements = []; 
let balanceTimeout; // Timer pour éviter de recalculer trop souvent

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
        
        initColumns();
        loadBatch(); 
        setupInfiniteScroll();

        // Rééquilibrage au redimensionnement de la fenêtre
        window.addEventListener('resize', () => {
            initColumns();
            // On recharge tout le contenu actuel pour le redistribuer proprement
            const totalLoaded = currentIndex;
            currentIndex = 1; 
            document.querySelectorAll('.photo-item').forEach(el => el.remove());
            loadBatch(totalLoaded); 
        });

    } else {
        document.getElementById('album-title').innerText = "Album introuvable";
        const loader = document.getElementById('loader-indicator');
        if(loader) loader.style.display = 'none';
    }
});

// Crée les 3 colonnes vides
function initColumns() {
    const container = document.getElementById('gallery-container');
    // On ne vide le conteneur que s'il n'a pas de colonnes
    if(container.children.length === 0 || !container.querySelector('.gallery-col')) {
        container.innerHTML = ''; 
        columnsElements = [];

        const width = window.innerWidth;
        let colCount = 3;
        if (width <= 768) colCount = 1;
        else if (width <= 1024) colCount = 2;

        for (let i = 0; i < colCount; i++) {
            const col = document.createElement('div');
            col.className = 'gallery-col';
            container.appendChild(col);
            columnsElements.push(col);
        }
    } else {
        // Si elles existent déjà, on met juste à jour la référence
        columnsElements = Array.from(container.querySelectorAll('.gallery-col'));
    }
}

function loadBatch(forceCount = null) {
    if (isLoading && !forceCount) return;
    
    // Si forceCount est défini (ex: resize), on ne bloque pas sur isLoading
    if(!forceCount && currentIndex > album.count) return;
    
    isLoading = true;
    const loader = document.getElementById('loader-indicator');
    loader.classList.add('active');

    // Combien d'images à charger ? (Soit le paquet normal, soit tout ce qu'on avait avant un resize)
    let limit = forceCount ? forceCount : Math.min(currentIndex + BATCH_SIZE, album.count + 1);
    
    // On boucle pour créer les images
    for (let i = currentIndex; i < limit; i++) {
        const item = createPhotoItem(i);
        
        // INSERTION INTELLIGENTE : On ajoute à la colonne la plus petite (en pixels)
        // Note : Au tout début, tout est à 0, donc ça remplit 1, 2, 3...
        const shortestCol = getShortestColumn();
        shortestCol.appendChild(item);

        // Animation douce
        setTimeout(() => { item.classList.add('visible'); }, 50 + (i - currentIndex) * 30);
    }

    currentIndex = limit;

    // Fin du chargement
    setTimeout(() => {
        isLoading = false;
        if (currentIndex > album.count) loader.style.display = 'none';
        else loader.classList.remove('active');
        
        // Une fois le lot ajouté, on lance l'équilibrage fin
        triggerBalance();
    }, 500);
}

// Trouve la colonne la plus petite ACTUELLEMENT
function getShortestColumn() {
    // On trie les colonnes par hauteur (offsetHeight)
    // On retourne celle qui a la plus petite hauteur
    return columnsElements.reduce((prev, curr) => {
        return (prev.offsetHeight < curr.offsetHeight) ? prev : curr;
    });
}

// Fonction qui déclenche l'équilibrage avec un petit délai (debounce)
function triggerBalance() {
    clearTimeout(balanceTimeout);
    balanceTimeout = setTimeout(balanceLayout, 300);
}

// C'est ici que la magie opère : LE RÉ-ÉQUILIBRAGE
function balanceLayout() {
    // Inutile sur mobile (1 colonne)
    if (columnsElements.length <= 1) return;

    let moves = 0;
    const MAX_MOVES = 10; // Sécurité pour éviter boucle infinie
    let balanced = false;

    while (!balanced && moves < MAX_MOVES) {
        // Trouver la plus grande et la plus petite colonne
        let minCol = columnsElements[0];
        let maxCol = columnsElements[0];

        columnsElements.forEach(col => {
            if (col.offsetHeight < minCol.offsetHeight) minCol = col;
            if (col.offsetHeight > maxCol.offsetHeight) maxCol = col;
        });

        // Si la différence de hauteur est supérieure à la taille moyenne d'une photo (ex: 300px)
        // ET que la grande colonne a plus d'images que la petite
        if ((maxCol.offsetHeight - minCol.offsetHeight > 300) && maxCol.children.length > 1) {
            // On prend la DERNIÈRE image de la plus grande colonne
            const lastImg = maxCol.lastElementChild;
            // Et on la déplace vers la plus petite
            minCol.appendChild(lastImg);
            moves++;
        } else {
            balanced = true; // C'est assez équilibré
        }
    }
}

function createPhotoItem(index) {
    const extension = album.ext || ".webp";
    const div = document.createElement('div');
    div.className = 'photo-item';
    
    const img = document.createElement('img');
    const smallSrc = `${album.folder}/${album.prefix}${index}-small${extension}`;
    const bigSrc = `${album.folder}/${album.prefix}${index}${extension}`;

    img.src = smallSrc;
    img.loading = "lazy"; 
    img.alt = `${album.title} ${index}`;
    
    // Quand l'image est chargée, on revérifie l'équilibre (car maintenant on connait sa vraie hauteur)
    img.onload = () => triggerBalance();

    img.onerror = function() { 
        if (this.src !== bigSrc) this.src = bigSrc; 
    };

    div.onclick = () => openLightbox(bigSrc);
    div.appendChild(img);
    return div;
}

// SCROLL INFINI (inchangé)
function setupInfiniteScroll() {
    const trigger = document.getElementById('loader-indicator');
    const observer = new IntersectionObserver((entries) => {
        if (entries[0].isIntersecting) loadBatch();
    }, { rootMargin: "400px" });
    observer.observe(trigger);
}

// LIGHTBOX (inchangée)
window.openLightbox = function(src) {
    const lb = document.getElementById('lightbox');
    const lbImg = document.getElementById('lightbox-img');
    lbImg.src = src;
    lb.style.display = 'flex';
}
window.closeLightbox = function() {
    document.getElementById('lightbox').style.display = 'none';
}