---
title: "Keycloak local"
description: "Configurer le profil local et les comptes de test."
sidebar:
  order: 2
---

Dans `docker/envs/.envs-mviewerstudio`, configurer les valeurs du realm de test :

```bash
MVIEWERSTUDIO_AUTHLIB_ISSUER=http://localhost/keycloak/realms/mviewer
MVIEWERSTUDIO_AUTHLIB_METADATA_URL=http://keycloak:8080/keycloak/realms/mviewer/.well-known/openid-configuration
MVIEWERSTUDIO_AUTHLIB_CLIENT_ID=mviewerstudio
MVIEWERSTUDIO_AUTHLIB_CLIENT_SECRET=mviewerstudio-local-secret
SECRET_KEY=remplacer-par-un-secret-aleatoire-long
```

Dans `docker/envs/.envs-keycloak`, conserver les paramètres du serveur local,
notamment :

```bash
KC_HOSTNAME=http://localhost/keycloak
KC_BOOTSTRAP_ADMIN_USERNAME=admin
KC_BOOTSTRAP_ADMIN_PASSWORD=admin
```

Démarrer avec le profil :

```bash
docker compose --env-file docker/.env.docker -f docker/docker-compose.yml --profile keycloak up -d --build
```

Le profil sélectionne les services ; les valeurs Authlib restent celles définies
dans le fichier d'environnement. Le realm importé est `mviewer`.
Avec ce profil, Studio et le proxy attendent que la découverte OIDC du realm
réponde en HTTP 200 avant de démarrer. Ce contrôle tient compte du temps
d'initialisation et d'import du Keycloak local.

| Usage | Utilisateur | Mot de passe local |
|---|---|---|
| Studio | `john.doe` | `john` |
| Test | `test` | `test` |
| Administration | `admin` | `admin` |

Dans `docker/envs/.envs-keycloak`, le compte administrateur se configure avec `KC_BOOTSTRAP_ADMIN_USERNAME` et
`KC_BOOTSTRAP_ADMIN_PASSWORD`.
Le serveur fonctionne en mode développement ; ses données résident dans le
conteneur. Sa recréation réimporte le realm et réinitialise les modifications
faites dans la console.
