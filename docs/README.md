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
