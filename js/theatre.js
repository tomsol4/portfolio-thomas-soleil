(() => {
    'use strict';
    const stage = document.querySelector('[data-theatre]');
    if (!stage) return;
    const motion = matchMedia('(prefers-reduced-motion: reduce)');
    const curtain = stage.querySelector('.concert-curtain');
    const canvas = curtain.querySelector('canvas');
    const photo = stage.querySelector('.concert-cover img');
    const replay = stage.querySelector('.theatre-replay');
    const nav = document.querySelector('.site-nav');
    const reveals = [...document.querySelectorAll(
        '.concert-reportages .collection-link, .concert-mosaic-photo, #presentation .personal-copy')];
    let observer;
    const entranceKey = 'concerts.theatre.entered';

    function entranceRemembered() {
        try {
            if (sessionStorage.getItem(entranceKey) === 'yes') return true;
        } catch (_) {}
        return Boolean(history.state?.concertTheatreEntered);
    }

    function rememberEntrance() {
        try { sessionStorage.setItem(entranceKey, 'yes'); } catch (_) {}
        try { history.replaceState({ ...history.state, concertTheatreEntered: true }, ''); } catch (_) {}
    }

    // L'ouverture ne se joue qu'à la première visite de la session.
    let entered = Boolean(location.hash || window.scrollY > 50 || entranceRemembered() || motion.matches);

    // Le rideau : un velours calculé image par image (plis irréguliers, éclairage de scène fixe), posé sur le plancher,
    // avec le lambrequin derrière le menu. En millisecondes : il attend, ses deux pans s'écartent vers les côtés
    // (le bas suit le haut avec retard), puis le bas du tissu se balance un peu et se pose, froncé de chaque côté.
    const HOLD = 600, OPEN = 2400, LAG = 300, SETTLE = 1000, END_FIRST = HOLD + OPEN + LAG + SETTLE;
    // « Rejouer » : les pans se referment, un temps, puis se rouvrent.
    const CLOSE = 1100, PAUSE = 350, END_REPLAY = CLOSE + PAUSE + OPEN + LAG + SETTLE;
    const clamp01 = v => Math.min(Math.max(v, 0), 1);
    const smooth = (a, b, v) => { const x = clamp01((v - a) / (b - a)); return x * x * (3 - 2 * x); };
    const smoother = p => { p = clamp01(p); return p * p * p * (p * (p * 6 - 15) + 10); };
    let replaying = false;
    const begin = () => replaying ? CLOSE + PAUSE : HOLD;
    const end = () => replaying ? END_REPLAY : END_FIRST;
    // Part du chemin parcourue par le haut d'un pan (0 fermé, 1 froncé sur le côté).
    function openAt(ms) {
        if (replaying && ms < CLOSE) return 1 - smoother(ms / CLOSE);
        return smoother((ms - begin()) / OPEN);
    }

    const VERT = 'attribute vec2 a;void main(){gl_Position=vec4(a,0.,1.);}';
    const FRAG = `precision highp float;
uniform vec2 uRes, uView, uOpenL, uOpenR;
uniform float uScale, uHc, uFloorH, uP, uTime, uSway, uSwayX, uRipple, uSpill, uApron, uHem, uStack, uOv, uSwingL, uSwingR, uShadow, uValH, uSwag;
float hash11(float p){ p = fract(p*.1031); p *= p + 33.33; p *= p + p; return fract(p); }
float hash12(vec2 p){ vec3 q = fract(vec3(p.xyx)*.1031); q += dot(q, q.yzx + 33.33); return fract((q.x + q.y)*q.z); }
float noise1(float x){ float i = floor(x), f = fract(x); return mix(hash11(i), hash11(i + 1.), f*f*(3. - 2.*f)); }
float vnoise(vec2 p){ vec2 i = floor(p), f = fract(p), u = f*f*(3. - 2.*f);
  return mix(mix(hash12(i), hash12(i + vec2(1., 0.)), u.x), mix(hash12(i + vec2(0., 1.)), hash12(i + vec2(1.)), u.x), u.y); }
// Bruit et sa pente, pour le léger gonflement du tissu.
vec3 vnoised(vec2 p){
  vec2 i = floor(p), f = fract(p), u = f*f*(3. - 2.*f), du = 6.*f*(1. - f);
  float a = hash12(i), b = hash12(i + vec2(1., 0.)), c = hash12(i + vec2(0., 1.)), d = hash12(i + vec2(1.)), k = a - b - c + d;
  return vec3(a + (b - a)*u.x + (c - a)*u.y + k*u.x*u.y, du*vec2(b - a + k*u.y, c - a + k*u.x));
}
vec3 tonemap(vec3 c){ return pow(1. - exp(-c*1.6), vec3(1./2.2)); }
// Position des plis (F) et ses pentes : pas irrégulier, plis qui serpentent vers le bas, ondulation quand le tissu bouge.
vec3 foldF(float s, float tf){
  float q = (s - uSwayX*tf*tf)/uP;
  float a1 = q*.61 + 1.3, a2 = q*1.37 + 4.1, a3 = q*2.9 + .7, b = q*.5 + tf*3.1 + 1.;
  float F = q + .20*sin(a1) + .12*sin(a2) + .05*sin(a3) + .07*sin(b);
  float Fq = 1. + .122*cos(a1) + .1644*cos(a2) + .145*cos(a3) + .035*cos(b);
  float Ft = .217*cos(b);
  float m = tf*sqrt(tf), c1 = q*.83 + tf*2.1 + 2., c2 = q*1.9 - tf*3.3 + 5.;
  float w = .16*sin(c1) + .08*sin(c2);
  F += m*w;
  Fq += m*(.1328*cos(c1) + .152*cos(c2));
  Ft += 1.5*sqrt(tf)*w + m*(.336*cos(c1) - .264*cos(c2));
  float r = 6.2832*(tf*1.3 - uTime*.9) + q*.35;
  F += uRipple*tf*tf*sin(r);
  Fq += uRipple*tf*tf*.35*cos(r);
  Ft += uRipple*(2.*tf*sin(r) + tf*tf*8.168*cos(r));
  Ft -= Fq*2.*uSwayX*tf/uP;
  return vec3(F, Fq/uP, Ft);
}
// x : profondeur vers le spectateur (px), y : profil (-1 creux, 1 crête), z : pente le long du tissu, w : pente vers le bas (par hauteur de rideau).
vec4 foldD(float s, float t, out float amp){
  float tf = clamp(t/uHc, 0., 1.1);
  vec3 F = foldF(s, tf);
  float ph = 6.2832*F.x;
  float u = max(.5 + .5*cos(ph), 1e-4), p = pow(u, .72);
  float prof = 2.*p - 1. + .10*sin(2.*ph + .8);
  float dprof = -.72*p/u*sin(ph) + .20*cos(2.*ph + .8);
  amp = (.70 + .60*noise1(F.x*.83 + 3.7))*(.84 + .24*min(tf, 1.))*(.80 + .40*vnoise(vec2(F.x*.9, tf*2.6)));
  float A = .46*uP*amp;
  vec3 bulge = vnoised(vec2(s/(4.5*uP), t/(uHc*.55)));         // le tissu ne pend pas tout à fait à plat
  return vec4(A*prof + (bulge.x - .5)*.9*uP, prof, A*dprof*6.2832*F.y + bulge.y*.2, A*dprof*6.2832*F.z + bulge.z*.9*uP/.55);
}
// Bord intérieur de chaque pan : droit quand le rideau est fermé ; une fois ouvert, le pan froncé se resserre à mi-hauteur.
float shapeF(float tf){ float d = (tf - .56)/.32; return 1. - .26*exp(-d*d); }
float edgeL(float tf){ return mix(uView.x*.5 + uOv, uStack*shapeF(tf), mix(uOpenL.x, uOpenL.y, pow(tf, 1.4))) + uSwingL*tf*tf; }
float edgeR(float tf){ return uView.x - mix(uView.x*.5 + uOv, uStack*1.03*shapeF(tf), mix(uOpenR.x, uOpenR.y, pow(tf, 1.4))) - uSwingR*tf*tf; }
float paneWidth(float tf, float side){ return side > 0. ? uView.x - edgeR(tf) : edgeL(tf); }
// Un pan de velours vu au point (x, y) : il se fronce régulièrement entre son côté et son bord intérieur.
// Très froncés, les plis se tassent les uns contre les autres : on en voit moins, mais plus ronds.
vec4 cloth(float x, float y, float side){
  float tf = clamp(y/uHc, 0., 1.), hw = uView.x*.5 + uOv;
  float w = paneWidth(tf, side);
  float ed = w - (side > 0. ? uView.x - x : x);                  // distance au bord intérieur du pan
  if (ed < -2.) return vec4(0.);
  float comp = w/hw, gather = 1. - comp, k = mix(1., .34, gather*gather);
  float s0 = (side > 0. ? uView.x - x : x)*hw*k/w, s = side > 0. ? uView.x - s0 : s0, amp;
  float hemProf = y > uHc - 10. ? foldD(s, uHc, amp).y : 0.;
  float above = uHc + 3.2*mix(.4, 1., comp)*hemProf - y;        // ourlet festonné posé sur le plancher
  if (above < -2.) return vec4(0.);
  float e = 1.5, dwdy = (paneWidth(clamp((y + e)/uHc, 0., 1.), side) - paneWidth(clamp((y - e)/uHc, 0., 1.), side))/(2.*e);
  vec4 f = foldD(s, y, amp);
  float dm = .3 + .7*comp, aa = smoothstep(1.6, 4., uP*comp/k);  // plis trop serrés pour l'écran : on les adoucit
  vec3 n = vec3(-f.z*(hw*k/w)*dm*aa, (f.z*side*s0/w*dwdy + f.w/uHc)*dm*aa, 1.);
  n.y += uSway*smoothstep(.45, 1., tf);
  float roll = 1. - smoothstep(0., 6., above);
  n.y -= roll*roll*1.6;
  float er = 1. - smoothstep(0., 5., ed);
  n.x -= side*er*er*1.4;                                         // le bord intérieur s'arrondit
  n = normalize(n);
  vec2 sp = vec2(x, y)/uView;
  vec2 dp = (sp - vec2(.5, .42))*vec2(1.25, 1.05);
  float pool = exp(-dot(dp, dp)*3.2);                            // la poursuite, fixe
  float key = (.14 + 1.05*pool)*mix(.10, 1., smoothstep(-.02, .40, sp.y));
  float foot = .45*exp(-(1. - sp.y)*4.);                         // la rampe, au ras du plancher
  vec3 L1 = normalize(vec3(-.48, .42, .77)), L3 = normalize(vec3(.50, .35, .79)), L2 = normalize(vec3(.10, -.60, .79));
  float g = vnoise(vec2(s, y)*1.2) - .5;                         // le poil du velours : un grain très fin
  vec2 mp = vec2(s, y*.8)/150.;
  float mott = .66*vnoise(mp) + .34*vnoise(mp*2.03 + 17.1) - .5; // reflets inégaux du poil couché
  // Le velours renvoie la lumière de façon assez plate ; ce sont les creux sombres et le reflet sur les flancs qui dessinent les plis.
  float w1 = clamp(.28 + .72*dot(n, L1), 0., 1.), w2 = clamp(.28 + .72*dot(n, L2), 0., 1.), w3 = clamp(.28 + .72*dot(n, L3), 0., 1.);
  float rim = pow(clamp(1. - n.z, 0., 1.), 1.6)*mix(1., .5, gather);
  float ao = pow(mix(.05, 1., mix(.6, smoothstep(-1., .75, f.y*min(amp, 1.2)), aa)), 1.15 + .8*gather);
  vec3 light = w1*key*vec3(1., .88, .74) + w3*key*.32*vec3(.85, .85, 1.) + w2*foot*vec3(1., .70, .42);
  vec3 col = vec3(.36, .010, .022)*(.02 + light);
  col += vec3(.9, .16, .17)*rim*((.3 + .7*w1)*key*.5*(1. + .6*mott) + w2*foot*.25);
  col *= ao*(1. + .05*g)*mix(1., .8, gather);
  float seam = above - uHem;
  col *= 1. - .5*exp(-seam*seam*.8);                             // couture de l'ourlet
  if (side < 0.){ float d = edgeR(tf) - x; col *= 1. - .55*exp(-max(d, 0.)/2.5); }   // au milieu, le pan droit passe devant le gauche
  col += vec3(1., .35, .22)*uSpill*.16*exp(-max(ed, 0.)/2.2);   // la lumière de la scène effleure les bords
  float a = clamp(above*uScale + .5, 0., 1.)*clamp(ed*uScale + .5, 0., 1.);
  return vec4(tonemap(col)*a, a);
}
// Le lambrequin : la bande de velours fixe derrière le menu, plissée, dont le bas retombe en trois festons comme sur le site actuel.
float valPleat(float x){
  float q = x/(uP*.55);
  float F = q + .06*sin(q*.7 + 1.) + .04*sin(q*1.9 + 2.);
  return pow(max(.5 + .5*cos(6.2832*F), 0.), .8)*2. - 1.;
}
float valArc(float x){ return sin(3.14159*fract(x/(uView.x/3.))); }
float valEdge(float x){ return uValH + uSwag*pow(valArc(x), .9) + 1.8*valPleat(x); }
float valDepth(float x, float y){
  float arc = valArc(x), v = clamp(y/(uValH + uSwag*arc), 0., 1.);
  return .42*uP*.55*valPleat(x)*mix(1.15, .55, arc) + arc*v*v*uSwag*.9;   // plis serrés aux attaches, feston bombé vers le bas
}
vec4 valance(float x, float y){
  float above = valEdge(x) - y;
  if (above < -2.) return vec4(0.);
  float e = .8;
  vec3 n = vec3(-(valDepth(x + e, y) - valDepth(x - e, y))/(2.*e), (valDepth(x, y + e) - valDepth(x, y - e))/(2.*e), 1.);
  float roll = 1. - smoothstep(0., 5., above);
  n.y -= roll*roll*1.5;
  n = normalize(n);
  vec3 L1 = normalize(vec3(-.48, .42, .77)), L3 = normalize(vec3(.50, .35, .79));
  float key = (.32 + .55*exp(-pow((x/uView.x - .5)*1.7, 2.)*2.))*mix(.45, 1., smoothstep(0., uValH*.8, y));
  float w1 = clamp(.28 + .72*dot(n, L1), 0., 1.), w3 = clamp(.28 + .72*dot(n, L3), 0., 1.);
  float rim = pow(clamp(1. - n.z, 0., 1.), 1.6);
  float ao = pow(mix(.08, 1., smoothstep(-1., .75, valPleat(x))), 1.15);
  float g = vnoise(vec2(x, y)*1.2) - .5;
  vec3 col = vec3(.36, .010, .022)*(.02 + (w1*vec3(1., .88, .74) + w3*.32*vec3(.85, .85, 1.))*key);
  col += vec3(.9, .16, .17)*rim*(.3 + .7*w1)*key*.5;
  col *= ao*(1. + .05*g);
  float seam = above - 8.;
  col *= 1. - .45*exp(-seam*seam*.8);                            // couture de l'ourlet
  col *= 1. + (hash12(gl_FragCoord.xy + floor(uTime*24.)*13.7) - .5)*.022;
  float a = clamp(above*uScale + .5, 0., 1.);
  return vec4(tonemap(col)*a, a);
}
void main(){
  vec2 px = vec2(gl_FragCoord.x, uRes.y - gl_FragCoord.y)/uScale;
  float x = px.x, y = px.y, tf = clamp(y/uHc, 0., 1.);
  float ve = uValH + uSwag + 4.;
  if (y < uValH + uSwag + 70.) ve = valEdge(x);
  if (y < ve - 2.){ gl_FragColor = valance(x, y); return; }     // sous le lambrequin, rien d'autre ne se voit
  float xl = edgeL(tf), xr = edgeR(tf);
  vec4 col = vec4(0.);
  if (x > xr - 2.) col = cloth(x, y, 1.);
  if (x < xl + 2. && col.a < .999){ vec4 l = cloth(x, y, -1.); col += l*(1. - col.a); }
  col.rgb *= 1. + (hash12(gl_FragCoord.xy + floor(uTime*24.)*13.7) - .5)*.022;   // grain de pellicule
  float floorTop = uView.y - uFloorH;
  vec3 bc = vec3(0.); float ba = 0.;
  if (y > floorTop - 4.){                                        // le plancher continue derrière les festons
    float xlB = edgeL(1.), xrB = edgeR(1.), hw = uView.x*.5 + uOv;
    float under = max(clamp((xlB - x)*uScale + .5, 0., 1.), clamp((x - xrB)*uScale + .5, 0., 1.));
    float d = max(y - floorTop, 0.), prof = 0.;
    if (under > 0.){
      float side = x > xrB ? 1. : -1., wB = paneWidth(1., side), cB = wB/hw, kB = mix(1., .34, (1. - cB)*(1. - cB)), amp;
      float s0 = (side > 0. ? uView.x - x : x)*hw*kB/wB;
      prof = foldD(side > 0. ? uView.x - s0 : s0, uHc, amp).y;
    }
    vec3 fl = vec3(.004, .003, .0025)*(1. - .35*d/uFloorH);
    fl += vec3(.11, .006, .012)*exp(-d/9.)*(.55 + .45*prof)*under;   // reflet du velours sur le plancher
    fl *= 1. - .8*exp(-d/3.)*under;                                  // ombre de contact
    fl += vec3(1., .62, .34)*uSpill*.07*exp(-d/12.)*(1. - under);    // la lumière de la scène sur le plancher
    bc = tonemap(fl); ba = max(uApron, under);
  } else {
    float dl = x - xl, dr = xr - x;                              // ombre douce des pans sur la scène
    if (dl > 0. && dr > 0.) ba = uShadow*max(exp(-dl/22.), exp(-dr/22.));
  }
  float dith = (hash12(gl_FragCoord.xy + fract(uTime*7.)*97.) - .5)/255.;
  vec4 outp = vec4(col.rgb + bc*ba*(1. - col.a) + dith*(col.a + ba), col.a + ba*(1. - col.a));
  float sh = .5*exp(-max(y - ve, 0.)/12.);                       // ombre portée du lambrequin
  outp = vec4(outp.rgb*(1. - sh), outp.a + sh*(1. - outp.a));
  if (y < ve + 2.){ vec4 v = valance(x, y); outp = v + outp*(1. - v.a); }
  gl_FragColor = outp;
}`;

    let gl = null, U = {}, geo = null, raf = 0, start = 0, last = 0, lights = null, sequence = 0;
    function setup() {
        gl = canvas.getContext('webgl', { alpha: true, premultipliedAlpha: true, antialias: false });
        if (!gl) return;
        const shader = (type, source) => {
            const item = gl.createShader(type);
            gl.shaderSource(item, source);
            gl.compileShader(item);
            if (!gl.getShaderParameter(item, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(item));
            return item;
        };
        const program = gl.createProgram();
        gl.attachShader(program, shader(gl.VERTEX_SHADER, VERT));
        gl.attachShader(program, shader(gl.FRAGMENT_SHADER, FRAG));
        gl.bindAttribLocation(program, 0, 'a');
        gl.linkProgram(program);
        if (!gl.getProgramParameter(program, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(program));
        gl.useProgram(program);
        gl.bindBuffer(gl.ARRAY_BUFFER, gl.createBuffer());
        gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW);
        gl.enableVertexAttribArray(0);
        gl.vertexAttribPointer(0, 2, gl.FLOAT, false, 0, 0);
        for (const name of ['uRes', 'uView', 'uOpenL', 'uOpenR', 'uScale', 'uHc', 'uFloorH', 'uP', 'uTime', 'uSway', 'uSwayX', 'uRipple',
            'uSpill', 'uApron', 'uHem', 'uStack', 'uOv', 'uSwingL', 'uSwingR', 'uShadow', 'uValH', 'uSwag']) U[name] = gl.getUniformLocation(program, name);
    }

    // Mesures en pixels CSS. Une fois ouvert, chaque pan reste froncé sur son côté sans toucher le bouton « Rejouer ».
    function layout() {
        const W = curtain.clientWidth || innerWidth, H = curtain.clientHeight || innerHeight;
        // Au plus 2,2 millions de points calculés par image, quelle que soit la taille de l'écran.
        const scale = Math.min(devicePixelRatio || 1, W < 700 ? 1.3 : 1.6, Math.sqrt(2.2e6 / (W * H)));
        const floorH = Math.round(Math.min(Math.max(H * .045, 24), 44));
        canvas.width = Math.round(W * scale);
        canvas.height = Math.round(H * scale);
        // Le lambrequin couvre la hauteur du menu et descend encore un peu dessous.
        const bar = nav ? nav.getBoundingClientRect().height : 64;
        geo = { W, H, scale, floorH, Hc: H - floorH, P: Math.min(Math.max(W / 17, 34), 76), stack: Math.min(Math.max(W * .04, 20), 56) * .85,
                hem: W < 700 ? 11 : 15, valH: Math.round(bar + (W < 700 ? 3 : 4)), swag: W < 700 ? 10 : 14 };
        gl.viewport(0, 0, canvas.width, canvas.height);
    }

    function render(ms) {
        last = ms;
        const G = geo, stop = end();
        ms = Math.min(ms, stop);
        // Le pan droit part un peu après le gauche ; dans chaque pan, le bas suit le haut avec retard.
        const top = openAt(ms), bottom = openAt(ms - LAG), rightTop = openAt(ms - 70), rightBottom = openAt(ms - 70 - LAG * 1.15);
        const after = (ms - begin() - OPEN - LAG) / 1000, settle = 1 - smooth(stop - 350, stop, ms);
        const swing = after > 0 ? Math.sin(after * 5.4) * Math.exp(-after / .45) * settle : 0;
        const s = (ms - begin()) / 1000, moving = smooth(0, .3, s) * (1 - smooth(OPEN / 1000, OPEN / 1000 + 1.2, s));
        gl.uniform2f(U.uRes, canvas.width, canvas.height);
        gl.uniform2f(U.uView, G.W, G.H);
        gl.uniform2f(U.uOpenL, top, bottom);
        gl.uniform2f(U.uOpenR, rightTop, rightBottom);
        gl.uniform1f(U.uScale, G.scale);
        gl.uniform1f(U.uHc, G.Hc);
        gl.uniform1f(U.uFloorH, G.floorH);
        gl.uniform1f(U.uP, G.P);
        gl.uniform1f(U.uTime, ms / 1000);
        gl.uniform1f(U.uSway, (.03 * Math.sin(ms / 1000 * 2.03) + moving * .16 * Math.sin(s * 4.4)) * settle);
        gl.uniform1f(U.uSwayX, moving * 3 * Math.sin(s * 3.7 + .6));
        gl.uniform1f(U.uRipple, .014 + .05 * moving);
        gl.uniform1f(U.uSpill, smooth(0, .06, top));
        gl.uniform1f(U.uApron, 1 - smooth(.05, .6, top));
        gl.uniform1f(U.uHem, G.hem);
        gl.uniform1f(U.uStack, G.stack);
        gl.uniform1f(U.uOv, 6);
        gl.uniform1f(U.uSwingL, swing * G.stack * .22);
        gl.uniform1f(U.uSwingR, swing * G.stack * .18);
        gl.uniform1f(U.uShadow, .42 * (1 - .45 * top));
        gl.uniform1f(U.uValH, G.valH);
        gl.uniform1f(U.uSwag, G.swag);
        gl.drawArrays(gl.TRIANGLES, 0, 3);
        curtain.classList.add('is-live');
    }

    // La salle s'éteint, la scène s'éclaire.
    function stageLights(delay) {
        lights?.cancel();
        lights = photo.animate([{ filter: 'brightness(.3)', transform: 'scale(1.07)' }, { filter: 'brightness(.3)', transform: 'scale(1.07)', offset: .3 },
            { filter: 'brightness(1)', transform: 'none' }], { duration: 3300, delay, easing: 'cubic-bezier(.3,.1,.3,1)', fill: delay ? 'forwards' : 'both' });
    }

    // Rideau ouvert et immobile : les deux pans restent froncés sur les côtés, plus rien n'est recalculé.
    function settle() {
        sequence += 1;
        cancelAnimationFrame(raf);
        lights?.cancel();
        lights = null;
        if (gl && geo) render(end());
        stage.classList.remove('theatre-is-moving');
        stage.classList.add('is-open');
        stage.dataset.curtain = 'open';
        replay.disabled = false;
    }

    function tick(now) {
        const ms = now - start;
        if (ms >= end()) return settle();
        render(ms);
        raf = requestAnimationFrame(tick);
    }

    function openCurtain(again) {
        entered = true;
        rememberEntrance();
        cancelAnimationFrame(raf);
        replaying = again;
        stage.classList.add('theatre-is-moving');
        stage.classList.remove('is-open');
        stage.dataset.curtain = 'opening';
        replay.disabled = true;
        start = performance.now();
        stageLights(again ? CLOSE + PAUSE : 0);
        raf = requestAnimationFrame(tick);
    }

    function configureMotion() {
        if (motion.matches) entered = true;
        observer?.disconnect();
        stage.classList.toggle('theatre-ready', !motion.matches);
        replay.hidden = motion.matches || !gl;
        reveals.forEach(item => item.classList.remove('theatre-reveal', 'is-visible'));
        if (motion.matches) return;
        if ('IntersectionObserver' in window) {
            observer = new IntersectionObserver(entries => {
                entries.forEach(entry => {
                    if (!entry.isIntersecting) return;
                    entry.target.classList.add('is-visible');
                    observer.unobserve(entry.target);
                });
            }, { threshold: 0.08 });
            reveals.forEach(item => {
                item.classList.add('theatre-reveal');
                observer.observe(item);
            });
        }
    }

    try { setup(); } catch (error) { gl = null; setTimeout(() => { throw error; }); }
    if (!gl) curtain.hidden = true;
    configureMotion();

    replay.addEventListener('click', () => {
        scrollTo({ top: 0, behavior: 'instant' });
        if (gl && !motion.matches) openCurtain(true);
    });
    document.addEventListener('focusin', event => {
        event.target.closest('.theatre-reveal')?.classList.add('is-visible');
    });
    document.addEventListener('visibilitychange', () => {
        if (document.hidden && stage.classList.contains('theatre-is-moving')) settle();
    });
    motion.addEventListener('change', () => {
        configureMotion();
        settle();
    });
    window.addEventListener('hashchange', () => {
        if (location.hash) {
            entered = true;
            settle();
        }
    });
    window.addEventListener('pagehide', settle);
    window.addEventListener('pageshow', event => {
        if (event.persisted) {
            entered = true;
            settle();
        }
    });
    window.addEventListener('resize', () => {
        if (!gl || curtain.hidden) return;
        layout();
        render(stage.classList.contains('theatre-is-moving') ? last : end());
    }, { passive: true });
    window.addEventListener('scroll', () => {
        if (stage.classList.contains('theatre-is-moving') && stage.getBoundingClientRect().bottom < innerHeight * .5) settle();
    }, { passive: true });

    if (!gl) {
        settle();
        return;
    }
    layout();
    if (entered) {
        settle();
        return;
    }
    // Première visite : le rideau est fermé ; on attend que la photo de scène soit prête (1,6 s au plus) avant d'ouvrir.
    stage.dataset.curtain = 'closed';
    render(0);
    const current = sequence;
    const loaded = photo.complete ? Promise.resolve() : new Promise(resolve => photo.addEventListener('load', resolve, { once: true }));
    Promise.race([loaded.then(() => photo.decode()).catch(() => {}), new Promise(resolve => setTimeout(resolve, 1600))]).then(() => {
        if (sequence === current && !entered) openCurtain(false);
    });
})();
