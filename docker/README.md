# Stack Docker mviewer + mviewerstudio

Ce dossier contient plusieurs compositions Docker pour lancer `mviewer`, `mviewerstudio` et, selon le cas, la chaine OIDC complete avec `Keycloak` et `oauth2-proxy`.

## Contenu

- `docker-compose.yml` : composition de base avec `proxy`, `mviewer` et `mviewerstudio`.
- `docker-compose.keycloak.yml` : surcouche qui ajoute `postgres`, `keycloak` et `oauth2-proxy`, et remplace le template nginx par la variante OIDC.
- `docker-compose.gateway.yml` : composition 3 services pour un usage derriere une gateway qui transmet deja les entetes d'authentification.
- `.env.docker` : variables locales de configuration.
- `compose.sh` : wrapper pour `docker compose` avec chargement automatique de `.env.docker`.
- `nginx/templates/default.conf.template` : routage HTTP pour la variante Keycloak.
- `nginx/templates/default.gateway.conf.template` : routage HTTP simple pour la variante gateway.
- `mviewerstudio/templates/config.json.template` : template de `config.json` genere pour mviewerstudio au demarrage.
- `mviewerstudio/render_config.py` : script de rendu du template `config.json`.

## Compositions disponibles

- Base : `proxy`, `mviewer`, `mviewerstudio`
- Keycloak : base + `postgres`, `keycloak`, `oauth2-proxy`
- Gateway : `proxy`, `mviewer`, `mviewerstudio`

## Demarrage

Depuis ce dossier, avec la composition de base :

```bash
./compose.sh up --build
```

Pour la variante Keycloak :

```bash
./compose.sh -f docker-compose.yml -f docker-compose.keycloak.yml up --build
```

Pour la variante gateway :

```bash
./compose.sh -f docker-compose.gateway.yml up --build
```

Si la stack Keycloak a deja tourne et que vous voulez rejouer l'import du realm :

```bash
./compose.sh -f docker-compose.yml -f docker-compose.keycloak.yml down -v
./compose.sh -f docker-compose.yml -f docker-compose.keycloak.yml up --build
```

## URLs par defaut

- mviewerstudio : `http://localhost/mviewerstudio/`
- mviewer : `http://localhost/mviewer/`
- Keycloak : `http://localhost/keycloak/` avec la variante Keycloak uniquement

L'acces racine `http://localhost/` redirige vers `mviewerstudio`.

## Authentification

### Variante Keycloak

Le flux d'authentification est le suivant :

1. nginx protege `/mviewerstudio/` et `/mviewer/` via `auth_request /oauth2/auth`
2. `oauth2-proxy` redirige l'utilisateur vers Keycloak
3. Keycloak authentifie l'utilisateur et retourne vers `/oauth2/callback`
4. `oauth2-proxy` pose sa session, renvoie les entetes utilisateur et transmet aussi l'access token
5. nginx propage ces entetes vers `mviewerstudio` et `mviewer`

Les schemas de login/logout sont documentes dans `../schemas/`.

### Variante gateway

La composition gateway n'embarque ni `Keycloak` ni `oauth2-proxy`.
Elle attend qu'une gateway externe gere l'authentification et transmette les entetes `sec-*` a nginx, qui les propage ensuite vers `mviewerstudio`.

## Configuration OIDC locale

Valeurs par defaut de `.env.docker` :

- `OAUTH2_PROXY_CLIENT_ID=mviewerstudio`
- `OAUTH2_PROXY_CLIENT_SECRET=mviewerstudio-local-secret`
- `OAUTH2_PROXY_COOKIE_SECRET=0123456789abcdef0123456789abcdef`
- `OAUTH2_PROXY_ALLOWED_ROLE=MVIEWER_ACCESS`
- `KEYCLOAK_HOSTNAME=http://localhost/keycloak`
- `OAUTH2_PROXY_OIDC_ISSUER_URL=http://localhost/keycloak/realms/mviewer`
- `OAUTH2_PROXY_LOGIN_URL=http://localhost/keycloak/realms/mviewer/protocol/openid-connect/auth`
- `OAUTH2_PROXY_REDIRECT_URL=http://localhost/oauth2/callback`

Le realm importe par defaut est `mviewer`.

Identifiants Keycloak par defaut :

- administration : `admin` / `admin`
- utilisateur de test : `john.doe` / `john`

Le realm importe egalement le role `MVIEWER_ACCESS`, deja attribue aux utilisateurs de test prevus pour l'acces a `mviewerstudio`.

## Variables utiles

- `PROXY_HTTP_PORT` : port HTTP expose localement par nginx.
- `NGINX_HOST` : nom d'hote public utilise par nginx.
- `MVIEWERSTUDIO_URL_PATH_PREFIX` : prefixe d'URL de `mviewerstudio`.
- `MVIEWERSTUDIO_DEFAULT_ORG` : organisation par defaut si aucune organisation n'est transmise.
- `MVIEWERSTUDIO_AUTH_ALLOWED_ROLES` : roles applicatifs acceptes par `mviewerstudio`.
- `MVIEWER_STORE_PATH` : dossier des configurations de travail dans `apps/`.
- `MVIEWER_PUBLIC_PATH` : dossier des configurations publiees dans `apps/`.

Si vous changez l'hote, le port, ou les URLs publiques, pensez a aligner :

- `KEYCLOAK_HOSTNAME`
- `OAUTH2_PROXY_OIDC_ISSUER_URL`
- `OAUTH2_PROXY_LOGIN_URL`
- `OAUTH2_PROXY_REDIRECT_URL`

et la configuration du client `mviewerstudio` dans le realm Keycloak.

## Volumes et fichiers generes

- `../resources/mviewer/apps` est partage entre `mviewer`, `mviewerstudio` et nginx.
- `mviewerstudio` genere son `config.json` a partir de `mviewerstudio/templates/config.json.template`.
- Le volume Docker `postgres_data` persiste les donnees Keycloak dans la variante OIDC.

## Notes

- Les secrets de `.env.docker` sont adaptes a un usage local uniquement.
- Remplacez `OAUTH2_PROXY_CLIENT_SECRET`, `OAUTH2_PROXY_COOKIE_SECRET` et les mots de passe PostgreSQL/Keycloak avant tout environnement partage.
- Les fichiers `docker-compose.yml` et `docker-compose.gateway.yml` construisent l'image `mviewerstudio` depuis le depot courant, avec le `Dockerfile` du projet principal.
