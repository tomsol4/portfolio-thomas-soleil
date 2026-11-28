// Effets d'image de la visite, comme dans un jeu vidéo récent (écrits à la main sur three.js, sans module en plus).
// - La scène est d'abord dessinée dans une image « HDR » (des lumières plus fortes que le blanc), bords lissés (MSAA).
// - Ombres de contact (SSAO) : là où deux surfaces se touchent (pied des bancs, bord des cadres, angles des salles,
//   embrasures des portes), un peu d'ombre, calculée d'après la profondeur de chaque point de l'image.
// - Halo (bloom) : les lumières fortes (verrière, tache de soleil, fenêtres) débordent un peu autour d'elles.
// - Image finale : la même courbe de tons que Blender (toneCurve dans galerie.js), un peu de netteté, vignetage et
//   grain de pellicule à peine visibles.
// Les photos accrochées et le ciel ne passent par aucun de ces effets : leurs couleurs restent exactement les vraies.
// Qualité « bas » (téléphones) ou adresse « index.html?effets=0 » : rien de tout ça, la scène est dessinée directement
// à l'écran, comme avant.
import * as THREE from 'three';
import { Q } from './qualite.js';

// Réglages, modifiables en direct pour essayer : window.__galerie.effets.reglages (puis bouger un peu)
export const REGLAGES = {
  ombre: 2.5,        // force des ombres de contact (0 : aucune)
  rayon: 0.5,        // portée des ombres de contact (m)
  halo: 0.05,        // force du halo
  seuil: 3.5,        // lumière à partir de laquelle le halo apparaît (valeur HDR ; murs ≈ 0,1 à 5, blanc pur ≈ 9)
  cielHalo: 6,       // le ciel des fenêtres compte comme une lumière de cette force dans le halo
  nettete: 0.3,      // netteté (0 : aucune, 1 : forte)
  vignette: 0.06,    // assombrissement des coins de l'image
  grain: 0.008,      // grain de pellicule (en part du blanc)
  saturation: 1.03,  // 1 : couleurs telles quelles
};

// Effets à l'écran ? (galerie.js crée le moteur sans lissage quand les effets lissent eux-mêmes)
// index.html?effets=0 : sans effets ; ?effets=ombres : seulement les ombres de contact, en gris (pour les régler)
const ASKED = new URLSearchParams(location.search).get('effets');
export const EFFETS = Q.niveau !== 'bas' && ASKED !== '0';
export const PIXELS = Q.pixels;

// Les photos et le ciel s'inscrivent dans l'image HDR avec cette marque (dans la transparence) : « à montrer tel quel »
const TEL_QUEL = -1000;

const PLEIN_ECRAN = `
varying vec2 vUv;
void main() {
	vUv = position.xy * 0.5 + 0.5;
	gl_Position = vec4( position.xy, 0.0, 1.0 );
}`;

// Profondeur → distance à l'œil (m), en demi-résolution : un pixel sur quatre
const PROFONDEUR = `
uniform highp sampler2D tDepth;
uniform vec2 clip;   // proche, loin
void main() {
	ivec2 size = textureSize( tDepth, 0 );
	float d = texelFetch( tDepth, min( ivec2( gl_FragCoord.xy ) * 2, size - 1 ), 0 ).r;
	gl_FragColor = vec4( clip.x * clip.y / ( clip.y - ( clip.y - clip.x ) * d ), 0.0, 0.0, 1.0 );
}`;

