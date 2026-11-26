---
title: "Adapter à son environnement"
description: "Personnaliser l'inventaire, les variables, PostgreSQL, GeoServer et les chemins du déploiement Ansible."
---

- Les commandes s'exécutent depuis `ansible/` pour charger `ansible.cfg` et ses modules locaux.

- Pour la procédure complète, voir [Installation](/mviewer-galaxy/guides/installation-ansible/).

## Choisir le bon fichier

| Fichier | Usage |
|---|---|
| `inventories/dev/hosts.ini` | Adresse SSH, compte avec sudo et clé privée |
| `group_vars/all/` | Un fichier par application et `common.yml` pour les valeurs partagées |
| `site.yml` | Paramètres propres au déploiement, chargés avec `-e @site.yml` |
| `secrets.vault.yml` | Identifiants PostgreSQL et GeoServer, clé Studio et secrets OIDC/SSH/sudo facultatifs |
| `roles/postgres/templates/pg_hba.conf.j2` | Règles d'accès PostgreSQL, à préparer avant l'installation |

- Les variables passées avec `-e` ont priorité sur les valeurs du playbook.

- Le fichier `secrets.vault.yml` est lu sur le poste de contrôle et n'est pas exécuté par un shell.

## Variables par application

| Fichier | Paramètres |
|---|---|
| `group_vars/all/common.yml` | Comptes système, chemins partagés, paquets communs et schéma public |
| `group_vars/all/mviewer.yml` | Dépôt et version Git, répertoires partagés apps/store/public |
| `group_vars/all/mviewerstudio.yml` | Dépôt et version Git, Gunicorn, chemins et paramètres OIDC publics |
| `group_vars/all/nginx.yml` | Nom du serveur public, port HTTP et journaux |
| `group_vars/all/postgres.yml` | Paquets, base et utilisateur par défaut, port, socket et template pg_hba |
| `group_vars/all/geoserver.yml` | Version, empreinte de l’archive, Java, chemins, ports et catalogue PostGIS |
| `group_vars/all/geoserver_extensions.yml` | Liste des extensions avec URL et empreintes SHA-256 |

- Les deux playbooks principaux chargent explicitement ces fichiers avec `vars_files`, y compris avec un autre inventaire.

- Conserver les adaptations du déploiement dans `site.yml`, chargé avec `-e @site.yml`. Ces variables remplacent les valeurs fournies ; si plusieurs fichiers `-e @…` définissent la même variable, le dernier a priorité.

- Seul le rôle réutilisable `logging` conserve ses valeurs internes dans `roles/logging/defaults/main.yml`.

## Connexion SSH et domaine public

```ini
[galaxy]
production ansible_host=serveur.example.org ansible_user=deploy ansible_port=22
```

| Élément | Explication |
|---|---|
| `[galaxy]` | Groupe de serveurs ciblé par les playbooks ; conserver ce nom. |
| `production` | Alias libre à personnaliser pour identifier le serveur dans Ansible. |
| `ansible_host` | Nom de domaine ou adresse IP du serveur cible, joignable depuis le poste de contrôle. |
| `ansible_user` | Compte SSH avec sudo qui réalisera l'installation ; `deploy` est un exemple à remplacer. |
| `ansible_port` | Port SSH de la cible ; ajouter cette variable si le port diffère de `22`. |
| `ansible_ssh_private_key_file` | Chemin de la clé privée sur le poste de contrôle, si une clé spécifique est nécessaire. |
| `--ask-become-pass` | Demande le mot de passe sudo du compte SSH. |

Le compte applicatif se configure séparément avec `galaxy_user` et `galaxy_group`, tous deux définis à `mviewer` par défaut.

Dans `site.yml`, le domaine public et les ports se configurent ainsi :

```yaml
nginx_server_name: cartes.example.org
nginx_http_port: 80
mviewerstudio_port: 5007
geoserver_port: 8080
galaxy_public_scheme: http
```

