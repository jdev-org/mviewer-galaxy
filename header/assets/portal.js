"use strict";

const config = window.PORTAL_CONFIG || {};
if (config.heroImage) document.querySelector(".hero-image").src = config.heroImage;

const defaultMap = {
  title: "Carte du territoire",
  description: "Explorez les données du territoire dans Mviewer.",
  image: config.heroImage || "/assets/coast.webp",
  href: "/mviewer/?config=/apps/default.xml",
};

function catalogueURL(value, base) {
  if (typeof value !== "string" || !value.trim()) return null;
  try {
    const url = new URL(value, base);
    return ["http:", "https:"].includes(url.protocol) ? url.href : null;
  } catch {
    return null;
  }
}

async function loadFeaturedMaps() {
  try {
    const response = await fetch("/catalogue/data.json", {
      cache: "no-store",
      signal: AbortSignal.timeout(8000),
    });
    if (!response.ok) throw new Error("Catalogue unavailable");
    const catalogue = await response.json();
    if (!Array.isArray(catalogue.data)) throw new Error("Invalid catalogue");
    if (!catalogue.data.length) {
      renderFeaturedMaps([defaultMap]);
      return;
    }
    // Resolve relative links from the catalogue directory, as on its own page.
    const base = response.url || new URL("/catalogue/data.json", window.location.href).href;
    const maps = catalogue.data
      .filter(map => map && map.favorite === true)
      .map(map => ({
        title: map.title,
        description: map.description,
        href: catalogueURL(map.url_demo, base),
        image: catalogueURL(map.image, base) || defaultMap.image,
        newTab: map.newTab === true,
      }))
      .filter(map => map.href);
    renderFeaturedMaps(maps);
  } catch {
    // Keep the portal usable if the catalogue cannot be loaded.
    renderFeaturedMaps([defaultMap]);
  }
}

function renderFeaturedMaps(featuredMaps) {
  if (!featuredMaps.length) return;
  const track = document.getElementById("featured-track");
  const previous = document.getElementById("featured-prev");
  const next = document.getElementById("featured-next");
  const position = document.getElementById("featured-position");
  let activeIndex = 0;

  featuredMaps.forEach((map, index) => {
    const slide = document.createElement("article");
    slide.className = "featured-slide";
    slide.setAttribute("role", "group");
    slide.setAttribute("aria-roledescription", "diapositive");
    slide.setAttribute("aria-label", `${index + 1} sur ${featuredMaps.length}`);
    const link = document.createElement("a");
    link.className = "featured-card";
    link.href = map.href;
    if (map.newTab) {
      link.target = "_blank";
      link.rel = "noopener noreferrer";
    }
    if (map.image) {
      const image = document.createElement("img");
      image.src = map.image;
      image.alt = "";
      image.loading = "lazy";
      image.className = "featured-image";
      link.append(image);
    }
    const copy = document.createElement("div");
    copy.className = "featured-copy";
    const title = document.createElement("h3");
    title.textContent = map.title;
    const description = document.createElement("p");
    description.textContent = map.description || "";
    const action = document.createElement("span");
    action.className = "featured-action";
    action.textContent = map.newTab ? "Explorer la carte ↗ (nouvel onglet)" : "Explorer la carte ↗";
    copy.append(title, description, action);
    link.append(copy);
    slide.append(link);
    track.append(slide);
  });

  function scrollStops() {
    const maximum = Math.max(0, track.scrollWidth - track.clientWidth);
    const first = track.firstElementChild.offsetLeft;
    return [...new Set([...track.children].map(slide =>
      Math.min(maximum, slide.offsetLeft - first)))];
  }

  function updatePosition() {
    const stops = scrollStops();
    activeIndex = stops.reduce((nearest, left, index) =>
      Math.abs(left - track.scrollLeft) < Math.abs(stops[nearest] - track.scrollLeft)
        ? index : nearest, 0);
    previous.disabled = activeIndex === 0;
    next.disabled = activeIndex === stops.length - 1;
    position.textContent = `${activeIndex + 1} / ${stops.length}`;
  }

  function moveBy(delta) {
    const stops = scrollStops();
    const index = Math.max(0, Math.min(stops.length - 1, activeIndex + delta));
    track.scrollTo({
      left: stops[index],
      behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "instant" : "smooth",
    });
  }

  previous.addEventListener("click", () => moveBy(-1));
  next.addEventListener("click", () => moveBy(1));
  track.addEventListener("scroll", updatePosition, { passive: true });
  track.addEventListener("keydown", (event) => {
    if (event.key === "ArrowLeft" || event.key === "ArrowRight") {
      event.preventDefault();
      moveBy(event.key === "ArrowLeft" ? -1 : 1);
    }
  });
  // Preserve the selected map when the viewport changes orientation or size.
  new ResizeObserver(() => {
    const stops = scrollStops();
    track.scrollTo({ left: stops[Math.min(activeIndex, stops.length - 1)], behavior: "instant" });
    updatePosition();
  }).observe(track);
  document.getElementById("cartes-phares").hidden = false;
  document.getElementById("featured-shortcut").hidden = false;
  updatePosition();
}

loadFeaturedMaps();
