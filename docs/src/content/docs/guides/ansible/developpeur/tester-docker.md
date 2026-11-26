---
title: "Tester dans un conteneur Docker"
description: "Utiliser une cible Ubuntu avec systemd et SSH pour tester les rôles Ansible sans VM."
---

Ce conteneur remplace une VM pour tester l'installation native avec Ansible : les rôles y installent PostgreSQL, GeoServer, Mviewer, Studio et nginx.

Il partage le noyau de l'hôte ; il ne valide donc pas tous les comportements d'une VM ou d'un serveur physique.

## Préparer le poste de contrôle

- Utiliser un hôte Linux avec Docker Engine, cgroups v2 et les droits d'accès au démon Docker. Cette procédure vise Docker classique ; Docker rootless et Docker Desktop ne sont pas couverts.

- Installer Ansible Core 2.16+, Python 3 et le client OpenSSH sur ce poste.

- Cloner le dépôt et disposer d'un accès réseau aux dépôts APT, Git et aux téléchargements des applications.

- Exécuter les premières commandes à la racine du dépôt, dans le même terminal pour conserver `MVIEWER_TEST_DIR`.

Le conteneur utilise `--privileged` pour exécuter systemd. Réserver cette cible à un poste de développement de confiance : ce mode donne des droits étendus sur l'hôte. Voir la [documentation Docker](https://docs.docker.com/reference/cli/docker/container/run/#privileged).

## Construire et démarrer la cible

```bash
docker build -t mviewer-galaxy-ansible-test docs/examples/ansible-docker

MVIEWER_TEST_DIR=$(mktemp -d /tmp/mviewer-galaxy-ansible.XXXXXX)
ssh-keygen -t ed25519 -N '' -f "$MVIEWER_TEST_DIR/id_ed25519"

docker run -d --name mviewer-galaxy-ansible-test \
  --privileged --cgroupns=private \
  --tmpfs /run --tmpfs /run/lock \
  -p 127.0.0.1:2222:22 \
  -p 127.0.0.1:8088:80 \
  mviewer-galaxy-ansible-test
```

| Élément | Explication |
|---|---|
| `docs/examples/ansible-docker/Dockerfile` | Image Ubuntu 24.04 contenant systemd, SSH, sudo et Python. Les applications seront installées par Ansible. |
| `mviewer-galaxy-ansible-test` | Nom de l'image et du conteneur de test. |
| `MVIEWER_TEST_DIR` | Répertoire temporaire du poste de contrôle : clé SSH, inventaire et secrets jetables. |
| `--cgroupns=private` | Espace de noms cgroup propre au conteneur pour systemd. |
| `--tmpfs /run`, `--tmpfs /run/lock` | Répertoires d'exécution temporaires nécessaires aux services. |
| `127.0.0.1:2222:22` | SSH accessible uniquement depuis le poste de contrôle, sur le port 2222. |
| `127.0.0.1:8088:80` | nginx accessible uniquement depuis ce poste, sur le port 8088. |

Aucun répertoire du serveur réel n'est monté : les données et les applications restent dans le conteneur.

## Configurer la connexion SSH

```bash
docker cp "$MVIEWER_TEST_DIR/id_ed25519.pub" \
  mviewer-galaxy-ansible-test:/home/deploy/.ssh/authorized_keys
docker exec mviewer-galaxy-ansible-test \
  chown deploy:deploy /home/deploy/.ssh/authorized_keys
docker exec mviewer-galaxy-ansible-test \
  chmod 600 /home/deploy/.ssh/authorized_keys

cat > "$MVIEWER_TEST_DIR/hosts.ini" <<EOF
[galaxy]
docker-test ansible_host=127.0.0.1 ansible_port=2222 ansible_user=deploy ansible_ssh_private_key_file=$MVIEWER_TEST_DIR/id_ed25519

[galaxy:vars]
ansible_ssh_common_args='-o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new -o UserKnownHostsFile=$MVIEWER_TEST_DIR/known_hosts'
EOF
```

| Élément | Explication |
|---|---|
| `deploy` | Compte SSH créé dans l'image avec sudo sans mot de passe, réservé à ce test. |
| `authorized_keys` | Reçoit uniquement la clé publique ; la clé privée reste sur le poste de contrôle. |
| `[galaxy]` | Groupe ciblé par le playbook. |
| `docker-test` | Alias libre de cette cible dans l'inventaire. |
| `ansible_host`, `ansible_port` | Adresse et port SSH publiés par Docker. |
| `ansible_user` | Compte SSH qui réalise l'installation avec sudo. |
| `ansible_ssh_private_key_file` | Clé privée jetable utilisée pour cette connexion. |
| `IdentitiesOnly=yes` | Évite de présenter les autres clés d'un éventuel agent SSH. |
| `StrictHostKeyChecking=accept-new`, `UserKnownHostsFile` | Enregistre la clé du serveur dans un fichier isolé pour ce test. |

