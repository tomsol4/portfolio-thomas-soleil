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

L’accueil `instants-de-vie/index.html` présente une photographie en plein écran, une introduction courte et les reportages. Le menu se superpose à la couverture avec un fond transparent, puis devient opaque après 50 pixels de défilement ou à l’ouverture du menu mobile. Sans JavaScript, la navigation reste opaque et la photographie remplit l’espace disponible dessous. La couverture s’adapte à l’écran avec un cadrage centré sur les mariés sur téléphone. Chaque reportage apparaît dans un cadre compact avec une seule photographie de couverture et un lien vers son album. Dans `data/albums.json`, `reportage_title` définit le titre affiché au-dessus de la couverture. Les photographies des reportages et le portrait gardent leurs proportions sur téléphone et ordinateur.

La page `instants-de-vie/prestations.html` compare les trois formules mariage, puis présente séparément le baptême et les autres événements. Le baptême est illustré par les deux fichiers du dossier `images/bapteme/`. Les boutons ouvrent le formulaire avec le projet et, pour les mariages, la formule correspondante déjà sélectionnés. Son style dédié est `css/life-services.css`.

La page `instants-de-vie/contact.html` place la photographie `images/mariage/mariage15NB.jpg` à gauche d’un formulaire compact sur ordinateur. À 1000 pixels et moins, le formulaire passe avant la photographie. Les champs et leur traitement restent partagés avec `templates/contact.html` et `js/contact.js` ; la mise en page est définie dans `css/contact.css` sous `.life-contact-page`. Le lien Instagram reste dans le pied de page.

L’accueil Concerts met en scène la photographie de Sinfonia Garonna entre deux rideaux de velours. Le menu est intégré au bandeau supérieur festonné de `templates/theatre-nav.svg` ; il devient sobre et opaque après 50 pixels de défilement ou à l’ouverture du menu mobile. À la première entrée de la session, les rideaux restent fermés jusqu’au clic sur « Lever le rideau » ; leurs plis se rassemblent vers les bords et leur contour se courbe. L’ouverture dure 2,4 secondes ; elle reste rejouable. Son état est conservé dans la session et l’historique pour éviter de fermer à nouveau le rideau au retour d’un album. Les liens « Les reportages » des albums Concerts rejoignent directement `#reportages`. Sur les écrans peu hauts, la scène peut défiler pour conserver une photographie suffisamment grande et entière. La hauteur réelle du menu est mesurée pour respecter l’agrandissement du texte. `js/theatre.js` utilise Web Animations ; la relance attend la fermeture complète avant de rouvrir et reste désactivée pendant la séquence. Les reportages apparaissent au défilement ; une lumière douce suit la souris sur ordinateur. Avec `prefers-reduced-motion`, le clic ouvre les rideaux instantanément. Sans JavaScript, ils restent ouverts et les liens restent accessibles. La présentation visuelle se trouve dans `templates/concerts.html` et `css/concerts.css`. Vérifier ces interactions avec `python -B scripts/test_theatre.py` et `python -B scripts/test_concerts.py`.

L’univers artistique affiche une seule image à la fois, entière, sur la hauteur disponible à l’écran. La couverture du Couvent ouvre le parcours, suivie des autres séries et des photographies individuelles. Les flèches, le clavier et le balayage permettent de naviguer manuellement, sans lecture automatique. Un clic sur une couverture ouvre la série complète ; un clic sur une photographie individuelle l’agrandit dans la visionneuse. Sans JavaScript, le parcours reste accessible par défilement horizontal. Son logo renvoie à l’accueil ; dans une série, il renvoie aux projets personnels. Le lien vers les tirages reste discret dans une barre de navigation fixe. Le champ `presentation: "individual"` distingue les images indépendantes d’une série ; le dossier `vrac` utilise ce mode.

Les albums se découvrent depuis les quatre univers de l’accueil. Les galeries sont accessibles directement à `albums/identifiant.html`. Les tarifs sont propres aux univers Sport, Mariage et Concerts.

Les albums marqués `password_protected: true` dans `data/albums.json` conservent leur couverture publique avec un petit cadenas. Actuellement, seul le concert de Noël du Chœur Unum (`noel`) est concerné. Un clic ouvre une demande de mot de passe ; la page contient la galerie chiffrée, qui est déverrouillée dans le navigateur avant de retrouver sa disposition et sa visionneuse habituelles. Les fichiers photos et leurs liens directs restent publics, conformément au choix de Thomas. Sans JavaScript, cet album reste fermé. Le mot de passe n’est ni envoyé au serveur ni mémorisé dans le navigateur ; une nouvelle ouverture de la page le demande à nouveau.

