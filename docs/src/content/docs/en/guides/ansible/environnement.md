---
title: "Adapt to your environment"
description: "Customize the inventory, variables, PostgreSQL, GeoServer and paths for an Ansible deployment."
---

- Run commands from `ansible/` to load `ansible.cfg` and its local modules.

- For the full procedure, see [Installation](/mviewer-galaxy/en/guides/installation-ansible/).

## Choose the right file

| File | Purpose |
|---|---|
| `inventories/dev/hosts.ini` | SSH address, sudo account and private key |
| `group_vars/all.yml` | Shared defaults supplied by the repository |
| `roles/*/defaults/main.yml` | Role defaults |
| `site.yml` | Deployment settings, loaded with `-e @site.yml` |
| `.env` | GIS database, SQL user and password |
| `secrets.vault.yml` | Studio session key and secrets encrypted with Ansible Vault |
| `roles/postgres/templates/pg_hba.conf.j2` | PostgreSQL access rules to prepare before installation |

- Variables passed with `-e` take precedence over playbook values.

- Ansible reads `.env` on the control machine without executing it through a shell.

## SSH connection and public domain

```ini
[galaxy]
production ansible_host=server.example.org ansible_user=deploy ansible_port=22
```

| Element | Explanation |
|---|---|
| `[galaxy]` | Server group targeted by the playbooks; keep this name. |
| `production` | Arbitrary alias to customize when identifying the server in Ansible. |
| `ansible_host` | Target server domain name or IP address, reachable from the control machine. |
| `ansible_user` | SSH account with sudo that performs the installation; replace the example `deploy` account. |
| `ansible_port` | Target SSH port; add this variable if the port differs from `22`. |
| `ansible_ssh_private_key_file` | Private key path on the control machine when a specific key is needed. |
| `--ask-become-pass` | Prompts for the SSH account sudo password. |

The application account is configured separately through `galaxy_user` and `galaxy_group`, both set to `mviewer` by default.

Set the public domain and ports in `site.yml`:

```yaml
nginx_server_name: maps.example.org
nginx_http_port: 80
mviewerstudio_port: 5007
geoserver_port: 8080
galaxy_public_scheme: http
```

| Element | Explanation |
|---|---|
| `nginx_server_name` | Public site domain; replace `maps.example.org` and configure its DNS. |
| `nginx_http_port` | HTTP port nginx listens on at the target; `80` by default. |
| `mviewerstudio_port` | Internal Gunicorn port; `5007` by default. |
| `geoserver_port` | Internal Jetty port; `8080` by default. |
| `galaxy_public_scheme` | Public `http` or `https` scheme forwarded to applications by nginx. |

- Nginx serves `/home/`, `/mviewer/`, `/mviewerstudio/` and `/geoserver/`.

- Studio and GeoServer listen locally by default.

- Behind a TLS terminator, use `galaxy_public_scheme: https`.

- This variable does not install a certificate.

## GIS database and network access

Configure `.env`, which Git ignores:

```dotenv
POSTGRES_DB=donneessig
POSTGRES_USER=usersig
POSTGRES_PASSWORD=
```

| Element | Explanation |
|---|---|
| `POSTGRES_DB` | GIS database to create; `donneessig` is the default. |
| `POSTGRES_USER` | SQL account owning the database and `public` schema; `usersig` is the default. |
| `POSTGRES_PASSWORD` | Required SQL password to fill in; do not leave it empty. |

- Enter a password.

- Database and user names accept 1 to 63 lowercase letters, digits and underscores, without a leading digit.

- Values may be quoted.

- `$`, `%`, `#` and `=` remain literal.

- Put comments on separate lines.

- To use another file, set `postgres_env_file` in `site.yml` to an absolute path on the control machine.

- `postgres_port` and `postgres_socket_dir` select the local PostgreSQL server to configure.

- Allowed IP addresses belong in `pg_hba.conf.j2`.

- The role replaces the whole `pg_hba.conf` file with this template: keep local administration and include any required rules.

- Add allowed clients before the `reject` rules.

- The role sets `listen_addresses = '*'`.

- Configure the firewall for the desired access.

- The SQL user owns the database and the `public` schema.

- To change the password, edit `.env` and rerun the full deployment to update both PostgreSQL and GeoServer.

- Changing a database name does not migrate the old database's data.

- Existing tables retain their own owners.

## GeoServer and Studio

```yaml
geoserver_workspace: donnessig
geoserver_datastore: postgis
geoserver_postgres_host: 127.0.0.1
geoserver_postgres_port: 5432
mviewerstudio_auth_mode: public
```

| Element | Explanation |
|---|---|
| `geoserver_workspace` | GeoServer workspace to create and select as default: `donnessig` in this example. |
| `geoserver_datastore` | Name of the PostGIS store inside the workspace: `postgis` in this example. |
| `geoserver_postgres_host` | PostgreSQL address as seen by GeoServer; `127.0.0.1` for the local database. |
| `geoserver_postgres_port` | SQL port used by the GeoServer store; must match the PostgreSQL server port. |
| `mviewerstudio_auth_mode` | `public` allows access without signing in; `authlib` enables OIDC. |

- The GeoServer role creates the default workspace and a store connected to the database from `.env`, without publishing layers.

- Supply the current administrator password through `geoserver_admin_password` in Vault if it differs from the initial `geoserver` value.

- The role uses this password without changing it.

- Studio always requires `mviewerstudio_secret_key`.

- For OIDC, set `mviewerstudio_auth_mode: authlib`.

- Configure the issuer, client and secret through `mviewerstudio_oidc_*`.

- The callback must match the domain, public scheme and `mviewerstudio_url_prefix`.

## Paths and versions

| Variable | Default | Purpose |
|---|---|---|
| `galaxy_install_dir` | `/var/www/mviewergalaxy` | Site root containing the home page and Mviewer sources |
| `mviewerstudio_install_dir` | `/srv/apps/mviewerstudio` | Studio sources and its Python virtual environment |
| `mviewer_apps_dir` | `/srv/data/mviewer/apps` | Mviewer map configurations |
| `mviewer_store_dir` | `/srv/data/mviewer/store` | Maps saved by Studio |
| `mviewer_public_dir` | `/srv/data/mviewer/public` | Maps published by Studio |
| `geoserver_data_dir` | `/srv/data/geoserver/datadir` | GeoServer catalog, data and security configuration |
| `galaxy_logs_dir` | `/srv/logs` | Log root with one directory per application |

- Mviewer links, nginx and Studio permissions follow these variables.

- Back up the existing data directories.

- Move existing data before changing paths: the playbook does not migrate data automatically.

- Pin `mviewer_version` and `mviewerstudio_version` to tags or SHAs for reproducible deployments.

- For GeoServer, update `geoserver_version` together with `geoserver_archive_checksum`.

- `logging_rotate` sets the number of retained log archives (14 by default).
