---
title: "Installation"
description: "Install Mviewer, Studio, PostgreSQL/PostGIS and GeoServer on a server running systemd."
sidebar:
  order: 2
next:
  label: "Adapt to your environment"
  link: /mviewer-galaxy/en/guides/ansible/environnement/
---

- The playbook installs Mviewer, Studio with Gunicorn, PostgreSQL/PostGIS, GeoServer with Jetty and Java 21, nginx and logrotate.

- Applications run as systemd services.

- Studio uses public access by default.

- OIDC authentication can be enabled with an external provider.

## Overall installation plan

| Step | Action | Expected result |
|---|---|---|
| 1. [Check prerequisites](#install-prerequisites) | Prepare Ansible on the control machine and a target with systemd, Python 3.11+ and Java 21 available through APT. | An environment compatible with the roles. |
| 2. [Configure SSH](#install-ssh) | Set the server address and SSH account with sudo in the inventory. | A reachable server in the `galaxy` group. |
| 3. [Set site parameters](#install-site) | Create `site.yml` with the public domain and desired settings. | Deployment-specific configuration. |
| 4. [Prepare the GIS database](#install-database) | Set the database, SQL user and password in `secrets.vault.yml`. | Credentials shared by PostgreSQL and GeoServer. |
| 5. [Prepare PostgreSQL access](#install-network) | Set server interfaces and allowed clients in `site.yml`. | Network rules ready before installation. |
| 6. [Prepare secrets](#install-secrets) | Set GeoServer credentials, the Studio key and optional OIDC secrets, then encrypt Vault. | Secrets available to the playbook. |
| 7. [Check and deploy](#install-deployment) | Check prerequisites, then run the playbook with site settings and secrets. | Applications installed and services configured. |
| 8. [Check applications](#install-applications) | Open public URLs and [inspect services and logs](#install-operations). | Home page, Mviewer, Studio and GeoServer available. |
| 9. [Configure CORS if needed](#install-cors) | Allow client origins when maps query GeoServer from another origin. | Browser requests allowed for those clients. |

<div class="ansible-section-anchor" id="install-components"></div>

## Dependencies and versions

- The versions below match the repository defaults.

- APT package versions depend on the target distribution and configured repositories.

- The playbook does not pin them to specific releases.

| Component | Default version or reference | Installation and configuration |
|---|---|---|
| Mviewer | `master` branch | Git sources; `mviewer_version` also accepts a tag or SHA |
| Mviewer Studio | `oauth2-proxy-keycloak` branch | Git sources; `mviewerstudio_version` also accepts a tag or SHA |
| GeoServer | `3.0.2` | Official archive; `geoserver_version` and `geoserver_archive_checksum` |
| Jetty | `12.1.14` | Bundled with the GeoServer `3.0.2` archive; its version follows the GeoServer distribution |
| Java / OpenJDK | `21` | APT package `openjdk-21-jre-headless`; patches come from the target repositories |
| Python | `3.11` minimum | Existing Python or APT package `python3`, with `python3-pip` and `python3-venv` |
| Gunicorn | `>20` in the current Studio dependencies | Installed by pip in the Studio virtual environment, following `install/requirements.txt` from the deployed revision |
| PostgreSQL | Version provided by the target APT repositories | Package `postgresql`, configurable through `postgres_packages` |
| PostGIS | Version provided by the target APT repositories | Packages `postgresql-postgis` and `postgis`, for the PostgreSQL version supplied by those repositories |
| nginx | Version provided by the target APT repositories | Package `nginx`; serves pages and proxies Studio and GeoServer |
| logrotate | Version provided by the target APT repositories | Package `logrotate`, with `logrotate.timer` enabled |
| System tools and libraries | Versions provided by the target APT repositories | `git`, `ca-certificates`, `unzip`, `libxml2-dev`, `libxslt1-dev` |

- Other Studio Python dependencies also follow its `install/requirements.txt`.

- Git branches can change: use a tag or SHA to pin sources.

- Ansible Core `2.16+` on the control machine and systemd on the target are prerequisites rather than components installed by the playbook.

- For detailed settings, see [Adapt to your environment](/mviewer-galaxy/en/guides/ansible/environnement/).

- If a deployment fails, check [Ansible troubleshooting](/mviewer-galaxy/en/guides/ansible/depannage/).

<div class="ansible-section-anchor" id="install-prerequisites"></div>

## Prerequisites

- Control machine: Ansible Core 2.16 or later and a copy of this repository.
- Target: Debian 12+ or Ubuntu 22.04+, running systemd, with an SSH account that can use sudo.
- Python 3.11+ and `openjdk-21-jre-headless` installed or available in the target's APT repositories.
- Outbound access to APT, Git and Python repositories, plus SourceForge and its mirrors for GeoServer.

- The `common` role can install Python if it is missing and available through APT.

- The base repositories of some releases, including Debian 12, do not provide Java 21: prepare a suitable repository before deployment.

- The roles do not add a Java repository.

- No external Ansible collection is required.

Run every command below from the repository's `ansible/` directory so that Ansible loads `ansible.cfg` and its local modules:

```bash
cd ansible
```

<div class="ansible-section-anchor" id="install-ssh"></div>

## Configure the SSH connection

Edit `inventories/dev/hosts.ini`:

```ini
[galaxy]
mviewer-dev ansible_host=server.example.org ansible_user=deploy
```

| Element | Explanation |
|---|---|
| `[galaxy]` | Server group targeted by the playbooks; keep this name. |
| `mviewer-dev` | Arbitrary alias to customize when identifying the server in Ansible. |
| `ansible_host` | Target server domain name or IP address, reachable from the control machine. |
| `ansible_user` | SSH account with sudo that performs the installation; replace the example `deploy` account. |
| `ansible_port` | Target SSH port; add this variable if the port differs from `22`. |
| `ansible_ssh_private_key_file` | Private key path on the control machine when a specific key is needed. |

By default, the `mviewer` system account created by the `common` role runs Mviewer Studio and writes to its data and log directories.

To use a specific key, add `ansible_ssh_private_key_file=/path/to/key` to the server line.

<div class="ansible-section-anchor" id="install-site"></div>

## Set the site parameters

Create `site.yml`:

```yaml
nginx_server_name: maps.example.org
mviewerstudio_auth_mode: public
geoserver_workspace: donnessig
geoserver_datastore: postgis
```

| Element | Explanation |
|---|---|
| `nginx_server_name` | Public site domain; replace `maps.example.org` and configure its DNS. |
| `mviewerstudio_auth_mode` | `public` allows access without signing in; `authlib` enables OIDC. |
| `geoserver_workspace` | GeoServer workspace to create and select as default: `donnessig` in this example. |
| `geoserver_datastore` | Name of the PostGIS store inside the workspace: `postgis` in this example. |

- `nginx_server_name` is the public hostname of the site.

- Point its DNS record to the server.

- Variables are split between `group_vars/all/common.yml` and one file per application under `group_vars/all/`. Secrets belong in `secrets.vault.yml`.

- Both playbooks explicitly load the application settings and extension list in `group_vars/all/`. Deployment overrides in `-e @site.yml` take precedence.

- Sources are cloned from their Git repositories on the target.

- Local submodule changes are not transferred.

- For a public HTTPS URL, configure a TLS terminator in front of nginx.

- Set `galaxy_public_scheme: https` to forward the public scheme to applications.

- This variable adjusts public URLs and forwarded headers.

- It does not configure a certificate.

| File | Settings |
|---|---|
| `group_vars/all/common.yml` | System accounts, shared paths, common packages and public URL scheme |
| `group_vars/all/mviewer.yml` | Git source and version, shared apps/store/public directories |
| `group_vars/all/mviewerstudio.yml` | Git source and version, Gunicorn, paths and public OIDC settings |
| `group_vars/all/nginx.yml` | Public server name, HTTP port and logs |
| `group_vars/all/postgres.yml` | Packages, database and user defaults, port, socket and pg_hba template |
| `group_vars/all/geoserver.yml` | Version, archive checksum, Java, paths, ports and PostGIS catalog |
| `group_vars/all/geoserver_extensions.yml` | Extension list, archive URLs and SHA-256 checksums |

<div class="ansible-section-anchor" id="install-database"></div>

## Prepare the GIS database

```bash
cp secrets.example.yml secrets.vault.yml
chmod 600 secrets.vault.yml
```

- `secrets.example.yml` / `secrets.vault.yml`: Supplied example and local PostgreSQL credentials file to customize.

Edit `secrets.vault.yml` with the desired values and your own password:

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

- The password is required.

- Values follow YAML syntax and are passed to the modules without shell interpretation.

- Git ignores `secrets.vault.yml`.

- Ansible reads it on the control machine.

- Load the encrypted file with `-e @secrets.vault.yml --ask-vault-pass`.

- The role creates the SQL user, database and PostGIS.

- The user owns both the database and the `public` schema, can log in and has no superuser privileges.

- SQL accounts are separate from Linux and SSH accounts.

<div class="ansible-section-anchor" id="install-network"></div>

### Prepare network access before installation

Configure these lists in `site.yml`, loaded with `-e @site.yml`:

```yaml
postgres_listen_addresses:
  - 127.0.0.1
  - '::1'
  - 192.0.2.20
postgres_allowed_clients:
  - 192.0.2.10/32
  - 10.0.0.0/24
```

Replace the examples with your addresses. `postgres_listen_addresses` contains server interfaces, not client addresses. Keep loopback if GeoServer uses it. `postgres_allowed_clients` contains client IPs/networks in CIDR format (`/32` for one IPv4 address, `/128` for one IPv6 address).

The default template preserves local access and inserts client rules before the rejection rules for the SIG database and user. It replaces the entire `pg_hba.conf`: include any other rules you need in a custom template. By default, only local interfaces are used (`['127.0.0.1', '::1']`) and no remote clients are added (`[]`). Configure the firewall for the desired access.

For rule syntax and authentication methods, see the [PostgreSQL documentation on `pg_hba.conf` (French)](https://docs.postgresql.fr/12/auth-pg-hba-conf.html).

<div class="ansible-section-anchor" id="install-secrets"></div>

## Complete and encrypt the application Vault

Ansible Vault encrypts files containing deployment passwords and secrets. Use `secrets.example.yml` as a template to create your `secrets.vault.yml` file, which is decrypted when running playbooks using the Vault password.

```bash
# Use the file prepared for the GIS database.
python3 -c 'import secrets; print(secrets.token_hex(32))'
```

| Element | Explanation |
|---|---|
| `secrets.example.yml` / `secrets.vault.yml` | Supplied example and deployment secrets file to customize and encrypt. |
| `mviewerstudio_secret_key` | Random session key of at least 32 characters, required even in public mode. |
| `geoserver_admin_username`, `geoserver_admin_password` | Current GeoServer REST credentials, required from the first installation; the role supplies no defaults. |
| `mviewerstudio_oidc_client_secret` | OIDC client secret in `authlib` mode. |
| `ansible_password`, `ansible_become_password` | Optional SSH/sudo passwords; keep these in Vault when needed. |

- Set `mviewerstudio_secret_key` in `secrets.vault.yml` to the generated value.

- Also set `geoserver_admin_username` and `geoserver_admin_password` to the current server credentials, including on the first installation.

- Encrypt the file:

```bash
ansible-vault encrypt secrets.vault.yml
```

- A fresh GeoServer distribution initially uses `admin` / `geoserver`. For an existing server, use its current credentials. The role does not change this password.

- Edit the encrypted file later with `ansible-vault edit secrets.vault.yml`; keep an existing Vault instead of replacing it with the template.

- The file is not loaded automatically: add `-e @secrets.vault.yml --ask-vault-pass` to commands that need it.


- `secrets.vault.yml`: Control-machine secrets file ignored by Git.
- The session key is required even in `public` mode.

- To enable OIDC, set `mviewerstudio_auth_mode: authlib` in `site.yml` and provide the issuer and client secret using the `mviewerstudio_oidc_*` variables.

- The target must be able to reach the issuer.

- The public callback is `https://maps.example.org/mviewerstudio/auth/callback`.

- Adapt it to your site.

- The playbook does not install Keycloak.

<div class="ansible-section-anchor" id="install-deployment"></div>

## Check and deploy

Check the inventory, syntax and prerequisites:

```bash
ansible-inventory --graph
ansible-playbook playbooks/install.yml --syntax-check
ansible-playbook playbooks/install.yml --tags check -e @site.yml --ask-become-pass
```

| Element | Explanation |
|---|---|
| `ansible-inventory --graph` | Displays groups and servers in the loaded inventory. |
| `playbooks/install.yml` | Main Mviewer Galaxy installation playbook. |
| `--syntax-check` | Checks playbook syntax without deploying applications. |
| `--tags check` | Runs only prerequisite checks. |
| `-e @site.yml` | Loads custom site settings from the control machine. |
| `--ask-become-pass` | Prompts for the SSH account sudo password; omit for passwordless sudo. |

- The prerequisite check requires no application secrets. If SSH/sudo passwords are stored in Vault, load it for this command too.

- It checks sudo privileges, the target system, APT packages and access to Git repositories.

- The first command previews changes with `--check --diff`.

- The second command applies the deployment without `--check`:

```bash
ansible-playbook playbooks/install.yml -e @site.yml -e @secrets.vault.yml --ask-vault-pass --ask-become-pass --check --diff
ansible-playbook playbooks/install.yml -e @site.yml -e @secrets.vault.yml --ask-vault-pass --ask-become-pass
```

| Element | Explanation |
|---|---|
| `playbooks/install.yml` | Deploys all roles on servers in the `galaxy` group. |
| `-e @site.yml` | Loads site-specific variables. |
| `-e @secrets.vault.yml` | Loads encrypted secrets. |
| `--ask-vault-pass` | Prompts for the password used to decrypt the Vault file. |
| `--ask-become-pass` | Prompts for the SSH account sudo password. |
| `--check` | Simulates changes supported by the roles. |
| `--diff` | Displays differences for unhidden files; sensitive tasks remain protected by `no_log`. |
| `-i inventories/production/hosts.ini` | Optional argument selecting another inventory. |

- Omit `--ask-become-pass` if sudo does not require a password.

- To use another inventory, add `-i inventories/production/hosts.ini` to each command.

- Check mode requires Python to be installed on the target.

- It does not validate service startup, SQL provisioning, PostgreSQL access rules or GeoServer catalog configuration.

- Subsequent runs preserve data and reconcile the configuration.

- Changing the password in `secrets.vault.yml` updates PostgreSQL and the GeoServer store.

- Repeating the playbook with unchanged sources and parameters lets you check idempotence.

- Pin Git versions to tags or SHAs for a reproducible deployment.

- Changing a database name creates a new database without migrating the old one.

The default deployment also installs 14 extensions listed with their URLs and SHA-256 checksums in `group_vars/all/geoserver_extensions.yml`. To add extensions later, use the dedicated `playbooks/geoserver_extensions.yml` playbook. See [extension management](/mviewer-galaxy/en/guides/ansible/environnement/#add-or-update-geoserver-extensions). GDAL raster support is excluded; OGR and Image Pyramid install the `gdal-bin` and `python3-gdal` tools.

<div class="ansible-section-anchor" id="install-applications"></div>

## Access the applications

- Examples use `maps.example.org` as the public domain and `server.example.org` as the SSH target.

- Ports shown below are the defaults.

| Service | URL or connection | Access port | Destination on the server |
|---|---|---|---|
| Home page | `http://maps.example.org/` or `/accueil/` | `80` | nginx, static files |
| Catalogue | `http://maps.example.org/catalogue/` | `80` | nginx, static files |
| Mviewer | `http://maps.example.org/mviewer/` | `80` | nginx, static files |
| Studio | `http://maps.example.org/mviewerstudio/` | `80` | Gunicorn on `127.0.0.1:5007` |
| GeoServer | `http://maps.example.org/geoserver/` | `80` | Jetty on `127.0.0.1:8080` |
| PostgreSQL | `postgresql://usersig@server.example.org:5432/donneessig` | `5432`, if the client is allowed | Direct SQL connection, controlled by `pg_hba.conf` and the firewall |
| SSH / Ansible | `ssh://deploy@server.example.org:22` | `22`, depending on inventory settings | Existing SSH service on the target |

- Web applications share the nginx port, `nginx_http_port`.

- The proxy uses `mviewerstudio_port` and `geoserver_port` internally.

- Browsers use the public URLs from the table.

- `postgres_port` selects the PostgreSQL port used by the roles, and `ansible_port` sets the SSH port in the inventory.

- With HTTPS, the usual public port is `443` on the TLS terminator.

- Nginx keeps its configured HTTP port.

- Set `galaxy_public_scheme: https`.

- Adapt URLs, ports, prefixes and credentials to `site.yml`, the inventory and `secrets.vault.yml`.

- GeoServer runs on Java 21 and Jetty, listening locally on `127.0.0.1:8080`.

- The role creates **`donnessig`** as the default workspace and configures the **`postgis`** store to connect to **`donneessig`** using **`usersig`** and the password from `secrets.vault.yml`.

- The connection is checked without automatically publishing layers.

- GeoServer initially uses the `admin` / `geoserver` account.

- Change this password before making the service public.

- Provide its current value through `geoserver_admin_password` in the Vault file for subsequent deployments.

- The role does not change the administrator password itself.

The home page and catalogue are deployed from the local `home/`, `header/` and `catalogue/` directories. See [home-page customization and redeployment](/mviewer-galaxy/en/guides/ansible/environnement/#home-page-header-and-catalogue). For OIDC, also allow the public `/accueil/` URL as a post-logout redirect.

<div class="ansible-section-anchor" id="install-cors"></div>

## CORS: access GeoServer from another origin

- An origin consists of the protocol, hostname and port.

- In the default deployment, Mviewer and GeoServer share the same nginx endpoint: a map served from `https://maps.example.org/mviewer/` can query `/geoserver/` on that same origin without additional CORS configuration.

| Client application | Requested service | Configure CORS for JavaScript requests |
|---|---|---|
| `https://maps.example.org/mviewer/` | `https://maps.example.org/geoserver/` | No, same origin |
| `https://gis.example.org/` | `https://maps.example.org/geoserver/` | Yes, different hostname |
| `http://localhost:4321/` | `http://localhost:8080/geoserver/` | Yes, different port |

- Use GeoServer's public URL in maps rather than its internal address, `127.0.0.1:8080`.

- For a service hosted elsewhere, that remote service must allow the map's origin.

### Configure GeoServer

- The playbook does not configure CORS automatically.

- In the default GeoServer **3.0.2** administration interface, open **Security > CORS**, enable CORS and configure the required options:

| Option | Purpose | Example for an allowed client |
|---|---|---|
| Allowed Origin Patterns | Client application origins allowed to read responses | `https://gis.example.org`, without a path |
| Allowed Methods | HTTP methods allowed for requests | `GET, HEAD, OPTIONS`; add `POST` if needed |
| Allowed Headers | Headers the browser is allowed to send | `Accept, Content-Type`; add `Authorization` if used |
| Supports Credentials | Allows the browser to send cookies or credentials | Disabled for public data accessed without credentials |
| Max Age | How long to cache a preflight result | `600` seconds |

- Save the CORS settings in GeoServer.

- Restart GeoServer, as described in the [GeoServer documentation](https://docs.geoserver.org/stable/en/user/production/container/#enable-cors):

```bash
sudo systemctl restart geoserver
```

- `geoserver`: GeoServer systemd unit name to restart.
- For requests sending cookies or credentials, enable the corresponding support and allow explicit origins: `Access-Control-Allow-Origin: *` is incompatible with credentialed requests.

- See [MDN's explanation](https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/CORS/Errors/CORSNotSupportingCredentials).

- The current nginx template proxies GeoServer responses without adding CORS headers.

- Keep this configuration in GeoServer: adding the same headers in nginx can produce duplicate values that browsers reject.

- See [CORS errors](https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/CORS/Errors).

### Check the response and preflight

Test with the client application's actual origin:

```bash
curl -sS -D - -o /dev/null \
  -H 'Origin: https://gis.example.org' \
  'https://maps.example.org/geoserver/donnessig/wms?service=WMS&request=GetCapabilities'
```

| Element | Explanation |
|---|---|
| `-H 'Origin: …'` | Simulates the client application origin; substitute its actual protocol, host and port. |
| `/geoserver/donnessig/wms` | WMS service in the `donnessig` workspace through the public server URL. |
| `service=WMS` | Selects the WMS map service protocol. |
| `request=GetCapabilities` | Requests service capabilities and metadata. |

- The response must allow `https://gis.example.org` through the `Access-Control-Allow-Origin` header.

- Also check an `OPTIONS` preflight for a client sending a `Content-Type` header:

```bash
curl -i -X OPTIONS \
  -H 'Origin: https://gis.example.org' \
  -H 'Access-Control-Request-Method: GET' \
  -H 'Access-Control-Request-Headers: content-type' \
  'https://maps.example.org/geoserver/donnessig/wms'
```

| Element | Explanation |
|---|---|
| `-X OPTIONS` | Sends a preflight request to check CORS permissions. |
| `Origin` | Actual client application origin to allow. |
| `Access-Control-Request-Method: GET` | Indicates that the actual request will use `GET`. |
| `Access-Control-Request-Headers: content-type` | Indicates that the client wants to send a `Content-Type` header. |

- Check `Access-Control-Allow-Origin`, `Access-Control-Allow-Methods` and `Access-Control-Allow-Headers`.

- Test in the browser.

- `curl` does not enforce browser CORS restrictions.

- HTTP 200 alone is insufficient.

- Public WMS/WFS reads do not require allowing administrative `PUT` or `DELETE` methods.

- Layer and database access permissions remain separate from CORS.

<div class="ansible-section-anchor" id="install-operations"></div>

## Data, logs and services

These useful directories match the default installation.

| Server directory | Contents and purpose |
|---|---|
| `/var/www/mviewergalaxy/home/` | Static home page |
| `/var/www/mviewergalaxy/header/` | Shared header and theme |
| `/var/www/mviewergalaxy/catalogue/` | Map catalogue |
| `/var/www/mviewergalaxy/mviewer/` | Mviewer sources and `apps`, `store`, `public` links |
| `/srv/apps/mviewerstudio/` | Studio sources and `.venv/` virtual environment |
| `/opt/geoserver/3.0.2/` | GeoServer and Jetty distribution; path follows `geoserver_version` |
| `/srv/data/mviewer/apps/` | Mviewer maps |
| `/srv/data/mviewer/store/` | Maps generated by Studio |
| `/srv/data/mviewer/public/` | Maps published from `store` |
| `/srv/data/geoserver/datadir/` | GeoServer catalog, data and security |
| `/var/lib/postgresql/<version>/<cluster>/` | PostgreSQL cluster data; check the actual path with `pg_lsclusters` |
| `/var/lib/mviewer-galaxy/` | Generated `mviewerstudio-config.json` front-end configuration |
| `/var/lib/mviewer-galaxy/sessions/` | Private Studio sessions |
| `/srv/logs/nginx/` | HTTP access and proxy error logs |
| `/srv/logs/mviewerstudio/` | Gunicorn logs and application output |
| `/srv/logs/geoserver/` | GeoServer logs and Jetty console output |
| `/srv/logs/postgresql/` | PostgreSQL cluster logs |
| `/var/cache/geoserver/` | Java and Jetty temporary files |
| `/var/cache/geoserver-downloads/` | GeoServer archive and store configuration fingerprint |
| `/etc/nginx/` | nginx configuration; site in `sites-available/mviewer-galaxy` |
| `/etc/mviewerstudio/` | Studio variables and secrets in `environment`, root access |
| `/etc/postgresql/<version>/<cluster>/` | Cluster configuration, including `postgresql.conf` and `pg_hba.conf` |
| `/etc/systemd/system/` | `mviewerstudio.service` and `geoserver.service` units |
| `/etc/logrotate.d/` | Application log rotation rules |

- Mviewer's `apps`, `store` and `public` directories are symbolic links to their destinations under `/srv/data/mviewer/`.

- The `geoserver` and `postgres` accounts run their respective services.

- Log rotation runs daily and keeps 14 archives by default.

On the target:

```bash
sudo systemctl status nginx mviewerstudio geoserver postgresql logrotate.timer
sudo nginx -t
sudo logrotate --debug /etc/logrotate.conf
sudo tail -n 100 /srv/logs/geoserver/jetty.log
psql -h 127.0.0.1 -U usersig -d donneessig -W --command='SELECT PostGIS_Full_Version();'
```

| Element | Explanation |
|---|---|
| `/srv/logs/geoserver/jetty.log` | GeoServer console log for diagnosing Java and Jetty. |
| `-h 127.0.0.1` | Uses a local TCP connection governed by `host` rules in `pg_hba.conf`. |
| `-U usersig` | Connects using the SQL account configured in `postgres_username`. |
| `-d donneessig` | Selects the database configured in `postgres_database`. |
| `SELECT PostGIS_Full_Version();` | Returns PostGIS and library versions in the selected database. |

- Adapt the credentials if you customized `secrets.vault.yml`.

- Back up data and secrets before updates.

- Existing installation directories are not moved automatically: migrate their contents before changing destinations.

<div class="ansible-section-anchor" id="install-updates"></div>

## Update Mviewer

- Set the desired tag, branch or SHA in `mviewer_version` in `site.yml`.

- Run the Mviewer update playbook:

```bash
ansible-playbook playbooks/upgrade_mviewer.yml -e @site.yml --ask-become-pass
```

| Element | Explanation |
|---|---|
| `playbooks/upgrade_mviewer.yml` | Deploys the requested Mviewer Git reference while preserving data links. |
| `mviewer_version` | Target tag, branch or SHA set in `site.yml`. |
| `-e @site.yml` | Loads the target version and site settings. |
| `--ask-become-pass` | Prompts for the sudo password used during the update. |

This playbook preserves shared links and their data and does not require Studio or PostgreSQL secrets.
