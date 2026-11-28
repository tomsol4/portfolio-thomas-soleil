// La galerie des projets personnels en 3D : un hall et une salle par série, lumière calculée dans Blender.
// Fichiers produits par scripts/musee_3d.py (mode « cuisson ») : musee.glb, plan.json,
// lumiere/*.png (cartes de lumière), matieres/*.webp (textures). Moteur 3D : three.js 0.169 (lib/, licence MIT).
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { addPatch, preparerMatieres, roomMaterial, objectShading, objectMaps } from './materiaux.js';   // murs, sols, cadres « de jeu »
import { Q } from './qualite.js';
import { effets, EFFETS, PIXELS } from './effets.js';   // effets d'image : ombres de contact, halo, netteté…

const IMG = '../../images/optimized/';
const EYE = 1.6;
const WALK = 1.7, RUN = 3.2;   // vitesses de marche et de course (m/s, Maj enfoncée)
const PHOTO_GAIN = 1;   // éclat des photos là où elles sont le plus éclairées (1 = leurs vraies valeurs)
const $ = id => document.getElementById(id);
const phone = matchMedia('(max-width: 800px)').matches;
// Écran tactile (téléphone, tablette) : manette à l'écran. Pas sur un ordinateur tactile à grand écran (souris).
const touch = matchMedia('(pointer: coarse)').matches || (navigator.maxTouchPoints > 0 && matchMedia('(max-width: 1024px)').matches);
const SHARP = phone ? 960 : 1600;   // largeur des photos de la salle où l'on est

// Un cadre par salle : baguette (largeur en m), couleur unie ou bois (texture), passe-partout (couleur, marge)
const FRAMES = {
  hall: { bar: 0.024, couleur: [0.02, 0.019, 0.018], rugosite: 0.38, reflets: 0.35 },
  couvent: { bar: 0.055, bois: 'wood_table_worn', teinte: [0.3, 0.25, 0.22], rugosite: 0.6, reflets: 0.3, passe: [0.86, 0.835, 0.78] },
  toulouse: { bar: 0.016, couleur: [0.012, 0.012, 0.012], rugosite: 0.45, reflets: 0.3, marge: 0.1 },
  garde: { bar: 0.04, bois: 'oak_wood_planks', teinte: [0.78, 0.7, 0.62], rugosite: 0.6, reflets: 0.3 },
  messe: { bar: 0.05, couleur: [0.56, 0.38, 0.13], metal: 0.8, rugosite: 0.3, reflets: 1, passe: [0.88, 0.86, 0.8] },
  montagne: { bar: 0.035, bois: 'hinoki_planks', teinte: [1.05, 1.0, 0.95], rugosite: 0.65, reflets: 0.25 },
};

// ---------- Rendu ----------
const canvas = document.createElement('canvas');
canvas.setAttribute('role', 'img');
canvas.setAttribute('aria-label', 'Visite en 3D de la galerie de photographies');
canvas.tabIndex = -1;   // reçoit le focus quand la vue en grand se ferme
document.body.prepend(canvas);
// Comme sur le reste du site : pas de menu « Enregistrer l'image » ni de glisser-déposer des photos
for (const type of ['contextmenu', 'dragstart']) {
  document.addEventListener(type, e => { if (e.target instanceof Element && e.target.closest('canvas, .viewer figure')) e.preventDefault(); });
}
let renderer;
try {
  // avec les effets d'image, les bords sont lissés dans leur image à eux (pas besoin de lisser l'écran)
  renderer = new THREE.WebGLRenderer({ canvas, antialias: !EFFETS, powerPreference: 'high-performance' });
} catch {
  $('loading-text').innerHTML = 'Cet appareil ne peut pas afficher la galerie en 3D.<br><a href="../index.html">Voir les photos</a>';
  throw new Error('WebGL indisponible');
}
renderer.setPixelRatio(PIXELS);   // selon la qualité (qualite.js)
// Couleurs : la courbe de tons de Blender (lue dans plan.json, voir toneCurve), comme dans les rendus validés
renderer.toneMapping = THREE.CustomToneMapping;
renderer.toneMappingExposure = Number(new URLSearchParams(location.search).get('expo') ?? 1);
const maxAniso = renderer.capabilities.getMaxAnisotropy();
const scene = new THREE.Scene();
// Le ciel, vu par les fenêtres : un dégradé du bleu (en haut) au clair (à l'horizon)
function sky() {
  const c = document.createElement('canvas'); c.width = 8; c.height = 256;
  const g = c.getContext('2d'), grad = g.createLinearGradient(0, 0, 0, 256);
  grad.addColorStop(0, '#4f86cf'); grad.addColorStop(0.42, '#9cc0ea'); grad.addColorStop(0.5, '#e4ebf2');
  grad.addColorStop(0.53, '#b8b2a3'); grad.addColorStop(1, '#7d7766');
  g.fillStyle = grad; g.fillRect(0, 0, 8, 256);
  const t = new THREE.CanvasTexture(c);
  t.mapping = THREE.EquirectangularReflectionMapping;
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}
scene.background = sky();
scene.backgroundIntensity = 1.5;
const camera = new THREE.PerspectiveCamera(60, 1, 0.05, 80);
camera.rotation.order = 'YXZ';
const post = effets(renderer, scene, camera);   // post.render() dessine une image (avec ou sans effets)
window.__galerie = { THREE, scene, renderer, camera, effets: post, render: () => post.render() };

let PLAN, ROOMS, ART, OBSTACLES = [];
const linear = c => new THREE.Color().setRGB(c[0], c[1], c[2], THREE.LinearSRGBColorSpace);

// La courbe de tons de Blender (vue AgX, look « Medium High Contrast ») : plan.json → tonalite, gris tels que Blender
// les affiche. Même chemin que l'AgX de three.js (matrices d'entrée et de sortie), seule la courbe change :
// les gris sortent identiques aux rendus, les couleurs suivent l'AgX de three.js.
function toneCurve({ ev: [evMin, evMax], valeurs }) {
  const toLinear = v => (v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4);
  const table = valeurs.map(v => (toLinear(v) ** (1 / 2.2)).toFixed(6));
  const n = table.length, f = x => x.toFixed(6);
  THREE.ShaderChunk.tonemapping_pars_fragment = THREE.ShaderChunk.tonemapping_pars_fragment.replace(
    'vec3 CustomToneMapping( vec3 color ) { return color; }', `
const float BLENDER_TONES[ ${n} ] = float[ ${n} ]( ${table.join(', ')} );
float blenderTone( float x ) {
	float t = clamp( ( log2( max( x, 1e-10 ) ) - ( ${f(evMin)} ) ) / ${f(evMax - evMin)}, 0.0, 1.0 ) * ${f(n - 1)};
	int i = int( min( floor( t ), ${f(n - 2)} ) );
	return mix( BLENDER_TONES[ i ], BLENDER_TONES[ i + 1 ], t - float( i ) );
}
vec3 CustomToneMapping( vec3 color ) {
	const mat3 inset = mat3( vec3( 0.856627153315983, 0.137318972929847, 0.11189821299995 ), vec3( 0.0951212405381588, 0.761241990602591, 0.0767994186031903 ), vec3( 0.0482516061458583, 0.101439036467562, 0.811302368396859 ) );
	const mat3 outset = mat3( vec3( 1.1271005818144368, - 0.1413297634984383, - 0.14132976349843826 ), vec3( - 0.11060664309660323, 1.157823702216272, - 0.11060664309660294 ), vec3( - 0.016493938717834573, - 0.016493938717834257, 1.2519364065950405 ) );
	color = inset * ( LINEAR_SRGB_TO_LINEAR_REC2020 * ( color * toneMappingExposure ) );
	color = vec3( blenderTone( color.r ), blenderTone( color.g ), blenderTone( color.b ) );
	color = pow( max( vec3( 0.0 ), outset * color ), vec3( 2.2 ) );
	return clamp( LINEAR_REC2020_TO_LINEAR_SRGB * color, 0.0, 1.0 );
}`);
}

