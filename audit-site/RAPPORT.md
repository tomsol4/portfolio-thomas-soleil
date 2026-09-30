# Audit du site Thomas Soleil

Date : 29 septembre 2026. Périmètre : version locale du projet.

**Bilan : une identité visuelle cohérente et une structure simple, mais plusieurs défauts de galerie, d'accessibilité et de poids des images doivent être corrigés avant de chercher à attirer davantage de visiteurs.** Le parcours commercial gagnerait aussi à être plus direct et les prestations plus précises.

## Méthode et limites

- Lecture des six pages HTML, de `css/style.css` et des quatre fichiers JavaScript.
- Vérification des chemins locaux `src`/`href` présents dans les pages : aucun fichier absent détecté pour ces liens statiques. Cette vérification ne valide pas les liens externes, les fragments ni la casse sur un hébergement Linux.
- Vérification des 1 221 chemins de photos construits par la configuration des neuf albums.
- Rendu dans Chrome sans interface graphique, servi par HTTP local ; consultation des captures et inspection du DOM.
- Tests dans une fenêtre d'ordinateur et des cadres de navigateur de 320 et 390 pixels. Les cadres permettent de contourner la largeur minimale de 500 pixels rencontrée avec Chrome sans interface. Il ne s'agit pas de tests sur de vrais téléphones ni dans Safari.
- Calcul des contrastes à partir des couleurs CSS.
- Consultation des références officielles W3C, Google Search Central et CNIL.

Les mesures locales ne constituent pas un score Lighthouse ou des Core Web Vitals en production. Le navigateur de recherche n'a pas pu ouvrir le domaine public : cela ne démontre pas que le site est indisponible. HTTPS, cache du serveur, indexation réelle et délivrabilité Formspree restent à vérifier. Aucun formulaire n'a été envoyé. Les fichiers du site n'ont pas été modifiés ; seuls les documents de cet audit ont été ajoutés.

## 1. Corrections prioritaires

### P1 — Des photos annoncées n'existent pas aux chemins générés

Le script fabrique les noms de fichiers de 1 à `count`, alors que plusieurs séries ont des trous dans leur numérotation.

| Album | Chemins configurés | Fichiers absents à ces chemins |
| --- | ---: | ---: |
| Rugby CO MHR | 214 | 12 |
| Mariage | 89 | 23 |
| Argentique | 23 | 0 |
| Rugby CO RCT | 196 | 48 |
| Montagne | 112 | 50 |
| Concert Sinfonia Garonna | 64 | 0 |
| Rugby Castres Bayonne Espoirs | 241 | 0 |
| Concert de Noël | 260 | 54 |
| Autres | 22 | 2 |
| **Total** | **1 221** | **189** |

Cela représente environ 15,5 % des chemins générables. Toutes ces requêtes ne partent pas dès l'ouverture : les lots suivants dépendent du défilement. Le navigateur confirme les erreurs pour `co_mhr-7.webp` et `co_mhr-8.webp` dans le premier lot. `img.onerror` supprime ensuite les éléments, ce qui cache le problème visuellement.

**Correction :** conserver une liste explicite des fichiers de chaque album, idéalement générée depuis les dossiers. Réduire simplement `count` ne corrige pas les trous au milieu d'une série. La liste complète des absences est dans `photos-manquantes.json`.

Références : `js/config.js:14`, `js/gallery.js:58`, `js/gallery.js:80`.

### P1 — La visionneuse ne parcourt pas tout l'album

La navigation utilise uniquement `loadedPhotos`, c'est-à-dire les images déjà chargées par la page. Dans le test CO MHR, 28 images du premier lot étaient disponibles ; passer à la suivante depuis la dernière revenait à `co_mhr-1.webp`, alors que l'album est configuré avec 214 chemins. Le défilement de la page est bloqué lorsque la visionneuse est ouverte.

