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
| `group_vars/all/` | One file per application and `common.yml` for shared settings |
| `site.yml` | Deployment settings, loaded with `-e @site.yml` |
| `secrets.vault.yml` | PostgreSQL and GeoServer credentials, Studio session key and optional OIDC/SSH/sudo secrets |
| `roles/postgres/templates/pg_hba.conf.j2` | PostgreSQL access rules to prepare before installation |

- Variables passed with `-e` take precedence over playbook values.

- Ansible reads `secrets.vault.yml` on the control machine without executing it through a shell.

## Variables by application

| File | Settings |
|---|---|
| `group_vars/all/common.yml` | System accounts, shared paths, common packages and public URL scheme |
| `group_vars/all/mviewer.yml` | Git source and version, shared apps/store/public directories |
| `group_vars/all/mviewerstudio.yml` | Git source and version, Gunicorn, paths and public OIDC settings |
| `group_vars/all/nginx.yml` | Public server name, HTTP port and logs |
| `group_vars/all/postgres.yml` | Packages, database and user defaults, port, socket and pg_hba template |
| `group_vars/all/geoserver.yml` | Version, archive checksum, Java, paths, ports and PostGIS catalog |
| `group_vars/all/geoserver_extensions.yml` | Extension list with URLs and SHA-256 checksums |

- Both main playbooks explicitly load these files through `vars_files`, including when using a different inventory.

- Keep deployment overrides in `site.yml`, loaded with `-e @site.yml`. Extra variables override the supplied values; when several `-e @…` files define the same variable, the last file takes precedence.

- Only the reusable `logging` role retains internal defaults in `roles/logging/defaults/main.yml`.

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

## One Vault for application secrets

| Variables | Required for |
|---|---|
| `postgres_password` | PostgreSQL and GeoServer |
| `postgres_database`, `postgres_username` | Shared database identifiers; defaults are supplied by `postgres.yml` and can be overridden in Vault |
| `geoserver_admin_username`, `geoserver_admin_password` | GeoServer REST access, from the first installation |
| `mviewerstudio_secret_key` | Full deployment; at least 32 random characters, including in `public` mode |
| `mviewerstudio_oidc_client_secret` | Full deployment in `authlib` mode, together with the issuer and client ID |
| `ansible_password`, `ansible_become_password` | Optional SSH/sudo passwords, if required for connection |

- Copy `secrets.example.yml` once, fill in the required values and encrypt it with `ansible-vault encrypt secrets.vault.yml`.

- For later changes, use `ansible-vault edit secrets.vault.yml`; keep the existing secrets and database identifiers.

- Load it explicitly with `-e @secrets.vault.yml --ask-vault-pass`. The `.vault.yml` suffix alone does not encrypt a file or make Ansible load it.

- Use separate Vault files for separate environments, selecting the matching inventory and Vault at deployment time.

- Secret-bearing tasks use `no_log`; Studio environment rendering also disables `--diff` and writes a root-only `0600` file under `/etc/mviewerstudio/` (`0700`). Vault encryption protects the source file on the control machine.

## GIS database and network access

Copy `secrets.example.yml` to `secrets.vault.yml` if it does not exist, then configure the GIS credentials before encryption. Use `ansible-vault edit secrets.vault.yml` if it is already encrypted:

```yaml
postgres_database: donneessig
postgres_username: usersig
postgres_password: ""
```

| Element | Explanation |
|---|---|
| `postgres_database` | GIS database to create; `donneessig` is the default. |
| `postgres_username` | SQL account owning the database and `public` schema; `usersig` is the default. |
| `postgres_password` | Required SQL password to fill in; do not leave it empty. |

- Enter a password.

- Database and user names accept 1 to 63 lowercase letters, digits and underscores, without a leading digit.

- Values may be quoted.

- `$`, `%`, `#` and `=` remain literal.

- Values follow YAML syntax; use single quotes for literal strings containing special characters and double any embedded single quote.

- Encrypt with `ansible-vault encrypt secrets.vault.yml`, then load with `-e @secrets.vault.yml --ask-vault-pass`. Edit it with `ansible-vault edit secrets.vault.yml`.

- `postgres_port` and `postgres_socket_dir` select the local PostgreSQL server to configure.

- Allowed IP addresses belong in `pg_hba.conf.j2`.

- The role replaces the whole `pg_hba.conf` file with this template: keep local administration and include any required rules.

- Add allowed clients before the `reject` rules.

- The role sets `listen_addresses = '*'`.

- Configure the firewall for the desired access.

- The SQL user owns the database and the `public` schema.

- To change the password, run `ansible-vault edit secrets.vault.yml` and rerun the full deployment to update both PostgreSQL and GeoServer.

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

