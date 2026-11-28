"""La galerie 3D des projets personnels (regards/galerie/) : un hall (photos isolées) et une salle par série.

Script pour Blender, lancé sans fenêtre (Blender 5.2 portable, rangé dans .tools/blender, hors de Git) :

    .tools\\blender\\blender-5.2.5-windows-x64\\blender.exe -b --factory-startup -P scripts\\musee_3d.py -- cuisson 160
        → calcule la lumière de chaque surface (≈ 15 min) et refait regards/galerie/ : musee.glb, plan.json,
          lumiere/*.png, matieres/*.jpg. À relancer après un changement de salle, de photo ou d'éclairage.
    ... -P scripts\\musee_3d.py -- matieres
        → refait seulement les textures du site (matieres/*.jpg, avec leur relief), en quelques secondes.
    ... -P scripts\\musee_3d.py -- hall,couvent,garde,toulouse,messe,montagne 96
        → images fixes de contrôle (test-results/galerie-3d/rendus/*.png, ≈ 2 à 6 min chacune).

Les photos viennent de images/optimized (celles des albums) ; les matières, de textures Poly Haven (CC0, libres de
droits) en 2048 px rangées dans .tools/textures (hors de Git). Repère de three.js (y en haut, mètres).
Plan : hall x[-5,5] z[-6,6] ; à l'ouest Couvent (nord) et Toulouse (sud) ; à l'est La Garde (nord) et Messe (sud) ;
au nord Échappées en montagne. Murs de 30 cm entre les salles.
"""
import glob
import json
import math
import os
import re
import sys
import time

import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..'))
TEX = os.path.join(ROOT, '.tools', 'textures')
OUT = os.path.join(ROOT, 'test-results', 'galerie-3d', 'rendus')
OPT = os.path.join(ROOT, 'images', 'optimized')
FONT = os.path.join(ROOT, '.tools', 'fonts', 'Montserrat-Medium.ttf')   # la police du site (licence OFL)
ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
# « plan » : refait seulement plan.json (salles, emplacements, projecteurs, matières) en quelques secondes, sans
# cuisson : à n'utiliser que si la géométrie n'a pas changé (sinon les cartes de lumière ne correspondent plus)
MODE = ARGS[0] if ARGS and ARGS[0] in ('cuisson', 'matieres', 'plan') else 'rendu'
VIEWS = ARGS[0].split(',') if ARGS and MODE == 'rendu' else ['hall']
SAMPLES = int(ARGS[1]) if len(ARGS) > 1 else 96
# « -- cuisson 128 messe,garde » : ne recalcule que ces salles (les autres gardent leurs cartes de lumière)
BAKE_ROOMS = set(ARGS[2].split(',')) if MODE == 'cuisson' and len(ARGS) > 2 else set()


def group_room(name):
    """Salle d'un groupe de la cuisson : « messe__rouge », « banc_hall », « luminaires_garde »…"""
    m = re.match(r'^(hall|couvent|toulouse|garde|messe|montagne)__', name) or re.match(r'^(?:banc|luminaires|deco)_(\w+)$', name)
    return m.group(1) if m else 'hall'
T = 0.3
WEB = os.path.join(ROOT, 'regards', 'galerie')   # la visite en 3D, dans le site
VIEW_PHOTO = 'projet_perso_montagne_Montagne-42'  # le « paysage » vu par la baie de la salle Montagne
VIEW_STRENGTH = 2.2
K = 6.0   # les cartes de lumière vont de 0 à K (enregistrées en 8 bits, sRGB)
# Soleil au sud-est (hauteur 35°, azimut 40°) : par la fenêtre haute de La Garde, le rayon traverse la salle
TO_SUN = (math.cos(math.radians(35)) * math.cos(math.radians(40)), math.sin(math.radians(35)),
          math.cos(math.radians(35)) * math.sin(math.radians(40)))
# Le rayon visible sur le site : fenêtre de La Garde (côté salle), d'où part le faisceau
SUN_BEAM = {'salle': 'garde', 'vers_soleil': [round(v, 5) for v in TO_SUN], 'x': 12.3, 'y': [3.0, 4.15], 'z': [-3.675, -2.475]}
SKY = os.path.join(ROOT, '.tools', 'hdri', 'kloofendal_48d_partly_cloudy_puresky_2k.hdr')   # Poly Haven, CC0
os.makedirs(OUT, exist_ok=True)

# Les salles, pour la page 3D : contour (x0, x1, z0, z1), hauteur, porte sur le hall, point d'arrivée (x, z, cap)
SALLES = {
    'hall': {'titre': 'Hall', 'rect': [-5, 5, -6, 6], 'hauteur': 5.0, 'entree': [0, 5.0, 0.0]},
    'couvent': {'titre': 'Couvent', 'lien': '../../albums/Argentique.html', 'rect': [-12.3, -5.3, -6, -0.15], 'hauteur': 4.4,
                'porte': [-5.15, -3.0], 'largeur': 2.2, 'entree': [-6.5, -3.0, math.pi / 2]},
    'toulouse': {'titre': 'Toulouse', 'lien': '../../albums/argentique_toulouse.html', 'rect': [-12.3, -5.3, 0.15, 6], 'hauteur': 4.2,
                 'porte': [-5.15, 3.0], 'largeur': 2.2, 'entree': [-6.5, 3.0, math.pi / 2]},
    'garde': {'titre': 'La Garde', 'lien': '../../albums/la_garde.html', 'rect': [5.3, 12.3, -6, -0.15], 'hauteur': 4.6,
              'porte': [5.15, -3.0], 'largeur': 2.2, 'entree': [6.5, -3.0, -math.pi / 2]},
    'messe': {'titre': 'Messe', 'lien': '../../albums/messe.html', 'rect': [5.3, 12.3, 0.15, 6], 'hauteur': 4.2,
              'porte': [5.15, 3.0], 'largeur': 2.2, 'entree': [6.5, 3.0, -math.pi / 2]},
    'montagne': {'titre': 'Échappées en montagne', 'lien': '../../albums/montagne.html', 'rect': [-5, 5, -14.3, -6.3], 'hauteur': 4.6,
                 'porte': [0, -6.15], 'largeur': 3.2, 'entree': [0, -7.4, 0.0]},
}
# Matières, pour la page 3D (mêmes réglages que dans Blender, voir museum). Textures Poly Haven (CC0) dans
# .tools/textures ; « tuile » = taille réelle d'une répétition en mètres (donnée par Poly Haven), « teinte » multiplie
# la couleur (albédo moyen mesuré de chaque texture, ramené à la matière voulue).
MATIERES = {
    # Sols. Sur le site seulement : « variation » (écart de teinte d'un endroit à l'autre, contre l'effet papier peint),
    # « saturation » (1 = couleurs de la texture), « carreaux » (nombre de carreaux par répétition : chacun sa teinte),
    # « melange » (contre la répétition : « hex » = la texture tirée au hasard par morceaux fondus, pour les matières
    # sans motif régulier ; « carreaux » = chaque carreau pris au hasard dans la texture et tourné),
    # « profondeur » (relief réel en mètres, vu en bougeant : joints des briques, des pierres, des carreaux)
    'parquet': {'texture': 'herringbone_parquet', 'tuile': 3.4, 'teinte': [0.78, 0.72, 0.66], 'rugosite': 0.75, 'reflets': 0.45, 'variation': 0.12, 'profondeur': 0.002},
    'parquet_clair': {'texture': 'herringbone_parquet', 'tuile': 3.4, 'teinte': [1.12, 1.08, 1.02], 'rugosite': 0.8, 'reflets': 0.45, 'variation': 0.12, 'profondeur': 0.002},
    'dalles': {'texture': 'monastery_stone_floor', 'tuile': 1.8, 'teinte': [1.5, 1.46, 1.4], 'rugosite': 0.9, 'reflets': 0.5, 'variation': 0.14, 'melange': 'hex'},
    'beton': {'texture': 'concrete_floor_02', 'tuile': 2.0, 'teinte': [1.05, 1.12, 1.4], 'rugosite': 0.7, 'reflets': True, 'variation': 0.16, 'melange': 'hex'},
    'tomettes': {'texture': 'terracotta_floor_tiles', 'tuile': 2.08, 'teinte': [2.25, 2.2, 2.25], 'rugosite': 0.8, 'reflets': 0.6,
                 'saturation': 0.72, 'carreaux': 9, 'variation': 0.1, 'melange': 'carreaux', 'profondeur': 0.004},
    'marbre': {'texture': 'marble_01', 'tuile': 1.5, 'teinte': [1.3, 1.35, 1.55], 'rugosite': 0.25, 'reflets': True, 'variation': 0.06, 'melange': 'hex'},
    # Murs, voûte, plafonds
    'pierre': {'texture': 'sandstone_blocks_05', 'tuile': 3.0, 'teinte': [1.12, 1.15, 1.22], 'variation': 0.14, 'profondeur': 0.035},
    # Toulouse : vieille brique irrégulière à joints de chaux (moins orange, moins régulière que l'ancienne)
    'brique': {'texture': 'castle_brick_02_white', 'tuile': 3.0, 'teinte': [1.12, 1.08, 1.08], 'variation': 0.14, 'saturation': 0.9, 'profondeur': 0.022},
    'chaux': {'texture': 'painted_plaster_wall', 'tuile': 2.0, 'teinte': [2.0, 2.12, 2.15], 'variation': 0.05, 'melange': 'hex'},
    'enduit': {'texture': 'painted_plaster_wall', 'tuile': 2.0, 'teinte': [1.92, 1.87, 1.76], 'variation': 0.06, 'melange': 'hex'},   # murs du hall
    'rouge': {'texture': 'painted_plaster_wall', 'tuile': 2.0, 'teinte': [0.55, 0.1, 0.115], 'variation': 0.1, 'melange': 'hex'},
    'bois': {'texture': 'wood_table_worn', 'tuile': 0.55, 'teinte': [1.4, 1.4, 1.4], 'profondeur': 0.004},
    'lambris': {'texture': 'wood_table_worn', 'tuile': 0.55, 'teinte': [0.62, 0.55, 0.5], 'rugosite': 0.55, 'reflets': 0.35, 'profondeur': 0.004},
    'bois_plafond': {'texture': 'hinoki_planks', 'tuile': 1.89, 'teinte': [1.15, 1.12, 1.08]},
    'blanc': {'couleur': [0.84, 0.83, 0.81]}, 'plafond': {'couleur': [0.86, 0.86, 0.85]},
    'plinthe': {'couleur': [0.8, 0.8, 0.79]}, 'plinthe_bois': {'couleur': [0.05, 0.032, 0.022]},
    'corniche': {'couleur': [0.84, 0.82, 0.78]},
    # Bancs : chêne et acier noir
    'chene': {'texture': 'oak_wood_planks', 'tuile': 1.2, 'teinte': [1, 1, 1], 'rugosite': 0.55, 'reflets': 0.4},
    # Noirs (cadres, projecteurs, rails) : reflets atténués, sinon ils paraissent gris sur le site
    'cadre': {'couleur': [0.02, 0.019, 0.018], 'rugosite': 0.38, 'reflets': 0.35},
    'passe-partout': {'couleur': [0.88, 0.875, 0.86]},
    'noir': {'couleur': [0.015, 0.015, 0.015], 'rugosite': 0.4, 'reflets': 0.4},
    'lettres': {'couleur': [0.012, 0.012, 0.012]},
    'verriere': {'lumineux': [0.94, 0.965, 1.0], 'force': 2.6},
    'jour': {'lumineux': [0.95, 0.97, 1.0], 'force': 2.4},
    'vue': {'photo': VIEW_PHOTO, 'force': VIEW_STRENGTH},
    # Seuils de pierre des portes, appui de la fenêtre de La Garde : calcaire clair (la texture du marbre, en plus gris)
    'seuil': {'texture': 'marble_01', 'tuile': 1.5, 'teinte': [1.08, 1.1, 1.24], 'rugosite': 0.5, 'reflets': 0.3, 'variation': 0.08},
}
# Relief des textures du site : sur le web la lumière est précalculée, le relief des pierres disparaîtrait ;
# on l'imprime dans la texture (force ; lumière venant d'en haut pour un mur, de face pour un sol ou un plafond),
# avec l'occlusion (« ao ») de Poly Haven quand elle existe
RELIEF = {'sandstone_blocks_05': (1.0, 'mur'), 'castle_brick_02_white': (1.0, 'mur'), 'painted_plaster_wall': (0.6, 'mur'),
          'wood_table_worn': (0.5, 'mur'), 'hinoki_planks': (0.5, 'sol'), 'monastery_stone_floor': (0.9, 'sol'),
          'concrete_floor_02': (0.4, 'sol'), 'terracotta_floor_tiles': (0.7, 'sol'), 'marble_01': (0.35, 'sol'),
          'oak_wood_planks': (0.3, 'sol'), 'herringbone_parquet': (0.35, 'sol')}


def B(x, y, z):
    return Vector((x, -z, y))


def V(*a):
    return Vector(a)


# ---------- Matières ----------
def new_material(name):
    mat = bpy.data.materials.new(name)
    try:
        mat.use_nodes = True
    except AttributeError:
        pass
    nodes = mat.node_tree.nodes
    return mat, nodes, mat.node_tree.links, nodes['Principled BSDF']


