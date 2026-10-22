// Configuration du portail. Aucun build nécessaire : modifier puis recharger.
window.PORTAL_CONFIG = {
  brand: {
    name: "mviewer",
    subtitle: "GALAXY",
    // Logo partagé par l'accueil et le catalogue. Modifiable ici.
    logo: "/catalogue/img/logo_mviewer.svg",
  },
  heroImage: "/assets/coast.webp",
  // Les cartes à la une viennent de catalogue/data.json (favorite: true).
  // Si le catalogue est vide, l'accueil présente apps/default.xml.
  // Ajouter, supprimer ou réordonner les entrées de ce tableau.
  // newTab: true ouvre un lien dans un nouvel onglet.
  headerLinks: [
    { label: "Explorer", href: "/catalogue/" },
    { label: "Mviewer", href: "/mviewer/" },
    { label: "Studio", href: "/portal/studio" },
    // { label: "Documentation", href: "https://exemple.fr/docs", newTab: true },
  ],
};
