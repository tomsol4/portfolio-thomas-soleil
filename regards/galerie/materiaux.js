// Les matières des salles (murs, sols, plafonds, cadres, bancs), rendues comme dans un jeu vidéo récent.
// La lumière vient des cartes de Blender (lumiere/*.png : tout ce que reçoit chaque point, rebonds compris). Mais ces
// cartes ne connaissent pas le relief des pierres, des briques, des joints : seules, les surfaces paraissent plates.
// La page rajoute donc :
// - la pente de chaque bosse et de chaque joint (carte de normales, matieres/*_normale) ;
// - la lumière des projecteurs et du soleil, recalculée (plan.json → projecteurs, soleil) : on sait d'où elle vient,
//   donc quel côté d'une pierre l'attrape et quel côté reste dans l'ombre ; et les reflets brillants qu'elle fait
//   sur le marbre, le bois verni, les tomettes (selon la rugosité, matieres/*_rugosite) ;
// - le relief réel (parallaxe, matieres/*_hauteur) : les joints se creusent quand on bouge, avec l'ombre des bosses ;
// - pas d'effet papier peint (morceaux tirés au hasard, carreaux tournés) et une ombre douce dans les angles.
// Réglages par matière dans plan.json → matieres (scripts/musee_3d.py, MATIERES) ; ceux propres à la page ci-dessous.
import * as THREE from 'three';
import { Q } from './qualite.js';

// Intensité des projecteurs : puissance ÷ 4π (W/sr, la convention de Blender). Mesuré le 28/11/2026 sur les cartes de
// lumière (scratch calib.py : 2 000 points par salle) : au cœur des faisceaux, carte ÷ calcul = 1,01 à 1,06 selon la
// salle, le surplus étant la lumière renvoyée par les murs. Le calcul colle donc aux cartes tel quel.
const SPOT_GAIN = 1.0;
// Soleil de La Garde, comme dans Blender (musee_3d.py, sky_and_sun) : 60 W/m², un peu doré
const SUN = { force: 60, couleur: [1, 0.93, 0.82] };
// Lumière renvoyée par la salle (hors faisceaux), médiane mesurée sur les murs le 28/11/2026 : elle sert à deviner,
// dans la carte, ce qui vient directement des projecteurs (et donc où ils sont cachés par un obstacle)
const AMBIANT = { hall: 9.8, couvent: 0.6, toulouse: 1.6, garde: 1.8, messe: 0.73, montagne: 1.45 };
// Force du relief (pente des cartes de normales) : 1 = telle que Poly Haven la donne. Plan.json → matieres → relief
// pour changer une seule matière.
const BOSSES = {
  sandstone_blocks_05: 1.5, castle_brick_02_white: 1.4, monastery_stone_floor: 1.3, terracotta_floor_tiles: 1.3,
  painted_plaster_wall: 1.0, wood_table_worn: 1.2, herringbone_parquet: 1.0, hinoki_planks: 1.0,
  concrete_floor_02: 0.9, marble_01: 0.5, oak_wood_planks: 1.0,
};
const DOUX = 0.7;          // relief sous la lumière renvoyée (0 : aucun ; 1 : fort), pour qu'il se lise partout
const ANGLES = 0.26;       // ombre douce des angles (l'ombre de contact à l'écran fait le reste)
const PEINTURE = 0.05;     // grain léger des peintures unies (murs blancs, plafonds)
const REFLETS_MURS = 0.5;  // reflets des murs sans réglage « reflets » (pierre, brique, enduit)
const MAX_SPOTS = 8;

// Retouches de shader : plusieurs par matière (surface, reflets), chacune avec sa clé (les programmes compilés
// ne se mélangent pas entre matières qui n'ont pas les mêmes retouches)
export function addPatch(material, key, fn) {
  const patches = material.userData.patches ??= [];
  patches.push({ key, fn });
  material.onBeforeCompile = shader => { for (const p of patches) p.fn(shader); };
  material.customProgramCacheKey = () => patches.map(p => p.key).join('+');
  material.needsUpdate = true;
}

