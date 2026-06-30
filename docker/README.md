# Stack Docker mviewer + mviewerstudio

Ce dossier contient plusieurs compositions Docker pour lancer `mviewer`, `mviewerstudio` et, selon le cas, la chaîne OIDC complète avec `Keycloak` et `oauth2-proxy`.

Le scénario recommandé en production est d'utiliser un nginx déjà déployé sur le serveur comme reverse proxy TLS en frontal, et d'exposer le service `proxy` de cette stack uniquement en local.

## Proxy et Reverse Proxy

- `proxy` : c'est le conteneur nginx inclus dans cette stack Docker. Il route les requêtes vers `mviewer`, `mviewerstudio` et, selon la variante, vers `oauth2-proxy`.
- `reverse proxy` : c'est le nginx déjà déployé sur le serveur, placé devant la stack. Il reçoit le trafic public, termine TLS en `https://`, puis relaie vers le service `proxy` en HTTP local.

Schéma recommandé :

```text
Internet
  -> HTTPS
reverse proxy nginx existant
  -> HTTP
service `proxy` de cette stack
  -> mviewerstudio / mviewer / oauth2-proxy
```

## Contenu

- `docker-compose.yml` : composition de base avec `proxy`, `mviewer` et `mviewerstudio`.
- `docker-compose.keycloak.yml` : surcouche qui ajoute `postgres`, `keycloak` et `oauth2-proxy`, et remplace le template nginx par la variante OIDC.
- `docker-compose.keycloak-external.yml` : surcouche qui ajoute uniquement `oauth2-proxy` pour se connecter à un Keycloak existant.
- `docker-compose.gateway.yml` : composition 3 services pour un usage derrière une gateway qui transmet déjà les en-têtes d'authentification.
- `.env.docker` : variables locales de configuration.
- `compose.sh` : wrapper pour `docker compose` avec chargement automatique de `.env.docker`.
- `nginx/templates/default.conf.template` : routage HTTP pour la variante Keycloak.
- `nginx/templates/default.keycloak-external.conf.template` : routage HTTP pour la variante avec Keycloak externe.
- `nginx/templates/default.gateway.conf.template` : routage HTTP simple pour la variante gateway.
- `mviewerstudio/templates/config.json.template` : template de `config.json` généré pour mviewerstudio au démarrage.
- `mviewerstudio/render_config.py` : script de rendu du template `config.json`.

## Compositions disponibles

- Base : `proxy`, `mviewer`, `mviewerstudio`
- Keycloak : base + `postgres`, `keycloak`, `oauth2-proxy`
- Keycloak externe : base + `oauth2-proxy`
- Gateway : `proxy`, `mviewer`, `mviewerstudio`

## Lancer la stack

### Cas recommandé en production : nginx déjà déployé

Schéma cible :

```text
Internet
  -> HTTPS
nginx existant
  -> HTTP
service `proxy` de cette stack
  -> mviewerstudio / mviewer / oauth2-proxy
```

Variables `.env.docker` recommandées :

```env
PROXY_HTTP_PORT=8080
PROXY_HTTP_HOST_IP=127.0.0.1
NGINX_HOST=maps.example.org
OAUTH2_PROXY_COOKIE_SECURE=true
OAUTH2_PROXY_REDIRECT_URL=https://maps.example.org/oauth2/callback
```

Commande :

```bash
./compose.sh -f docker-compose.yml -f docker-compose.keycloak-external.yml up --build
```

Le nginx déjà déployé doit relayer vers `http://127.0.0.1:8080` et transmettre au minimum :

- `Host`
- `X-Forwarded-For`
- `X-Forwarded-Proto https`

## Pour une mise en production

La voie recommandée est :

1. déployer un nginx déjà existant ou géré au niveau du serveur
2. faire terminer TLS sur ce nginx
3. exposer le service `proxy` de cette stack seulement en local
4. lancer la variante `keycloak-external` si le serveur Keycloak est déjà existant

Configuration `.env.docker` minimale :

```env
PROXY_HTTP_PORT=8080
PROXY_HTTP_HOST_IP=127.0.0.1
NGINX_HOST=maps.example.org
OAUTH2_PROXY_COOKIE_SECURE=true
OAUTH2_PROXY_COOKIE_SAMESITE=lax
OAUTH2_PROXY_REDIRECT_URL=https://maps.example.org/oauth2/callback
```

Commande recommandée :

