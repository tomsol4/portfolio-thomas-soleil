// Sensations de jeu de la visite en 3D, dans un seul module sans dépendance :
// - createAudio() : les bruits de pas et l'acoustique de chaque salle, fabriqués par le navigateur (Web Audio) :
//   aucun fichier son à télécharger ;
// - readGamepad() : la manette de jeu (Xbox, PlayStation…), lue à chaque image ;
// - createSettings() : le petit panneau de réglages (roue dentée en haut à droite) ;
// - fovKick() : le champ de vision qui s'ouvre un peu quand on court, comme dans les jeux.
import { NIVEAU, setNiveau } from './qualite.js';

const clamp = (v, a, b) => Math.min(b, Math.max(a, v));

// ============================================================================================================
// Son
// ============================================================================================================

// Chaque sol, décrit comme on l'entend :
// - corps : le coup sourd du talon (fréquence de départ en Hz, force, durée en s) ;
// - contact : le claquement de la semelle, un souffle bref filtré (fréquence, largeur de bande Q, force, durée) ;
// - resonance : la caisse qui sonne sous un plancher ou un carreau (fréquence, gain en dB, Q) ;
// - aigus : les aigus gardés, en Hz (une semelle souple les adoucit : rien de criard, même au 500e pas) ;
// - pointe : le second appui, la pointe du pied (retard en s, force par rapport au talon) ;
// - frottement : le grain sous la semelle sur la pierre ou le béton (force, durée) ;
// - grince : la chance qu'une latte grince, par pas (très rare, sinon on ne l'entend plus que ça).
const SURFACES = {
  parquet:   { corps: [105, 0.5, 0.075], contact: [950, 0.9, 0.55, 0.05],   resonance: [240, 6, 2.2], aigus: 4200,  pointe: [0.085, 0.45], frottement: [0, 0],       grince: 0.02 },
  bois:      { corps: [92, 0.55, 0.085], contact: [800, 0.9, 0.5, 0.055],   resonance: [190, 8, 2.5], aigus: 3800,  pointe: [0.09, 0.4],   frottement: [0, 0],       grince: 0.04 },
  pierre:    { corps: [78, 0.4, 0.05],   contact: [1900, 0.8, 0.6, 0.035],  resonance: null,          aigus: 7000,  pointe: [0.07, 0.5],   frottement: [0.14, 0.11], grince: 0 },
  beton:     { corps: [72, 0.45, 0.045], contact: [1350, 0.7, 0.55, 0.032], resonance: null,          aigus: 5200,  pointe: [0.07, 0.45],  frottement: [0.12, 0.09], grince: 0 },
  carrelage: { corps: [88, 0.35, 0.04],  contact: [2300, 1.1, 0.65, 0.03],  resonance: [1250, 4, 3],  aigus: 8000,  pointe: [0.065, 0.55], frottement: [0.05, 0.05], grince: 0 },
  marbre:    { corps: [82, 0.3, 0.035],  contact: [3100, 1.3, 0.7, 0.024],  resonance: null,          aigus: 10000, pointe: [0.06, 0.6],   frottement: [0.03, 0.04], grince: 0 },
};

// Le nom des matières de sol de la galerie (plan.json, musee_3d.py) → le bruit de pas qui va avec
const SOL_DES_MATIERES = { parquet: 'parquet', parquet_clair: 'parquet', dalles: 'pierre', beton: 'beton',
                           tomettes: 'carrelage', marbre: 'marbre', bois: 'bois', pierre: 'pierre', carrelage: 'carrelage' };

// Matière d'un sol → surface pour footstep(). Accepte aussi les noms de la scène (« couvent__dalles », « marbre.001 »).
export function surfaceOf(materialName) {
  const nom = String(materialName ?? '').toLowerCase().split('__').pop().replace(/[.\-_]\d+$/, '');
  return SOL_DES_MATIERES[nom] ?? 'parquet';
}

// L'acoustique des matières des murs : « a » = part du son absorbée à chaque rebond, en comptant aussi les bancs, les
// cadres et les visiteurs (sinon une salle vide de pierre résonnerait 5 secondes) ; « clair » = les aigus gardés
// (la pierre et le marbre renvoient les aigus, la brique et le bois les mangent).
const MATIERES_SON = {
  pierre: { a: 0.05, clair: 0.95 }, marbre: { a: 0.06, clair: 0.9 }, enduit: { a: 0.1, clair: 0.85 },
  beton: { a: 0.08, clair: 0.75 }, brique: { a: 0.095, clair: 0.6 }, chaux: { a: 0.135, clair: 0.7 },
  rouge: { a: 0.145, clair: 0.5 }, bois: { a: 0.19, clair: 0.5 }, lambris: { a: 0.19, clair: 0.5 },
};

// Les salles de la galerie (mêmes mesures que plan.json) : matière des murs, sol, part de réverbération (humide),
// délai avant les premiers échos (predelai, plus long dans une grande salle) et montée de la queue de réverbération.
// Résultat : Couvent ≈ 3 s, clair (voûte de pierre) ; Hall ≈ 2 s, aéré ; Toulouse ≈ 1,5 s ; La Garde, Messe ≈ 1 s ;
// Montagne < 1 s (bois et parquet).
const SALLES_SON = {
  hall:     { largeur: 10, profondeur: 12,   hauteur: 5.0, materiau: 'enduit', sol: 'parquet',   humide: 0.24, predelai: 0.026, montee: 0.06 },
  couvent:  { largeur: 7,  profondeur: 5.85, hauteur: 4.4, materiau: 'pierre', sol: 'pierre',    humide: 0.32, predelai: 0.012, montee: 0.03 },
  toulouse: { largeur: 7,  profondeur: 5.85, hauteur: 4.2, materiau: 'brique', sol: 'beton',     humide: 0.2,  predelai: 0.01,  montee: 0.025 },
  garde:    { largeur: 7,  profondeur: 5.85, hauteur: 4.6, materiau: 'chaux',  sol: 'carrelage', humide: 0.15, predelai: 0.01,  montee: 0.025 },
  messe:    { largeur: 7,  profondeur: 5.85, hauteur: 4.2, materiau: 'rouge',  sol: 'marbre',    humide: 0.14, predelai: 0.01,  montee: 0.025 },
  montagne: { largeur: 10, profondeur: 8,    hauteur: 4.6, materiau: 'bois',   sol: 'parquet',   humide: 0.12, predelai: 0.014, montee: 0.03 },
};
const SALLE_INCONNUE = { largeur: 8, profondeur: 8, hauteur: 4.5, materiau: 'enduit', sol: 'parquet', humide: 0.18, predelai: 0.014, montee: 0.03 };

