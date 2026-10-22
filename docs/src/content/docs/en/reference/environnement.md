---
title: "Adapt to your environment"
description: "Understand env_file, --env-file and the configuration of each service."
sidebar:
  order: 1
---

You can adapt the installation to your environment using the variables in these files:

| File | Settings |
|---|---|
| `docker/.env.docker` | `PROXY_HTTP_PORT`, `MVIEWERSTUDIO_UID`, `MVIEWERSTUDIO_GID` |
| `docker/envs/.envs-proxy` | `NGINX_HOST`, `MVIEWERSTUDIO_URL_PATH_PREFIX` |
| `docker/envs/.envs-mviewerstudio` | Authlib, session, organization and application paths |
| `docker/envs/.envs-keycloak` | Local server `KC_*` variables |

Keep the same `MVIEWERSTUDIO_URL_PATH_PREFIX` in the proxy and Studio files.

### Understand the two loading mechanisms

The `env_file` setting in a service provides variables to the **container**. For example, nginx receives its settings from:

```yaml
env_file:
  - ./envs/.envs-proxy
```

The `--env-file` option provides variables to **Docker Compose**, which uses them to replace `${…}` expressions before creating containers. For example:

```yaml
ports:
  - "${PROXY_HTTP_PORT:-80}:80"
```

`PROXY_HTTP_PORT` defines the port published on the host. The nginx port inside the container remains `80`: with `PROXY_HTTP_PORT=8080`, Studio is available at `http://localhost:8080/mviewerstudio/`.

Compose defaults are `80` for the port and `1000:1000` for Studio's UID/GID. Variables exported in the terminal take precedence over those loaded with `--env-file`.

### Put the port in the proxy file

To group the port with the nginx settings, move `PROXY_HTTP_PORT` from `docker/.env.docker` to `docker/envs/.envs-proxy`:

```bash
PROXY_HTTP_PORT=80
NGINX_HOST=localhost
MVIEWERSTUDIO_URL_PATH_PREFIX=mviewerstudio
```

Then load this file in the command as well. From the repository root:

```bash
docker compose --env-file docker/.env.docker --env-file docker/envs/.envs-proxy -f docker/docker-compose.yml --profile keycloak up -d --build
```

The first file provides the UID/GID; the second provides the port. When a variable appears in both, the last file specified takes precedence. The `proxy` service continues to load `.envs-proxy` through its `env_file` for its internal variables.

If the default UID/GID `1000:1000` suits your setup, the proxy file is enough for the command:

```bash
docker compose --env-file docker/envs/.envs-proxy -f docker/docker-compose.yml --profile keycloak up -d --build
```

From `docker/`, the same command becomes:

```bash
docker compose --env-file envs/.envs-proxy --profile keycloak up -d --build
```

To use remote Keycloak, run the chosen command without `--profile keycloak`, after configuring Studio for that server.
Keep the same `--env-file` options for `config`, `up`, `logs` and `down`. Other examples in this guide use the file layout in the table above.

## Studio connection settings

These three variables must be set and non-empty in both modes:

| Variable | Purpose |
|---|---|
| `MVIEWERSTUDIO_AUTHLIB_ISSUER` | Keycloak realm URL |
| `MVIEWERSTUDIO_AUTHLIB_CLIENT_SECRET` | OIDC client secret |
| `SECRET_KEY` | Studio session key |

Enter these values in `docker/envs/.envs-mviewerstudio`. Check the Compose syntax and file loading before starting services:

```bash
docker compose --env-file docker/.env.docker -f docker/docker-compose.yml config --quiet
```

This command checks the Compose configuration. Application variables are passed to the containers; then check the required values and the sign-in flow to verify exchanges with Keycloak.

## Additional variables

| Variable | Reference value | Purpose |
|---|---|---|
| `PROXY_HTTP_PORT` | `80` | HTTP port published on the host |
| `NGINX_HOST` | `localhost` | nginx server name |
| `MVIEWERSTUDIO_UID` / `MVIEWERSTUDIO_GID` | `1000` / `1000` | Studio process identity |
| `DEFAULT_ORG` | `public` | Default organization |
| `MVIEWERSTUDIO_AUTHLIB_CLIENT_ID` | `mviewerstudio` | OIDC client |
| `MVIEWERSTUDIO_AUTHLIB_SCOPE` | `openid profile email organization` | Requested scopes |
| `MVIEWERSTUDIO_AUTHLIB_ALLOWED_GROUPS` | `MVIEWER_ACCESS` | Studio access control |
| `KC_HOSTNAME` | `http://localhost/keycloak` | Public URL of local Keycloak |