// Murs, sols, plafonds, cadres : voir materiaux.js (relief, lumière des projecteurs, reflets brillants)
let DOORS = [];

// Reflets : la photo à 360° de chaque salle est rapportée sur les murs de la salle (une boîte), pour que les reflets
// tombent au bon endroit et ne glissent pas avec le visiteur. Elle ne sert qu'aux reflets : la lumière diffuse vient
// déjà des cartes de Blender (sans ça, elle compterait deux fois et délaverait les sols).
const BOX_PARS = `
uniform vec3 boxMin;
uniform vec3 boxMax;
uniform vec3 boxProbe;
varying vec3 vBoxWorld;
vec3 boxProject( vec3 dir ) {
	vec3 d = normalize( dir );
	vec3 far = max( ( boxMax - vBoxWorld ) / d, ( boxMin - vBoxWorld ) / d );
	return vBoxWorld + d * min( min( far.x, far.y ), far.z ) - boxProbe;
}
`;
function boxReflections(material, room) {
  const [x0, x1, z0, z1] = room.rect;
  const uniforms = {
    boxMin: { value: new THREE.Vector3(x0, 0, z0) },
    boxMax: { value: new THREE.Vector3(x1, room.hauteur ?? 5, z1) },
    boxProbe: { value: new THREE.Vector3((x0 + x1) / 2, 1.5, (z0 + z1) / 2) },
  };
  addPatch(material, 'box', shader => {
    Object.assign(shader.uniforms, uniforms);
    shader.vertexShader = shader.vertexShader
      .replace('#include <common>', '#include <common>\nvarying vec3 vBoxWorld;')
      .replace('#include <worldpos_vertex>', '#include <worldpos_vertex>\nvBoxWorld = ( modelMatrix * vec4( transformed, 1.0 ) ).xyz;');
    shader.fragmentShader = shader.fragmentShader
      .replace('#include <envmap_physical_pars_fragment>', BOX_PARS + THREE.ShaderChunk.envmap_physical_pars_fragment.replace(
        'vec4 envMapColor = textureCubeUV( envMap, envMapRotation * reflectVec, roughness );',
        'vec4 envMapColor = textureCubeUV( envMap, envMapRotation * boxProject( reflectVec ), roughness );'))
      .replace('#include <lights_fragment_maps>', THREE.ShaderChunk.lights_fragment_maps.replace(
        'iblIrradiance += getIBLIrradiance( geometryNormal );', ''));
  });
}

// ---------- Chargement ----------
const loader = new THREE.TextureLoader();
let done = 0, total = 1;
const tick = () => { $('progress').style.width = `${Math.min(100, ++done / total * 100)}%`; };
function texture(url, { color = true } = {}) {
  return loader.loadAsync(url).then(t => {
    t.flipY = false;   // coordonnées de texture venues de Blender (glTF)
    t.colorSpace = color ? THREE.SRGBColorSpace : THREE.NoColorSpace;
    t.anisotropy = maxAniso;
    tick();
    return t;
  });
}
// Photo pour un cadre fabriqué par la page (coordonnées de texture habituelles : pas de retournement à la glTF)
function photoTexture(url) {
  return loader.loadAsync(url).then(t => {
    t.colorSpace = THREE.SRGBColorSpace;
    t.anisotropy = maxAniso;
    return t;
  });
}
const photoUrl = (art, wanted) => {
  const width = art.tailles.find(w => w >= wanted) ?? art.tailles[art.tailles.length - 1];
  return `${IMG}${art.photo}-${width}.webp`;
};
const startRoom = () => {
  const wanted = decodeURIComponent(location.hash.slice(1));
  return ROOMS[wanted] ? wanted : 'hall';
};

