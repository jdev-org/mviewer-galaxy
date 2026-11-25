# Déploiement Ansible

Installation native sur Debian 12+ ou Ubuntu 22.04+ avec systemd : nginx sert
Mviewer et relaie Studio vers Gunicorn sur `127.0.0.1:5007`. Studio fonctionne
par défaut sans authentification (`mviewerstudio_auth_mode: public`). OIDC est
optionnel, avec un fournisseur externe comme Keycloak. Le playbook n'installe
ni Docker ni Keycloak.

Le rôle `postgres` installe également PostgreSQL, l'extension serveur PostGIS
et ses outils en ligne de commande, puis active et démarre le service
`postgresql`. Les versions sont celles des dépôts APT de la cible.

Le rôle `geoserver` installe GeoServer avec son Jetty embarqué et Java 21,
puis active son service systemd. Il écoute sur `127.0.0.1:8080` par défaut.

## Préparer

Ansible Core 2.16+ doit être disponible sur le poste de contrôle. La cible doit
être accessible en SSH avec un compte root ou disposant de droits sudo, et avoir
accès aux dépôts Git, APT et Python. Python >= 3.11 (`/usr/bin/python3`) doit être
installé ou disponible dans les dépôts APT. S'il est absent, le rôle `common`
l'installe avant d'utiliser les modules Ansible. Aucun module de collection
externe n'est requis.

Les dépôts APT doivent également fournir `openjdk-21-jre-headless`. Ce paquet
n'est pas disponible dans les dépôts de base de toutes les versions ciblées,
notamment Debian 12 : préparer un dépôt adapté ou utiliser une cible plus
récente fournissant Java 21. Le rôle n'ajoute pas de dépôt APT. La cible doit
aussi pouvoir télécharger l'archive GeoServer depuis SourceForge et ses miroirs.

Toutes les commandes suivantes s'exécutent depuis `ansible/` pour charger
`ansible.cfg`. Modifier `inventories/dev/hosts.ini` : l'adresse `192.0.2.10`
est un exemple sans serveur associé. Le groupe attendu est `galaxy`.

Les variables sont réparties dans `group_vars/all/`, avec un fichier par
application et `common.yml` pour les paramètres partagés. Ces fichiers sont
chargés explicitement par les deux playbooks.

Pour les adapter sans modifier ces valeurs, créer un fichier
`site.yml` et le charger avec `-e @site.yml` :

```yaml
nginx_server_name: cartes.example.org
# Utiliser des SHA Git ou des tags pour figer les versions déployées.
mviewer_version: master
mviewerstudio_version: oauth2-proxy-keycloak
```

| Fichier | Configuration |
|---|---|
| `group_vars/all/common.yml` | Comptes système, chemins partagés, paquets communs et schéma public |
| `group_vars/all/mviewer.yml` | Sources, version et répertoires Mviewer |
| `group_vars/all/mviewerstudio.yml` | Sources, chemins, port et paramètres OIDC publics de Studio |
| `group_vars/all/nginx.yml` | Nom du serveur, port HTTP et journaux nginx |
| `group_vars/all/postgres.yml` | Paquets, port, socket et paramètres PostgreSQL |
| `group_vars/all/geoserver.yml` | Version, Java, chemins, réseau et catalogue GeoServer |
| `secrets.vault.yml` | Identifiants et secrets chiffrés partagés par les applications |

Les sources sont clonées sur la cible depuis les dépôts définis dans les
variables ; les changements locaux des sous-modules ne sont pas transférés.
Les branches par défaut correspondent à `.gitmodules`.

Adapter `roles/postgres/templates/pg_hba.conf.j2` avec les clients autorisés
avant une installation complète (voir « PostgreSQL et PostGIS »).

Préparer les secrets :

```bash
cp secrets.example.yml secrets.vault.yml
chmod 600 secrets.vault.yml
# Modifier secrets.vault.yml avec les vraies valeurs avant chiffrement.
python3 -c 'import secrets; print(secrets.token_hex(32))'
ansible-vault encrypt secrets.vault.yml
```