// ---------- Shaders ----------
const PARS = `
varying vec3 vGWorld;
uniform vec3 gSpotPos[ ${MAX_SPOTS} ];
uniform vec3 gSpotDir[ ${MAX_SPOTS} ];
uniform vec3 gSpotCol[ ${MAX_SPOTS} ];   // couleur × intensité
uniform vec2 gSpotCone[ ${MAX_SPOTS} ];  // cosinus du demi-angle, 1 / largeur du fondu (comme Cycles)
uniform int gSpots;
uniform vec3 gSunDir;     // vers le soleil
uniform vec3 gSunCol;     // 0 : pas de soleil dans cette salle
uniform vec4 gSunWin;     // fenêtre où il entre : y0, y1, z0, z1, dans le plan x = gSunX
uniform float gSunX;
uniform vec4 gSky;        // xyz : d'où vient la lumière douce (haut de la salle) ; w : lumière renvoyée estimée
uniform float gClip;      // plus forte lumière qu'une carte peut contenir (8 bits)
uniform vec3 gLmNormal;   // cadres : la normale du mur dont ils prennent la carte (sinon 0)
uniform float gSpecular;
#ifdef G_ROOM
uniform vec4 gRoom;       // x0, x1, z0, z1 de la salle
uniform float gRoomTop;   // hauteur du plafond (très grande sous une voûte : pas d'ombre de plafond)
uniform vec4 gDoors[ 8 ];
uniform float gAO;
float gCorner( float d ) { return 1.0 - gAO * exp( - max( d, 0.0 ) / 0.38 ) * step( 0.0, d ); }
#endif
#ifdef G_PAINT
uniform float gPaint;
#endif
#if defined( G_TEXTURE ) || defined( G_PAINT )
float sHash( vec2 p ) { p = fract( p * vec2( 123.34, 456.21 ) ); p += dot( p, p + 45.32 ); return fract( p.x * p.y ); }
float sNoise( vec2 p ) {
	vec2 i = floor( p ), f = fract( p ), u = f * f * ( 3.0 - 2.0 * f );
	return mix( mix( sHash( i ), sHash( i + vec2( 1.0, 0.0 ) ), u.x ), mix( sHash( i + vec2( 0.0, 1.0 ) ), sHash( i + vec2( 1.0, 1.0 ) ), u.x ), u.y );
}
#endif
#ifdef G_TEXTURE
uniform vec4 gSurface;    // x : variation, y : saturation, z : carreaux par répétition, w : taille d'une répétition (m)
uniform int gMix;         // 0 : texture telle quelle ; 1 : morceaux au hasard ; 2 : carreaux au hasard
uniform sampler2D gNormal;
uniform sampler2D gRough;
uniform float gBump;
vec2 gHash2( vec2 p ) { return fract( sin( vec2( dot( p, vec2( 127.1, 311.7 ) ), dot( p, vec2( 269.5, 183.3 ) ) ) ) * 43758.5453 ); }
// Carreau au hasard : la case prend le dessin d'une autre case de la texture, tourné d'un quart de tour au hasard
vec2 gCell( vec2 uv, out mat2 turn ) {
	float n = gSurface.z;
	vec2 c = floor( uv * n ), f = fract( uv * n ) - 0.5;
	float r = floor( gHash2( c + 0.37 ).x * 4.0 );
	turn = mat2( 1.0 );
	if ( r >= 3.0 ) turn = mat2( 0.0, - 1.0, 1.0, 0.0 );
	else if ( r >= 2.0 ) turn = mat2( - 1.0, 0.0, 0.0, - 1.0 );
	else if ( r >= 1.0 ) turn = mat2( 0.0, 1.0, - 1.0, 0.0 );
	return ( floor( gHash2( c + 5.17 ) * n ) + turn * f + 0.5 ) / n;
}
// Morceaux fondus : trois tirages de la texture, décalés au hasard sur une grille de triangles
void gHexSetup( vec2 uv, out vec2 a, out vec2 b, out vec2 c, out vec3 w ) {
	vec2 st = uv * 2.2;
	vec2 sk = vec2( st.x - 0.57735027 * st.y, 1.15470054 * st.y );
	vec2 base = floor( sk ), fr = fract( sk );
	float z = 1.0 - fr.x - fr.y;
	vec2 ca = base + 1.0, cb = base + vec2( 1.0, 0.0 ), cc = base + vec2( 0.0, 1.0 );
	w = vec3( - z, 1.0 - fr.y, 1.0 - fr.x );
	if ( z > 0.0 ) { w = vec3( z, fr.y, fr.x ); ca = base; cb = base + vec2( 0.0, 1.0 ); cc = base + vec2( 1.0, 0.0 ); }
	a = uv + gHash2( ca ); b = uv + gHash2( cb ); c = uv + gHash2( cc );
}
// Une texture lue aux mêmes endroits que la couleur (même tirage, mêmes poids) : relief et rugosité restent collés au dessin
vec4 gFetch( sampler2D tex, vec2 a, vec2 b, vec2 c, vec3 w, vec2 dx, vec2 dy ) {
	vec4 r = textureGrad( tex, a, dx, dy );
	if ( gMix == 1 ) r = r * w.x + textureGrad( tex, b, dx, dy ) * w.y + textureGrad( tex, c, dx, dy ) * w.z;
	return r;
}
// Repère de la texture sur la surface (monde) : t, b = où u et v augmentent ; n = la surface, tournée vers nous
void gFrame( vec2 dx, vec2 dy, out vec3 t, out vec3 b, out vec3 n ) {
	vec3 dp1 = dFdx( vGWorld ), dp2 = dFdy( vGWorld );
	n = normalize( cross( dp1, dp2 ) );
	vec3 a = cross( dp2, n ), c = cross( n, dp1 );
	t = a * dx.x + c * dy.x;
	b = a * dx.y + c * dy.y;
	t *= inversesqrt( max( dot( t, t ), 1e-24 ) );
	b *= inversesqrt( max( dot( b, b ), 1e-24 ) );
}
#endif
#ifdef G_RELIEF
uniform float gDepth;     // profondeur du relief, en répétitions de texture
uniform sampler2D gHeight;
float gHeightAt( vec2 uv, vec2 dx, vec2 dy ) {
	mat2 t = mat2( 1.0 );
	vec2 at = uv;
	if ( gMix == 2 ) at = gCell( uv, t );
	return textureGrad( gHeight, at, t * dx, t * dy ).r;
}
// Relief : le regard s'enfonce sous la surface jusqu'au fond des joints (« parallax occlusion mapping ») ;
// h : hauteur trouvée (1 : le dessus des pierres, 0 : le fond des joints)
vec2 gParallax( vec2 uv, vec2 dx, vec2 dy, vec3 t, vec3 b, vec3 n, out float h ) {
	vec3 v = normalize( cameraPosition - vGWorld );
	vec3 vt = vec3( dot( v, t ), dot( v, b ), max( dot( v, n ), 0.15 ) );
	float layers = mix( G_LAYERS, 8.0, vt.z ), layer = 1.0 / layers, depth = 0.0;
	vec2 shift = vt.xy / vt.z * gDepth * layer, cur = uv;
	float below = 1.0 - gHeightAt( cur, dx, dy );
	for ( int i = 0; i < int( G_LAYERS ); i ++ ) {
		if ( depth >= below ) break;
		cur -= shift; depth += layer; below = 1.0 - gHeightAt( cur, dx, dy );
	}
	vec2 prev = cur + shift;
	float after = below - depth, before = ( 1.0 - gHeightAt( prev, dx, dy ) ) - depth + layer;
	float w = clamp( after / min( after - before, - 1e-5 ), 0.0, 1.0 );
	h = 1.0 - ( depth - w * layer );
	return mix( cur, prev, w );
}
#endif
#ifdef G_RELIEF_SHADOW
// Ombre du relief : de ce point, la lumière (direction lt, dans le repère de la texture) passe-t-elle au-dessus
// des bosses voisines ? Six pas vers elle ; ombre douce selon de combien la bosse dépasse.
float gReliefShadow( vec2 uv, float h, vec3 lt, vec2 dx, vec2 dy ) {
	vec2 run = lt.xy / max( lt.z, 0.12 ) * gDepth * ( 1.0 - h );
	float shadow = 0.0;
	for ( int i = 1; i <= 6; i ++ ) {
		float f = float( i ) / 6.0;
		float above = gHeightAt( uv + run * f, dx, dy ) - ( h + ( 1.0 - h ) * f );
		shadow = max( shadow, above * ( 1.0 - 0.5 * f ) );
	}
	return 1.0 - clamp( shadow * 5.0, 0.0, 1.0 ) * step( 0.0, lt.z );
}
#endif
`;

