---
title: "Cookies et confidentialité"
description: "Informations de référence sur les sessions et cookies de la stack."
sidebar:
  order: 3
---

Cette stack peut déposer au moins des cookies techniques de session liés à l'authentification OIDC, via la session Authlib de Studio et les cookies de session Keycloak.

En pratique, pour cette architecture :

- les cookies strictement nécessaires à l'authentification et au maintien de session sont en principe exemptés de recueil du consentement, dès lors qu'ils sont strictement nécessaires au service explicitement demandé par l'utilisateur ;
- ils restent toutefois soumis à une obligation d'information : ils doivent être mentionnés dans votre politique de confidentialité ou votre politique cookies ;
- si vous ajoutez des cookies de mesure d'audience, de personnalisation non essentielle, de publicité, ou des traceurs tiers, il faut réévaluer le besoin d'un bandeau cookies et du recueil du consentement ;
- certains cookies de mesure d'audience peuvent être exemptés de consentement, mais seulement sous les conditions posées par la CNIL.

Conséquence pratique :

- avec la seule brique d'authentification OIDC de cette stack, il est raisonnable de considérer que vous n'avez pas automatiquement besoin d'un bandeau cookies pour les seuls cookies de session techniques ;
- en revanche, vous devez documenter ces cookies dans votre information RGPD ;
- si vous ajoutez Matomo, Google Analytics, scripts tiers, widgets sociaux, vidéos embarquées, pixels de suivi ou outils marketing, il faudra vérifier que le consentement est requis ou non.

Références officielles :

- CNIL, « Cookies et traceurs : que dit la loi ? » : https://www.cnil.fr/fr/cookies-et-autres-traceurs/que-dit-la-loi
- CNIL, « Cookies : solutions pour les outils de mesure d'audience » : https://www.cnil.fr/fr/cookies-solutions-pour-les-outils-de-mesure-daudience
- CNIL, portail « Site web, cookies et autres traceurs » : https://www.cnil.fr/fr/cookies-et-autres-traceurs
- Directive ePrivacy 2002/58/CE, article 5(3) : https://eur-lex.europa.eu/legal-content/FR/TXT/?uri=CELEX:32002L0058

Point de prudence :

- cette section donne un cadrage technique et documentaire, pas un avis juridique ;
- si le site est destiné à des usagers externes ou à une collectivité, faites valider la politique cookies et la base légale retenue par votre DPO ou conseil juridique.