def pbr(name, tex_id, tile, tint=(1, 1, 1), rough=1.0, normal=1.0):
    mat, nodes, links, bsdf = new_material(name)
    coord, mapping = nodes.new('ShaderNodeTexCoord'), nodes.new('ShaderNodeMapping')
    mapping.inputs['Scale'].default_value = (1 / tile, 1 / tile, 1)
    links.new(coord.outputs['UV'], mapping.inputs['Vector'])

    def image(kind, color):
        node = nodes.new('ShaderNodeTexImage')
        # « diff » ou « diffuse » selon les textures
        node.image = bpy.data.images.load(glob.glob(os.path.join(TEX, tex_id, f'*_{kind}*_2k.jpg'))[0], check_existing=True)
        node.image.colorspace_settings.name = 'sRGB' if color else 'Non-Color'
        links.new(mapping.outputs['Vector'], node.inputs['Vector'])
        return node

    tinted = nodes.new('ShaderNodeVectorMath')
    tinted.operation = 'MULTIPLY'
    links.new(image('diff', True).outputs['Color'], tinted.inputs[0])
    tinted.inputs[1].default_value = tint
    links.new(tinted.outputs['Vector'], bsdf.inputs['Base Color'])
    scaled = nodes.new('ShaderNodeMath')
    scaled.operation = 'MULTIPLY'
    links.new(image('rough', False).outputs['Color'], scaled.inputs[0])
    scaled.inputs[1].default_value = rough
    links.new(scaled.outputs['Value'], bsdf.inputs['Roughness'])
    normal_map = nodes.new('ShaderNodeNormalMap')
    # Pour la cuisson, pas de relief : à 32 pixels par mètre, il ne donnerait que des taches (la texture le montre déjà)
    normal_map.inputs['Strength'].default_value = 0 if MODE == 'cuisson' else normal
    links.new(image('nor_gl', False).outputs['Color'], normal_map.inputs['Color'])
    links.new(normal_map.outputs['Normal'], bsdf.inputs['Normal'])
    return mat


def paint(name, color, rough=0.88, bump=0.12, scale=45):
    mat, nodes, links, bsdf = new_material(name)
    bsdf.inputs['Base Color'].default_value = (*color, 1)
    bsdf.inputs['Roughness'].default_value = rough
    noise, bumpn = nodes.new('ShaderNodeTexNoise'), nodes.new('ShaderNodeBump')
    noise.inputs['Scale'].default_value = scale
    noise.inputs['Detail'].default_value = 10
    bumpn.inputs['Strength'].default_value = 0 if MODE == 'cuisson' else bump
    bumpn.inputs['Distance'].default_value = 0.003
    links.new(noise.outputs['Fac'], bumpn.inputs['Height'])
    links.new(bumpn.outputs['Normal'], bsdf.inputs['Normal'])
    return mat


def flat(name, color, rough=0.5, metal=0.0):
    mat, _, _, bsdf = new_material(name)
    bsdf.inputs['Base Color'].default_value = (*color, 1)
    bsdf.inputs['Roughness'].default_value = rough
    bsdf.inputs['Metallic'].default_value = metal
    return mat


def glow(name, color, strength):
    mat, _, _, bsdf = new_material(name)
    bsdf.inputs['Base Color'].default_value = (*color, 1)
    bsdf.inputs['Emission Color'].default_value = (*color, 1)
    bsdf.inputs['Emission Strength'].default_value = strength
    return mat


def photo_material(file):
    mat, nodes, links, bsdf = new_material('photo')
    node = nodes.new('ShaderNodeTexImage')
    node.image = bpy.data.images.load(file, check_existing=True)
    links.new(node.outputs['Color'], bsdf.inputs['Base Color'])
    bsdf.inputs['Roughness'].default_value = 0.5
    return mat, node.image


# ---------- Géométrie ----------
def build(name, faces, mat, uvs=None, shadow=True):
    verts, polys = [], []
    for f in faces:
        base = len(verts)
        verts += [B(*p) for p in f]
        polys.append(tuple(range(base, base + len(f))))
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], polys)
    me.update()
    uv = me.uv_layers.new(name='UVMap')
    for poly, f, fuv in zip(me.polygons, faces, uvs or [None] * len(faces)):
        if fuv is None:
            a, b, d = V(*f[0]), V(*f[1]), V(*f[-1])
            w, h = (b - a).length, (d - a).length
            fuv = [(0, 0), (w, 0), (w, h), (0, h)]
        for k, li in enumerate(poly.loop_indices):
            uv.data[li].uv = fuv[k]
    obj = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(mat)
    obj.visible_shadow = shadow
    return obj


def face(corners, normal):
    """Range les coins pour que la face regarde vers `normal`."""
    a, b, d = V(*corners[0]), V(*corners[1]), V(*corners[-1])
    return corners if (b - a).cross(d - a).dot(V(*normal)) >= 0 else corners[::-1]


def quarter(o0, y0, o1, y1, concave, steps=3):
    """Quart de rond de (o0, y0) à (o1, y1), sans le point de départ : creux (gorge) ou bombé (quart-de-rond)."""
    pts = []
    for i in range(1, steps + 1):
        t = math.pi / 2 * i / steps
        if concave:
            pts.append((o1 - (o1 - o0) * math.cos(t), y0 + (y1 - y0) * math.sin(t)))
        else:
            pts.append((o0 + (o1 - o0) * math.sin(t), y1 - (y1 - y0) * math.cos(t)))
    return pts


# Profils des moulures : (saillie hors du mur, hauteur) en mètres, de bas en haut. Les plinthes et les bandeaux sont
# comptés depuis le sol, les corniches depuis le haut du mur (hauteurs négatives).
PLINTHE = [(0.017, 0), (0.017, 0.1), (0.011, 0.112), (0.011, 0.126), (0, 0.14)]   # hall : plinthe moulurée
PLINTHE_NETTE = [(0.014, 0), (0.014, 0.094), (0.008, 0.1), (0, 0.1)]               # montagne : plinthe droite
# hall : corniche classique (filet, quart-de-rond, larmier, gorge), 34 cm de haut, 22 cm de saillie
CORNICHE = ([(0, -0.34), (0.015, -0.34), (0.015, -0.32)] + quarter(0.015, -0.32, 0.06, -0.275, False)
            + [(0.12, -0.275), (0.12, -0.18), (0.135, -0.18), (0.135, -0.165)]
            + quarter(0.135, -0.165, 0.22, -0.03, True, 4) + [(0.22, 0)])
# messe : voussure (grande gorge entre le mur et le plafond) sur un petit quart-de-rond
VOUSSURE = ([(0, -0.32), (0.012, -0.32), (0.012, -0.3)] + quarter(0.012, -0.3, 0.035, -0.277, False, 2)
            + [(0.035, -0.26)] + quarter(0.035, -0.26, 0.26, -0.035, True, 6) + [(0.285, -0.035), (0.285, 0)])
SOCLE = [(0.04, 0), (0.04, 0.28), (0, 0.32)]   # couvent : soubassement de pierre, dessus chanfreiné
CORDON = [(0, 2.84), (0.03, 2.84), (0.07, 2.9), (0.07, 2.97), (0.05, 3.0), (0, 3.0)]   # couvent : à la naissance de la voûte
# messe : rosace du plafond (rayon, retombée), du bord vers le centre
ROSACE = [(0.44, 0), (0.43, 0.012), (0.37, 0.02), (0.34, 0.034), (0.27, 0.04), (0.22, 0.058), (0.13, 0.066), (0.08, 0.085), (0, 0.095)]


def extrude(name, origin, d, length, n, s, pts, mat, caps=(True, True)):
    """Moulure droite : le profil `pts` [(saillie, travers)] tiré le long de `d` sur `length` mètres depuis `origin`.
    n : sens de la saillie (hors du mur), s : sens du travers (vers le haut pour une corniche, à l'écart de la baie pour
    un chambranle) ; le travers ne fait que croître. caps : fermer les bouts (pas dans les angles de la salle : la
    moulure du mur voisin les recouvre, en onglet)."""
    o, d, n, s = V(*origin), V(*d).normalized(), V(*n).normalized(), V(*s).normalized()
    P = lambda u, out, a: tuple(o + d * u + n * out + s * a)
    faces = []
    for (o0, a0), (o1, a1) in zip(pts, pts[1:]):
        if abs(o1 - o0) + abs(a1 - a0) < 1e-6:
            continue
        faces.append(face([P(0, o0, a0), P(length, o0, a0), P(length, o1, a1), P(0, o1, a1)], tuple(n * (a1 - a0) - s * (o1 - o0))))
    for u, outward, wanted in ((0, -d, caps[0]), (length, d, caps[1])):
        if not wanted:
            continue
        for (o0, a0), (o1, a1) in zip(pts, pts[1:]):   # le bout : des trapèzes entre le mur et le profil
            if a1 - a0 < 1e-6 or max(o0, o1) < 1e-6:
                continue
            corners = [P(u, 0, a0)] + ([P(u, o0, a0)] if o0 > 1e-6 else []) + ([P(u, o1, a1)] if o1 > 1e-6 else []) + [P(u, 0, a1)]
            faces.append(face(corners, tuple(outward)))
    return build(name, faces, mat)


def wall(name, start, direction, normal, length, height, mat, openings=(), plinth=None, cornice=None, dado=None, bands=(), trim=0.0):
    """Mur plat le long de `direction` ; openings : (début, fin, haut, bas) en mètres le long du mur.
    Moulures, coupées aux ouvertures qu'elles croisent (et à `trim` près : la largeur des chambranles) :
    plinth, cornice : (matière, profil) d'une plinthe en bas ou d'une corniche en haut (profil compté depuis le haut) ;
    dado : (hauteur, matière du lambris, matière de la cimaise et de la plinthe) : un lambris à panneaux en bas du mur ;
    bands : autres moulures [(nom, matière, profil)], comme le cordon de pierre du couvent."""
    s, d, up, n = V(*start), V(*direction).normalized(), V(0, 1, 0), V(*normal).normalized()
    if d.cross(up).dot(n) < 0:
        s, d = s + d * length, -d
        openings = [(length - e, length - b, top, bottom) for (b, e, top, bottom) in openings]
    faces, uvs = [], []

    def rect(u0, u1, y0, y1):
        p = lambda u, y: s + d * u + up * y
        faces.append([p(u0, y0), p(u1, y0), p(u1, y1), p(u0, y1)])
        uvs.append([(u0, y0), (u1, y0), (u1, y1), (u0, y1)])

    u = 0
    for b, e, top, bottom in sorted(openings):
        if b > u:
            rect(u, b, 0, height)
        if top < height:
            rect(b, e, top, height)
        if bottom > 0:
            rect(b, e, 0, bottom)
        u = e
    if u < length:
        rect(u, length, 0, height)
    obj = build(name, faces, mat, uvs)

    def moulding(part, material, pts):
        """Une moulure le long du mur ; ses morceaux (début, fin), entre les ouvertures."""
        ys = [y for _, y in pts]
        gap = trim + 0.003 if trim else 0.0   # 3 mm avant le chambranle : pas de faces confondues
        cuts = sorted((b - gap, e + gap) for b, e, top, bottom in openings if bottom < max(ys) and top > min(ys))
        pieces, u = [], 0.0
        for b, e in cuts:
            if b > u + 0.01:
                pieces.append((u, b))
            u = max(u, e)
        if u < length - 0.01:
            pieces.append((u, length))
        for u0, u1 in pieces:
            extrude(f'{name}_{part}', s + d * u0, d, u1 - u0, n, up, pts, material, caps=(u0 > 1e-6, u1 < length - 1e-6))
        return pieces

    if plinth:
        moulding('plinthe', *plinth)
    if dado:
        # lambris à panneaux : traverses en bas et en haut, champ en retrait, montants tous les 90 cm environ ;
        # par-dessus, une cimaise arrondie et une plinthe de bois sombre
        top, panel, rail = dado
        field = (0.212, top - 0.132)
        pieces = moulding('lambris', panel, [(0.03, 0), (0.03, 0.2), (0.018, field[0]), (0.018, field[1]),
                                             (0.03, top - 0.12), (0.03, top - 0.02), (0, top - 0.02)])
        for u0, u1 in pieces:
            count = max(1, round((u1 - u0) / 0.9))
            for k in range(count + 1):
                c = min(max(u0 + (u1 - u0) * k / count, u0 + 0.035), u1 - 0.035)
                a, b = s + d * (c - 0.035) + n * 0.018 + up * field[0], s + d * (c + 0.035) + n * 0.03 + up * field[1]
                block(f'{name}_lambris', tuple(a), tuple(b), panel, hide=(side(-n), '+y', '-y'))
        moulding('cimaise', rail, [(0.03, top - 0.045), (0.045, top - 0.035), (0.05, top - 0.015), (0.05, top + 0.01),
                                   (0.04, top + 0.025), (0.02, top + 0.035), (0, top + 0.035)])
        moulding('plinthe', rail, [(0.042, 0), (0.042, 0.12), (0.036, 0.13), (0.03, 0.142)])
    for part, material, pts in bands:
        moulding(part, material, pts)
    if cornice:
        moulding('corniche', cornice[0], [(o, height + y) for o, y in cornice[1]])
    return obj


def floor(name, x0, x1, z0, z1, y, mat, up=True):
    corners = [(x0, y, z1), (x1, y, z1), (x1, y, z0), (x0, y, z0)]
    uvs = [[(x0, -z1), (x1, -z1), (x1, -z0), (x0, -z0)]]
    if not up:
        corners, uvs = corners[::-1], [uvs[0][::-1]]
    return build(name, [corners], mat, uvs)


