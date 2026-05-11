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
            id: "Argentique",
            title: "Photo Argentique",
            cover: "images/argentique/Argentique-26.webp",
            folder: "images/argentique",
            prefix: "Argentique-",
            count: 23,
            date: "2025",
            ext: ".webp"
        },
        {
            id: "mariage",
            title: "mariage",
            cover: "images/mariage/mariage1-1.webp",
            folder: "images/mariage",
            prefix: "mariage1-",
            count: 77,
            date: "2026",
            ext: ".webp"
        },
        {
            id: "rugby",
            title: "Rugby toulouse-Leinster Espoirs",
            cover: "images/rugby/CO-BayonneEspoirs-209.webp",
            folder: "images/rugby",
            prefix: "CO-BayonneEspoirs-",
            count: 241,
            date: "2026",
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
            id: "rugby_co",
            title: "Castres Olympique Feminin",
            cover: "images/rugby_co/rugbyCO-88.webp",
            folder: "images/rugby_co",
            prefix: "rugbyCO-",
            count: 203,
            date: "2026",
            ext: ".webp"
        },

        {
            id: "noel", 
            title: "Concert Noël Chor Unum",
            cover: "images/noelchorunum/chorunumnoel-4.webp", 
            folder: "images/noelchorunum", 
            prefix: "chorunumnoel-", // Attention à ce nom, vérifie tes fichiers !
            count: 260,
            date: "2025",
            ext: ".webp"
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