| Élément | Explication |
|---|---|
| `nginx_server_name` | Nom de domaine public du site ; remplacer `cartes.example.org` et configurer son DNS. |
| `nginx_http_port` | Port HTTP écouté par nginx sur la cible ; `80` par défaut. |
| `mviewerstudio_port` | Port interne de Gunicorn ; `5007` par défaut. |
| `geoserver_port` | Port interne de Jetty ; `8080` par défaut. |
| `galaxy_public_scheme` | Schéma public `http` ou `https` transmis aux applications par nginx. |

- Nginx sert `/accueil/`, `/header/`, `/catalogue/`, `/mviewer/`, `/mviewerstudio/` et `/geoserver/`.

- Studio et GeoServer écoutent localement par défaut.

- Derrière un terminateur TLS, utiliser `galaxy_public_scheme: https`.

- Cette variable n'installe pas de certificat.

## Un Vault pour les secrets des applications

| Variables | Usage obligatoire |
|---|---|
| `postgres_password` | PostgreSQL et GeoServer |
| `postgres_database`, `postgres_username` | Identifiants de la base partagés ; les valeurs par défaut de `postgres.yml` peuvent être remplacées dans le Vault |
| `geoserver_admin_username`, `geoserver_admin_password` | Accès REST GeoServer dès la première installation |
| `mviewerstudio_secret_key` | Déploiement complet ; au moins 32 caractères aléatoires, même en mode `public` |
| `mviewerstudio_oidc_client_secret` | Déploiement complet en mode `authlib`, avec l’issuer et l’identifiant client |
| `ansible_password`, `ansible_become_password` | Mots de passe SSH/sudo facultatifs si la connexion en a besoin |

- Copier `secrets.example.yml` une seule fois, renseigner les valeurs requises puis chiffrer avec `ansible-vault encrypt secrets.vault.yml`.

- Pour les modifications suivantes, utiliser `ansible-vault edit secrets.vault.yml` en conservant les secrets et identifiants de base existants.

- Charger explicitement avec `-e @secrets.vault.yml --ask-vault-pass`. Le suffixe `.vault.yml` ne chiffre pas le fichier et ne provoque pas son chargement automatique.

- Pour plusieurs environnements, utiliser des Vaults distincts et sélectionner l’inventaire et le Vault correspondants au déploiement.

- Les tâches contenant des secrets utilisent `no_log`. Le rendu de l’environnement Studio désactive aussi `--diff` et écrit un fichier `0600` réservé à root dans `/etc/mviewerstudio/` (`0700`). Le chiffrement Vault protège le fichier source sur le poste de contrôle.

## Base SIG et accès réseau

Copier `secrets.example.yml` vers `secrets.vault.yml` s'il n'existe pas, puis renseigner les identifiants SIG avant chiffrement. Utiliser `ansible-vault edit secrets.vault.yml` si le fichier est déjà chiffré :

```yaml
postgres_database: donneessig
postgres_username: usersig
postgres_password: ""
```

| Élément | Explication |
|---|---|
| `postgres_database` | Base SIG à réutiliser si elle existe, ou à créer sinon ; `donneessig` est la valeur par défaut. |
| `postgres_username` | Compte SQL propriétaire de la base et du schéma `public` ; `usersig` est la valeur par défaut. |
| `postgres_password` | Mot de passe SQL obligatoire à renseigner ; ne pas laisser la valeur vide. |

- Renseigner le mot de passe.

- Les noms de base et d'utilisateur acceptent de 1 à 63 caractères minuscules, chiffres et underscores, sans chiffre initial.

- Les valeurs peuvent être entourées de guillemets.

- `$`, `%`, `#` et `=` restent littéraux.

- Respecter la syntaxe YAML ; utiliser des guillemets simples pour les chaînes littérales contenant des caractères spéciaux et doubler les apostrophes internes.

- Chiffrer avec `ansible-vault encrypt secrets.vault.yml`, puis charger avec `-e @secrets.vault.yml --ask-vault-pass`. Modifier avec `ansible-vault edit secrets.vault.yml`.

- `postgres_port` et `postgres_socket_dir` ciblent le serveur PostgreSQL local à configurer.