// Ombres de contact : autour de chaque point, des échantillons en spirale (plus serrés près du centre) ; un voisin
// placé « au-dessus » de la surface (du côté de sa normale) et proche cache une part du ciel : un peu d'ombre.
const OMBRES = `
uniform highp sampler2D tZ;
uniform vec2 clip;
uniform vec4 proj;      // 1 / P00, 1 / P11, décentrage x, y
uniform vec2 full;      // taille de l'image entière (pixels)
uniform float radius, strength, projScale;
const int N = 14;
vec3 pos( ivec2 q, float d ) {
	vec2 ndc = ( vec2( q * 2 ) + 0.5 ) / full * 2.0 - 1.0;
	return vec3( ( ndc + proj.zw ) * proj.xy * d, - d );
}
vec3 at( ivec2 q, ivec2 size ) { q = clamp( q, ivec2( 0 ), size - 1 ); return pos( q, texelFetch( tZ, q, 0 ).r ); }
float ign( vec2 p ) { return fract( 52.9829189 * fract( dot( p, vec2( 0.06711056, 0.00583715 ) ) ) ); }
void main() {
	ivec2 p = ivec2( gl_FragCoord.xy ), size = textureSize( tZ, 0 );
	float d = texelFetch( tZ, p, 0 ).r;
	if ( d > clip.y * 0.98 ) { gl_FragColor = vec4( 1.0, d, 0.0, 1.0 ); return; }   // le ciel
	vec3 P = pos( p, d );
	// normale d'après les voisins, du côté le plus proche en profondeur (pour ne pas mélanger deux objets)
	vec3 l = at( p - ivec2( 1, 0 ), size ), r = at( p + ivec2( 1, 0 ), size );
	vec3 b = at( p - ivec2( 0, 1 ), size ), t = at( p + ivec2( 0, 1 ), size );
	vec3 dx = abs( r.z - P.z ) < abs( P.z - l.z ) ? r - P : P - l;
	vec3 dy = abs( t.z - P.z ) < abs( P.z - b.z ) ? t - P : P - b;
	vec3 n = normalize( cross( dx, dy ) );
	float px = min( radius * projScale / d, 90.0 );   // le rayon à l'écran, en pixels
	float turn = 6.2831853 * ign( gl_FragCoord.xy ), shift = ign( gl_FragCoord.yx + 31.0 );
	float r2 = radius * radius, sum = 0.0;
	for ( int i = 0; i < N; i ++ ) {
		float a = ( float( i ) + shift ) / float( N );
		float angle = a * 6.2831853 * 5.0 + turn;
		vec2 off = vec2( cos( angle ), sin( angle ) ) * ( 1.0 + ( px - 1.0 ) * a * a );
		vec3 v = at( p + ivec2( round( off ) ), size ) - P;
		float vv = dot( v, v );
		float cosine = dot( v, n ) * inversesqrt( vv + 1e-8 );
		sum += max( cosine - 0.1, 0.0 ) * max( 1.0 - vv / r2, 0.0 );
	}
	float ao = clamp( 1.0 - strength * sum / ( 0.9 * float( N ) ), 0.0, 1.0 );
	gl_FragColor = vec4( ao, d, 0.0, 1.0 );
}`;

// Flou des ombres, en ligne puis en colonne, sans déborder d'un objet sur l'autre : les voisins qui ne sont pas sur
// le même plan que le point (d'après 1 / distance, qui varie en ligne droite le long d'un plan) ne comptent pas
const FLOU = `
uniform highp sampler2D tAO;
uniform ivec2 dir;
void main() {
	ivec2 p = ivec2( gl_FragCoord.xy ), size = textureSize( tAO, 0 );
	vec2 c = texelFetch( tAO, p, 0 ).rg;
	float i0 = 1.0 / c.g;
	float il = 1.0 / texelFetch( tAO, clamp( p - dir, ivec2( 0 ), size - 1 ), 0 ).g;
	float ir = 1.0 / texelFetch( tAO, clamp( p + dir, ivec2( 0 ), size - 1 ), 0 ).g;
	float slope = abs( i0 - il ) < abs( ir - i0 ) ? i0 - il : ir - i0;
	float sum = c.r, total = 1.0;
	for ( int i = - 4; i <= 4; i ++ ) {
		if ( i == 0 ) continue;
		vec2 s = texelFetch( tAO, clamp( p + dir * i, ivec2( 0 ), size - 1 ), 0 ).rg;
		float plane = abs( 1.0 / s.g - ( i0 + slope * float( i ) ) ) / i0;
		float w = exp( - float( i * i ) / 12.0 ) * max( 0.0, 1.0 - plane * 60.0 );
		sum += s.r * w;
		total += w;
	}
	gl_FragColor = vec4( sum / total, c.g, 0.0, 1.0 );
}`;

