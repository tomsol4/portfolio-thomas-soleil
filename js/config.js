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
            id: "rugby",
            title: "Rugby",
            cover: "images/rugby/rugby-33.webp",
            folder: "images/rugby",
            prefix: "rugby-",
            count: 147,
            date: "2025",
            ext: ".webp"
        },
        {
            id: "noel", 
            title: "Concert Noël Chor Unum",
            // CORRECTION ICI : On met .webp
            cover: "images/noelchorunum/chorunumnoel-4.webp", 
            folder: "images/noelchorunum", 
            prefix: "chorunumnoel-", // Attention à ce nom, vérifie tes fichiers !
            count: 260,
            date: "2025",
            ext: ".webp"
        },

        {
            id: "rocktoulouse",
            title: "Rock Toulouse",
            cover: "images/rocktoulouse/Rock-25.webp",
            folder: "images/rocktoulouse",
            prefix: "Rock-",
            count: 77,
            date: "2025",
            ext: ".webp"
        },
        {
            id: "montagne",
            title: "Randonnée Montagne",
            cover: "images/montagne/Montagne-5.webp",
            folder: "images/montagne",
            prefix: "Montagne-",
            count: 112,
            date: "2025",
            ext: ".webp"
        },
        {
            id: "argentique",
            title: "Photo Argentique",
            cover: "images/argentique/argentique1.jpg",
            folder: "images/argentique",
            prefix: "argentique",
            count: 23,
            date: "2025",
            ext: ".jpg"
        },
        {
            id: "autres",
            title: "autres",
            cover: "images/vrac/vrac-18.jpg", // Mets le nom de ta photo préférée
            folder: "images/vrac",
            prefix: "vrac-",    
            count: 22,
            date: "",
            ext: ".jpg"
        },
    ]
};