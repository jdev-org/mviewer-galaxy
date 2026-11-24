import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

export default defineConfig({
  site: 'https://jdev-org.github.io',
  base: '/mviewer-galaxy',
  redirects: {
    '/guides/keycloak-local/': '/mviewer-galaxy/guides/authentification/keycloak/local/',
    '/guides/keycloak-distant/': '/mviewer-galaxy/guides/authentification/keycloak/distant/',
    '/reference/environnement/': '/mviewer-galaxy/guides/environnement/',
    '/reference/depannage/': '/mviewer-galaxy/guides/depannage/',
    '/en/reference/environnement/': '/mviewer-galaxy/en/guides/environnement/',
    '/en/reference/depannage/': '/mviewer-galaxy/en/guides/depannage/',
  },
  integrations: [
    starlight({
      title: 'Mviewer Galaxy',
      logo: { src: './src/assets/mviewer-logo.svg', alt: 'Logo Mviewer' },
      favicon: '/favicon.svg',
      description: 'Déployer Mviewer Galaxy avec Docker ou Ansible : Mviewer, Studio et GeoServer.',
      defaultLocale: 'root',
      locales: {
        root: { label: 'Français', lang: 'fr' },
        en: { label: 'English', lang: 'en' },
      },
      customCss: ['./src/styles/custom.css'],
      sidebar: [
        { label: 'Accueil', translations: { en: 'Home' }, slug: '' },
        {
          label: 'Guide',
          translations: { en: 'Guide' },
          items: [
            { slug: 'guides/demarrage' },
            { slug: 'guides/environnement' },
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
            { slug: 'guides/depannage' },
          ],
        },
        {
          label: 'Guide Ansible',
          translations: { en: 'Ansible guide' },
          items: [
            {
              label: 'Installation',
              translations: { en: 'Installation' },
              items: [
                { label: 'Vue d’ensemble', translations: { en: 'Overview' }, slug: 'guides/installation-ansible' },
                ...[
                  ['components', 'Dépendances et versions', 'Dependencies and versions'],
                  ['prerequisites', 'Prérequis', 'Prerequisites'],
                  ['ssh', 'Connexion SSH', 'SSH connection'],
                  ['site', 'Paramètres du site', 'Site settings'],
                  ['database', 'Base PostgreSQL / PostGIS', 'PostgreSQL / PostGIS database'],
                  ['network', 'Accès réseau PostgreSQL', 'PostgreSQL network access'],
                  ['secrets', 'Secrets de Studio', 'Studio secrets'],
                  ['deployment', 'Vérifier et déployer', 'Check and deploy'],
                  ['applications', 'Accéder aux applications', 'Access the applications'],
                  ['cors', 'CORS', 'CORS'],
                  ['operations', 'Données, journaux et services', 'Data, logs and services'],
                  ['updates', 'Mettre à jour Mviewer', 'Update Mviewer'],
                ].map(([section, label, en]) => ({
                  label,
                  translations: { en },
                  link: `/guides/installation-ansible/#install-${section}`,
                })),
              ],
            },
            { slug: 'guides/ansible/environnement' },
            { slug: 'guides/ansible/depannage' },
          ],
        },
        { label: 'Référence', translations: { en: 'Reference' }, items: [{ autogenerate: { directory: 'reference' } }] },
      ],
    }),
  ],
});