// Couleur : relief (parallaxe), tirage au hasard, puis variation de teinte d'un endroit à l'autre
const MAP = `
#ifdef G_TEXTURE
	vec2 gDx = dFdx( vMapUv ), gDy = dFdy( vMapUv );
	vec3 gTw, gBw, gNf;
	gFrame( gDx, gDy, gTw, gBw, gNf );
	vec2 gUv = vMapUv;
	float gH = 1.0;
	#ifdef G_RELIEF
		gUv = gParallax( vMapUv, gDx, gDy, gTw, gBw, gNf, gH );
	#endif
	vec2 gS0 = gUv, gS1 = gUv, gS2 = gUv, gSx = gDx, gSy = gDy;
	vec3 gW = vec3( 1.0, 0.0, 0.0 );
	mat2 gTurn = mat2( 1.0 );
	vec4 sampledDiffuseColor = vec4( 1.0 );
	if ( gMix == 2 ) { gS0 = gCell( gUv, gTurn ); gSx = gTurn * gDx; gSy = gTurn * gDy; }
	if ( gMix == 1 ) {   // le plus clair des trois morceaux l'emporte (comme un relief) : pas de fondu baveux
		gHexSetup( gUv, gS0, gS1, gS2, gW );
		vec4 ca = textureGrad( map, gS0, gDx, gDy ), cb = textureGrad( map, gS1, gDx, gDy ), cc = textureGrad( map, gS2, gDx, gDy );
		const vec3 Y = vec3( 0.3, 0.59, 0.11 );
		gW = pow( gW * ( 1.0 + 1.2 * vec3( dot( ca.rgb, Y ), dot( cb.rgb, Y ), dot( cc.rgb, Y ) ) ), vec3( 5.0 ) );
		gW /= gW.x + gW.y + gW.z;
		sampledDiffuseColor = ca * gW.x + cb * gW.y + cc * gW.z;
	} else sampledDiffuseColor = textureGrad( map, gS0, gSx, gSy );
	diffuseColor *= sampledDiffuseColor;
	{
		vec3 c = max( mix( vec3( dot( diffuseColor.rgb, vec3( 0.2126, 0.7152, 0.0722 ) ) ), diffuseColor.rgb, gSurface.y ), 0.0 );
		vec2 m = vMapUv * gSurface.w;
		float n = sNoise( m / 1.9 ) * 0.65 + sNoise( m / 0.6 + 7.31 ) * 0.35;
		float hue = sNoise( m / 2.7 + 3.7 ) - 0.5;
		float tile = gSurface.z > 0.0 ? sHash( floor( vMapUv * gSurface.z ) + 0.5 ) - 0.5 : 0.0;
		c *= 1.0 + gSurface.x * ( n * 2.0 - 1.0 ) + tile * 0.34;
		c *= vec3( 1.0 + hue * gSurface.x * 0.6 + tile * 0.1, 1.0, 1.0 - hue * gSurface.x * 0.6 - tile * 0.1 );
		diffuseColor.rgb = c;
	}
#else
	#include <map_fragment>
#endif`;

