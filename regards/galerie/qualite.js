// Niveau de qualité de la visite, partagé par tous les modules (matières, effets d'image, sensations de jeu).
// « haut » sur ordinateur, « bas » sur téléphone, sauf choix du visiteur (réglages, gardé dans le navigateur).
// Aussi forçable par l'adresse : index.html?qualite=moyen
const phone = matchMedia('(max-width: 800px)').matches;
const NIVEAUX = ['bas', 'moyen', 'haut'];
function saved() {
  try { return localStorage.getItem('galerie-qualite'); } catch { return null; }
}
const asked = new URLSearchParams(location.search).get('qualite');
export const NIVEAU = NIVEAUX.includes(asked) ? asked : NIVEAUX.includes(saved()) ? saved() : (phone ? 'bas' : 'haut');

export const Q = {
  niveau: NIVEAU,
  textures2k: NIVEAU === 'haut',           // couleurs des matières en 2048 px (sinon 1024)
  relief: NIVEAU !== 'bas',                // relief des murs par parallaxe (coûteux)
  reliefOmbre: NIVEAU === 'haut',          // ombre du relief (joints dans l'ombre)
  ao: NIVEAU !== 'bas',                    // ombres de contact à l'écran (SSAO)
  halo: NIVEAU !== 'bas',                  // halo des lumières (bloom)
  msaa: NIVEAU === 'haut' ? 4 : NIVEAU === 'moyen' ? 2 : 0,
  pixels: NIVEAU === 'bas' ? Math.min(devicePixelRatio, 1.25) : Math.min(devicePixelRatio, 2),
  phone,
};

export function setNiveau(niveau) {
  if (!NIVEAUX.includes(niveau)) return;
  try { localStorage.setItem('galerie-qualite', niveau); } catch { /* navigation privée : seulement pour cette fois */ }
  location.reload();
}
