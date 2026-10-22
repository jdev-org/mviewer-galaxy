---
title: "Local Keycloak"
description: "Configure the local profile and test accounts."
sidebar:
  order: 2
---

In `docker/envs/.envs-mviewerstudio`, configure the test realm values:

```bash
MVIEWERSTUDIO_AUTHLIB_ISSUER=http://localhost/keycloak/realms/mviewer
MVIEWERSTUDIO_AUTHLIB_METADATA_URL=http://keycloak:8080/keycloak/realms/mviewer/.well-known/openid-configuration
MVIEWERSTUDIO_AUTHLIB_CLIENT_ID=mviewerstudio
MVIEWERSTUDIO_AUTHLIB_CLIENT_SECRET=mviewerstudio-local-secret
SECRET_KEY=replace-with-a-long-random-secret
```

In `docker/envs/.envs-keycloak`, keep the local server settings, including:

```bash
KC_HOSTNAME=http://localhost/keycloak
KC_BOOTSTRAP_ADMIN_USERNAME=admin
KC_BOOTSTRAP_ADMIN_PASSWORD=admin
```

Start with the profile:

```bash
docker compose --env-file docker/.env.docker -f docker/docker-compose.yml --profile keycloak up -d --build
```

The profile selects the services; Authlib values remain those defined in the environment file. The imported realm is `mviewer`.
With this profile, Studio and the proxy wait for the realm's OIDC discovery endpoint to return HTTP 200 before starting. This check accounts for the time needed to initialize local Keycloak and import the realm.

| Purpose | Username | Local password |
|---|---|---|
| Studio | `john.doe` | `john` |
| Test | `test` | `test` |
| Administration | `admin` | `admin` |

In `docker/envs/.envs-keycloak`, configure the administrator account using `KC_BOOTSTRAP_ADMIN_USERNAME` and `KC_BOOTSTRAP_ADMIN_PASSWORD`.
The server runs in development mode; its data is stored inside the container. Recreating it imports the realm again and resets any changes made in the console.