- Définir `postgres_install: false` dans `site.yml` pour réutiliser PostgreSQL/PostGIS déjà installés sur la cible, sans installer leurs paquets. La valeur par défaut est `true`. Un cluster absent bloque le déploiement, même en simulation. Les contrôles de version, la création ou réutilisation de la base, les identifiants SQL, les journaux et les accès réseau restent gérés par Ansible. Le tag `check` exclut les paquets PostgreSQL/PostGIS de son contrôle APT lorsque cette option est désactivée.

- Avant d’installer les paquets, le rôle détecte un cluster sur `postgres_port` et conserve sa version majeure. Seul ce cluster est démarré et configuré ; un port ne correspondant à aucun cluster existant bloque le déploiement.

- Les versions minimales sont `postgres_minimum_version: 14` et `postgres_minimum_postgis_version: 3`, configurables dans `site.yml`. Les versions sont vérifiées avant toute écriture SQL. Une version incompatible bloque le déploiement sans migration ni mise à niveau automatique de l’extension. La base existante est réutilisée ; PostGIS est activé seulement s’il est absent. Les identifiants SQL et les propriétaires de la base et du schéma restent alignés sur la configuration.

- Définir `postgres_allowed_clients` dans `site.yml` : liste des IP/réseaux clients au format CIDR, par exemple `[192.0.2.10/32, 10.0.0.0/24]`. La valeur par défaut est `[]` (aucun client distant).

- Le rôle remplace tout le fichier `pg_hba.conf` avec ce template : conserver l'administration locale et reporter les règles nécessaires.

- Le template par défaut insère ces clients avant les règles `reject` pour la base et l’utilisateur SIG. Un template personnalisé doit gérer lui-même `postgres_allowed_clients`.

- Définir `postgres_listen_addresses` avec les interfaces du serveur, par exemple `['127.0.0.1', '::1', '192.0.2.20']`. Ce sont les adresses du serveur, pas les IP clientes. La valeur par défaut est `['127.0.0.1', '::1']` (interfaces locales uniquement). Conserver la boucle locale si GeoServer l’utilise ; un changement d’interfaces redémarre le cluster concerné.

- Le pare-feu reste à adapter aux accès souhaités.

- L'utilisateur SQL est propriétaire de la base et du schéma `public`.

- Modifier le mot de passe avec `ansible-vault edit secrets.vault.yml`.

- Rejouer le déploiement complet pour mettre à jour PostgreSQL et GeoServer.

- Changer un nom de base ne migre pas les données de l'ancienne base.

- Les tables existantes conservent leurs propres propriétaires.

## GeoServer et Studio

```yaml
geoserver_workspace: donnessig
geoserver_datastore: postgis
geoserver_postgres_host: 127.0.0.1
geoserver_postgres_port: 5432
mviewerstudio_auth_mode: public
```

| Élément | Explication |
|---|---|
| `geoserver_workspace` | Nom du workspace GeoServer créé et défini par défaut : `donnessig` dans cet exemple. |
| `geoserver_datastore` | Nom de l'entrepôt PostGIS dans le workspace : `postgis` dans cet exemple. |
| `geoserver_postgres_host` | Adresse de PostgreSQL vue depuis GeoServer ; `127.0.0.1` pour la base locale. |
| `geoserver_postgres_port` | Port SQL utilisé par l’entrepôt GeoServer ; doit correspondre à celui du serveur PostgreSQL. |
| `mviewerstudio_auth_mode` | `public` autorise un accès sans connexion ; `authlib` active OIDC. |

- Le rôle GeoServer crée le workspace par défaut et l'entrepôt connecté à la base de `secrets.vault.yml`, sans publier de couche.

- Fournir `geoserver_admin_username` et `geoserver_admin_password` dans le Vault dès la première installation. Utiliser les identifiants actuels du serveur, puis mettre à jour le Vault après tout changement dans GeoServer.

- Le rôle utilise ce mot de passe sans le modifier.

- Studio exige toujours `mviewerstudio_secret_key`.

- Pour OIDC, définir `mviewerstudio_auth_mode: authlib`.

- Renseigner l'issuer, le client et son secret dans les variables `mviewerstudio_oidc_*`.

- Le callback doit correspondre au domaine, au schéma public et à `mviewerstudio_url_prefix`.