// Le fond sonore de chaque salle, à peine audible et jamais musical : du bruit filtré (souffle d'air, rumeur lointaine)
// qui ondule lentement (houle : vitesse en Hz, profondeur de 0 à 0,7 ; balayage : la bande qui se déplace, en Hz).
// Deux ondulations de vitesses sans rapport simple : on ne sent pas de cycle qui revient.
const AMBIANCES = {
  hall:     [{ bruit: 'rose', filtres: [['highpass', 160], ['lowpass', 2400]], niveau: 0.012, houle: [0.045, 0.3] }],          // air d'une grande salle
  couvent:  [{ bruit: 'brun', filtres: [['lowpass', 420]], niveau: 0.018, houle: [0.03, 0.2] },
             { bruit: 'rose', filtres: [['bandpass', 900, 0.7]], niveau: 0.004, houle: [0.05, 0.3] }],                         // + des pas lointains (voir ECHOS)
  toulouse: [{ bruit: 'brun', filtres: [['lowpass', 240]], niveau: 0.018, houle: [0.06, 0.4] },                                // la ville, derrière la brique
             { bruit: 'rose', filtres: [['bandpass', 600, 0.6]], niveau: 0.005, houle: [0.08, 0.5] }],
  garde:    [{ bruit: 'rose', filtres: [['highpass', 1400], ['lowpass', 6500]], niveau: 0.006, houle: [0.05, 0.45] },          // l'air du dehors, par la fenêtre haute
             { bruit: 'brun', filtres: [['lowpass', 320]], niveau: 0.012 }],
  messe:    [{ bruit: 'brun', filtres: [['lowpass', 300]], niveau: 0.016, houle: [0.025, 0.15] },                               // silence d'église
             { bruit: 'rose', filtres: [['bandpass', 800, 0.7]], niveau: 0.0035 }],
  montagne: [{ bruit: 'rose', filtres: [['bandpass', 480, 0.8]], niveau: 0.02, houle: [0.07, 0.65], balayage: 220 },           // le vent sur la grande baie
             { bruit: 'rose', filtres: [['bandpass', 2400, 1.2]], niveau: 0.004, houle: [0.11, 0.7], balayage: 600 }],
};
const ECHOS = { couvent: true };   // de temps en temps, quelqu'un marche au loin sous la voûte (on n'entend que l'écho)

// Bruit rangé une fois pour toutes dans un tampon : blanc (pour les pas) ou rose / brun (plus doux, pour les fonds),
// bouclé sans raccord audible (la fin est fondue dans le début)
function fabriquerBruit(ctx, secondes, couleur) {
  const sr = ctx.sampleRate, n = Math.round(sr * secondes), fondu = couleur === 'blanc' ? 0 : Math.round(sr * 0.25);
  const brut = new Float32Array(n + fondu);
  let b0 = 0, b1 = 0, b2 = 0, br = 0, somme = 0;
  for (let i = 0; i < brut.length; i++) {
    const w = Math.random() * 2 - 1;
    if (couleur === 'rose') {   // filtre de Paul Kellet : chaque octave a la même énergie, comme le vent ou l'air
      b0 = 0.99765 * b0 + w * 0.099046; b1 = 0.963 * b1 + w * 0.2965164; b2 = 0.57 * b2 + w * 1.0526913;
      brut[i] = b0 + b1 + b2 + w * 0.1848;
    } else if (couleur === 'brun') { br = (br + 0.02 * w) / 1.02; brut[i] = br; }   // grave, une rumeur
    else brut[i] = w;
    somme += brut[i];
  }
  const moyenne = somme / brut.length;
  const tampon = ctx.createBuffer(1, n, sr), d = tampon.getChannelData(0);
  for (let i = 0; i < n; i++) d[i] = brut[i] - moyenne;
  for (let i = 0; i < fondu; i++) {   // raccord de boucle : le début reprend en douceur la suite de la fin
    const x = i / fondu;
    d[i] = (brut[i] - moyenne) * Math.sqrt(x) + (brut[n + i] - moyenne) * Math.sqrt(1 - x);
  }
  if (couleur !== 'blanc') {   // même niveau moyen pour tous les fonds (0,25), pour régler leurs niveaux simplement
    let e = 0; for (let i = 0; i < n; i++) e += d[i] * d[i];
    const k = 0.25 / Math.sqrt(e / n || 1);
    for (let i = 0; i < n; i++) d[i] = clamp(d[i] * k, -1, 1);
  }
  return tampon;
}

// Réponse d'une salle (ce que l'on entend après un claquement de mains), calculée : quelques premiers échos sur le sol,
// le plafond et les murs, puis une queue de bruit qui s'éteint. Sa durée vient de la formule de Sabine (volume de la
// salle / surface × absorption) ; les aigus s'éteignent plus vite que les graves, plus encore sur la brique et le bois.
function fabriquerReponse(ctx, p) {
  const m = MATIERES_SON[p.materiau] ?? MATIERES_SON.enduit;
  const L = p.largeur, W = p.profondeur, H = p.hauteur;
  const volume = L * W * H, surface = 2 * (L * W + L * H + W * H);
  const rt = clamp(0.161 * volume / (surface * m.a), 0.4, 3.4);   // temps pour perdre 60 dB, en secondes
  const sr = ctx.sampleRate, n = Math.ceil(sr * Math.min(4, rt * 1.1 + 0.08));
  const ir = ctx.createBuffer(2, n, sr);
  const fHaut = 3500 + 8500 * m.clair, fBas = 350 + 2800 * m.clair ** 1.5;
  const amorti = Math.log(fHaut / fBas) / rt;   // la coupure des aigus descend de fHaut à fBas pendant la réverbération
  const debut = Math.floor(p.predelai * sr), baisse = Math.exp(-6.91 / (rt * sr)), montee = Math.max(1, p.montee * sr);
  // premiers échos, l'auditeur un peu décentré (sinon les deux murs répondent en même temps) : chemin en plus (m),
  // part dans l'oreille gauche, part dans l'oreille droite, nombre de rebonds
  const echos = [[3.2, 1, 1, 1], [2 * (H - 1.6), 0.9, 0.9, 1], [0.8 * L, 1, 0.55, 1], [1.2 * L, 0.55, 1, 1],
                 [0.9 * W, 0.8, 0.8, 1], [1.1 * W, 0.8, 0.8, 1], [2 * H, 0.6, 0.6, 2], [2 * L, 0.5, 0.5, 2], [2 * W, 0.5, 0.5, 2]];
  const rebond = Math.sqrt(1 - m.a);
  for (let c = 0; c < 2; c++) {
    const d = ir.getChannelData(c);
    let y = 0, k = 1, env = 1;
    for (let i = debut; i < n; i++) {
      const j = i - debut;
      if ((j & 31) === 0) k = 1 - Math.exp(-2 * Math.PI * fHaut * Math.exp(-amorti * j / sr) / sr);
      y += k * (Math.random() * 2 - 1 - y);
      d[i] = y * env * Math.min(1, j / montee);
      env *= baisse;
    }
    for (const [chemin, gauche, droite, fois] of echos) {
      const i = Math.round(chemin / 343 * sr);
      if (i < 1 || i >= n - 1) continue;
      const a = 2.2 * (c === 0 ? gauche : droite) * rebond ** fois / (1 + chemin / 4) * (0.9 + Math.random() * 0.2);
      d[i - 1] += a * 0.25; d[i] += a * 0.5; d[i + 1] += a * 0.25;   // un écho un peu adouci, pas un clic
    }
    const fin = Math.min(n, Math.round(sr * 0.08));   // la fin fondue : pas de coupure nette
    for (let i = 0; i < fin; i++) d[n - 1 - i] *= i / fin;
  }
  return { ir, rt };
}

