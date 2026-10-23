"""Shared, factual structured data for generated pages."""
import json
from pathlib import Path

BASE = 'https://www.tsoleil.fr'
PHOTO_DESCRIPTIONS = json.loads((Path(__file__).resolve().parents[1] / 'data/photo-descriptions.json').read_text(encoding='utf-8'))


def structured_data(title, description, url, cover, page_type='WebPage'):
    person_id = BASE + '/#photographer'
    website_id = BASE + '/#website'
    graph = [
        {'@type': 'Person', '@id': person_id, 'name': 'Thomas Soleil',
         'jobTitle': 'Photographe', 'url': BASE + '/',
         'sameAs': ['https://www.instagram.com/tomsol_photo/'],
         'knowsAbout': ['Photographie sportive', 'Photographie de mariage',
                        'Photographie de concert', 'Photographie argentique']},
        {'@type': 'WebSite', '@id': website_id, 'url': BASE + '/',
         'name': 'Thomas Soleil — Photographe', 'inLanguage': 'fr-FR',
         'publisher': {'@id': person_id}},
        {'@type': page_type, '@id': url + '#page', 'url': url,
         'name': title, 'description': description, 'inLanguage': 'fr-FR',
         'isPartOf': {'@id': website_id}, 'author': {'@id': person_id},
         'image': BASE + '/' + cover}
    ]
    payload = json.dumps({'@context': 'https://schema.org', '@graph': graph}, ensure_ascii=False)
    return '<script type="application/ld+json">' + payload.replace('<', '\\u003c') + '</script>'
