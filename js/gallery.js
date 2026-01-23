document.addEventListener("DOMContentLoaded", () => {
    const params = new URLSearchParams(window.location.search);
    const albumId = params.get('id');
    
    if (typeof siteConfig === 'undefined' || !albumId) {
        const title = document.getElementById('album-title');
        if(title) title.innerText = "Album introuvable";
        return;
    }

    const album = siteConfig.albums.find(a => a.id === albumId);

    if (album) {
        document.title = `${album.title} | Thomas Soleil`;
        document.getElementById('album-title').innerText = album.title;
        document.getElementById('album-meta').innerText = album.date;
        
        // Lancement de la génération intelligente
        generateSmartGallery(album);
    } else {
        document.getElementById('album-title').innerText = "Album introuvable";
    }
});

async function generateSmartGallery(album) {
    const container = document.getElementById('gallery-container');
    const extension = album.ext || ".webp";
    
    container.innerHTML = ""; 

    // 1. CRÉATION DES COLONNES
    const isMobile = window.innerWidth < 768;
    const colCount = isMobile ? 2 : 3;
    const columns = [];

    for (let c = 0; c < colCount; c++) {
        const colDiv = document.createElement('div');
        colDiv.className = 'masonry-column';
        container.appendChild(colDiv);
        columns.push(colDiv);
    }

    // 2. CHARGEMENT ET DISTRIBUTION INTELLIGENTE
    // On boucle sur toutes les images
    for (let i = 1; i <= album.count; i++) {
        const src = `${album.folder}/${album.prefix}${i}${extension}`;
        
        // On crée l'objet image en mémoire pour tester sa taille
        const imgObject = new Image();
        imgObject.src = src;

        // ASTUCE PRO : On attend que l'image ait chargé ses infos (taille)
        // avant de l'afficher. Cela permet de savoir si c'est un portrait ou paysage.
        await new Promise(resolve => {
            imgObject.onload = resolve;
            imgObject.onerror = resolve; // On continue même si erreur
        });

        // 3. ALGORITHME "COLONNE LA PLUS COURTE"
        // On cherche quelle colonne est la moins haute actuellement
        let shortestColIndex = 0;
        let minHeight = columns[0].offsetHeight;

        for (let j = 1; j < columns.length; j++) {
            if (columns[j].offsetHeight < minHeight) {
                minHeight = columns[j].offsetHeight;
                shortestColIndex = j;
            }
        }

        // 4. CRÉATION DE LA CARTE FINALE
        const div = document.createElement('div');
        div.className = 'photo-item loaded'; // On met direct 'loaded' car on a déjà attendu
        
        // On reprend l'image qu'on a déjà chargée (plus rapide)
        const finalImg = imgObject; 
        finalImg.alt = `Photo ${i} - ${album.title}`;
        
        // Click Lightbox
        div.onclick = () => openLightbox(src);
        div.appendChild(finalImg);

        // On l'ajoute dans la colonne LA PLUS COURTE
        columns[shortestColIndex].appendChild(div);
    }
}

// --- LIGHTBOX ---
window.openLightbox = function(src) {
    const lb = document.getElementById('lightbox');
    const lbImg = document.getElementById('lightbox-img');
    if(lb && lbImg) {
        lbImg.src = src;
        lb.style.display = 'flex';
    }
}

window.closeLightbox = function() {
    const lb = document.getElementById('lightbox');
    if(lb) lb.style.display = 'none';
}