// Un pas : le talon (coup sourd + claquement filtré), la pointe un instant après, le grain de la semelle, parfois une
// latte qui grince. Chaque pas varie un peu (hauteur, force, place gauche-droite) : un pas répété à l'identique
// sonne « machine ». Renvoie les sources (à arrêter) et les nœuds (à débrancher après).
function jouerPas(ctx, bruit, sec, envoi, s, force, t, cote, grincer) {
  const noeuds = [], sources = [];
  const garder = n => { noeuds.push(n); return n; };
  const filtre = (type, f, q = 0.7, gain = 0) => {
    const b = garder(ctx.createBiquadFilter());
    b.type = type; b.frequency.value = f; b.Q.value = q; b.gain.value = gain;
    return b;
  };
  // enveloppe sans clic : part de 0, monte en 1 à 4 ms, retombe en douceur vers 0
  const enveloppe = (crete, attaque, duree, quand) => {
    const g = garder(ctx.createGain());
    g.gain.setValueAtTime(0, quand);
    g.gain.linearRampToValueAtTime(crete, quand + attaque);
    g.gain.setTargetAtTime(0, quand + attaque, duree / 4);
    return g;
  };
  const f = clamp(force, 0, 1.6), hauteur = 1 + (Math.random() * 2 - 1) * 0.06;
  const voix = garder(ctx.createGain());
  voix.gain.value = f * (0.82 + Math.random() * 0.18);
  let tete = voix;
  if (ctx.createStereoPanner) {   // pied gauche, pied droit : à peine décalés, comme sous soi
    const p = garder(ctx.createStereoPanner());
    p.pan.value = clamp(cote * 0.14 + (Math.random() - 0.5) * 0.06, -1, 1);
    voix.connect(p); tete = p;
  }
  if (sec) tete.connect(sec);
  if (envoi) tete.connect(envoi);
  const aigus = Math.min(16000, s.aigus * (0.75 + 0.25 * f));   // un pas appuyé (en courant) est un peu plus clair

  // 1. le talon : un coup sourd qui descend un peu (le corps et le sol qui encaissent)
  const [f0, gCorps, dCorps] = s.corps;
  const osc = ctx.createOscillator(); sources.push(osc);
  osc.frequency.setValueAtTime(f0 * hauteur, t);
  osc.frequency.exponentialRampToValueAtTime(f0 * hauteur * 0.6, t + dCorps * 1.5);
  osc.connect(enveloppe(gCorps, 0.004, dCorps, t)).connect(voix);
  osc.start(t);

  // 2. la semelle qui claque : un souffle bref, filtré selon la matière
  const contact = (quand, ratio, niveau, duree, avecCaisse) => {
    const src = ctx.createBufferSource(); src.buffer = bruit; sources.push(src);
    const chaine = [filtre('highpass', 150), filtre('bandpass', s.contact[0] * hauteur * ratio, s.contact[1])];
    if (avecCaisse && s.resonance) chaine.push(filtre('peaking', s.resonance[0] * hauteur, s.resonance[2], s.resonance[1]));
    chaine.push(filtre('lowpass', aigus), enveloppe(niveau, 0.0015, duree, quand));
    let n = src;
    for (const b of chaine) { n.connect(b); n = b; }
    n.connect(voix);
    src.start(quand, Math.random() * (bruit.duration - 0.4));   // un autre morceau de bruit à chaque fois
  };
  contact(t, 1, s.contact[2], s.contact[3], true);

  // 3. la pointe du pied, un instant après (plus vite en courant), plus faible et un peu plus aiguë
  const tp = t + s.pointe[0] * (0.85 + Math.random() * 0.3) / Math.max(0.8, f);
  contact(tp, 1.15, s.contact[2] * s.pointe[1], s.contact[3] * 0.8, false);

  // 4. le grain sous la semelle (pierre, béton) : un frottement à peine audible
  if (s.frottement[0] > 0) {
    const src = ctx.createBufferSource(); src.buffer = bruit; sources.push(src);
    const chaine = [filtre('bandpass', 2600 * hauteur, 0.6), filtre('lowpass', aigus),
                    enveloppe(s.frottement[0], 0.012, s.frottement[1], t + 0.012)];
    let n = src;
    for (const b of chaine) { n.connect(b); n = b; }
    n.connect(voix);
    src.start(t + 0.012, Math.random() * (bruit.duration - 0.4));
  }

  // fin : chaque enveloppe est retombée à -80 dB environ, on peut tout arrêter sans clic
  let fin = Math.max(tp + s.contact[3] * 2.5, t + dCorps * 2.5, t + 0.012 + s.frottement[1] * 2.5) + 0.05;
  // 5. une latte qui grince : une suite de petits accrocs (bois qui frotte), pas une note
  if (grincer) {
    const tg = t + 0.03, duree = 0.16 + Math.random() * 0.24;
    const points = 14, courbe = new Float32Array(points);
    let fr = 28 + Math.random() * 22;
    for (let i = 0; i < points; i++) { fr = clamp(fr + (Math.random() - 0.45) * 12, 20, 85); courbe[i] = fr; }
    const scie = ctx.createOscillator(); scie.type = 'sawtooth'; sources.push(scie);
    scie.frequency.value = courbe[0];
    scie.frequency.setValueCurveAtTime(courbe, tg, duree);
    const g = garder(ctx.createGain());
    g.gain.setValueAtTime(0, tg);
    g.gain.linearRampToValueAtTime(1.1, tg + 0.05);   // ≈ 8 dB sous le pas : on l'entend, sans sursauter
    g.gain.setTargetAtTime(0, tg + duree * 0.65, duree * 0.1);
    const centre = 600 + Math.random() * 500;
    for (const [mult, q, niv] of [[1, 6, 1], [2.3, 9, 0.5]]) {
      const b = filtre('bandpass', centre * mult, q), k = garder(ctx.createGain());
      k.gain.value = niv;
      scie.connect(b); b.connect(k); k.connect(g);
    }
    g.connect(voix);
    scie.start(tg);
    fin = Math.max(fin, tg + duree * 1.5 + 0.05);
  }
  for (const src of sources) src.stop(fin);
  return { sources, noeuds };
}

