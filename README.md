# Portfolio de Thomas Soleil

Site statique servi directement par GitHub Pages. Les fichiers HTML sont générés avec Python ; le navigateur utilise uniquement HTML, CSS et JavaScript.

## Organisation

- `data/albums.json` : albums, titres, couvertures et sélection explicite des photographies. La présence d’une photo dans un dossier ne la publie pas automatiquement.
- `data/photo-descriptions.json` : descriptions accessibles des images principales. Ajouter une entrée par chemin de photographie ; le texte décrit ce qui est réellement visible. Un album peut également définir un objet `photo_alts` pour ses images sélectionnées.
- `templates/` : contenus des pages et des présentations.
- `scripts/build.py` : génération HTML, images optimisées, métadonnées et sitemap.
- `scripts/universes.py` : accueil et quatre univers.
- `css/` : base commune et styles propres à chaque univers. `style.css` sert aux pages générales.
- `css/gallery.css` et `css/contact.css` : styles partagés de la visionneuse, des galeries et des formulaires.
- `js/` : navigation, visionneuse et formulaire.
- `images/` : photographies sources, logo et icônes. `images/optimized/` contient uniquement des fichiers générés.
- `fonts/` : polices locales et leurs licences.

## Pages et navigation

L’accueil conserve sa couverture d’origine sans filtre, sur fond noir, puis donne accès aux quatre univers :

| Univers | Accueil | Tarifs |
| --- | --- | --- |
| Sport | `rugby/index.html` | `rugby/tarifs.html` |
| Mariage et événements | `instants-de-vie/index.html` | `instants-de-vie/prestations.html` |
| Concerts | `concerts/index.html` | `concerts/tarifs.html` |
| Projets personnels | `regards/index.html` | Aucun |

Les présentations Sport, Mariage et Concerts apparaissent dans le défilement de leur accueil, à `#presentation`. Les pages À propos Sport et Mariage restent accessibles aux anciennes adresses. Le portrait est `images/portrait.jpg` ; ses variantes portent une empreinte de son contenu pour actualiser les fichiers remplacés.

La page `instants-de-vie/prestations.html` compare les trois formules mariage, puis présente séparément le baptême et les autres événements. Le baptême est illustré par les deux fichiers du dossier `images/bapteme/`. Les boutons ouvrent le formulaire avec le projet et, pour les mariages, la formule correspondante déjà sélectionnés. Son style dédié est `css/life-services.css`.

L’univers artistique affiche une seule image à la fois, entière, sur la hauteur disponible à l’écran. La couverture du Couvent ouvre le parcours, suivie des autres séries et des photographies individuelles. Les flèches, le clavier et le balayage permettent de naviguer manuellement, sans lecture automatique. Un clic sur une couverture ouvre la série complète ; un clic sur une photographie individuelle l’agrandit dans la visionneuse. Sans JavaScript, le parcours reste accessible par défilement horizontal. Son logo renvoie à l’accueil ; dans une série, il renvoie aux projets personnels. Le lien vers les tirages reste discret dans une barre de navigation fixe. Le champ `presentation: "individual"` distingue les images indépendantes d’une série ; le dossier `vrac` utilise ce mode.

Les albums se découvrent depuis les quatre univers de l’accueil. Les galeries sont accessibles directement à `albums/identifiant.html`. Les tarifs sont propres aux univers Sport, Mariage et Concerts.

`regards/tirages.html` présente les tirages sur devis avec une seule photographie d’exemple, une courte explication, un formulaire et un lien Instagram. `data/prints.json` définit l’image d’exemple et l’introduction. Aucun catalogue ni sélection de photos à acheter n’est affiché. Le formulaire reste accessible sans JavaScript. Confirmation et paiement se font après échange. Tester ce parcours avec `python scripts/test_prints.py` (envois Formspree simulés).

Les formulaires préremplissent le projet selon le lien utilisé. Les offres mariage préremplissent également la formule. Les prix et les choix de photographies proviennent des contenus existants.

Les albums conservent leur sélection complète et leur ordre de publication. Les galeries utilisent une disposition Masonry : les photos restent entières et se placent dans la colonne la moins remplie, avec deux colonnes sur téléphone, trois sur tablette et quatre sur grand écran. `js/masonry.js` utilise leurs dimensions pour réserver la place avant leur chargement et recalcule la disposition au redimensionnement. Sans JavaScript, une grille reste accessible. Les albums rugby indiquent qu’ils présentent une partie du reportage, sans date ni compteur dans leur introduction. La visionneuse choisit une image adaptée à l’écran, sans bouton d’ouverture du fichier source. Les séries personnelles indiquent leur position et le lien pour les ouvrir.