// Halo, première réduction (image entière → moitié) : 4 lectures qui couvrent 4 × 4 pixels, seulement la lumière
// au-dessus du seuil ; les photos n'y comptent pas, le ciel compte comme une lumière (cielHalo)
const HALO_SEUIL = `
uniform sampler2D tHDR;
uniform highp sampler2D tDepth;
uniform vec2 texel;   // taille d'un pixel de l'image entière
uniform float threshold, sky;
varying vec2 vUv;
vec3 tap( vec2 uv ) {
	vec4 c = texture2D( tHDR, uv );
	float mark = clamp( ( 1.0 - c.a ) / ${1 - TEL_QUEL}.0, 0.0, 1.0 );
	float isSky = texture2D( tDepth, uv ).r >= 1.0 ? sky : 0.0;
	c.rgb *= 1.0 - mark + mark * isSky;
	return c.rgb / ( 1.0 + max( c.r, max( c.g, c.b ) ) );   // moyenne pondérée : un pixel très fort ne scintille pas
}
void main() {
	vec3 c = tap( vUv + texel * vec2( - 1.0, - 1.0 ) ) + tap( vUv + texel * vec2( 1.0, - 1.0 ) )
		+ tap( vUv + texel * vec2( - 1.0, 1.0 ) ) + tap( vUv + texel * vec2( 1.0, 1.0 ) );
	c *= 0.25;
	c /= max( 1.0 - max( c.r, max( c.g, c.b ) ), 1e-3 );
	float bright = max( c.r, max( c.g, c.b ) ), knee = threshold * 0.5;
	float soft = clamp( bright - threshold + knee, 0.0, 2.0 * knee );
	soft = soft * soft / ( 4.0 * knee + 1e-5 );
	c *= max( soft, bright - threshold ) / max( bright, 1e-5 );
	gl_FragColor = vec4( c, 1.0 );
}`;

// Halo, réductions suivantes : 13 lectures (comme Call of Duty, 2014), sans crénelage quand on bouge
const HALO_REDUIRE = `
uniform sampler2D tSrc;
uniform vec2 texel;
varying vec2 vUv;
vec3 T( float x, float y ) { return texture2D( tSrc, vUv + texel * vec2( x, y ) ).rgb; }
void main() {
	vec3 c = T( 0.0, 0.0 ) * 0.125;
	c += ( T( - 2.0, 2.0 ) + T( 2.0, 2.0 ) + T( - 2.0, - 2.0 ) + T( 2.0, - 2.0 ) ) * 0.03125;
	c += ( T( 0.0, 2.0 ) + T( - 2.0, 0.0 ) + T( 2.0, 0.0 ) + T( 0.0, - 2.0 ) ) * 0.0625;
	c += ( T( - 1.0, 1.0 ) + T( 1.0, 1.0 ) + T( - 1.0, - 1.0 ) + T( 1.0, - 1.0 ) ) * 0.125;
	gl_FragColor = vec4( c, 1.0 );
}`;

// Halo, remontée : l'étage plus petit, adouci (tente 3 × 3), s'ajoute à l'étage du dessus
const HALO_AGRANDIR = `
uniform sampler2D tSrc;
uniform vec2 texel;
varying vec2 vUv;
vec3 T( float x, float y ) { return texture2D( tSrc, vUv + texel * vec2( x, y ) ).rgb; }
void main() {
	vec3 c = T( 0.0, 0.0 ) * 4.0;
	c += ( T( - 1.0, 0.0 ) + T( 1.0, 0.0 ) + T( 0.0, - 1.0 ) + T( 0.0, 1.0 ) ) * 2.0;
	c += T( - 1.0, - 1.0 ) + T( 1.0, - 1.0 ) + T( - 1.0, 1.0 ) + T( 1.0, 1.0 );
	gl_FragColor = vec4( c / 16.0, 1.0 );
}`;

