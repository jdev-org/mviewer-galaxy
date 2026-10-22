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

## Page d’accueil et session

La racine `/` sert le portail contenu dans `header/`, monté en lecture seule
dans nginx. Il contient une image locale, les liens vers Mviewer et Studio et
un header dont le bouton de connexion ou déconnexion suit la session Studio.
Ce répertoire utilise HTML, CSS et JavaScript sans compilation ni dépendance.

### Personnaliser l’accueil

| Fichier | Personnalisation |
|---|---|
| `header/config.js` | Nom, sous-titre, logo, image d’accueil et liens `headerLinks` |
| `catalogue/data.json` | Cartes du catalogue et sélection des cartes à la une avec `favorite` |
| `header/theme.css` | Couleurs, polices, arrondis, hauteurs et espacements via les variables CSS |
| `header/custom.css` | Styles libres, prioritaires sur les styles de base |
| `header/index.html` | Textes et structure du contenu |

Pour ajouter un lien dans le header, ajouter une entrée dans `headerLinks` :

```js
{ label: "Documentation", href: "https://exemple.fr/docs", newTab: true },
```

Les liens restent visibles sur mobile et passent à la ligne si nécessaire.
L’accueil et le catalogue partagent `header/assets/header.css` et
`header/assets/header.js` pour leur navigation et leur état de connexion.
Le logo par défaut des deux pages est `catalogue/img/logo_mviewer.svg` ;
`brand.logo` dans `header/config.js` permet de le remplacer pour les deux pages.
Dans `theme.css`, `--page-gutter` règle les marges latérales, `--section-padding`
les espacements des sections et `--card-padding` ceux des cartes. Les marges
latérales par défaut sont réduites à 3 % (entre 16 et 48 pixels).
Modifier les fichiers puis recharger la page suffit grâce au montage Docker ;
aucune reconstruction n’est nécessaire pour ces personnalisations.

### Cartes phares

L’accueil charge `catalogue/data.json` et présente les entrées de `data` dont
`favorite` vaut le booléen `true`. Le titre et la description sont repris du
catalogue, et `url_demo` fournit le lien. `image` et `newTab` sont facultatifs ;
sans image, le visuel d’accueil est utilisé. L’ordre du tableau est conservé.
Les chemins relatifs des liens et des images sont résolus depuis `/catalogue/`,
comme sur la page du catalogue. Privilégier un chemin absolu comme `/mviewer/`
pour pointer vers le visualiseur.

```json
{
  "favorite": true,
  "id": "1",
  "title": "Ma carte phare",
  "description": "Présentation de la carte.",
  "image": "/catalogue/img/ma-carte.webp",
  "url_demo": "/mviewer/?config=/apps/public/ma-carte.xml"
}
```

Si le catalogue est vide (`"data": []`), l’accueil affiche la carte par défaut
`/mviewer/?config=/apps/default.xml`. Cette carte sert aussi de repli si le
catalogue ne peut pas être chargé. Un catalogue non vide sans favori masque la
section et son raccourci. Aucun exemple n’est ajouté automatiquement au catalogue.

Le carrousel se parcourt avec ses boutons, les flèches du clavier ou un geste
tactile. Il ne défile pas automatiquement. Les hauteurs des images se règlent
avec `--featured-image-height` et `--featured-image-height-mobile` dans le thème.

Le proxy fournit `/portal/login`, `/portal/logout`, `/portal/studio` et
`/portal/session` et les relie au préfixe `MVIEWERSTUDIO_URL_PATH_PREFIX`.
Le bouton de connexion revient à l’accueil après authentification. L’accès à
Mviewer reste public ; les droits Studio continuent d’être vérifiés côté serveur.

`MVIEWERSTUDIO_AUTHLIB_ANONYMOUS_REDIRECT_URL=/`, dans `.envs-mviewerstudio`,
renvoie les visiteurs anonymes de Studio à l’accueil. Une valeur vide conserve
le démarrage direct du parcours de connexion. Après déconnexion, nginx remplace
le retour OIDC par la racine publique, en conservant le protocole et le port.

Autoriser cette URL racine dans **Valid post logout redirect URIs** du client
Keycloak. Le realm local fourni contient déjà cette configuration ; un realm
déjà importé doit être mis à jour dans Keycloak, car modifier le JSON ne modifie
pas un realm existant. Pour prendre en compte le nouveau montage et le changement
de Studio, relancer `up -d --build` avec les options du mode choisi.

### Visuel

Le fichier `header/assets/coast.webp` est une illustration générée avec l’outil
intégré imagegen, puis optimisée en WebP. Prompt : « Vue aérienne réaliste d’un
estuaire de la côte bretonne, eau turquoise, bancs de sable et champs verts.
Composition panoramique, océan sombre à gauche pour le texte, côte détaillée à
droite, lumière douce du matin. Aucun texte, logo, bordure ou élément d’interface. »

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
