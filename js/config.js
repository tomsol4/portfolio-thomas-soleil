// ============================================================
// CONFIGURATION DU SITE (100% WEBP)
// ============================================================

const siteConfig = {
    identity: {
        name: "Thomas Soleil",
        tagline: "Photographe Événementiel & Portrait",
        email: "ton-email@exemple.com",
        instagram: "https://www.instagram.com/tomsol_photo/"
    },

    // LISTE DES ALBUMS
    albums: [
        {
            id: "noel", 
            title: "Concert Noël Chor Unum",
            
            // CORRECTION ICI : On met .webp
            cover: "images/noelchorunum/noelchorunum-4.webp", 
            
            folder: "images/noelchorunum", 
            prefix: "chorunumnoel-", // Attention à ce nom, vérifie tes fichiers !
            count: 260,
            date: "2024",
            ext: ".webp"
        },
        {
            id: "chartres",
            title: "Chartres",
            
            // CORRECTION ICI
            cover: "images/chartres/chartres-5.webp", // Mets le nom de ta photo préférée
            
            folder: "images/chartres",
            prefix: "chartres-",
            count: 22,
            date: "2024",
            ext: ".webp"
        },
        {
            id: "rock-toulouse",
            title: "Rock Toulouse",
            cover: "images/rocktoulouse/Rock-31.webp",
            folder: "images/rocktoulouse",
            prefix: "Rock-",
            count: 100,
            date: "2024",
            ext: ".webp"
        },
        {
            id: "montagne",
            title: "Expédition Montagne",
            cover: "images/Montagne/Montagne-2.webp",
            folder: "images/Montagne",
            prefix: "Montagne-",
            count: 112,
            date: "2023",
            ext: ".webp"
        }
    ]
};