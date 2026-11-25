---
title: "Installation"
description: "Installer Mviewer, Studio, PostgreSQL/PostGIS et GeoServer sur un serveur avec systemd."
sidebar:
  order: 2
next:
  label: "Adapter à son environnement"
  link: /mviewer-galaxy/guides/ansible/environnement/
---

- Le playbook installe Mviewer, Studio avec Gunicorn, PostgreSQL/PostGIS, GeoServer avec Jetty et Java 21, nginx et logrotate.

- Les applications sont exécutées comme services systemd.

- Studio fonctionne par défaut sans authentification.

- OIDC peut être activé avec un fournisseur externe.

## Plan général des étapes d'installation

| Étape | Action | Résultat attendu |
|---|---|---|
| 1. [Vérifier les prérequis](#install-prerequisites) | Préparer Ansible sur le poste de contrôle et une cible avec systemd, Python 3.11+ et Java 21 disponible dans APT. | Environnement compatible avec les rôles. |
| 2. [Configurer SSH](#install-ssh) | Renseigner l'adresse du serveur et le compte SSH avec sudo dans l'inventaire. | Serveur accessible dans le groupe `galaxy`. |
| 3. [Définir le site](#install-site) | Créer `site.yml` avec le domaine public et les paramètres souhaités. | Configuration propre au déploiement. |
| 4. [Préparer la base SIG](#install-database) | Renseigner la base, l'utilisateur SQL et son mot de passe dans `secrets.vault.yml`. | Identifiants partagés par PostgreSQL et GeoServer. |
| 5. [Préparer les accès PostgreSQL](#install-network) | Adapter le template `pg_hba.conf.j2` avec les clients autorisés. | Règles réseau prêtes avant l'installation. |
| 6. [Préparer les secrets](#install-secrets) | Définir les accès GeoServer, la clé Studio et les secrets OIDC éventuels, puis chiffrer le Vault. | Secrets disponibles pour le playbook. |
| 7. [Contrôler et déployer](#install-deployment) | Vérifier les prérequis, puis exécuter le playbook avec les fichiers du site et des secrets. | Applications installées et services configurés. |
| 8. [Vérifier les applications](#install-applications) | Ouvrir les URL publiques et [consulter les services et journaux](#install-operations). | Accueil, Mviewer, Studio et GeoServer accessibles. |
| 9. [Configurer CORS si nécessaire](#install-cors) | Autoriser les origines clientes si les cartes interrogent GeoServer depuis une autre origine. | Requêtes du navigateur autorisées pour ces clients. |

<div class="ansible-section-anchor" id="install-components"></div>

## Dépendances et versions

- Les versions ci-dessous correspondent aux valeurs par défaut du dépôt.

- Les versions des paquets APT dépendent de la distribution et des dépôts configurés sur la cible.

- Le playbook ne les fixe pas à une version précise.

| Élément | Version ou référence par défaut | Installation et configuration |
|---|---|---|
| Mviewer | Branche `master` | Sources Git ; variable `mviewer_version`, acceptant aussi un tag ou un SHA |
| Mviewer Studio | Branche `oauth2-proxy-keycloak` | Sources Git ; variable `mviewerstudio_version`, acceptant aussi un tag ou un SHA |
| GeoServer | `3.0.2` | Archive officielle ; `geoserver_version` et `geoserver_archive_checksum` |
| Jetty | `12.1.14` | Inclus dans l'archive GeoServer `3.0.2` ; sa version suit celle de la distribution GeoServer |
| Java / OpenJDK | `21` | Paquet APT `openjdk-21-jre-headless` ; correctifs fournis par les dépôts de la cible |
| Python | `3.11` minimum | Python existant ou paquet APT `python3`, avec `python3-pip` et `python3-venv` |
| Gunicorn | `>20` dans les dépendances Studio actuelles | Installé par pip dans le virtualenv Studio, selon `install/requirements.txt` de la révision déployée |
| PostgreSQL | Version des dépôts APT de la cible | Paquet `postgresql`, configurable dans `postgres_packages` |
| PostGIS | Version des dépôts APT de la cible | Paquets `postgresql-postgis` et `postgis`, pour la version PostgreSQL fournie par ces dépôts |
| nginx | Version des dépôts APT de la cible | Paquet `nginx` ; sert les pages et relaie Studio et GeoServer |
| logrotate | Version des dépôts APT de la cible | Paquet `logrotate`, avec activation de `logrotate.timer` |
| Outils et bibliothèques système | Versions des dépôts APT de la cible | `git`, `ca-certificates`, `unzip`, `libxml2-dev`, `libxslt1-dev` |

- Les autres dépendances Python de Studio suivent également son fichier `install/requirements.txt`.

- Une branche Git peut évoluer : utiliser un tag ou un SHA pour figer les sources.

- Ansible Core `2.16+` sur le poste de contrôle et systemd sur la cible sont des prérequis, plutôt que des composants installés par le playbook.

- Pour les paramètres détaillés, voir [Adapter à son environnement](/mviewer-galaxy/guides/ansible/environnement/).

- En cas d'erreur, consulter le [Dépannage Ansible](/mviewer-galaxy/guides/ansible/depannage/).

<div class="ansible-section-anchor" id="install-prerequisites"></div>

## Prérequis

- Sur le poste de contrôle : Ansible Core 2.16 ou supérieur et une copie du dépôt.
- Sur la cible : Debian 12+ ou Ubuntu 22.04+, avec systemd et un compte SSH disposant de sudo.
- Python 3.11+ et `openjdk-21-jre-headless` installés ou disponibles dans les dépôts APT de la cible.
- Accès sortant aux dépôts APT, Git et Python, ainsi qu'à SourceForge et ses miroirs pour GeoServer.

- Le rôle `common` peut installer Python s'il est absent et disponible dans APT.

- Les dépôts de base de certaines versions, notamment Debian 12, ne fournissent pas Java 21 : préparer un dépôt adapté avant le déploiement.

- Les rôles n'ajoutent pas de dépôt Java.

- Aucune collection Ansible externe n'est nécessaire.

Toutes les commandes suivantes s'exécutent depuis le répertoire `ansible/` du dépôt, afin de charger `ansible.cfg` et ses modules locaux :

```bash
cd ansible
```

<div class="ansible-section-anchor" id="install-ssh"></div>

## Configurer la connexion SSH

Adapter `inventories/dev/hosts.ini` :

```ini
[galaxy]
mviewer-dev ansible_host=serveur.example.org ansible_user=deploy
```

| Élément | Explication |
|---|---|
| `[galaxy]` | Groupe de serveurs ciblé par les playbooks ; conserver ce nom. |
| `mviewer-dev` | Alias libre à personnaliser pour identifier le serveur dans Ansible. |
| `ansible_host` | Nom de domaine ou adresse IP du serveur cible, joignable depuis le poste de contrôle. |
| `ansible_user` | Compte SSH avec sudo qui réalisera l'installation ; `deploy` est un exemple à remplacer. |
| `ansible_port` | Port SSH de la cible ; ajouter cette variable si le port diffère de `22`. |
| `ansible_ssh_private_key_file` | Chemin de la clé privée sur le poste de contrôle, si une clé spécifique est nécessaire. |

Par défaut, le compte système `mviewer`, créé par le rôle `common`, sert à exécuter Mviewer Studio et à écrire dans ses répertoires de données et de journaux.

Pour utiliser une clé spécifique, ajouter `ansible_ssh_private_key_file=/chemin/vers/la/cle` sur la ligne du serveur.

<div class="ansible-section-anchor" id="install-site"></div>

## Définir les paramètres du site

Créer `site.yml` :

```yaml
nginx_server_name: cartes.example.org
mviewerstudio_auth_mode: public
geoserver_workspace: donnessig
geoserver_datastore: postgis
```

| Élément | Explication |
|---|---|
| `nginx_server_name` | Nom de domaine public du site ; remplacer `cartes.example.org` et configurer son DNS. |
| `mviewerstudio_auth_mode` | `public` autorise un accès sans connexion ; `authlib` active OIDC. |
| `geoserver_workspace` | Nom du workspace GeoServer créé et défini par défaut : `donnessig` dans cet exemple. |
| `geoserver_datastore` | Nom de l'entrepôt PostGIS dans le workspace : `postgis` dans cet exemple. |

- Faire pointer l'enregistrement DNS du domaine public vers le serveur.

- Les variables sont dans `group_vars/all/common.yml` et un fichier par application sous `group_vars/all/`. Les secrets sont dans `secrets.vault.yml`.

- Les personnaliser avec `-e @site.yml`.

- Les deux playbooks principaux chargent explicitement les fichiers de variables et la liste des extensions, même avec un inventaire personnalisé.

- Les sources sont clonées sur la cible depuis les dépôts Git, sans transférer les modifications locales des sous-modules.

- Pour une URL publique HTTPS, configurer un terminateur TLS devant nginx.

- Définir `galaxy_public_scheme: https` pour transmettre le schéma public aux applications.

- Cette variable adapte les URL et en-têtes transmis aux applications.

- Elle ne configure pas de certificat.

| Fichier | Paramètres |
|---|---|
| `group_vars/all/common.yml` | Comptes système, chemins partagés, paquets communs et schéma public |
| `group_vars/all/mviewer.yml` | Dépôt et version Git, répertoires partagés apps/store/public |
| `group_vars/all/mviewerstudio.yml` | Dépôt et version Git, Gunicorn, chemins et paramètres OIDC publics |
| `group_vars/all/nginx.yml` | Nom du serveur public, port HTTP et journaux |
| `group_vars/all/postgres.yml` | Paquets, base et utilisateur par défaut, port, socket et template pg_hba |
| `group_vars/all/geoserver.yml` | Version, empreinte de l’archive, Java, chemins, ports et catalogue PostGIS |
| `group_vars/all/geoserver_extensions.yml` | Liste des extensions, URL des archives et empreintes SHA-256 |

<div class="ansible-section-anchor" id="install-database"></div>

## Préparer la base de données SIG

```bash
cp secrets.example.yml secrets.vault.yml
chmod 600 secrets.vault.yml
```

- `secrets.example.yml` / `secrets.vault.yml` : Modèle fourni et fichier local contenant les identifiants PostgreSQL à personnaliser.

Modifier `secrets.vault.yml` avec les valeurs souhaitées et un mot de passe personnel :

```yaml
postgres_database: donneessig
postgres_username: usersig
postgres_password: ""
```

| Élément | Explication |
|---|---|
| `postgres_database` | Nom de la base SIG à créer ; `donneessig` est la valeur par défaut. |
| `postgres_username` | Compte SQL propriétaire de la base et du schéma `public` ; `usersig` est la valeur par défaut. |
| `postgres_password` | Mot de passe SQL obligatoire à renseigner ; ne pas laisser la valeur vide. |

- Le mot de passe est obligatoire.

- Les valeurs suivent la syntaxe YAML et sont transmises aux modules sans interprétation shell.

- `secrets.vault.yml` est ignoré par Git et lu sur le poste de contrôle.

- Charger le fichier chiffré avec `-e @secrets.vault.yml --ask-vault-pass`.

- Le rôle crée l'utilisateur SQL, la base et PostGIS.

- L'utilisateur est propriétaire de la base et du schéma `public`, avec connexion autorisée et sans droits superutilisateur.

- Les comptes SQL sont distincts des comptes Linux et SSH.

<div class="ansible-section-anchor" id="install-network"></div>

### Préparer les accès réseau avant l'installation

- Modifier `roles/postgres/templates/pg_hba.conf.j2` avant de lancer le déploiement : ce template remplace le fichier `pg_hba.conf` du serveur.

- Conserver les règles d'accès local déjà présentes.

- Ajouter les IP ou réseaux autorisés à l'emplacement prévu, avant les règles de refus :

```text
host "{{ postgres_configuration.database }}" "{{ postgres_configuration.username }}" 192.0.2.10/32 scram-sha-256
```

- Remplacer `192.0.2.10/32` par l'adresse du client ou le réseau autorisé.

- Conserver les variables Jinja : les noms de base et d'utilisateur proviennent de `secrets.vault.yml`.

- Adapter le pare-feu pour autoriser les connexions souhaitées au port PostgreSQL.

Pour le format des règles et les méthodes d'authentification, consulter la [documentation PostgreSQL sur `pg_hba.conf`](https://docs.postgresql.fr/12/auth-pg-hba-conf.html).

<div class="ansible-section-anchor" id="install-secrets"></div>

## Compléter et chiffrer le Vault des applications

```bash
# Reprendre le fichier préparé pour la base SIG.
python3 -c 'import secrets; print(secrets.token_hex(32))'
```

| Élément | Explication |
|---|---|
| `secrets.example.yml` / `secrets.vault.yml` | Modèle fourni et fichier de secrets du déploiement, à personnaliser et chiffrer. |
| `mviewerstudio_secret_key` | Clé de session aléatoire de 32 caractères minimum ; obligatoire même en mode public. |
| `geoserver_admin_username`, `geoserver_admin_password` | Compte REST actuel de GeoServer, obligatoire dès la première installation ; aucune valeur par défaut dans le rôle. |
| `mviewerstudio_oidc_client_secret` | Secret du client OIDC en mode `authlib`. |
| `ansible_password`, `ansible_become_password` | Mots de passe SSH/sudo facultatifs ; à conserver dans le Vault si nécessaires. |

- Renseigner la valeur générée dans `mviewerstudio_secret_key` du fichier `secrets.vault.yml`.

- Renseigner aussi `geoserver_admin_username` et `geoserver_admin_password` avec les identifiants actuels du serveur, dès la première installation.

- Chiffrer ce fichier :

```bash
ansible-vault encrypt secrets.vault.yml
```

- Pour une installation vierge, les identifiants initiaux GeoServer sont `admin` / `geoserver`. Pour un serveur existant, utiliser ses identifiants actuels. Le rôle ne change pas ce mot de passe.

- Pour modifier ensuite le fichier chiffré, utiliser `ansible-vault edit secrets.vault.yml` ; ne pas recopier le modèle par-dessus un Vault existant.

- Le fichier n’est pas chargé automatiquement : ajouter `-e @secrets.vault.yml --ask-vault-pass` aux commandes qui en ont besoin.


- `secrets.vault.yml` : Fichier de secrets du poste de contrôle, ignoré par Git.
- La clé de session est requise même en mode `public`.

- Pour activer OIDC, définir `mviewerstudio_auth_mode: authlib` dans `site.yml`.

- Fournir l'issuer et le secret du client via les variables `mviewerstudio_oidc_*`.

- L'issuer doit être accessible depuis la cible.

- Le callback public est `https://cartes.example.org/mviewerstudio/auth/callback`, à adapter au site.

- Le playbook n'installe pas Keycloak.

<div class="ansible-section-anchor" id="install-deployment"></div>

## Vérifier puis déployer

Vérifier l'inventaire, la syntaxe et les prérequis :

```bash
ansible-inventory --graph
ansible-playbook playbooks/install.yml --syntax-check
ansible-playbook playbooks/install.yml --tags check -e @site.yml --ask-become-pass
```

| Élément | Explication |
|---|---|
| `ansible-inventory --graph` | Affiche les groupes et les serveurs de l'inventaire chargé. |
| `playbooks/install.yml` | Playbook principal d'installation de Mviewer Galaxy. |
| `--syntax-check` | Vérifie la syntaxe du playbook sans déployer les applications. |
| `--tags check` | Exécute uniquement les contrôles de prérequis. |
| `-e @site.yml` | Charge les paramètres personnalisés du site depuis le poste de contrôle. |
| `--ask-become-pass` | Demande le mot de passe sudo du compte SSH ; omettre si sudo est sans mot de passe. |

- Le contrôle seul ne demande aucun secret applicatif. Si les mots de passe SSH/sudo sont stockés dans le Vault, le charger aussi pour cette commande.

- Il vérifie notamment les droits sudo, le système cible, les paquets APT et l'accès aux dépôts Git.

- La première commande simule les changements avec `--check --diff`.

- La seconde commande applique le déploiement sans `--check` :

```bash
ansible-playbook playbooks/install.yml -e @site.yml -e @secrets.vault.yml --ask-vault-pass --ask-become-pass --check --diff
ansible-playbook playbooks/install.yml -e @site.yml -e @secrets.vault.yml --ask-vault-pass --ask-become-pass
```

| Élément | Explication |
|---|---|
| `playbooks/install.yml` | Déploie tous les rôles sur les serveurs du groupe `galaxy`. |
| `-e @site.yml` | Charge les variables propres au site. |
| `-e @secrets.vault.yml` | Charge les secrets chiffrés. |
| `--ask-vault-pass` | Demande le mot de passe permettant de déchiffrer le fichier Vault. |
| `--ask-become-pass` | Demande le mot de passe sudo du compte SSH. |
| `--check` | Simule les changements pris en charge par les rôles. |
| `--diff` | Affiche les différences des fichiers non masqués ; les tâches sensibles restent protégées par `no_log`. |
| `-i inventories/production/hosts.ini` | Option à ajouter pour sélectionner un autre inventaire. |

- Omettre `--ask-become-pass` si sudo fonctionne sans mot de passe.

- Avec un autre inventaire, ajouter `-i inventories/production/hosts.ini` à chaque commande.

- La simulation nécessite Python déjà installé sur la cible.

- Elle ne valide pas le démarrage des services, le provisionnement SQL, les accès PostgreSQL ni la configuration du catalogue GeoServer.

- Les passages suivants conservent les données et ajustent la configuration.

- Un mot de passe modifié dans `secrets.vault.yml` est appliqué à PostgreSQL et à l'entrepôt GeoServer.

- À sources et paramètres inchangés, une nouvelle exécution permet de contrôler l'idempotence.

- Figer les versions Git par tag ou SHA pour un déploiement reproductible.

- Changer un nom de base crée une nouvelle base sans migrer l'ancienne.

Le déploiement installe aussi les 14 extensions listées avec leurs URL et empreintes SHA-256 dans `group_vars/all/geoserver_extensions.yml`. Pour en ajouter ensuite, utiliser le playbook dédié `playbooks/geoserver_extensions.yml`. Voir [la gestion des extensions](/mviewer-galaxy/guides/ansible/environnement/#ajouter-ou-mettre-à-jour-les-extensions-geoserver). Le support raster GDAL est exclu ; OGR et Image Pyramid installent les outils `gdal-bin` et `python3-gdal`.

<div class="ansible-section-anchor" id="install-applications"></div>

## Accéder aux applications

- Exemples avec le domaine public `cartes.example.org` et la cible SSH `serveur.example.org`.

- Les ports indiqués sont les valeurs par défaut.

| Service | URL ou connexion | Port d'accès | Destination sur le serveur |
|---|---|---|---|
| Accueil | `http://cartes.example.org/` ou `/home/` | `80` | nginx, fichiers statiques |
| Mviewer | `http://cartes.example.org/mviewer/` | `80` | nginx, fichiers statiques |
| Studio | `http://cartes.example.org/mviewerstudio/` | `80` | Gunicorn sur `127.0.0.1:5007` |
| GeoServer | `http://cartes.example.org/geoserver/` | `80` | Jetty sur `127.0.0.1:8080` |
| PostgreSQL | `postgresql://usersig@serveur.example.org:5432/donneessig` | `5432`, si le client est autorisé | Connexion SQL directe, contrôlée par `pg_hba.conf` et le pare-feu |
| SSH / Ansible | `ssh://deploy@serveur.example.org:22` | `22`, selon l'inventaire | Service SSH préexistant de la cible |

- Les applications web partagent le port nginx `nginx_http_port`.

- Les ports `mviewerstudio_port` et `geoserver_port` sont utilisés par le proxy en interne.

- Le navigateur utilise les URL publiques du tableau.

- `postgres_port` définit le port PostgreSQL ciblé par les rôles, et `ansible_port` le port SSH dans l'inventaire.

- Avec HTTPS, le port public habituel est `443` sur le terminateur TLS.

- Nginx conserve son port HTTP configuré.

- Définir alors `galaxy_public_scheme: https`.

- Adapter les URL, ports, préfixes et identifiants aux paramètres de `site.yml`, de l'inventaire et de `secrets.vault.yml`.

- GeoServer utilise Java 21 et Jetty, avec une écoute locale sur `127.0.0.1:8080`.

- Le rôle crée le workspace **`donnessig`**, le définit par défaut.

- Configure l'entrepôt **`postgis`** vers **`donneessig`** avec **`usersig`** et le mot de passe du Vault `secrets.vault.yml`.

- La connexion est vérifiée sans publier automatiquement de couche.

- L'administration initiale de GeoServer utilise `admin` / `geoserver`.

- Changer ce mot de passe avant une publication publique.

- Fournir sa valeur actuelle via `geoserver_admin_password` dans le fichier Vault pour les déploiements suivants.

- Le rôle ne change pas lui-même le mot de passe administrateur.

<div class="ansible-section-anchor" id="install-cors"></div>

## CORS : accéder à GeoServer depuis une autre origine

- Une origine correspond au protocole, au nom d'hôte et au port.

- Dans le déploiement par défaut, Mviewer et GeoServer passent par le même nginx : une carte servie depuis `https://cartes.example.org/mviewer/` peut interroger `/geoserver/` sur cette même origine sans réglage CORS supplémentaire.

| Application cliente | Service interrogé | CORS à configurer pour les requêtes JavaScript |
|---|---|---|
| `https://cartes.example.org/mviewer/` | `https://cartes.example.org/geoserver/` | Non, même origine |
| `https://sig.example.org/` | `https://cartes.example.org/geoserver/` | Oui, nom d'hôte différent |
| `http://localhost:4321/` | `http://localhost:8080/geoserver/` | Oui, port différent |

- Utiliser l'URL publique de GeoServer, plutôt que son adresse interne `127.0.0.1:8080`, dans les cartes.

- Pour un service hébergé ailleurs, c'est ce service distant qui doit autoriser l'origine de la carte.

### Configurer GeoServer

- Le playbook ne configure pas automatiquement CORS.

- Dans l'administration GeoServer **3.0.2** installée par défaut, ouvrir **Security > CORS**, activer CORS.

- Renseigner les options utiles :

| Option | Rôle | Exemple pour un client autorisé |
|---|---|---|
| Allowed Origin Patterns | Origines des applications clientes autorisées à lire les réponses | `https://sig.example.org`, sans chemin |
| Allowed Methods | Méthodes HTTP autorisées pour les requêtes | `GET, HEAD, OPTIONS` ; ajouter `POST` si nécessaire |
| Allowed Headers | En-têtes que le navigateur pourra envoyer | `Accept, Content-Type` ; ajouter `Authorization` si utilisé |
| Supports Credentials | Autorise l'envoi de cookies ou d'identifiants par le navigateur | Désactivé pour les données publiques sans identifiants |
| Max Age | Durée de mise en cache du résultat d'un preflight | `600` secondes |

- Enregistrer les paramètres CORS dans GeoServer.

- Redémarrer GeoServer, comme indiqué dans la [documentation GeoServer](https://docs.geoserver.org/stable/en/user/production/container/#enable-cors) :

```bash
sudo systemctl restart geoserver
```

- `geoserver` : Nom de l’unité systemd GeoServer à redémarrer.
- Pour des requêtes envoyant des cookies ou des identifiants, activer le support correspondant et autoriser des origines explicites : une réponse `Access-Control-Allow-Origin: *` est incompatible avec les requêtes utilisant des credentials.

- Voir [l'explication MDN](https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/CORS/Errors/CORSNotSupportingCredentials).

- Le template nginx actuel relaie les réponses de GeoServer sans ajouter d'en-têtes CORS.

- Conserver cette gestion dans GeoServer : configurer en parallèle les mêmes en-têtes dans nginx peut produire des valeurs dupliquées, refusées par le navigateur.

- Voir [les erreurs CORS](https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/CORS/Errors).

### Vérifier la réponse et le preflight

Tester avec l'origine réelle de l'application cliente :

```bash
curl -sS -D - -o /dev/null \
  -H 'Origin: https://sig.example.org' \
  'https://cartes.example.org/geoserver/donnessig/wms?service=WMS&request=GetCapabilities'
```

| Élément | Explication |
|---|---|
| `-H 'Origin: …'` | Simule l’origine de l’application cliente ; remplacer par son protocole, hôte et port réels. |
| `/geoserver/donnessig/wms` | Service WMS du workspace `donnessig`, via l’URL publique du serveur. |
| `service=WMS` | Sélectionne le protocole de service cartographique WMS. |
| `request=GetCapabilities` | Demande les capacités et les métadonnées du service. |

- La réponse doit autoriser `https://sig.example.org` via l'en-tête `Access-Control-Allow-Origin`.

- Vérifier aussi une requête préalable `OPTIONS` pour un client qui envoie l'en-tête `Content-Type` :

```bash
curl -i -X OPTIONS \
  -H 'Origin: https://sig.example.org' \
  -H 'Access-Control-Request-Method: GET' \
  -H 'Access-Control-Request-Headers: content-type' \
  'https://cartes.example.org/geoserver/donnessig/wms'
```

| Élément | Explication |
|---|---|
| `-X OPTIONS` | Envoie la requête préalable utilisée pour vérifier les autorisations CORS. |
| `Origin` | Origine réelle de l’application cliente à autoriser. |
| `Access-Control-Request-Method: GET` | Indique que la requête réelle utilisera la méthode `GET`. |
| `Access-Control-Request-Headers: content-type` | Indique que le client souhaite envoyer l’en-tête `Content-Type`. |

- Contrôler les en-têtes `Access-Control-Allow-Origin`, `Access-Control-Allow-Methods` et `Access-Control-Allow-Headers`.

- Tester depuis le navigateur.

- `curl` n'applique pas les restrictions CORS du navigateur.

- Un statut HTTP 200 seul ne suffit pas.

- La lecture WMS/WFS publique n'exige pas d'autoriser les méthodes d'administration `PUT` ou `DELETE`.

- Les droits d'accès aux couches et à la base restent gérés séparément de CORS.

<div class="ansible-section-anchor" id="install-operations"></div>

## Données, journaux et services

Les répertoires utiles ci-dessous correspondent à l'installation par défaut.

| Répertoire sur le serveur | Contenu et utilité |
|---|---|
| `/var/www/mviewergalaxy/home/` | Accueil statique |
| `/var/www/mviewergalaxy/mviewer/` | Sources Mviewer et liens `apps`, `store`, `public` |
| `/srv/apps/mviewerstudio/` | Sources Studio et virtualenv `.venv/` |
| `/opt/geoserver/3.0.2/` | Distribution GeoServer et Jetty ; chemin lié à `geoserver_version` |
| `/srv/data/mviewer/apps/` | Cartes Mviewer |
| `/srv/data/mviewer/store/` | Cartes générées par Studio |
| `/srv/data/mviewer/public/` | Cartes publiées depuis `store` |
| `/srv/data/geoserver/datadir/` | Catalogue, données et sécurité GeoServer |
| `/var/lib/postgresql/<version>/<cluster>/` | Données SQL du cluster PostgreSQL ; vérifier le chemin réel avec `pg_lsclusters` |
| `/var/lib/mviewer-galaxy/` | Configuration front générée `mviewerstudio-config.json` |
| `/var/lib/mviewer-galaxy/sessions/` | Sessions privées de Studio |
| `/srv/logs/nginx/` | Accès HTTP et erreurs du proxy |
| `/srv/logs/mviewerstudio/` | Journaux Gunicorn et sortie de l'application |
| `/srv/logs/geoserver/` | Journaux GeoServer et console Jetty |
| `/srv/logs/postgresql/` | Journaux des clusters PostgreSQL |
| `/var/cache/geoserver/` | Fichiers temporaires de Java et Jetty |
| `/var/cache/geoserver-downloads/` | Archive GeoServer et empreinte de configuration de l'entrepôt |
| `/etc/nginx/` | Configuration nginx ; site dans `sites-available/mviewer-galaxy` |
| `/etc/mviewerstudio/` | Fichier `environment` contenant les variables et secrets de Studio, accès root |
| `/etc/postgresql/<version>/<cluster>/` | Configuration du cluster, dont `postgresql.conf` et `pg_hba.conf` |
| `/etc/systemd/system/` | Unités `mviewerstudio.service` et `geoserver.service` |
| `/etc/logrotate.d/` | Règles de rotation des journaux applicatifs |

- Les répertoires `apps`, `store` et `public` de Mviewer sont des liens symboliques vers leurs destinations dans `/srv/data/mviewer/`.

- Les comptes `geoserver` et `postgres` exécutent leurs services respectifs.

- La rotation des journaux est quotidienne, avec 14 archives conservées par défaut.

Sur la cible :

```bash
sudo systemctl status nginx mviewerstudio geoserver postgresql logrotate.timer
sudo nginx -t
sudo logrotate --debug /etc/logrotate.conf
sudo tail -n 100 /srv/logs/geoserver/jetty.log
psql -h 127.0.0.1 -U usersig -d donneessig -W --command='SELECT PostGIS_Full_Version();'
```

| Élément | Explication |
|---|---|
| `/srv/logs/geoserver/jetty.log` | Journal console de GeoServer pour diagnostiquer Java et Jetty. |
| `-h 127.0.0.1` | Utilise une connexion TCP locale soumise aux règles `host` de `pg_hba.conf`. |
| `-U usersig` | Se connecte avec le compte SQL configuré dans `postgres_username`. |
| `-d donneessig` | Sélectionne la base configurée dans `postgres_database`. |
| `SELECT PostGIS_Full_Version();` | Retourne la version de PostGIS et de ses bibliothèques dans la base sélectionnée. |

- Adapter les identifiants si `secrets.vault.yml` a été personnalisé.

- Sauvegarder les données et secrets avant une mise à jour.

- Les anciens chemins d'une installation ne sont pas déplacés automatiquement : migrer leur contenu avant de changer les destinations.

<div class="ansible-section-anchor" id="install-updates"></div>

## Mettre à jour Mviewer

- Renseigner le tag, la branche ou le SHA souhaité dans `mviewer_version` de `site.yml`.

- Lancer :

```bash
ansible-playbook playbooks/upgrade_mviewer.yml -e @site.yml --ask-become-pass
```

| Élément | Explication |
|---|---|
| `playbooks/upgrade_mviewer.yml` | Déploie la référence Git demandée pour Mviewer en conservant les liens de données. |
| `mviewer_version` | Tag, branche ou SHA cible, défini dans `site.yml`. |
| `-e @site.yml` | Charge la version et les paramètres propres au site. |
| `--ask-become-pass` | Demande le mot de passe sudo utilisé pendant la mise à jour. |

Ce playbook conserve les liens partagés et leurs données et ne demande pas les secrets de Studio ou de PostgreSQL.
