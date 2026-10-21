---
title: "Reverse proxy et HTTPS"
description: "Exposer les applications avec leur nom de domaine public."
sidebar:
  order: 5
---

Un nginx existant peut terminer TLS et relayer vers le port HTTP du service
`proxy`. Transmettre `Host`, `X-Forwarded-For` et `X-Forwarded-Proto: https` pour
que Studio construise son URL de retour publique. Aligner le callback autorisé
côté Keycloak.

Le port publié se règle avec `PROXY_HTTP_PORT` ; le Compose le publie sur les
interfaces de l'hôte. Le template nginx résout le nom du Keycloak local à la
réception des requêtes, ce qui permet de démarrer dans les deux modes.

## Certificats TLS

### Si vous n'avez pas encore de certificats

Le plus simple en production est d'utiliser Let's Encrypt avec `certbot` sur le VPS qui héberge déjà nginx.

Pré-requis :

- le nom DNS `maps.example.org` doit pointer vers l'adresse IP du VPS
- les ports `80` et `443` doivent être ouverts
- le nginx déjà déployé doit pouvoir répondre au challenge Let's Encrypt, ou être arrêté temporairement si vous utilisez `certbot --standalone`

Installation typique sur Debian/Ubuntu :

```bash
sudo apt update
sudo apt install certbot
```

Émission d'un certificat standalone :

```bash
sudo certbot certonly --standalone -d maps.example.org
```

Alternative si le nginx déjà déployé est déjà configuré sur le domaine :

```bash
sudo certbot --nginx -d maps.example.org
```

Fichiers obtenus en général :

- `/etc/letsencrypt/live/maps.example.org/fullchain.pem`
- `/etc/letsencrypt/live/maps.example.org/privkey.pem`

Ces certificats restent utilisés par le nginx déjà déployé sur le serveur, pas par la stack Docker applicative.

### Renouvellement

Let's Encrypt délivre des certificats à durée limitée. Le renouvellement se fait généralement avec :

```bash
sudo certbot renew
```

Après renouvellement, rechargez le nginx déjà déployé pour qu'il relise les certificats.
