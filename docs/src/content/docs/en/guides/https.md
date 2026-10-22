---
title: "Reverse proxy and HTTPS"
description: "Expose the applications using their public domain name."
sidebar:
  order: 5
---

An existing nginx server can terminate TLS and forward requests to the `proxy` service's HTTP port. Forward `Host`, `X-Forwarded-For` and `X-Forwarded-Proto: https` so that Studio builds its public callback URL. Match the allowed callback in Keycloak.

Set the published port using `PROXY_HTTP_PORT`; Compose publishes it on the host interfaces. The nginx template resolves the local Keycloak hostname when receiving requests, allowing startup in either mode.

## TLS certificates

### If you do not have certificates yet

A straightforward production setup is to use Let's Encrypt with `certbot` on the VPS that already hosts nginx.

Prerequisites:

- The DNS name `maps.example.org` must point to the VPS IP address.
- Ports `80` and `443` must be open.
- The deployed nginx must be able to answer the Let's Encrypt challenge, or be stopped temporarily when using `certbot --standalone`.

Typical installation on Debian/Ubuntu:

```bash
sudo apt update
sudo apt install certbot
```

Issue a certificate in standalone mode:

```bash
sudo certbot certonly --standalone -d maps.example.org
```

Alternatively, if the deployed nginx is already configured for the domain:

```bash
sudo certbot --nginx -d maps.example.org
```

The resulting files are usually:

- `/etc/letsencrypt/live/maps.example.org/fullchain.pem`
- `/etc/letsencrypt/live/maps.example.org/privkey.pem`

These certificates are used by the nginx server already deployed on the host.

### Renewal

Let's Encrypt certificates have a limited lifetime. They are generally renewed with:

```bash
sudo certbot renew
```

After renewal, reload the deployed nginx server so it reads the updated certificates.