Renseigner aussi `postgres_password`, `geoserver_admin_username` et
`geoserver_admin_password` dans ce fichier pour PostgreSQL et GeoServer.
Utiliser la valeur générée pour `mviewerstudio_secret_key`, nécessaire dans les
deux modes pour les sessions Flask.

Le fichier `*.vault.yml` est ignoré par Git.

Le playbook refuse une clé de session absente et masque le rendu des secrets
dans les sorties.

Attention : ne pas utiliser les valeurs d'exemple pour un déploiement réel.

## Répartition des variables et secrets

Un seul fichier `secrets.vault.yml` regroupe les données confidentielles du déploiement :

| Usage | Variables dans le Vault |
|---|---|
| PostgreSQL / GeoServer | `postgres_database`, `postgres_username`, `postgres_password` |
| Administration REST GeoServer | `geoserver_admin_username`, `geoserver_admin_password` |
| Sessions Studio | `mviewerstudio_secret_key` |
| OIDC facultatif | `mviewerstudio_oidc_client_secret`, et éventuellement `mviewerstudio_oidc_issuer`, `mviewerstudio_oidc_client_id` |
| Connexion Ansible facultative | `ansible_password`, `ansible_become_password` |

Les fichiers de `group_vars/all/` sont chargés explicitement via `vars_files`,
même avec un inventaire personnalisé. Les variables `-e @site.yml` remplacent
ces valeurs ; si plusieurs fichiers `-e @…` définissent une même variable, le
dernier a priorité. Les paramètres internes de rotation restent dans
`roles/logging/defaults/main.yml`.

Créer le Vault une seule fois. Pour le modifier ensuite, utiliser
`ansible-vault edit secrets.vault.yml` en conservant les secrets existants.
Le suffixe `.vault.yml` ne chiffre pas le fichier et ne déclenche pas son
chargement : utiliser `ansible-vault encrypt`, puis charger le fichier avec
`-e @secrets.vault.yml --ask-vault-pass`. Le mot de passe Vault sert au
déchiffrement ; les mots de passe PostgreSQL, GeoServer et sudo sont distincts.

Les secrets n'ont aucune valeur par défaut dans les rôles ou `group_vars/all/`.
Les ports, chemins, versions, URL publiques et noms de services restent dans
`site.yml` ou les valeurs par défaut. Les rôles `check`, `common`, `mviewer`,
`upgrade_mviewer`, `nginx` et `logging` ne définissent aucun secret applicatif.
Ne pas placer de jeton dans une URL Git ; utiliser une authentification SSH adaptée
si les dépôts deviennent privés.

Ansible déchiffre le Vault lors de l'exécution. Sur la cible, Studio reçoit ses
secrets via `/etc/mviewerstudio/environment`, réservé à root (`0600` dans un
répertoire `0700`) ; son rendu est masqué et exclu de `--diff`. Les tâches de
configuration PostgreSQL et GeoServer masquent également leurs secrets.
Le Vault protège les sources sur le poste de contrôle ; les services conservent
leurs propres mécanismes de stockage sur la cible.

| Exécution | Secrets applicatifs nécessaires |
|---|---|
| Installation complète | PostgreSQL, compte REST GeoServer, clé de session Studio, et secret OIDC en mode `authlib` |
| `--tags postgres` | `postgres_password` |
| `--tags geoserver` | `postgres_password`, `geoserver_admin_username`, `geoserver_admin_password` |
| `--tags check`, `upgrade_mviewer.yml` | Aucun secret applicatif |

Si les mots de passe SSH/sudo sont dans le Vault, le charger aussi pour les
contrôles ou mises à jour qui nécessitent ces identifiants de connexion.

## Authentification OIDC optionnelle

En mode `public`, Studio est accessible sans connexion et aucun paramètre OIDC
n'est requis ni écrit dans le fichier d'environnement.

Pour activer OIDC, ajouter dans `site.yml` :

```yaml
mviewerstudio_auth_mode: authlib
```