const clickable = [], reflective = [], photoMaterials = {}, maps = {};
let viewMaterial = null;
async function load() {
  // plan.json : les salles et leur lumière (cuisson Blender) ; accrochage.json : la photo de chaque emplacement
  // (scripts/accrocher.py, une seconde : changer de photo ne demande pas de nouvelle cuisson)
  const [plan, hanging] = await Promise.all(['plan.json', 'accrochage.json']
    .map(file => fetch(file, { cache: 'no-cache' }).then(r => r.json())));
  PLAN = plan;
  ROOMS = PLAN.salles;
  OBSTACLES = PLAN.obstacles ?? [];
  const slots = Object.fromEntries(PLAN.accrochages.map(slot => [slot.id, slot]));
  ART = hanging.filter(h => slots[h.emplacement]).map(h => {
    const slot = slots[h.emplacement];
    return { id: h.emplacement, salle: slot.salle, photo: h.photo, tailles: h.tailles, centre: slot.centre,
             normale: slot.normale, taille: slot.taille, cadre: [slot.taille, slot.taille],
             titre: slot.salle === 'hall' ? '' : ROOMS[slot.salle].titre };
  });
  // Le numéro du calcul au bout de chaque fichier : après une nouvelle cuisson, rien ne vient de l'ancienne
  const V = PLAN.version ? `?v=${PLAN.version}` : '';
  const EXT = PLAN.format_matieres ?? '.jpg';
  if (PLAN.tonalite) toneCurve(PLAN.tonalite);
  else renderer.toneMapping = THREE.AgXToneMapping;
  const lightFiles = PLAN.lumieres;
  const textured = Object.values(PLAN.matieres).filter(m => m.texture);
  const textureIds = [...new Set(textured.map(m => m.texture))];
  // le relief par parallaxe : pas en qualité « basse » (téléphone : il coûterait trop à la carte graphique)
  const heightIds = new Set(Q.relief ? textured.filter(m => m.profondeur).map(m => m.texture) : []);
  total = Object.keys(lightFiles).length + textureIds.length * 3 + heightIds.size + ART.length + 3;
  // Les portes : pas d'ombre d'angle dans leur passage
  DOORS = Object.values(ROOMS).filter(r => r.porte).map(r => {
    const [px, pz] = r.porte, half = r.largeur / 2;
    return Math.abs(px) > Math.abs(pz) ? new THREE.Vector4(px - 0.5, px + 0.5, pz - half, pz + half)
      : new THREE.Vector4(px - half, px + half, pz - 0.5, pz + 0.5);
  });
  DOORS.push(new THREE.Vector4(-1.6, 1.6, 5.5, 6.6));   // la porte d'entrée vitrée du hall, au sud
  while (DOORS.length < 8) DOORS.push(new THREE.Vector4());
  preparerMatieres(PLAN, DOORS);

  const lightmaps = {};
  const loads = Object.entries(lightFiles).map(([name, file]) => texture(file + V).then(t => {
    t.channel = 1;   // deuxième jeu de coordonnées (LightMap)
    t.generateMipmaps = false;
    t.minFilter = THREE.LinearFilter;
    lightmaps[name] = t;
  }));
  // Pour chaque texture : la couleur (2048 px en qualité « haute », 1024 sinon), les pentes du relief (normales), la
  // rugosité (où ça brille), les hauteurs (parallaxe). Les trois dernières sont lues aux mêmes coordonnées que la
  // couleur, déjà répétées : elles se répètent donc elles-mêmes.
  for (const id of textureIds) {
    loads.push(texture(`matieres/${id}${Q.textures2k ? '_2k' : ''}${EXT}${V}`)
      .catch(() => texture(`matieres/${id}${EXT}${V}`))   // ancienne exportation, sans la grande taille
      .then(t => { maps[id] = t; }));
    const extra = [['_normale', '_n'], ['_rugosite', '_r'], ...(heightIds.has(id) ? [['_hauteur', '_h']] : [])];
    for (const [suffix, key] of extra) {
      loads.push(texture(`matieres/${id}${suffix}${EXT}${V}`, { color: false }).then(t => {
        t.wrapS = t.wrapT = THREE.RepeatWrapping;
        maps[id + key] = t;
      }, () => tick()));   // texture absente : la matière s'en passe (surface lisse)
    }
  }
  // Photos légères d'abord : 960 px pour la salle d'arrivée, 480 px ailleurs (vues de loin, à travers les portes).
  // En entrant dans une salle, ses photos passent en grand (voir sharpenRoom) : on ne charge que ce que l'on regarde.
  const first = startRoom(), photos = {};
  for (const art of ART) {
    art.url = photoUrl(art, art.salle === first ? 960 : 480);
    loads.push(photoTexture(art.url).then(t => { photos[art.id] = t; tick(); }));
  }
  const view = PLAN.matieres.vue;
  loads.push(texture(`${IMG}${view.photo}-960.webp`).then(t => { photos.__vue = t; }));
  // Le ciel vu par les fenêtres : panorama déjà passé par la courbe de Blender, affiché tel quel
  if (PLAN.ciel) {
    loads.push(loader.loadAsync(PLAN.ciel + V).then(t => {
      t.mapping = THREE.EquirectangularReflectionMapping;
      t.colorSpace = THREE.SRGBColorSpace;
      scene.background = t;
      scene.backgroundIntensity = 1;
      tick();
    }, () => tick()));   // sans ciel, le dégradé de départ reste
  }
  const gltf = await new GLTFLoader().loadAsync('musee.glb' + V);
  tick();
  await Promise.all(loads);

  const tiled = (key, tile) => {
    const t = maps[key].clone(); t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(1 / tile, 1 / tile); t.needsUpdate = true; return t;
  };
  const lmScale = PLAN.K * Math.PI;

  const root = gltf.scene, lit = [];
  root.traverse(mesh => {
    if (!mesh.isMesh) return;
    // Un groupe à une seule matière est un objet ; à plusieurs matières, un groupe d'objets portant son nom
    const group = mesh.parent === root ? mesh.name : mesh.parent.name;
    const lightMap = lightmaps[group];
    if (lightMap) lit.push(mesh);
    const base = (mesh.material?.name || '').split('.')[0];
    const spec = PLAN.matieres[base] || { couleur: [0.8, 0.8, 0.8] };
    const room = roomOfGroup(group);
    let material;
    if (base === 'vue') {
      material = viewMaterial = new THREE.MeshBasicMaterial({ map: photos.__vue, color: new THREE.Color(spec.force, spec.force, spec.force) });
    } else if (spec.lumineux) {
      material = new THREE.MeshBasicMaterial({ color: linear(spec.lumineux).multiplyScalar(spec.force) });
    } else if (/^\w+__/.test(group) && lightMap) {
      // murs, sols, plafonds d'une salle (« couvent__pierre ») : relief, lumière des projecteurs, reflets (materiaux.js)
      const map = spec.texture && maps[spec.texture] ? tiled(spec.texture, spec.tuile) : null;
      material = roomMaterial({ spec, room, lightMap, lmScale, map, maps });
    } else if (spec.texture) {
      // bancs : bois avec son relief et sa rugosité, la même lumière des projecteurs que les murs
      const options = { map: tiled(spec.texture, spec.tuile), color: linear(spec.teinte), lightMap, lightMapIntensity: lmScale };
      material = new THREE.MeshStandardMaterial({ ...options, ...objectMaps(maps, spec.texture, spec.tuile),
        roughness: spec.rugosite ?? 1, metalness: 0 });
      objectShading(material, room);
    } else {
      const options = { color: linear(spec.couleur) };
      if (lightMap) Object.assign(options, { lightMap, lightMapIntensity: lmScale });
      material = spec.reflets ? new THREE.MeshStandardMaterial({ ...options, roughness: spec.rugosite ?? 0.5, metalness: 0 })
        : new THREE.MeshBasicMaterial(options);
    }
    if (material.isMeshStandardMaterial) {
      material.userData.room = room;
      // les noirs reflètent moins ; les murs sans réglage, un peu (materiaux.js)
      material.userData.reflets ??= spec.reflets === true ? 1 : spec.reflets;
      reflective.push(material);
    }
    mesh.material = material;
    if (group.startsWith('lettres_')) { mesh.userData.goto = group.slice(8); clickable.push(mesh); }
  });
  scene.add(gltf.scene);
  scene.updateMatrixWorld(true);
  hangArtworks(lit, photos, lmScale);
  sunBeam();
  await document.fonts.ready;
  reflections();
  menu();
}

// Le rayon de soleil de La Garde, visible dans l'air : un faisceau qui part de la fenêtre et suit la direction du
// soleil de Blender jusqu'au mur ou au sol (là où la cuisson a posé la tache de lumière)
function sunBeam() {
  const sun = PLAN.soleil, room = sun && ROOMS[sun.salle];
  if (!room) return;
  const [x0, x1, z0, z1] = room.rect, top = room.hauteur ?? 5;
  const dir = new THREE.Vector3(...sun.vers_soleil).negate().normalize();
  const exit = p => {
    let t = Infinity;
    for (const [axis, lo, hi] of [['x', x0, x1], ['y', 0, top], ['z', z0, z1]]) {
      const d = dir[axis];
      if (Math.abs(d) < 1e-6) continue;
      const s = ((d > 0 ? hi : lo) - p[axis]) / d;
      if (s > 1e-4 && s < t) t = s;
    }
    return p.clone().addScaledVector(dir, t);
  };
  const near = [[sun.y[0], sun.z[0]], [sun.y[1], sun.z[0]], [sun.y[1], sun.z[1]], [sun.y[0], sun.z[1]]]
    .map(([y, z]) => new THREE.Vector3(sun.x, y, z));
  const far = near.map(exit);
  const positions = [], along = [];
  for (let i = 0; i < 4; i++) {
    const j = (i + 1) % 4;
    for (const [p, a] of [[near[i], 0], [near[j], 0], [far[j], 1], [near[i], 0], [far[j], 1], [far[i], 1]]) {
      positions.push(p.x, p.y, p.z);
      along.push(a);
    }
  }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
  geometry.setAttribute('along', new THREE.Float32BufferAttribute(along, 1));
  geometry.computeVertexNormals();
  const beam = new THREE.Mesh(geometry, new THREE.ShaderMaterial({
    uniforms: { tint: { value: new THREE.Color(1, 0.9, 0.74) }, strength: { value: 0.09 } },
    vertexShader: `attribute float along; varying float vAlong; varying vec3 vNormal; varying vec3 vView;
      void main() {
        vAlong = along;
        vec4 world = modelMatrix * vec4( position, 1.0 );
        vNormal = normalize( mat3( modelMatrix ) * normal );
        vView = normalize( cameraPosition - world.xyz );
        gl_Position = projectionMatrix * viewMatrix * world;
      }`,
    fragmentShader: `uniform vec3 tint; uniform float strength; varying float vAlong; varying vec3 vNormal; varying vec3 vView;
      void main() {
        float grazing = 1.0 - abs( dot( normalize( vNormal ), normalize( vView ) ) );
        float fade = smoothstep( 0.0, 0.1, vAlong ) * ( 1.0 - smoothstep( 0.5, 1.0, vAlong ) );
        gl_FragColor = vec4( tint * strength * ( 0.3 + grazing * grazing ) * fade, 1.0 );
      }`,
    transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, side: THREE.DoubleSide,
  }));
  beam.raycast = () => {};   // le rayon ne gêne pas les clics
  beam.renderOrder = 2;
  scene.add(beam);
}

