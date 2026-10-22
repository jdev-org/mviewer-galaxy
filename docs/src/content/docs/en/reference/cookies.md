---
title: "Cookies and privacy"
description: "Reference information about sessions and cookies in the stack."
sidebar:
  order: 3
---

This stack may set technical session cookies related to OIDC authentication, through Studio's Authlib session and Keycloak session cookies.

In practice, for this architecture:

- Cookies strictly necessary for authentication and session continuity are generally exempt from consent requirements, provided they are strictly necessary for the service explicitly requested by the user.
- Information requirements still apply: these cookies must be mentioned in your privacy policy or cookie policy.
- If you add analytics cookies, non-essential personalization, advertising or third-party trackers, you need to reassess the need for a cookie banner and consent collection.
- Some analytics cookies may be exempt from consent, but only under the conditions set by the French data protection authority, the CNIL.

Practical implications:

- With only the stack's OIDC authentication component, a cookie banner is not automatically needed solely for technical session cookies.
- You must still document these cookies in your GDPR privacy information.
- If you add Matomo, Google Analytics, third-party scripts, social widgets, embedded videos, tracking pixels or marketing tools, check whether consent is required.

Official references:

- CNIL, “Cookies et traceurs : que dit la loi ?” (French): https://www.cnil.fr/fr/cookies-et-autres-traceurs/que-dit-la-loi
- CNIL, “Cookies : solutions pour les outils de mesure d'audience” (French): https://www.cnil.fr/fr/cookies-solutions-pour-les-outils-de-mesure-daudience
- CNIL, “Site web, cookies et autres traceurs” portal (French): https://www.cnil.fr/fr/cookies-et-autres-traceurs
- ePrivacy Directive 2002/58/EC, Article 5(3): https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32002L0058

Caution:

- This section provides technical and documentation context, rather than legal advice.
- If the site serves external users or a local authority, have your DPO or legal adviser validate the cookie policy and the chosen legal basis.
