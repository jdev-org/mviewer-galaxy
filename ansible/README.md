# Installer Mviewer Galaxy avec Ansible

Suivre les étapes ci-dessous pour installer PostgreSQL/PostGIS, GeoServer,
Mviewer, Mviewer Studio et nginx sur un serveur Debian ou Ubuntu avec systemd.
Studio est accessible sans authentification par défaut ; l'étape 6 permet
l'activation d'OIDC avec un fournisseur externe. Le playbook n'installe ni
Docker ni Keycloak.

Pour une installation existante, commencer par [migrer la configuration](#migrer-une-ancienne-configuration).

## 1. Vérifier les prérequis

Préparer le poste de contrôle et le serveur cible :

| Emplacement | Prérequis |
|---|---|
| Poste de contrôle | Ansible Core 2.16+ |
| Serveur cible | Debian 12+ ou Ubuntu 22.04+, avec systemd actif |
| Connexion | Accès SSH avec root ou un compte disposant de sudo |
| Python sur la cible | Python 3.11+ installé ou disponible dans les dépôts APT |
| Java sur la cible | Paquet `openjdk-21-jre-headless` disponible dans APT |
| Accès réseau de la cible | Dépôts Git, APT et Python, SourceForge et ses miroirs |

Le rôle `common` installe Python s'il est absent. Aucune collection Ansible
externe ni bibliothèque Python PostgreSQL supplémentaire n'est nécessaire.

Vérifier en particulier la disponibilité de Java 21 : certaines versions
ciblées, dont Debian 12, nécessitent un dépôt adapté. Le rôle n'ajoute pas de
dépôt APT. Sur Ubuntu, le dépôt `universe` doit être disponible pour PostGIS.

Depuis la racine du dépôt, ouvrir le répertoire Ansible :

```bash
cd ansible
ansible --version
```

**Exécuter toutes les commandes Ansible de ce guide depuis `ansible/`**, afin de
charger `ansible.cfg`, les rôles et les modules locaux. Les commandes de contrôle
des services seront à exécuter sur le serveur cible.

## 2. Renseigner le serveur dans l'inventaire

Modifier `inventories/dev/hosts.ini` avec les paramètres de la cible :

```ini
[galaxy]
production ansible_host=192.0.2.10 ansible_user=deploy
```

| Paramètre | Valeur à renseigner |
|---|---|
| `[galaxy]` | Conserver ce groupe, ciblé par les playbooks |
| `production` | Alias libre pour identifier le serveur |
| `ansible_host` | Remplacer `192.0.2.10` par l'adresse IP ou le domaine de la cible |
| `ansible_user` | Remplacer `deploy` par le compte SSH disposant de sudo |
| `ansible_port` | Ajouter ce paramètre si SSH n'écoute pas sur le port 22 |
| `ansible_ssh_private_key_file` | Ajouter le chemin de la clé privée si nécessaire |

Vérifier que le serveur apparaît dans le groupe `galaxy` :

```bash
ansible-inventory --graph
```

Pour utiliser un inventaire distinct, créer par exemple
`inventories/production/hosts.ini`, puis ajouter
`-i inventories/production/hosts.ini` à chaque commande Ansible du guide.

## 3. Créer la configuration du site

Créer `site.yml` dans le répertoire `ansible/` :

```yaml
nginx_server_name: cartes.example.org
nginx_http_port: 80
galaxy_public_scheme: http
mviewerstudio_auth_mode: public
# Remplacer ces branches par des tags ou SHA pour figer le déploiement.
mviewer_version: master
mviewerstudio_version: oauth2-proxy-keycloak
```

Remplacer `cartes.example.org` par le domaine public du site et faire pointer
son DNS vers le serveur. Adapter le port HTTP si un autre service utilise déjà
le port 80.

Pour une URL publique HTTPS, configurer un terminateur TLS devant nginx et
mettre `galaxy_public_scheme: https`. Cette variable adapte les URL et les
en-têtes transmis aux applications ; elle ne configure ni certificat ni écoute
TLS. Restreindre alors l'accès HTTP au proxy de confiance.

Pour personnaliser d'autres paramètres, consulter les fichiers suivants puis
reporter les valeurs souhaitées dans `site.yml` :

| Fichier | Paramètres disponibles |
|---|---|
| `group_vars/all/common.yml` | Comptes système, chemins partagés, paquets communs, schéma public |
| `group_vars/all/mviewer.yml` | Dépôt et version Git, répertoires apps/store/public |
| `group_vars/all/mviewerstudio.yml` | Dépôt et version Git, Gunicorn, chemins, paramètres OIDC publics |
| `group_vars/all/nginx.yml` | Nom du serveur, port HTTP, journaux |
| `group_vars/all/postgres.yml` | Paquets, base et utilisateur par défaut, port, socket, template pg_hba |
| `group_vars/all/geoserver.yml` | Version, empreinte de l'archive, Java, chemins, ports, catalogue PostGIS |

Les deux playbooks chargent explicitement ces six fichiers, même avec un autre
inventaire. Les valeurs de `-e @site.yml` les remplacent. Si plusieurs fichiers
`-e @…` définissent une même variable, le dernier a priorité.

Les sources sont clonées sur la cible depuis les dépôts configurés. Les
modifications locales des sous-modules ne sont pas transférées.

## 4. Préparer les accès PostgreSQL

Ouvrir `roles/postgres/templates/pg_hba.conf.j2` avant le déploiement.
Conserver les règles d'administration locale et celles utilisées par GeoServer.
Si des clients distants doivent accéder à PostgreSQL, ajouter leurs IP ou
réseaux **avant les lignes `reject`**, par exemple :

```text
host "{{ postgres_configuration.database }}" "{{ postgres_configuration.username }}" 192.0.2.10/32 scram-sha-256
```

Remplacer `192.0.2.10/32` par l'adresse du client autorisé. Conserver les variables
Jinja : elles reprennent les noms de base et d'utilisateur validés par le rôle.

Le template remplace entièrement le `pg_hba.conf` du serveur sélectionné par
`postgres_port` : reporter les règles nécessaires d'une installation existante.
Pour utiliser un autre template, définir `postgres_hba_template` dans `site.yml`.

Le rôle configure `listen_addresses = '*'`. Adapter le pare-feu pour autoriser
les connexions souhaitées au port PostgreSQL, **5432** par défaut. Les changements
d'écoute entraînent le redémarrage du cluster actif concerné ; les règles
`pg_hba.conf` sont validées puis rechargées.

## 5. Renseigner et chiffrer les secrets

### Créer le fichier une seule fois

Pour une nouvelle installation :

```bash
cp secrets.example.yml secrets.vault.yml
chmod 600 secrets.vault.yml
```

Si le Vault existe déjà, conserver son contenu et l'ouvrir avec
`ansible-vault edit secrets.vault.yml`.

### Renseigner les valeurs obligatoires

Générer une clé de session Studio sur le poste de contrôle :

```bash
python3 -c 'import secrets; print(secrets.token_hex(32))'
```

Ouvrir `secrets.vault.yml` dans l'éditeur et compléter les valeurs :

| Variable | Valeur à renseigner |
|---|---|
| `postgres_database` | Base SIG à créer ; `donneessig` par défaut |
| `postgres_username` | Propriétaire SQL de la base et du schéma `public` ; `usersig` par défaut |
| `postgres_password` | Mot de passe SQL non vide, partagé avec GeoServer |
| `geoserver_admin_username` | Compte administrateur REST actuel de GeoServer |
| `geoserver_admin_password` | Mot de passe actuel de ce compte, obligatoire dès la première installation |
| `mviewerstudio_secret_key` | Clé générée ci-dessus, d'au moins 32 caractères, requise même en mode `public` |

Pour une distribution GeoServer vierge, renseigner ses identifiants initiaux
`admin` / `geoserver`. Pour un serveur existant, utiliser ses identifiants
actuels. Le rôle utilise ce compte sans changer son mot de passe.

Les noms PostgreSQL acceptent de 1 à 63 caractères minuscules, chiffres et
underscores, sans chiffre initial. Les mots de passe suivent la syntaxe YAML
et sont transmis sans interprétation shell. Les comptes SQL sont distincts
des comptes Linux et SSH.

Si la connexion exige des mots de passe SSH ou sudo, les variables facultatives
`ansible_password` et `ansible_become_password` peuvent également être placées
dans le Vault. Conserver les clés SSH sur le poste de contrôle.

### Chiffrer le fichier complété

Après avoir enregistré les vraies valeurs :

```bash
ansible-vault encrypt secrets.vault.yml
```

Choisir et conserver le mot de passe Vault : il sert à déchiffrer le fichier et
est distinct des mots de passe des services et de sudo. Pour toute modification
ultérieure :

```bash
ansible-vault edit secrets.vault.yml
```

Les fichiers `*.vault.yml` sont ignorés par Git. Le suffixe ne chiffre pas le
fichier et ne le charge pas automatiquement : les commandes de déploiement
utiliseront `-e @secrets.vault.yml --ask-vault-pass`.

Les tâches sensibles utilisent `no_log`. Sur la cible, Studio reçoit ses secrets
via `/etc/mviewerstudio/environment`, réservé à root (`0600` dans un répertoire
`0700`), dont le rendu est également exclu de `--diff`. Le Vault protège le
fichier source sur le poste de contrôle ; les services utilisent leurs propres
mécanismes de stockage sur la cible.

## 6. Activer OIDC si nécessaire

Pour conserver Studio sans authentification, laisser
`mviewerstudio_auth_mode: public` et passer à l'étape 7.

Pour activer OIDC, modifier `site.yml` :

```yaml
mviewerstudio_auth_mode: authlib
```

Ouvrir le Vault avec `ansible-vault edit secrets.vault.yml`, puis renseigner
`mviewerstudio_oidc_issuer` et `mviewerstudio_oidc_client_secret`. Le client utilise
`mviewerstudio_oidc_client_id: mviewerstudio` par défaut ; adapter cette valeur si
nécessaire. Les paramètres OIDC ne sont vérifiés et écrits qu'en mode `authlib`.

Configurer le fournisseur externe, par exemple Keycloak :

| Paramètre | Configuration attendue |
|---|---|
| Client | Client confidentiel `mviewerstudio`, avec le secret renseigné dans le Vault |
| Callback | `https://cartes.example.org/mviewerstudio/auth/callback`, à adapter au domaine, au schéma et au préfixe |
| Déconnexion | Autoriser les URL de retour vers Mviewer |
| Accès utilisateur | Groupe `MVIEWER_ACCESS` par défaut |
| Organisation | Claim attendu par `mviewerstudio_oidc_claims_mapping` |

Vérifier que l'issuer et son endpoint de découverte sont accessibles depuis
la cible. Les groupes, claims et scopes sont configurables avec les variables
`mviewerstudio_oidc_*`.

## 7. Contrôler la cible avant l'installation

Depuis le poste de contrôle :

```bash
ansible-playbook playbooks/install.yml --syntax-check
ansible-playbook playbooks/install.yml --tags check -e @site.yml --ask-become-pass
```

Le contrôle vérifie les droits root/sudo, le système et systemd, Python, les
paquets APT (dont Java 21, PostgreSQL/PostGIS et logrotate) et l'accès aux dépôts
Git. Si Git est absent, sa vérification est différée après son installation par
`common`, avant le clonage.

Le tag `check` fonctionne sans Python installé et ne demande aucun secret
applicatif. Si les mots de passe SSH/sudo sont dans le Vault, ajouter
`-e @secrets.vault.yml --ask-vault-pass` à la commande de contrôle.

Attendre un résultat sans échec avant de poursuivre. Le contrôle ne modifie pas
l'état installé ni les caches APT : les téléchargements utilisent un répertoire
temporaire supprimé en fin d'exécution. Les vérifications réseau sont rejouées
à chaque passage, y compris avec `--check`, et restent à `changed=0`. Les paquets
déjà satisfaits ne sont pas téléchargés à nouveau.

## 8. Simuler puis déployer

### Simuler les changements

Si Python est déjà installé sur la cible :

```bash
ansible-playbook playbooks/install.yml -e @site.yml -e @secrets.vault.yml --ask-vault-pass --ask-become-pass --check --diff
```

La simulation ignore notamment les installations pip, le provisionnement SQL
et les actions sur les services. Pour GeoServer, elle ignore l'extraction,
l'initialisation des données et le rendu du service. Elle ne valide ni le
démarrage des applications ni leurs dépendances Python.

Si Python est absent, utiliser le contrôle de l'étape 7, puis lancer directement
le déploiement pour permettre son installation.

### Appliquer le déploiement

```bash
ansible-playbook playbooks/install.yml -e @site.yml -e @secrets.vault.yml --ask-vault-pass --ask-become-pass
```

| Option | Usage |
|---|---|
| `-e @site.yml` | Charger les paramètres du site |
| `-e @secrets.vault.yml` | Charger les secrets chiffrés |
| `--ask-vault-pass` | Demander le mot de passe de déchiffrement Vault |
| `--ask-become-pass` | Demander le mot de passe sudo ; omettre si sudo n'en exige pas ou s'il est fourni dans le Vault |
| `--check --diff` | Prévoir les changements et afficher les différences des tâches non masquées |

Le playbook exécute les rôles dans cet ordre : `check`, `common`, `postgres`,
`geoserver`, `mviewer`, `mviewerstudio`, `nginx`.

Il crée la base SIG, son propriétaire et PostGIS, puis le workspace GeoServer
`donnessig` et l'entrepôt `postgis`, connecté au schéma `public` de la base.
La connexion SQL est vérifiée sans publier automatiquement de couches.

Attendre un récapitulatif avec `failed=0` et `unreachable=0`, puis passer aux
contrôles de l'étape 9. Une nouvelle exécution conserve les données et applique
les changements de configuration et de sources ; elle peut mettre à jour les
dépendances Studio et redémarrer les services concernés.

## 9. Vérifier les services et ouvrir les applications

Sur le **serveur cible**, vérifier les services et la base :

```bash
sudo systemctl status nginx mviewerstudio geoserver postgresql
sudo nginx -t
psql -h 127.0.0.1 -U usersig -d donneessig -W --command='SELECT PostGIS_Full_Version();'
curl -I http://127.0.0.1:5007/mviewerstudio/
curl -I http://127.0.0.1:8080/geoserver/web/
```

Adapter le compte SQL, la base, les ports et le préfixe si les valeurs par défaut
ont été remplacées. Le mot de passe demandé par `psql` est `postgres_password`.

Depuis le navigateur, ouvrir les URL suivantes en remplaçant `<serveur>` par
le domaine configuré dans `nginx_server_name` :

| Brique | URL ou adresse | Port par défaut | Version configurée |
|---|---|---|---|
| Accueil nginx | `http://<serveur>/home/` | 80 | Paquet APT de la cible |
| Mviewer | `http://<serveur>/mviewer/` | 80 via nginx | Branche `master` |
| Mviewer Studio | `http://<serveur>/mviewerstudio/` | 80 → 5007 local | Branche `oauth2-proxy-keycloak` |
| GeoServer | `http://<serveur>/geoserver/web/` | 80 → 8080 local | 3.0.2 avec Java 21 |
| PostgreSQL / PostGIS | `<serveur>:5432`, selon les accès autorisés | 5432 | Paquets APT de la cible |

Studio et GeoServer écoutent sur `127.0.0.1`. nginx publie leurs URL ; `/`
redirige vers `/home/`. Son site par défaut est désactivé, les autres sites sont
conservés. Adapter le schéma et le port des URL si HTTPS ou un autre port HTTP
a été configuré.

Dans Studio, vérifier l'enregistrement et la publication d'une carte. En mode
`authlib`, vérifier d'abord la redirection vers le fournisseur OIDC et la connexion.

Dans GeoServer, vérifier le workspace `donnessig` et l'entrepôt `postgis`.
Sur une installation vierge, changer le mot de passe initial dans l'interface
avant de publier le service, puis mettre à jour `geoserver_admin_password` dans
le Vault pour les prochaines exécutions.

En cas d'échec, consulter le [guide de dépannage](../docs/src/content/docs/guides/ansible/depannage.md).

## Mettre à jour une installation

### Déployer une autre version de Mviewer

1. Sauvegarder les données et le Vault.
2. Modifier `mviewer_version` dans `site.yml` avec un tag exact, une branche ou
   un SHA. Exemple à remplacer :

   ```yaml
   mviewer_version: vX.Y.Z
   ```

3. Depuis le poste de contrôle, lancer :

   ```bash
   ansible-playbook playbooks/upgrade_mviewer.yml -e @site.yml --ask-become-pass
   ```

4. Vérifier la carte et les données partagées dans Mviewer.

Ce playbook ne demande aucun secret applicatif. Ajouter le Vault s'il contient
les mots de passe de connexion SSH/sudo. Ajouter `--check` pour une prévision.
Un tag est déployé en HEAD détachée ; revenir à un ancien tag est possible.

Le rôle conserve les liens `apps`, `store`, `public` si la version est déjà
déployée. Sinon, il les retire temporairement puis les restaure même en cas
d'échec. Les sources modifiées localement ne sont pas écrasées (`force: false`).

### Modifier les identifiants PostgreSQL

1. Ouvrir `ansible-vault edit secrets.vault.yml` et modifier `postgres_password`.
2. Rejouer le déploiement complet de l'étape 8 pour mettre à jour PostgreSQL
   et l'entrepôt GeoServer avec la même valeur.
3. Vérifier la connexion SQL et l'entrepôt dans GeoServer.

Les mots de passe SQL sont stockés avec SCRAM-SHA-256 et ne sont changés que
si la valeur du Vault change. Modifier le nom de la base ou de l'utilisateur
crée de nouvelles ressources sans supprimer les anciennes ni migrer leurs
données. Les tables existantes conservent leurs propriétaires et leurs droits.

### Changer de version GeoServer

1. Sauvegarder le répertoire de données GeoServer.
2. Modifier ensemble `geoserver_version` et `geoserver_archive_checksum` dans
   `site.yml`, avec le SHA-256 de la nouvelle archive officielle.
3. Vérifier la compatibilité des données et de Java avec la version choisie.
4. Rejouer le déploiement complet puis contrôler le service et le catalogue.

La distribution est installée dans son propre répertoire. Le rôle conserve le
catalogue existant et initialise les données uniquement si le répertoire est
vide, fichiers cachés compris. Une distribution déjà installée n'est pas
retéléchargée. Conserver les options Java de `group_vars/all/geoserver.yml`
lorsqu'une liste personnalisée les remplace.

## Exécuter uniquement PostgreSQL ou GeoServer

1. Préparer la cible avec Python installé et les dépôts APT nécessaires.
2. Suivre les étapes 2 à 5 pour l'inventaire, le site, les accès SQL et le Vault.
3. Installer PostgreSQL/PostGIS :

   ```bash
   ansible-playbook playbooks/install.yml --tags postgres -e @site.yml -e @secrets.vault.yml --ask-vault-pass --ask-become-pass
   ```

4. Si nécessaire, installer ensuite GeoServer, dont la base PostGIS doit déjà
   être disponible :

   ```bash
   ansible-playbook playbooks/install.yml --tags geoserver -e @site.yml -e @secrets.vault.yml --ask-vault-pass --ask-become-pass
   ```

| Exécution | Secrets applicatifs requis |
|---|---|
| `--tags postgres` | `postgres_password` |
| `--tags geoserver` | `postgres_password`, `geoserver_admin_username`, `geoserver_admin_password` |
| Installation complète | Identifiants SQL et GeoServer, clé Studio, secret OIDC si `authlib` |
| `--tags check`, `upgrade_mviewer.yml` | Aucun ; charger le Vault si les mots de passe SSH/sudo s'y trouvent |

Les tags `postgres` et `geoserver` n'exigent pas les secrets Studio. Pour un
autre environnement, sélectionner son inventaire et son Vault avec
`-i inventories/production/hosts.ini -e @/chemin/production.vault.yml --ask-vault-pass`.

## Retrouver les données et consulter les journaux

Sur la cible, utiliser les chemins suivants (valeurs par défaut) :

| Chemin | Contenu |
|---|---|
| `/var/www/mviewergalaxy/home/` | Accueil statique |
| `/var/www/mviewergalaxy/mviewer/` | Sources Mviewer |
| `/srv/apps/mviewerstudio/` | Sources Studio et virtualenv `.venv/`, appartenant à root |
| `/srv/data/mviewer/apps/` | Configurations des cartes |
| `/srv/data/mviewer/store/` | Cartes enregistrées et prévisualisations Studio |
| `/srv/data/mviewer/public/` | Cartes publiées par Studio |
| `/srv/data/geoserver/datadir/` | Catalogue, sécurité et données GeoServer |
| `/var/lib/mviewer-galaxy/` | Sessions Studio et configuration front `mviewerstudio-config.json` |
| `/etc/mviewerstudio/environment` | Secrets et variables d'environnement Studio, accès root |
| `/srv/logs/<application>/` | Journaux nginx, Studio, GeoServer et PostgreSQL |

Les liens `apps`, `store` et `public` sous Mviewer pointent vers les répertoires
partagés. nginx les sert sous `/mviewer/<nom>/` et `/<nom>/`. Pour ouvrir une
carte, indiquer le chemin d'un fichier XML existant :

```text
/mviewer/?config=apps/ma-carte.xml
/mviewer/?config=store/organisation/utilisateur/carte/carte.xml
/mviewer/?config=public/ma-carte.xml
```

Le compte système `mviewer` écrit dans les données et les journaux Studio.
Les sources et son virtualenv restent la propriété de root. La configuration
front est adaptée sans modifier les sources Git et servie sous
`/mviewerstudio/config.json`.

Pour diagnostiquer un problème sur la cible :

```bash
sudo journalctl -u mviewerstudio -u geoserver -n 100 --no-pager
sudo tail -n 100 /srv/logs/nginx/error.log
sudo tail -n 100 /srv/logs/mviewerstudio/error.log
sudo tail -n 100 /srv/logs/geoserver/jetty.log
sudo ls /srv/logs/postgresql/
sudo logrotate --debug /etc/logrotate.conf
sudo systemctl status logrotate.timer
```

La rotation quotidienne conserve 14 archives par défaut. Pour changer cette
rétention, ajouter `logging_rotate` dans `site.yml` puis rejouer le déploiement.
Les valeurs internes du rôle sont dans `roles/logging/defaults/main.yml`.
`copytruncate` conserve les fichiers ouverts sans redémarrer les applications ;
quelques lignes peuvent être perdues pendant la rotation. Pour PostgreSQL, les
liens de journaux sont gérés par cluster ; seuls les clusters actifs concernés
par un changement sont redémarrés.

## Migrer une ancienne configuration

1. Sauvegarder les données existantes et les secrets.
2. Reporter les adaptations de `group_vars/all.yml` et des anciens fichiers
   `roles/postgres/defaults/main.yml` et `roles/geoserver/defaults/main.yml` dans
   `site.yml`. Les valeurs fournies sont désormais réparties par application
   sous `group_vars/all/`.
3. Reporter les identifiants de l'ancien `.env` dans le Vault :

   | Ancienne clé | Variable Vault |
   |---|---|
   | `POSTGRES_DB` | `postgres_database` |
   | `POSTGRES_USER` | `postgres_username` |
   | `POSTGRES_PASSWORD` | `postgres_password` |

4. Conserver les noms SQL, les mots de passe actuels et la clé de session Studio.
   Fournir les identifiants actuels de GeoServer ; le rôle n'a plus de mot de
   passe administrateur par défaut. Chiffrer le Vault selon l'étape 5.
5. Si les chemins de données changent, déplacer les données avant le déploiement
   en conservant leurs propriétaires. Par exemple, migrer `/var/lib/geoserver/`
   vers `/srv/data/geoserver/datadir/` avec les droits du compte `geoserver`.
6. Rejouer les étapes 7 à 9 avec le Vault et les paramètres du site.
7. Après validation, supprimer l'ancien `.env` local.

Lorsqu'un dossier occupe l'emplacement d'un lien partagé, le playbook le déplace
vers `<mviewer_install_dir>.<nom>-backup` sans écraser une sauvegarde existante.
Récupérer les cartes souhaitées depuis ces sauvegardes ou les anciens dossiers
`apps/store` et `apps/public`. Changer un chemin ne déplace pas les données.
Les anciens répertoires et liens renommés sont conservés ; Git utilise
`sparse-checkout` pour préserver les répertoires partagés lors des mises à jour.

Pour personnaliser les noms de `store` et `public`, les chemins ou les ports,
consulter le [guide d'adaptation à l'environnement](../docs/src/content/docs/guides/ansible/environnement.md).
Le [guide d'installation détaillé](../docs/src/content/docs/guides/installation-ansible.md)
couvre également les accès aux applications et CORS.
