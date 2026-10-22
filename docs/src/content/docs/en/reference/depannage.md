---
title: "Troubleshooting"
description: "Identify startup, sign-in and sign-out errors."
sidebar:
  order: 2
---

## Check the logs

```bash
docker compose --env-file docker/.env.docker -f docker/docker-compose.yml --profile keycloak ps -a
docker compose --env-file docker/.env.docker -f docker/docker-compose.yml --profile keycloak logs --tail 100 proxy mviewerstudio keycloak
```

## Connection to Keycloak refused

Check service availability and the value of `MVIEWERSTUDIO_AUTHLIB_METADATA_URL`. For the local server, it points to `http://keycloak:8080/keycloak/realms/mviewer/.well-known/openid-configuration`.

The readiness check waits for the realm import before starting Studio with the `keycloak` profile.

## Invalid redirect uri

Compare the URL rejected in the Keycloak logs with the URLs allowed for the Studio client. Check the protocol, hostname, port and path:

- Sign-in: `http://localhost/mviewerstudio/auth/callback`.
- Post-logout redirect: `http://localhost/mviewer/`.

Adapt these addresses to the public domain for a remote deployment. Nginx adjusts the post-logout redirect to `/mviewer/` while preserving the public protocol.

## Studio returns a 502 error

Check that Studio has started. A permission error on `apps/store/register.json` prevents startup. Match the process UID/GID to the owner of the shared directories, then recreate the service.

See [Volumes and operations](/mviewer-galaxy/en/guides/exploitation/).

## A 500 error after successful sign-in

Read Studio's Python traceback. If it says `normalize() argument 2 must be str, not list`, the received `organization` claim does not match the format expected by the application. Check the realm mappers and the format of the claims sent to Studio.

## Access denied after sign-in

Check the user's permissions and how they match `MVIEWERSTUDIO_AUTHLIB_ALLOWED_GROUPS`.

## The configured port does not change

`env_file` supplies the container; `--env-file` supplies Compose expressions. To use `PROXY_HTTP_PORT` from `.envs-proxy`, also load that file in the command.

See [Adapt to your environment](/mviewer-galaxy/en/reference/environnement/).