## Installer sans portail d’accueil

Définir cette option dans `site.yml`, chargé avec `-e @site.yml` :

```yaml
galaxy_home_enabled: false
```

La valeur par défaut est `true`. Quand l’option est désactivée, Ansible ignore
la copie de l’accueil, de l’en-tête partagé, du catalogue et de la carte de
repli. nginx redirige `/` vers `/mviewer/`, et Studio utilise le même retour.

Sur une installation existante, rejouer le déploiement complet avec cette
option pour adapter nginx et l’environnement Studio. Les fichiers statiques
existants sont conservés sur disque mais ne sont plus exposés. `update_home.yml`
ignore la copie lorsque l’option est désactivée ; il ne modifie pas les routes nginx.

## Accueil, en-tête et catalogue

Ansible copie les répertoires locaux `home/`, `header/` et `catalogue/` sur la
cible. Les conserver à côté de `ansible/` dans la copie du dépôt sur le poste
de contrôle. Le rôle `nginx` conserve leur contenu sans interpréter le
JavaScript ou les templates Mustache comme du Jinja.

| Source locale | Variable du répertoire cible | URL publique |
|---|---|---|
| `home/` | `galaxy_home_dir` | `/accueil/` (la racine publique y redirige) |
| `header/` | `galaxy_header_dir` | `/header/` |
| `catalogue/` | `galaxy_catalogue_dir` | `/catalogue/` |

- Modifier `header/config.js` pour l’identité et la navigation, `home/config.js` pour l’image d’accueil et `catalogue/data.json` pour les cartes et leurs favoris.

- Quand le catalogue est vide, l’accueil pointe vers `/apps/default.xml`. Le rôle `nginx` le copie depuis `resources/mviewer/apps/default.xml` uniquement s’il est absent. Une carte existante est conservée ; `mviewer_default_map_source` permet de fournir un autre exemple initial.

- Pour utiliser d’autres sources locales, définir `galaxy_home_source_dir`, `galaxy_header_source_dir` et `galaxy_catalogue_source_dir` dans `site.yml`.

- Sur un serveur installé, lancer `ansible-playbook playbooks/update_home.yml -e @site.yml --ask-become-pass` pour actualiser l’accueil, l’en-tête et le catalogue. Omettre le fichier de site s’il n’existe pas ; charger le Vault seulement si les mots de passe de connexion l’exigent. Ajouter `--check --diff` pour prévisualiser les changements.

- Ce playbook copie seulement les fichiers statiques, sans redémarrer les services. Recharger la page pour voir les changements. Utiliser `playbooks/install.yml --tags nginx` si les routes ou la configuration nginx doivent aussi être actualisées.

- Le lien Studio pointe directement vers `/mviewerstudio/`. Si son préfixe est personnalisé, adapter `header/config.js`, `home/index.html` et `catalogue/index.html`. Les routes `/portal/login`, `/portal/logout` et `/portal/session` utilisent le préfixe Studio configuré.

- Pour OIDC, autoriser le retour après déconnexion vers l’URL publique `https://votre-domaine/accueil/`. Un déploiement complet adapte l’environnement Studio pour renvoyer les visiteurs anonymes à l’accueil.

## Ajouter ou mettre à jour les extensions GeoServer

### Préparer une archive avec extensions avant le transfert

Cette étape s’exécute sur le poste de contrôle, sans sudo ni secrets applicatifs.
Elle nécessite Python 3.11+, Ansible et l’outil `unzip` sur ce poste. Depuis
`ansible/`, après avoir choisi les extensions dans
`group_vars/all/geoserver_extensions.yml` :

```bash
ansible-playbook playbooks/prepare_geoserver.yml
```

Ajouter `-e @site.yml` si la version, les sources ou les chemins y sont définis.
Le playbook télécharge les archives officielles, vérifie les empreintes SHA-256,
contrôle les conflits de JAR puis produit une archive avec les extensions et un
manifeste. Les exclusions `exclude_jars` sont respectées. Le répertoire temporaire
est supprimé, même en cas d’échec. La préparation ne prend pas en charge `--check`.

