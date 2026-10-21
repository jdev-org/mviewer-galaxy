# Docker : Mviewer et Mviewer Studio

La composition `docker-compose.yml` démarre nginx (`proxy`), Mviewer et
Mviewer Studio. Studio gère directement l'authentification OIDC avec Authlib.
Le profil `keycloak` ajoute un serveur Keycloak local de test.

Toutes les commandes de ce guide s'exécutent depuis la racine du dépôt.
Les variables sont chargées depuis `docker/.env.docker` avec `--env-file`.

## Fichiers utilisés

- `docker/docker-compose.yml` : services, profil et volumes.
- `docker/.env.docker` : variables de configuration.
- `docker/nginx/templates/authlib-keycloak-optional.conf.template` : routage HTTP commun aux deux modes.
- `resources/keycloak/mviewer-realm.json` : realm importé par le service Keycloak local.
- `resources/mviewer/` : dossiers partagés avec les services applicatifs.

L'image Studio est construite à partir de `mviewerstudio/docker/Dockerfile`.
Sa configuration frontend est celle embarquée dans l'image.

## Configuration

Ces trois variables doivent être renseignées et non vides dans les deux modes :

| Variable | Usage |
|---|---|
| `MVIEWERSTUDIO_AUTHLIB_ISSUER` | URL du realm Keycloak |
| `MVIEWERSTUDIO_AUTHLIB_CLIENT_SECRET` | Secret du client OIDC |
| `MVIEWERSTUDIO_SECRET_KEY` | Clé de session Studio |

Compose bloque le démarrage et indique la variable à renseigner si elle est
absente ou vide. Vérifier la configuration avant de lancer les services :

```bash
docker compose --env-file docker/.env.docker -f docker/docker-compose.yml config --quiet
```

Cette commande vérifie la configuration Compose. L'accès à Keycloak et la
validité des identifiants se vérifient pendant le parcours de connexion.

### Keycloak externe

Renseigner les valeurs correspondant au serveur distant :

```env
MVIEWERSTUDIO_AUTHLIB_ISSUER=https://sso.example.org/realms/mviewer
MVIEWERSTUDIO_AUTHLIB_METADATA_URL=https://sso.example.org/realms/mviewer/.well-known/openid-configuration
MVIEWERSTUDIO_AUTHLIB_CLIENT_ID=mviewerstudio
MVIEWERSTUDIO_AUTHLIB_CLIENT_SECRET=secret-du-client
MVIEWERSTUDIO_SECRET_KEY=remplacer-par-un-secret-aleatoire-long
```

Définir explicitement `MVIEWERSTUDIO_AUTHLIB_METADATA_URL` : une valeur absente
ou vide utilise le défaut du Compose, qui cible le service local `keycloak:8080`.
Les endpoints du serveur distant doivent être accessibles depuis le navigateur
pour la connexion, et depuis Studio pour les échanges OIDC.

Le client Keycloak doit autoriser le callback
`https://votre-domaine/mviewerstudio/auth/callback`, ou
`http://localhost/mviewerstudio/auth/callback` pour un test local.
Les claims doivent correspondre au contrôle d'accès configuré par
`MVIEWERSTUDIO_AUTHLIB_ALLOWED_GROUPS` (par défaut `MVIEWER_ACCESS`).

Démarrer :

```bash
docker compose --env-file docker/.env.docker -f docker/docker-compose.yml up -d --build
```

### Keycloak local

Configurer les valeurs du realm de test :

```env
MVIEWERSTUDIO_AUTHLIB_ISSUER=http://localhost/keycloak/realms/mviewer
MVIEWERSTUDIO_AUTHLIB_METADATA_URL=http://keycloak:8080/keycloak/realms/mviewer/.well-known/openid-configuration
MVIEWERSTUDIO_AUTHLIB_CLIENT_ID=mviewerstudio
MVIEWERSTUDIO_AUTHLIB_CLIENT_SECRET=mviewerstudio-local-secret
MVIEWERSTUDIO_SECRET_KEY=remplacer-par-un-secret-aleatoire-long
KEYCLOAK_HOSTNAME=http://localhost/keycloak
```

Démarrer avec le profil :

```bash
docker compose --env-file docker/.env.docker -f docker/docker-compose.yml --profile keycloak up -d --build
```

Le profil sélectionne les services ; les valeurs Authlib restent celles définies
dans le fichier d'environnement. Le realm importé est `mviewer`.

| Usage | Utilisateur | Mot de passe local |
|---|---|---|
| Studio | `john.doe` | `john` |
| Test | `test` | `test` |
| Administration | `admin` | `admin` |

