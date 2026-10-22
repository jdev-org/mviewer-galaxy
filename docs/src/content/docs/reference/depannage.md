---
title: "Dépannage"
description: "Identifier les erreurs de démarrage, de connexion et de déconnexion."
sidebar:
  order: 2
---

## Consulter les journaux

```bash
docker compose --env-file docker/.env.docker -f docker/docker-compose.yml --profile keycloak ps -a
docker compose --env-file docker/.env.docker -f docker/docker-compose.yml --profile keycloak logs --tail 100 proxy mviewerstudio keycloak
```

## Connexion refusée vers Keycloak

Vérifier la disponibilité du service et la valeur de `MVIEWERSTUDIO_AUTHLIB_METADATA_URL`. Pour le serveur local, elle cible `http://keycloak:8080/keycloak/realms/mviewer/.well-known/openid-configuration`.

Le contrôle de disponibilité attend l'import du realm avant de démarrer Studio avec le profil `keycloak`.

## Invalid redirect uri

Comparer l'URL rejetée dans les journaux Keycloak aux URL autorisées pour le client Studio. Vérifier protocole, nom d'hôte, port et chemin :

- connexion : `http://localhost/mviewerstudio/auth/callback` ;
- retour après déconnexion : `http://localhost/mviewer/`.

Adapter ces adresses au domaine public pour un déploiement distant. Nginx adapte le retour après déconnexion vers `/mviewer/` en conservant le protocole public.

## Erreur 502 sur Studio

Vérifier que Studio est démarré. Une erreur de permission sur `apps/store/register.json` empêche son démarrage. Aligner l'UID/GID du processus sur le propriétaire des dossiers partagés, puis recréer le service.

Voir [Volumes et exploitation](/mviewer-galaxy/guides/exploitation/).

## Erreur 500 après une connexion réussie

Lire la trace Python de Studio. Si elle indique `normalize() argument 2 must be str, not list`, le claim `organization` reçu ne correspond pas au format attendu par l'application. Contrôler les mappers du realm et le format des claims transmis à Studio.

## Accès refusé après connexion

Vérifier les autorisations de l'utilisateur et leur correspondance avec `MVIEWERSTUDIO_AUTHLIB_ALLOWED_GROUPS`.

## Le port configuré ne change pas

`env_file` alimente le conteneur ; `--env-file` alimente les expressions du Compose. Pour utiliser `PROXY_HTTP_PORT` depuis `.envs-proxy`, charger aussi ce fichier dans la commande.

Voir [Adapter à son environnement](/mviewer-galaxy/reference/environnement/).