// Ombre douce au pied des murs, dans les coins, sous le plafond (la salle est une boîte : la distance à chaque paroi
// suffit), sauf dans le passage des portes
const CORNERS = `
#include <color_fragment>
#ifdef G_ROOM
{
	vec3 p = vGWorld, n = abs( normalize( cross( dFdx( p ), dFdy( p ) ) ) );
	bool door = false;
	for ( int i = 0; i < 8; i ++ ) {
		vec4 r = gDoors[ i ];
		if ( p.x > r.x && p.x < r.y && p.z > r.z && p.z < r.w ) door = true;
	}
	float ao = 1.0;
	if ( n.x < 0.5 && ! door ) ao *= gCorner( p.x - gRoom.x ) * gCorner( gRoom.y - p.x );
	if ( n.z < 0.5 && ! door ) ao *= gCorner( p.z - gRoom.z ) * gCorner( gRoom.w - p.z );
	if ( n.y < 0.5 ) ao *= gCorner( p.y ) * gCorner( gRoomTop - p.y );
	diffuseColor.rgb *= ao;
}
#endif`;

const ROUGH = `
#include <roughnessmap_fragment>
#ifdef G_TEXTURE
	roughnessFactor *= gFetch( gRough, gS0, gS1, gS2, gW, gSx, gSy ).g;
#endif`;

