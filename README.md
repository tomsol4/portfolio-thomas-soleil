# Portfolio de Thomas Soleil

Site statique : les pages HTML générées peuvent être servies directement par GitHub Pages. Aucun serveur applicatif ni compilation dans le navigateur.

## Modifier le site

- `data/albums.json` : source unique des albums, de leur ordre, de leurs titres, de leurs couvertures et de la liste **explicite** des photos publiées. Une photo présente dans un dossier n'est jamais publiée automatiquement dans un album.
- `templates/` : contenu des pages Prestations, À propos, Contact et Mentions.
- `scripts/build.py` : structure commune, accueil, pages d'albums, métadonnées, sitemap et optimisation des images.
- `css/style.css` : présentation et responsive.
- `js/` : navigation, visionneuse et formulaire. `config.js` est généré pour les anciennes adresses de galeries.

Après une modification des données ou des templates, régénérer les fichiers HTML :

```powershell
python -m pip install --target .tools/python -r requirements-dev.txt
python scripts/build.py
```

Le script conserve les originaux, génère des variantes WebP et réutilise les fichiers optimisés si la source n'a pas changé. Il s'arrête si une photo sélectionnée manque. Pour ajouter un album, suivre la structure existante dans le JSON : `id`, `title`, `cover`, `date`, `photos`, `category`, `description`, `project`. Les catégories disponibles sont celles du dictionnaire `group_ids` dans le script ; `project` correspond à une option du formulaire.

Les nouvelles URL sont `albums/identifiant.html`. Les anciennes URL `galerie.html?id=identifiant` redirigent côté navigateur ; sans JavaScript, la liste des albums reste disponible. Les albums eux-mêmes et leurs liens de photos fonctionnent sans JavaScript.

## Vérifier

```powershell
python scripts/check_site.py
python scripts/test_browser.py
```

Le second script utilise Chrome installé sur Windows, ou `CHROME_PATH` si défini. Les tests du formulaire interceptent les requêtes et **n'envoient aucun email réel**. Les captures et résultats sont placés dans `test-results/`.

Pour prévisualiser : `python -m http.server 8000 --bind 127.0.0.1`, puis ouvrir `http://127.0.0.1:8000`.

## Avant publication

Les fichiers HTML générés, `albums/`, `images/optimized/`, les icônes, les polices et leurs licences doivent être déployés avec CSS, JS, CNAME, sitemap, robots et la page 404. `_config.yml` exclut les sources et documents internes lors d'une publication via Jekyll/GitHub Pages. Pour un autre mode de déploiement, exclure également `.tools`, `.backups`, `audit-site`, `test-results`, `Microsoft`, `scripts`, `templates` et `data`. Ne pas publier le dossier de travail entier sans ces exclusions.

À compléter avec les informations réelles du propriétaire :

- Statut professionnel, identifiants et coordonnées légalement applicables ; conserver une adresse d'hébergement vérifiée. Le texte actuel ne constitue pas une certification de conformité juridique.
- Durées, quantités, délais de livraison, frais et conditions des prestations. Aucune quantité ni durée n'a été inventée : le devis reste la référence.
- Modalités de conservation et suppression effectives des messages, configuration Formspree, garanties contractuelles relatives aux transferts, protection antispam et service de galerie privée. Le code ne peut pas administrer ces comptes.
- Faire un envoi réel de contrôle depuis le domaine public, puis vérifier la réception et les réponses de Formspree.
- Vérifier HTTPS, cache, redirections du domaine, performances en production et soumettre le sitemap à Search Console.

Les prix de départ existants (portrait 70 €, mariage 600 €) sont conservés. Aucun déploiement n'est effectué par les scripts de génération ou de test. Une sauvegarde du code antérieur existe localement dans `.backups/site-before-improvements.zip`.

## Références utilisées

- [CNIL — Information des personnes](https://www.cnil.fr/fr/conformite-rgpd-information-des-personnes-et-transparence)
- [Service Public — Mentions d'un entrepreneur individuel](https://entreprendre.service-public.gouv.fr/vosdroits/F31228)
- [Formspree — Formulaires AJAX](https://help.formspree.io/articles/building-your-form/submit-forms-with-javascript-ajax/)
- [Formspree — Confidentialité](https://formspree.io/legal/privacy-policy/)

Montserrat est distribué sous SIL Open Font License, fournie dans `fonts/Montserrat-LICENSE.txt`. La police Rosehot et les photographies préexistantes sont conservées ; leurs droits restent ceux du propriétaire.