Le visiteur peut donc croire qu'il a terminé l'album. Si des images se chargent pendant la consultation, le tri de `loadedPhotos` peut également déplacer les positions mémorisées.

**Correction :** baser la navigation sur la liste complète des fichiers valides, charger la photo demandée et précharger ses voisines ; ajouter un compteur et gérer les erreurs de chargement.

Références : `js/gallery.js:74`, `js/gallery.js:96`, `js/gallery.js:114`.

### P1 — Le bouton suivant de la visionneuse sort de l'écran mobile

À 390 pixels, la mesure donne un bord gauche d'environ 397 pixels et un bord droit d'environ 461 pixels pour la flèche suivante. Elle se retrouve entièrement hors écran dans le cas testé. L'image peut prendre 80 vw, auxquels s'ajoutent les deux boutons et les marges internes.

**Correction :** superposer les contrôles à l'image ou réserver explicitement leur largeur, avec des dimensions adaptées aux petits écrans. Vérifier également une navigation tactile. Capture : `verified-galerie-co_mhr-390.png`.

Références : `css/style.css:357`, `css/style.css:361`, `css/style.css:362`.

### P1 — Le portrait et le favicon alourdissent inutilement le site

| Ressource | Poids du fichier |
| --- | ---: |
| `images/portrait.jpg`, utilisé sur l'accueil et À propos | 5 220 391 octets, soit 5,22 Mo |
| `images/portrait.webp`, déjà présent | 94 990 octets, soit environ 95 ko |
| `images/favicon1.png`, référencé sur toutes les pages | 813 290 octets, soit environ 813 ko |
| Image principale de l'accueil en WebP | 20 274 octets, soit environ 20 ko |

Le portrait de l'accueil n'a pas de chargement différé, bien qu'il apparaisse après les albums. Sa récupération est observée pendant le chargement de la page locale. Le WebP existant pèse environ 55 fois moins ; son usage économiserait environ 98 % du poids du fichier, sous réserve de vérifier sa qualité et son cadrage.

**Correction :** utiliser une version adaptée du portrait, ajouter le chargement différé sous la ligne de flottaison, générer de petites icônes aux dimensions requises. La grande image d'accueil est déjà très légère : elle n'est pas la priorité.

Références : `index.html:7`, `index.html:112`, `a-propos.html:34`.

### P1 — Des interactions essentielles ne sont pas accessibles au clavier

- Le menu mobile est un `div` avec un événement de clic : il n'est pas un bouton accessible par tabulation et n'annonce pas son état.
- Les photos ouvrant la visionneuse sont aussi des `div` cliquables.
- La fermeture de la visionneuse est un `span` cliquable.
- Le focus reste sur le document lors de l'ouverture de la visionneuse ; aucun déplacement, confinement ou retour du focus n'est prévu.
- Les flèches sont de vrais boutons, mais leurs symboles devraient être accompagnés de noms accessibles explicites.
- Les trois champs du formulaire ont des textes visuels, mais aucun `label` n'est associé au champ. Le DOM confirme zéro libellé associé pour chaque champ.

**Correction :** boutons natifs, associations `for`/`id`, `aria-expanded` et `aria-controls` pour le menu ; dialogue correctement nommé et gestion du focus pour la visionneuse. Ajouter `autocomplete="name"` et `autocomplete="email"` au formulaire.

Les raccourcis gauche, droite et Échap existent déjà dans la visionneuse : c'est un point positif à conserver.

Références : `index.html:25`, `contact.html:37`, `galerie.html:40`, `js/gallery.js:86`.

## 2. Design et expérience de navigation

### Points forts

- La palette beige, les gris chauds et la typographie donnent une identité cohérente de portfolio photographique.
- La navigation comporte quatre entrées faciles à comprendre et reste identique entre les pages.
- L'accueil propose des familles de reportages distinctes, une présentation personnelle, des arguments pratiques et un appel à prendre contact.
- Le texte À propos raconte une pratique personnelle concrète : rugby, chant, argentique et formation.
- Les tarifs donnent un premier repère et chaque offre propose une prise de contact.