def doorway(name, plane, axis, center, width, height, mat, sill_mat=None, bottom=0.0, sill=0.0):
    """Embrasure (porte ou fenêtre) entre deux plans de mur parallèles : axis = 'x' (murs x = constante) ou 'z'.
    sill : épaisseur d'un seuil (ou d'un appui de fenêtre) en pierre, un peu plus large que la baie, qui dépasse de
    4 cm de chaque côté du mur ; sinon une simple face au sol."""
    a, b = sorted(plane)
    c0, c1 = center - width / 2, center + width / 2
    y0, y1 = bottom, height
    if axis == 'x':
        P = lambda w, y, c: (w, y, c)
        nz = lambda s: (0, 0, s)
    else:
        P = lambda w, y, c: (c, y, w)
        nz = lambda s: (s, 0, 0)
    sides = [face([P(a, y0, c0), P(b, y0, c0), P(b, y1, c0), P(a, y1, c0)], nz(1)),
             face([P(a, y0, c1), P(b, y0, c1), P(b, y1, c1), P(a, y1, c1)], nz(-1)),
             face([P(a, y1, c0), P(b, y1, c0), P(b, y1, c1), P(a, y1, c1)], (0, -1, 0))]
    obj = build(name, sides, mat)
    if sill > 0:   # dessous caché pour une porte (posé sur le sol), visible pour un appui de fenêtre
        block(name + '_seuil', P(a - 0.04, y0, c0 - 0.03), P(b + 0.04, y0 + sill, c1 + 0.03), sill_mat or mat,
              hide=('-y',) if bottom == 0 else ())
    else:
        floor_sill = [face([P(a, y0 + 0.002, c0), P(b, y0 + 0.002, c0), P(b, y0 + 0.002, c1), P(a, y0 + 0.002, c1)], (0, 1, 0))]
        build(name + '_seuil', floor_sill, sill_mat or mat)
    return obj


FACES = {'+x': (0, 1), '-x': (0, -1), '+y': (1, 1), '-y': (1, -1), '+z': (2, 1), '-z': (2, -1)}


def side(v):
    """Nom de la face d'un pavé qui regarde dans la direction v (son axe principal) : '+x', '-z'…"""
    axis = max(range(3), key=lambda k: abs(v[k]))
    return ('+' if v[axis] > 0 else '-') + 'xyz'[axis]


def block(name, lo, hi, mat, hide=(), shadow=True):
    """Pavé entre deux coins opposés ; hide : les faces cachées (contre un mur, sous un plafond…), qu'on ne fabrique
    pas : moins de triangles, et pas de place perdue dans les cartes de lumière."""
    lo, hi = [min(p, q) for p, q in zip(lo, hi)], [max(p, q) for p, q in zip(lo, hi)]
    faces = []
    for key, (axis, sign) in FACES.items():
        if key in hide:
            continue
        i, j = [k for k in range(3) if k != axis]
        corners = []
        for p, q in ((lo[i], lo[j]), (hi[i], lo[j]), (hi[i], hi[j]), (lo[i], hi[j])):
            c = [0.0, 0.0, 0.0]
            c[axis], c[i], c[j] = (hi if sign > 0 else lo)[axis], p, q
            corners.append(tuple(c))
        normal = [0, 0, 0]
        normal[axis] = sign
        faces.append(face(corners, tuple(normal)))
    return build(name, faces, mat, shadow=shadow)


def on_wall(name, axis, plane, out, a0, a1, o0, o1, y0, y1, mat, hide=('dos',)):
    """Pavé contre un mur (x = plane si axis == 'x', sinon z = plane), côté `out` (±1) : de a0 à a1 le long du mur,
    de o0 à o1 en saillie, de y0 à y1 en hauteur. hide : 'dos' (contre le mur), 'face', 'haut', 'bas', 'debut' (côté
    a0), 'fin' (côté a1)."""
    if axis == 'x':
        lo, hi = (plane + out * o0, y0, a0), (plane + out * o1, y1, a1)
        names = {'face': '+x' if out > 0 else '-x', 'dos': '-x' if out > 0 else '+x', 'debut': '-z', 'fin': '+z'}
    else:
        lo, hi = (a0, y0, plane + out * o0), (a1, y1, plane + out * o1)
        names = {'face': '+z' if out > 0 else '-z', 'dos': '-z' if out > 0 else '+z', 'debut': '-x', 'fin': '+x'}
    names.update(haut='+y', bas='-y')
    return block(name, lo, hi, mat, hide=[names[h] for h in hide])


def ring(name, x0, x1, z0, z1, y, bands, mat):
    """Cadre en gradins sous un plafond (à la hauteur y), autour d'une ouverture x[x0, x1] z[z0, z1] (verrière, caisson) :
    bands = [(de, à, retombée)], en mètres depuis le bord de l'ouverture, du plus profond au plus plat."""
    for a, b, drop in bands:
        inner = () if a == 0 else ('+z',)   # le côté intérieur d'un gradin plat est caché par le gradin plus profond
        block(name, (x0 - b, y - drop, z0 - b), (x1 + b, y, z0 - a), mat, hide=('+y',) + inner)
        block(name, (x0 - b, y - drop, z1 + a), (x1 + b, y, z1 + b), mat, hide=('+y',) + (() if a == 0 else ('-z',)))
        block(name, (x0 - b, y - drop, z0 - a), (x0 - a, y, z1 + a), mat, hide=('+y', '-z', '+z') + (() if a == 0 else ('+x',)))
        block(name, (x1 + a, y - drop, z0 - a), (x1 + b, y, z1 + a), mat, hide=('+y', '-z', '+z') + (() if a == 0 else ('-x',)))


def rosace(name, center, pts, mat, seg=20):
    """Rosace de plafond : le profil [(rayon, retombée)] tourné autour d'un axe vertical, du bord vers le centre."""
    cx, cy, cz = center
    p = lambda r, h, t: (cx + r * math.cos(t), cy - h, cz + r * math.sin(t))
    faces = []
    for (r0, h0), (r1, h1) in zip(pts, pts[1:]):
        for k in range(seg):
            t0, t1, tm = 2 * math.pi * k / seg, 2 * math.pi * (k + 1) / seg, 2 * math.pi * (k + 0.5) / seg
            corners = [p(r0, h0, t0), p(r0, h0, t1)] + ([p(r1, h1, t1), p(r1, h1, t0)] if r1 > 1e-6 else [p(0, h1, 0)])
            faces.append(face(corners, (math.cos(tm) * (h1 - h0), r1 - r0, math.sin(tm) * (h1 - h0))))
    return build(name, faces, mat)


def box(name, center, size, mat, shadow=True):
    cx, cy, cz = center
    sx, sy, sz = (s / 2 for s in size)
    p = lambda x, y, z: (cx + x * sx, cy + y * sy, cz + z * sz)
    faces = [face([p(1, -1, 1), p(1, -1, -1), p(1, 1, -1), p(1, 1, 1)], (1, 0, 0)),
             face([p(-1, -1, -1), p(-1, -1, 1), p(-1, 1, 1), p(-1, 1, -1)], (-1, 0, 0)),
             face([p(-1, 1, 1), p(1, 1, 1), p(1, 1, -1), p(-1, 1, -1)], (0, 1, 0)),
             face([p(-1, -1, -1), p(1, -1, -1), p(1, -1, 1), p(-1, -1, 1)], (0, -1, 0)),
             face([p(-1, -1, 1), p(1, -1, 1), p(1, 1, 1), p(-1, 1, 1)], (0, 0, 1)),
             face([p(1, -1, -1), p(-1, -1, -1), p(-1, 1, -1), p(1, 1, -1)], (0, 0, -1))]
    return build(name, faces, mat, shadow=shadow)


def vault(name, x0, x1, z0, z1, spring, rise, mat, steps=28):
    """Voûte en berceau surbaissé, dans la longueur x, au-dessus de la naissance `spring`."""
    half = (z1 - z0) / 2
    zc = (z0 + z1) / 2
    radius = (half ** 2 + rise ** 2) / (2 * rise)
    yc = spring + rise - radius
    t1 = math.asin(half / radius)
    faces, uvs = [], []
    for i in range(steps):
        ta, tb = -t1 + 2 * t1 * i / steps, -t1 + 2 * t1 * (i + 1) / steps
        za, ya = zc + radius * math.sin(ta), yc + radius * math.cos(ta)
        zb, yb = zc + radius * math.sin(tb), yc + radius * math.cos(tb)
        quad = [(x0, ya, za), (x1, ya, za), (x1, yb, zb), (x0, yb, zb)]
        mid = V(0, yc - (ya + yb) / 2, zc - (za + zb) / 2)
        ordered = face(quad, tuple(mid))
        sa, sb = radius * ta, radius * tb
        uv = [(x0, sa), (x1, sa), (x1, sb), (x0, sb)]
        faces.append(ordered)
        uvs.append(uv if ordered is quad else uv[::-1])
    return build(name, faces, mat, uvs)


# ---------- Lumières ----------
def spot(name, origin, target, angle, energy, color=(1, 0.97, 0.93)):
    light = bpy.data.lights.new(name, 'SPOT')
    light.energy, light.color = energy, color
    light.spot_size, light.spot_blend = 2 * angle, 0.85
    light.shadow_soft_size = 0.05
    obj = bpy.data.objects.new(name, light)
    obj.location = B(*origin)
    obj.rotation_euler = (B(*target) - B(*origin)).normalized().to_track_quat('-Z', 'Y').to_euler()
    bpy.context.collection.objects.link(obj)


def area(name, center, size, energy, color=(1, 0.98, 0.95)):
    light = bpy.data.lights.new(name, 'AREA')
    light.shape = 'RECTANGLE'
    light.size, light.size_y = size
    light.energy, light.color = energy, color
    obj = bpy.data.objects.new(name, light)
    obj.location = B(*center)   # orientée vers le bas par défaut
    bpy.context.collection.objects.link(obj)


BLACK = None


def fixture(origin, target, ceiling):
    """Projecteur noir suspendu au plafond."""
    d = (V(*target) - V(*origin)).normalized()
    body = bpy.data.meshes.new('projecteur')
    obj = bpy.data.objects.new('projecteur', body)
    bpy.context.collection.objects.link(obj)
    import bmesh
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=20, radius1=0.045, radius2=0.052, depth=0.17)
    bm.to_mesh(body)
    bm.free()
    obj.location = B(*origin)
    obj.rotation_euler = B(*d).to_track_quat('Z', 'Y').to_euler()
    obj.data.materials.append(BLACK)
    obj.visible_shadow = False
    stem = box('tige', (origin[0], (ceiling + origin[1]) / 2, origin[2]), (0.014, ceiling - origin[1], 0.014), BLACK, shadow=False)
    return obj, stem


# ---------- Œuvres ----------
FRAME = MOUNT = None


def photo_file(name):
    for width in (1600, 1500, 1333, 1250, 960):
        path = os.path.join(OPT, f'{name}-{width}.webp')
        if os.path.exists(path):
            return path
    raise FileNotFoundError(name)


SLOTS = []      # emplacements d'accrochage (mur, taille, projecteur) : la page 3D y pose les photos choisies
# Projecteurs, pour l'éclairage en temps réel de la page (reflets, relief des murs) : salle, position (bouche du
# boîtier), cible, demi-angle du faisceau (radians), puissance (W, comme dans Blender), couleur
SPOTS = []
FIXTURES = []   # projecteurs (salle, position, normale du mur, plafond) : les rails les relient (voir rails)
# Ses choix (emplacement → photo), appliqués par scripts/accrocher.py sans nouvelle cuisson ; ici pour les images fixes
CHOICES_FILE = os.path.join(ROOT, 'data', 'galerie-accrochage.json')
try:
    with open(CHOICES_FILE, encoding='utf-8') as _f:
        CHOICES = json.load(_f)
except (OSError, ValueError):
    CHOICES = {}


GROW = 1.22   # photos agrandies le 28/11 (« photos plus grandes ») : taille × 1,22, au plus 1,8 m


def hang(name, at, n, size, ceiling, energy, color=(1, 0.97, 0.93), room='hall', drop=0.3):
    """Un emplacement d'accrochage sur un mur et son projecteur (cuit dans la lumière des salles). Le cadre et la photo
    ne sont fabriqués ici que pour les images fixes : sur le site, la page les pose elle-même (scripts/accrocher.py),
    changer de photo ne demande donc aucune nouvelle cuisson. `name` : la photo par défaut de l'emplacement."""
    grown = round(min(size * GROW, 1.8), 3)
    energy *= (grown / size) ** 2   # même éclairement sur une photo plus grande
    size = grown
    slot = f'{room}_{sum(1 for s in SLOTS if s["salle"] == room) + 1}'
    SLOTS.append({'id': slot, 'salle': room, 'centre': [round(v, 4) for v in at], 'normale': [round(v, 4) for v in n],
                  'taille': size, 'photo': name})
    if MODE == 'rendu' and CHOICES.get(slot, name):
        frame_photo(CHOICES.get(slot, name), at, n, size)
    n, at = V(*n), V(*at)
    # projecteur au plafond ; la lumière sort de la bouche du boîtier (au centre, le boîtier l'enfermait).
    # Son faisceau couvre un cadre de la taille de l'emplacement, quelle que soit la photo posée.
    origin = at + n * 1.55
    origin.y = ceiling - drop
    FIXTURES.append((room, origin.copy(), n.copy(), ceiling))
    target = at + V(0, 0.05, 0)
    mouth = origin + (target - origin).normalized() * 0.1
    reach = (target - mouth).length
    angle = math.atan(((size * 1.25 + 0.06) * 0.62 + 0.15) / reach)
    spot('projecteur', tuple(mouth), tuple(target), angle, energy, color)
    SPOTS.append({'salle': room, 'position': [round(v, 4) for v in mouth], 'cible': [round(v, 4) for v in target],
                  'angle': round(angle, 4), 'flou': 0.85, 'puissance': round(energy, 1), 'couleur': list(color)})
    for part in fixture(tuple(origin), tuple(target), ceiling):
        part['groupe'] = f'luminaires_{room}'   # sans ombre à la cuisson (voir cuisson)


