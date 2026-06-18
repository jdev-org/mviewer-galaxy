# Stack Docker mviewer + mviewerstudio

Ce dossier contient plusieurs compositions Docker pour lancer `mviewer`, `mviewerstudio` et, selon le cas, la chaîne OIDC complète avec `Keycloak` et `oauth2-proxy`.

## Contenu

- `docker-compose.yml` : composition de base avec `proxy`, `mviewer` et `mviewerstudio`.
- `docker-compose.keycloak.yml` : surcouche qui ajoute `postgres`, `keycloak` et `oauth2-proxy`, et remplace le template nginx par la variante OIDC.
- `docker-compose.keycloak-external.yml` : surcouche qui ajoute uniquement `oauth2-proxy` pour se connecter à un Keycloak existant.
- `docker-compose.gateway.yml` : composition 3 services pour un usage derrière une gateway qui transmet déjà les en-têtes d'authentification.
- `.env.docker` : variables locales de configuration.
- `compose.sh` : wrapper pour `docker compose` avec chargement automatique de `.env.docker`.
- `nginx/templates/default.conf.template` : routage HTTP pour la variante Keycloak.
- `nginx/templates/default.gateway.conf.template` : routage HTTP simple pour la variante gateway.
- `mviewerstudio/templates/config.json.template` : template de `config.json` généré pour mviewerstudio au démarrage.
- `mviewerstudio/render_config.py` : script de rendu du template `config.json`.

## Compositions disponibles

- Base : `proxy`, `mviewer`, `mviewerstudio`
- Keycloak : base + `postgres`, `keycloak`, `oauth2-proxy`
- Keycloak externe : base + `oauth2-proxy`
- Gateway : `proxy`, `mviewer`, `mviewerstudio`

## Lancer la stack

Depuis ce dossier, avec la composition de base :

```bash
./compose.sh up --build
```

Pour la variante Keycloak :

```bash
./compose.sh -f docker-compose.yml -f docker-compose.keycloak.yml up --build
```

Pour la variante connectée à un Keycloak déjà existant :

```bash
./compose.sh -f docker-compose.yml -f docker-compose.keycloak-external.yml up --build
```

Pour la variante gateway :

```bash
./compose.sh -f docker-compose.gateway.yml up --build
```

Si la stack Keycloak a déjà tourné et que vous voulez rejouer l'import du realm :

```bash
./compose.sh -f docker-compose.yml -f docker-compose.keycloak.yml down -v
./compose.sh -f docker-compose.yml -f docker-compose.keycloak.yml up --build
```

## URLs par défaut

- mviewerstudio : `http://localhost/mviewerstudio/`
- mviewer : `http://localhost/mviewer/`
- Keycloak : `http://localhost/keycloak/` avec la variante Keycloak uniquement

L'accès racine `http://localhost/` redirige vers `mviewerstudio`.

## Authentification

### Variante Keycloak

Le flux d'authentification est le suivant :

1. nginx protège `/mviewerstudio/` et `/mviewer/` via `auth_request /oauth2/auth`
2. `oauth2-proxy` redirige l'utilisateur vers Keycloak
3. Keycloak authentifie l'utilisateur et retourne vers `/oauth2/callback`
4. `oauth2-proxy` pose sa session, renvoie les en-têtes utilisateur et transmet aussi l'access token
5. nginx propage ces en-têtes vers `mviewerstudio` et `mviewer`

Les schémas de login/logout sont documentés dans `../schemas/`.

### Variante gateway

La composition gateway n'embarque ni `Keycloak` ni `oauth2-proxy`.
Elle attend qu'une gateway externe gère l'authentification et transmette les en-têtes `sec-*` à nginx, qui les propage ensuite vers `mviewerstudio`.

## Connecter un Keycloak déjà existant

La variante `docker-compose.keycloak-external.yml` permet de conserver `mviewer`, `mviewerstudio`, nginx et `oauth2-proxy` en local, tout en pointant vers un serveur Keycloak déjà déployé.

Commande :

```bash
./compose.sh -f docker-compose.yml -f docker-compose.keycloak-external.yml up --build
```

Variables à renseigner dans `.env.docker` :

- `OAUTH2_PROXY_CLIENT_ID`
- `OAUTH2_PROXY_CLIENT_SECRET`
- `OAUTH2_PROXY_COOKIE_SECRET`
- `OAUTH2_PROXY_OIDC_ISSUER_URL`
- `OAUTH2_PROXY_LOGIN_URL`
- `OAUTH2_PROXY_REDEEM_URL`
- `OAUTH2_PROXY_OIDC_JWKS_URL`
- `OAUTH2_PROXY_REDIRECT_URL`

Exemple :

```env
OAUTH2_PROXY_CLIENT_ID=mviewerstudio
OAUTH2_PROXY_CLIENT_SECRET=change-me
OAUTH2_PROXY_COOKIE_SECRET=0123456789abcdef0123456789abcdef
OAUTH2_PROXY_OIDC_ISSUER_URL=https://sso.example.org/realms/mviewer
OAUTH2_PROXY_LOGIN_URL=https://sso.example.org/realms/mviewer/protocol/openid-connect/auth
OAUTH2_PROXY_REDEEM_URL=https://sso.example.org/realms/mviewer/protocol/openid-connect/token
OAUTH2_PROXY_OIDC_JWKS_URL=https://sso.example.org/realms/mviewer/protocol/openid-connect/certs
OAUTH2_PROXY_REDIRECT_URL=https://maps.example.org/oauth2/callback
OAUTH2_PROXY_ALLOWED_ROLE=MVIEWER_ACCESS
```

