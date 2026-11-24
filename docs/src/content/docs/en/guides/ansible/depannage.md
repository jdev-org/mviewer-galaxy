---
title: "Ansible troubleshooting"
description: "Diagnose SSH, sudo, systemd services, PostgreSQL and GeoServer in an Ansible deployment."
---

This page covers the native installation deployed with the Ansible roles.

- Run Ansible commands from `ansible/` on the control machine.

- Run service, log and PostgreSQL checks on the target server.

- For a Compose deployment, see [Docker troubleshooting](/mviewer-galaxy/en/guides/depannage/).

## Check the target and prerequisites

From `ansible/` on the control machine:

```bash
ansible-inventory --graph
ansible-playbook playbooks/install.yml --tags check -e @site.yml --ask-become-pass
```

| Element | Explanation |
|---|---|
| `ansible-inventory --graph` | Displays groups and servers in the loaded inventory. |
| `--tags check` | Runs only prerequisite checks. |
| `-e @site.yml` | Loads custom site settings from the control machine. |
| `--ask-become-pass` | Prompts for the SSH account sudo password; omit for passwordless sudo. |

- If SSH fails, check `ansible_host`, `ansible_port`, `ansible_user` and the private key in the inventory.

- Test the same connection with `ssh`.

- If sudo fails, check the SSH account's privileges and use `--ask-become-pass`.

- The `mviewer` application account is separate from the deployment's SSH account.

A Docker target used to test this playbook must actually run systemd: the `check` role rejects targets without `/run/systemd/system`.

## Python or Java 21 missing from repositories

- The check requires Python 3.11+ and an `openjdk-21-jre-headless` package available through APT.

- The role can install Python if available, but does not add a Java repository.

- Check the target's repositories and outbound network access.

- Full `--check` mode requires Python to be installed already.

## Missing .env or secrets

- The PostgreSQL validation task is hidden with `no_log`.

- On the control machine, check that `.env` exists and contains a non-empty `POSTGRES_PASSWORD`.

- If you use another file, check `postgres_env_file` and its read permissions.

- Studio requires a `mviewerstudio_secret_key` at least 32 characters long, even in `public` mode.

- Load the encrypted file with `-e @secrets.vault.yml` and `--ask-vault-pass`.

- In `authlib` mode, also configure the issuer and OIDC secrets.

## Check services and logs

On the target:

```bash
sudo systemctl status nginx mviewerstudio geoserver postgresql logrotate.timer
sudo journalctl -u mviewerstudio -u geoserver -n 100 --no-pager
sudo tail -n 100 /srv/logs/nginx/error.log
sudo tail -n 100 /srv/logs/mviewerstudio/error.log
sudo tail -n 100 /srv/logs/geoserver/jetty.log
sudo nginx -t
```

| Element | Explanation |
|---|---|
| `/srv/logs/nginx/error.log` | nginx and HTTP proxy errors. |
| `/srv/logs/mviewerstudio/error.log` | Gunicorn and Studio errors. |
| `/srv/logs/geoserver/jetty.log` | Java and Jetty console output, useful for GeoServer startup errors. |

- `journalctl` includes unit startup events.

- Application logs are stored under `/srv/logs/<application>/`.

## nginx returns 502

Test the local services on the target:

```bash
curl -I http://127.0.0.1:5007/mviewerstudio/
curl -I http://127.0.0.1:8080/geoserver/web/
```

| Element | Explanation |
|---|---|
| `127.0.0.1` | Targets the service from the server itself without using the public domain. |
| `5007/mviewerstudio/` | Studio internal port and prefix; adapt if customized. |
| `8080/geoserver/web/` | GeoServer internal port and web interface. |

- Adapt ports and prefixes if customized.

- Check that the services are active and nginx uses the same ports.

- For Studio, check shared data and log permissions:

```bash
sudo -u mviewer test -w /srv/data/mviewer/store
sudo -u mviewer test -w /srv/data/mviewer/public
sudo -u mviewer test -w /srv/logs/mviewerstudio
```