// Le moteur de son de la visite. Rien ne se fait avant unlock() (les navigateurs refusent le son avant un geste).
// options.contexte : un OfflineAudioContext, pour mesurer les niveaux sans haut-parleur (page d'essai) ;
// options.grince : forcer la chance de grincement (1 = à chaque pas), pour l'essai.
export function createAudio(options = {}) {
  let ctx = options.contexte ?? null;
  const horsLigne = !!ctx && typeof OfflineAudioContext !== 'undefined' && ctx instanceof OfflineAudioContext;
  let graphe = null, actif = true, volume = 0.7, salle = null, infoSalle = null, voulue = null;
  let cote = 1, actives = 0, dernierGrince = -99, ambiance = null, minuterieEcho = 0;
  const reverbs = [];          // réverbérations branchées (la salle actuelle en dernier, les autres s'effacent)
  const reponses = new Map();  // réponses de salle déjà calculées

  const gainVoulu = () => (actif ? volume * volume : 0);   // au carré : le curseur de volume paraît plus régulier
  const pret = () => graphe && actif && (horsLigne || (ctx.state === 'running' && !document.hidden));

  // Le circuit, une fois : pas (secs) + réverbération de la salle + fond sonore → limiteur → volume → haut-parleurs.
  // Le limiteur évite toute saturation, même si beaucoup de sons tombent en même temps.
  function construire() {
    if (graphe) return true;
    if (!ctx) {
      const AC = window.AudioContext || window.webkitAudioContext;
      if (!AC) return false;
      try { ctx = new AC({ latencyHint: 'interactive' }); } catch { return false; }
    }
    const bus = ctx.createGain();
    const limiteur = ctx.createDynamicsCompressor();
    limiteur.threshold.value = -8; limiteur.knee.value = 6; limiteur.ratio.value = 12;
    limiteur.attack.value = 0.002; limiteur.release.value = 0.2;
    const maitre = ctx.createGain(); maitre.gain.value = gainVoulu();
    bus.connect(limiteur); limiteur.connect(maitre); maitre.connect(ctx.destination);
    const pas = ctx.createGain(); pas.gain.value = 0.5; pas.connect(bus);
    const envoi = ctx.createGain();   // vers la réverbération de la salle
    const lointain = ctx.createBiquadFilter(); lointain.type = 'lowpass'; lointain.frequency.value = 900;
    const lointainNiveau = ctx.createGain(); lointainNiveau.gain.value = 0.4;
    lointain.connect(lointainNiveau); lointainNiveau.connect(envoi);
    const fond = ctx.createGain(); fond.connect(bus);
    graphe = { bus, limiteur, maitre, pas, envoi, lointain, fond,
               bruits: { blanc: fabriquerBruit(ctx, 1, 'blanc'), rose: fabriquerBruit(ctx, 6, 'rose'), brun: fabriquerBruit(ctx, 6, 'brun') } };
    if (!horsLigne) {   // onglet caché : on coupe tout (batterie), on reprend au retour
      document.addEventListener('visibilitychange', () => {
        if (document.hidden) { if (ctx.state === 'running') ctx.suspend().catch(() => {}); }
        else if (actif && ctx.state === 'suspended') ctx.resume().catch(() => {});
      });
    }
    if (voulue) changerSalle(voulue.id, voulue.dims);
    return true;
  }

  // Le fond sonore d'une salle : des bruits en boucle, filtrés, qui ondulent ; arrivée et départ en fondu
  function demarrerAmbiance(id, premier) {
    const recette = AMBIANCES[id] ?? AMBIANCES.hall, t = ctx.currentTime;
    const sortie = ctx.createGain(); sortie.gain.value = 0; sortie.connect(graphe.fond);
    const noeuds = [sortie], sources = [];
    const ondulation = (param, vitesse, profondeur) => {   // deux lentes ondulations, sans cycle qui revient
      for (const [v, part] of [[vitesse, 0.6], [vitesse * 1.73, 0.4]]) {
        const lfo = ctx.createOscillator(), k = ctx.createGain();
        lfo.frequency.value = v; k.gain.value = profondeur * part;
        lfo.connect(k); k.connect(param);
        lfo.start(t); sources.push(lfo); noeuds.push(k);
      }
    };
    for (const couche of recette) {
      const src = ctx.createBufferSource(); src.buffer = graphe.bruits[couche.bruit]; src.loop = true;
      let n = src;
      for (const [type, fr, q = 0.7] of couche.filtres) {
        const b = ctx.createBiquadFilter(); b.type = type; b.frequency.value = fr; b.Q.value = q;
        n.connect(b); n = b; noeuds.push(b);
        if (couche.balayage && type === 'bandpass') ondulation(b.frequency, couche.houle?.[0] ?? 0.05, Math.min(couche.balayage, fr * 0.6));
      }
      const g = ctx.createGain(); g.gain.value = couche.niveau; noeuds.push(g);
      n.connect(g); g.connect(sortie);
      if (couche.houle) ondulation(g.gain, couche.houle[0], couche.niveau * couche.houle[1]);
      src.start(t, Math.random() * src.buffer.duration);
      sources.push(src);
    }
    sortie.gain.setTargetAtTime(1, t, premier ? 0.6 : 0.5);
    return {
      arreter() {
        const t2 = ctx.currentTime;
        sortie.gain.cancelScheduledValues(t2);
        sortie.gain.setValueAtTime(sortie.gain.value, t2);
        sortie.gain.setTargetAtTime(0, t2, 0.4);
        setTimeout(() => {
          for (const s of sources) { try { s.stop(); } catch { /* déjà arrêtée */ } s.disconnect(); }
          for (const nd of noeuds) nd.disconnect();
        }, 3000);
      },
    };
  }

  // Couvent : de temps en temps, deux à quatre pas au loin, qu'on n'entend que par l'écho de la voûte
  function planifierEchos(id) {
    clearTimeout(minuterieEcho);
    if (!ECHOS[id] || horsLigne) return;
    const suivant = () => {
      minuterieEcho = setTimeout(() => {
        if (salle !== id) return;
        if (pret() && actives < 4) {
          const combien = 2 + Math.floor(Math.random() * 3), ecart = 0.5 + Math.random() * 0.15;
          for (let i = 0; i < combien; i++) {
            lancer(SURFACES.pierre, 0.6 - i * 0.06, ctx.currentTime + 0.05 + i * ecart, null, graphe.lointain, false);
          }
        }
        suivant();
      }, 9000 + Math.random() * 14000);
    };
    suivant();
  }

  function oublierReverb(r) {
    const i = reverbs.indexOf(r);
    if (i >= 0) reverbs.splice(i, 1);
    try { graphe.envoi.disconnect(r.conv); } catch { /* déjà fait */ }
    r.conv.disconnect(); r.g.disconnect();
  }

  // Nouvelle salle : sa réverbération et son fond sonore arrivent en fondu, ceux de l'ancienne s'effacent
  function changerSalle(id, dims = {}) {
    const base = SALLES_SON[id] ?? SALLE_INCONNUE;
    const p = { ...base };
    for (const k of ['largeur', 'profondeur', 'hauteur']) if (Number.isFinite(dims[k]) && dims[k] > 0.5) p[k] = dims[k];
    if (dims.materiau && MATIERES_SON[dims.materiau]) p.materiau = dims.materiau;
    const cle = `${id}|${p.largeur}|${p.profondeur}|${p.hauteur}|${p.materiau}`;
    let rep = reponses.get(cle);
    if (!rep) { rep = fabriquerReponse(ctx, p); reponses.set(cle, rep); }
    const premier = salle === null, t = ctx.currentTime;
    const conv = ctx.createConvolver(); conv.buffer = rep.ir;   // normalize (par défaut) : même force dans toutes les salles
    const g = ctx.createGain();
    graphe.envoi.connect(conv); conv.connect(g); g.connect(graphe.bus);
    if (premier) g.gain.value = p.humide;
    else { g.gain.value = 0; g.gain.setTargetAtTime(p.humide, t, 0.35); }
    for (const ancien of reverbs) {
      ancien.g.gain.cancelScheduledValues(t);
      ancien.g.gain.setValueAtTime(ancien.g.gain.value, t);
      ancien.g.gain.setTargetAtTime(0, t, 0.3);
      clearTimeout(ancien.minuterie);
      ancien.minuterie = setTimeout(() => oublierReverb(ancien), 4000);   // après sa queue de réverbération
    }
    reverbs.push({ conv, g, minuterie: 0 });
    ambiance?.arreter();
    ambiance = demarrerAmbiance(id, premier);
    salle = id; infoSalle = { id, rt: Math.round(rep.rt * 100) / 100, surface: p.sol };
    planifierEchos(id);
  }

  function lancer(s, force, t, sec, envoi, grincer) {
    const v = jouerPas(ctx, graphe.bruits.blanc, sec, envoi, s, force, t, (cote = -cote), grincer);
    actives++;
    v.sources[0].onended = () => {   // tout s'arrête au même instant : on débranche tout d'un coup
      actives--;
      for (const src of v.sources) src.disconnect();
      for (const n of v.noeuds) n.disconnect();
    };
  }

  return {
    // À appeler au premier geste du visiteur (clic, touche, doigt) ; sans frais si on l'appelle à chaque geste
    unlock() {
      if (!construire()) return;
      if (!horsLigne && actif && ctx.state !== 'running' && !document.hidden) {
        ctx.resume().catch(() => {});
        try {   // iPhone : un son vide joué pendant le geste « réveille » le son
          const vide = ctx.createBufferSource(); vide.buffer = ctx.createBuffer(1, 1, ctx.sampleRate);
          vide.connect(ctx.destination); vide.onended = () => vide.disconnect(); vide.start();
        } catch { /* pas grave */ }
      }
    },
    // Un pas. surface : 'parquet' | 'pierre' | 'beton' | 'carrelage' | 'marbre' | 'bois' (vide = le sol de la salle).
    // strength : 1 en marchant, jusqu'à 1,6 en courant (plus fort, plus clair). quand : retard en secondes (facultatif).
    // Renvoie false si le son n'est pas prêt (avant unlock, coupé, onglet caché) : rien n'est mis en attente.
    footstep(surface, strength = 1, quand = 0) {
      if (!pret() || actives >= 8) return false;   // au plus 8 pas qui sonnent en même temps
      const s = SURFACES[surface] ?? SURFACES[infoSalle?.surface] ?? SURFACES.parquet;
      const t = ctx.currentTime + 0.006 + Math.random() * 0.012 + Math.max(0, quand);   // un pas jamais pile à l'heure
      const chance = options.grince ?? s.grince;
      const grincer = chance >= 1 || (chance > 0 && Math.random() < chance && t - dernierGrince > 6);
      if (grincer) dernierGrince = t;
      lancer(s, strength, t, graphe.pas, graphe.envoi, grincer);
      return true;
    },
    // La salle où l'on est : id de plan.json ('hall', 'couvent'…) ; mesures facultatives (en mètres) et matière des
    // murs ('pierre', 'brique', 'chaux', 'enduit', 'rouge', 'bois', 'marbre', 'beton'). Sans effet si rien ne change.
    setRoom(id, { largeur, profondeur, hauteur, materiau } = {}) {
      if (!id) return;
      const dims = { largeur, profondeur, hauteur, materiau };
      if (!graphe) { voulue = { id, dims }; return; }
      if (id !== salle) changerSalle(id, dims);
    },
    // Son allumé ou coupé (en fondu). Coupé : le moteur se met en pause, il ne coûte plus rien.
    setEnabled(on) {
      actif = !!on;
      if (!graphe) return;
      graphe.maitre.gain.setTargetAtTime(gainVoulu(), ctx.currentTime, 0.04);
      if (horsLigne) return;
      if (actif) { if (ctx.state === 'suspended' && !document.hidden) ctx.resume().catch(() => {}); }
      else setTimeout(() => { if (!actif && ctx.state === 'running') ctx.suspend().catch(() => {}); }, 400);
    },
    // Volume de 0 à 1
    setVolume(v) {
      volume = clamp(Number(v) || 0, 0, 1);
      if (graphe) graphe.maitre.gain.setTargetAtTime(gainVoulu(), ctx.currentTime, 0.04);
    },
    surfaceOf,
    get room() { return infoSalle; },        // { id, rt (durée de réverbération en s), surface (sol de la salle) }
    get actives() { return actives; },       // pas en train de sonner (pour l'essai)
    get context() { return ctx; },
  };
}