Le rôle `common` crée ensuite le compte applicatif `mviewer` pour les services, les données et les journaux.

## Générer les paramètres de test

```bash
python3 - "$MVIEWER_TEST_DIR" <<'PY'
import json
import secrets
import sys
from pathlib import Path

root = Path(sys.argv[1])
(root / "vars.json").write_text(json.dumps({
    "postgres_database": "donneessig",
    "postgres_username": "usersig",
    "postgres_password": secrets.token_hex(32),
    "mviewerstudio_secret_key": secrets.token_hex(32),
    "geoserver_admin_username": "admin",
    "geoserver_admin_password": "geoserver",
    "nginx_server_name": "localhost",
}))
(root / "vars.json").chmod(0o600)
PY
ansible-vault encrypt "$MVIEWER_TEST_DIR/vars.json"
```

| Élément | Explication |
|---|---|
| `vars.json` | Variables de test chiffrées avec Ansible Vault ; JSON permet de générer les variables Ansible sans dépendance YAML. |
| `postgres_password` | Mot de passe aléatoire partagé par PostgreSQL et GeoServer. |
| `geoserver_admin_username`, `geoserver_admin_password` | Identifiants initiaux `admin` / `geoserver` du serveur jetable, stockés dans le fichier chiffré. |
| `mviewerstudio_secret_key` | Clé de session aléatoire nécessaire à Studio. |
| `nginx_server_name` | Nom de serveur HTTP utilisé pour l'accès local. |
| `0o600` | Réserve la lecture et l'écriture de ces secrets à leur propriétaire. |

Le template `ansible/roles/postgres/templates/pg_hba.conf.j2` autorise déjà les connexions locales nécessaires à GeoServer. Le port PostgreSQL n'est pas publié sur l'hôte.

## Exécuter le déploiement

```bash
cd ansible

ansible galaxy -i "$MVIEWER_TEST_DIR/hosts.ini" \
  -m ansible.builtin.wait_for_connection -a 'timeout=60'

ansible-playbook playbooks/install.yml \
  -i "$MVIEWER_TEST_DIR/hosts.ini" \
  --tags check

ansible-playbook playbooks/install.yml \
  -i "$MVIEWER_TEST_DIR/hosts.ini" \
  -e @"$MVIEWER_TEST_DIR/vars.json" --ask-vault-pass
```

| Élément | Explication |
|---|---|
| `ansible/` | Répertoire depuis lequel lancer Ansible pour charger `ansible.cfg`, les rôles et les modules partagés. |
| `-i` | Sélectionne exclusivement l'inventaire du conteneur. |
| `wait_for_connection`, `timeout=60` | Attend jusqu'à 60 secondes que la connexion Ansible soit utilisable. |
| `-e @…/vars.json --ask-vault-pass` | Charge les paramètres et secrets jetables du test. |
| `--tags check` | Vérifie les prérequis ; ce contrôle effectue notamment des téléchargements APT temporaires. |
| `playbooks/install.yml` | Lance l'installation complète des applications et des services. |

Aucun mot de passe sudo n'est demandé pour `deploy` dans cette image.

Relancer la dernière commande pour vérifier l'idempotence : à configuration et sources inchangées, le récapitulatif doit indiquer `changed=0` et `failed=0`.

## Mettre à jour les couleurs et l’image de l’accueil

Modifier `header/theme.css`, `header/custom.css` ou `home/config.js`, puis
recopier les fichiers sur le conteneur depuis `ansible/` :

```bash
ansible-playbook playbooks/update_home.yml -i "$MVIEWER_TEST_DIR/hosts.ini"
```

Le compte SSH de test dispose de sudo sans mot de passe. Aucun secret applicatif
n’est requis pour cette commande. Recharger ensuite `http://localhost:8088/accueil/`.

## Configurer le front de Studio

Le fichier `docs/examples/ansible-docker/mviewerstudio/src/static/config.json` fournit une configuration du front adaptée à cette cible.

Depuis `ansible/`, après le déploiement :

```bash
docker cp ../docs/examples/ansible-docker/mviewerstudio/src/static/config.json \
  mviewer-galaxy-ansible-test:/var/lib/mviewer-galaxy/mviewerstudio-config.json
docker cp ../docs/examples/ansible-docker/nginx-localhost.conf \
  mviewer-galaxy-ansible-test:/etc/nginx/conf.d/ansible-test-localhost.conf
docker exec mviewer-galaxy-ansible-test nginx -t
docker exec mviewer-galaxy-ansible-test systemctl reload nginx
```

