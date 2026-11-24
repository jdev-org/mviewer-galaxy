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
| `group_vars/all.yml` | Valeurs communes fournies par le dépôt |
| `roles/*/defaults/main.yml` | Valeurs par défaut propres aux rôles |
| `site.yml` | Paramètres propres au déploiement, chargés avec `-e @site.yml` |
| `.env` | Base SIG, utilisateur SQL et mot de passe |
| `secrets.vault.yml` | Clé de session Studio et secrets chiffrés par Ansible Vault |
| `roles/postgres/templates/pg_hba.conf.j2` | Règles d'accès PostgreSQL, à préparer avant l'installation |

- Les variables passées avec `-e` ont priorité sur les valeurs du playbook.

- Le fichier `.env` est lu sur le poste de contrôle et n'est pas exécuté par un shell.

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

- Nginx sert `/home/`, `/mviewer/`, `/mviewerstudio/` et `/geoserver/`.

- Studio et GeoServer écoutent localement par défaut.

- Derrière un terminateur TLS, utiliser `galaxy_public_scheme: https`.

- Cette variable n'installe pas de certificat.

## Base SIG et accès réseau

Configurer `.env`, ignoré par Git :

```dotenv
POSTGRES_DB=donneessig
POSTGRES_USER=usersig
POSTGRES_PASSWORD=
```

| Élément | Explication |
|---|---|
| `POSTGRES_DB` | Nom de la base SIG à créer ; `donneessig` est la valeur par défaut. |
| `POSTGRES_USER` | Compte SQL propriétaire de la base et du schéma `public` ; `usersig` est la valeur par défaut. |
| `POSTGRES_PASSWORD` | Mot de passe SQL obligatoire à renseigner ; ne pas laisser la valeur vide. |

- Renseigner le mot de passe.

- Les noms de base et d'utilisateur acceptent de 1 à 63 caractères minuscules, chiffres et underscores, sans chiffre initial.

- Les valeurs peuvent être entourées de guillemets.

- `$`, `%`, `#` et `=` restent littéraux.

- Écrire les commentaires sur leurs propres lignes.

- Pour choisir un autre fichier, définir `postgres_env_file` dans `site.yml` avec un chemin absolu sur le poste de contrôle.

- `postgres_port` et `postgres_socket_dir` ciblent le serveur PostgreSQL local à configurer.

- Les IP autorisées se définissent dans `pg_hba.conf.j2`.

- Le rôle remplace tout le fichier `pg_hba.conf` avec ce template : conserver l'administration locale et reporter les règles nécessaires.

- Ajouter les clients avant les règles `reject`.

- Le rôle configure `listen_addresses = '*'`.

- Le pare-feu reste à adapter aux accès souhaités.

- L'utilisateur SQL est propriétaire de la base et du schéma `public`.

- Modifier le mot de passe dans `.env`.

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

- Le rôle GeoServer crée le workspace par défaut et l'entrepôt connecté à la base de `.env`, sans publier de couche.

- Fournir le mot de passe administrateur actuel dans `geoserver_admin_password`, via Vault, s'il diffère de la valeur initiale `geoserver`.

- Le rôle utilise ce mot de passe sans le modifier.

- Studio exige toujours `mviewerstudio_secret_key`.

- Pour OIDC, définir `mviewerstudio_auth_mode: authlib`.

- Renseigner l'issuer, le client et son secret dans les variables `mviewerstudio_oidc_*`.

- Le callback doit correspondre au domaine, au schéma public et à `mviewerstudio_url_prefix`.

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

- Pour GeoServer, adapter ensemble `geoserver_version` et `geoserver_archive_checksum`.

- `logging_rotate` définit le nombre d'archives de journaux conservées (14 par défaut).