def frame_photo(name, at, n, size):
    """Photo encadrée (cadre noir, passe-partout blanc) posée sur un mur : pour les images fixes seulement
    (galerie.js fabrique les mêmes cadres sur le site)."""
    ident = re.sub(r'[^A-Za-z0-9]+', '_', name.split('projet_perso_')[-1]).strip('_').lower()
    mat, image = photo_material(photo_file(name))
    ratio = image.size[0] / image.size[1]
    w, h = (size, size / ratio) if ratio >= 1 else (size * ratio, size)
    margin = max(0.09, min(w, h) * 0.15)
    bar, depth = 0.03, 0.035
    n = V(*n)
    right = V(0, 1, 0).cross(n)   # la droite pour qui regarde l'œuvre
    at = V(*at)
    W, H = w + 2 * margin, h + 2 * margin
    local = lambda x, y, z: at + right * x + V(0, 1, 0) * y + n * z
    # passe-partout (plaque), photo légèrement en retrait sous une fenêtre de passe-partout
    parts = []
    for (cx, cy, sx, sy) in [(0, (h + margin) / 2, W, margin), (0, -(h + margin) / 2, W, margin),
                             ((w + margin) / 2, 0, margin, h), (-(w + margin) / 2, 0, margin, h)]:
        c = local(cx, cy, depth - 0.006)
        parts.append(face([c - right * sx / 2 - V(0, sy / 2, 0), c + right * sx / 2 - V(0, sy / 2, 0),
                           c + right * sx / 2 + V(0, sy / 2, 0), c - right * sx / 2 + V(0, sy / 2, 0)], tuple(n)))
    build(f'oeuvre_{ident}', parts, MOUNT)['groupe'] = f'oeuvre_{ident}'
    # coins dans l'ordre bas-gauche, bas-droite, haut-droite, haut-gauche : la face regarde vers n, l'image est droite
    c, up = local(0, 0, depth - 0.009), V(0, 1, 0)
    corners = [c - right * w / 2 - up * h / 2, c + right * w / 2 - up * h / 2, c + right * w / 2 + up * h / 2, c - right * w / 2 + up * h / 2]
    build(f'photo_{ident}', [corners], mat, uvs=[[(0, 0), (1, 0), (1, 1), (0, 1)]])['groupe'] = f'photo_{ident}'
    # cadre : quatre baguettes
    for (cx, cy, sx, sy) in [(0, (H + bar) / 2, W + 2 * bar, bar), (0, -(H + bar) / 2, W + 2 * bar, bar),
                             ((W + bar) / 2, 0, bar, H), (-(W + bar) / 2, 0, bar, H)]:
        center = local(cx, cy, depth / 2)
        size3 = right * sx + V(0, sy, 0) + n * depth
        box(f'oeuvre_{ident}', tuple(center), (abs(size3.x) or 0.001, abs(size3.y), abs(size3.z) or 0.001), FRAME)['groupe'] = f'oeuvre_{ident}'


def sign(text, at, n, size=0.25, room='hall'):
    curve = bpy.data.curves.new(name=text, type='FONT')
    curve.body = text
    if os.path.exists(FONT):
        curve.font = bpy.data.fonts.load(FONT, check_existing=True)
    curve.size = size
    curve.space_character = 1.25
    curve.align_x = 'CENTER'
    curve.align_y = 'CENTER'
    curve.extrude = 0          # lettres plates, courbes moins découpées : le fichier 3D passe de 1 Mo à bien moins
    curve.resolution_u = 4
    obj = bpy.data.objects.new(text, curve)
    bpy.context.collection.objects.link(obj)
    nb = B(*n)
    up = Vector((0, 0, 1))
    x = up.cross(nb)
    obj.matrix_world = Matrix.Translation(B(*(V(*at) + V(*n) * 0.004))) @ Matrix((x, up, nb)).transposed().to_4x4()
    obj.data.materials.append(flat('lettres', (0.012, 0.012, 0.012), 0.55))
    obj['groupe'] = f'lettres_{room}'   # le nom d'une salle, au-dessus de sa porte : un clic y mène


OAK = None
OBSTACLES = []   # où l'on ne peut pas marcher (les bancs) : x0, x1, z0, z1, pour la page 3D


def bench(center, room='hall'):
    """Banc de musée : plateau de chêne sur deux piètements d'acier noir, dans la longueur x."""
    cx, _, cz = center
    OBSTACLES.append([round(cx - 0.9, 3), round(cx + 0.9, 3), round(cz - 0.23, 3), round(cz + 0.23, 3)])
    box('banc', (cx, 0.45, cz), (1.8, 0.05, 0.46), OAK)['groupe'] = f'banc_{room}'
    for dx in (-0.72, 0.72):
        box('pied', (cx + dx, 0.2125, cz), (0.035, 0.425, 0.4), BLACK)['groupe'] = f'banc_{room}'


def casing_profile(kind, w, dep):
    """Profil d'un chambranle (saillie, travers depuis le bord de la baie), large de w, épais de dep."""
    if kind == 'pierre':    # pierre de taille, arête chanfreinée côté baie
        return [(0, 0), (dep * 0.6, 0), (dep, dep * 0.5), (dep, w), (0, w)]
    if kind == 'moderne':   # plat, arêtes adoucies
        return [(0, 0), (dep - 0.006, 0), (dep, 0.006), (dep, w - 0.006), (dep - 0.006, w), (0, w)]
    # moulure classique : baguette côté baie, champ plat en retrait, contre-profil qui remonte vers l'extérieur
    return [(0, 0), (dep * 0.75, 0), (dep * 0.75, w * 0.1), (dep * 0.55, w * 0.18), (dep * 0.55, w * 0.55),
            (dep * 0.8, w * 0.68), (dep, w * 0.8), (dep, w), (0, w)]


def casing(name, axis, plane, side, center, width, height, mat, w=0.09, depth=0.022, cap=False, profile='moulure', bottom=0.0):
    """Chambranle mouluré d'une porte, posé sur le mur `plane` (x = plane si axis == 'x', sinon z = plane), côté `side`
    (±1) : deux montants et un linteau assemblés en onglet. cap : une petite corniche posée dessus (dessus-de-porte).
    profile : 'moulure' (bois peint), 'pierre', 'moderne' ; bottom : bas des montants (au-dessus d'une banquette)."""
    n = (side, 0, 0) if axis == 'x' else (0, 0, side)
    along = V(0, 0, 1) if axis == 'x' else V(1, 0, 0)
    at = lambda a, y: (plane, y, a) if axis == 'x' else (a, y, plane)
    pts = casing_profile(profile, w, depth)
    for edge, away in ((center - width / 2, -1), (center + width / 2, 1)):
        extrude(name, at(edge, bottom), (0, 1, 0), height + w - bottom, n, tuple(along * away), pts, mat, caps=(False, False))
    extrude(name, at(center - width / 2 - w, height), tuple(along), width + 2 * w, n, (0, 1, 0), pts, mat, caps=(False, False))
    if cap:   # 1 mm au-dessus du linteau (pas de faces confondues), 4 cm plus large de chaque côté
        k = depth
        top = ([(0, 0), (k + 0.012, 0), (k + 0.012, 0.02)] + quarter(k + 0.012, 0.02, k + 0.045, 0.055, False, 2)
               + [(k + 0.06, 0.055), (k + 0.06, 0.085), (0, 0.105)])
        extrude(name, at(center - width / 2 - w - 0.04, height + w + 0.001), tuple(along), width + 2 * w + 0.08, n, (0, 1, 0), top, mat)


def pilaster(name, axis, plane, side, center, width, top, mat, base_mat, cap_mat, depth=0.05):
    """Pilastre plat contre un mur, du sol jusqu'à `top` (le dessous de la corniche) : socle peint, fût de la matière du
    mur, chapiteau en deux gradins."""
    c0, c1 = center - width / 2, center + width / 2
    on_wall(name, axis, plane, side, c0 - 0.03, c1 + 0.03, 0, depth + 0.03, 0, 0.24, base_mat, hide=('dos', 'bas'))
    on_wall(name, axis, plane, side, c0, c1, 0, depth, 0.24, top - 0.16, mat, hide=('dos', 'bas', 'haut'))
    on_wall(name, axis, plane, side, c0 - 0.02, c1 + 0.02, 0, depth + 0.02, top - 0.16, top - 0.08, cap_mat, hide=('dos', 'haut'))
    on_wall(name, axis, plane, side, c0 - 0.04, c1 + 0.04, 0, depth + 0.04, top - 0.08, top, cap_mat, hide=('dos', 'haut'))


def stone_bench(name, axis, plane, side, a0, a1, mat, ends=(True, True)):
    """Banc de pierre contre un mur, de a0 à a1 : une dalle de 7 cm sur un massif en retrait. ends : bouts visibles
    (pas contre un mur). C'est un obstacle pour la page 3D, comme les bancs du hall."""
    hidden = [h for h, keep in zip(('debut', 'fin'), ends) if not keep]
    on_wall(name, axis, plane, side, a0, a1, 0, 0.42, 0.38, 0.45, mat, hide=['dos'] + hidden)
    b0, b1 = (a0 + 0.04 if ends[0] else a0), (a1 - 0.04 if ends[1] else a1)
    on_wall(name, axis, plane, side, b0, b1, 0, 0.36, 0, 0.38, mat, hide=['dos', 'haut', 'bas'] + hidden)
    w0, w1 = sorted((plane, plane + side * 0.42))
    OBSTACLES.append([round(a0, 3), round(a1, 3), round(w0, 3), round(w1, 3)] if axis == 'z' else
                     [round(w0, 3), round(w1, 3), round(a0, 3), round(a1, 3)])


def rails():
    """Rails d'éclairage au plafond : un par mur portant des œuvres ; chaque projecteur y est suspendu."""
    lines = {}
    for room, origin, n, ceiling in FIXTURES:
        if room == 'couvent':   # sous la voûte, les projecteurs pendent à leur tige
            continue
        across = origin.x if abs(n.x) > 0.5 else origin.z
        lines.setdefault((room, round(n.x), round(n.z), round(across, 2), ceiling), []).append(origin)
    for (room, nx, nz, across, ceiling), points in lines.items():
        x0, x1, z0, z1 = SALLES[room]['rect']
        if abs(nx) > 0.5:
            lo, hi = max(min(p.z for p in points) - 0.7, z0 + 0.4), min(max(p.z for p in points) + 0.7, z1 - 0.4)
            center, size = (across, ceiling - 0.02, (lo + hi) / 2), (0.045, 0.035, hi - lo)
        else:
            lo, hi = max(min(p.x for p in points) - 0.7, x0 + 0.4), min(max(p.x for p in points) + 0.7, x1 - 0.4)
            center, size = ((lo + hi) / 2, ceiling - 0.02, across), (hi - lo, 0.035, 0.045)
        box('rail', center, size, BLACK, shadow=False)['groupe'] = f'luminaires_{room}'


def arches(xs, X0, X1, Z0, Z1, S, R, mat, width=0.42, depth=0.14, steps=28):
    """Arcs doubleaux sous la voûte (en x = xs) et leurs pilastres le long des murs : le rythme d'un vrai couvent."""
    half, zc = (Z1 - Z0) / 2, (Z0 + Z1) / 2
    radius = (half ** 2 + R ** 2) / (2 * R)
    yc, t1 = S + R - radius, math.asin(half / radius)
    inner = radius - depth
    for xc in xs:
        xa, xb = xc - width / 2, xc + width / 2
        faces, uvs = [], []

        def add(quad, normal, uv):
            ordered = face(quad, normal)
            faces.append(ordered)
            uvs.append(uv if ordered is quad else uv[::-1])

        for i in range(steps):
            ta, tb = -t1 + 2 * t1 * i / steps, -t1 + 2 * t1 * (i + 1) / steps
            ia = (zc + inner * math.sin(ta), yc + inner * math.cos(ta))
            ib = (zc + inner * math.sin(tb), yc + inner * math.cos(tb))
            oa = (zc + radius * math.sin(ta), yc + radius * math.cos(ta))
            ob = (zc + radius * math.sin(tb), yc + radius * math.cos(tb))
            inward = (0, yc - (ia[1] + ib[1]) / 2, zc - (ia[0] + ib[0]) / 2)
            add([(xa, ia[1], ia[0]), (xb, ia[1], ia[0]), (xb, ib[1], ib[0]), (xa, ib[1], ib[0])], inward,
                [(xa, inner * ta), (xb, inner * ta), (xb, inner * tb), (xa, inner * tb)])
            for xs_, nx in ((xa, -1), (xb, 1)):
                add([(xs_, ia[1], ia[0]), (xs_, ib[1], ib[0]), (xs_, ob[1], ob[0]), (xs_, oa[1], oa[0])], (nx, 0, 0),
                    [(ia[0], ia[1]), (ib[0], ib[1]), (ob[0], ob[1]), (oa[0], oa[1])])
        build('couvent_arc', faces, mat, uvs)
        for z, out in ((Z0, 1), (Z1, -1)):
            # pilastre sur une base plus large, coiffé d'une imposte en deux gradins où l'arc prend naissance
            on_wall('couvent_pilastre', 'z', z, out, xa, xb, 0, depth, 0.34, S - 0.16, mat, hide=('dos', 'haut', 'bas'))
            on_wall('couvent_pilastre', 'z', z, out, xa - 0.03, xb + 0.03, 0, depth + 0.03, 0, 0.34, mat, hide=('dos', 'bas'))
            on_wall('couvent_pilastre', 'z', z, out, xa - 0.03, xb + 0.03, 0, depth + 0.03, S - 0.16, S - 0.08, mat, hide=('dos', 'haut'))
            on_wall('couvent_pilastre', 'z', z, out, xa - 0.06, xb + 0.06, 0, depth + 0.06, S - 0.08, S, mat, hide=('dos', 'haut'))


