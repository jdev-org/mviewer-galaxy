(() => {
"use strict";

const config = window.PORTAL_CONFIG || {};
const brand = config.brand || {};
if (brand.name) document.getElementById("brand-name").textContent = brand.name;
if (typeof brand.subtitle === "string") {
  document.getElementById("brand-subtitle").textContent = brand.subtitle;
}
if (brand.name) {
  document.querySelector(".brand").setAttribute("aria-label", `${brand.name} ${brand.subtitle || ""}, accueil`);
  const footerBrand = document.querySelector(".footer-brand");
  if (footerBrand) footerBrand.textContent = `${brand.name} ${brand.subtitle || ""}`.trim();
}
const logoPath = brand.logo;
if (logoPath) {
  const logo = document.createElement("img");
  logo.src = logoPath;
  logo.alt = "";
  logo.className = "brand-mark";
  document.querySelector(".brand-mark").replaceWith(logo);
}

if (Array.isArray(config.headerLinks)) {
  const links = config.headerLinks.map(({ label, href, newTab }) => {
    const link = document.createElement("a");
    link.textContent = label;
    link.href = href;
    if (newTab) {
      link.target = "_blank";
      link.rel = "noopener noreferrer";
    }
    return link;
  });
  document.querySelector(".header-nav").replaceChildren(...links);
}

const authLink = document.getElementById("auth-link");
const userName = document.getElementById("user-name");
const sessionStatus = document.getElementById("session-status");

async function refreshSession() {
  try {
    const response = await fetch("/portal/session", {
      credentials: "same-origin",
      cache: "no-store",
      headers: { Accept: "application/json" },
      signal: AbortSignal.timeout(8000),
    });
    if (response.status === 401) {
      authLink.textContent = "Se connecter ↗";
      authLink.href = "/portal/login";
      userName.hidden = true;
      sessionStatus.textContent = "";
      return;
    }
    // A forbidden response means the session exists but lacks a Studio group.
    if (!response.ok && response.status !== 403) throw new Error("Session unavailable");
    const user = await response.json();
    const connected = response.status === 403 ||
      (Boolean(user.user_name) && user.user_name !== "anonymous");
    authLink.textContent = connected ? "Se déconnecter ↗" : "Se connecter ↗";
    authLink.href = connected ? "/portal/logout" : "/portal/login";
    userName.textContent = user.first_name || user.user_name || "";
    userName.hidden = !connected || !userName.textContent;
    sessionStatus.textContent = response.status === 403
      ? "Votre compte est connecté, mais ne dispose pas des droits d’accès à Studio."
      : "";
  } catch {
    sessionStatus.textContent = "L’état de connexion est momentanément indisponible. Vous pouvez réessayer en rechargeant la page.";
  }
}

// Also refresh on back/forward cache restores and when returning from another tab.
window.addEventListener("pageshow", refreshSession);
document.addEventListener("visibilitychange", () => {
  if (document.visibilityState === "visible") refreshSession();
});

})();
