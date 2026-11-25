---
title: "Dépannage Ansible"
description: "Diagnostiquer SSH, sudo, les services systemd, PostgreSQL et GeoServer dans le déploiement Ansible."
---

Cette page concerne l'installation native réalisée avec les rôles Ansible.

- Exécuter les commandes Ansible depuis `ansible/` sur le poste de contrôle.

- Exécuter les contrôles des services, des journaux et de PostgreSQL sur le serveur cible.

- Pour un déploiement Compose, consulter le [Dépannage Docker](/mviewer-galaxy/guides/depannage/).

## Vérifier la cible et les prérequis

Depuis `ansible/` sur le poste de contrôle :

```bash
ansible-inventory --graph
ansible-playbook playbooks/install.yml --tags check -e @site.yml --ask-become-pass
```

| Élément | Explication |
|---|---|
| `ansible-inventory --graph` | Affiche les groupes et les serveurs de l'inventaire chargé. |
| `--tags check` | Exécute uniquement les contrôles de prérequis. |
| `-e @site.yml` | Charge les paramètres personnalisés du site depuis le poste de contrôle. |
| `--ask-become-pass` | Demande le mot de passe sudo du compte SSH ; omettre si sudo est sans mot de passe. |

- Si SSH échoue, vérifier `ansible_host`, `ansible_port`, `ansible_user` et la clé privée dans l'inventaire.

- Tester la même connexion avec `ssh`.

- Si sudo échoue, contrôler les droits du compte SSH et utiliser `--ask-become-pass`.

- Le compte applicatif `mviewer` n'est pas le compte SSH du déploiement.

Une cible Docker destinée à tester ce playbook doit réellement exécuter systemd : le rôle `check` refuse une cible sans `/run/systemd/system`.

## Python ou Java 21 absent des dépôts

- Le contrôle exige Python 3.11+ et un paquet `openjdk-21-jre-headless` disponible dans APT.

- Le rôle peut installer Python s'il est disponible, mais n'ajoute pas de dépôt Java.

- Vérifier les dépôts de la cible et l'accès réseau sortant.

- Le mode `--check` complet nécessite Python déjà installé.

## Fichier Vault ou secrets manquants

- Les tâches de validation utilisent `no_log` ; un échec masqué peut indiquer une variable obligatoire absente.

- Ouvrir le fichier sur le poste de contrôle avec `ansible-vault edit secrets.vault.yml` et vérifier les valeurs nécessaires au rôle demandé.

| Exécution | Secrets applicatifs requis |
|---|---|
| Installation complète | `postgres_password`, `geoserver_admin_username`, `geoserver_admin_password`, `mviewerstudio_secret_key` (32 caractères minimum) |
| `--tags postgres` | `postgres_password` |
| `--tags geoserver` | `postgres_password`, `geoserver_admin_username`, `geoserver_admin_password` |
| `--tags check`, `upgrade_mviewer.yml` | Aucun secret applicatif |

- En mode `authlib`, l’installation complète exige aussi `mviewerstudio_oidc_client_secret`, l’identifiant client et l’URL de l’issuer.

- Charger le Vault avec `-e @secrets.vault.yml --ask-vault-pass`. Vérifier le chemin, les droits du fichier et le mot de passe Vault si le déchiffrement échoue.

- Le mot de passe Vault déchiffre le fichier ; il est distinct des mots de passe PostgreSQL, GeoServer et sudo. Si les mots de passe SSH/sudo sont dans le Vault, le charger aussi pour les contrôles ou mises à jour qui en ont besoin.

- Un mot de passe GeoServer absent est refusé avant l’installation des paquets, y compris avec `--check`. Renseigner les identifiants actuels du serveur ; le rôle ne fournit aucune valeur par défaut.

## Consulter les services et les journaux

Sur la cible :

```bash
sudo systemctl status nginx mviewerstudio geoserver postgresql logrotate.timer
sudo journalctl -u mviewerstudio -u geoserver -n 100 --no-pager
sudo tail -n 100 /srv/logs/nginx/error.log
sudo tail -n 100 /srv/logs/mviewerstudio/error.log
sudo tail -n 100 /srv/logs/geoserver/jetty.log
sudo nginx -t
```

| Élément | Explication |
|---|---|
| `/srv/logs/nginx/error.log` | Erreurs nginx et du proxy HTTP. |
| `/srv/logs/mviewerstudio/error.log` | Erreurs Gunicorn et de Studio. |
| `/srv/logs/geoserver/jetty.log` | Sortie console de Java et Jetty, utile pour les erreurs de démarrage GeoServer. |

- `journalctl` conserve notamment les événements de démarrage des unités.

- Les journaux applicatifs sont sous `/srv/logs/<application>/`.

## nginx renvoie 502

Tester les services locaux sur la cible :

```bash
curl -I http://127.0.0.1:5007/mviewerstudio/
curl -I http://127.0.0.1:8080/geoserver/web/
```

| Élément | Explication |
|---|---|
| `127.0.0.1` | Cible le service depuis le serveur lui-même, sans passer par le domaine public. |
| `5007/mviewerstudio/` | Port et préfixe internes de Studio à adapter si personnalisés. |
| `8080/geoserver/web/` | Port interne et interface web de GeoServer. |

- Adapter les ports et le préfixe s'ils ont été personnalisés.

- Vérifier que les services sont actifs et que nginx utilise les mêmes ports.