# ---------- Le musée ----------
def museum():
    global BLACK, FRAME, MOUNT, OAK
    BLACK = flat('noir', (0.015, 0.015, 0.015), 0.4, 0.3)
    FRAME = flat('cadre', (0.02, 0.019, 0.018), 0.38)
    MOUNT = flat('passe-partout', (0.88, 0.875, 0.86), 0.92)
    white = paint('blanc', (0.84, 0.83, 0.81))
    ceiling = paint('plafond', (0.86, 0.86, 0.85), bump=0.05)
    trim = flat('plinthe', (0.8, 0.8, 0.79), 0.45)   # plinthes et chambranles peints, satinés

    def textured(name):
        m = MATIERES[name]
        return pbr(name, m['texture'], m['tuile'], tint=tuple(m['teinte']), rough=m.get('rugosite', 1.0))

    parquet, light_parquet, OAK = textured('parquet'), textured('parquet_clair'), textured('chene')
    stone, slabs = textured('pierre'), textured('dalles')
    brick, concrete, wood = textured('brique'), textured('beton'), textured('bois')
    lime, terracotta = textured('chaux'), textured('tomettes')
    red, marble, wood_ceiling = textured('rouge'), textured('marbre'), textured('bois_plafond')
    plaster, panelling = textured('enduit'), textured('lambris')
    cornice = flat('corniche', (0.84, 0.82, 0.78), 0.6)
    threshold = textured('seuil')   # seuils de pierre des portes

    # --- Hall (photos isolées) : enduit blanc cassé, corniche moulurée, verrière dans un plafond à gradins, pilastres,
    # plinthes et chambranles moulurés ---
    H = 5.0
    floor('hall_sol', -5, 5, -6, 6, 0, parquet)
    moulures = dict(plinth=(trim, PLINTHE), cornice=(cornice, CORNICHE), trim=0.12)
    wall('hall_ouest', (-5, 0, -6), (0, 0, 1), (1, 0, 0), 12, H, plaster, [(1.9, 4.1, 3.2, 0), (7.9, 10.1, 3.2, 0)], **moulures)
    wall('hall_est', (5, 0, -6), (0, 0, 1), (-1, 0, 0), 12, H, plaster, [(1.9, 4.1, 3.2, 0), (7.9, 10.1, 3.2, 0)], **moulures)
    wall('hall_nord', (-5, 0, -6), (1, 0, 0), (0, 0, 1), 10, H, plaster, [(3.4, 6.6, 3.4, 0)], **moulures)
    wall('hall_sud', (-5, 0, 6), (1, 0, 0), (0, 0, -1), 10, H, plaster, [(3.5, 6.5, 3.0, 0)], **dict(moulures, trim=0.16))
    # chambranles moulurés, coiffés d'un dessus-de-porte (sous le nom de la salle) ; la porte d'entrée, plus large
    for z in (-3, 3):
        casing('hall_chambranle', 'x', -5, 1, z, 2.2, 3.2, trim, w=0.12, depth=0.03, cap=True)
        casing('hall_chambranle', 'x', 5, -1, z, 2.2, 3.2, trim, w=0.12, depth=0.03, cap=True)
    casing('hall_chambranle', 'z', -6, 1, 0, 3.2, 3.4, trim, w=0.12, depth=0.03, cap=True)
    casing('hall_chambranle', 'z', 6, -1, 0, 3.0, 3.0, trim, w=0.16, depth=0.035, cap=True)
    # pilastres entre chaque porte et la photo du milieu (murs ouest et est), jusque sous la corniche
    for x, out in ((-5, 1), (5, -1)):
        for z in (-1.33, 1.33):
            pilaster('hall_pilastre', 'x', x, out, z, 0.36, H - 0.34, plaster, trim, cornice)
    # plafond percé de la verrière x[-3,3] z[-4,4] : un puits blanc, un verre dépoli lumineux, des croisillons d'acier
    for (x0, x1, z0, z1) in [(-5, 5, -6, -4), (-5, 5, 4, 6), (-5, -3, -4, 4), (3, 5, -4, 4)]:
        floor('hall_plafond', x0, x1, z0, z1, H, ceiling, up=False)
    # autour de la verrière, un cadre en deux gradins ; plus loin, une baguette dessine un grand caisson (loin des rails)
    ring('hall_caisson', -3, 3, -4, 4, H, [(0, 0.14, 0.1), (0.14, 0.34, 0.04)], cornice)
    baguette = [(0, 0), (0.008, 0.006), (0.016, 0.02), (0.016, 0.05), (0.008, 0.064), (0, 0.07)]
    for z in (-5.4, 5.4):
        extrude('hall_baguette', (-4.435, H, z - 0.035), (1, 0, 0), 8.87, (0, -1, 0), (0, 0, 1), baguette, cornice, caps=(False, False))
    for x in (-4.4, 4.4):
        extrude('hall_baguette', (x - 0.035, H, -5.435), (0, 0, 1), 10.87, (0, -1, 0), (1, 0, 0), baguette, cornice, caps=(False, False))
    for (start, d, n, length) in [((-3, H, -4), (1, 0, 0), (0, 0, 1), 6), ((-3, H, 4), (1, 0, 0), (0, 0, -1), 6),
                                  ((-3, H, -4), (0, 0, 1), (1, 0, 0), 8), ((3, H, -4), (0, 0, 1), (-1, 0, 0), 8)]:
        w_obj = wall('puits', (start[0], 0, start[2]), d, n, length, 0.7, white)
        w_obj.location.z += H
    floor('verriere', -3, 3, -4, 4, H + 0.7, glow('verriere', (0.94, 0.965, 1.0), 2.8), up=False)['groupe'] = 'lumineux_verriere'
    for xm in (-2, -1, 0, 1, 2):
        box('verriere_barre', (xm, H + 0.64, 0), (0.04, 0.08, 8), BLACK, shadow=False)['groupe'] = 'deco_hall'
    for zm in (-3, -2, -1, 0, 1, 2, 3):
        box('verriere_barre', (0, H + 0.64, zm), (6, 0.08, 0.04), BLACK, shadow=False)['groupe'] = 'deco_hall'
    area('verriere', (0, H + 0.5, 0), (6, 8), 2600, (0.94, 0.965, 1.0))
    # porte d'entrée vitrée (la lumière du jour), avec ses montants
    floor_glow = glow('jour', (0.95, 0.97, 1.0), 2.4)
    build('entree', [face([(-1.6, 0, 6.35), (1.6, 0, 6.35), (1.6, 3.1, 6.35), (-1.6, 3.1, 6.35)], (0, 0, -1))], floor_glow)['groupe'] = 'lumineux_entree'
    doorway('entree_embrasure', (6, 6.3), 'z', 0, 3.0, 3.0, white, threshold, sill=0.02)
    for xm in (-1.475, 0, 1.475):
        box('entree_barre', (xm, 1.5, 6.32), (0.05, 3.0, 0.05), BLACK, shadow=False)['groupe'] = 'deco_hall'
    box('entree_barre', (0, 2.35, 6.32), (3.0, 0.05, 0.05), BLACK, shadow=False)['groupe'] = 'deco_hall'
    bench((0, 0, 0.5), 'hall')
    singles = [('projet_perso_vrac_vrac-3', (-5, 1.55, 0), (1, 0, 0)), ('projet_perso_vrac_vrac-14', (5, 1.55, 0), (-1, 0, 0)),
               ('projet_perso_vrac_chartres-12', (-3.3, 1.55, 6), (0, 0, -1)), ('projet_perso_vrac_vrac-8', (3.3, 1.55, 6), (0, 0, -1)),
               ('projet_perso_vrac_vrac-2', (-3.3, 1.55, -6), (0, 0, 1)), ('projet_perso_vrac_vrac-1', (3.3, 1.55, -6), (0, 0, 1))]
    for name, at, n in singles:
        hang(name, at, n, 1.0, H, 520, room='hall')
    sign('COUVENT', (-5, 3.75, -3), (1, 0, 0), room='couvent')
    sign('TOULOUSE', (-5, 3.75, 3), (1, 0, 0), room='toulouse')
    sign('LA GARDE', (5, 3.75, -3), (-1, 0, 0), room='garde')
    sign('MESSE', (5, 3.75, 3), (-1, 0, 0), room='messe')
    sign('ÉCHAPPÉES EN MONTAGNE', (0, 3.95, -6), (0, 0, 1), room='montagne')

    # --- Couvent : pierre de taille, voûte en berceau sur deux arcs doubleaux, dallage ancien, lumière chaude ---
    X0, X1, Z0, Z1, S, R = -12.3, -5.3, -6, -0.15, 3.0, 1.4
    floor('couvent_sol', X0, X1, Z0, Z1, 0, slabs)
    # Les quatre murs montent jusqu'au toit : le vide au-dessus de la voûte est fermé, le ciel n'y entre plus
    # (sinon le haut caché des murs du fond, éclairé, déteint sur l'arc : un trait clair le long de la voûte)
    top = S + R + 0.02
    # soubassement de pierre au pied des murs, cordon mouluré à la naissance de la voûte (coupés à la porte)
    pierre = dict(plinth=(stone, SOCLE), bands=[('cordon', stone, CORDON)])
    wall('couvent_ouest', (X0, 0, Z0), (0, 0, 1), (1, 0, 0), Z1 - Z0, top, stone, **pierre)
    wall('couvent_est', (X1, 0, Z0), (0, 0, 1), (-1, 0, 0), Z1 - Z0, top, stone, [(1.9, 4.1, 3.2, 0)], trim=0.28, **pierre)
    wall('couvent_nord', (X0, 0, Z0), (1, 0, 0), (0, 0, 1), X1 - X0, top, stone, **pierre)
    wall('couvent_sud', (X0, 0, Z1), (1, 0, 0), (0, 0, -1), X1 - X0, top, stone, **pierre)
    vault('couvent_voute', X0, X1, Z0, Z1, S, R, stone)
    arches([X0 + (X1 - X0) * k / 3 for k in (1, 2)], X0, X1, Z0, Z1, S, R, stone)   # trois travées
    floor('couvent_toit', X0, X1, Z0, Z1, top, BLACK, up=False)['groupe'] = 'deco_couvent'
    doorway('couvent_porte', (-5.3, -5), 'x', -3, 2.2, 3.2, stone, stone, sill=0.025)   # seuil de pierre
    # encadrement de pierre de la porte, côté salle (montants et linteau chanfreinés)
    casing('couvent_chambranle', 'x', X1, -1, -3, 2.2, 3.2, stone, w=0.28, depth=0.05, profile='pierre')
    # bancs de pierre le long des murs, dans les travées sans photo (pilastres à ±0,21 m du milieu des arcs)
    arcs = [X0 + (X1 - X0) * k / 3 for k in (1, 2)]
    stone_bench('couvent_banc', 'z', Z0, 1, arcs[0] + 0.31, arcs[1] - 0.31, stone)
    stone_bench('couvent_banc', 'z', Z1, -1, X0, arcs[0] - 0.31, stone, ends=(False, True))
    # hauteur de la voûte au-dessus d'un point : les projecteurs y sont suspendus par leur tige
    half, zc = (Z1 - Z0) / 2, (Z0 + Z1) / 2
    radius = (half ** 2 + R ** 2) / (2 * R)
    under_vault = lambda z: S + R - radius + math.sqrt(radius ** 2 - (z - zc) ** 2)
    bays = [X0 + (X1 - X0) * (k + 0.5) / 3 for k in range(3)]   # milieu de chaque travée
    warm = (1, 0.9, 0.76)
    hang('projet_perso_argentique_argentique_couvent_argentiqueNB-15', (X0, 1.6, -3.075), (1, 0, 0), 1.35, under_vault(-3.075), 650, warm, room='couvent', drop=0.7)
    hang('projet_perso_argentique_argentique_couvent_argentiqueNB-4', (bays[0], 1.55, Z0), (0, 0, 1), 0.95, under_vault(Z0 + 1.55), 520, warm, room='couvent', drop=0.6)
    hang('projet_perso_argentique_argentique_couvent_argentiqueNB-8', (bays[2], 1.55, Z0), (0, 0, 1), 0.95, under_vault(Z0 + 1.55), 520, warm, room='couvent', drop=0.6)
    hang('projet_perso_argentique_argentique_couvent_argentiqueNB-13', (bays[1], 1.55, Z1), (0, 0, -1), 0.95, under_vault(Z1 - 1.55), 520, warm, room='couvent', drop=0.6)
    area('couvent_ambiance', (-8.8, S + R - 0.05, -3.075), (5, 3), 70, warm)

    # --- Toulouse : vieille brique à joints de chaux, béton, plafond à la française (solives de bois sombre sur
    # un fond chaulé : le plafond n'est plus un trou noir) ---
    X0, X1, Z0, Z1, Hh = -12.3, -5.3, 0.15, 6, 4.2
    floor('toulouse_sol', X0, X1, Z0, Z1, 0, concrete)
    floor('toulouse_plafond', X0, X1, Z0, Z1, Hh, lime, up=False)
    wall('toulouse_ouest', (X0, 0, Z0), (0, 0, 1), (1, 0, 0), Z1 - Z0, Hh, brick)
    wall('toulouse_est', (X1, 0, Z0), (0, 0, 1), (-1, 0, 0), Z1 - Z0, Hh, brick, [(1.75, 3.95, 3.2, 0)])
    wall('toulouse_nord', (X0, 0, Z0), (1, 0, 0), (0, 0, 1), X1 - X0, Hh, brick)
    wall('toulouse_sud', (X0, 0, Z1), (1, 0, 0), (0, 0, -1), X1 - X0, Hh, brick)
    for i in range(12):
        box('toulouse_solive', (X0 + 0.3 + i * (X1 - X0 - 0.6) / 11, Hh - 0.09, (Z0 + Z1) / 2), (0.12, 0.18, Z1 - Z0), wood)
    # sablières : deux poutres le long des murs nord et sud, où reposent les bouts des solives
    for z, out in ((Z0, 1), (Z1, -1)):
        on_wall('toulouse_sabliere', 'z', z, out, X0, X1, 0, 0.16, Hh - 0.36, Hh - 0.18, wood, hide=('dos', 'haut', 'debut', 'fin'))
    # deux tirants de fer d'un mur à l'autre, au-dessus des têtes, avec platine et écrou ; placés entre les faisceaux
    # des projecteurs (x = -10,4, -8,8, -7,4) pour ne pas faire d'ombre sur les photos
    for x in (-9.6, -8.0):
        box('tirant', (x, 3.45, (Z0 + Z1) / 2), (0.026, 0.026, Z1 - Z0), BLACK)['groupe'] = 'deco_toulouse'
        for z, out in ((Z0, 1), (Z1, -1)):
            box('platine', (x, 3.45, z + out * 0.01), (0.14, 0.14, 0.02), BLACK)['groupe'] = 'deco_toulouse'
            box('ecrou', (x, 3.45, z + out * 0.035), (0.05, 0.05, 0.03), BLACK)['groupe'] = 'deco_toulouse'
    doorway('toulouse_porte', (-5.3, -5), 'x', 3, 2.2, 3.2, brick, threshold, sill=0.02)
    # linteau de bois au-dessus de la porte, côté salle
    on_wall('toulouse_linteau', 'x', X1, -1, 1.6, 4.4, 0, 0.035, 3.2, 3.44, wood)
    beams = Hh - 0.18   # les projecteurs pendent sous les solives
    hang('projet_perso_argentique_argentique_toulouse_argentiqueNB-9', (X0, 1.6, 3.075), (1, 0, 0), 1.55, beams, 780, room='toulouse')
    hang('projet_perso_argentique_argentique_toulouse_argentiqueNB-10', (-10.4, 1.55, Z0), (0, 0, 1), 1.0, beams, 650, room='toulouse')
    hang('projet_perso_argentique_argentique_toulouse_argentiqueNB-11', (-7.4, 1.55, Z0), (0, 0, 1), 1.0, beams, 650, room='toulouse')
    hang('projet_perso_argentique_argentique_toulouse_argentiqueNB-23', (-8.8, 1.55, Z1), (0, 0, -1), 1.0, beams, 650, room='toulouse')
    area('toulouse_ambiance', (-8.8, Hh - 0.3, 3.075), (5, 4), 180)

    # --- La Garde : enduit à la chaux, tomettes, un rayon de soleil par une fenêtre haute à croisée ---
    X0, X1, Z0, Z1, Hh = 5.3, 12.3, -6, -0.15, 4.6
    floor('garde_sol', X0, X1, Z0, Z1, 0, terracotta)
    floor('garde_plafond', X0, X1, Z0, Z1, Hh, ceiling, up=False)
    wall('garde_ouest', (X0, 0, Z0), (0, 0, 1), (1, 0, 0), Z1 - Z0, Hh, lime, [(1.9, 4.1, 3.2, 0)])
    wall('garde_est', (X1, 0, Z0), (0, 0, 1), (-1, 0, 0), Z1 - Z0, Hh, lime, [(2.325, 3.525, 4.15, 3.0)])
    wall('garde_nord', (X0, 0, Z0), (1, 0, 0), (0, 0, 1), X1 - X0, Hh, lime)
    wall('garde_sud', (X0, 0, Z1), (1, 0, 0), (0, 0, -1), X1 - X0, Hh, lime)
    doorway('garde_porte', (5, 5.3), 'x', -3, 2.2, 3.2, lime, threshold, sill=0.02)
    # mur épais de monastère ; appui de pierre de 4 cm, qui dépasse à peine dans la salle (le soleil passe au-dessus)
    doorway('garde_fenetre', (12.3, 12.75), 'x', -3.075, 1.2, 4.15, lime, threshold, bottom=3.0, sill=0.04)
    # trois poutres de bois sous le plafond, posées sur des corbeaux ; les rails des projecteurs y sont fixés (ils
    # passent au-dessus, à 4,58 m). Le rayon de soleil entre par le haut de la fenêtre (4,15 m) et descend : il passe
    # sous les poutres et sous les corbeaux (dessous à 4,22 m)
    for z in (-4.45, -3.075, -1.7):
        block('garde_poutre', (X0, Hh - 0.22, z - 0.1), (X1, Hh, z + 0.1), wood, hide=('-x', '+x', '+y'))
        for x, out in ((X0, 1), (X1, -1)):
            extrude('garde_corbeau', (x, 0, z - 0.08), (0, 0, 1), 0.16, (out, 0, 0), (0, 1, 0),
                    [(0, Hh - 0.38), (0.07, Hh - 0.38), (0.18, Hh - 0.27), (0.18, Hh - 0.22)], wood)
    # croisée de bois sombre : son ombre se dessine dans la tache de soleil
    for z in (-3.65, -3.075, -2.5):
        box('croisee', (12.62, 3.575, z), (0.05, 1.15, 0.05), BLACK)['groupe'] = 'deco_garde'
    for y in (3.025, 3.62, 4.125):
        box('croisee', (12.62, y, -3.075), (0.05, 0.05, 1.2), BLACK)['groupe'] = 'deco_garde'
    hang('projet_perso_la_garde_2026_02_LaGarde-29', (X1, 1.5, -3.075), (-1, 0, 0), 1.3, Hh, 420, room='garde')
    hang('projet_perso_la_garde_2026_02_LaGarde-25', (7.3, 1.55, Z0), (0, 0, 1), 1.1, Hh, 420, room='garde')
    hang('projet_perso_la_garde_2026_02_LaGarde-9', (10.4, 1.55, Z0), (0, 0, 1), 1.0, Hh, 420, room='garde')
    hang('projet_perso_la_garde_2026_02_LaGarde-21', (8.8, 1.55, Z1), (0, 0, -1), 1.0, Hh, 420, room='garde')
    area('garde_ambiance', (8.8, Hh - 0.02, -3.075), (5, 4), 95)
    vol_mat = bpy.data.materials.new('air')
    try:
        vol_mat.use_nodes = True
    except AttributeError:
        pass
    vnodes = vol_mat.node_tree.nodes
    vnodes.remove(vnodes['Principled BSDF'])
    volume = vnodes.new('ShaderNodeVolumePrincipled')
    volume.inputs['Density'].default_value = 0.035
    volume.inputs['Anisotropy'].default_value = 0.45
    vol_mat.node_tree.links.new(volume.outputs['Volume'], vnodes['Material Output'].inputs['Volume'])
    air = box('air', ((X0 + X1) / 2, Hh / 2, (Z0 + Z1) / 2), (X1 - X0 - 0.02, Hh - 0.02, Z1 - Z0 - 0.02), vol_mat, shadow=False)
    air['groupe'] = 'air'   # seulement pour les rendus fixes (rayon visible)

    # --- Messe : murs rouge sombre au-dessus d'un lambris de bois sombre (cimaise), corniche claire, marbre clair,
    # lumière dorée ---
    X0, X1, Z0, Z1, Hh = 5.3, 12.3, 0.15, 6, 4.2
    dark_trim = flat('plinthe_bois', (0.05, 0.032, 0.022), 0.5)
    dado = (0.78, panelling, dark_trim)   # les cadres commencent au-dessus (voir les hauteurs d'accrochage)
    floor('messe_sol', X0, X1, Z0, Z1, 0, marble)
    # plafond : un caisson au milieu, 15 cm plus haut, bordé d'une moulure en gradins, avec une rosace ; entre les rails
    # des projecteurs (z = 1,7 et 4,45 ; x = 10,75), centré sur la salle
    cx0, cx1, cz0, cz1, rise = 7.15, 10.45, 2.1, 4.05, 0.15
    for (a, b, c, e) in [(X0, X1, Z0, cz0), (X0, X1, cz1, Z1), (X0, cx0, cz0, cz1), (cx1, X1, cz0, cz1)]:
        floor('messe_plafond', a, b, c, e, Hh, ceiling, up=False)
    floor('messe_plafond', cx0, cx1, cz0, cz1, Hh + rise, ceiling, up=False)
    build('messe_caisson', [face([(cx0, Hh, cz0), (cx0, Hh, cz1), (cx0, Hh + rise, cz1), (cx0, Hh + rise, cz0)], (1, 0, 0)),
                            face([(cx1, Hh, cz0), (cx1, Hh, cz1), (cx1, Hh + rise, cz1), (cx1, Hh + rise, cz0)], (-1, 0, 0)),
                            face([(cx0, Hh, cz0), (cx1, Hh, cz0), (cx1, Hh + rise, cz0), (cx0, Hh + rise, cz0)], (0, 0, 1)),
                            face([(cx0, Hh, cz1), (cx1, Hh, cz1), (cx1, Hh + rise, cz1), (cx0, Hh + rise, cz1)], (0, 0, -1))], ceiling)
    ring('messe_caisson', cx0, cx1, cz0, cz1, Hh, [(0, 0.08, 0.05), (0.08, 0.2, 0.02)], cornice)
    rosace('messe_rosace', (8.8, Hh + rise, 3.075), ROSACE, cornice)
    # voussure entre les murs et le plafond ; lambris à panneaux, cimaise et plinthe de bois sombre
    moulures = dict(cornice=(cornice, VOUSSURE), dado=dado)
    wall('messe_ouest', (X0, 0, Z0), (0, 0, 1), (1, 0, 0), Z1 - Z0, Hh, red, [(1.75, 3.95, 3.2, 0)], trim=0.1, **moulures)
    wall('messe_est', (X1, 0, Z0), (0, 0, 1), (-1, 0, 0), Z1 - Z0, Hh, red, **moulures)
    wall('messe_nord', (X0, 0, Z0), (1, 0, 0), (0, 0, 1), X1 - X0, Hh, red, **moulures)
    wall('messe_sud', (X0, 0, Z1), (1, 0, 0), (0, 0, -1), X1 - X0, Hh, red, **moulures)
    doorway('messe_porte', (5, 5.3), 'x', 3, 2.2, 3.2, red, marble, sill=0.02)   # seuil de marbre
    casing('messe_chambranle', 'x', X0, 1, 3, 2.2, 3.2, dark_trim, w=0.1, depth=0.035, cap=True)
    # pilastres d'angle : socle de bois sombre à la hauteur du lambris, fût clair, chapiteau sous la voussure ; ceux
    # de deux murs voisins se rejoignent en équerre dans l'angle (photos à 30 cm au moins)
    for axis, plane, out, lo, hi in [('z', Z0, 1, X0, X1), ('z', Z1, -1, X0, X1), ('x', X0, 1, Z0, Z1), ('x', X1, -1, Z0, Z1)]:
        for corner, a0, a1, grow in (('debut', lo, lo + 0.3, (1, 0)), ('fin', hi - 0.3, hi, (0, 1))):
            wide = lambda e: (a0 - e * grow[1], a1 + e * grow[0])   # plus large du seul côté libre
            on_wall('messe_pilastre', axis, plane, out, *wide(0.02), 0, 0.08, 0, 0.84, dark_trim, hide=('dos', 'bas', corner))
            on_wall('messe_pilastre', axis, plane, out, a0, a1, 0, 0.06, 0.84, 3.7, cornice, hide=('dos', 'bas', 'haut', corner))
            on_wall('messe_pilastre', axis, plane, out, *wide(0.015), 0, 0.075, 3.7, 3.79, cornice, hide=('dos', 'haut', corner))
            on_wall('messe_pilastre', axis, plane, out, *wide(0.03), 0, 0.09, 3.79, Hh - 0.32, cornice, hide=('dos', 'haut', corner))
    gold = (1, 0.88, 0.7)
    # Son choix (28/11) : une photo au fond, deux au nord, trois au sud (de gauche à droite pour qui les regarde).
    # Accrochées plus haut qu'ailleurs : le bas du plus grand cadre reste au-dessus de la cimaise (0,82 m)
    for name, at, n, size in [('projet_perso_messe_2026_08_Rentr-eScoute-5511-b37d43af', (X1, 1.85, 3.075), (-1, 0, 0), 1.2),
                              ('projet_perso_messe_2026_08_Rentr-eScoute-5489-524fd3bf', (7.3, 1.66, Z0), (0, 0, 1), 0.95),
                              ('projet_perso_messe_2026_08_MesseDeRentr-e-5232-1290e039', (10.4, 1.66, Z0), (0, 0, 1), 0.95),
                              ('projet_perso_messe_2026_08_Rentr-eScoute-5582-ee59a3d6', (10.9, 1.66, Z1), (0, 0, -1), 0.95),
                              ('projet_perso_messe_IMG_8463', (8.8, 1.66, Z1), (0, 0, -1), 0.95),
                              ('projet_perso_messe_2026_08_MesseDeRentr-e-5203-240bbafd', (6.7, 1.66, Z1), (0, 0, -1), 0.95)]:
        hang(name, at, n, size, Hh, 700, gold, room='messe')
    area('messe_ambiance', (8.8, Hh - 0.02, 3.075), (5, 4), 50, gold)

    # --- Échappées en montagne : grande baie, parquet clair, plafond de lames de bois ---
    X0, X1, Z0, Z1, Hh = -5, 5, -14.3, -6.3, 4.6
    floor('montagne_sol', X0, X1, Z0, Z1, 0, light_parquet)
    floor('montagne_plafond', X0, X1, Z0, Z1, Hh, wood_ceiling, up=False)
    nette = (trim, PLINTHE_NETTE)
    wall('montagne_sud', (X0, 0, Z1), (1, 0, 0), (0, 0, -1), X1 - X0, Hh, white, [(3.4, 6.6, 3.4, 0)], plinth=nette, trim=0.1)
    wall('montagne_nord', (X0, 0, Z0), (1, 0, 0), (0, 0, 1), X1 - X0, Hh, white, [(1.5, 8.5, 3.8, 0.45)], plinth=nette)
    wall('montagne_ouest', (X0, 0, Z0), (0, 0, 1), (1, 0, 0), Z1 - Z0, Hh, white, plinth=nette)
    wall('montagne_est', (X1, 0, Z0), (0, 0, 1), (-1, 0, 0), Z1 - Z0, Hh, white, plinth=nette)
    doorway('montagne_porte', (-6.3, -6), 'z', 0, 3.2, 3.4, white, threshold, sill=0.02)
    casing('montagne_chambranle', 'z', Z1, -1, 0, 3.2, 3.4, trim, w=0.1, depth=0.025, profile='moderne')
    # la baie dans un caisson de chêne de 25 cm (côtés, dessus), avec une banquette sous la fenêtre : dalle de chêne
    # sur un socle blanc en retrait (un obstacle)
    for a0, a1 in ((-3.54, -3.5), (3.5, 3.54)):
        on_wall('montagne_baie', 'z', Z0, 1, a0, a1, 0, 0.25, 0.45, 3.8, OAK, hide=('dos', 'bas', 'haut'))
    on_wall('montagne_baie', 'z', Z0, 1, -3.54, 3.54, 0, 0.25, 3.8, 3.84, OAK, hide=('dos', 'haut'))
    on_wall('montagne_banquette', 'z', Z0, 1, -3.6, 3.6, 0, 0.5, 0.4, 0.45, OAK)
    on_wall('montagne_banquette', 'z', Z0, 1, -3.55, 3.55, 0, 0.44, 0, 0.4, white, hide=('dos', 'haut', 'bas'))
    OBSTACLES.append([-3.6, 3.6, Z0, round(Z0 + 0.5, 3)])
    for xm in (-3.5, -1.17, 1.17, 3.5):
        box('meneau', (xm, 2.125, Z0 + 0.03), (0.06, 3.35, 0.08), BLACK)['groupe'] = 'deco_montagne'
    for ym in (0.45, 3.8):
        box('traverse', (0, ym, Z0 + 0.03), (7.06, 0.06, 0.08), BLACK)['groupe'] = 'deco_montagne'
    hang('projet_perso_montagne_Montagne-59', (X0, 1.6, -10.3), (1, 0, 0), 1.7, Hh, 600, room='montagne')
    hang('projet_perso_montagne_Montagne-5', (X1, 1.55, -8.6), (-1, 0, 0), 1.1, Hh, 600, room='montagne')
    hang('projet_perso_montagne_Montagne-18', (X1, 1.55, -12.0), (-1, 0, 0), 1.1, Hh, 600, room='montagne')
    hang('projet_perso_montagne_Montagne-64', (3.3, 1.55, Z1), (0, 0, -1), 1.1, Hh, 600, room='montagne')
    bench((0, 0, -11.0), 'montagne')   # face à la baie, assez loin de l'entrée pour ne pas boucher la vue
    area('montagne_ambiance', (0, Hh - 0.02, -10.3), (8, 6), 140)
    # Par la baie : une de ses photos de montagne, grande et lumineuse, en guise de paysage
    view_mat, nodes, links, bsdf = new_material('vue')
    view_image = nodes.new('ShaderNodeTexImage')
    view_image.image = bpy.data.images.load(photo_file(VIEW_PHOTO), check_existing=True)
    bsdf.inputs['Base Color'].default_value = (0, 0, 0, 1)
    links.new(view_image.outputs['Color'], bsdf.inputs['Emission Color'])
    bsdf.inputs['Emission Strength'].default_value = VIEW_STRENGTH
    vz = Z0 - 7.7
    build('vue_montagne', [[(-12, -5.8, vz), (12, -5.8, vz), (12, 10.2, vz), (-12, 10.2, vz)]], view_mat,
          uvs=[[(0, 0), (1, 0), (1, 1), (0, 1)]])['groupe'] = 'lumineux_vue'
    rails()   # les projecteurs de chaque mur, reliés par un rail au plafond