```bash
./compose.sh -f docker-compose.yml -f docker-compose.keycloak-external.yml up --build
```

Points d'attention :

- ne pas exposer directement `PROXY_HTTP_PORT` sur Internet
- configurer le reverse proxy nginx serveur pour relayer vers `http://127.0.0.1:8080`
- transmettre `Host`, `X-Forwarded-For` et `X-Forwarded-Proto https`
- utiliser des secrets réels pour `OAUTH2_PROXY_CLIENT_SECRET` et `OAUTH2_PROXY_COOKIE_SECRET`
- utiliser une URL publique cohérente entre nginx, `OAUTH2_PROXY_REDIRECT_URL` et le client OIDC côté Keycloak

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
- GeoServer : `http://localhost/geoserver/`
- GeoServer admin local : `http://localhost/geoserver-local/`
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
6. `GeoServer` reste accessible derrière nginx sur `/geoserver/`, sans passer par `oauth2-proxy`, afin de laisser `GeoServer` gérer lui-même son authentification

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

Variables recommandées pour la production :

- `OAUTH2_PROXY_COOKIE_SECURE=true`
- `OAUTH2_PROXY_COOKIE_SAMESITE=lax`

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

Pré-requis de mise en production :

- exposer la stack derrière HTTPS
- utiliser une `OAUTH2_PROXY_REDIRECT_URL` en `https://`
- ne pas utiliser le template nginx de la variante Keycloak locale, qui contient une route `/keycloak/` vers un service Docker local
- si vous utilisez déjà un nginx sur le serveur, faites-le pointer vers `http://127.0.0.1:8080` et n'exposez pas directement le port HTTP de la stack sur Internet

## Certificats TLS

### Si vous n'avez pas encore de certificats

Le plus simple en production est d'utiliser Let's Encrypt avec `certbot` sur le VPS qui héberge déjà nginx.

Pré-requis :

- le nom DNS `maps.example.org` doit pointer vers l'adresse IP du VPS
- les ports `80` et `443` doivent être ouverts
- le nginx déjà déployé doit pouvoir répondre au challenge Let's Encrypt, ou être arrêté temporairement si vous utilisez `certbot --standalone`

Installation typique sur Debian/Ubuntu :

```bash
sudo apt update
sudo apt install certbot
```

Émission d'un certificat standalone :

```bash
sudo certbot certonly --standalone -d maps.example.org
```

Alternative si le nginx déjà déployé est déjà configuré sur le domaine :

```bash
sudo certbot --nginx -d maps.example.org
```

Fichiers obtenus en général :

- `/etc/letsencrypt/live/maps.example.org/fullchain.pem`
- `/etc/letsencrypt/live/maps.example.org/privkey.pem`

Ces certificats restent utilisés par le nginx déjà déployé sur le serveur, pas par la stack Docker applicative.

### Renouvellement

Let's Encrypt délivre des certificats à durée limitée. Le renouvellement se fait généralement avec :

```bash
sudo certbot renew
```

Après renouvellement, rechargez le nginx déjà déployé pour qu'il relise les certificats.

## Cookies et RGPD

Cette stack peut déposer au moins des cookies techniques de session liés à l'authentification OIDC, notamment via `oauth2-proxy` et, selon le parcours de déconnexion, des cookies de session Keycloak.

En pratique, pour cette architecture :

- les cookies strictement nécessaires à l'authentification et au maintien de session sont en principe exemptés de recueil du consentement, dès lors qu'ils sont strictement nécessaires au service explicitement demandé par l'utilisateur ;
- ils restent toutefois soumis à une obligation d'information : ils doivent être mentionnés dans votre politique de confidentialité ou votre politique cookies ;
- si vous ajoutez des cookies de mesure d'audience, de personnalisation non essentielle, de publicité, ou des traceurs tiers, il faut réévaluer le besoin d'un bandeau cookies et du recueil du consentement ;
- certains cookies de mesure d'audience peuvent être exemptés de consentement, mais seulement sous les conditions posées par la CNIL.

Conséquence pratique :

- avec la seule brique d'authentification OIDC de cette stack, il est raisonnable de considérer que vous n'avez pas automatiquement besoin d'un bandeau cookies pour les seuls cookies de session techniques ;
- en revanche, vous devez documenter ces cookies dans votre information RGPD ;
- si vous ajoutez Matomo, Google Analytics, scripts tiers, widgets sociaux, vidéos embarquées, pixels de suivi ou outils marketing, il faudra vérifier que le consentement est requis ou non.

