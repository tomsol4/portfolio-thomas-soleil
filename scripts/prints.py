"""Page des tirages : une photo d'exemple et un formulaire de demande."""
from pathlib import Path
from html import escape
import json

ROOT = Path(__file__).resolve().parents[1]


def build_prints(albums, picture, write, shell):
    config = json.loads((ROOT / 'data/prints.json').read_text(encoding='utf-8'))
    personal = [a for a in albums if a['category'] in ('Argentique', 'Autres regards')]
    source = config['example_source']
    example_album = next((a for a in personal if source in a['photos']), None)
    if example_album is None:
        raise ValueError(f'La photo d’exemple des tirages doit venir d’un projet personnel publié : {source}')
    image = picture(source, 'Intérieur du couvent en noir et blanc', '../',
                    loading='eager', sizes='(max-width:760px) 80vw, 40vw')
    body = (ROOT / 'templates/prints.html').read_text(encoding='utf-8')
    body = body.replace('{{INTRODUCTION}}', escape(config['introduction']))
    body = body.replace('{{EXAMPLE}}', image)
    write('regards/tirages.html', shell(body, 'Tirages photo | Thomas Soleil',
          'Envie d’un tirage de mes projets personnels ? Contactez-moi pour choisir ensemble la photographie, le format et le papier, sur devis.',
          'regards/tirages.html', 'regards', '../',
          f'images/optimized/og-{example_album["id"]}.jpg', ('contact.js',)))
    return {}
