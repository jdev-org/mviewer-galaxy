---
title: "Getting started"
description: "Prepare the configuration and start the Docker services."
sidebar:
  order: 1
---

## Prepare the repository

Use Docker with the Compose plugin. The `mviewer/` and `mviewerstudio/` directories provide the applications; Studio is built from `mviewerstudio/docker/Dockerfile`.

Configure the following files:

| File | Purpose |
|---|---|
| `docker/.env.docker` | Published port and UID/GID |
| `docker/envs/.envs-proxy` | nginx server name and Studio prefix |
| `docker/envs/.envs-mviewerstudio` | Authlib, session and application paths |
| `docker/envs/.envs-keycloak` | Local Keycloak server |

## Choose your Keycloak server

Choose the [local server](/mviewer-galaxy/en/guides/authentification/keycloak/local/) or the [remote server](/mviewer-galaxy/en/guides/authentification/keycloak/distant/) before starting.

## Check the configuration

```bash
docker compose --env-file docker/.env.docker -f docker/docker-compose.yml config --quiet
```

This command checks the Compose configuration and the loaded files. Signing in through the browser then lets you check credentials and OIDC exchanges.

## Start with local Keycloak

```bash
docker compose --env-file docker/.env.docker -f docker/docker-compose.yml --profile keycloak up -d --build
```

Studio and the proxy wait for the local realm's OIDC discovery endpoint to return HTTP 200.

## Start with remote Keycloak

```bash
docker compose --env-file docker/.env.docker -f docker/docker-compose.yml up -d --build
```

## Open the applications

- [Studio](http://localhost/mviewerstudio/)
- [Mviewer](http://localhost/mviewer/)
- [Local Keycloak administration](http://localhost/keycloak/admin/)

These URLs use HTTP port `80`. For a different port, also update the public URLs and the allowed redirects in Keycloak.
