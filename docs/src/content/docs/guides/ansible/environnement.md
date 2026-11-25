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

- Les deux playbooks chargent explicitement ces six fichiers avec `vars_files`, y compris avec un autre inventaire.

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

- Nginx sert `/home/`, `/mviewer/`, `/mviewerstudio/` et `/geoserver/`.

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
| `postgres_database` | Nom de la base SIG à créer ; `donneessig` est la valeur par défaut. |
| `postgres_username` | Compte SQL propriétaire de la base et du schéma `public` ; `usersig` est la valeur par défaut. |
| `postgres_password` | Mot de passe SQL obligatoire à renseigner ; ne pas laisser la valeur vide. |

- Renseigner le mot de passe.

- Les noms de base et d'utilisateur acceptent de 1 à 63 caractères minuscules, chiffres et underscores, sans chiffre initial.

- Les valeurs peuvent être entourées de guillemets.

- `$`, `%`, `#` et `=` restent littéraux.

- Respecter la syntaxe YAML ; utiliser des guillemets simples pour les chaînes littérales contenant des caractères spéciaux et doubler les apostrophes internes.

- Chiffrer avec `ansible-vault encrypt secrets.vault.yml`, puis charger avec `-e @secrets.vault.yml --ask-vault-pass`. Modifier avec `ansible-vault edit secrets.vault.yml`.

- `postgres_port` et `postgres_socket_dir` ciblent le serveur PostgreSQL local à configurer.

- Les IP autorisées se définissent dans `pg_hba.conf.j2`.

- Le rôle remplace tout le fichier `pg_hba.conf` avec ce template : conserver l'administration locale et reporter les règles nécessaires.

- Ajouter les clients avant les règles `reject`.

- Le rôle configure `listen_addresses = '*'`.

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

## Migrer une installation existante

| Ancienne configuration | Configuration actuelle |
|---|---|
| `group_vars/all.yml` | `group_vars/all/common.yml` et un fichier par application |
| `roles/postgres/defaults/main.yml` | `group_vars/all/postgres.yml` |
| `roles/geoserver/defaults/main.yml` | `group_vars/all/geoserver.yml` |
| `.env` : `POSTGRES_DB` | Vault : `postgres_database` |
| `.env` : `POSTGRES_USER` | Vault : `postgres_username` |
| `.env` : `POSTGRES_PASSWORD` | Vault : `postgres_password` |
| `postgres_env_file`, `geoserver_postgres_env_file` | Supprimés ; charger le Vault avec `-e @secrets.vault.yml --ask-vault-pass` |

- Reporter les adaptations existantes dans `site.yml` et les identifiants dans le Vault avant le déploiement.

- Conserver les noms de base et d’utilisateur ainsi que la clé de session Studio. Changer les identifiants de base crée des ressources sans migrer les données ; changer la clé invalide les sessions existantes.

- Fournir les identifiants actuels de l’administrateur GeoServer : le rôle ne fournit plus de mot de passe par défaut et ne change pas celui du serveur.

- Rejouer le déploiement complet avec le Vault, valider les services puis supprimer l’ancien `.env` local.
