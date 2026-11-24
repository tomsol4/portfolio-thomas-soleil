"""Les albums de data/albums.json, avec la liste complète de leurs photos.

Un album donne ses photos une par une (« photos », dans l'ordre voulu), ou bien tout un dossier : « dossier » prend
toutes les photos rangées directement dans ce dossier, dans l'ordre de leurs noms (« 2 » avant « 10 »), et « sauf »
retire des noms de fichiers de ce dossier. Sans « cover », la couverture est la première photo. Exemple :
    {"id": "concert_ete", "title": "Concert d'été", "category": "Concerts", "description": "…",
     "dossier": "images/concert/ete", "sauf": ["IMG_0012.jpg"]}
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PHOTO_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.webp')


def natural_order(name):
    """Clé de tri des noms de fichiers : « photo-2 » avant « photo-10 »."""
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r'(\d+)', name)]


def folder_photos(folder, root=ROOT):
    """Les photos rangées directement dans `folder`, dans l'ordre de leurs noms.

    Sur un ordinateur sans les originaux, ce sont celles dont data/image-manifest.json se souvient."""
    folder = folder.strip('/')
    path = root / folder
    if path.is_dir():
        names = [item.name for item in path.iterdir() if item.is_file() and item.suffix.lower() in PHOTO_EXTENSIONS]
    else:
        manifest = root / 'data/image-manifest.json'
        known = json.loads(manifest.read_text(encoding='utf-8')) if manifest.is_file() else {}
        names = [src[len(folder) + 1:] for src in known if src.startswith(folder + '/') and '/' not in src[len(folder) + 1:]]
    return [f'{folder}/{name}' for name in sorted(names, key=natural_order)]


def load_albums(root=ROOT):
    """Les albums, chacun avec sa liste « photos » complète et sa couverture."""
    albums = json.loads((root / 'data/albums.json').read_text(encoding='utf-8'))
    for album in albums:
        if 'photos' not in album and album.get('dossier'):
            skipped = set(album.get('sauf', []))
            album['photos'] = [src for src in folder_photos(album['dossier'], root) if src.rsplit('/', 1)[-1] not in skipped]
        album.setdefault('photos', [])
        if album['photos']:
            album.setdefault('cover', album['photos'][0])
    return albums


def page_photos(root=ROOT):
    """Les photos choisies dans data/photos-des-pages.json pour les pages du site."""
    path = root / 'data/photos-des-pages.json'

    def collect(entry):
        if isinstance(entry, str):
            return {entry} if entry.startswith('images/') else set()
        if isinstance(entry, dict):
            return set().union(*(collect(value) for key, value in entry.items() if not key.startswith('_')))
        if isinstance(entry, list):
            return set().union(*(collect(item) for item in entry))
        return set()
    return collect(json.loads(path.read_text(encoding='utf-8'))) if path.is_file() else set()


def public_photos(albums, chosen_for_pages=()):
    """Les photos publiées lisibles : les couvertures, les albums publics et les photos choisies pour les pages.

    Une photo d'album protégé choisie pour une page devient donc publique ; les autres restent chiffrées."""
    return ({album['cover'] for album in albums}
            | {src for album in albums if not album.get('password_protected') for src in album['photos']}
            | set(chosen_for_pages))