### Améliorations

**Aligner la première image et la promesse.** L'accueil montre une silhouette d'architecture, tandis que le texte annonce un photographe événementiel et sportif. La photo crée une atmosphère, mais une image forte de reportage, de sport ou de mariage illustrerait plus directement le service vendu. Il s'agit d'un choix éditorial, pas d'une erreur technique.

**Rendre l'action suivante visible dès l'accueil.** Le premier écran occupe toute la hauteur et présente surtout le nom et le métier. Ajouter un accès clair aux reportages ou au contact, ainsi que Toulouse/Castres dans le texte visible, aiderait les nouveaux visiteurs à s'orienter.

**Afficher les noms d'albums sans dépendre du survol.** `.album-info` est transparent par défaut et devient visible uniquement sur `:hover`, sans équivalent `:focus-visible` ni variante pour écran tactile. Un téléphone ne dispose pas d'un survol permanent ; le comportement au toucher dépend du navigateur. Les noms devraient rester lisibles sur mobile et apparaître aussi au clavier.

**Alléger la sélection publique.** Plusieurs galeries configurent plus de 200 photos. Une sélection éditoriale resserrée peut mieux présenter le travail aux prospects, avec un accès séparé au reportage complet lorsque cela est utile. Il n'est pas nécessaire de supprimer les archives.

**Réduire l'effet de longueur sur mobile.** Les neuf couvertures au format 3:4 passent sur une seule colonne. La présentation personnelle et le grand bouton de contact arrivent donc très bas. Placer un appel à contact plus tôt et proposer une entrée par prestation réduirait ce parcours.

Références : `index.html:33`, `index.html:111`, `css/style.css:186`, `css/style.css:389`.

## 3. Responsive et lisibilité

Des adaptations existent : grilles d'albums, présentation personnelle, arguments et tarifs passent sur une colonne ; la galerie est créée avec deux colonnes sur petit écran. Cela constitue une bonne base.

Les points à corriger sont les suivants :

- La page Prestations atteint 403 pixels de largeur de contenu dans les cadres de 390 et de 320 pixels. À 320 pixels, le débordement touche aussi les cartes de tarifs. Le grand titre et les contraintes de largeur méritent un traitement spécifique ; `overflow-x: hidden` peut masquer le débordement au lieu de le résoudre. Mentions légales présente également un léger débordement, à 324 pixels pour un cadre de 320 pixels.
- Les titres de galerie restent à `4rem` sur mobile ; les titres longs occupent beaucoup de hauteur avant les photos. Adapter leur taille avec `clamp()` et autoriser les coupures adaptées.
- Le nombre de colonnes est choisi une seule fois à l'ouverture ; aucun recalcul n'existe au redimensionnement ou au changement d'orientation. La disposition peut donc rester celle de la largeur initiale.
- Le menu mobile est déplacé hors écran avec `transform`, sans être retiré du parcours de tabulation lorsqu'il est fermé.
- Le défilement fluide et les animations n'ont pas d'adaptation à `prefers-reduced-motion`.
- Le fond fixe du hero mérite une vérification sur de vrais appareils, notamment Safari iOS ; aucun défaut spécifique à iOS n'a été établi ici.

### Contrastes calculés

| Texte / fond | Contraste approximatif | Observation |
| --- | ---: | --- |
| `#2c2928` sur `#f7f5f0` | 13,25:1 | Très bon pour le texte courant |
| `#7a7673` sur `#f7f5f0` | 4,13:1 | Sous le seuil AA pour du texte courant |
| `#cccccc` sur `#f7f5f0` | 1,47:1 | Très insuffisant pour le sous-titre des prestations |

Le seuil AA pour le texte courant est de 4,5:1 ; les grands textes ont un seuil différent. Source : [W3C — Contrast Minimum](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html).