Renseigner ensuite `mviewerstudio_oidc_issuer` et
`mviewerstudio_oidc_client_secret` dans le fichier de secrets (avec
`ansible-vault edit secrets.vault.yml` s'il est déjà chiffré). Le client utilise
`mviewerstudio_oidc_client_id: mviewerstudio` par défaut. Ces paramètres sont
vérifiés uniquement en mode `authlib`.

Configurer dans Keycloak le client confidentiel `mviewerstudio`, son secret,
le callback `https://cartes.example.org/mviewerstudio/auth/callback` (ou
`http://` pour un test) et les URL de retour de déconnexion de Mviewer.
Le préfixe peut changer via `mviewerstudio_url_prefix`. Les utilisateurs doivent
avoir le groupe `MVIEWER_ACCESS` et le claim d'organisation attendu par Studio ;
ces valeurs s'adaptent via les variables `mviewerstudio_oidc_*`.
L'issuer et son endpoint de découverte doivent être accessibles depuis le serveur.

## Contrôler les prérequis

Le rôle `check` précède `common` et vérifie depuis la cible :

- Les droits root effectifs, directement ou via sudo avec l'escalade Ansible.
- Le système Debian 12+ ou Ubuntu 22.04+ avec systemd.
- Python >= 3.11 s'il est installé, ou la version du paquet APT s'il est absent.
- L'accès aux dépôts APT et le téléchargement de nginx et des dépendances
  déclarées dans `galaxy_system_packages`, dont `python3-pip` et `python3-venv`,
  ainsi que des paquets PostgreSQL/PostGIS déclarés dans `postgres_packages`.
- La disponibilité de Java 21, des outils déclarés dans `geoserver_packages`
  et de logrotate.
- L'accès aux deux dépôts Git avec `git ls-remote`. Si Git est absent, ce contrôle
  est différé après son installation par `common`, avant tout clonage.

Pour lancer uniquement ces contrôles, sans clé de session ni secrets OIDC :

```bash
ansible-playbook playbooks/install.yml --tags check --ask-become-pass
```

Ajouter `-e @site.yml` pour vérifier les paramètres d'un déploiement personnalisé.
Le rôle `check` ne modifie pas l'état installé ni les caches APT du système.
Les index et les téléchargements sont isolés dans un répertoire temporaire,
supprimé même en cas d'échec. Les hooks APT sont désactivés pour ces contrôles.
Les vérifications réseau sont rejouées à chaque passage, y compris avec
`--check`, et restent à `changed=0`. Les paquets déjà satisfaits par
l'installation existante ne sont pas téléchargés à nouveau.
Le contrôle Git peut donc rester différé lors d'une exécution limitée à `check`.
L'installation Python via pip et l'authentification OIDC sont vérifiées lors
des étapes d'installation et d'utilisation correspondantes.

## Vérifier et déployer

```bash
ansible-inventory --graph
ansible-playbook playbooks/install.yml --syntax-check
ansible-playbook playbooks/install.yml -e @site.yml -e @secrets.vault.yml --ask-vault-pass --check --diff
ansible-playbook playbooks/install.yml -e @site.yml -e @secrets.vault.yml --ask-vault-pass --ask-become-pass
```

Omettre `-e @site.yml` si ce fichier n'a pas été créé. Avec un autre inventaire,
ajouter `-i inventories/production/hosts.ini`. Les paramètres personnalisés se
passent avec `-e @site.yml`, car le playbook charge les valeurs communes via
`vars_files`. Retirer `--ask-become-pass` si sudo ne demande pas de mot de passe.

Le mode `--check` donne une prévision : il ignore les installations pip et les
actions sur les services. La simulation complète nécessite Python déjà installé
sur la cible ; le contrôle seul (`--tags check`) fonctionne aussi sans Python. Il ne vérifie pas le démarrage de l'application ni
les dépendances Python. Les rechargements de nginx passent par `nginx -t`.
Une nouvelle exécution met à jour les sources et les dépendances déclarées
par Studio, et redémarre Studio si nécessaire. Le paquet local de Studio n'est
réinstallé que si les sources changent ou s'il est absent du virtualenv. Les données ne sont pas effacées.

## PostgreSQL et PostGIS

Le rôle `postgres` est exécuté après `common` dans le playbook d'installation.
Il utilise uniquement les modules intégrés à Ansible. Les paquets par défaut
sont `postgresql`, `postgresql-postgis` et `postgis` ; la liste `postgres_packages`
peut être remplacée dans `site.yml` si nécessaire. Sur Ubuntu, le dépôt
`universe` doit être disponible pour PostGIS.

Sur une cible disposant déjà de Python et de dépôts APT configurés, installer
uniquement PostgreSQL et PostGIS :

```bash
# Utiliser le Vault préparé ci-dessus et renseigner les identifiants PostgreSQL.
ansible-vault edit secrets.vault.yml
# Adapter roles/postgres/templates/pg_hba.conf.j2 avec les clients autorisés.
ansible-playbook playbooks/install.yml --tags postgres -e @secrets.vault.yml --ask-vault-pass --ask-become-pass
```

Les variables de la base SIG sont partagées par PostgreSQL et GeoServer.
Le modèle `secrets.example.yml` contient :

```yaml
postgres_database: donneessig
postgres_username: usersig
postgres_password: ""
```

Renseigner un mot de passe non vide avant chiffrement. Les noms acceptent de
1 à 63 caractères minuscules, chiffres et underscores, sans chiffre initial.
Les valeurs sont des chaînes YAML ; les caractères spéciaux du mot de passe
sont transmis sans interprétation shell. Les tâches et paramètres secrets sont masqués.

Charger le Vault avec `-e @secrets.vault.yml --ask-vault-pass` pour les rôles
`postgres` et `geoserver`, y compris lors d'une installation complète.
Le tag `check` seul n'en a pas besoin. Pour un autre environnement, charger
son fichier Vault avec `-e @/chemin/production.vault.yml --ask-vault-pass`.
Modifier les valeurs avec `ansible-vault edit secrets.vault.yml`.

Pour migrer les anciennes variables, reporter les adaptations de `group_vars/all.yml`
et des anciens fichiers `roles/postgres/defaults/main.yml` et
`roles/geoserver/defaults/main.yml` dans `site.yml`. Les valeurs fournies sont
désormais dans `group_vars/all/common.yml` et les cinq fichiers applicatifs.

Pour migrer une installation existante, reporter `POSTGRES_DB`, `POSTGRES_USER`
et `POSTGRES_PASSWORD` de l'ancien `.env` dans `postgres_database`,
`postgres_username` et `postgres_password`, puis chiffrer le Vault. Conserver
les mêmes valeurs pour éviter de créer une autre base ou de changer le mot de passe.
Après validation du déploiement avec le Vault, supprimer l'ancien `.env` local.

Le rôle crée l'utilisateur SQL avec connexion autorisée, sans droits
superutilisateur ni création de rôles ou de bases, puis la base dont il est
propriétaire, le schéma `public` dont il est aussi propriétaire et l'extension
PostGIS. Les identifiants sont distincts des comptes
Linux et SSH. La configuration s'applique au serveur local sur le port
`postgres_port` (5432 par défaut), via `postgres_socket_dir` (`/var/run/postgresql`).
Le module local au rôle utilise `psql` et Python standard ; aucune collection
Ansible ni bibliothèque Python PostgreSQL supplémentaire n'est nécessaire.

Les passages suivants conservent la base et ses données, et ne changent le mot
de passe que si sa valeur dans le Vault change. Les mots de passe sont stockés
avec SCRAM-SHA-256 et les tâches contenant des secrets sont masquées.
Changer le nom de base ou d'utilisateur crée les nouvelles ressources sans
supprimer les anciennes ni transférer leurs données. En mode `--check`, les
variables PostgreSQL sont validées, mais le provisionnement SQL et les accès réseau sont ignorés.

Si la base existe déjà, son propriétaire est ajusté à l'utilisateur configuré.
Les tables existantes conservent leurs propriétaires et leurs droits ; leur
migration éventuelle reste une opération distincte.

### Préparer pg_hba.conf avant l'installation

Modifier `roles/postgres/templates/pg_hba.conf.j2` avant de lancer le rôle.
Les IP autorisées se définissent dans ce template. Le fichier Vault contient
uniquement les noms et le mot de passe de la base SIG.

Le template contient l'administration locale par `peer`, les connexions locales
de GeoServer et des exemples commentés pour ajouter des IP ou réseaux CIDR.
Ajouter les clients autorisés avant les lignes `reject`, par exemple :

```text
host "{{ postgres_configuration.database }}" "{{ postgres_configuration.username }}" 192.0.2.10/32 scram-sha-256
```

Conserver les variables Jinja : la base et l'utilisateur seront lus dans le Vault.
Le template remplace entièrement le fichier `pg_hba.conf` du serveur sélectionné
par `postgres_port` : y reporter aussi les règles spécifiques à une installation
existante. Un autre template peut être fourni via `postgres_hba_template` dans
`site.yml` (chemin absolu ou nom d'un template du rôle).

Une tâche du rôle déploie ce fichier, vérifie sa syntaxe via PostgreSQL puis
notifie son rechargement. `postgresql.conf` est également configuré avec
`listen_addresses = '*'`. Le serveur écoute donc sur toutes ses interfaces ;
les clients SIG admis sont ceux du template. Les changements d'écoute déclenchent
le redémarrage du cluster actif concerné. Le pare-feu doit autoriser les connexions
souhaitées au port PostgreSQL.

Pour vérifier la base créée :

```bash
psql -h 127.0.0.1 -U usersig -d donneessig -W --command='SELECT PostGIS_Full_Version();'
sudo systemctl status postgresql
```

## GeoServer avec Jetty et Java 21

Le rôle `geoserver` utilise la distribution binaire officielle GeoServer
`3.0.2`, qui inclut Jetty `12.1.14`. Il installe le JRE Java 21 via APT et
utilise directement le binaire de ce paquet, indépendamment de la version Java
par défaut du système. Il vérifie que la JVM utilisée est bien Java 21.

Après démarrage, le rôle crée le workspace `donnessig`, le définit comme workspace
par défaut, puis crée l'entrepôt PostGIS `postgis`. Celui-ci utilise la base et
l'utilisateur du Vault (`donneessig` / `usersig` par défaut), le schéma `public`
et le même mot de passe. La connexion à PostgreSQL est vérifiée sans publication
automatique de couches. Exécuter le rôle `postgres` avant `geoserver` pour
préparer la base ; le playbook complet respecte cet ordre.

Les variables `geoserver_workspace`, `geoserver_datastore`,
`geoserver_postgres_host` et `geoserver_postgres_port` adaptent ce paramétrage.
Les accès REST exigent `geoserver_admin_username` et `geoserver_admin_password`
dans le Vault, dès la première installation. Renseigner les identifiants actuels
du serveur (initialement `admin` / `geoserver` pour la distribution vierge).
Après changement dans GeoServer, mettre à jour le Vault. Le rôle utilise ce
compte et ne modifie pas son mot de passe. Une valeur absente ou vide est refusée
avant l'installation des paquets, y compris en simulation.

La configuration du catalogue passe par l'API REST, afin de conserver le
chiffrement des mots de passe par GeoServer. Une empreinte protégée en mode
`0600`, dans `/var/cache/geoserver-downloads/postgis-catalog.json`, permet de
détecter les changements de mot de passe et d'éviter de réécrire l'entrepôt à
chaque passage. Les autres workspaces et entrepôts sont conservés.

Les paramètres du rôle sont dans `group_vars/all/geoserver.yml` et peuvent
être remplacés dans `site.yml`, par exemple :

```yaml
geoserver_port: 8081
geoserver_data_dir: /srv/data/geoserver/datadir
geoserver_java_options:
  - -Xms512m
  - -Xmx2048m
  - -Djava.awt.headless=true
  - -XX:-UseBASE64Intrinsics
```

Le dernier paramètre Java applique la
[mitigation publiée par GeoServer pour Java4Shell](https://geoserver.org/vulnerability/2026/11/18/java4shell-mitigation.html).
Conserver Java à jour via les dépôts du système.

Pour installer uniquement GeoServer sur une cible disposant déjà de Python et
de dépôts APT fournissant Java 21, lancer depuis `ansible/` :

```bash
ansible-playbook playbooks/install.yml --tags geoserver -e @site.yml -e @secrets.vault.yml --ask-vault-pass --ask-become-pass
```

Omettre `-e @site.yml` si ce fichier n'existe pas. Aucun secret Studio n'est
nécessaire pour ce tag. Le contrôle `--tags check` vérifie les paquets APT ;
le téléchargement de GeoServer et la validation de Java ont lieu à l'installation.
En mode `--check`, l'extraction, l'initialisation des données, le rendu du service
et les actions sur ce service sont ignorés car ils dépendent des fichiers installés.

Les chemins par défaut sont :

- `/opt/geoserver/3.0.2/` : distribution GeoServer et Jetty, appartenant à root.
- `/srv/data/geoserver/datadir/` : catalogue, configuration, sécurité et données, appartenant au compte système `geoserver`.
- `/srv/logs/geoserver/` : journaux applicatifs et sortie console de Jetty.
- `/var/cache/geoserver/` : fichiers temporaires de la JVM et de Jetty.
- `/var/cache/geoserver-downloads/` : archive téléchargée, vérifiée par SHA-256.
- `/etc/systemd/system/geoserver.service` : unité systemd.

Les données initiales sont copiées uniquement si le répertoire de données est
vide (fichiers cachés compris). Tout répertoire déjà renseigné est conservé,
même s'il ne contient pas de fichier `global.xml`. Les exécutions suivantes
conservent le catalogue et sa configuration. Si la distribution demandée est déjà
installée, le téléchargement et l'extraction sont ignorés, même si l'archive en
cache a été supprimée. Le redémarrage est notifié uniquement si la distribution,
les données initiales ou l'unité systemd changent.
Sauvegarder le répertoire de données avant de changer de version.
Pour changer de version, adapter ensemble `geoserver_version` et
`geoserver_archive_checksum` avec le SHA-256 de la nouvelle archive officielle ;
le nouveau logiciel sera installé dans son propre répertoire.

nginx publie GeoServer sous `/geoserver/`, vers `127.0.0.1:8080` par défaut.
Le contexte `/geoserver` et les paramètres des requêtes OGC sont conservés.
Le service GeoServer utilise les en-têtes du proxy pour construire les URL
publiques ; `galaxy_public_scheme` choisit leur schéma HTTP ou HTTPS.

Ouvrir `http://<nginx_server_name>/geoserver/` (adapter le port et le schéma).
L'installation initiale utilise
le compte GeoServer `admin` / `geoserver` fourni par la distribution : changer ce
mot de passe dans l'interface avant de publier le service. Pour vérifier la cible :

```bash
sudo systemctl status geoserver
sudo tail -n 100 /srv/logs/geoserver/jetty.log
curl -I http://127.0.0.1:8080/geoserver/web/
```

## Mettre à jour Mviewer

Le rôle `upgrade_mviewer` déploie la valeur de `mviewer_version`. Pour cibler
un tag, indiquer son nom exact dans `site.yml` (remplacer cet exemple) :

```yaml
mviewer_version: vX.Y.Z
```

Puis lancer depuis `ansible/` :

```bash
ansible-playbook playbooks/upgrade_mviewer.yml -e @site.yml --ask-become-pass
```

Ou passer directement le tag en ligne de commande :

```bash
ansible-playbook playbooks/upgrade_mviewer.yml -e mviewer_version=vX.Y.Z --ask-become-pass
```

Aucun secret Studio ou OIDC n'est nécessaire. Le module Git récupère les
références nécessaires et effectue le checkout de la version demandée ; un tag
est déployé en HEAD détachée. Il est possible de passer d'un tag à un autre,
y compris de revenir à un tag précédent. La variable accepte aussi une branche
ou un SHA, comme à l'installation.

Le rôle prévoit le changement avant de retirer les liens partagés (`apps`,
`store`, `public` par défaut). Si la version demandée est déjà déployée, les liens
restent en place et aucun changement n'est effectué. Sinon, les liens sont
retirés pendant le déploiement puis restaurés vers leurs destinations initiales
dans un bloc `always`, même si le déploiement
échoue. Les données partagées sont conservées. Les modifications locales des
sources ne sont pas écrasées (`force: false`). Avec `--check`, le rôle consulte
le dépôt distant et prévoit les changements sans modifier l'installation.

## Données et accès

- `/var/www/mviewergalaxy/mviewer/` : sources de Mviewer.
- `/var/www/mviewergalaxy/home/` : page d'accueil statique, servie sous `/home/`.
- `/srv/apps/mviewerstudio/` : sources de Studio et environnement virtuel Python dans `.venv/`.
- `/srv/data/geoserver/datadir/` : données et configuration GeoServer.
- `/srv/data/mviewer/apps/` : cartes Mviewer.
- `/srv/data/mviewer/store/` : cartes générées par Studio.
- `/srv/data/mviewer/public/` : cartes publiées par Studio, copiées depuis `store` lors de la publication.
- `/srv/logs/` : journaux, dans un répertoire par application, avec logrotate.
- `/var/lib/mviewer-galaxy/sessions/` : sessions privées de Studio.
- `/var/lib/mviewer-galaxy/mviewerstudio-config.json` : configuration front adaptée, servie par nginx.
- `/etc/mviewerstudio/environment` : variables et secrets, accès root uniquement.
- `/etc/systemd/system/mviewerstudio.service` : Gunicorn exécuté depuis le virtualenv de `/srv/apps/mviewerstudio/`.

Les trois répertoires sont partagés comme des volumes Docker. Des liens sont
créés sous `/var/www/mviewergalaxy/mviewer/` :

| Lien dans Mviewer | Destination par défaut | Usage |
|---|---|---|
| `apps` | `/srv/data/mviewer/apps` | Configurations générales |
| `store` | `/srv/data/mviewer/store` | Enregistrements et prévisualisations Studio |
| `public` | `/srv/data/mviewer/public` | Publications Studio |

nginx sert les mêmes répertoires sous `/mviewer/apps/`, `/mviewer/store/` et
`/mviewer/public/`, ainsi que sous `/apps/`, `/store/` et `/public/`.
Le paramètre `config` désigne un fichier XML dans le dossier choisi :

```text
/mviewer/?config=apps/ma-carte.xml
/mviewer/?config=store/organisation/utilisateur/carte/carte.xml
/mviewer/?config=public/ma-carte.xml
```

Adapter les chemins aux fichiers réellement présents. Un nom de répertoire
seul (`?config=store`, par exemple) ne désigne pas une configuration XML.

Les destinations et les noms de `store` et `public` sont configurables dans
`site.yml`, par exemple :

```yaml
mviewer_apps_dir: /srv/data/mviewer/apps
mviewer_store_name: brouillons
mviewer_store_dir: /srv/data/mviewer/brouillons
mviewer_public_name: cartes
mviewer_public_dir: /srv/data/mviewer/cartes
```

Avec cet exemple, les liens et URL deviennent `mviewer/brouillons` et
`mviewer/cartes`. Les chemins du backend Studio, ses URL de prévisualisation et
de publication et les permissions systemd suivent ces variables. La configuration
front est générée à partir du fichier fourni par Studio et servie par nginx sur
`/mviewerstudio/config.json`, sans modifier les sources Git.

Un dossier existant à l'emplacement d'un lien est déplacé sans perte de contenu
hors du dépôt, dans `<mviewer_install_dir>.<nom>-backup`. Pour `apps`, ce chemin
reste configurable via `mviewer_apps_backup_dir`. Une sauvegarde existante
n'est jamais écrasée. Lors d'une migration, récupérer les fichiers souhaités
depuis ces sauvegardes ou depuis les anciens dossiers `apps/store` et
`apps/public` vers leurs nouvelles destinations. Changer les variables ne
déplace pas automatiquement les données existantes.

Pour une installation utilisant les anciens chemins, sauvegarder puis migrer
les données de `/var/lib/geoserver/` vers `/srv/data/geoserver/datadir/` en
conservant les droits du compte `geoserver`, avant de démarrer le service avec
les nouveaux paramètres. Les sources Mviewer seront clonées au nouvel
emplacement ; récupérer aussi les éventuels fichiers locaux de l'ancien
`/opt/mviewer-galaxy/mviewer/`. Le playbook ne supprime pas ces anciens dossiers.

Git exclut ces répertoires via `sparse-checkout` afin de préserver les liens et
les données pendant les mises à jour. Les exécutions suivantes conservent les
liens et les sauvegardes sans changement. Lors d’un changement de nom, les anciens
liens et leurs exclusions Git sont conservés pour préserver les accès existants.

Le compte système `mviewer` (groupe `mviewer`) exécute Gunicorn et écrit dans
les données et les journaux de Studio ; les sources et le
virtualenv appartiennent à root. Les répertoires partagés, y compris `store`,
sont servis par nginx comme dans la composition Docker.
Sauvegarder le répertoire de données et les secrets avant une mise à jour.

Mviewer est accessible sur `/mviewer/`, Studio sur `/mviewerstudio/`,
GeoServer sur `/geoserver/`, et `/`
redirige vers l'accueil `/home/`. Le site nginx par défaut est désactivé ; les autres sites
existants sont conservés. Adapter le port si une autre stack écoute déjà dessus.

nginx écoute en HTTP. Pour une URL publique HTTPS, placer un terminateur TLS
devant lui et définir `galaxy_public_scheme: https`. Ce paramètre fixe le schéma
transmis à Studio ; il n'active pas TLS. Avec OIDC, les callbacks doivent utiliser
le même schéma et le même nom public. Restreindre alors l'accès au port HTTP
au proxy de confiance.

Sur la cible, vérifier le fonctionnement :

```bash
sudo systemctl status mviewerstudio nginx
sudo tail -n 100 /srv/logs/mviewerstudio/error.log
sudo nginx -t
curl -I http://localhost/home/
curl -I http://localhost/mviewer/
curl -I http://localhost/mviewerstudio/
```

En mode `public`, Studio s'ouvre sans connexion. En mode `authlib`, une session
anonyme doit être redirigée vers le fournisseur OIDC. Adapter l'URL et le port à `nginx_server_name` et `nginx_http_port`, puis vérifier dans le
navigateur la connexion, l'enregistrement et la publication d'une carte.

## Journaux et rotation

Chaque application configure le rôle partagé `logging` :

| Répertoire | Journaux |
|---|---|
| `/srv/logs/nginx/` | `access.log`, `error.log`, y compris les journaux globaux de nginx |
| `/srv/logs/mviewerstudio/` | `access.log`, `error.log` de Gunicorn, `application.log` pour stdout/stderr |
| `/srv/logs/geoserver/` | `geoserver.log`, `jetty.log` pour stdout/stderr de Java |
| `/srv/logs/postgresql/` | `postgresql-<version>-<cluster>.log` |

Mviewer et l'accueil sont statiques : leurs accès figurent dans les journaux
nginx. Les messages de cycle de vie des unités restent accessibles via
`journalctl`. Les anciens journaux sous `/var/log/` sont conservés.

Le rôle installe logrotate et active `logrotate.timer`. La rotation est
quotidienne, avec 14 archives conservées, compression différée et absence de
rotation des fichiers vides. `logging_rotate` permet d'adapter cette rétention.
Les règles nginx et PostgreSQL remplacent celles des paquets ; celles de Studio
et GeoServer se trouvent dans `/etc/logrotate.d/mviewer-galaxy-<application>`.
`copytruncate` conserve les descripteurs ouverts sans redémarrer les applications ;
quelques lignes peuvent être perdues entre la copie et la troncature.

Pour PostgreSQL, le lien `log` de chaque cluster pointe vers le nouveau dossier,
avec `logging_collector = off` et `log_destination = 'stderr'` dans un bloc
Ansible. Seuls les clusters actifs dont la configuration ou le lien change sont
redémarrés. Les données SQL restent à leur emplacement de la distribution.

```bash
sudo logrotate --debug /etc/logrotate.conf
sudo systemctl status logrotate.timer
```