// Photos nettes, salle par salle : en entrant dans une salle, ses photos passent en grand (1600 px, 960 sur téléphone).
// Les salles où l'on ne va pas ne coûtent rien de plus.
let sharpening = Promise.resolve();
const sharpened = new Set();
function sharpenRoom(room) {
  if (sharpened.has(room)) return;
  sharpened.add(room);
  sharpening = sharpening.then(async () => {
    for (const art of ART.filter(a => a.salle === room)) {
      const material = photoMaterials[art.id], url = photoUrl(art, SHARP);
      if (!material || url === art.url) continue;
      try {
        const t = await photoTexture(url);
        const old = material.map;
        material.map = t;
        old.dispose();
        art.url = url;
        dirty = true;
      } catch { /* la photo plus légère reste */ }
    }
    if (room === 'montagne' && viewMaterial && !phone) {   // le paysage de la baie, en grand
      try {
        const t = await photoTexture(`${IMG}${PLAN.matieres.vue.photo}-1600.webp`);
        t.flipY = false;
        const old = viewMaterial.map;
        viewMaterial.map = t;
        old.dispose();
        dirty = true;
      } catch { /* le paysage en 960 px reste */ }
    }
  });
}

function roomOfGroup(group) {
  // « couvent__pierre », ou « banc_hall », « luminaires_messe », « deco_montagne »
  const m = group.match(/^(hall|couvent|toulouse|garde|messe|montagne)__/) || group.match(/^(?:banc|luminaires|deco)_(\w+)$/);
  return m ? m[1] : 'hall';
}

// ---------- Cadres ----------
// Les photos et leurs cadres sont posés par la page sur les emplacements (accrochage.json) : changer de photo ne
// demande aucune nouvelle cuisson. Ils prennent la lumière du mur juste derrière eux (sa carte de lumière, au même
// endroit : le halo du projecteur y est, sans l'ombre d'un cadre), plus une ombre douce qui les décolle du mur.
// Chaque salle a son cadre (FRAMES) : chêne sombre au Couvent, noir fin à Toulouse, doré à la Messe…
// Les baguettes prennent aussi la lumière des projecteurs (materiaux.js) : dessus éclairé, dessous dans l'ombre,
// reflet sur le bois ciré ou la dorure ; le bois a son relief (veines, pores).
function frameMaterial(style, lit, room, wallNormal) {
  const options = { roughness: style.rugosite ?? 0.5, metalness: style.metal ?? 0, ...lit };
  if (style.bois && maps[style.bois]) {
    const tile = Object.values(PLAN.matieres).find(m => m.texture === style.bois)?.tuile ?? 1;
    const map = maps[style.bois].clone();
    map.wrapS = map.wrapT = THREE.RepeatWrapping;
    map.repeat.set(1 / tile, 1 / tile);
    map.needsUpdate = true;
    // rugosité de la texture × celle du cadre (rugosite 0,6 : bois ciré)
    Object.assign(options, { map, color: linear(style.teinte ?? [1, 1, 1]), ...objectMaps(maps, style.bois, tile) });
  } else {
    options.color = linear(style.couleur ?? [0.02, 0.02, 0.02]);
  }
  const material = new THREE.MeshStandardMaterial(options);
  Object.assign(material.userData, { room, reflets: style.reflets ?? 0.35 });
  objectShading(material, room, wallNormal);
  reflective.push(material);
  return material;
}
// Coordonnées de texture d'une baguette de bois en mètres, le fil du bois dans la longueur
function grainUv(geometry, horizontal) {
  const p = geometry.attributes.position, uv = geometry.attributes.uv;
  for (let i = 0; i < p.count; i++) {
    const x = p.getX(i), y = p.getY(i), z = p.getZ(i);
    uv.setXY(i, horizontal ? x : y, (horizontal ? y : x) + z);
  }
  uv.needsUpdate = true;
}

function hangArtworks(walls, photos, lmScale) {
  const raycaster = new THREE.Raycaster(), shadow = contactShadow();
  ART.forEach((art, index) => {
    const style = FRAMES[art.salle] ?? FRAMES.hall;
    const tex = photos[art.id], ratio = tex.image.width / tex.image.height, size = art.taille;
    const [w, h] = ratio >= 1 ? [size, size / ratio] : [size * ratio, size];
    const margin = Math.max(0.06, Math.min(w, h) * (style.marge ?? 0.15)), bar = style.bar, depth = 0.035;
    const W = w + 2 * margin, H = h + 2 * margin;
    art.cadre = [W + 2 * bar, H + 2 * bar];
    const n = new THREE.Vector3(...art.normale), at = new THREE.Vector3(...art.centre);
    const up = new THREE.Vector3(0, 1, 0), right = up.clone().cross(n);
    // Où tombent, dans la carte de lumière du mur, le centre, un point 10 cm à droite et un point 10 cm au-dessus
    const probe = (x, y) => {
      raycaster.set(at.clone().addScaledVector(right, x).addScaledVector(up, y).addScaledVector(n, 0.3), n.clone().negate());
      return raycaster.intersectObjects(walls, false).find(hit => hit.uv1);
    };
    const hit = probe(0, 0), hx = probe(0.1, 0), hy = probe(0, 0.1);
    const lightMap = hit?.object.material.lightMap;
    const u0 = hit ? hit.uv1 : new THREE.Vector2();
    const ax = hx && hit ? hx.uv1.clone().sub(u0).multiplyScalar(10) : new THREE.Vector2();
    const ay = hy && hit ? hy.uv1.clone().sub(u0).multiplyScalar(10) : new THREE.Vector2();
    const uvAt = (x, y) => [u0.x + x * ax.x + y * ay.x, u0.y + x * ax.y + y * ay.y];
    const lit = lightMap ? { lightMap, lightMapIntensity: lmScale } : {};
    const group = new THREE.Group();
    group.position.copy(at);
    group.quaternion.setFromRotationMatrix(new THREE.Matrix4().makeBasis(right, up, n));
    const add = (geometry, material, x, y, z) => {
      geometry.translate(x, y, z);
      const p = geometry.attributes.position, uv1 = new Float32Array(p.count * 2);
      for (let i = 0; i < p.count; i++) [uv1[2 * i], uv1[2 * i + 1]] = uvAt(p.getX(i), p.getY(i));
      geometry.setAttribute('uv1', new THREE.BufferAttribute(uv1, 2));
      const mesh = new THREE.Mesh(geometry, material);
      mesh.userData.art = index;
      clickable.push(mesh);
      group.add(mesh);
      return geometry;
    };
    // passe-partout autour de la photo, photo un peu en retrait, quatre baguettes de cadre
    const mount = new THREE.MeshBasicMaterial({ color: linear(style.passe ?? PLAN.matieres['passe-partout'].couleur), ...lit });
    for (const [cx, cy, sx, sy] of [[0, (h + margin) / 2, W, margin], [0, -(h + margin) / 2, W, margin],
                                    [(w + margin) / 2, 0, margin, h], [-(w + margin) / 2, 0, margin, h]]) {
      add(new THREE.PlaneGeometry(sx, sy), mount, cx, cy, depth - 0.006);
    }
    // Vraies couleurs : pas de courbe de tons, et la lumière reçue ramenée à 1 (et à du blanc) là où la photo est la
    // plus éclairée ; seul reste le léger dégradé du projecteur
    const [r, g, b] = lightMap ? wallLight(lightMap, uvAt, w, h) : [1, 1, 1];
    const photo = new THREE.MeshBasicMaterial({ map: tex, toneMapped: false, ...lit });
    if (post.actif) addPatch(photo, 'tel-quel', post.telQuel);   // ni courbe de tons ni effets d'image sur la photo
    photo.color.setRGB(PHOTO_GAIN / r, PHOTO_GAIN / g, PHOTO_GAIN / b);
    photoMaterials[art.id] = photo;
    add(new THREE.PlaneGeometry(w, h), photo, 0, 0, depth - 0.009);
    const frame = frameMaterial(style, lit, art.salle, n);
    for (const [cx, cy, sx, sy] of [[0, (H + bar) / 2, W + 2 * bar, bar], [0, -(H + bar) / 2, W + 2 * bar, bar],
                                    [(W + bar) / 2, 0, bar, H], [-(W + bar) / 2, 0, bar, H]]) {
      const geometry = add(new THREE.BoxGeometry(sx, sy, depth), frame, cx, cy, depth / 2);
      if (style.bois) grainUv(geometry, sx > sy);
    }
    // ombre douce sur le mur, un peu plus bas (la lumière vient d'en haut)
    const halo = new THREE.Mesh(new THREE.PlaneGeometry(W + 2 * bar + 0.16, H + 2 * bar + 0.18).translate(0, -0.03, 0.002),
      new THREE.MeshBasicMaterial({ color: 0x000000, alphaMap: shadow, transparent: true, opacity: 0.32, depthWrite: false }));
    halo.raycast = () => {};
    group.add(halo);
    scene.add(group);
  });
}

