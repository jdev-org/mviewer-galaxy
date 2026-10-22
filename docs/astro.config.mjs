import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

export default defineConfig({
  site: 'https://jdev-org.github.io',
  base: '/mviewer-galaxy',
  redirects: {
    '/guides/keycloak-local/': '/mviewer-galaxy/guides/authentification/keycloak/local/',
    '/guides/keycloak-distant/': '/mviewer-galaxy/guides/authentification/keycloak/distant/',
  },
  integrations: [
    starlight({
      title: 'Mviewer Galaxy',
      logo: { src: './src/assets/mviewer-logo.svg', alt: 'Logo Mviewer' },
      favicon: '/favicon.svg',
      description: 'Déployer et configurer Mviewer Studio avec Docker et Keycloak.',
      defaultLocale: 'root',
      locales: {
        root: { label: 'Français', lang: 'fr' },
        en: { label: 'English', lang: 'en' },
      },
      customCss: ['./src/styles/custom.css'],
      sidebar: [
        { label: 'Accueil', translations: { en: 'Home' }, slug: '' },
        {
          label: 'Guides',
          items: [
            { slug: 'guides/demarrage' },
            {
              label: 'Authentification',
              translations: { en: 'Authentication' },
              items: [
                {
                  label: 'Keycloak',
                  items: [{ autogenerate: { directory: 'guides/authentification/keycloak' } }],
                },
                { slug: 'guides/authentification/geonode' },
                { slug: 'guides/authentification/georchestra-gateway' },
              ],
            },
            { slug: 'guides/exploitation' },
            { slug: 'guides/https' },
          ],
        },
        { label: 'Référence', translations: { en: 'Reference' }, items: [{ autogenerate: { directory: 'reference' } }] },
      ],
    }),
  ],
});
