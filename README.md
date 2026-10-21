# mviewer-galaxy

Environnement d'intégration de Mviewer et Mviewer Studio, avec authentification
OIDC gérée par Authlib et Keycloak.

## Organisation

- `mviewer/` : sous-module Mviewer.
- `mviewerstudio/` : sous-module Mviewer Studio, utilisé pour construire l'image Docker.
- [docs/](docs/README.md) : site de documentation Astro Starlight.
- [docker/](docker/README.md) : accès rapide à la composition et aux guides.
- `resources/keycloak/mviewer-realm.json` : realm de test importé par le Keycloak local.
- `resources/mviewer/` : dossiers partagés entre Studio, Mviewer et nginx.

## Démarrage

Configurer `docker/.env.docker` et les fichiers de `docker/envs/` selon le
[guide Docker](docker/README.md).
Le guide explique la différence entre `env_file` (variables des conteneurs)
et `--env-file` (paramètres Compose), ainsi que le chargement de `.envs-proxy`
pour configurer le port publié.
Toutes les commandes ci-dessous s'exécutent depuis la racine du dépôt.

Avec un Keycloak externe :

```bash
docker compose --env-file docker/.env.docker -f docker/docker-compose.yml up -d --build
```

Avec le Keycloak local de test :

```bash
docker compose --env-file docker/.env.docker -f docker/docker-compose.yml --profile keycloak up -d --build
```

Le profil `keycloak` ajoute le serveur local. Les URL et identifiants Authlib
se configurent dans `docker/envs/.envs-mviewerstudio` pour le mode choisi.

## Accès

- [Mviewer Studio](http://localhost/mviewerstudio/)
- [Mviewer](http://localhost/mviewer/)
- [Administration Keycloak locale](http://localhost/keycloak/admin/) avec le profil `keycloak`.

Studio utilise le callback `/mviewerstudio/auth/callback`.
Le [guide Docker](docker/README.md) détaille les variables obligatoires,
les comptes locaux, les volumes et l'exploitation.

## Documentation locale

```bash
cd docs
npm ci
npm run dev
```

Ouvrir `http://localhost:4321`. Les guides couvrent le démarrage, Keycloak local
et distant, les variables, les volumes et le dépannage.