// Lumière reçue (dans la carte du mur) par la partie la plus éclairée d'une photo : 64 points, le dixième le plus clair
const lightPixels = new Map();
function wallLight(texture, uvAt, w, h) {
  if (!lightPixels.has(texture)) {
    const image = texture.image, c = document.createElement('canvas');
    c.width = image.width;
    c.height = image.height;
    const g = c.getContext('2d', { willReadFrequently: true });
    g.drawImage(image, 0, 0);
    lightPixels.set(texture, { data: g.getImageData(0, 0, c.width, c.height).data, W: c.width, H: c.height });
  }
  const { data, W, H } = lightPixels.get(texture);
  const decode = v => { v /= 255; return (v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4) * PLAN.K; };
  const samples = [];
  for (let i = 0; i < 8; i++) {
    for (let j = 0; j < 8; j++) {
      const [u, v] = uvAt(-w / 2 + w * (i + 0.5) / 8, -h / 2 + h * (j + 0.5) / 8);
      const x = Math.min(W - 1, Math.max(0, Math.floor(u * W))), y = Math.min(H - 1, Math.max(0, Math.floor(v * H)));
      const k = (y * W + x) * 4;
      samples.push([decode(data[k]), decode(data[k + 1]), decode(data[k + 2])]);
    }
  }
  const luminance = p => p[0] * 0.2126 + p[1] * 0.7152 + p[2] * 0.0722;
  const top = samples.sort((a, b) => luminance(b) - luminance(a)).slice(0, 7);
  return [0, 1, 2].map(c => Math.max(0.05, top.reduce((s, p) => s + p[c], 0) / top.length));
}

// Ombre douce d'un cadre : un rectangle flou, opaque au centre
function contactShadow() {
  const c = document.createElement('canvas');
  c.width = c.height = 128;
  const g = c.getContext('2d');
  g.fillStyle = '#000';
  g.fillRect(0, 0, 128, 128);
  g.filter = 'blur(9px)';
  g.fillStyle = '#fff';
  g.fillRect(20, 20, 88, 88);
  return new THREE.CanvasTexture(c);
}

// Reflets : une photo à 360° prise au centre de chaque salle, une fois, sert de miroir flou au sol et aux cadres
// (rapportée sur les murs de la salle : voir boxReflections)
function reflections() {
  const envs = {};
  const pmrem = new THREE.PMREMGenerator(renderer);
  for (const [id, room] of Object.entries(ROOMS)) {
    const [x0, x1, z0, z1] = room.rect;
    const target = new THREE.WebGLCubeRenderTarget(phone ? 128 : 256, { type: THREE.HalfFloatType });
    const cube = new THREE.CubeCamera(0.05, 60, target);
    cube.position.set((x0 + x1) / 2, 1.5, (z0 + z1) / 2);
    cube.update(renderer, scene);
    envs[id] = pmrem.fromCubemap(target.texture).texture;
    target.dispose();
  }
  for (const m of reflective) {
    const id = envs[m.userData.room] ? m.userData.room : 'hall';
    m.envMap = envs[id];
    m.envMapIntensity = m.userData.reflets ?? 1;
    boxReflections(m, ROOMS[id]);
  }
}

// ---------- Plan : où peut-on marcher ? ----------
const MARGIN = 0.4;
function doorRect(room) {
  const [px, pz] = room.porte, half = room.largeur / 2 - 0.35;
  return Math.abs(px) > Math.abs(pz) ? [px - 0.9, px + 0.9, pz - half, pz + half] : [px - half, px + half, pz - 0.9, pz + 0.9];
}
function walkable(x, z) {
  for (const room of Object.values(ROOMS)) {
    const [x0, x1, z0, z1] = room.rect;
    if (x > x0 + MARGIN && x < x1 - MARGIN && z > z0 + MARGIN && z < z1 - MARGIN) return true;
    if (room.porte) { const [a, b, c, d] = doorRect(room); if (x > a && x < b && z > c && z < d) return true; }
  }
  return false;
}
// Libre : dans une salle, et pas dans un banc
function free(x, z) {
  if (!walkable(x, z)) return false;
  const m = 0.28;
  return !OBSTACLES.some(([x0, x1, z0, z1]) => x > x0 - m && x < x1 + m && z > z0 - m && z < z1 + m);
}
function roomAt(x, z) {
  for (const [id, room] of Object.entries(ROOMS)) {
    const [x0, x1, z0, z1] = room.rect;
    if (x >= x0 && x <= x1 && z >= z0 && z <= z1) return id;
  }
  return 'hall';
}
// Côté salle et côté hall d'une porte
function doorPoints(id) {
  const room = ROOMS[id], [px, pz] = room.porte;
  const [x0, x1, z0, z1] = room.rect;
  const inside = new THREE.Vector3(px, EYE, pz), hall = new THREE.Vector3(px, EYE, pz);
  if (Math.abs(px) > Math.abs(pz)) { const s = Math.sign((x0 + x1) / 2 - px); inside.x += s * 1.0; hall.x -= s * 1.0; }
  else { const s = Math.sign((z0 + z1) / 2 - pz); inside.z += s * 1.0; hall.z -= s * 1.0; }
  return { inside, hall };
}

// ---------- Déplacements ----------
// Comme dans un jeu : le regard suit la souris ou le doigt en douceur (look → pose), la marche accélère et freine
// (vel), le pas se sent à peine (bob). Un clic sur le sol ou une photo y mène tout seul (glide).
const pose = { pos: new THREE.Vector3(0, EYE, 5.0), yaw: 0, pitch: -0.02 };
const look = { yaw: 0, pitch: -0.02 };   // où le regard va
const vel = new THREE.Vector3();
let glide = null, dirty = true, here = 'hall', currentArt = -1, bob = 0, bobAmount = 0;
const keys = new Set();
const forward = yaw => new THREE.Vector3(-Math.sin(yaw), 0, -Math.cos(yaw));
const right = yaw => new THREE.Vector3(Math.cos(yaw), 0, -Math.sin(yaw));
const joy = { x: 0, y: 0, id: null };   // manette tactile : x à droite, y vers le bas (-1 à 1)

