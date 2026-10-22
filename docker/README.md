# Docker : Mviewer et Mviewer Studio

La documentation détaillée se trouve dans le [site Astro Starlight](../docs/README.md).
Pour la consulter en local, depuis la racine du dépôt :

```bash
cd docs
npm ci
npm run dev
```

Ouvrir `http://localhost:4321`.

## Démarrer la stack

Ces commandes s'exécutent depuis la racine du dépôt après configuration de
`docker/.env.docker` et des fichiers de `docker/envs/`.

Avec Keycloak local :

```bash
docker compose --env-file docker/.env.docker -f docker/docker-compose.yml --profile keycloak up -d --build
```

Avec Keycloak distant :

```bash
docker compose --env-file docker/.env.docker -f docker/docker-compose.yml up -d --build
```

## Guides

| Sujet | Source Markdown |
|---|---|
| Démarrage | [Guide](../docs/src/content/docs/guides/demarrage.md) |
| Keycloak local | [Guide](../docs/src/content/docs/guides/authentification/keycloak/local.md) |
| Keycloak distant | [Guide](../docs/src/content/docs/guides/authentification/keycloak/distant.md) |
| Adapter à son environnement | [Référence](../docs/src/content/docs/reference/environnement.md) |
| Volumes et exploitation | [Guide](../docs/src/content/docs/guides/exploitation.md) |
| Reverse proxy et HTTPS | [Guide](../docs/src/content/docs/guides/https.md) |
| Dépannage | [Référence](../docs/src/content/docs/reference/depannage.md) |
| Cookies et confidentialité | [Référence](../docs/src/content/docs/reference/cookies.md) |
