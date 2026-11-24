"""Données structurées et adresses publiques partagées par toutes les pages."""
import json
from pathlib import Path

# Adresse du site et du compte Instagram : écrites ici seulement, tout le reste les reprend.
BASE = 'https://www.tsoleil.fr'
INSTAGRAM = 'https://www.instagram.com/tomsol_photo/'


def photo_descriptions(root=Path(__file__).resolve().parents[1]):
    """Descriptions des photos, facultatives : lues aux personnes aveugles, elles aident aussi Google Images.

    Une photo sans description est décrite par le titre de son album (« Titre — photographie 12 »). Les photos des
    albums protégés n'en ont pas : leur description dirait ce que l'album cache.
    """
    return json.loads((root / 'data/photo-descriptions.json').read_text(encoding='utf-8'))


PHOTO_DESCRIPTIONS = photo_descriptions()


def public_url(path):
    """Adresse publique d'une page : les index sont servis à l'adresse de leur dossier."""
    if path == 'index.html':
        return BASE + '/'
    if path.endswith('/index.html'):
        return BASE + '/' + path[:-len('index.html')]
    return BASE + '/' + path


def structured_data(title, description, url, cover, page_type='WebPage', extra=()):
    """Informations lisibles par Google : le photographe, son activité, le site et la page."""
    person_id = BASE + '/#photographer'
    website_id = BASE + '/#website'
    business_id = BASE + '/#business'
    graph = [
        {'@type': 'Person', '@id': person_id, 'name': 'Thomas Soleil',
         'jobTitle': 'Photographe', 'url': BASE + '/',
         'sameAs': [INSTAGRAM],
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
         'sameAs': [INSTAGRAM]},
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