Le client OIDC déclaré dans le Keycloak distant doit autoriser :

- l'URL de redirection `.../oauth2/callback`
- les origines/web origins correspondant à l'URL publique de la stack
- les scopes et claims nécessaires à `oauth2-proxy` et `mviewerstudio`

Scopes attendus :

- `openid` : obligatoire pour le flux OIDC
- `email` : utilisé par `oauth2-proxy`
- `profile` : permet d'exposer `preferred_username`, `given_name`, `family_name`
- `organization` : utilisé ici pour exposer l'organisation de l'utilisateur
- `roles` : recommandé si vous voulez récupérer les rôles directement dans le token, en plus du contrôle d'accès fait par `oauth2-proxy`

Claims attendus côté application :

- `preferred_username` : identifiant utilisateur affiché/utilisé par `mviewerstudio`
- `given_name` : prénom
- `family_name` : nom
- `organization` : organisation de rattachement
- `roles` ou `realm_access.roles` : rôles applicatifs

Claims transmis par `oauth2-proxy` via nginx :

- `X-Auth-Request-User`
- `X-Auth-Request-Preferred-Username`
- `X-Auth-Request-Given-Name`
- `X-Auth-Request-Family-Name`
- `X-Auth-Request-Groups`
- `X-Auth-Request-Access-Token`

Comportement de repli :

- si `preferred_username`, `given_name` ou `family_name` ne sont pas présents dans les en-têtes, `mviewerstudio` les relit dans le token d'accès
- si `roles` n'est pas présent, l'application tente `realm_access.roles`
- si `organization` n'est pas présent comme claim dédié, elle peut être déduite du groupe transmis dans `X-Auth-Request-Groups`

## Configuration OIDC locale

Valeurs par défaut de `.env.docker` :

- `OAUTH2_PROXY_CLIENT_ID=mviewerstudio`
- `OAUTH2_PROXY_CLIENT_SECRET=mviewerstudio-local-secret`
- `OAUTH2_PROXY_COOKIE_SECRET=0123456789abcdef0123456789abcdef`
- `OAUTH2_PROXY_ALLOWED_ROLE=MVIEWER_ACCESS`
- `OAUTH2_PROXY_SCOPE=openid email profile organization`
- `OAUTH2_PROXY_OIDC_GROUPS_CLAIM=organization`
- `KEYCLOAK_HOSTNAME=http://localhost/keycloak`
- `OAUTH2_PROXY_OIDC_ISSUER_URL=http://localhost/keycloak/realms/mviewer`
- `OAUTH2_PROXY_LOGIN_URL=http://localhost/keycloak/realms/mviewer/protocol/openid-connect/auth`
- `OAUTH2_PROXY_REDEEM_URL=http://keycloak:8080/keycloak/realms/mviewer/protocol/openid-connect/token`
- `OAUTH2_PROXY_OIDC_JWKS_URL=http://keycloak:8080/keycloak/realms/mviewer/protocol/openid-connect/certs`
- `OAUTH2_PROXY_REDIRECT_URL=http://localhost/oauth2/callback`

Le realm importé par défaut est `mviewer`.

Identifiants Keycloak par défaut :

- administration : `admin` / `admin`
- utilisateur de test : `john.doe` / `john`

Le realm importe également le rôle `MVIEWER_ACCESS`, déjà attribué aux utilisateurs de test prévus pour l'accès à `mviewerstudio`.

## Variables utiles

- `PROXY_HTTP_PORT` : port HTTP exposé localement par nginx.
- `NGINX_HOST` : nom d'hôte public utilisé par nginx.
- `MVIEWERSTUDIO_URL_PATH_PREFIX` : préfixe d'URL de `mviewerstudio`.
- `MVIEWERSTUDIO_DEFAULT_ORG` : organisation par défaut si aucune organisation n'est transmise.
- `MVIEWERSTUDIO_AUTH_ALLOWED_ROLES` : rôles applicatifs acceptés par `mviewerstudio`.
- `MVIEWER_STORE_PATH` : dossier des configurations de travail dans `apps/`.
- `MVIEWER_PUBLIC_PATH` : dossier des configurations publiées dans `apps/`.

Si vous changez l'hôte, le port, ou les URLs publiques, pensez à aligner :

- `KEYCLOAK_HOSTNAME`
- `OAUTH2_PROXY_OIDC_ISSUER_URL`
- `OAUTH2_PROXY_LOGIN_URL`
- `OAUTH2_PROXY_REDEEM_URL`
- `OAUTH2_PROXY_OIDC_JWKS_URL`
- `OAUTH2_PROXY_REDIRECT_URL`

et la configuration du client `mviewerstudio` dans le realm Keycloak.

## Volumes et fichiers générés

- `../resources/mviewer/apps` est partagé entre `mviewer`, `mviewerstudio` et nginx.
- `mviewerstudio` génère son `config.json` à partir de `mviewerstudio/templates/config.json.template`.
- Le volume Docker `postgres_data` persiste les données Keycloak dans la variante OIDC.

## Notes

- Les secrets de `.env.docker` sont adaptés à un usage local uniquement.
- Remplacez `OAUTH2_PROXY_CLIENT_SECRET`, `OAUTH2_PROXY_COOKIE_SECRET` et les mots de passe PostgreSQL/Keycloak avant tout environnement partage.
- Les fichiers `docker-compose.yml` et `docker-compose.gateway.yml` construisent l'image `mviewerstudio` depuis le depot courant, avec le `Dockerfile` du projet principal.
