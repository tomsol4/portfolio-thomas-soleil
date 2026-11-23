"""Les prix du site, écrits une seule fois dans data/tarifs.json.

Les modèles de pages les reprennent avec des jetons {{PRIX_…}} (par exemple {{PRIX_BAPTEME}}), remplacés à la
génération ; le formulaire de contact et les informations données à Google utilisent les mêmes valeurs.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRICES = {name: value for name, value in json.loads((ROOT / 'data/tarifs.json').read_text(encoding='utf-8')).items()
          if not name.startswith('_')}
for _name, _value in PRICES.items():
    if not isinstance(_value, int) or _value <= 0:
        raise ValueError(f'Prix invalide dans data/tarifs.json : « {_name} » doit être un nombre entier d’euros.')

# Formules de mariage : valeur envoyée par le formulaire, nom affiché, prix.
WEDDING_FORMULAS = [('ceremonie', 'Cérémonie', PRICES['mariage_ceremonie']),
                    ('cocktail', 'Demi-journée', PRICES['mariage_demi_journee']),
                    ('complet', 'Journée', PRICES['mariage_journee'])]
WEDDING_FROM = min(price for _, _, price in WEDDING_FORMULAS)
SESSION_FROM = min(PRICES['seance_couple'], PRICES['seance_famille'])


def euros(amount):
    """1000 → « 1 000 € », avec des espaces insécables : un prix ne se coupe jamais en fin de ligne."""
    return f'{amount:,}'.replace(',', ' ') + ' €'


def price_tokens():
    """Jetons utilisables dans les modèles de pages : {{PRIX_BAPTEME}}, {{PRIX_MARIAGE_A_PARTIR_DE}}…"""
    tokens = {'{{PRIX_' + name.upper() + '}}': euros(value) for name, value in PRICES.items()}
    tokens['{{PRIX_MARIAGE_A_PARTIR_DE}}'] = euros(WEDDING_FROM)
    tokens['{{PRIX_SEANCE_A_PARTIR_DE}}'] = euros(SESSION_FROM)
    return tokens