Le compte administrateur peut être configuré avec `KEYCLOAK_ADMIN` et
`KEYCLOAK_ADMIN_PASSWORD`.
Le serveur fonctionne en mode développement ; ses données résident dans le
conteneur. Sa recréation réimporte le realm et réinitialise les modifications
faites dans la console.

## URLs

- Studio : `http://localhost/mviewerstudio/`.
- Mviewer : `http://localhost/mviewer/`.
- Administration Keycloak locale : `http://localhost/keycloak/admin/`.

La racine `/` redirige vers Studio. Le callback OIDC est
`/mviewerstudio/auth/callback`. Adapter les adresses publiques si le port ou le
nom d'hôte change, ainsi que les URL autorisées dans le client Keycloak.

## Variables complémentaires

| Variable | Valeur par défaut | Usage |
|---|---|---|
| `PROXY_HTTP_PORT` | `80` | Port HTTP publié sur l'hôte |
| `NGINX_HOST` | `localhost` | Nom de serveur nginx |
| `MVIEWERSTUDIO_UID` / `MVIEWERSTUDIO_GID` | `1000` / `1000` | Identité du processus Studio |
| `MVIEWERSTUDIO_DEFAULT_ORG` | `jdev` | Organisation par défaut |
| `MVIEWERSTUDIO_AUTHLIB_CLIENT_ID` | `mviewerstudio` | Client OIDC |
| `MVIEWERSTUDIO_AUTHLIB_SCOPE` | `openid profile email organization` | Scopes demandés |
| `MVIEWERSTUDIO_AUTHLIB_ALLOWED_GROUPS` | `MVIEWER_ACCESS` | Contrôle d'accès Studio |
| `KEYCLOAK_HOSTNAME` | `http://localhost/keycloak` | URL publique du Keycloak local |

## Volumes et permissions

| Dossier de l'hôte | Chemin dans Studio | Chemin dans nginx et Mviewer |
|---|---|---|
| `resources/mviewer/apps` | `/home/mvuser/apps` | `/usr/share/nginx/html/apps` |
| `resources/mviewer/store` | `/home/mvuser/store` | `/usr/share/nginx/html/store` |
| `resources/mviewer/public` | `/home/mvuser/public` | `/usr/share/nginx/html/public` |

Studio dispose d'un accès en lecture-écriture ; nginx et Mviewer disposent d'un
accès en lecture seule. Studio enregistre actuellement ses configurations dans
`apps/store` et publie dans `apps/public`, à l'intérieur du premier montage.

Adapter `MVIEWERSTUDIO_UID` et `MVIEWERSTUDIO_GID` au propriétaire des dossiers
partagés si nécessaire. Une erreur de permission sur `apps/store/register.json`
empêche le démarrage de Studio et provoque un 502 dans nginx.

## Exploitation

Afficher l'état et les derniers journaux :

```bash
docker compose --env-file docker/.env.docker -f docker/docker-compose.yml --profile keycloak ps -a
docker compose --env-file docker/.env.docker -f docker/docker-compose.yml --profile keycloak logs --tail 100 proxy mviewerstudio keycloak
```

Après une modification des volumes ou des variables, relancer la commande
`up -d` du mode choisi pour recréer les services concernés. Ajouter `--build`
pour reconstruire l'image après une modification de Studio.

Arrêter et supprimer les conteneurs et le réseau de la composition :

```bash
docker compose --env-file docker/.env.docker -f docker/docker-compose.yml --profile keycloak down
```

Les dossiers partagés de l'hôte sont conservés. Le Keycloak local est réinitialisé
à la prochaine création de son conteneur.

Pour passer du Keycloak local à un serveur externe, arrêter d'abord le service :

```bash
docker compose --env-file docker/.env.docker -f docker/docker-compose.yml --profile keycloak stop keycloak
```

Configurer ensuite les valeurs externes et relancer la commande de démarrage
correspondante. Un changement de profil ne suffit pas à arrêter un service déjà actif.

## Reverse proxy HTTPS

Un nginx existant peut terminer TLS et relayer vers le port HTTP du service
`proxy`. Transmettre `Host`, `X-Forwarded-For` et `X-Forwarded-Proto: https` pour
que Studio construise son URL de retour publique. Aligner le callback autorisé
côté Keycloak.

Le port publié se règle avec `PROXY_HTTP_PORT` ; le Compose le publie sur les
interfaces de l'hôte. Le template nginx résout le nom du Keycloak local à la
réception des requêtes, ce qui permet de démarrer dans les deux modes.

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

Cette stack peut déposer au moins des cookies techniques de session liés à l'authentification OIDC, via la session Authlib de Studio et les cookies de session Keycloak.

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
