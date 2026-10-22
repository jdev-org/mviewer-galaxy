---
title: "Adapter à son environnement"
description: "Comprendre env_file, --env-file et la configuration de chaque service."
sidebar:
  order: 1
---

Vous pouvez adapter l'installation à votre environnement à partir des variables disponibles dans ces fichiers :

| Fichier | Paramètres |
|---|---|
| `docker/.env.docker` | `PROXY_HTTP_PORT`, `MVIEWERSTUDIO_UID`, `MVIEWERSTUDIO_GID`, `MVIEWER_APPS_PATH`, `MVIEWER_STORE_PATH`, `MVIEWER_PUBLIC_PATH` |
| `docker/envs/.envs-proxy` | `NGINX_HOST`, `MVIEWERSTUDIO_URL_PATH_PREFIX` |
| `docker/envs/.envs-mviewerstudio` | Authlib, session, organisation et chemins applicatifs |
| `docker/envs/.envs-keycloak` | Variables `KC_*` du serveur local |

Conserver le même `MVIEWERSTUDIO_URL_PATH_PREFIX` dans les fichiers du proxy et de Studio.

### Comprendre les deux chargements

`env_file` dans un service fournit des variables au **conteneur**. Par exemple,
nginx reçoit ses paramètres depuis :

```yaml
env_file:
  - ./envs/.envs-proxy
```

L'option `--env-file` fournit des variables à **Docker Compose**, qui les utilise
pour remplacer les expressions `${…}` avant de créer les conteneurs. Par exemple :

```yaml
ports:
  - "${PROXY_HTTP_PORT:-80}:80"
```

`PROXY_HTTP_PORT` définit le port publié sur l'hôte. Le port de nginx dans le
conteneur reste `80` : avec `PROXY_HTTP_PORT=8080`, Studio est accessible sur
`http://localhost:8080/mviewerstudio/`.

Les valeurs par défaut du Compose sont `80` pour le port et `1000:1000` pour
l'UID/GID de Studio. Les variables exportées dans le terminal sont prioritaires
sur celles chargées par `--env-file`.

### Placer le port dans le fichier du proxy

Pour regrouper le port et les paramètres nginx, déplacer `PROXY_HTTP_PORT` de
`docker/.env.docker` vers `docker/envs/.envs-proxy` :

```bash
PROXY_HTTP_PORT=80
NGINX_HOST=localhost
MVIEWERSTUDIO_URL_PATH_PREFIX=mviewerstudio
```

Charger alors ce fichier aussi dans la commande. Depuis la racine du dépôt :

```bash
docker compose --env-file docker/.env.docker --env-file docker/envs/.envs-proxy -f docker/docker-compose.yml --profile keycloak up -d --build
```

Le premier fichier fournit l'UID/GID ; le second fournit le port. En cas de
doublon, le dernier fichier indiqué est prioritaire. Le service `proxy` continue
de charger `.envs-proxy` via son `env_file` pour ses variables internes.

Si l'UID/GID par défaut `1000:1000` convient, le fichier du proxy suffit pour
la commande :

```bash
docker compose --env-file docker/envs/.envs-proxy -f docker/docker-compose.yml --profile keycloak up -d --build
```

Depuis `docker/`, la même commande devient :

```bash
docker compose --env-file envs/.envs-proxy --profile keycloak up -d --build
```

Pour utiliser le Keycloak distant, exécuter la commande choisie sans
`--profile keycloak`, après avoir configuré Studio pour ce serveur.
Conserver les mêmes options `--env-file` pour `config`, `up`, `logs` et `down`.
Les autres exemples de ce guide utilisent la répartition du tableau ci-dessus.

## Paramètres de connexion Studio

Ces trois variables doivent être renseignées et non vides dans les deux modes :

| Variable | Usage |
|---|---|
| `MVIEWERSTUDIO_AUTHLIB_ISSUER` | URL du realm Keycloak |
| `MVIEWERSTUDIO_AUTHLIB_CLIENT_SECRET` | Secret du client OIDC |
| `SECRET_KEY` | Clé de session Studio |

Renseigner ces valeurs dans `docker/envs/.envs-mviewerstudio`. Vérifier la syntaxe Compose
et le chargement du fichier avant de lancer les services :

```bash
docker compose --env-file docker/.env.docker -f docker/docker-compose.yml config --quiet
```

Cette commande vérifie la configuration Compose. Les variables applicatives
sont transmises aux conteneurs ; vérifier ensuite les valeurs requises et le
parcours de connexion pour contrôler les échanges avec Keycloak.

## Variables complémentaires

| Variable | Valeur de référence | Usage |
|---|---|---|
| `PROXY_HTTP_PORT` | `80` | Port HTTP publié sur l'hôte |
| `NGINX_HOST` | `localhost` | Nom de serveur nginx |
| `MVIEWERSTUDIO_UID` / `MVIEWERSTUDIO_GID` | `1000` / `1000` | Identité du processus Studio |
| `DEFAULT_ORG` | `public` | Organisation par défaut |
| `MVIEWERSTUDIO_AUTHLIB_CLIENT_ID` | `mviewerstudio` | Client OIDC |
| `MVIEWERSTUDIO_AUTHLIB_SCOPE` | `openid profile email organization` | Scopes demandés |
| `MVIEWERSTUDIO_AUTHLIB_ALLOWED_GROUPS` | `MVIEWER_ACCESS` | Contrôle d'accès Studio |
| `KC_HOSTNAME` | `http://localhost/keycloak` | URL publique du Keycloak local |
