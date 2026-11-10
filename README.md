# Portfolio de Thomas Soleil

Site statique de photographie publié sur GitHub Pages (www.tsoleil.fr).

## Organisation

- `templates/`, `data/`, `scripts/` : sources de génération (non publiées, voir `_config.yml`).
- Pages HTML, `css/`, `js/`, `fonts/` : le site publié. Les pages sont générées, ne pas les modifier à la main.
- `images/optimized/` : exports web générés (2560 px de large au maximum). Ce sont les seules photographies publiées.
- Le reste de `images/` (dossiers d'albums, `portrait.jpg`, `favicon1.png`…) contient les **originaux**.
  Ils restent sur l'ordinateur : `.gitignore` les exclut du dépôt, ils ne sont donc ni sur GitHub ni sur le site.
  Pensez à les sauvegarder ailleurs, GitHub n'en garde aucune copie.

## Générer le site

```
python scripts/build.py
python scripts/check_site.py
```

- `data/albums.json` : albums et sélection des photos. `data/photo-descriptions.json` : textes alternatifs.
- `data/legal.json` : coordonnées affichées dans les mentions légales (une valeur vide n'est pas affichée).
- `data/image-manifest.json` : dimensions des originaux, mises à jour par le build. Elles permettent de régénérer
  les pages sur une machine sans les originaux, tant que les exports existent.
- `data/sitemap-dates.json` : date de dernière modification réelle de chaque page pour `sitemap.xml`.
- La largeur maximale publiée se règle avec `MAX_WIDTH` dans `scripts/build.py`.

## Albums protégés par mot de passe

`python scripts/album_access.py ID_ALBUM` enregistre le mot de passe dans `.tools/` (jamais envoyé sur GitHub).
Sans ce mot de passe, le build laisse la page chiffrée existante intacte et l'indique.
Seul le contenu de la page est chiffré : les fichiers d'images restent accessibles à qui connaît leur adresse,
et leurs noms sont visibles tant que le dépôt GitHub est public.