| Élément | Explication |
|---|---|
| `src/static/config.json` | Format de configuration du front de mviewerstudio. |
| `/var/lib/mviewer-galaxy/mviewerstudio-config.json` | Copie servie par nginx à `/mviewerstudio/config.json` dans l'installation Ansible. |
| `api/app`, `api/style`, `api/user` | API Studio relatives au préfixe `/mviewerstudio/`. |
| `mviewer_instance` | URL complète du visualiseur : `http://localhost:8088/mviewer/`, nécessaire à l’API de chargement XML. |
| `nginx-localhost.conf` | Relais interne de `127.0.0.1:8088` vers nginx sur le port 80, pour que le backend puisse charger la même URL que le navigateur. Inclus dans les nouvelles images de test ; copié ici pour les conteneurs existants. |
| `conf_path_from_mviewer` | Prévisualise les cartes générées dans `/mviewer/store/`. |
| `publish_url` | Ouvre les cartes publiées dans `/mviewer/public/` ; `{{config}}` est remplacé par Studio. |
| `data_providers.wms` | Utilise `/geoserver/donnessig/wms` sur le même hôte et le même port que Studio, sans CORS supplémentaire. |
| `proxy` | Vide pour contacter directement le WMS local depuis le navigateur. |
| `external_themes.used` | Désactive le catalogue de thèmes externe pour ce test. |
| `baselayers.osm` | Fond OpenStreetMap, nécessitant un accès Internet depuis le navigateur. |

Le workspace `donnessig` est créé par Ansible, mais une couche doit être publiée dans GeoServer pour apparaître dans le catalogue WMS.

Recharger Studio dans le navigateur. Le rechargement nginx active le relais ; Studio lui-même n'a pas besoin de redémarrer.

Cette copie sert au test manuel : une nouvelle exécution du rôle `mviewerstudio` régénère le fichier à partir des sources de Studio et remplace cette personnalisation.

## Vérifier les applications

| URL depuis le poste de contrôle | Service | Port dans le conteneur |
|---|---|---|
| `http://localhost:8088/accueil/` | Accueil | nginx 80 |
| `http://localhost:8088/mviewer/` | Mviewer | nginx 80 |
| `http://localhost:8088/mviewerstudio/` | Studio via nginx | Gunicorn 5007 |
| `http://localhost:8088/geoserver/` | GeoServer via nginx | Jetty 8080 |

Ces URL supposent les préfixes et ports applicatifs par défaut. Seul nginx est publié ; les services internes restent accessibles dans le conteneur.

```bash
docker exec mviewer-galaxy-ansible-test \
  systemctl status nginx mviewerstudio geoserver postgresql logrotate.timer --no-pager
docker exec mviewer-galaxy-ansible-test nginx -t
docker exec --user postgres mviewer-galaxy-ansible-test \
  psql -d donneessig --command='SELECT PostGIS_Full_Version();'
```

- `nginx`, `mviewerstudio`, `geoserver`, `postgresql` : services installés par les rôles.

- `logrotate.timer` : planification de la rotation des journaux.

- `donneessig` : base SIG créée pour le test.

- `PostGIS_Full_Version()` : confirme la présence et la version de PostGIS dans cette base.

Les données et les journaux utilisent les [répertoires de l'installation native](/mviewer-galaxy/guides/installation-ansible/#install-components).

## Dépanner la cible

```bash
docker logs mviewer-galaxy-ansible-test
docker exec mviewer-galaxy-ansible-test systemctl status ssh --no-pager
docker info --format '{{.CgroupVersion}} {{.CgroupDriver}}'
```

- `ssh` : service nécessaire à la connexion Ansible.

- `CgroupVersion` : doit afficher `2` pour la configuration décrite ici.

- Si systemd ne démarre pas, vérifier le mode Docker et les options de lancement avant d'exécuter Ansible : la cible doit fournir `/run/systemd/system`.

- Si les ports 2222 ou 8088 sont occupés, adapter les ports publiés ; répercuter le port SSH dans `ansible_port` et le port HTTP dans les URL.

Pour les erreurs d'installation ou les journaux applicatifs, consulter le [Dépannage Ansible](/mviewer-galaxy/guides/ansible/depannage/).

## Supprimer l'environnement de test

```bash
docker rm -f mviewer-galaxy-ansible-test
rm -rf "${MVIEWER_TEST_DIR:?}"
unset MVIEWER_TEST_DIR
```

- `mviewer-galaxy-ansible-test` : sa suppression efface les applications, la base et les données contenues dans cette cible sans volumes.

- `MVIEWER_TEST_DIR` : sa suppression retire les clés SSH, les secrets et l'inventaire de test du poste de contrôle.

L'image Docker reste disponible pour recommencer avec une cible neuve.