| Element | Explanation |
|---|---|
| `mviewer` | Application account used for these checks; adapt if `galaxy_user` is customized. |
| `/srv/data/mviewer/store` | Directory where Studio saves generated maps. |
| `/srv/data/mviewer/public` | Directory where Studio publishes maps. |
| `/srv/logs/mviewerstudio` | Log directory Studio must be able to write to. |

These commands should succeed with the account configured in `galaxy_user`.

## PostgreSQL connection refused

```bash
sudo pg_lsclusters
psql -h 127.0.0.1 -U usersig -d donneessig -W --command='SELECT current_user;'
sudo ls /srv/logs/postgresql/
sudo -u postgres psql --dbname=postgres --command='SHOW listen_addresses;'
sudo -u postgres psql --dbname=postgres --command='SELECT line_number, error FROM pg_hba_file_rules WHERE error IS NOT NULL;'
```

| Element | Explanation |
|---|---|
| `sudo pg_lsclusters` | Lists PostgreSQL cluster versions, names, ports, states and paths. |
| `-h 127.0.0.1` | Uses a local TCP connection governed by `host` rules in `pg_hba.conf`. |
| `-U usersig` | Connects using the SQL account configured in `POSTGRES_USER`. |
| `-d donneessig` | Selects the database configured in `POSTGRES_DB`. |
| `SELECT current_user;` | Displays the SQL account actually connected. |
| `/srv/logs/postgresql/` | Directory containing PostgreSQL cluster logs. |
| `postgres` | PostgreSQL administrator Linux account used for local checks. |
| `--dbname=postgres` | Selects the local administration database for checks. |
| `SHOW listen_addresses;` | Displays configured listening interfaces; the role expects `*`. |
| `pg_hba_file_rules` | Access rule view; this query displays only lines with invalid syntax. |

- Adapt the credentials and add the port if necessary.

- Check the password in `.env`, the `pg_hba.conf.j2` template and the firewall.

- Allowed clients must appear before the `reject` rules: the first matching rule determines access.

- After editing the template, rerun the role to deploy it.

- Manual changes to the target file will be replaced.

- The configured user owns the database and `public` schema.

- This does not reassign existing tables owned by another user.

## GeoServer workspace or store not configured

- The role waits for the REST API and checks the PostGIS connection.

- HTTP 401 or 403 errors can indicate incorrect administrator credentials: `geoserver_admin_username` and `geoserver_admin_password` must match the current GeoServer account.

- For a PostGIS connection error, check that the `postgres` role has run, the database contains PostGIS, `.env` credentials are correct and `pg_hba.conf` allows the address used by GeoServer.

- Also check `geoserver_postgres_host` and `geoserver_postgres_port`.

- After changing the SQL password, rerun the full deployment to update both services.

- Read `/srv/logs/geoserver/geoserver.log` and `jetty.log` for details.

- Tasks carrying passwords are hidden.

## Incorrect HTTPS URL or OIDC redirect

- Compare the public domain, `galaxy_public_scheme`, port and Studio prefix with the URLs allowed by the OIDC provider.

- Behind a TLS terminator, `galaxy_public_scheme` must be `https`.

- Check issuer access from the target and the claims/groups expected by Studio.

## GeoServer request blocked by CORS

- Compare the map's origin and the service URL, including protocol, hostname and port.

- Check `OPTIONS` requests and response headers in the browser's network tools.

- A service HTTP error or redirect can also be hidden behind a CORS message.

Follow the [installation CORS section](/mviewer-galaxy/en/guides/installation-ansible/#install-cors).

## Log rotation

```bash
sudo systemctl status logrotate.timer
sudo logrotate --debug /etc/logrotate.conf
```

| Element | Explanation |
|---|---|
| `logrotate.timer` | Systemd unit scheduling daily log rotation. |
| `/etc/logrotate.conf` | Main configuration, including rules from `/etc/logrotate.d/`. |

- `--debug` checks rules without rotating files.

- Check log directory ownership if logrotate reports permission problems.

See also [Adapt to your environment](/mviewer-galaxy/en/guides/ansible/environnement/).
