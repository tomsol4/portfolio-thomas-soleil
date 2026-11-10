"""Données structurées et adresses publiques partagées par toutes les pages."""
import json
from pathlib import Path

BASE = 'https://www.tsoleil.fr'
PHOTO_DESCRIPTIONS = json.loads((Path(__file__).resolve().parents[1] / 'data/photo-descriptions.json').read_text(encoding='utf-8'))


def public_url(path):
    """Adresse publique d'une page : les index sont servis à l'adresse de leur dossier."""
    if path == 'index.html':
        return BASE + '/'
    if path.endswith('/index.html'):
        return BASE + '/' + path[:-len('index.html')]
    return BASE + '/' + path


def structured_data(title, description, url, cover, page_type='WebPage', extra=()):
    person_id = BASE + '/#photographer'
    website_id = BASE + '/#website'
    business_id = BASE + '/#business'
    graph = [
        {'@type': 'Person', '@id': person_id, 'name': 'Thomas Soleil',
         'jobTitle': 'Photographe', 'url': BASE + '/',
         'sameAs': ['https://www.instagram.com/tomsol_photo/'],
         'knowsAbout': ['Photographie sportive', 'Photographie de mariage',
                        'Photographie de concert', 'Photographie argentique']},
        {'@type': 'ProfessionalService', '@id': business_id, 'name': 'Thomas Soleil — Photographe',
         'description': 'Photographe de mariage, de sport et de concert en Occitanie.',
         'url': BASE + '/', 'image': BASE + '/images/optimized/og-home-cover.jpg',
         'founder': {'@id': person_id},
         'address': {'@type': 'PostalAddress', 'addressLocality': 'Toulouse',
                     'addressRegion': 'Occitanie', 'addressCountry': 'FR'},
         'areaServed': [{'@type': 'City', 'name': 'Toulouse'}, {'@type': 'City', 'name': 'Castres'},
                        {'@type': 'AdministrativeArea', 'name': 'Occitanie'}],
         'sameAs': ['https://www.instagram.com/tomsol_photo/']},
        {'@type': 'WebSite', '@id': website_id, 'url': BASE + '/',
         'name': 'Thomas Soleil — Photographe', 'inLanguage': 'fr-FR',
         'publisher': {'@id': person_id}},
        {'@type': page_type, '@id': url + '#page', 'url': url,
         'name': title, 'description': description, 'inLanguage': 'fr-FR',
         'isPartOf': {'@id': website_id}, 'author': {'@id': person_id},
         'about': {'@id': business_id},
         'image': BASE + '/' + cover},
        *extra
    ]
    payload = json.dumps({'@context': 'https://schema.org', '@graph': graph}, ensure_ascii=False)
    return '<script type="application/ld+json">' + payload.replace('<', '\\u003c') + '</script>'


def offers(items, area='Toulouse, Castres et Occitanie'):
    """Prestations à prix affiché, telles qu'elles figurent sur la page."""
    return [{'@type': 'Service', 'name': name, 'serviceType': 'Photographie', 'areaServed': area,
             'provider': {'@id': BASE + '/#business'},
             'offers': {'@type': 'Offer', 'price': str(price), 'priceCurrency': 'EUR'}}
            for name, price in items]