// Pour galerie.js : un pas tombe quand la phase du balancement de la caméra passe un multiple de π
// (galerie.js : bob += dt * vitesse * 3,9 ; la caméra est au plus bas quand sin(bob) = 0, le pied touche le sol)
export function stepDue(prevPhase, phase) {
  return Math.floor(phase / Math.PI) !== Math.floor(prevPhase / Math.PI);
}

// ============================================================================================================
// Manette
// ============================================================================================================

// Zone morte ronde : sous 15 % de course, le stick est au repos (il ne revient jamais pile au centre) ; au-delà, on
// repart de 0 pour ne pas sauter d'un coup à 15 %
function zoneMorte(x, y, seuil = 0.15) {
  const m = Math.hypot(x, y);
  if (m < seuil) return { x: 0, y: 0 };
  const k = Math.min(1, (m - seuil) / (1 - seuil)) / m;
  return { x: x * k || 0, y: y * k || 0 };   // || 0 : pas de « -0 »
}
const dejaPresses = new Map();   // boutons de l'image précédente, par manette (pour ne réagir qu'à l'appui)

// La manette, à lire à chaque image. null si aucune manette (elle n'apparaît qu'après un premier bouton pressé).
// move : x à droite, y en avant (positif = avancer) ; look : x à droite, y vers le haut (pousser le stick droit vers
// l'avant = regarder en haut ; REGLAGES.inverserY s'applique après), courbe au carré pour viser finement ;
// run : stick gauche enfoncé ou gâchette gauche (tenu) ; action (A), back (B), menu (Start) : vrais seulement à
// l'image de l'appui.
export function readGamepad() {
  let pads = [];
  try { pads = navigator.getGamepads ? Array.from(navigator.getGamepads()) : []; } catch { return null; }
  const pad = pads.find(p => p && p.connected && p.mapping === 'standard') ?? pads.find(p => p && p.connected);
  if (!pad) { dejaPresses.clear(); return null; }
  const axe = i => { const v = pad.axes[i]; return Number.isFinite(v) ? v : 0; };
  const bouton = i => { const b = pad.buttons[i]; return !!b && (b.pressed || b.value > 0.5); };
  const move = zoneMorte(axe(0), -axe(1));
  const brut = pad.axes.length >= 4 ? zoneMorte(axe(2), -axe(3)) : { x: 0, y: 0 };
  const m = Math.hypot(brut.x, brut.y);
  const look = { x: brut.x * m, y: brut.y * m };
  const etat = { a: bouton(0), b: bouton(1), start: bouton(9) };
  const avant = dejaPresses.get(pad.index) ?? etat;   // manette qui vient d'apparaître : rien ne « vient » d'être pressé
  dejaPresses.set(pad.index, etat);
  return {
    move, look,
    run: bouton(10) || (pad.buttons[6]?.value ?? 0) > 0.4,
    action: etat.a && !avant.a,
    back: etat.b && !avant.b,
    menu: etat.start && !avant.start,
  };
}

