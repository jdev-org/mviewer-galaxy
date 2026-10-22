# Documentation Mviewer Galaxy

Site statique en français et en anglais construit avec Astro et Starlight.

## Développement

Prérequis : Node.js 22.22 ou supérieur et npm.
Depuis la racine du dépôt :

```bash
cd docs
npm ci
npm run dev
```

Ouvrir `http://localhost:4321/mviewer-galaxy/` pour accéder à la page d’accueil. Le bouton
**Démarrer** mène au guide `/mviewer-galaxy/guides/demarrage/` et à la navigation de
la documentation. Le site dispose d'une navigation par rubriques,
d'un thème clair/sombre et d'une recherche indexée lors du build.

## Build et aperçu

Depuis `docs/` :

```bash
npm run build
npm run preview
```

Les fichiers statiques sont générés dans `docs/dist/` et peuvent être servis
par un hébergement statique. Le dossier `/docs` est le dossier source du projet ;
le site utilise le préfixe `/mviewer-galaxy/`, défini par `base` dans
`astro.config.mjs`. Les liens internes écrits dans le contenu doivent conserver
ce préfixe, comme `/mviewer-galaxy/guides/demarrage/`.

Le workflow `.github/workflows/docs.yml` publie le site sur
`https://jdev-org.github.io/mviewer-galaxy/` après un push sur `main` modifiant
la documentation, ou après un déclenchement manuel. Dans les paramètres du dépôt,
sélectionner **Pages → Source → GitHub Actions**.

## Modifier les pages

- `src/content/docs/index.mdx` : accueil.
- `src/content/docs/guides/` : parcours de démarrage et exploitation.
- `src/content/docs/guides/authentification/` : guides séparés par technologie ; Keycloak local et distant sont documentés, GeoNode et geOrchestra Gateway sont à venir.
- `src/content/docs/reference/` : environnement, dépannage et confidentialité.
- `astro.config.mjs` : langue, navigation et titre.
- `src/styles/custom.css` : couleurs.

Chaque page Markdown contient un frontmatter `title` et `description`.
La navigation est définie dans `astro.config.mjs` ; les guides Keycloak et les
pages de référence sont générés à partir des dossiers, dans l’ordre de `sidebar.order`.
Utiliser des valeurs d'exemple pour les secrets dans la documentation.

## Traductions

Le français est la langue par défaut à `/mviewer-galaxy/`. La version anglaise
est disponible à `/mviewer-galaxy/en/`. Le sélecteur de langue de Starlight
permet de passer à la traduction de la page courante.

Les pages françaises restent dans `src/content/docs/`. Pour chaque page,
ajouter sa traduction dans `src/content/docs/en/` avec le même chemin relatif
et le même nom de fichier, afin de conserver la correspondance entre langues.
Traduire le contenu, les titres, les descriptions, les textes alternatifs et
les libellés des liens. Les liens internes anglais doivent commencer par
`/mviewer-galaxy/en/`. Conserver les commandes et les noms de variables.

Les libellés de groupes de navigation sont traduits avec `translations.en`
dans `astro.config.mjs`. Starlight traduit ses propres éléments d’interface.
L’illustration d’accueil anglaise est `src/assets/galaxy-map-en.svg`.

Référence : [configuration manuelle de Starlight](https://starlight.astro.build/manual-setup/).

## Charte graphique

- Bleu nuit : `#1F1F40`, pour l'en-tête et les surfaces sombres.
- Turquoise : `#2ED2C5`, pour les boutons et les accents.
- Blanc : `#FFFFFF`, pour les surfaces claires et le symbole du logo.

Le titre d'accueil utilise le bleu nuit en thème clair et un blanc doux en thème
sombre. Les liens de lecture utilisent une variante turquoise plus foncée sur
fond blanc pour préserver leur contraste.
Le logo vectoriel reprend le symbole Mviewer du dépôt et est copié dans
`src/assets/mviewer-logo.svg` et `public/favicon.svg`.