def sky_and_sun(scene):
    world = bpy.data.worlds.new('ciel')
    try:
        world.use_nodes = True
    except AttributeError:
        pass
    nodes, links = world.node_tree.nodes, world.node_tree.links
    bg = nodes['Background']
    try:
        sky = nodes.new('ShaderNodeTexSky')
        sky.sky_type = 'MULTIPLE_SCATTERING' if 'MULTIPLE_SCATTERING' in {i.identifier for i in sky.bl_rna.properties['sky_type'].enum_items} else 'NISHITA'
        sky.sun_disc = False
        sky.sun_elevation = math.radians(32)
        sky.sun_rotation = math.radians(15)
        links.new(sky.outputs['Color'], bg.inputs['Color'])
        bg.inputs['Strength'].default_value = 0.35
    except Exception as error:
        print('Ciel simple :', error)
        bg.inputs['Color'].default_value = (0.55, 0.7, 0.95, 1)
        bg.inputs['Strength'].default_value = 1.2
    scene.world = world
    # Soleil au sud-est : par la fenêtre haute de La Garde, le rayon traverse la salle en diagonale
    to_sun = V(*TO_SUN)
    sun = bpy.data.lights.new('soleil', 'SUN')
    sun.energy = 60
    sun.color = (1, 0.93, 0.82)
    sun.angle = math.radians(0.8)
    obj = bpy.data.objects.new('soleil', sun)
    obj.rotation_euler = (-B(*to_sun)).to_track_quat('-Z', 'Y').to_euler()
    bpy.context.collection.objects.link(obj)