// ============================================================================================================
// Champ de vision en courant
// ============================================================================================================

// Degrés à ajouter au champ de vision : rien en marchant, jusqu'à +4° à pleine course, en douceur.
// speedRatio = vitesse / vitesse de course (galerie.js : vitesse / RUN ; la marche fait ≈ 0,5).
export function fovKick(speedRatio) {
  const t = clamp((speedRatio - 0.55) / 0.45, 0, 1);
  return 4 * t * t * (3 - 2 * t);
}

// ============================================================================================================
// Réglages
// ============================================================================================================

const CLE = 'galerie-reglages';
const DEFAUTS = { sensibilite: 1, inverserY: false, son: true, volume: 0.7 };
function lireReglages() {
  let brut = null;
  try { brut = JSON.parse(localStorage.getItem(CLE) || 'null'); } catch { brut = null; }
  const r = { ...DEFAUTS };
  if (brut && typeof brut === 'object') {   // valeurs vérifiées : un réglage abîmé ne casse pas la visite
    if (Number.isFinite(brut.sensibilite)) r.sensibilite = clamp(brut.sensibilite, 0.4, 2.5);
    if (typeof brut.inverserY === 'boolean') r.inverserY = brut.inverserY;
    if (typeof brut.son === 'boolean') r.son = brut.son;
    if (Number.isFinite(brut.volume)) r.volume = clamp(brut.volume, 0, 1);
  }
  return r;
}
function ecrireReglages() {
  const { sensibilite, inverserY, son, volume } = REGLAGES;
  try { localStorage.setItem(CLE, JSON.stringify({ sensibilite, inverserY, son, volume })); }
  catch { /* navigation privée : gardé pour cette visite seulement */ }
}

// Les réglages du visiteur, lus dès le chargement (gardés dans le navigateur) :
// sensibilite (0,4 à 2,5, multiplie la vitesse du regard), inverserY, son, volume (0 à 1),
// qualite ('bas' | 'moyen' | 'haut', celle de qualite.js), pleinEcran (état actuel, pas gardé).
export const REGLAGES = { ...lireReglages(), qualite: NIVEAU, pleinEcran: false };

