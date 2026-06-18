```mermaid
sequenceDiagram
    participant B as Browser
    participant N as Nginx
    participant O as oauth2-proxy
    participant K as Keycloak
    participant A as mviewerstudio (Flask)

    B->>N: GET /mviewerstudio/
    N->>O: GET /oauth2/auth
    O-->>N: 401 Unauthorized (no session)
    N-->>B: 302 /oauth2/start?rd=http://host/mviewerstudio/

    B->>O: GET /oauth2/start?rd=...
    O-->>B: 302 Keycloak /protocol/openid-connect/auth

    B->>K: GET /keycloak/.../auth
    K-->>B: login form
    B->>K: submit credentials
    K-->>B: 302 /oauth2/callback?code=...

    B->>O: GET /oauth2/callback?code=...
    O->>K: POST /protocol/openid-connect/token
    K-->>O: ID token + access token
    O-->>B: Set-Cookie _oauth2_proxy=... + 302 rd=http://host/mviewerstudio/

    B->>N: GET /mviewerstudio/ + cookie
    N->>O: GET /oauth2/auth
    O-->>N: 202/200 + X-Auth-Request-* headers

    N->>A: proxied request + X-Auth-Request-* / X-Forwarded-* headers
    A->>A: build current_user from headers or token
    A-->>B: 200 OK