Références : `prestations.html:28`, `css/style.css:20`, `css/style.css:264`, `js/gallery.js:33`.

## 4. Fonctionnement et robustesse

**Galerie sans identifiant ou identifiant inconnu.** Les deux cas testés conservent « Chargement… » et une galerie vide. Afficher un message « Album introuvable » avec retour aux albums, ou rediriger de manière maîtrisée. Prévoir également un état utilisable lorsque JavaScript échoue ou est désactivé.

**Chargement des images et stabilité.** Les emplacements de galerie ont initialement un ratio 3:4, puis prennent le ratio réel au chargement. Les photographies de paysage peuvent déplacer le contenu. Déclarer les dimensions ou le ratio réel dans les données de chaque photo limiterait ces mouvements. Leur impact CLS en production n'a pas été mesuré.

**Ordre des images.** `columns[i % columns.length]` commence dans la deuxième colonne puisque `i` débute à 1. L'ordre visuel des premières images diffère donc de la séquence numérique de la visionneuse. Utiliser au minimum `(i - 1) % columns.length`, puis vérifier la cohérence du parcours visuel et de lecture.

**Formulaire.** La structure permet une soumission HTML directe vers Formspree. Aucun retour personnalisé de succès ou d'erreur n'est géré par le code du site ; le comportement final dépend de Formspree et de sa configuration. Vérifier la réception d'un message avec un test autorisé, les limitations éventuelles du compte, la protection antispam et l'expérience après soumission. Ajouter une adresse électronique cliquable sur Contact comme solution de repli.

Références : `js/gallery.js:12`, `js/gallery.js:61`, `css/style.css:284`, `contact.html:36`.

## 5. Référencement et partage

### Déjà en place

- Langue française, encodage et viewport déclarés sur toutes les pages.
- Titres distincts pour les six pages, descriptions sur les principales pages commerciales.
- Navigation et liens d'albums écrits directement dans le HTML.
- Attributs `alt` présents sur les images statiques et générés sur les photos de galerie.
- Métadonnées Open Graph sur l'accueil, À propos, Contact et Galerie.

### À améliorer

