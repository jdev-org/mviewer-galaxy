
```mermaid
sequenceDiagram
    participant B as Browser
    participant A as mviewerstudio (Flask)
    participant O as oauth2-proxy
    participant K as Keycloak

    B->>A: GET /logout
    A-->>B: 302 /oauth2/sign_out?rd=<keycloak logout url> + expire cookies

    B->>O: GET /oauth2/sign_out?rd=...
    O-->>B: clear proxy session + 302 Keycloak logout

    B->>K: GET /protocol/openid-connect/logout
    K-->>B: 302 /oauth2/start?rd=/mviewerstudio/

    B->>O: GET /oauth2/start?rd=/mviewerstudio/
    O-->>B: 302 login page Keycloak