// Normale : la pente lue dans la carte (même tirage que la couleur), dans le repère de la surface
const NORMAL = `
#include <normal_fragment_maps>
#ifdef G_TEXTURE
{
	vec3 nt = gFetch( gNormal, gS0, gS1, gS2, gW, gSx, gSy ).xyz * 2.0 - 1.0;
	// De loin, les pentes se moyennent (la carte se raccourcit) : le reflet s'élargit d'autant, sans scintiller
	float len = length( nt );
	roughnessFactor = sqrt( roughnessFactor * roughnessFactor + clamp( ( 1.0 - len ) / max( len, 0.1 ), 0.0, 1.0 ) * 0.6 );
	nt.y = - nt.y;   // carte « OpenGL » : le vert monte vers le haut de l'image, c'est-à-dire vers les v décroissants
	nt.xy = nt.xy * gTurn;   // carreau tourné : sa pente tourne avec lui
	nt.xy *= gBump;
	vec3 ns = inverseTransformDirection( normal, viewMatrix );
	vec3 nw = normalize( gTw * nt.x + gBw * nt.y + ns * max( nt.z, 0.05 ) );
	normal = normalize( ( viewMatrix * vec4( nw, 0.0 ) ).xyz );
}
#endif
#ifdef G_PAINT
{   // peinture : un grain très léger, qui ne se voit qu'en lumière rasante
	vec3 ns = inverseTransformDirection( normal, viewMatrix );
	vec3 ta = abs( ns.y ) > 0.5 ? vec3( 1.0, 0.0, 0.0 ) : normalize( vec3( - ns.z, 0.0, ns.x ) );
	vec3 tb = cross( ns, ta );
	vec2 q = vec2( dot( vGWorld, ta ), dot( vGWorld, tb ) ) * 9.0;
	float e = 0.2;
	float h0 = sNoise( q ) + 0.5 * sNoise( q * 2.7 + 3.1 );
	float hx = sNoise( q + vec2( e, 0.0 ) ) + 0.5 * sNoise( ( q + vec2( e, 0.0 ) ) * 2.7 + 3.1 );
	float hy = sNoise( q + vec2( 0.0, e ) ) + 0.5 * sNoise( ( q + vec2( 0.0, e ) ) * 2.7 + 3.1 );
	vec3 nw = normalize( ns - gPaint * ( ta * ( hx - h0 ) + tb * ( hy - h0 ) ) / e );
	normal = normalize( ( viewMatrix * vec4( nw, 0.0 ) ).xyz );
}
#endif`;