Le clic droit et le glisser-déposer sont bloqués sur les photographies lorsque JavaScript est actif. Les styles limitent aussi le menu d’enregistrement par appui long sur les navigateurs compatibles. La navigation, les gestes de balayage et le zoom restent disponibles. Ces mesures découragent l’enregistrement courant ; les fichiers servis au navigateur et les captures d’écran restent accessibles. Elles ne remplacent pas un contrôle d’accès pour des photographies privées.

Le reportage mariage utilise les 38 fichiers JPEG de remplacement dans `images/mariage/`. Les miniatures sont générées en WebP ; la visionneuse propose aussi le fichier source en pleine définition pour les grands écrans. Les noms des originaux sont conservés, y compris les espaces, qui sont encodés dans les liens. Les fichiers optimisés ont des noms compatibles avec les URL.

Les reportages sport utilisent la sélection nettoyée des JPEG : 45 photos Castres–Montpellier, 57 Castres–Toulon et 95 Espoirs Castres–Bayonne. Les couvertures d’origine sont conservées dans leur version haute définition. Les miniatures restent légères ; la visionneuse dispose de versions WebP de meilleure qualité jusqu’à 2 560 pixels de large et du fichier source en pleine définition.

Sinfonia Garonna utilise les 38 JPEG du dossier `images/concert/concertsinfonia/`, dans l’ordre du reportage précédent. La couverture reste la même photographie (`IMG_8628.jpg`). Comme pour le sport, les vues en grand disposent de variantes WebP jusqu’à 2 560 pixels et d’un accès au fichier source.

Les frais de déplacement sont à la charge du client et précisés dans le devis. Durée, quantité et délai de livraison dépendent de la prestation. Aucun délai de réponse fixe n’est annoncé sans confirmation du propriétaire. Les informations de statut professionnel et les mentions légales restent à compléter avec ses coordonnées réelles avant publication.

## Modifier et générer

Installer les dépendances de développement une première fois :

```powershell
python -m pip install --target .tools/python -r requirements-dev.txt
```

Après modification des données, des templates ou du générateur :

```powershell
python scripts/build.py
```

Le générateur vérifie les photographies sélectionnées et conserve les fichiers sources. Il crée les variantes nécessaires et réutilise les fichiers optimisés existants. Les grandes images proposent leur fichier source ; leur résolution reste limitée à celle de ce fichier. En fin de génération, les anciennes images optimisées devenues inutilisées sont supprimées automatiquement.

Pour ajouter un album, reprendre les champs existants du JSON : `id`, `title`, `cover`, `date`, `photos`, `category`, `description` et `project`. Les catégories correspondent à `group_ids` dans le générateur.

## Vérification et aperçu

```powershell
python scripts/check_site.py
python scripts/test_browser.py
python -m http.server 8000 --bind 127.0.0.1
```

L’aperçu est accessible à `http://127.0.0.1:8000`. Les tests utilisent Chrome installé sur Windows, ou `CHROME_PATH`. Les requêtes du formulaire sont simulées : aucun email réel n’est envoyé. Les captures sont régénérées dans `test-results/`, un dossier temporaire ignoré par Git.

`check_site.py` contrôle les liens et les fichiers référencés. `test_browser.py` parcourt les pages à quatre largeurs d’écran, puis vérifie les menus, les galeries, les contacts propres aux univers et les freins à l’enregistrement des photos. Le rapport `test-results/results.json` indique l’état de la dernière exécution : `running`, `passed` ou `failed`. Un échec remplace l’ancien rapport de réussite pour éviter de le confondre avec le résultat actuel. `test_prints.py` vérifie séparément la page des tirages.

## Publication

Publier les fichiers HTML générés, les dossiers des univers, `albums/`, `images/`, `fonts/`, `css/`, `js/`, `CNAME`, `sitemap.xml`, `robots.txt` et la page 404. `_config.yml` exclut les outils, les sources et les résultats de tests pour GitHub Pages. Appliquer les mêmes exclusions pour un autre hébergement.

`.tools/` contient les dépendances locales ; `.backups/` conserve les sauvegardes antérieures. Ces dossiers sont ignorés et ne font pas partie du site publié. Les scripts ne déploient pas le site.

Les coordonnées, mentions, prestations et réglages du service de formulaire doivent correspondre aux informations réelles du propriétaire. La réception des messages et le domaine se vérifient sur le site publié.

Montserrat et Cormorant Garamond sont fournies sous SIL Open Font License, conservée dans `fonts/Montserrat-LICENSE.txt` et `fonts/CormorantGaramond-LICENSE.txt`. Les titres utilisent Cormorant Garamond en romain et en italique, avec les jeux latin et latin étendu, pour afficher les accents français sans mélanger les polices. Les fichiers WOFF2 sont hébergés localement. Les anciennes polices Rosehot et Bodoni Moda ne sont plus chargées ; elles et les photographies préexistantes conservent leurs droits d’origine.
