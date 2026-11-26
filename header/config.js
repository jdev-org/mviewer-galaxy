// Configuration de l’en-tête partagé. Aucun build nécessaire : modifier puis recharger.
window.HEADER_CONFIG = {
  brand: {
    name: "mviewer",
    subtitle: "GALAXY",
    // Logo partagé par l'accueil et le catalogue. Modifiable ici.
    logo: "/catalogue/img/logo_mviewer.svg",
  },
  // Ajouter, supprimer ou réordonner les entrées de ce tableau.
  // newTab: true ouvre un lien dans un nouvel onglet.
  headerLinks: [
    { label: "Explorer", href: "/catalogue/" },
    { label: "Mviewer", href: "/mviewer/" },
    { label: "Studio", href: "/mviewerstudio/" },
    // { label: "Documentation", href: "https://exemple.fr/docs", newTab: true },
  ],
};