def camera(name, pos, look, fov):
    cam = bpy.data.cameras.new(name)
    cam.sensor_fit = 'VERTICAL'
    cam.angle_y = math.radians(fov)
    cam.clip_start = 0.05
    obj = bpy.data.objects.new(name, cam)
    obj.location = B(*pos)
    obj.rotation_euler = (B(*look) - B(*pos)).normalized().to_track_quat('-Z', 'Y').to_euler()
    bpy.context.collection.objects.link(obj)
    return obj


VIEWPOINTS = {
    'hall': ((0, 1.6, 5.3), (0, 2.0, -6), 64),
    'couvent': ((-5.75, 1.6, -0.75), (-12.3, 1.9, -4.2), 62),
    'garde': ((5.75, 1.6, -0.75), (12.3, 2.5, -4.4), 66),
    'toulouse': ((-5.75, 1.6, 5.55), (-12.3, 1.8, 1.4), 62),
    'messe': ((5.75, 1.6, 5.55), (12.3, 1.8, 1.4), 62),
    'montagne': ((3.6, 1.6, -6.9), (-5, 1.6, -11.6), 66),
}


# ---------- Cuisson de la lumière et export pour la page 3D ----------
def shelf_pack(sizes, tex, pad=10):
    """Range des rectangles (en mètres) dans une image carrée de `tex` pixels, à la même échelle pour tous.
    Écart de 10 pixels : le lissage (soften, rayon 7) ne mélange pas la lumière de deux faces voisines."""
    order = sorted(range(len(sizes)), key=lambda i: -sizes[i][1])

    def attempt(scale):
        x = y = pad
        shelf, placed = 0, {}
        for i in order:
            w, h = max(2, sizes[i][0] * scale), max(2, sizes[i][1] * scale)
            if x + w + pad > tex:
                x, y, shelf = pad, y + shelf + pad, 0
            if y + h + pad > tex or w + 2 * pad > tex:
                return None
            placed[i] = (x, y, w, h)
            x += w + pad
            shelf = max(shelf, h)
        return placed

    lo, hi, best = 0.5, 20000.0, None
    for _ in range(40):
        mid = (lo + hi) / 2
        got = attempt(mid)
        if got:
            best, lo = got, mid
        else:
            hi = mid
    return [(best[i][0] / tex, best[i][1] / tex, (best[i][0] + best[i][2]) / tex, (best[i][1] + best[i][3]) / tex)
            for i in range(len(sizes))]


def lightmap_uv(obj, density, pad=10):
    """Deuxième jeu de coordonnées (LightMap) : chaque face à plat, sans chevauchement, à densité égale ;
    l'image est assez grande pour la densité voulue plus l'écart `pad` autour de chaque face."""
    me = obj.data
    uv1 = me.uv_layers.get('LightMap') or me.uv_layers.new(name='LightMap')
    sizes = []
    for poly in me.polygons:
        co = [me.vertices[me.loops[li].vertex_index].co for li in poly.loop_indices]
        sizes.append((max((co[1] - co[0]).length, 0.005), max((co[-1] - co[0]).length, 0.005)))
    area = sum(w * h for w, h in sizes)
    side = math.sqrt(area * density ** 2 + len(sizes) * (pad + 2) ** 2) * 1.25
    tex = int(min(2048, max(64, math.ceil(side / 8) * 8)))
    for poly, (u0, v0, u1, v1) in zip(me.polygons, shelf_pack(sizes, tex, pad)):
        corners = [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]
        for k, li in enumerate(poly.loop_indices):
            uv1.data[li].uv = corners[min(k, 3)]
    return tex


def soften(image, sigma=1.5):
    """Lisse le grain du calcul (la lumière varie doucement), sans mélanger les zones vides de l'image."""
    import numpy as np
    w, h = image.size
    px = np.empty(w * h * 4, dtype=np.float32)
    image.pixels.foreach_get(px)
    px = px.reshape(h, w, 4)
    rgb = px[..., :3].copy()
    mask = (rgb.sum(axis=2) > 0).astype(np.float32)
    r = int(math.ceil(3 * sigma))
    weights = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma) ** 2)
    weights /= weights.sum()

    def blur(a):
        for axis in (0, 1):
            pad = [(0, 0)] * a.ndim
            pad[axis] = (r, r)
            padded = np.pad(a, pad, mode='edge')
            out = np.zeros_like(a)
            for k, wk in enumerate(weights):
                out += wk * np.take(padded, range(k, k + a.shape[axis]), axis=axis)
            a = out
        return a

    num, den = blur(rgb * mask[..., None]), blur(mask)[..., None]
    return np.where(den > 1e-4, num / np.maximum(den, 1e-4), rgb)


def save_lightmap(rgb, path):
    """Carte de lumière en PNG 8 bits : valeur / K, codée en sRGB (plus de précision dans les ombres)."""
    import numpy as np
    h, w = rgb.shape[:2]
    v = np.clip(rgb / K, 0.0, 1.0)
    enc = np.where(v <= 0.0031308, v * 12.92, 1.055 * np.power(v, 1 / 2.4) - 0.055)
    out = bpy.data.images.new(os.path.basename(path), w, h, alpha=False, float_buffer=False)
    data = np.ones((h, w, 4), dtype=np.float32)
    data[..., :3] = enc
    out.pixels.foreach_set(data.ravel())
    out.filepath_raw = path
    out.file_format = 'PNG'
    out.save()


