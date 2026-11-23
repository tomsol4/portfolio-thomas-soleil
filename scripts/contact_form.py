"""Le formulaire de contact de l'accueil et de chaque univers.

Le formulaire lui-même est dans templates/contact-form.html. Chaque page ne règle que ce qui change chez elle :
le titre, la phrase d'accueil, le projet déjà choisi, l'exemple de message, avec ou sans formule de mariage.
"""
from html import escape
from pathlib import Path

from prices import WEDDING_FORMULAS, euros
from site_metadata import INSTAGRAM

ROOT = Path(__file__).resolve().parents[1]

# Types de projet de la liste « Votre projet » (valeur envoyée, nom affiché).
PROJECTS = [('mariage', 'Mariage'), ('evenement', 'Événement'), ('portrait', 'Portrait'), ('sport', 'Sport'),
            ('concert', 'Concert'), ('autre', 'Autre projet ou question')]
LIFE_PROJECTS = [('mariage', 'Mariage'), ('evenement', 'Événement'), ('bapteme', 'Baptême'), ('fiancailles', 'Fiançailles'),
                 ('couple', 'Couple'), ('famille', 'Famille'), ('autre', 'Autre projet ou question')]
INTRO = 'Indiquez la date et le lieu, c’est ce qu’il me faut pour vous répondre.'
MESSAGE_HINT = 'Votre projet, vos questions…'


def project_fields(selected, projects, wedding_formula):
    """La liste des projets, suivie si besoin de celle des formules de mariage (affichée seulement pour un mariage)."""
    options = ''.join(f'<option value="{value}"{" selected" if value == selected else ""}>{label}</option>'
                      for value, label in projects)
    fields = ('<div class="form-group"><label for="project">Votre projet <span>(facultatif)</span></label>'
              f'<select id="project" name="projet"><option value="">Choisir un type de projet</option>{options}</select></div>')
    if wedding_formula:
        formulas = ''.join(f'<option value="{value}">{label} — {euros(price)}</option>' for value, label, price in WEDDING_FORMULAS)
        fields += ('\n<div class="form-group" id="wedding-offer-group"><label for="wedding-offer">Formule <span>(facultatif)</span></label>'
                   f'<select id="wedding-offer" name="offre_mariage"><option value="">À définir ensemble</option>{formulas}</select></div>')
    return fields


def contact_form(prefix='', project='', projects=PROJECTS, wedding_formula=False, project_row=False, message_hint=MESSAGE_HINT):
    """Le formulaire ; `prefix` mène de la page à la racine du site (« ../ » depuis un univers)."""
    fields = project_fields(project, projects, wedding_formula)
    if project_row:
        fields = f'<div class="form-row life-project-row">{fields}</div>'
    form = (ROOT / 'templates/contact-form.html').read_text(encoding='utf-8').rstrip('\n')
    return form.replace('{{CHAMPS_PROJET}}', fields).replace('{{EXEMPLE_MESSAGE}}', escape(message_hint)).replace('{{RACINE}}', prefix)


def contact_aside(intro=INTRO, heading='h2', css='contact-aside'):
    """L'encadré « Pour commencer », à côté du formulaire."""
    return (f'<aside class="{css}"><{heading}>Pour commencer</{heading}><p>{intro}</p>'
            '<p>J’habite entre Toulouse et Castres et je me déplace partout en France.</p>'
            f'<p><a href="{INSTAGRAM}" target="_blank" rel="noopener noreferrer">Instagram<span class="sr-only"> (nouvel onglet)</span></a></p></aside>')


def contact_page(title, side, form, main_class='container', header_class='page-header', eyebrow_class='eyebrow',
                 layout_class='contact-layout'):
    """Page Contact d'un univers : le titre, puis l'encadré (ou une photo) à côté du formulaire."""
    return (f'<main id="contenu" class="{main_class}"><header class="{header_class}"><p class="{eyebrow_class}">Contact</p>'
            f'<h1>{title}</h1></header>\n<div class="{layout_class}">{side}\n{form}</div></main>\n')


def home_contact():
    """Section Contact de l'accueil, sous « À propos »."""
    return ('<section class="portal-contact" id="contact" aria-labelledby="contact-title"><div class="frame">'
            '<header class="page-header"><p class="portal-eyebrow">Contact</p><h2 id="contact-title">Me contacter.</h2></header>\n'
            f'<div class="contact-layout">{contact_aside(heading="h3")}\n{contact_form(wedding_formula=True)}</div></div></section>\n')
