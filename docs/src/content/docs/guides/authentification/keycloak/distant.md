---
title: "Keycloak distant"
description: "Relier Studio à un realm externe et configurer ses retours OIDC."
sidebar:
  order: 3
---

## Préparer le client

Dans le realm distant, configurer un client OpenID Connect pour Studio avec authentification du client et flux d'autorisation par code (Standard Flow). Reporter son identifiant et son secret dans la configuration ci-dessous.

Prévoir les scopes et claims demandés par Studio. Le realm local fourni dans `resources/keycloak/mviewer-realm.json` peut servir de référence pour les mappers.

## Configurer Studio

Dans `docker/envs/.envs-mviewerstudio`, renseigner les valeurs du serveur distant :

```bash
MVIEWERSTUDIO_AUTHLIB_ISSUER=https://sso.example.org/realms/mviewer
MVIEWERSTUDIO_AUTHLIB_METADATA_URL=https://sso.example.org/realms/mviewer/.well-known/openid-configuration
MVIEWERSTUDIO_AUTHLIB_CLIENT_ID=mviewerstudio
MVIEWERSTUDIO_AUTHLIB_CLIENT_SECRET=secret-du-client
SECRET_KEY=remplacer-par-un-secret-aleatoire-long
```

Adapter `MVIEWERSTUDIO_AUTHLIB_METADATA_URL` au serveur distant ; la valeur
locale renseignée dans `.envs-mviewerstudio` cible le service `keycloak:8080`.
Les endpoints du serveur distant doivent être accessibles depuis le navigateur
pour la connexion, et depuis Studio pour les échanges OIDC.

Le client Keycloak doit autoriser le callback
`https://votre-domaine/mviewerstudio/auth/callback`, ou
`http://localhost/mviewerstudio/auth/callback` pour un test local.
Autoriser également le retour après déconnexion vers
`https://votre-domaine/mviewer/` (ou `http://localhost/mviewer/` en local).
Les claims doivent correspondre au contrôle d'accès configuré par
`MVIEWERSTUDIO_AUTHLIB_ALLOWED_GROUPS` (par défaut `MVIEWER_ACCESS`).

Démarrer :

```bash
docker compose --env-file docker/.env.docker -f docker/docker-compose.yml up -d --build
```

## Passer du serveur local au serveur distant

```bash
docker compose --env-file docker/.env.docker -f docker/docker-compose.yml --profile keycloak stop keycloak
```

Modifier les valeurs de Studio puis relancer la commande de démarrage du mode distant. Le profil contrôle les services ; il ne change pas les URL Authlib et n'arrête pas un conteneur déjà actif.

## Publier en HTTPS

Le navigateur doit joindre la page de connexion. Studio doit joindre les endpoints de découverte, de jetons et de clés publiques annoncés par le realm. Les certificats HTTPS doivent être reconnus par l'environnement du conteneur.

Voir le guide [Reverse proxy et HTTPS](/mviewer-galaxy/guides/https/).