Références officielles :

- CNIL, « Cookies et traceurs : que dit la loi ? » : https://www.cnil.fr/fr/cookies-et-autres-traceurs/que-dit-la-loi
- CNIL, « Cookies : solutions pour les outils de mesure d'audience » : https://www.cnil.fr/fr/cookies-solutions-pour-les-outils-de-mesure-daudience
- CNIL, portail « Site web, cookies et autres traceurs » : https://www.cnil.fr/fr/cookies-et-autres-traceurs
- Directive ePrivacy 2002/58/CE, article 5(3) : https://eur-lex.europa.eu/legal-content/FR/TXT/?uri=CELEX:32002L0058

Point de prudence :

- cette section donne un cadrage technique et documentaire, pas un avis juridique ;
- si le site est destiné à des usagers externes ou à une collectivité, faites valider la politique cookies et la base légale retenue par votre DPO ou conseil juridique.

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

Pour `GeoServer`, le reverse proxy transmet aussi :

- `Authorization: Bearer <access_token>`
- `X-Forwarded-Access-Token`

Comportement de repli :

- si `preferred_username`, `given_name` ou `family_name` ne sont pas présents dans les en-têtes, `mviewerstudio` les relit dans le token d'accès
- si `roles` n'est pas présent, l'application tente `realm_access.roles`
- si `organization` n'est pas présent comme claim dédié, elle peut être déduite du groupe transmis dans `X-Auth-Request-Groups`

### Cas GeoServer

Si `oauth2-proxy` protège déjà `/geoserver/`, évitez de laisser `GeoServer` démarrer un second login web OIDC autonome, sinon l'utilisateur repasse par une redirection vers Keycloak.

Deux approches cohérentes existent :

- soit `GeoServer` fait confiance au reverse proxy et consomme les en-têtes `X-Auth-Request-*` ou le bearer token transmis par nginx ;
- soit `GeoServer` gère lui-même tout le flux OIDC, mais dans ce cas il ne faut pas attendre un SSO transparent uniquement via `oauth2-proxy`.

En pratique, pour éviter la double saisie, la première approche est celle à viser derrière cette stack.

Mode cible recommandé pour cette stack :

- `oauth2-proxy` gère seul le login navigateur ;
- nginx protège `/geoserver/` via `auth_request /oauth2/auth` ;
- nginx transmet à `GeoServer` un `Authorization: Bearer <access_token>` ainsi que des en-têtes utilisateur compacts ;
- `GeoServer` valide ce bearer token en mode resource server et ne doit pas déclencher son propre login OIDC web.

Checklist GeoServer pour ce mode :

1. installer l'extension communautaire `sec-oidc` correspondant exactement à la version GeoServer ;
2. si vous utilisez l'image Docker officielle, déclarer `sec-oidc` dans `COMMUNITY_EXTENSIONS` et non dans `STABLE_EXTENSIONS` ;
3. définir `PROXY_BASE_URL` sur l'URL publique de GeoServer, par exemple `http://localhost/geoserver` en local ;
4. dans `Security -> Authentication -> Filters`, conserver le filtre OIDC uniquement pour l'acceptation des bearer tokens ;
5. laisser activé `Enable Resource Server (Bearer JWT)` ;
6. ne pas ajouter ce filtre à la chaîne `web` si vous voulez éviter un second login interactif ;
7. réserver l'usage du filtre OIDC aux requêtes portant déjà un bearer token transmis par nginx.

Si vous avez déjà suivi le tutoriel GeoServer OIDC pour un login web Keycloak :

- retirez le filtre OIDC de la chaîne `web` ;
- gardez l'extension pour la validation du JWT ;
- laissez nginx et `oauth2-proxy` être le seul point d'entrée interactif.

## Configuration OIDC locale

Valeurs par défaut de `.env.docker` :

- `OAUTH2_PROXY_CLIENT_ID=mviewerstudio`
- `OAUTH2_PROXY_CLIENT_SECRET=mviewerstudio-local-secret`
- `OAUTH2_PROXY_COOKIE_SECRET=0123456789abcdef0123456789abcdef`
- `OAUTH2_PROXY_ALLOWED_ROLE=MVIEWER_ACCESS`
- `OAUTH2_PROXY_SCOPE=openid email profile organization roles`
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
