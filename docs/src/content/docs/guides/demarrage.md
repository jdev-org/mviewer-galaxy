---
title: "Démarrage"
description: "Préparer la configuration et démarrer les services Docker."
sidebar:
  order: 1
---

## Préparer le dépôt

Utiliser Docker avec le plugin Compose. Les dossiers `mviewer/` et `mviewerstudio/` fournissent les applications ; Studio est construit depuis `mviewerstudio/docker/Dockerfile`.

Configurer les fichiers suivants :

| Fichier | Usage |
|---|---|
| `docker/.env.docker` | Port publié et UID/GID |
| `docker/envs/.envs-proxy` | Nom nginx et préfixe Studio |
| `docker/envs/.envs-mviewerstudio` | Authlib, session et chemins applicatifs |
| `docker/envs/.envs-keycloak` | Serveur Keycloak local |

## Choisir son Keycloak

Choisir le [serveur local](/mviewer-galaxy/guides/authentification/keycloak/local/) ou le [serveur distant](/mviewer-galaxy/guides/authentification/keycloak/distant/) avant de démarrer.

## Vérifier la configuration

```bash
docker compose --env-file docker/.env.docker -f docker/docker-compose.yml config --quiet
```

Cette commande vérifie la configuration Compose et les fichiers chargés. La connexion dans le navigateur permet ensuite de vérifier les identifiants et les échanges OIDC.

## Démarrer avec Keycloak local

```bash
docker compose --env-file docker/.env.docker -f docker/docker-compose.yml --profile keycloak up -d --build
```

Studio et le proxy attendent que la découverte OIDC du realm local réponde en HTTP 200.

## Démarrer avec Keycloak distant

```bash
docker compose --env-file docker/.env.docker -f docker/docker-compose.yml up -d --build
```

## Ouvrir les applications

- [Studio](http://localhost/mviewerstudio/)
- [Mviewer](http://localhost/mviewer/)
- [Administration Keycloak locale](http://localhost/keycloak/admin/)

Ces URL correspondent au port HTTP `80`. Pour un autre port, adapter aussi les URL publiques et les redirections autorisées côté Keycloak.