La sortie par défaut est `ansible/artifacts/geoserver/geoserver-3.0.2-bundle.zip`
(pour la version 3.0.2), ignorée par Git. `geoserver_bundle_dir` configure le cache
et `geoserver_bundle_archive` le fichier produit. Ajouter ensuite dans `site.yml`
le chemin absolu de cette archive sur le poste de contrôle :

```yaml
geoserver_local_archive: /chemin/mviewer-galaxy/ansible/artifacts/geoserver/geoserver-3.0.2-bundle.zip
```

Lancer ensuite l’installation habituelle avec `-e @site.yml` et le Vault.
La version et la sélection d’extensions doivent être identiques à celles de la
préparation. Le manifeste est vérifié avant installation ; le transfert est
contrôlé par SHA-256. Les outils système requis par les extensions sont installés
sur la cible. L’installation ne télécharge et n’ajoute aucune extension séparément.

Sans `geoserver_local_archive`, l’installation utilise la distribution officielle
sans ajout d’extensions. Une archive préparée sert à une première installation :
une distribution existante issue d’une autre archive n’est pas remplacée.
Pour ajouter des extensions après installation, lancer manuellement :

```bash
ansible-playbook playbooks/geoserver_extensions.yml -e @site.yml --ask-become-pass
```

Ce playbook reste indépendant de `install.yml`. Pour une nouvelle version de la
sélection, modifier sa liste et ses empreintes avant de l’exécuter. Aucun secret
applicatif n’est nécessaire, sauf si le Vault contient les accès SSH/sudo.

### Modifier la liste des extensions

Ouvrir `group_vars/all/geoserver_extensions.yml`. Ce fichier contient la version
ciblée et, pour chaque extension, son nom, son URL HTTPS et son empreinte SHA-256.
Les extensions sont intégrées à une archive préparée sur le poste de contrôle,
ou ajoutées ensuite avec le playbook dédié lancé manuellement.

| Fonction | Identifiant d'extension |
|---|---|
| OGC API Features | `ogcapi-features` |
| Service SLD | `sldservice` |
| Sorties DXF, Excel, GeoPackage, KML/KMZ | `dxf`, `excel`, `geopkg-output`, `kml` |
| Sorties OGR et tuiles vectorielles | `ogr-wfs`, `vectortiles` |
| Couverture Image Pyramid | `pyramid` |
| Import de données | `importer` |
| Styles YSLD, CSS et Chart Symbolizer | `ysld`, `css`, `charts` |
| Filtrage entre couches | `querylayer` |