1. **Personnaliser le contenu de chaque album.** Ajouter contexte, événement, lieu, date et quelques descriptions pertinentes. Le titre seul et des alternatives comme « Photo Rugby CO MHR 12 » donnent peu d'informations.
2. **Rendre la suite des albums explorable.** Seul le premier lot de 30 éléments est créé à l'ouverture ; les lots suivants dépendent d'un événement de défilement. Google indique que son exploration n'interagit pas avec la page par défilement ou clic. Prévoir des pages ou liens explorables pour la suite, ou une génération statique adaptée. Cela ne signifie pas que tout JavaScript empêche l'indexation. Source : [Google Search Central — Lazy loading](https://developers.google.com/search/docs/crawling-indexing/javascript/lazy-loading).
3. **Métadonnées propres aux albums.** Le titre du document est changé en JavaScript, mais les descriptions Open Graph, l'image et `og:url` restent génériques. Les partages risquent de tous se ressembler. Des pages d'album générées avec leurs métadonnées initiales seraient plus fiables.
4. **Clarifier les URL de référence.** Aucune balise canonical n'est présente. Définir une politique cohérente pour `/`, `/index.html` et chaque album, sans envoyer tous les albums vers une seule URL générique.
5. **Ajouter un sitemap.** Aucun `sitemap.xml` ni `robots.txt` n'existe dans le projet. Un sitemap faciliterait la découverte des pages et albums. L'absence de `robots.txt` n'interdit pas l'indexation et n'est pas, à elle seule, une panne SEO.
6. **Renforcer le contexte local visible.** Toulouse et Castres sont mentionnés dans certains textes et descriptions, mais pourraient figurer plus clairement sur l'accueil et les prestations concernées.
7. **Compléter le partage de Prestations.** Cette page n'a pas de métadonnées Open Graph.
8. **Nettoyer la hiérarchie des titres.** Mentions légales affiche deux `h1` identiques puis des `h4`. Prestations passe du `h1` aux `h3`. Une structure plus cohérente aiderait surtout la lecture et les technologies d'assistance ; ce n'est pas une pénalité automatique à annoncer.

Références : `galerie.html:11`, `js/gallery.js:17`, `js/gallery.js:147`, `mentions.html:25`, `mentions.html:30`, `prestations.html:34`.

## 6. Présentation commerciale et contenu

**Les offres restent trop imprécises pour comparer et réserver sereinement.** Pour le portrait, préciser au moins la durée, un ordre de grandeur du nombre de photos livrées et le délai de livraison. Pour le mariage, préciser ce que comprend réellement le prix de départ, la durée de couverture, les déplacements et les principales options. L'énumération cérémonie, cocktail, repas et première danse peut faire attendre une couverture complète au tarif minimal.

**Mieux relier promesse, portfolio et prestations.** Les concerts sont présents dans le portfolio et les textes, mais n'ont pas d'offre dédiée. Le portrait a une offre, sans catégorie explicite de portraits sur l'accueil. Le mariage est mis en avant sur les tarifs tandis que le haut de l'accueil annonce surtout événementiel et sport. Choisir une hiérarchie commerciale, puis la refléter sur les trois pages.

**Faciliter les demandes exploitables.** Ajouter quelques champs facultatifs utiles : type de projet, date envisagée, lieu. Faire transmettre le type de prestation depuis les boutons « Réserver » afin d'éviter de recommencer le parcours.

**Renforcer les preuves réelles.** Ajouter, si disponibles et autorisés, des témoignages, le contexte de missions et des exemples de livraisons. Ne pas inventer d'avis ou de références. La page À propos apporte déjà un élément personnel crédible.

**Soigner quelques formulations.** Vérifier « Castres Olympiques », harmoniser « Chœur Unum » avec les titres de configuration, les capitales et les noms d'albums ; remplacer « Autres » par un intitulé plus évocateur si le contenu le permet.

## 7. Données personnelles et sécurité

**Information sur le formulaire incomplète.** La page Mentions indique un usage des données recueillies par email ; le formulaire collecte pourtant nom, email et message via Formspree. Il manque une information adaptée à ce parcours : finalité et base légale retenue, destinataires/prestataires, conservation, exercice des droits et renvoi utile vers la notice complète. La configuration et les conditions du prestataire sont à vérifier. La CNIL propose une information à plusieurs niveaux, dont un premier niveau près du formulaire : [exemples de mentions de collecte](https://www.cnil.fr/fr/exemples-de-formulaire-de-collecte-de-donnees-caractere-personnel).

Les mentions d'identité et d'activité doivent être revues selon le statut professionnel réel ; le code ne permet pas de déterminer les informations administratives applicables. Cet audit n'établit pas une conformité juridique complète.

**Polices externes.** Les pages contactent Google Fonts. Héberger Montserrat localement permettrait de réduire cette dépendance et ces requêtes tierces. Aucun outil de suivi publicitaire ou analytique n'a été repéré dans le code examiné ; cela ne suffit pas à certifier tous les comportements des services externes ni à imposer automatiquement un bandeau cookies.

**Galeries publiques et promesse de galerie privée.** Les galeries de ce dépôt sont accessibles par URL, sans mécanisme d'authentification visible. Une galerie de livraison privée peut être gérée ailleurs, mais il faut vérifier que la promesse commerciale correspond bien au service utilisé. Un identifiant d'album n'est pas un contrôle d'accès.

**Blocage du clic droit.** Le code interdit le menu contextuel et le glisser-déposer des images. Cela ne protège pas les fichiers publics contre le téléchargement et peut gêner la navigation. Préférer une politique claire d'utilisation et, selon les besoins, des versions de consultation adaptées.

La surface technique est limitée par l'architecture statique et l'absence de serveur applicatif dans le dépôt. Les liens Instagram utilisent déjà `rel="noopener"`. La sécurité du compte d'hébergement, du domaine et de Formspree n'a pas été auditée.

Références : `mentions.html:54`, `contact.html:36`, `js/main.js:77`.

## 8. Maintenance

- Architecture légère en HTML/CSS/JavaScript, sans dépendances applicatives volumineuses : adaptée à ce type de site.
- L'accueil contient une liste d'albums écrite manuellement, tandis que `js/config.js` en contient une deuxième. Leur synchronisation devient fragile, comme les noms et comptes de photos l'illustrent.
- `js/home.js` n'est chargé par aucune page et attend un élément `albums-list` absent : ancien code à retirer ou à réintégrer volontairement.
- `config.js` est chargé sur l'accueil sans être consommé par le JavaScript effectivement exécuté sur cette page.
- Navigation et pied de page sont recopiés dans six fichiers : envisager des fragments générés au moment de la construction, en conservant le HTML final statique.
- Plusieurs styles sont intégrés au HTML ; le sous-titre `#ccc` de Prestations semble notamment avoir échappé à l'adaptation au thème clair.
- Certains commentaires évoquent encore un thème noir et une configuration « 100 % WebP », alors que le thème est beige et que des JPG sont utilisés.
- Un dossier `Microsoft/Windows/PowerShell/ModuleAnalysisCache` a été observé dans l'espace de travail. Il n'appartient pas aux ressources du site : vérifier qu'il ne part pas dans un déploiement. Aucun statut Git n'a pu être obtenu avec les outils disponibles.

## Ordre de travail conseillé

| Ordre | Action | Résultat attendu |
| --- | --- | --- |
| 1 | Liste explicite des fichiers et correction de la navigation de visionneuse | Albums complets et parcours fiable |
| 2 | Contrôles de visionneuse sur mobile, menu et formulaire accessibles | Fonctions essentielles utilisables sur petits écrans et au clavier |
| 3 | Portrait, favicon, dimensions et variantes d'images | Réduction immédiate du volume transféré et meilleure stabilité |
| 4 | Contrastes, titres mobiles et noms d'albums visibles | Lecture et orientation facilitées |
| 5 | Erreurs de galerie, retour de formulaire et information sur les données | Parcours plus compréhensible et rassurant |
| 6 | Métadonnées d'albums, découverte des lots suivants et sitemap | Contenu plus facilement explorable et partage plus pertinent |
| 7 | Offres détaillées, sélection photographique et appel à contact plus tôt | Meilleure compréhension de ce qui peut être réservé |
| 8 | Source unique des albums et nettoyage du code | Mises à jour plus fiables |

Après correction : contrôler les neuf albums, parcourir tout un album dans la visionneuse, tester au clavier, vérifier les largeurs 320/390/768/1440 pixels et un appareil iOS/Android réel ; puis mesurer les performances sur l'hébergement public et faire un envoi de formulaire explicitement autorisé.

## Pièces de l'audit

- `mesures.json` : premier passage Chrome. Les champs `width` sont les largeurs réellement obtenues ; `requestedWidth` est seulement la taille demandée. Les captures initiales nommées `*-390.png` hors préfixes `mobile-`/`verified-` ne constituent pas des rendus fiables à 390 pixels.
- `mesures-mobile.json` : contrôles dans des cadres de largeur exacte.
- `photos-manquantes.json` : détail des chemins manquants par album.
- `index-1440.png` : aperçu de l'accueil sur ordinateur.
- `verified-index-390.png`, `verified-prestations-390.png` : aperçus à 390 pixels.
- `verified-galerie-co_mhr-390.png` : visionneuse à 390 pixels. La zone grise à droite appartient au support de capture et non au site.