// Image finale : netteté, ombres de contact, halo, courbe de tons de Blender, couleurs, vignetage, grain ;
// les photos et le ciel (marqués) restent tels quels
const FINAL = `
uniform sampler2D tHDR;
uniform highp sampler2D tDepth;
uniform highp sampler2D tAO;
uniform sampler2D tBloom;
uniform vec2 clip;
uniform float sharpen, shadow, bloom, vignette, grain, saturation, time;
varying vec2 vUv;
vec3 squeeze( vec3 c ) { return c / ( 1.0 + c ); }
float hash( vec2 p ) { vec3 q = fract( vec3( p.xyx ) * 0.1031 ); q += dot( q, q.yzx + 33.33 ); return fract( ( q.x + q.y ) * q.z ); }
void main() {
	ivec2 p = ivec2( gl_FragCoord.xy ), size = textureSize( tHDR, 0 );
	gl_FragDepth = texelFetch( tDepth, p, 0 ).r;   // la profondeur de la scène, pour le rayon de soleil dessiné après
	vec4 c = texelFetch( tHDR, p, 0 );
	float mark = clamp( ( 1.0 - c.a ) / ${1 - TEL_QUEL}.0, 0.0, 1.0 );
	vec3 color = c.rgb;
	// netteté adaptée au contraste (« CAS » d'AMD), sur une version tassée de la lumière (les très fortes ne débordent pas)
	if ( sharpen > 0.0 ) {
		vec3 n = squeeze( texelFetch( tHDR, min( p + ivec2( 0, 1 ), size - 1 ), 0 ).rgb );
		vec3 s = squeeze( texelFetch( tHDR, max( p - ivec2( 0, 1 ), ivec2( 0 ) ), 0 ).rgb );
		vec3 e = squeeze( texelFetch( tHDR, min( p + ivec2( 1, 0 ), size - 1 ), 0 ).rgb );
		vec3 w = squeeze( texelFetch( tHDR, max( p - ivec2( 1, 0 ), ivec2( 0 ) ), 0 ).rgb );
		vec3 m = squeeze( color );
		vec3 lo = min( m, min( min( n, s ), min( e, w ) ) ), hi = max( m, max( max( n, s ), max( e, w ) ) );
		vec3 amp = sqrt( clamp( min( lo, 1.0 - hi ) / max( hi, 1e-4 ), 0.0, 1.0 ) );
		vec3 k = - amp * mix( 0.125, 0.2, sharpen );
		vec3 r = clamp( ( m + k * ( n + s + e + w ) ) / ( 1.0 + 4.0 * k ), 0.0, 0.999 );
		color = r / ( 1.0 - r );
	}
#ifdef AO
	{
		// ombres calculées en demi-résolution : les 4 voisines, celles à la même distance que le pixel comptent le plus
		float z = clip.x * clip.y / ( clip.y - ( clip.y - clip.x ) * texelFetch( tDepth, p, 0 ).r );
		ivec2 half_ = textureSize( tAO, 0 );
		vec2 h = vec2( p ) * 0.5;
		ivec2 b = ivec2( h );
		vec2 f = h - vec2( b );
		float sum = 0.0, total = 1e-5;
		for ( int j = 0; j < 2; j ++ ) for ( int i = 0; i < 2; i ++ ) {
			vec2 s = texelFetch( tAO, min( b + ivec2( i, j ), half_ - 1 ), 0 ).rg;
			float w = ( i == 0 ? 1.0 - f.x : f.x ) * ( j == 0 ? 1.0 - f.y : f.y );
			w *= 1.0 / ( 0.002 + abs( s.g - z ) / z );
			sum += s.r * w;
			total += w;
		}
		float ao = sum / total;
		color *= mix( 1.0, ao, shadow );
	#ifdef VOIR_OMBRES
		gl_FragColor = vec4( vec3( ao ), 1.0 );
		return;
	#endif
	}
#endif
#ifdef HALO
	color += texture2D( tBloom, vUv ).rgb * bloom;
#endif
#ifdef TONE_MAPPING
	color = toneMapping( color );
#endif
	color = max( mix( vec3( dot( color, vec3( 0.2126, 0.7152, 0.0722 ) ) ), color, saturation ), 0.0 );
	vec2 q = vUv - 0.5;
	float r2 = dot( q, q ) * 2.0;
	color *= 1.0 - vignette * r2 * r2;
	vec3 shown = linearToOutputTexel( vec4( color, 1.0 ) ).rgb;
	// grain : deux tirages au hasard (bruit en triangle), plus visible dans les tons moyens ; il ne bouge que quand on bouge
	float noise = hash( gl_FragCoord.xy + time * 17.0 ) + hash( gl_FragCoord.xy * 1.37 + time * 31.0 + 7.0 ) - 1.0;
	float l = dot( shown, vec3( 0.333 ) );
	shown += noise * ( grain * 4.0 * l * ( 1.0 - l ) + 0.5 / 255.0 );
	vec3 asIs = linearToOutputTexel( vec4( c.rgb, 1.0 ) ).rgb;
	gl_FragColor = vec4( mix( shown, asIs, mark ), 1.0 );
}`;