Les mots de passe restent dans `.tools/album-passwords.json`, ignoré par Git et exclu de GitHub Pages. Pour en changer un : `python scripts/album_access.py noel`, puis `python scripts/build.py`. Un environnement de génération automatisé peut fournir le même dictionnaire JSON via le secret d’environnement `ALBUM_PASSWORDS_JSON`. Une génération sans le secret d’un album protégé échoue au lieu de publier sa galerie sans verrou. Les outils de génération et de contrôle utilisent Node.js, ou celui inclus avec les dépendances Playwright, pour AES-GCM ; aucune dépendance JavaScript n’est ajoutée au site. `check_site.py` vérifie aussi les références à l’intérieur des galeries chiffrées et le nettoyage conserve leurs miniatures. Tester le parcours avec `python -B scripts/test_album_access.py`.

`regards/tirages.html` présente les tirages sur devis avec une seule photographie d’exemple, une courte explication, un formulaire et un lien Instagram. `data/prints.json` définit l’image d’exemple et l’introduction. Aucun catalogue ni sélection de photos à acheter n’est affiché. Le formulaire reste accessible sans JavaScript. Confirmation et paiement se font après échange. Tester ce parcours avec `python scripts/test_prints.py` (envois Formspree simulés).

Les formulaires préremplissent le projet selon le lien utilisé. Les offres mariage préremplissent également la formule. Les prix et les choix de photographies proviennent des contenus existants.

À l’intérieur de la scène Concerts, le plancher en perspective accompagne les rideaux ; l’arche et les points lumineux du bas ont été retirés. La photographie principale reste seule, sans légende, cadre ni lien vers un album. Elle occupe davantage de place sur ordinateur, jusqu’à 1 100 px de large selon la hauteur disponible, et conserve ses proportions. Les deux reportages prennent la forme de billets anciens : papier ivoire, impression bordeaux, double filet, bords découpés et talon perforé. Le billet entier ouvre son album ; aucun lien supplémentaire n’est ajouté. Le portrait de la présentation conserve ses proportions dans un format plus compact. Le formulaire Concerts ne contient pas de champ « Offre mariage », même sans JavaScript.

La visionneuse Concerts calcule la taille utile d’une photo d’après ses proportions et l’espace disponible. Sur ordinateur, elle prévoit au moins deux pixels d’image par pixel d’affichage ; les écrans plus denses peuvent choisir davantage. Sinfonia dispose d’exports WebP dédiés de qualité 95 jusqu’à 3 840 px, et les fichiers sources restent disponibles pour les affichages nécessitant la définition native. Seule une version limitée à 1 600 px de la photo suivante est préchargée, sans préchargement sur les connexions signalées comme très lentes ou économes en données. Les originaux, sélections, ordre et descriptions alternatives des albums sont conservés.

À reprendre dans un deuxième temps à la demande de Thomas : proposer un raffinement du décor en gardant une immersion théâtre et concert ; travailler la page Tarifs ; éventuellement revoir la disposition mobile du formulaire. Les descriptions accessibles des photos ont seulement été expliquées et n’ont pas été réécrites.

Si le visiteur modifie un formulaire pendant l’envoi, les nouvelles valeurs sont conservées et signalées comme non envoyées. Sans modification, le formulaire se réinitialise après confirmation. Les menus mobiles restent sur une seule colonne et défilent dans la hauteur disponible, y compris sur les écrans peu hauts. Une ouverture de rideau interrompue ou un changement de taille d’écran rétablit immédiatement une scène utilisable.

Les albums conservent leur sélection complète et leur ordre de publication. Les galeries utilisent une disposition Masonry : les photos restent entières et se placent dans la colonne la moins remplie, avec deux colonnes sur téléphone et trois sur tablette et ordinateur. `js/masonry.js` utilise leurs dimensions pour réserver la place avant leur chargement et recalcule la disposition au redimensionnement. Sans JavaScript, une grille reste accessible. Les albums rugby indiquent qu’ils présentent une partie du reportage, sans date ni compteur dans leur introduction. La visionneuse choisit une image adaptée à l’écran, sans bouton d’ouverture du fichier source. Les séries personnelles indiquent leur position et le lien pour les ouvrir.

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