const STYLE = `
.jeu-reglages{position:fixed;top:max(16px,env(safe-area-inset-top));right:max(16px,env(safe-area-inset-right));z-index:3;pointer-events:none;font:500 13px/1.4 Montserrat,system-ui,sans-serif;color:#1e1e1e;letter-spacing:.01em;transition:opacity .3s}
.jeu-reglages button,.jeu-reglages input{font:inherit;color:inherit}
.jeu-roue{pointer-events:auto;display:grid;place-items:center;width:42px;height:42px;margin:0;padding:0;border:0;border-radius:50%;background:rgba(250,249,246,.86);-webkit-backdrop-filter:blur(12px);backdrop-filter:blur(12px);box-shadow:0 6px 22px rgba(0,0,0,.14);cursor:pointer;transition:background .2s}
.jeu-roue:hover{background:rgba(250,249,246,.96)}
.jeu-roue svg{width:20px;height:20px;transition:transform .5s ease}
.jeu-roue[aria-expanded="true"] svg{transform:rotate(45deg)}
.jeu-panneau{pointer-events:auto;position:absolute;top:52px;right:0;box-sizing:border-box;width:min(300px,calc(100vw - 32px));max-height:calc(100vh - 110px);max-height:calc(100dvh - 110px);overflow:auto;overscroll-behavior:contain;padding:14px 18px 18px;border-radius:18px;background:rgba(250,249,246,.94);-webkit-backdrop-filter:blur(12px);backdrop-filter:blur(12px);box-shadow:0 14px 40px rgba(0,0,0,.2);transform-origin:top right;animation:jeu-ouvre .22s ease-out}
.jeu-panneau[hidden]{display:none}
@keyframes jeu-ouvre{from{opacity:0;transform:translateY(-6px) scale(.97)}}
.jeu-tete{display:flex;align-items:center;justify-content:space-between;margin:0 -6px 2px 0}
.jeu-panneau h2{margin:0;font:500 1.4rem/1.15 'Cormorant Garamond',Georgia,serif;letter-spacing:.01em}
.jeu-reglages .jeu-fermer{width:32px;height:32px;padding:0;border:0;border-radius:50%;background:transparent;font:300 22px/1 Montserrat,system-ui,sans-serif;cursor:pointer}
.jeu-reglages .jeu-fermer:hover{background:rgba(0,0,0,.06)}
.jeu-groupe{margin:16px 0 8px;font-size:.66rem;letter-spacing:.13em;text-transform:uppercase;color:#6b665f}
.jeu-niveaux{display:grid;grid-template-columns:repeat(3,1fr);gap:2px;padding:3px;border-radius:999px;background:rgba(0,0,0,.06)}
.jeu-niveaux button{padding:7px 0;border:0;border-radius:999px;background:transparent;cursor:pointer;transition:background .2s,box-shadow .2s}
.jeu-niveaux button:hover{background:rgba(255,255,255,.55)}
.jeu-niveaux button[aria-pressed="true"]{background:#fff;box-shadow:0 2px 8px rgba(0,0,0,.12);cursor:default}
.jeu-note{margin:6px 2px 0;font-size:.72rem;color:#6b665f}
.jeu-ligne{display:flex;align-items:center;justify-content:space-between;gap:12px;min-height:36px;cursor:pointer}
.jeu-ligne output{font-variant-numeric:tabular-nums;color:#6b665f}
.jeu-curseur{margin:2px 0 4px}
.jeu-curseur .jeu-ligne{min-height:24px;cursor:default}
.jeu-curseur.eteint{opacity:.45}
.jeu-reglages input[type=range]{-webkit-appearance:none;appearance:none;display:block;width:100%;height:24px;margin:0;background:transparent;cursor:pointer;--p:50%}
.jeu-reglages input[type=range]:disabled{cursor:default}
.jeu-reglages input[type=range]::-webkit-slider-runnable-track{height:2px;border-radius:2px;background:linear-gradient(#282828,#282828) 0/var(--p) 100% no-repeat,#d6d1c8}
.jeu-reglages input[type=range]::-webkit-slider-thumb{-webkit-appearance:none;width:16px;height:16px;margin-top:-7px;border:0;border-radius:50%;background:#282828;box-shadow:0 0 0 4px rgba(250,249,246,.94)}
.jeu-reglages input[type=range]::-moz-range-track{height:2px;border-radius:2px;background:#d6d1c8}
.jeu-reglages input[type=range]::-moz-range-progress{height:2px;border-radius:2px;background:#282828}
.jeu-reglages input[type=range]::-moz-range-thumb{width:16px;height:16px;border:0;border-radius:50%;background:#282828;box-shadow:0 0 0 4px rgba(250,249,246,.94)}
.jeu-cache{position:absolute;width:1px;height:1px;margin:0;opacity:0;pointer-events:none}
.jeu-inter{flex:none;position:relative;width:36px;height:20px;border-radius:999px;background:#d6d1c8;transition:background .2s}
.jeu-inter::after{content:"";position:absolute;left:2px;top:2px;width:16px;height:16px;border-radius:50%;background:#fff;box-shadow:0 1px 3px rgba(0,0,0,.25);transition:transform .2s}
.jeu-cache:checked+.jeu-inter{background:#282828}
.jeu-cache:checked+.jeu-inter::after{transform:translateX(16px)}
.jeu-reglages :focus-visible,.jeu-cache:focus-visible+.jeu-inter{outline:2px solid #1e1e1e;outline-offset:2px}
.jeu-reglages input[type=range]:focus-visible{outline-offset:4px;border-radius:4px}
body.playing .jeu-reglages{opacity:.4}
@media (pointer:coarse){.jeu-roue{width:46px;height:46px}.jeu-panneau{top:56px}.jeu-ligne{min-height:44px}.jeu-niveaux button{padding:10px 0}.jeu-reglages input[type=range]{height:32px}.jeu-reglages input[type=range]::-webkit-slider-thumb{width:22px;height:22px;margin-top:-10px}.jeu-reglages input[type=range]::-moz-range-thumb{width:22px;height:22px}}
@media (prefers-reduced-motion:reduce){.jeu-panneau{animation:none}.jeu-roue svg,.jeu-inter,.jeu-inter::after{transition:none}}
`;

// La roue dentée, dessinée ici (8 dents, un trou au centre)
function roueDentee() {
  const points = [];
  for (let k = 0; k < 8; k++) {
    const a = k / 8 * 2 * Math.PI;
    for (const [r, da] of [[7.3, -0.27], [10, -0.16], [10, 0.16], [7.3, 0.27]]) {
      points.push(`${(12 + r * Math.cos(a + da)).toFixed(2)} ${(12 + r * Math.sin(a + da)).toFixed(2)}`);
    }
  }
  const trou = 'M15.3 12a3.3 3.3 0 1 0-6.6 0a3.3 3.3 0 1 0 6.6 0Z';
  return `<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path fill="currentColor" fill-rule="evenodd" d="M${points.join('L')}Z${trou}"/></svg>`;
}

const NOMS_NIVEAUX = { bas: 'Bas', moyen: 'Moyen', haut: 'Haut' };
const nombre = v => v.toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