// Lumière : la carte de Blender, retouchée là où le relief tourne une pente vers un projecteur (ou le soleil) ou l'en
// détourne, plus les reflets brillants de ces lumières. Ce que la carte donne en plus du calcul (lumière renvoyée par
// la salle) prend un relief plus doux, comme éclairé d'en haut. Là où la carte est plus sombre que le calcul, un
// obstacle cache la lumière : ni relief ni reflet de cette lumière-là.
const LIGHT = `
#if defined( USE_LIGHTMAP ) && defined( RE_IndirectDiffuse )
{
	const vec3 LUMA = vec3( 0.2126, 0.7152, 0.0722 );
	vec3 p = vGWorld;
	vec3 nb = inverseTransformDirection( geometryNormal, viewMatrix );       // avec le relief
	vec3 ns = inverseTransformDirection( nonPerturbedNormal, viewMatrix );   // la surface lisse
	vec3 nl = dot( gLmNormal, gLmNormal ) > 0.5 ? gLmNormal : ns;            // celle pour qui la carte a été calculée
	vec3 v = normalize( cameraPosition - p );
	vec3 flatE = vec3( 0.0 ), bumpE = vec3( 0.0 ), specE = vec3( 0.0 ), toward = vec3( 0.0 );
	for ( int i = 0; i < ${MAX_SPOTS}; i ++ ) {
		if ( i < gSpots ) {
			vec3 d = gSpotPos[ i ] - p;
			float d2 = max( dot( d, d ), 0.04 );
			vec3 L = d * inversesqrt( d2 );
			float c = clamp( ( dot( gSpotDir[ i ], - L ) - gSpotCone[ i ].x ) * gSpotCone[ i ].y, 0.0, 1.0 );
			vec3 e = gSpotCol[ i ] * ( c * c * ( 3.0 - 2.0 * c ) / d2 );
			float cf = max( dot( nl, L ), 0.0 );
			float cb = max( dot( nb, L ), 0.0 ) * smoothstep( - 0.1, 0.1, dot( ns, L ) );
			flatE += e * cf;
			bumpE += e * cb;
			specE += e * ( cb * BRDF_GGX( L, v, nb, material ) );
			toward += L * dot( e * cf, LUMA );
		}
	}
	if ( gSunCol.g > 0.0 ) {   // le soleil : seulement là où son rayon passe par la fenêtre
		vec3 L = gSunDir;
		float t = ( gSunX - p.x ) / L.x;
		vec2 w = p.yz + t * L.yz;
		float inside = step( 0.0, t )
			* smoothstep( gSunWin.x - 0.02, gSunWin.x + 0.02, w.x ) * ( 1.0 - smoothstep( gSunWin.y - 0.02, gSunWin.y + 0.02, w.x ) )
			* smoothstep( gSunWin.z - 0.02, gSunWin.z + 0.02, w.y ) * ( 1.0 - smoothstep( gSunWin.w - 0.02, gSunWin.w + 0.02, w.y ) );
		float cf = max( dot( nl, L ), 0.0 );
		vec3 e = gSunCol * inside;
		// la carte plafonne (8 bits) : on prend le soleil aussi fort qu'elle le montre, pas plus
		e *= min( 1.0, max( gClip - gSky.w, 0.0 ) / max( dot( e, LUMA ) * cf, 1e-4 ) );
		float cb = max( dot( nb, L ), 0.0 ) * smoothstep( - 0.1, 0.1, dot( ns, L ) );
		flatE += e * cf;
		bumpE += e * cb;
		specE += e * ( cb * BRDF_GGX( L, v, nb, material ) );
		toward += L * dot( e * cf, LUMA );
	}
	float lum = dot( lightMapIrradiance, LUMA ), direct = dot( flatE, LUMA );
	float vis = clamp( ( lum - 0.75 * gSky.w ) / max( 0.85 * direct, 1e-3 ), 0.0, 1.0 );
	vec3 bounced = max( lightMapIrradiance - vis * flatE, vec3( 0.0 ) );
	vec3 Lc = normalize( gSky.xyz - p );
	float soft = mix( 1.0, ( 0.5 + 0.5 * dot( nb, Lc ) ) / max( 0.5 + 0.5 * dot( nl, Lc ), 0.15 ), ${DOUX.toFixed(2)} );
	float ss = 1.0;
	#if defined( G_RELIEF_SHADOW ) && defined( G_TEXTURE )
	{
		vec3 dir = normalize( toward + Lc * ( dot( bounced, LUMA ) * 0.3 + 1e-4 ) );
		ss = gReliefShadow( gUv, gH, vec3( dot( dir, gTw ), dot( dir, gBw ), dot( dir, gNf ) ), gDx, gDy );
	}
	#endif
	irradiance += vis * ( bumpE * ss - flatE ) + bounced * ( soft * mix( 1.0, ss, 0.4 ) - 1.0 );
	reflectedLight.directSpecular += specE * ( vis * ss * gSpecular );
}
#endif`;

// ---------- Uniformes ----------
let PLAN = null, DOORS = [];
const linear = c => new THREE.Color().setRGB(c[0], c[1], c[2], THREE.LinearSRGBColorSpace);
const pixel = rgba => { const t = new THREE.DataTexture(new Uint8Array(rgba), 1, 1); t.needsUpdate = true; return t; };
const FLAT = pixel([128, 128, 255, 255]), WHITE = pixel([255, 255, 255, 255]);