export function effets(renderer, scene, camera) {
  const direct = {
    actif: false,
    render() { renderer.render(scene, camera); },
    compile() { renderer.compile(scene, camera); },
    setSize() {},
    telQuel() {},
    reglages: REGLAGES,
  };
  if (!EFFETS || !renderer.extensions.has('EXT_color_buffer_float')) return direct;

  // Le ciel (fond de la scène) marqué « tel quel », comme les photos (voir telQuel)
  const lib = THREE.ShaderLib.backgroundCube;
  lib.fragmentShader = lib.fragmentShader.replace('#include <colorspace_fragment>',
    `#include <colorspace_fragment>\n\tgl_FragColor.a = ${TEL_QUEL}.0;`);

  const nearest = { minFilter: THREE.NearestFilter, magFilter: THREE.NearestFilter, depthBuffer: false };
  const hdr = new THREE.WebGLRenderTarget(1, 1, {
    type: THREE.HalfFloatType, samples: Q.msaa, depthTexture: new THREE.DepthTexture(1, 1),
  });
  const zHalf = new THREE.WebGLRenderTarget(1, 1, { ...nearest, type: THREE.FloatType, format: THREE.RedFormat });
  const aoA = new THREE.WebGLRenderTarget(1, 1, { ...nearest, type: THREE.HalfFloatType, format: THREE.RGFormat });
  const aoB = aoA.clone();
  const LEVELS = 6;
  const bloom = Array.from({ length: LEVELS }, () => new THREE.WebGLRenderTarget(1, 1, { type: THREE.HalfFloatType, depthBuffer: false }));

  const pass = (fragmentShader, uniforms, options = {}) => new THREE.ShaderMaterial({
    vertexShader: PLEIN_ECRAN, fragmentShader, uniforms, depthTest: false, depthWrite: false, toneMapped: false, ...options,
  });
  const clip = { value: new THREE.Vector2() };
  const depthMat = pass(PROFONDEUR, { tDepth: { value: hdr.depthTexture }, clip });
  const aoMat = pass(OMBRES, {
    tZ: { value: zHalf.texture }, clip, proj: { value: new THREE.Vector4() }, full: { value: new THREE.Vector2() },
    radius: { value: 0 }, strength: { value: 0 }, projScale: { value: 0 },
  });
  const blurH = pass(FLOU, { tAO: { value: aoA.texture }, dir: { value: [1, 0] } });
  const blurV = pass(FLOU, { tAO: { value: aoB.texture }, dir: { value: [0, 1] } });
  const prefilter = pass(HALO_SEUIL, {
    tHDR: { value: hdr.texture }, tDepth: { value: hdr.depthTexture }, texel: { value: new THREE.Vector2() },
    threshold: { value: 0 }, sky: { value: 0 },
  });
  const down = bloom.slice(0, -1).map(src => pass(HALO_REDUIRE, { tSrc: { value: src.texture }, texel: { value: new THREE.Vector2() } }));
  const add = { blending: THREE.CustomBlending, blendSrc: THREE.OneFactor, blendDst: THREE.OneFactor, blendEquation: THREE.AddEquation };
  const up = bloom.slice(1).map(src => pass(HALO_AGRANDIR, { tSrc: { value: src.texture }, texel: { value: new THREE.Vector2() } }, add));
  const defines = {};
  if (Q.ao) defines.AO = '';
  if (Q.halo) defines.HALO = '';
  if (ASKED === 'ombres') defines.VOIR_OMBRES = '';
  const finalMat = pass(FINAL, {
    tHDR: { value: hdr.texture }, tDepth: { value: hdr.depthTexture }, tAO: { value: aoA.texture },
    tBloom: { value: bloom[0].texture }, clip,
    sharpen: { value: 0 }, shadow: { value: 0 }, bloom: { value: 0 }, vignette: { value: 0 }, grain: { value: 0 }, saturation: { value: 1 },
    time: { value: 0 },
  }, { defines, toneMapped: true, depthTest: true, depthWrite: true, depthFunc: THREE.AlwaysDepth });

  // Les objets en mélange additif (le rayon de soleil de La Garde) sont réglés pour s'ajouter à l'image finale, en
  // couleurs d'écran : ils sont dessinés après les effets, par-dessus, exactement comme avant (voir compile)
  let overlays = [];

  // Un triangle qui couvre tout l'écran
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.Float32BufferAttribute([-1, -1, 0, 3, -1, 0, -1, 3, 0], 3));
  const quad = new THREE.Mesh(geometry, depthMat);
  quad.frustumCulled = false;
  const quadScene = new THREE.Scene(), quadCamera = new THREE.Camera();
  quadScene.add(quad);
  const draw = (material, target) => {
    quad.material = material;
    renderer.setRenderTarget(target);
    renderer.render(quadScene, quadCamera);
  };

  const size = new THREE.Vector2();
  function setSize() {
    renderer.getDrawingBufferSize(size);
    const w = Math.max(1, size.x), h = Math.max(1, size.y);
    hdr.setSize(w, h);
    const hw = Math.ceil(w / 2), hh = Math.ceil(h / 2);
    for (const t of [zHalf, aoA, aoB]) t.setSize(hw, hh);
    bloom.forEach((t, i) => t.setSize(Math.max(1, Math.round(w / 2 ** (i + 1))), Math.max(1, Math.round(h / 2 ** (i + 1)))));
    prefilter.uniforms.texel.value.set(1 / w, 1 / h);
    down.forEach((m, i) => m.uniforms.texel.value.set(1 / bloom[i].width, 1 / bloom[i].height));
    up.forEach((m, i) => m.uniforms.texel.value.set(1 / bloom[i + 1].width, 1 / bloom[i + 1].height));
    aoMat.uniforms.full.value.set(w, h);
  }

  let time = 0;
  function render() {
    const R = REGLAGES, autoClear = renderer.autoClear;
    for (const o of overlays) o.visible = false;
    renderer.setRenderTarget(hdr);
    renderer.render(scene, camera);
    for (const o of overlays) o.visible = true;
    renderer.autoClear = false;
    clip.value.set(camera.near, camera.far);
    const ao = Q.ao && R.ombre > 0, halo = Q.halo && R.halo > 0;
    if (ao) {
      const e = camera.projectionMatrix.elements;
      aoMat.uniforms.proj.value.set(1 / e[0], 1 / e[5], e[8], e[9]);
      aoMat.uniforms.projScale.value = aoA.height * e[5] / 2;
      aoMat.uniforms.radius.value = R.rayon;
      aoMat.uniforms.strength.value = R.ombre;
      draw(depthMat, zHalf);
      draw(aoMat, aoA);
      draw(blurH, aoB);
      draw(blurV, aoA);
    }
    if (halo) {
      prefilter.uniforms.threshold.value = R.seuil;
      prefilter.uniforms.sky.value = R.cielHalo;
      draw(prefilter, bloom[0]);
      down.forEach((m, i) => draw(m, bloom[i + 1]));
      for (let i = up.length - 1; i >= 0; i--) draw(up[i], bloom[i]);
    }
    const u = finalMat.uniforms;
    u.sharpen.value = R.nettete;
    u.shadow.value = ao ? 1 : 0;
    u.bloom.value = halo ? R.halo : 0;
    u.vignette.value = R.vignette;
    u.grain.value = R.grain;
    u.saturation.value = R.saturation;
    u.time.value = time = (time + 1) % 64;
    draw(finalMat, null);
    for (const o of overlays) renderer.render(o, camera);
    renderer.autoClear = autoClear;
  }

  return {
    actif: true,
    render,
    // préparer les programmes de la scène pour l'image HDR (pas pour l'écran : ce ne sont pas les mêmes)
    compile() {
      overlays = [];
      scene.traverse(o => { if (o.isMesh && o.visible && o.material?.blending === THREE.AdditiveBlending) overlays.push(o); });
      renderer.setRenderTarget(hdr);
      renderer.compile(scene, camera);
      renderer.setRenderTarget(null);
    },
    setSize,
    // Retouche de shader des photos : marquées « telles quelles » dans l'image HDR (ni courbe de tons, ni effets)
    telQuel(shader) {
      shader.fragmentShader = shader.fragmentShader.replace('#include <dithering_fragment>',
        `#include <dithering_fragment>\n\tgl_FragColor.a = ${TEL_QUEL}.0;`);
    },
    reglages: REGLAGES,
    hdr,
  };
}