- Pour Studio, contrôler les permissions des répertoires partagés et de son journal :

```bash
sudo -u mviewer test -w /srv/data/mviewer/store
sudo -u mviewer test -w /srv/data/mviewer/public
sudo -u mviewer test -w /srv/logs/mviewerstudio
```

| Élément | Explication |
|---|---|
| `mviewer` | Compte applicatif utilisé pour ces contrôles ; adapter si `galaxy_user` est personnalisé. |
| `/srv/data/mviewer/store` | Dossier dans lequel Studio enregistre les cartes générées. |
| `/srv/data/mviewer/public` | Dossier dans lequel Studio publie les cartes. |
| `/srv/logs/mviewerstudio` | Dossier des journaux que Studio doit pouvoir écrire. |

Ces commandes doivent réussir avec le compte configuré dans `galaxy_user`.

## Connexion PostgreSQL refusée

```bash
sudo pg_lsclusters
psql -h 127.0.0.1 -U usersig -d donneessig -W --command='SELECT current_user;'
sudo ls /srv/logs/postgresql/
sudo -u postgres psql --dbname=postgres --command='SHOW listen_addresses;'
sudo -u postgres psql --dbname=postgres --command='SELECT line_number, error FROM pg_hba_file_rules WHERE error IS NOT NULL;'
```

| Élément | Explication |
|---|---|
| `sudo pg_lsclusters` | Affiche les versions, noms, ports, états et chemins des clusters PostgreSQL. |
| `-h 127.0.0.1` | Utilise une connexion TCP locale soumise aux règles `host` de `pg_hba.conf`. |
| `-U usersig` | Se connecte avec le compte SQL configuré dans `postgres_username`. |
| `-d donneessig` | Sélectionne la base configurée dans `postgres_database`. |
| `SELECT current_user;` | Affiche le compte SQL réellement connecté. |
| `/srv/logs/postgresql/` | Répertoire contenant les journaux des clusters PostgreSQL. |
| `postgres` | Compte Linux administrateur de PostgreSQL utilisé pour les contrôles locaux. |
| `--dbname=postgres` | Sélectionne la base d’administration locale pour les contrôles. |
| `SHOW listen_addresses;` | Affiche les interfaces d’écoute configurées ; le rôle prévoit `*`. |
| `pg_hba_file_rules` | Vue des règles d’accès ; cette requête affiche uniquement les lignes dont la syntaxe est invalide. |

- Adapter les identifiants et ajouter le port si nécessaire.

- Vérifier le mot de passe de `secrets.vault.yml`, les règles du template `pg_hba.conf.j2` et le pare-feu.

- Les clients autorisés doivent apparaître avant les règles `reject` : la première règle correspondante décide de l'accès.

- Après modification du template, rejouer le rôle pour le déployer.

- Une modification manuelle du fichier cible sera remplacée.

- La base et le schéma `public` appartiennent à l'utilisateur configuré.

- Cela ne réattribue pas les tables existantes appartenant à un autre utilisateur.

## Workspace ou entrepôt GeoServer non configuré

- Le rôle attend l'API REST et valide la connexion PostGIS.

- Une erreur HTTP 401 ou 403 indique notamment des identifiants administrateur à vérifier : `geoserver_admin_username` et `geoserver_admin_password` doivent correspondre au compte actuel de GeoServer.

- Pour une erreur de connexion PostGIS, vérifier que le rôle `postgres` a été exécuté, que la base contient PostGIS, que les identifiants du `secrets.vault.yml` sont corrects et que `pg_hba.conf` autorise l'adresse utilisée par GeoServer.

- Vérifier aussi `geoserver_postgres_host` et `geoserver_postgres_port`.

- Après changement du mot de passe SQL, relancer le déploiement complet pour actualiser les deux services.

- Lire `/srv/logs/geoserver/geoserver.log` et `jetty.log` pour le détail.

- Les tâches transportant les mots de passe sont masquées.

## URL HTTPS ou redirection OIDC incorrecte

- Comparer le domaine public, `galaxy_public_scheme`, le port et le préfixe Studio aux URL autorisées chez le fournisseur OIDC.

- Derrière un terminateur TLS, `galaxy_public_scheme` doit valoir `https`.

- Vérifier l'accès à l'issuer depuis la cible et les claims/groupes attendus par Studio.

## Requête GeoServer bloquée par CORS

- Comparer l'origine de la carte et l'URL du service : protocole, hôte et port doivent être pris en compte.

- Vérifier les requêtes `OPTIONS` et les en-têtes de la réponse dans les outils réseau du navigateur.

- Une erreur HTTP du service ou une redirection peut aussi être masquée par un message CORS.

Suivre la [section CORS de l'installation](/mviewer-galaxy/guides/installation-ansible/#install-cors).

## Rotation des journaux

```bash
sudo systemctl status logrotate.timer
sudo logrotate --debug /etc/logrotate.conf
```

| Élément | Explication |
|---|---|
| `logrotate.timer` | Unité systemd qui planifie la rotation quotidienne des journaux. |
| `/etc/logrotate.conf` | Configuration principale qui charge notamment les règles de `/etc/logrotate.d/`. |

- Le mode `--debug` vérifie les règles sans effectuer de rotation.

- Contrôler les propriétaires des répertoires de journaux si logrotate signale un problème de droits.

Voir aussi [Adapter à son environnement](/mviewer-galaxy/guides/ansible/environnement/).
