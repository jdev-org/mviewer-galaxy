---
title: "Remote Keycloak"
description: "Connect Studio to an external realm and configure its OIDC redirects."
sidebar:
  order: 3
---

## Prepare the client

In the remote realm, configure an OpenID Connect client for Studio with client authentication and the authorization code flow (Standard Flow). Copy its ID and secret into the configuration below.

Provide the scopes and claims requested by Studio. The local realm supplied in `resources/keycloak/mviewer-realm.json` can serve as a reference for the mappers.

## Configure Studio

In `docker/envs/.envs-mviewerstudio`, enter the remote server values:

```bash
MVIEWERSTUDIO_AUTHLIB_ISSUER=https://sso.example.org/realms/mviewer
MVIEWERSTUDIO_AUTHLIB_METADATA_URL=https://sso.example.org/realms/mviewer/.well-known/openid-configuration
MVIEWERSTUDIO_AUTHLIB_CLIENT_ID=mviewerstudio
MVIEWERSTUDIO_AUTHLIB_CLIENT_SECRET=client-secret
SECRET_KEY=replace-with-a-long-random-secret
```

Update `MVIEWERSTUDIO_AUTHLIB_METADATA_URL` for the remote server; the local value in `.envs-mviewerstudio` points to the `keycloak:8080` service.
The remote server endpoints must be reachable from the browser for sign-in and from Studio for OIDC exchanges.

The Keycloak client must allow the callback `https://your-domain/mviewerstudio/auth/callback`, or `http://localhost/mviewerstudio/auth/callback` for a local test.
Also allow the post-logout redirect to `https://your-domain/mviewer/` (or `http://localhost/mviewer/` locally).
Claims must match the access control configured by `MVIEWERSTUDIO_AUTHLIB_ALLOWED_GROUPS` (`MVIEWER_ACCESS` by default).

Start:

```bash
docker compose --env-file docker/.env.docker -f docker/docker-compose.yml up -d --build
```

## Switch from the local server to the remote server

```bash
docker compose --env-file docker/.env.docker -f docker/docker-compose.yml --profile keycloak stop keycloak
```

Update Studio's values, then run the remote mode startup command again. The profile controls services; it does not change Authlib URLs or stop a container that is already running.

## Publish over HTTPS

The browser must be able to reach the sign-in page. Studio must be able to reach the discovery, token and public key endpoints advertised by the realm. HTTPS certificates must be trusted by the container environment.

See the [Reverse proxy and HTTPS guide](/mviewer-galaxy/en/guides/https/).