function moveBy(dx, dz) {
  const p = pose.pos;
  if (free(p.x + dx, p.z + dz)) { p.x += dx; p.z += dz; }
  else if (free(p.x + dx, p.z)) { p.x += dx; vel.z = 0; }   // on glisse le long du mur
  else if (free(p.x, p.z + dz)) { p.z += dz; vel.x = 0; }
  else vel.set(0, 0, 0);
}
function syncLook() { look.yaw = pose.yaw; look.pitch = pose.pitch; }
function stopGlide() { if (glide) { glide = null; syncLook(); } }

// Chemin d'un point à un autre, en passant par les portes (les salles ne s'ouvrent que sur le hall)
function route(to) {
  const from = pose.pos.clone(), a = roomAt(from.x, from.z), b = roomAt(to.x, to.z);
  const points = [from];
  if (a !== b) {
    if (a !== 'hall') { const d = doorPoints(a); points.push(d.inside, d.hall); }
    if (b !== 'hall') { const d = doorPoints(b); points.push(d.hall, d.inside); }
  }
  points.push(to.clone().setY(EYE));
  return points;
}
function travel(to, yaw = null, pitch = 0, then = null) {
  const points = route(to);
  const lengths = points.slice(1).map((p, i) => p.distanceTo(points[i]));
  const totalLength = lengths.reduce((s, l) => s + l, 0);
  // Pendant la marche, le regard suit le chemin ; à l'arrivée, il se pose sur la cible
  const finalYaw = yaw ?? (totalLength > 0.01 ? Math.atan2(-(to.x - pose.pos.x), -(to.z - pose.pos.z)) : pose.yaw);
  let turn = finalYaw - pose.yaw;
  turn = ((turn + Math.PI) % (2 * Math.PI) + 2 * Math.PI) % (2 * Math.PI) - Math.PI;
  vel.set(0, 0, 0);
  glide = { points, lengths, total: totalLength, yaw0: pose.yaw, turn, pitch0: pose.pitch, pitch1: pitch, then,
            start: performance.now(), duration: THREE.MathUtils.clamp(totalLength / 1.9, 0.8, 6) * 1000 };
}
const ease = t => t < 0.5 ? 4 * t * t * t : 1 - (-2 * t + 2) ** 3 / 2;
function stepGlide(now) {
  const t = Math.min(1, (now - glide.start) / glide.duration), e = ease(t);
  let along = e * glide.total, i = 0;
  while (i < glide.lengths.length - 1 && along > glide.lengths[i]) { along -= glide.lengths[i]; i++; }
  pose.pos.copy(glide.points[i]).lerp(glide.points[i + 1], glide.lengths[i] ? Math.min(1, along / glide.lengths[i]) : 1);
  pose.yaw = glide.yaw0 + glide.turn * e;
  pose.pitch = glide.pitch0 + (glide.pitch1 - glide.pitch0) * e;
  syncLook();
  if (t >= 1) { const then = glide.then; glide = null; if (then) then(); }
}

// Se placer devant une œuvre (assez loin pour voir tout le cadre)
function viewOf(index) {
  const art = ART[index], n = new THREE.Vector3(...art.normale), c = new THREE.Vector3(...art.centre);
  const vfov = THREE.MathUtils.degToRad(camera.fov), hfov = 2 * Math.atan(Math.tan(vfov / 2) * camera.aspect);
  const [w, h] = art.cadre;
  const d = THREE.MathUtils.clamp(Math.max((w / 2 + 0.5) / Math.tan(hfov / 2), (h / 2 + 0.45) / Math.tan(vfov / 2)), 1.6, 4.5);
  const p = c.clone().addScaledVector(n, d).setY(EYE);
  return { p, yaw: Math.atan2(n.x, n.z), pitch: Math.atan2(c.y - EYE, d) };
}
function goToArt(index, open = false) {
  currentArt = index;
  const v = viewOf(index);
  travel(v.p, v.yaw, v.pitch, open ? () => openViewer(index) : null);
  hideHint();
}
function goToRoom(id) {
  const [x, z, yaw] = ROOMS[id].entree;
  currentArt = -1;
  travel(new THREE.Vector3(x, EYE, z), yaw, -0.02);
  hideHint();
  closeMenu();
}
function roomArt(room) { return ART.map((a, i) => [a, i]).filter(([a]) => a.salle === room).map(([, i]) => i); }
function nextArt(delta) {
  const list = roomArt(here);
  if (!list.length) return;
  const at = list.indexOf(currentArt);
  goToArt(list[((at < 0 ? (delta > 0 ? -1 : 0) : at) + delta + list.length) % list.length]);
}

// ---------- Vue en grand ----------
const viewer = $('viewer'), viewerImg = $('viewer-img');
let viewing = -1;
function openViewer(index) {
  viewing = index;
  const art = ART[index];
  const largest = art.tailles[art.tailles.length - 1];
  viewerImg.srcset = art.tailles.map(w => `${IMG}${art.photo}-${w}.webp ${w}w`).join(', ');
  viewerImg.sizes = '100vw';
  viewerImg.src = `${IMG}${art.photo}-${largest}.webp`;
  viewerImg.alt = art.titre;
  $('viewer-title').textContent = art.titre;
  const room = ROOMS[art.salle];
  $('viewer-album').hidden = !room.lien;
  if (room.lien) $('viewer-album').href = room.lien;
  viewer.hidden = false;
  requestAnimationFrame(() => viewer.classList.add('open'));
  $('viewer-close').focus();
  // Une étape dans l'historique : le bouton ou le geste « retour » du téléphone ferme la photo au lieu de quitter la galerie
  if (!history.state?.vue) history.pushState({ vue: true }, '');
}
function closeViewer(fromHistory = false) {
  if (viewing < 0) return;
  viewer.classList.remove('open');
  setTimeout(() => { if (viewing < 0) viewer.hidden = true; }, 300);
  viewing = -1;
  canvas.focus();
  if (!fromHistory && history.state?.vue) history.back();
}
addEventListener('popstate', () => closeViewer(true));
// Adresse changée sur la page ouverte (« #couvent ») : on y va
addEventListener('hashchange', () => {
  const id = decodeURIComponent(location.hash.slice(1));
  if (ROOMS && ROOMS[id] && id !== here) goToRoom(id);
});
if (history.state?.vue) history.replaceState(null, '');   // page rechargée photo ouverte : on repart d'un historique propre
viewerImg.draggable = false;
function viewerStep(delta) {
  const list = roomArt(ART[viewing].salle);
  const next = list[(list.indexOf(viewing) + delta + list.length) % list.length];
  openViewer(next);
  currentArt = next;
  const v = viewOf(next);   // la visite suit, derrière
  pose.pos.copy(v.p); pose.yaw = v.yaw; pose.pitch = v.pitch; syncLook(); vel.set(0, 0, 0); dirty = true;
}
$('viewer-close').addEventListener('click', () => closeViewer());
$('viewer-prev').addEventListener('click', () => viewerStep(-1));
$('viewer-next').addEventListener('click', () => viewerStep(1));
// Sur téléphone : glisser le doigt vers la gauche ou la droite passe à la photo suivante ou précédente
let swipe = null, swiped = false;
viewer.addEventListener('pointerdown', e => { swipe = { x: e.clientX, y: e.clientY }; swiped = false; });
viewer.addEventListener('pointerup', e => {
  if (!swipe || viewing < 0) return;
  const dx = e.clientX - swipe.x, dy = e.clientY - swipe.y;
  swipe = null;
  if (Math.abs(dx) > 50 && Math.abs(dx) > Math.abs(dy) * 1.5) { swiped = true; viewerStep(dx < 0 ? 1 : -1); }
});
viewer.addEventListener('click', e => {
  if (swiped) { swiped = false; return; }
  if (e.target === viewer || e.target.tagName === 'FIGURE') closeViewer();
});