// Le panneau de réglages : une roue dentée en haut à droite, qui ouvre la qualité de l'image, la sensibilité du regard,
// le regard inversé, le son, le volume et le plein écran. onChange(REGLAGES) à chaque changement ;
// audio (facultatif) : l'objet de createAudio(), branché tout seul sur les réglages du son.
// Renvoie { element, open(), close(), toggle(), isOpen } : galerie.js peut l'ouvrir avec le bouton Start de la manette.
export function createSettings(parent, { onChange, audio } = {}) {
  if (!document.getElementById('jeu-style')) {
    const style = document.createElement('style');
    style.id = 'jeu-style'; style.textContent = STYLE;
    document.head.appendChild(style);
  }
  const hote = parent ?? document.querySelector('.ui') ?? document.body;
  const racine = document.createElement('div');
  racine.className = 'jeu-reglages';
  racine.innerHTML = `
    <button type="button" class="jeu-roue" aria-label="Réglages" title="Réglages" aria-expanded="false" aria-controls="jeu-panneau">${roueDentee()}</button>
    <div class="jeu-panneau" id="jeu-panneau" role="dialog" aria-labelledby="jeu-titre" hidden>
      <div class="jeu-tete"><h2 id="jeu-titre">Réglages</h2><button type="button" class="jeu-fermer" aria-label="Fermer les réglages">×</button></div>
      <p class="jeu-groupe" id="jeu-g-qualite">Qualité de l’image</p>
      <div class="jeu-niveaux" role="group" aria-labelledby="jeu-g-qualite">
        <button type="button" data-niveau="bas">Bas</button><button type="button" data-niveau="moyen">Moyen</button><button type="button" data-niveau="haut">Haut</button>
      </div>
      <p class="jeu-note" id="jeu-note-qualite"></p>
      <p class="jeu-groupe">Commandes</p>
      <div class="jeu-curseur">
        <label class="jeu-ligne" for="jeu-sens"><span>Sensibilité du regard</span><output id="jeu-sens-val" for="jeu-sens"></output></label>
        <input type="range" id="jeu-sens" min="0.4" max="2.5" step="0.05">
      </div>
      <label class="jeu-ligne"><span>Inverser le regard vertical</span><input type="checkbox" class="jeu-cache" id="jeu-inverser" role="switch"><i class="jeu-inter" aria-hidden="true"></i></label>
      <p class="jeu-groupe">Son</p>
      <label class="jeu-ligne"><span>Son</span><input type="checkbox" class="jeu-cache" id="jeu-son" role="switch"><i class="jeu-inter" aria-hidden="true"></i></label>
      <div class="jeu-curseur" id="jeu-volume-bloc">
        <label class="jeu-ligne" for="jeu-volume"><span>Volume</span><output id="jeu-volume-val" for="jeu-volume"></output></label>
        <input type="range" id="jeu-volume" min="0" max="1" step="0.05">
      </div>
      <div id="jeu-ecran">
        <p class="jeu-groupe">Écran</p>
        <label class="jeu-ligne"><span>Plein écran</span><input type="checkbox" class="jeu-cache" id="jeu-plein" role="switch"><i class="jeu-inter" aria-hidden="true"></i></label>
      </div>
    </div>`;
  hote.appendChild(racine);
  const $ = sel => racine.querySelector(sel);
  const roue = $('.jeu-roue'), panneau = $('.jeu-panneau'), note = $('#jeu-note-qualite');
  const sens = $('#jeu-sens'), inverser = $('#jeu-inverser'), son = $('#jeu-son'), vol = $('#jeu-volume'), plein = $('#jeu-plein');

  const notifier = () => { ecrireReglages(); onChange?.(REGLAGES); };
  if (audio) { audio.setEnabled(REGLAGES.son); audio.setVolume(REGLAGES.volume); }

  // Qualité : changer recharge la page (les matières et les effets se préparent au chargement)
  note.textContent = `Actuelle : ${NOMS_NIVEAUX[NIVEAU]} · changer recharge la page`;
  for (const b of racine.querySelectorAll('[data-niveau]')) {
    b.setAttribute('aria-pressed', String(b.dataset.niveau === NIVEAU));
    b.addEventListener('click', () => {
      const niveau = b.dataset.niveau;
      if (niveau === NIVEAU) return;
      REGLAGES.qualite = niveau;
      onChange?.(REGLAGES);
      note.textContent = 'Rechargement…';
      try {   // une qualité forcée dans l'adresse (?qualite=…) passerait avant le choix : on l'enlève
        const u = new URL(location.href);
        if (u.searchParams.has('qualite')) { u.searchParams.delete('qualite'); history.replaceState(history.state, '', u); }
      } catch { /* adresse intouchable : tant pis */ }
      setNiveau(niveau);
    });
  }

  // Curseurs : la barre se remplit jusqu'au pouce (--p), la valeur s'affiche à droite
  const curseur = (input, sortie, cle, format, quand) => {
    const maj = () => {
      input.style.setProperty('--p', `${(input.value - input.min) / (input.max - input.min) * 100}%`);
      sortie.textContent = format(+input.value);
    };
    input.value = String(REGLAGES[cle]); maj();
    input.addEventListener('input', () => { REGLAGES[cle] = +input.value; maj(); quand?.(); notifier(); });
  };
  curseur(sens, $('#jeu-sens-val'), 'sensibilite', nombre);
  curseur(vol, $('#jeu-volume-val'), 'volume', v => `${Math.round(v * 100)} %`, () => audio?.setVolume(REGLAGES.volume));
  const majVolume = () => { vol.disabled = !REGLAGES.son; $('#jeu-volume-bloc').classList.toggle('eteint', !REGLAGES.son); };
  majVolume();

  inverser.checked = REGLAGES.inverserY;
  inverser.addEventListener('change', () => { REGLAGES.inverserY = inverser.checked; notifier(); });
  son.checked = REGLAGES.son;
  son.addEventListener('change', () => {
    REGLAGES.son = son.checked;
    if (audio) { if (REGLAGES.son) audio.unlock(); audio.setEnabled(REGLAGES.son); }   // ce clic compte comme geste
    majVolume(); notifier();
  });

  // Plein écran (absent sur iPhone : la ligne disparaît)
  const ecranPossible = !!(document.fullscreenEnabled || document.webkitFullscreenEnabled);
  const elementPlein = () => document.fullscreenElement || document.webkitFullscreenElement || null;
  $('#jeu-ecran').hidden = !ecranPossible;
  const syncPlein = () => {
    const oui = !!elementPlein();
    plein.checked = oui;
    if (REGLAGES.pleinEcran !== oui) { REGLAGES.pleinEcran = oui; onChange?.(REGLAGES); }
  };
  plein.addEventListener('change', () => {
    const el = document.documentElement;
    try {
      const p = plein.checked
        ? (el.requestFullscreen ? el.requestFullscreen({ navigationUI: 'hide' }) : el.webkitRequestFullscreen?.())
        : (document.exitFullscreen ? document.exitFullscreen() : document.webkitExitFullscreen?.());
      p?.catch?.(syncPlein);   // refusé : l'interrupteur revient à l'état réel
    } catch { syncPlein(); }
  });
  document.addEventListener('fullscreenchange', syncPlein);
  document.addEventListener('webkitfullscreenchange', syncPlein);

  // Ouvrir, fermer
  let ouvert = false;
  function open() {
    if (ouvert) return;
    ouvert = true;
    try { if (document.pointerLockElement) document.exitPointerLock(); } catch { /* rien à rendre */ }   // la souris revient
    panneau.hidden = false;
    roue.setAttribute('aria-expanded', 'true');
    (racine.querySelector('[data-niveau][aria-pressed="true"]') ?? sens).focus({ preventScroll: true });
  }
  function close(rendreFocus = false) {
    if (!ouvert) return;
    ouvert = false;
    if (!rendreFocus && racine.contains(document.activeElement)) document.activeElement.blur();
    panneau.hidden = true;
    roue.setAttribute('aria-expanded', 'false');
    if (rendreFocus) roue.focus({ preventScroll: true });
  }
  roue.addEventListener('click', () => (ouvert ? close(true) : open()));
  $('.jeu-fermer').addEventListener('click', () => close(true));
  roue.addEventListener('keydown', e => { if (e.key === 'Escape' && ouvert) { e.preventDefault(); close(true); } });
  panneau.addEventListener('keydown', e => {
    if (e.key === 'Escape') { e.preventDefault(); close(true); }
    e.stopPropagation();   // les touches dans le panneau (flèches d'un curseur…) ne font pas marcher le visiteur
  });
  // Un clic ailleurs ferme le panneau, sans être retenu : il arrive aussi à la 3D
  document.addEventListener('pointerdown', e => { if (ouvert && !racine.contains(e.target)) close(false); }, true);

  return { element: racine, open, close, toggle: () => (ouvert ? close(true) : open()), get isOpen() { return ouvert; } };
}