// À appeler une fois plan.json lu : les salles, leurs projecteurs, leur soleil ; les portes (pas d'ombre d'angle)
export function preparerMatieres(plan, doors) {
  PLAN = plan;
  DOORS = doors;
}

// Les lumières d'une salle, partagées par toutes ses matières (mêmes objets : rien n'est copié)
const roomLights = {};
function lightsOf(id) {
  if (roomLights[id]) return roomLights[id];
  const spots = (PLAN.projecteurs ?? []).filter(s => s.salle === id).slice(0, MAX_SPOTS);
  const blank = () => new THREE.Vector3();
  const pos = [], dir = [], col = [], cone = [];
  for (let i = 0; i < MAX_SPOTS; i++) {
    const s = spots[i];
    if (!s) { pos.push(blank()); dir.push(new THREE.Vector3(0, -1, 0)); col.push(blank()); cone.push(new THREE.Vector2(1, 1)); continue; }
    const at = new THREE.Vector3(...s.position), cos = Math.cos(s.angle);
    pos.push(at);
    dir.push(new THREE.Vector3(...s.cible).sub(at).normalize());
    col.push(new THREE.Vector3(...s.couleur).multiplyScalar(s.puissance / (4 * Math.PI) * SPOT_GAIN));
    cone.push(new THREE.Vector2(cos, 1 / Math.max((1 - cos) * (s.flou ?? 0.85), 1e-4)));
  }
  const room = PLAN.salles[id], [x0, x1, z0, z1] = room.rect, top = room.hauteur ?? 5;
  const sun = PLAN.soleil?.salle === id ? PLAN.soleil : null;
  roomLights[id] = {
    gSpotPos: { value: pos }, gSpotDir: { value: dir }, gSpotCol: { value: col }, gSpotCone: { value: cone },
    gSpots: { value: spots.length },
    gSunDir: { value: sun ? new THREE.Vector3(...sun.vers_soleil).normalize() : new THREE.Vector3(0, 1, 0) },
    gSunCol: { value: sun ? new THREE.Vector3(...SUN.couleur).multiplyScalar(SUN.force) : blank() },
    gSunWin: { value: sun ? new THREE.Vector4(sun.y[0], sun.y[1], sun.z[0], sun.z[1]) : new THREE.Vector4() },
    gSunX: { value: sun ? sun.x : 0 },
    gSky: { value: new THREE.Vector4((x0 + x1) / 2, top * 0.9, (z0 + z1) / 2, AMBIANT[id] ?? 1.5) },
    gClip: { value: (PLAN.K ?? 6) * Math.PI },
  };
  return roomLights[id];
}

function patch(material, key, defines, uniforms) {
  const head = Object.entries(defines).map(([k, v]) => `#define ${k} ${v}\n`).join('');
  material.userData.uniforms = uniforms;   // pour régler à la main depuis la console (window.__galerie.scene)
  addPatch(material,`${key}:${Object.keys(defines).join(',')}`, shader => {
    Object.assign(shader.uniforms, uniforms);
    shader.vertexShader = shader.vertexShader
      .replace('#include <common>', '#include <common>\nvarying vec3 vGWorld;')
      .replace('#include <worldpos_vertex>', '#include <worldpos_vertex>\nvGWorld = ( modelMatrix * vec4( transformed, 1.0 ) ).xyz;');
    shader.fragmentShader = shader.fragmentShader
      .replace('#include <common>', '#include <common>\n' + head + PARS)
      .replace('#include <map_fragment>', MAP)
      .replace('#include <color_fragment>', CORNERS)
      .replace('#include <roughnessmap_fragment>', ROUGH)
      .replace('#include <normal_fragment_maps>', NORMAL)
      // après la carte de lumière, sans la remplacer (les reflets de la salle retouchent ce même morceau)
      .replace('#include <lights_fragment_maps>', '#include <lights_fragment_maps>\n' + LIGHT);
  });
}