La sélection comporte 14 extensions. L'extension raster GDAL n'est pas incluse.
Les sorties DXF, Excel et OGR concernent WFS ; WPS n'est pas installé.
L'entrée DXF exclut son JAR WPS facultatif avec `exclude_jars`, conformément
aux [instructions d'installation DXF](https://docs.geoserver.org/stable/en/user/extensions/dxf/).

OGR nécessite `gdal-bin` pour la commande `ogr2ogr`. Image Pyramid ajoute
`python3-gdal` pour l'outil de préparation `gdal_retile.py`. Ces paquets sont
installés selon la sélection lorsque l’archive préparée est utilisée ou lors
du lancement manuel du playbook des extensions.
Aucune liaison Java/JNI GDAL n'est nécessaire pour cette sélection.

Pour une extension supplémentaire, ajouter une entrée à la liste. Voici
l'entrée CSS déjà fournie :

```yaml
  - name: css
    url: https://downloads.sourceforge.net/project/geoserver/GeoServer/3.0.2/extensions/geoserver-3.0.2-css-plugin.zip
    checksum: sha256:fd067a425f883f9aafbeb555c5f0033daa45e55652df7ea53d2700cea68e402d
```

Utiliser une archive correspondant exactement à `geoserver_version` et calculer
son SHA-256 depuis le fichier téléchargé :

```bash
sha256sum geoserver-3.0.2-css-plugin.zip
```

La version et les archives sont référencées sur la
[page officielle GeoServer](https://geoserver.org/release/3.0.2/).

### Appliquer les changements sur un GeoServer installé

Depuis `ansible/` sur le poste de contrôle, simuler puis appliquer :

```bash
ansible-playbook playbooks/geoserver_extensions.yml -e @site.yml --ask-become-pass --check --diff
ansible-playbook playbooks/geoserver_extensions.yml -e @site.yml --ask-become-pass
```

Omettre `-e @site.yml` si ce fichier n'existe pas. Ce playbook ne demande aucun
secret applicatif et ne rejoue pas PostgreSQL, Studio ou la configuration du
catalogue. Si les mots de passe SSH/sudo sont dans le Vault, ajouter
`-e @secrets.vault.yml --ask-vault-pass`.

Le rôle dédié `geoserver_extensions` vérifie les empreintes et les bibliothèques
partagées avant de modifier le service. Il arrête GeoServer si des JAR changent,
installe uniquement les fichiers nouveaux ou modifiés, puis redémarre le service
et attend le retour de l'interface. Un second passage sans modification ne
redémarre pas GeoServer.

En simulation, les archives absentes du cache sont signalées sans téléchargement :
leur contenu sera vérifié lors de l'exécution réelle.

Le rôle installe et met à jour les extensions de la liste. Retirer une entrée
ne supprime pas ses JAR déjà installés, car certaines bibliothèques sont partagées.

### Vérifier l'installation

Ouvrir `http://<serveur>/geoserver/web/`, puis consulter l'état des modules.
Vérifier les formats de sortie dans les capacités WFS/WMS, les styles et l'option
Image Pyramid lors de la création d'un entrepôt raster. OGC API Features est
accessible sous `/geoserver/ogc/features/v1`.

## Chemins et versions

| Variable | Valeur par défaut | Utilité |
|---|---|---|
| `galaxy_install_dir` | `/var/www/mviewergalaxy` | Racine du site contenant l'accueil et les sources Mviewer |
| `mviewerstudio_install_dir` | `/srv/apps/mviewerstudio` | Sources de Studio et son virtualenv Python |
| `mviewer_apps_dir` | `/srv/data/mviewer/apps` | Configurations des cartes Mviewer |
| `mviewer_store_dir` | `/srv/data/mviewer/store` | Cartes enregistrées par Studio |
| `mviewer_public_dir` | `/srv/data/mviewer/public` | Cartes publiées par Studio |
| `geoserver_data_dir` | `/srv/data/geoserver/datadir` | Catalogue, données et configuration de sécurité GeoServer |
| `galaxy_logs_dir` | `/srv/logs` | Racine des journaux, avec un dossier par application |

- Les liens Mviewer, nginx et les permissions de Studio suivent ces variables.

- Sauvegarder les répertoires de données existants.

- Déplacer les données existantes avant de changer leur chemin : le playbook ne les migre pas automatiquement.

- Figer `mviewer_version` et `mviewerstudio_version` sur des tags ou SHA pour reproduire un déploiement.

- Pour GeoServer, adapter ensemble `geoserver_version`, `geoserver_archive_checksum`, la version des extensions, leurs URL et leurs empreintes.

- `logging_rotate` définit le nombre d'archives de journaux conservées (14 par défaut).

## Exécuter un rôle seul ou une mise à jour

```bash
ansible-playbook playbooks/install.yml --tags check -e @site.yml --ask-become-pass
ansible-playbook playbooks/install.yml --tags postgres -e @site.yml -e @secrets.vault.yml --ask-vault-pass --ask-become-pass
ansible-playbook playbooks/install.yml --tags geoserver -e @site.yml -e @secrets.vault.yml --ask-vault-pass --ask-become-pass
ansible-playbook playbooks/upgrade_mviewer.yml -e @site.yml --ask-become-pass
```

- Omettre `-e @site.yml` si aucun fichier de site n’a été créé, et `--ask-become-pass` si sudo ne demande pas de mot de passe.

- Les tags `postgres` et `geoserver` n’exigent pas les secrets Studio. GeoServer a besoin d’une base PostGIS existante ; exécuter `postgres` au préalable si nécessaire.

- Les contrôles et la mise à jour Mviewer ne demandent aucun secret applicatif ; charger le Vault s’il contient les mots de passe SSH/sudo nécessaires à la connexion.
