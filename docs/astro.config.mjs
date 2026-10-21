import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

export default defineConfig({
  integrations: [
    starlight({
      title: 'Mviewer Galaxy',
      logo: { src: './src/assets/mviewer-logo.svg', alt: 'Logo Mviewer' },
      favicon: '/favicon.svg',
      description: 'Déployer et configurer Mviewer Studio avec Docker et Keycloak.',
      defaultLocale: 'root',
      locales: { root: { label: 'Français', lang: 'fr' } },
      customCss: ['./src/styles/custom.css'],
      sidebar: [
        { label: 'Accueil', slug: '' },
        { label: 'Guides', items: [{ autogenerate: { directory: 'guides' } }] },
        { label: 'Référence', items: [{ autogenerate: { directory: 'reference' } }] },
      ],
    }),
  ],
});
