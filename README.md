# mviewer-galaxy

`mviewer-galaxy` regroupe un environnement d'intégration autour de `mviewer` et `mviewerstudio`, avec plusieurs variantes d'authentification et une base de déploiement Docker.

L'objectif est de fournir un espace autonome pour :

- lancer `mviewer` et `mviewerstudio` ensemble ;
- tester une authentification OIDC avec Keycloak ;
- raccorder la stack à un Keycloak déjà existant ;
- documenter les flux de connexion et de déconnexion ;
- préparer un déploiement derrière un nginx déjà présent sur le serveur.

## Ce que contient le projet

- [docker](./docker/README.md) : compositions Docker, templates nginx, variables d'environnement et guide de lancement.
- `resources/keycloak/mviewer-realm.json` : realm Keycloak d'exemple pour les tests locaux.
- `resources/mviewerstudio/config.json` : configuration générée pour `mviewerstudio`.
- `schemas/` : schémas d'architecture et de flux autour d'`oauth2-proxy`, du login et du logout.

## Variantes disponibles

Le dossier `docker/` fournit plusieurs modes de fonctionnement :

- base : `proxy`, `mviewer`, `mviewerstudio`
- Keycloak local : ajoute `postgres`, `keycloak`, `oauth2-proxy`
- Keycloak externe : conserve la stack applicative et pointe vers un serveur Keycloak existant
- gateway : variante simplifiée pour un environnement où l'authentification est déjà gérée en amont

Le scénario recommandé pour une mise en production est :

- un nginx déjà déployé sur le serveur assure la terminaison TLS ;
- ce nginx relaie vers le service `proxy` de la stack Docker ;
- la stack utilise la variante `keycloak-external` si l'IdP existe déjà.

## Démarrage

Le point d'entrée principal est le guide du dossier Docker :

- [Guide Docker](./docker/README.md)

Exemple courant avec Keycloak déjà existant :

```bash
cd docker
./compose.sh -f docker-compose.yml -f docker-compose.keycloak-external.yml up --build
```

## Authentification

Selon la variante choisie, l'authentification peut être :

- gérée localement par `oauth2-proxy` + Keycloak ;
- déléguée à un Keycloak externe ;
- ou transmise par une gateway amont via des en-têtes HTTP.

Les schémas de référence sont dans :

- [archi_oauth2-proxy_schema_login.md](./schemas/archi_oauth2-proxy_schema_login.md)
- [archi_oauth2-proxy_schema_logout.md](./schemas/archi_oauth2-proxy_schema_logout.md)

## Documentation complémentaire

- [README Docker](./docker/README.md)

Ce README racine présente le périmètre du projet. La documentation opérationnelle détaillée est centralisée dans `docker/README.md`.