// ---------- Salles ----------
function menu() {
  const box = $('menu');
  box.innerHTML = '';
  for (const [id, room] of Object.entries(ROOMS)) {
    const b = document.createElement('button');
    b.type = 'button';
    b.textContent = room.titre;
    b.dataset.room = id;
    b.addEventListener('click', () => goToRoom(id));
    box.append(b);
  }
}
function closeMenu() { $('menu').hidden = true; $('rooms').setAttribute('aria-expanded', 'false'); }
$('rooms').addEventListener('click', () => {
  const box = $('menu');
  box.hidden = !box.hidden;
  $('rooms').setAttribute('aria-expanded', String(!box.hidden));
  for (const b of box.children) b.toggleAttribute('aria-current', b.dataset.room === here);
});
$('prev').addEventListener('click', () => nextArt(-1));
$('next').addEventListener('click', () => nextArt(1));

// L'aide, selon l'appareil : souris et clavier, ou doigt et manette
$('hint').textContent = touch
  ? 'Manette pour marcher · glissez pour regarder · touchez une photo pour la voir en grand'
  : 'Cliquez pour prendre la main · la souris regarde · ZQSD pour marcher (Maj : courir) · Échap pour lâcher';
let hintTimer = setTimeout(hideHint, 12000);
function hideHint() { $('hint').classList.add('gone'); clearTimeout(hintTimer); }

// ---------- Commandes ----------
const raycaster = new THREE.Raycaster(), pointer = new THREE.Vector2();
function pick(x, y) {
  pointer.set(x / innerWidth * 2 - 1, -(y / innerHeight) * 2 + 1);
  raycaster.setFromCamera(pointer, camera);
  return raycaster.intersectObjects(scene.children, true).find(h => h.object.visible);
}
// Comme dans Minecraft (ordinateur) : un clic « prend la main » (la souris disparaît et tourne la vue directement,
// sans glisser), un viseur au centre ; clic sur une photo visée : elle s'ouvre en grand ; Échap rend la souris.
let locked = false, aimAt = 0;
const crosshair = $('crosshair');
// Si le navigateur refuse (page dans un cadre, appareil sans souris…), `refused` prend le relais : on marche jusqu'au
// point cliqué, comme avant
function lockPointer(refused) {
  if (locked) return;
  const again = () => {
    try {
      const p = canvas.requestPointerLock();
      if (p?.catch) p.catch(refused); else setTimeout(() => { if (!locked) refused(); }, 300);
    } catch { refused(); }
  };
  try {
    const asked = canvas.requestPointerLock?.({ unadjustedMovement: true });   // mouvement brut, sans accélération
    if (asked?.catch) asked.catch(e => (e?.name === 'NotSupportedError' ? again() : refused()));
    else if (asked === undefined && canvas.requestPointerLock) setTimeout(() => { if (!locked) refused(); }, 300);
    else if (!canvas.requestPointerLock) refused();
  } catch { refused(); }
}
document.addEventListener('pointerlockchange', () => {
  locked = document.pointerLockElement === canvas;
  document.body.classList.toggle('playing', locked);
  if (locked) { hideHint(); closeMenu(); }
  syncLook();
});
function aimed() { return ART ? pick(innerWidth / 2, innerHeight / 2) : null; }
function shoot() {
  const hit = aimed();
  if (hit?.object.userData.art !== undefined) { document.exitPointerLock(); goToArt(hit.object.userData.art, true); }
  else if (hit?.object.userData.goto) goToRoom(hit.object.userData.goto);
}