- The GeoServer role creates the default workspace and a store connected to the database from `secrets.vault.yml`, without publishing layers.

- Supply `geoserver_admin_username` and `geoserver_admin_password` in Vault from the first installation. Use the current server credentials and update Vault after changing them in GeoServer.

- The role uses this password without changing it.

- Studio always requires `mviewerstudio_secret_key`.

- For OIDC, set `mviewerstudio_auth_mode: authlib`.

- Configure the issuer, client and secret through `mviewerstudio_oidc_*`.

- The callback must match the domain, public scheme and `mviewerstudio_url_prefix`.

## Add or update GeoServer extensions

### Edit the extension list

Open `group_vars/all/geoserver_extensions.yml`. It contains the target version
and each extension's name, HTTPS URL and SHA-256 checksum. The full deployment
installs this selection; the dedicated playbook can add extensions afterwards.

| Feature | Extension identifier |
|---|---|
| OGC API Features | `ogcapi-features` |
| SLD service | `sldservice` |
| DXF, Excel, GeoPackage, KML/KMZ output | `dxf`, `excel`, `geopkg-output`, `kml` |
| OGR output and vector tiles | `ogr-wfs`, `vectortiles` |
| Image Pyramid coverage | `pyramid` |
| Data import | `importer` |
| YSLD, CSS and Chart Symbolizer styling | `ysld`, `css`, `charts` |

The default selection includes 13 extensions. It excludes GDAL raster support.
DXF, Excel and OGR output target WFS; WPS is not installed. The DXF entry uses
`exclude_jars` to skip its optional WPS JAR, following the
[DXF installation instructions](https://docs.geoserver.org/stable/en/user/extensions/dxf/).

OGR requires `gdal-bin` for `ogr2ogr`. Image Pyramid adds `python3-gdal` for the
`gdal_retile.py` preparation tool. These packages are installed according to the
selection and verified by the `check` role. This selection requires no GDAL
Java/JNI bindings.

To add an extension, append an entry to the list. This is the supplied CSS entry:

```yaml
  - name: css
    url: https://downloads.sourceforge.net/project/geoserver/GeoServer/3.0.2/extensions/geoserver-3.0.2-css-plugin.zip
    checksum: sha256:fd067a425f883f9aafbeb555c5f0033daa45e55652df7ea53d2700cea68e402d
```

Match the archive version exactly to `geoserver_version` and compute its SHA-256
from the downloaded file:

```bash
sha256sum geoserver-3.0.2-css-plugin.zip
```

See the [official GeoServer release page](https://geoserver.org/release/3.0.2/)
for the release and available extensions.

### Apply changes to an installed GeoServer

Run from `ansible/` on the control machine, first in check mode, then normally:

```bash
ansible-playbook playbooks/geoserver_extensions.yml -e @site.yml --ask-become-pass --check --diff
ansible-playbook playbooks/geoserver_extensions.yml -e @site.yml --ask-become-pass
```

Omit `-e @site.yml` if the file does not exist. This playbook requires no
application secrets and does not rerun PostgreSQL, Studio or catalog configuration.
If SSH/sudo passwords are stored in Vault, add
`-e @secrets.vault.yml --ask-vault-pass`.

The dedicated `geoserver_extensions` role verifies checksums and shared libraries
before changing the service. When JAR files differ, it stops GeoServer, installs
only new or changed files, starts the service and waits for the web interface.
An unchanged second run does not restart GeoServer.

Check mode reports archives missing from cache without downloading them; their
contents will be validated during a normal run.

The role installs and updates listed extensions. Removing an entry does not
delete its installed JAR files, as libraries may be shared.

### Verify installation

Open `http://<server>/geoserver/web/` and check module status. Verify output
formats in WFS/WMS capabilities, available style formats and Image Pyramid when
creating a raster store. OGC API Features is served at `/geoserver/ogc/features/v1`.

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

## Run a single role or upgrade

```bash
ansible-playbook playbooks/install.yml --tags check -e @site.yml --ask-become-pass
ansible-playbook playbooks/install.yml --tags postgres -e @site.yml -e @secrets.vault.yml --ask-vault-pass --ask-become-pass
ansible-playbook playbooks/install.yml --tags geoserver -e @site.yml -e @secrets.vault.yml --ask-vault-pass --ask-become-pass
ansible-playbook playbooks/upgrade_mviewer.yml -e @site.yml --ask-become-pass
```

- Omit `-e @site.yml` if no site file was created, and `--ask-become-pass` when sudo does not require a password.

- The `postgres` and `geoserver` tags do not require Studio secrets. GeoServer needs an existing PostGIS database; run `postgres` first if necessary.

- Checks and Mviewer upgrades need no application secrets; load Vault if it contains the SSH/sudo passwords required for connection.
