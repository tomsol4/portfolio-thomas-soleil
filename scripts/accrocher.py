"""Accrochage de la visite en 3D : quelle photo sur quel emplacement. Une seconde, sans Blender ni nouvelle cuisson.

    python scripts/accrocher.py                       → regards/galerie/accrochage.json (lu par la page 3D)
    python scripts/accrocher.py messe_2=68 garde_4=35 → pose les photos n° 68 et 35 de la planche sur ces emplacements
    python scripts/accrocher.py messe_6=vide          → laisse l'emplacement vide
    python scripts/accrocher.py --liste               → emplacements, photos posées et leurs numéros

Les emplacements (mur, taille, projecteur) viennent de la cuisson (regards/galerie/plan.json → accrochages) ;
ses choix sont gardés dans data/galerie-accrochage.json (jamais publié). Les numéros sont ceux de la planche
test-results/galerie-3d/choix-photos/index.html (toutes les photos des projets perso, série par série).
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OPT = ROOT / 'images' / 'optimized'
GALLERY = ROOT / 'regards' / 'galerie'
CHOICES = ROOT / 'data' / 'galerie-accrochage.json'
# Ordre des séries sur la planche (salle, début du nom des exports)
SERIES = [('hall', 'vrac'), ('couvent', 'argentique_argentique_couvent'), ('toulouse', 'argentique_argentique_toulouse'),
          ('garde', 'la_garde'), ('messe', 'messe'), ('montagne', 'montagne')]


def number_key(name):
    digits = ''.join(c if c.isdigit() else ' ' for c in name.split('-')[-1]).split()
    return (int(digits[0]) if digits else 0, name)


def catalogue():
    """Toutes les photos des projets perso, numérotées comme sur la planche : [(numéro, salle, photo)]."""
    photos, number = [], 0
    for room, prefix in SERIES:
        names = sorted((p.name[:-len('-480.webp')] for p in OPT.glob(f'projet_perso_{prefix}*-480.webp')), key=number_key)
        for name in names:
            number += 1
            photos.append((number, room, name))
    return photos


def sizes(photo):
    """Largeurs des exports web d'une photo (images/optimized/<photo>-<largeur>.webp)."""
    found = (p.stem[len(photo) + 1:] for p in OPT.glob(f'{photo}-*.webp'))
    return sorted(int(rest) for rest in found if rest.isdigit())


def main(args):
    plan = json.loads((GALLERY / 'plan.json').read_text(encoding='utf-8'))
    slots = {slot['id']: slot for slot in plan['accrochages']}
    choices = json.loads(CHOICES.read_text(encoding='utf-8')) if CHOICES.is_file() else {}
    numbers = {str(n): photo for n, _, photo in catalogue()}
    if '--liste' in args:
        by_photo = {photo: n for n, _, photo in catalogue()}
        for slot in plan['accrochages']:
            photo = choices.get(slot['id'], slot['photo'])
            print(f"{slot['id']:12s} n° {by_photo.get(photo, '?'):>3}  {photo or 'vide'}")
        return
    for arg in args:
        slot, _, value = arg.partition('=')
        if slot not in slots or not value:
            sys.exit(f'Emplacement inconnu ou photo manquante : {arg} (emplacements : {", ".join(slots)})')
        choices[slot] = None if value == 'vide' else numbers.get(value, value)
    if args:
        CHOICES.write_text(json.dumps(choices, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    hanging = []
    for slot in plan['accrochages']:
        photo = choices.get(slot['id'], slot['photo'])
        if not photo:
            continue
        widths = sizes(photo)
        if not widths:
            sys.exit(f'Photo sans export web : {photo} (lancer d’abord python scripts/build.py)')
        hanging.append({'emplacement': slot['id'], 'photo': photo, 'tailles': widths})
    (GALLERY / 'accrochage.json').write_text(json.dumps(hanging, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(f'Accrochage : {len(hanging)} photos sur {len(slots)} emplacements.')


if __name__ == '__main__':
    main(sys.argv[1:])
