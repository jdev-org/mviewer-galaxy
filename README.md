# Stack Docker mviewer + mviewerstudio + Keycloak

Cette composition lance :

- `proxy` : reverse-proxy nginx expose sur `http://localhost`
- `mviewer` : le code statique de `../mviewer` servi par nginx avec les apps de `keycloak/resources/mviewer/apps`
- `mviewerstudio` : image construite depuis `../mviewerstudio` avec la configuration `keycloak/resources/mviewerstudio/config.json`
- `postgres` : base PostgreSQL de Keycloak
- `keycloak` : Keycloak expose derriere `/keycloak` avec import du realm `resources/keycloak/mviewer-realm.json`
- `oauth2-proxy` : proxy OIDC qui protege l'acces a mviewerstudio avec Keycloak

## Demarrage

```bash
cd docker
cp .env.example .env
docker compose up --build
```

Si la stack avait deja ete lancee avant l'ajout du client OIDC, recreer le volume Keycloak pour rejouer l'import du realm :

```bash
docker compose down -v
docker compose up --build
```

URLs par defaut :

- mviewerstudio : `http://localhost/mviewerstudio/`
- mviewer : `http://localhost/mviewer/`
- Keycloak : `http://localhost/keycloak/`

Identifiants Keycloak par defaut : `admin` / `admin`.

Realm importe par defaut : `mviewer`.

Utilisateurs de test du realm :

- `admin` / `admin`
- `john.doe` / `john`

L'acces a `http://localhost/mviewerstudio/` redirige vers Keycloak. `oauth2-proxy` autorise uniquement les utilisateurs qui ont le role Keycloak configuré dans `OAUTH2_PROXY_ALLOWED_ROLE`. Par defaut, ce rôle est `MVIEWER_ACCESS` (disponible par défaut à l'installation).

Le role importe par defaut dans Keycloak est `MVIEWER_ACCESS`. Les utilisateurs de test `admin` et `john.doe` le possedent deja. mviewerstudio verifie aussi les roles transmis par `oauth2-proxy` via `MVIEWERSTUDIO_AUTH_ALLOWED_ROLES`, avec la valeur par defaut `MVIEWER_ACCESS`.

Le client OIDC importe dans Keycloak est `mviewerstudio`. Ses valeurs locales par defaut sont definies dans `docker/.env.example` :

- `OAUTH2_PROXY_CLIENT_ID=mviewerstudio`
- `OAUTH2_PROXY_CLIENT_SECRET=mviewerstudio-local-secret`
- `OAUTH2_PROXY_COOKIE_SECRET=0123456789abcdef0123456789abcdef`
- `OAUTH2_PROXY_ALLOWED_ROLE=MVIEWER_ACCESS`

Pour utiliser un autre role d'acces, creer ou attribuer ce role dans Keycloak, puis adapter :

- `OAUTH2_PROXY_ALLOWED_ROLE=<role_keycloak>`
- `MVIEWERSTUDIO_AUTH_ALLOWED_ROLES=<role_keycloak>`

Pour utiliser un autre hote ou un autre port public, adapter aussi :

- `KEYCLOAK_HOSTNAME`
- `OAUTH2_PROXY_OIDC_ISSUER_URL`
- `OAUTH2_PROXY_LOGIN_URL`
- `OAUTH2_PROXY_REDIRECT_URL`

et ajouter l'URL de callback correspondante dans le client Keycloak `mviewerstudio`.

## Notes

- Les mots de passe de `.env.example` sont uniquement prevus pour un environnement local.
- Les secrets `OAUTH2_PROXY_CLIENT_SECRET` et `OAUTH2_PROXY_COOKIE_SECRET` doivent etre remplaces avant tout deploiement partage ou expose.
- Le dossier local `resources/mviewer/apps` est partage entre mviewer, mviewerstudio et le proxy pour les configurations generees.
- Pour changer le port HTTP local, modifier `PROXY_HTTP_PORT` dans `.env`.