// Murs, sols, plafonds d'une salle (« couvent__pierre ») : spec = plan.json → matieres ; map = la couleur, déjà
// répétée (1 / tuile) ; maps : les autres textures (id + '_n' normales, '_r' rugosité, '_h' hauteurs)
export function roomMaterial({ spec, room, lightMap, lmScale, map, maps }) {
  const textured = Boolean(spec.texture && map);
  const material = new THREE.MeshStandardMaterial({
    map: textured ? map : null,
    color: linear(textured ? spec.teinte : spec.couleur ?? [0.8, 0.8, 0.8]),
    lightMap, lightMapIntensity: lmScale,
    roughness: spec.rugosite ?? (textured ? 1 : 0.9),
    metalness: 0,
  });
  const info = PLAN.salles[room], [x0, x1, z0, z1] = info.rect;
  const defines = { G_ROOM: '' };
  const uniforms = {
    ...lightsOf(room),
    gLmNormal: { value: new THREE.Vector3() },
    gSpecular: { value: 1 },
    gRoom: { value: new THREE.Vector4(x0, x1, z0, z1) },
    gRoomTop: { value: room === 'couvent' ? 99 : info.hauteur ?? 5 },   // sous la voûte du Couvent, pas d'angle au plafond
    gDoors: { value: DOORS },
    gAO: { value: ANGLES },
  };
  if (textured) {
    const id = spec.texture, height = Q.relief && spec.profondeur ? maps[id + '_h'] : null;
    defines.G_TEXTURE = '';
    Object.assign(uniforms, {
      gSurface: { value: new THREE.Vector4(spec.variation ?? 0, spec.saturation ?? 1, spec.carreaux ?? 0, spec.tuile ?? 1) },
      gMix: { value: { hex: 1, carreaux: 2 }[spec.melange] ?? 0 },
      gNormal: { value: maps[id + '_n'] ?? FLAT },
      gRough: { value: maps[id + '_r'] ?? WHITE },
      gBump: { value: spec.relief ?? BOSSES[id] ?? 1 },
    });
    if (height) {
      // 24 couches en « haut » (pierres de 3,5 cm vues de biais), 14 en « moyen »
      Object.assign(defines, { G_RELIEF: '', G_LAYERS: Q.reliefOmbre ? '24.0' : '14.0' });
      if (Q.reliefOmbre) defines.G_RELIEF_SHADOW = '';
      Object.assign(uniforms, { gDepth: { value: spec.profondeur / spec.tuile }, gHeight: { value: height } });
    }
  } else {
    defines.G_PAINT = '';
    uniforms.gPaint = { value: spec.grain ?? PEINTURE };
  }
  patch(material, 'salle', defines, uniforms);
  // reflets de la salle (voir reflections) : les murs sans réglage en ont un peu, comme une pierre ou un enduit mat
  material.userData.reflets = spec.reflets === true ? 1 : spec.reflets ?? REFLETS_MURS;
  return material;
}

// Cadres, bancs : leur propre carte de normales (celle de three.js), et la même lumière des projecteurs (relief des
// baguettes, reflets sur le bois verni ou la dorure). wallNormal : un cadre prend la carte de lumière du mur derrière
// lui ; la lumière de la carte est donc celle que reçoit le mur (sa normale), pas le dessus ou le côté de la baguette.
export function objectShading(material, room, wallNormal = null) {
  if (!PLAN || !PLAN.salles[room] || !material.lightMap) return material;
  patch(material, 'objet', {}, {
    ...lightsOf(room),
    gLmNormal: { value: wallNormal ? wallNormal.clone().normalize() : new THREE.Vector3() },
    gSpecular: { value: 1 },
  });
  return material;
}

// Une texture de relief (normales, rugosité) pour un objet : répétée comme sa couleur, à la convention de la page
// (coordonnées glTF, sans retournement : le vert de la carte « OpenGL » descend, d'où normalScale.y négatif)
export function objectMaps(maps, id, tile, strength = BOSSES[id] ?? 1) {
  const repeat = key => {
    if (!maps[key]) return null;
    const t = maps[key].clone();
    t.wrapS = t.wrapT = THREE.RepeatWrapping;
    t.repeat.set(1 / tile, 1 / tile);
    t.needsUpdate = true;
    return t;
  };
  const normalMap = repeat(id + '_n'), roughnessMap = repeat(id + '_r');
  const out = {};
  if (normalMap) Object.assign(out, { normalMap, normalScale: new THREE.Vector2(strength, -strength) });
  if (roughnessMap) out.roughnessMap = roughnessMap;
  return out;
}