let drag = null, hoverAt = 0;
canvas.addEventListener('pointerdown', e => {
  if (locked) { if (e.button === 0) shoot(); return; }
  drag = { x: e.clientX, y: e.clientY, moved: 0 };
  canvas.setPointerCapture(e.pointerId);
  closeMenu();
});
canvas.addEventListener('pointermove', e => {
  if (locked) {
    const clamp = v => THREE.MathUtils.clamp(v, -250, 250);   // certains navigateurs envoient des sauts énormes
    const k = 0.0022 * camera.fov / 70;
    if (Math.abs(e.movementX) + Math.abs(e.movementY) > 2) stopGlide();
    look.yaw -= clamp(e.movementX) * k;
    look.pitch = THREE.MathUtils.clamp(look.pitch - clamp(e.movementY) * k, -1.35, 1.35);
    return;
  }
  if (!drag) {
    // la main sur les photos et les noms de salle (au plus 20 fois par seconde : chercher sous la souris coûte)
    if (e.pointerType === 'mouse' && ART && e.timeStamp - hoverAt > 50) {
      hoverAt = e.timeStamp;
      const hit = pick(e.clientX, e.clientY);
      canvas.classList.toggle('pointing', !!hit && (hit.object.userData.art !== undefined || !!hit.object.userData.goto));
    }
    return;
  }
  const dx = e.clientX - drag.x, dy = e.clientY - drag.y;
  drag.x = e.clientX; drag.y = e.clientY; drag.moved += Math.abs(dx) + Math.abs(dy);
  if (drag.moved < 6) return;
  stopGlide(); hideHint();
  canvas.classList.add('dragging');
  const k = (e.pointerType === 'mouse' ? 0.0032 : 0.005) * camera.fov / 60;
  look.yaw += dx * k;
  look.pitch = THREE.MathUtils.clamp(look.pitch + dy * k, -0.7, 0.6);
});
canvas.addEventListener('pointerup', e => {
  canvas.classList.remove('dragging');
  if (drag && drag.moved < 6 && ART) {
    const hit = pick(e.clientX, e.clientY);
    const walk = () => {   // toucher le sol y mène
      if (!(hit && hit.face && hit.point.y < 0.05)) return;
      const p = hit.point.clone();
      // un point juste devant le mur s'il faut, pour rester dans la salle
      for (let i = 0; i < 20 && !free(p.x, p.z); i++) p.lerp(pose.pos, 0.15);
      if (free(p.x, p.z)) { currentArt = -1; travel(p, null, -0.02); hideHint(); }
    };
    if (hit?.object.userData.art !== undefined) goToArt(hit.object.userData.art, true);
    else if (hit?.object.userData.goto) goToRoom(hit.object.userData.goto);
    else if (!touch) lockPointer(walk);   // ordinateur : le clic prend la main, comme dans un jeu
    else walk();
  }
  drag = null;
});
canvas.addEventListener('pointercancel', () => { drag = null; canvas.classList.remove('dragging'); });
// La molette avance ou recule, avec élan
canvas.addEventListener('wheel', e => {
  e.preventDefault();
  stopGlide(); hideHint();
  vel.addScaledVector(forward(pose.yaw), THREE.MathUtils.clamp(-e.deltaY * 0.025, -3, 3));
  if (vel.length() > RUN) vel.setLength(RUN);
}, { passive: false });
const MOVE_KEYS = ['KeyW', 'KeyS', 'KeyA', 'KeyD', 'ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'ShiftLeft', 'ShiftRight'];
addEventListener('keydown', e => {
  if (e.ctrlKey || e.metaKey || e.altKey || !ART) return;
  if (viewing >= 0) {
    if (e.key === 'Escape') closeViewer();
    if (e.key === 'ArrowRight') viewerStep(1);
    if (e.key === 'ArrowLeft') viewerStep(-1);
    return;
  }
  // e.code : la place de la touche, pas sa lettre (ZQSD sur un clavier français, WASD ailleurs)
  if (MOVE_KEYS.includes(e.code)) {
    if (!e.code.startsWith('Shift')) { e.preventDefault(); stopGlide(); hideHint(); }
    keys.add(e.code);
  }
  if (e.key === 'Escape') closeMenu();
});
addEventListener('keyup', e => keys.delete(e.code));
addEventListener('blur', () => keys.clear());

// Manette tactile (téléphone, tablette) : le pouce gauche fait marcher, l'autre main regarde en glissant
const stick = $('stick'), knob = stick.firstElementChild;
if (touch) stick.hidden = false;
function moveStick(e) {
  const r = stick.getBoundingClientRect(), R = r.width / 2, max = R - 12;
  let dx = e.clientX - r.left - R, dy = e.clientY - r.top - R;
  const d = Math.hypot(dx, dy);
  if (d > max) { dx *= max / d; dy *= max / d; }
  knob.style.transform = `translate(${dx}px, ${dy}px)`;
  joy.x = dx / max; joy.y = dy / max;
}
stick.addEventListener('pointerdown', e => {
  joy.id = e.pointerId;
  try { stick.setPointerCapture(e.pointerId); } catch { /* doigt déjà levé */ }
  stick.classList.add('on');
  stopGlide(); hideHint(); closeMenu();
  moveStick(e);
});
stick.addEventListener('pointermove', e => { if (e.pointerId === joy.id) moveStick(e); });
const releaseStick = e => {
  if (e.pointerId !== joy.id) return;
  joy.id = null; joy.x = joy.y = 0;
  knob.style.transform = '';
  stick.classList.remove('on');
};
stick.addEventListener('pointerup', releaseStick);
stick.addEventListener('pointercancel', releaseStick);

function resize() {
  camera.aspect = innerWidth / innerHeight;
  camera.fov = camera.aspect < 0.8 ? 72 : 70;   // 70° : le champ de vision d'un jeu (celui de Minecraft)
  camera.updateProjectionMatrix();
  renderer.setSize(innerWidth, innerHeight, false);
  post.setSize();
  dirty = true;
}
addEventListener('resize', resize);

// La salle où l'on est : son nom en bas, l'adresse qui suit, ses photos en grand
function updateRoom() {
  const room = roomAt(pose.pos.x, pose.pos.z);
  if (room === here) return;
  here = room;
  $('room-title').textContent = ROOMS[room].titre;
  // l'adresse suit la salle (« …/galerie/index.html#couvent ») : on peut la partager, un album y mène
  history.replaceState(history.state, '', room === 'hall' ? location.pathname + location.search : `#${room}`);
  sharpenRoom(room);
}
function place() {
  camera.position.copy(pose.pos);
  camera.position.y += Math.abs(Math.sin(bob)) * 0.022 * bobAmount - 0.011 * bobAmount;   // le pas, à peine
  camera.rotation.set(pose.pitch, pose.yaw, Math.sin(bob) * 0.003 * bobAmount);
}

const clock = new THREE.Clock();
function frame(now) {
  const dt = Math.min(clock.getDelta(), 0.05);
  let moving = false;
  if (glide) { stepGlide(now); moving = true; }
  else {
    if (keys.has('ArrowLeft')) look.yaw += 1.7 * dt;
    if (keys.has('ArrowRight')) look.yaw -= 1.7 * dt;
    const ahead = (keys.has('KeyW') || keys.has('ArrowUp') ? 1 : 0) - (keys.has('KeyS') || keys.has('ArrowDown') ? 1 : 0) - joy.y;
    const side = (keys.has('KeyD') ? 1 : 0) - (keys.has('KeyA') ? 1 : 0) + joy.x;
    const want = forward(pose.yaw).multiplyScalar(ahead).addScaledVector(right(pose.yaw), side);
    const amount = want.length();
    if (amount > 1) want.divideScalar(amount);
    want.multiplyScalar(keys.has('ShiftLeft') || keys.has('ShiftRight') ? RUN : WALK);
    // accélère en 0,2 s, s'arrête en 0,15 s quand on a la main (plus doux sinon) : ni à-coups ni glissade
    vel.lerp(want, 1 - Math.exp(-dt * (amount > 0.01 ? (locked ? 14 : 8) : (locked ? 18 : 11))));
    if (vel.lengthSq() > 1e-5) { moveBy(vel.x * dt, vel.z * dt); moving = true; }
    else vel.set(0, 0, 0);
    // le regard suit la souris tout de suite quand on a la main ; en glissant, il la rejoint en douceur
    const k = locked ? 1 : 1 - Math.exp(-dt * 16), dyaw = look.yaw - pose.yaw, dpitch = look.pitch - pose.pitch;
    if (Math.abs(dyaw) > 1e-5 || Math.abs(dpitch) > 1e-5) { pose.yaw += dyaw * k; pose.pitch += dpitch * k; moving = true; }
    else { pose.yaw = look.yaw; pose.pitch = look.pitch; }
  }
  const speed = glide ? 0 : Math.hypot(vel.x, vel.z);
  bobAmount += (Math.min(1, speed / WALK) - bobAmount) * (1 - Math.exp(-dt * 6));
  if (bobAmount > 0.003) { bob += dt * speed * 3.9; moving = true; }   // un pas tous les 80 cm environ
  if (moving || dirty) {
    place();
    post.render();
    dirty = false;
    updateRoom();
  }
  // le viseur grossit sur une photo ou un nom de salle (un clic y mène)
  if (locked && now - aimAt > 100) {
    aimAt = now;
    const hit = aimed();
    crosshair.classList.toggle('aim', !!hit && (hit.object.userData.art !== undefined || !!hit.object.userData.goto));
  }
  requestAnimationFrame(frame);
}

// Pour les vérifications : aller tout de suite quelque part, sans attendre l'animation
function finishGlide() {
  while (glide) stepGlide(glide.start + glide.duration + 1);
  place();
  post.render();
  updateRoom();
}
Object.assign(window.__galerie, {
  room: id => { goToRoom(id); finishGlide(); return roomAt(pose.pos.x, pose.pos.z); },
  art: (i, open = false) => { goToArt(i, open); finishGlide(); return ART[i].id; },
  oeuvres: () => ART.map(({ id, salle, photo, cadre, url }) => ({ id, salle, photo, cadre, url })),
  sharpen: async () => { for (const room of Object.keys(ROOMS)) sharpenRoom(room); await sharpening; },   // toutes en grand
  pose, look, vel, keys, joy,
});

async function start() {
  resize();
  await load();
  // Arrivée directe dans une salle : « index.html#garde » (lien depuis l'album La Garde, par exemple)
  const first = startRoom();
  if (first !== 'hall') {
    const [x, z, yaw] = ROOMS[first].entree;
    pose.pos.set(x, EYE, z);
    pose.yaw = yaw;
  }
  syncLook();
  place();
  post.compile();
  post.render();
  updateRoom();
  sharpenRoom(here);
  requestAnimationFrame(frame);
  $('loading').classList.add('done');
  performance.mark('galerie-prete');
}
start().catch(error => {
  console.error(error);
  $('loading-text').textContent = 'La galerie n’a pas pu se charger.';
});
