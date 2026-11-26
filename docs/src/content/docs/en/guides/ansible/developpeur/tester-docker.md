---
title: "Test in a Docker container"
description: "Use an Ubuntu target with systemd and SSH to test Ansible roles without a VM."
---

This disposable container replaces a VM when testing the native Ansible installation: the roles install PostgreSQL, GeoServer, Mviewer, Studio and nginx inside it.

It shares the host kernel, so it does not validate every aspect of a VM or physical server.

## Prepare the control machine

- Use Linux with Docker Engine, cgroups v2 and access to the Docker daemon. This procedure targets regular Docker; rootless Docker and Docker Desktop are outside its scope.

- Install Ansible Core 2.16+, Python 3 and the OpenSSH client on the control machine.

- Clone the repository and provide network access to APT repositories, Git repositories and application downloads.

- Start at the repository root and keep the same terminal open to preserve `MVIEWER_TEST_DIR`.

The container uses `--privileged` to run systemd. Use a trusted development machine: this mode grants extensive host privileges. See the [Docker documentation](https://docs.docker.com/reference/cli/docker/container/run/#privileged).

## Build and start the target

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

| Item | Explanation |
|---|---|
| `docs/examples/ansible-docker/Dockerfile` | Ubuntu 24.04 image with systemd, SSH, sudo and Python. Ansible installs the applications afterwards. |
| `mviewer-galaxy-ansible-test` | Test image and container name. |
| `MVIEWER_TEST_DIR` | Temporary control-machine directory for the SSH key, inventory and disposable secrets. |
| `--cgroupns=private` | Container-specific cgroup namespace for systemd. |
| `--tmpfs /run`, `--tmpfs /run/lock` | Temporary runtime directories for services. |
| `127.0.0.1:2222:22` | SSH published on port 2222, accessible only from the control machine. |
| `127.0.0.1:8088:80` | nginx published on port 8088, accessible only from that machine. |

No real server directory is mounted: applications and data stay inside the container.

## Configure SSH

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

| Item | Explanation |
|---|---|
| `deploy` | SSH account created in the image with passwordless sudo, exclusively for this test. |
| `authorized_keys` | Receives the public key only; the private key stays on the control machine. |
| `[galaxy]` | Inventory group targeted by the playbook. |
| `docker-test` | Arbitrary inventory alias for this target. |
| `ansible_host`, `ansible_port` | Address and SSH port published by Docker. |
| `ansible_user` | SSH account performing the installation through sudo. |
| `ansible_ssh_private_key_file` | Disposable private key for this connection. |
| `IdentitiesOnly=yes` | Prevents an SSH agent from offering unrelated keys. |
| `StrictHostKeyChecking=accept-new`, `UserKnownHostsFile` | Records the server key in a separate file for this test. |

The `common` role then creates the application account `mviewer` for services, data and logs.

## Generate test settings

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

| Item | Explanation |
|---|---|
| `vars.json` | Test variables encrypted with Ansible Vault; JSON is used to generate valid Ansible variables without a YAML dependency. |
| `postgres_password` | Random password shared by PostgreSQL and GeoServer. |
| `geoserver_admin_username`, `geoserver_admin_password` | Initial `admin` / `geoserver` credentials for this disposable server, stored in the encrypted file. |
| `mviewerstudio_secret_key` | Random session key required by Studio. |
| `nginx_server_name` | HTTP server name for local access. |
| `0o600` | Restricts secret-file reading and writing to their owner. |

The `ansible/roles/postgres/templates/pg_hba.conf.j2` template already allows the local connections required by GeoServer. PostgreSQL's port is not published on the host.

## Run the deployment

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

| Item | Explanation |
|---|---|
| `ansible/` | Run Ansible here to load `ansible.cfg`, roles and shared modules. |
| `-i` | Selects only the container inventory. |
| `wait_for_connection`, `timeout=60` | Waits up to 60 seconds for a usable Ansible connection. |
| `-e @…/vars.json --ask-vault-pass` | Loads the disposable test settings and secrets. |
| `--tags check` | Checks prerequisites, including temporary APT downloads. |
| `playbooks/install.yml` | Installs all applications and services. |

The image's `deploy` account does not require a sudo password.

Run the last command again to check idempotence: with unchanged configuration and sources, the recap should show `changed=0` and `failed=0`.

## Update the home-page colors and image

Edit `header/theme.css`, `header/custom.css` or `home/config.js`, then copy the
files to the container from `ansible/`:

```bash
ansible-playbook playbooks/update_home.yml -i "$MVIEWER_TEST_DIR/hosts.ini"
```

The test SSH account has passwordless sudo. This command requires no application
secrets. Reload `http://localhost:8088/accueil/` afterwards.

## Configure the Studio front end

The file `docs/examples/ansible-docker/mviewerstudio/src/static/config.json` provides a front-end configuration for this target.

From `ansible/`, after deployment:

```bash
docker cp ../docs/examples/ansible-docker/mviewerstudio/src/static/config.json \
  mviewer-galaxy-ansible-test:/var/lib/mviewer-galaxy/mviewerstudio-config.json
docker cp ../docs/examples/ansible-docker/nginx-localhost.conf \
  mviewer-galaxy-ansible-test:/etc/nginx/conf.d/ansible-test-localhost.conf
docker exec mviewer-galaxy-ansible-test nginx -t
docker exec mviewer-galaxy-ansible-test systemctl reload nginx
```

| Item | Explanation |
|---|---|
| `src/static/config.json` | mviewerstudio front-end configuration format. |
| `/var/lib/mviewer-galaxy/mviewerstudio-config.json` | Copy served by nginx at `/mviewerstudio/config.json` in the Ansible installation. |
| `api/app`, `api/style`, `api/user` | Studio APIs relative to the `/mviewerstudio/` prefix. |
| `mviewer_instance` | Full viewer URL: `http://localhost:8088/mviewer/`, required by the XML loading API. |
| `nginx-localhost.conf` | Internal relay from `127.0.0.1:8088` to nginx on port 80, allowing the backend to fetch the same URL as the browser. Included in newly built test images; copied here for existing containers. |
| `conf_path_from_mviewer` | Previews generated maps under `/mviewer/store/`. |
| `publish_url` | Opens published maps under `/mviewer/public/`; Studio replaces `{{config}}`. |
| `data_providers.wms` | Uses `/geoserver/donnessig/wms` on the same host and port as Studio, without additional CORS configuration. |
| `proxy` | Empty to let the browser contact the local WMS directly. |
| `external_themes.used` | Disables the external theme catalogue for this test. |
| `baselayers.osm` | OpenStreetMap base layer, requiring Internet access from the browser. |

Ansible creates the `donnessig` workspace, but a layer must be published in GeoServer to appear in the WMS catalogue.

Reload Studio in the browser. The nginx reload activates the relay; Studio itself does not need a restart.

This copy is for manual testing: running the `mviewerstudio` role again regenerates the file from Studio sources and replaces this customization.

## Check applications

| URL on the control machine | Service | Container port |
|---|---|---|
| `http://localhost:8088/accueil/` | Home page | nginx 80 |
| `http://localhost:8088/mviewer/` | Mviewer | nginx 80 |
| `http://localhost:8088/mviewerstudio/` | Studio through nginx | Gunicorn 5007 |
| `http://localhost:8088/geoserver/` | GeoServer through nginx | Jetty 8080 |

These URLs assume default application prefixes and ports. Only nginx is published; internal services remain inside the container.

```bash
docker exec mviewer-galaxy-ansible-test \
  systemctl status nginx mviewerstudio geoserver postgresql logrotate.timer --no-pager
docker exec mviewer-galaxy-ansible-test nginx -t
docker exec --user postgres mviewer-galaxy-ansible-test \
  psql -d donneessig --command='SELECT PostGIS_Full_Version();'
```

- `nginx`, `mviewerstudio`, `geoserver`, `postgresql`: services installed by the roles.

- `logrotate.timer`: schedules log rotation.

- `donneessig`: GIS database created for the test.

- `PostGIS_Full_Version()`: confirms the presence and version of PostGIS in this database.

Data and logs use the [native installation directories](/mviewer-galaxy/en/guides/installation-ansible/#install-components).

## Troubleshoot the target

```bash
docker logs mviewer-galaxy-ansible-test
docker exec mviewer-galaxy-ansible-test systemctl status ssh --no-pager
docker info --format '{{.CgroupVersion}} {{.CgroupDriver}}'
```

- `ssh`: service required for the Ansible connection.

- `CgroupVersion`: must show `2` for this setup.

- If systemd fails to start, check the Docker mode and startup options before running Ansible: the target must provide `/run/systemd/system`.

- If ports 2222 or 8088 are busy, change the published ports; update `ansible_port` for SSH and the URLs for HTTP accordingly.

For installation failures or application logs, see [Ansible troubleshooting](/mviewer-galaxy/en/guides/ansible/depannage/).

## Remove the test environment

```bash
docker rm -f mviewer-galaxy-ansible-test
rm -rf "${MVIEWER_TEST_DIR:?}"
unset MVIEWER_TEST_DIR
```

- `mviewer-galaxy-ansible-test`: deleting this container removes its applications, database and data because this setup uses no volumes.

- `MVIEWER_TEST_DIR`: deleting this directory removes the SSH keys, secrets and test inventory from the control machine.

The Docker image remains available to start again with a fresh target.