def read_png(path):
    """Valeurs d'une image PNG (8 ou 16 bits) entre 0 et 1, telles qu'enregistrées (sans gestion des couleurs)."""
    import struct
    import zlib
    import numpy as np
    data = open(path, 'rb').read()
    pos, idat = 8, b''
    while pos < len(data):
        length, kind = struct.unpack('>I4s', data[pos:pos + 8])
        body = data[pos + 8:pos + 8 + length]
        if kind == b'IHDR':
            w, h, depth, ctype = struct.unpack('>IIBB', body[:10])
        elif kind == b'IDAT':
            idat += body
        pos += 12 + length
    channels = {0: 1, 2: 3, 4: 2, 6: 4}[ctype]
    bpp, raw = channels * depth // 8, zlib.decompress(idat)
    stride = w * bpp
    prev, rows = bytearray(stride), []
    for y in range(h):
        filt = raw[y * (stride + 1)]
        line = bytearray(raw[y * (stride + 1) + 1:(y + 1) * (stride + 1)])
        for i in range(stride):
            a = line[i - bpp] if i >= bpp else 0
            b, c = prev[i], (prev[i - bpp] if i >= bpp else 0)
            if filt == 1:
                line[i] = (line[i] + a) & 255
            elif filt == 2:
                line[i] = (line[i] + b) & 255
            elif filt == 3:
                line[i] = (line[i] + (a + b) // 2) & 255
            elif filt == 4:
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                line[i] = (line[i] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        rows.append(bytes(line))
        prev = line
    values = np.frombuffer(b''.join(rows), dtype='>u2' if depth == 16 else np.uint8).astype(np.float64)
    return values.reshape(h, w, channels) / (65535.0 if depth == 16 else 255.0)


EV = (-12.47393, 12.5260688117)   # étendue de « AgX Log » dans Blender : 25 diaphragmes


def tone_curve(scene, n=97):
    """Courbe de Blender (vue AgX, look « Medium High Contrast ») : n gris, de 2^-12,47 à 2^12,53, tels qu'affichés.
    La page 3D la reprend telle quelle : même contraste, mêmes noirs et mêmes blancs que les rendus."""
    import numpy as np
    evs = np.linspace(EV[0], EV[1], n)
    ramp = bpy.data.images.new('rampe', n, 1, float_buffer=True, alpha=False)
    px = np.ones((1, n, 4), dtype=np.float32)
    px[0, :, :3] = (2.0 ** evs)[:, None]
    ramp.pixels.foreach_set(px.ravel())
    settings = scene.render.image_settings
    before = settings.file_format, settings.color_depth, settings.color_mode
    settings.file_format, settings.color_depth, settings.color_mode = 'PNG', '16', 'RGB'
    path = os.path.join(OUT, 'courbe_agx.png')
    ramp.save_render(path, scene=scene)
    settings.file_format, settings.color_depth, settings.color_mode = before
    shown = read_png(path)[0, :, 0]
    print('Courbe AgX : 0,18 →', round(float(np.interp(math.log2(0.18), evs, shown)), 3), flush=True)
    return {'ev': list(EV), 'valeurs': [round(float(v), 5) for v in shown]}


EXT = '.webp'   # format des textures du site (matieres/)


def export_textures():
    """Textures du site (1024 px) : la couleur avec son relief imprimé (RELIEF), et la rugosité (512 px)."""
    import numpy as np
    os.makedirs(os.path.join(WEB, 'matieres'), exist_ok=True)

    def pixels(path, color):
        image = bpy.data.images.load(path, check_existing=False)
        image.colorspace_settings.name = 'sRGB' if color else 'Non-Color'
        w, h = image.size
        px = np.empty(w * h * 4, dtype=np.float32)
        image.pixels.foreach_get(px)   # image 8 bits : valeurs telles qu'enregistrées
        bpy.data.images.remove(image)
        return px.reshape(h, w, 4)

    def save(px, name, size=1024):
        h, w = px.shape[:2]
        image = bpy.data.images.new(name, w, h, alpha=False)
        image.pixels.foreach_set(px.astype(np.float32).ravel())
        image.scale(size, size)
        image.filepath_raw = os.path.join(WEB, 'matieres', name)
        image.file_format = 'WEBP'   # environ deux fois plus léger que le JPEG, à qualité égale
        try:
            image.save(quality=82)
        except TypeError:
            image.save()
        bpy.data.images.remove(image)

    # Pour un rendu « de jeu » : la page éclaire elle-même le relief (carte de normales) ; la couleur reste donc
    # propre (sans ombres imprimées), seulement assombrie dans les creux (occlusion de Poly Haven, à moitié).
    # Fichiers : <id> (couleur 1024 px, téléphone), <id>_2k (couleur 2048 px, ordinateur), <id>_normale (1024),
    # <id>_hauteur (1024, matières avec « profondeur »), <id>_rugosite (512).
    raised = {m['texture'] for m in MATIERES.values() if m.get('profondeur')}
    for texture in sorted({m['texture'] for m in MATIERES.values() if 'texture' in m}):
        def find(kind):
            return glob.glob(os.path.join(TEX, texture, f'*_{kind}*_2k.jpg'))[0]
        color = pixels(find('diff'), True)
        occlusion = glob.glob(os.path.join(TEX, texture, '*_ao_2k.jpg'))
        if occlusion:
            cavity = 1 - 0.5 * (1 - pixels(occlusion[0], False)[..., 0])
            srgb = color[..., :3]
            linear = np.where(srgb <= 0.04045, srgb / 12.92, ((srgb + 0.055) / 1.055) ** 2.4) * cavity[..., None]
            color[..., :3] = np.where(linear <= 0.0031308, linear * 12.92, 1.055 * np.clip(linear, 0, 1) ** (1 / 2.4) - 0.055)
        save(color, f'{texture}{EXT}')
        save(color, f'{texture}_2k{EXT}', 2048)
        normal = pixels(find('nor_gl'), False)
        save(normal, f'{texture}_normale{EXT}')
        save(pixels(find('rough'), False), f'{texture}_rugosite{EXT}', 512)
        if texture in raised:   # carte des hauteurs, pour le relief vu en bougeant (parallaxe)
            height = height_from_normal(normal[..., :3] * 2 - 1)
            grey = np.ones(height.shape + (4,))
            grey[..., :3] = height[..., None]
            save(grey, f'{texture}_hauteur{EXT}')
        print('Texture', texture, flush=True)
    used = {m['texture'] for m in MATIERES.values() if 'texture' in m}
    for old in glob.glob(os.path.join(WEB, 'matieres', '*.*')):   # textures qui ne servent plus, anciens JPEG
        base, ext = os.path.splitext(os.path.basename(old))
        kind = base.split('_')[-1]
        texture = base[:-len(kind) - 1] if kind in ('rugosite', 'hauteur', 'normale', '2k') else base
        if ext != EXT or texture not in used or (kind == 'hauteur' and texture not in raised):
            os.remove(old)


def height_from_normal(n):
    """Hauteurs (0 à 1) retrouvées à partir d'une carte de normales (convention OpenGL) : on intègre les pentes
    (méthode de Frankot et Chellappa, par transformée de Fourier : la texture se répète, ça tombe bien), sans les
    grandes ondulations (seuls comptent les joints, les creux, les bosses)."""
    import numpy as np
    nz = np.clip(n[..., 2], 0.2, None)
    p, q = -n[..., 0] / nz, -n[..., 1] / nz   # pentes en x (colonnes) et en y (lignes, de bas en haut)
    h, w = p.shape
    wx, wy = np.meshgrid(np.fft.fftfreq(w) * 2 * np.pi, np.fft.fftfreq(h) * 2 * np.pi)
    d = wx ** 2 + wy ** 2
    d[0, 0] = 1
    spectrum = (-1j * wx * np.fft.fft2(p) - 1j * wy * np.fft.fft2(q)) / d
    spectrum *= 1 - np.exp(-d / (2 * (2 * np.pi / 256) ** 2))   # au-delà de 256 px : ondulations, retirées
    spectrum[0, 0] = 0
    z = np.real(np.fft.ifft2(spectrum))
    lo, hi = np.percentile(z, [1, 99.5])
    return np.clip((z - lo) / (hi - lo + 1e-9), 0, 1)


def export_sky(scene):
    """Le ciel vu par les fenêtres sur le site : le ciel nuageux de Poly Haven (CC0), passé par la courbe de Blender,
    en panorama JPEG (affiché tel quel par la page)."""
    sky = bpy.data.images.load(SKY, check_existing=True)
    sky.scale(2048, 1024)
    settings = scene.render.image_settings
    before = settings.file_format, settings.color_depth, settings.color_mode, settings.quality
    settings.file_format, settings.color_mode, settings.quality = 'JPEG', 'RGB', 84
    exposure = scene.view_settings.exposure
    scene.view_settings.exposure = -0.4
    sky.save_render(os.path.join(WEB, 'ciel.jpg'), scene=scene)
    scene.view_settings.exposure = exposure
    settings.file_format, settings.color_depth, settings.color_mode, settings.quality = before
    print('Ciel exporté', flush=True)


def group_of(obj):
    """Groupe d'un objet : les surfaces d'une même salle et d'une même matière sont réunies."""
    if obj.get('groupe'):
        return obj['groupe']
    name = obj.name.split('.')[0]
    if name.startswith(('meneau', 'traverse')):
        return 'deco_montagne'
    room = next((r for r in ('couvent', 'toulouse', 'garde', 'messe', 'montagne') if name.startswith(r)), 'hall')
    material = obj.data.materials[0].name.split('.')[0] if obj.data.materials else 'sans'
    return f'{room}__{material}'


def cuisson(scene):
    os.makedirs(os.path.join(WEB, 'lumiere'), exist_ok=True)
    os.makedirs(os.path.join(WEB, 'matieres'), exist_ok=True)
    for obj in list(bpy.data.objects):
        if obj.get('groupe') == 'air':
            bpy.data.objects.remove(obj, do_unlink=True)
    texts = [o for o in bpy.data.objects if o.type == 'FONT']
    if texts:
        bpy.ops.object.select_all(action='DESELECT')
        for o in texts:
            o.select_set(True)
        bpy.context.view_layer.objects.active = texts[0]
        bpy.ops.object.convert(target='MESH')
    groups = {}
    for obj in [o for o in bpy.data.objects if o.type == 'MESH']:
        groups.setdefault(group_of(obj), []).append(obj)
    joined = {}
    for name, objs in sorted(groups.items()):
        bpy.ops.object.select_all(action='DESELECT')
        for o in objs:
            o.select_set(True)
        bpy.context.view_layer.objects.active = objs[0]
        if len(objs) > 1:
            bpy.ops.object.join()
        obj = bpy.context.view_layer.objects.active
        obj.name = obj.data.name = name
        if name.startswith('luminaires_'):
            obj.visible_shadow = False   # les boîtiers des projecteurs n'arrêtent pas leur propre lumière
        joined[name] = obj
    print(f'{len(joined)} groupes', flush=True)

    lightmaps, total = {}, time.time()
    for name, obj in joined.items():
        if name.startswith(('deco', 'lettres', 'lumineux', 'luminaires')):
            continue
        small = name.startswith('banc_')
        tex = lightmap_uv(obj, 90 if small else 40, pad=12 if small else 16)
        lightmaps[name] = f'lumiere/{name}.png'
        # Cuisson d'une salle seulement (« -- cuisson 128 messe ») : les autres gardent leur lumière déjà calculée
        # (même géométrie, donc même rangement des faces dans leurs images)
        if BAKE_ROOMS and group_room(name) not in BAKE_ROOMS and os.path.exists(os.path.join(WEB, lightmaps[name])):
            continue
        direct = bpy.data.images.new('lm_' + name, tex, tex, float_buffer=True, alpha=False)
        bounced = bpy.data.images.new('lmi_' + name, tex, tex, float_buffer=True, alpha=False)
        bake_nodes = []
        for slot in obj.material_slots:
            slot.material = slot.material.copy()
            node = slot.material.node_tree.nodes.new('ShaderNodeTexImage')
            slot.material.node_tree.nodes.active = node
            bake_nodes.append(node)
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        t = time.time()
        # La lumière directe (projecteurs, soleil) reste nette ; la lumière renvoyée par les murs, bruitée mais
        # douce par nature, est calculée plus longtemps et lissée plus fort : plus de taches
        for image, passes, samples in ((direct, {'DIRECT'}, max(32, SAMPLES // 4)), (bounced, {'INDIRECT'}, SAMPLES)):
            for node in bake_nodes:
                node.image = image
            scene.cycles.samples = samples
            bpy.ops.object.bake(type='DIFFUSE', pass_filter=passes, margin=4, uv_layer='LightMap', use_clear=True)
        rgb = soften(direct, 1.2 if small else 1.6) + soften(bounced, 2.5 if small else 4.0)
        save_lightmap(rgb, os.path.join(WEB, lightmaps[name]))
        for slot in obj.material_slots:
            nodes = slot.material.node_tree.nodes
            nodes.remove(nodes.active)
        print(f'Lumière {name} ({tex} px) : {time.time() - t:.0f} s', flush=True)
    print(f'Cuisson : {time.time() - total:.0f} s', flush=True)

    bpy.ops.object.select_all(action='DESELECT')
    for obj in joined.values():
        obj.select_set(True)
    options = dict(filepath=os.path.join(WEB, 'musee.glb'), export_format='GLB', use_selection=True, export_texcoords=True,
                   export_normals=True, export_materials='EXPORT', export_lights=False, export_cameras=False, export_yup=True)
    try:
        bpy.ops.export_scene.gltf(export_image_format='NONE', **options)
    except TypeError:
        for mat in bpy.data.materials:   # pas d'images dans le fichier 3D : la page les charge elle-même
            if mat.node_tree:
                for node in [n for n in mat.node_tree.nodes if n.type == 'TEX_IMAGE']:
                    mat.node_tree.nodes.remove(node)
        bpy.ops.export_scene.gltf(**options)

    export_textures()   # textures allégées pour le web (1024 px), avec leur relief
    export_sky(scene)

    # version : la page la met au bout de chaque fichier chargé, un navigateur ne mélange pas ancien et nouveau calcul
    plan = {'version': int(time.time()), 'K': K, 'tonalite': tone_curve(scene), 'salles': SALLES, 'accrochages': SLOTS,
            'matieres': MATIERES, 'format_matieres': EXT, 'obstacles': OBSTACLES, 'lumieres': lightmaps,
            'soleil': SUN_BEAM, 'ciel': 'ciel.jpg', 'projecteurs': SPOTS}
    with open(os.path.join(WEB, 'plan.json'), 'w', encoding='utf-8') as f:
        json.dump(plan, f, ensure_ascii=False, indent=1)
    for old in glob.glob(os.path.join(WEB, 'lumiere', '*.png')):   # cartes d'objets qui n'existent plus (anciens cadres)
        if f"lumiere/{os.path.basename(old)}" not in lightmaps.values():
            os.remove(old)
    print('Export terminé', flush=True)
    # les photos posées sur les emplacements (accrochage.json) : sans Blender, en une seconde
    import subprocess
    subprocess.run([sys.executable if 'python' in os.path.basename(sys.executable).lower() else 'python',
                    os.path.join(ROOT, 'scripts', 'accrocher.py')], check=False)


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.view_settings.view_transform = 'AgX'
    try:
        scene.view_settings.look = 'AgX - Medium High Contrast'
    except TypeError:
        pass
    if MODE == 'matieres':
        export_textures()
        export_sky(scene)
        # les réglages des matières (teintes, relief, mélange) passent aussi dans plan.json, sans nouvelle cuisson
        path = os.path.join(WEB, 'plan.json')
        with open(path, encoding='utf-8') as f:
            plan = json.load(f)
        plan.update(matieres=MATIERES, format_matieres=EXT, version=int(time.time()))
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(plan, f, ensure_ascii=False, indent=1)
        return print('plan.json : matières à jour', flush=True)
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = SAMPLES
    scene.cycles.use_adaptive_sampling = True
    scene.cycles.adaptive_threshold = 0.025
    scene.cycles.use_denoising = True
    scene.cycles.max_bounces = 8
    scene.cycles.diffuse_bounces = 4
    scene.cycles.glossy_bounces = 3
    scene.cycles.volume_bounces = 1
    scene.cycles.caustics_reflective = scene.cycles.caustics_refractive = False
    scene.cycles.blur_glossy = 1.0
    scene.render.resolution_x, scene.render.resolution_y = 1280, 720
    scene.render.image_settings.file_format = 'PNG'
    scene.view_settings.view_transform = 'AgX'
    try:
        scene.view_settings.look = 'AgX - Medium High Contrast'
    except TypeError:
        pass
    museum()
    sky_and_sun(scene)
    if MODE == 'cuisson':
        return cuisson(scene)
    if MODE == 'plan':
        path = os.path.join(WEB, 'plan.json')
        with open(path, encoding='utf-8') as f:
            plan = json.load(f)
        plan.update(salles=SALLES, accrochages=SLOTS, matieres=MATIERES, format_matieres=EXT, obstacles=OBSTACLES,
                    projecteurs=SPOTS, soleil=SUN_BEAM, version=int(time.time()))
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(plan, f, ensure_ascii=False, indent=1)
        return print(f'plan.json à jour ({len(SPOTS)} projecteurs)', flush=True)
    for view in VIEWS:
        pos, look, fov = VIEWPOINTS[view]
        scene.camera = camera(view, pos, look, fov)
        scene.render.filepath = os.path.join(OUT, f'{view}.png')
        t = time.time()
        bpy.ops.render.render(write_still=True)
        print(f'Rendu {view} : {time.time() - t:.0f} s', flush=True)


main()
