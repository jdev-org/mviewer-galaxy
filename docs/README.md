# Documentation Mviewer Galaxy

Site statique en français construit avec Astro et Starlight.

## Développement

Prérequis : Node.js 22.22 ou supérieur et npm.
Depuis la racine du dépôt :

```bash
cd docs
npm ci
npm run dev
```

Ouvrir `http://localhost:4321` pour accéder à la page d’accueil. Le bouton
**Getting started** mène au guide `/guides/demarrage/` et à la navigation de
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
le site utilise la racine URL `/`. Pour l'héberger sous un préfixe, configurer
`base` dans `astro.config.mjs` et adapter les liens internes.

## Modifier les pages

- `src/content/docs/index.mdx` : accueil.
- `src/content/docs/guides/` : parcours de démarrage et exploitation.
- `src/content/docs/reference/` : environnement, dépannage et confidentialité.
- `astro.config.mjs` : langue, navigation et titre.
- `src/styles/custom.css` : couleurs.

Chaque page Markdown contient un frontmatter `title`, `description` et
`sidebar.order`. Les rubriques de navigation sont générées à partir des dossiers.
Utiliser des valeurs d'exemple pour les secrets dans la documentation.

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
