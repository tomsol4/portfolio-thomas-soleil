// ============================================================
// CONFIGURATION DU SITE - C'est ici que tu ajoutes tes albums
// ============================================================

const siteConfig = {
    // Tes infos personnelles
    identity: {
        name: "Thomas Soleil",
        tagline: "Photographe Événementiel & Portrait",
        email: "ton-email@exemple.com",
        instagram: "https://www.instagram.com/tomsol_photo/"
    },

    // LA LISTE DE TES ALBUMS
    // Pour ajouter un album, copie un bloc {...} et colle-le en dessous
    albums: [
        {
            id: "chartres", // L'identifiant unique (utilisé dans l'URL)
            title: "Chartres",
            cover: "images/photo-05.jpg", // Image de couverture pour l'accueil
            folder: "images/chartres", // Dossier où sont les photos
            prefix: "chartres-", // Début du nom des fichiers
            count: 22, // Nombre de photos
            date: "2024"
        },
        {
            id: "rock-toulouse",
            title: "Rock Toulouse",
            cover: "images/rocktoulouse/Rock-31.jpg",
            folder: "images/rocktoulouse",
            prefix: "Rock-",
            count: 100,
            date: "2024"
        },
        {
            id: "montagne",
            title: "Expédition Montagne",
            cover: "images/photo-02.jpg",
            folder: "images/Montagne",
            prefix: "Montagne-",
            count: 112,
            date: "2023"
        },
        {
            id: "noel",
            title: "Concert Noël Chor Unum",
            cover: "images/noelchorunum/noelchorunum-4.jpg",
            folder: "images/noelchorunum",
            prefix: "noelchorunum-",
            count: 260,
            date: "2024"
        }
    ]
};