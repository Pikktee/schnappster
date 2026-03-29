/**
 * Prüft, ob die URL eine Kleinanzeigen-Suchergebnisseite ist (keine Einzelanzeige).
 */
function isKleinanzeigenSearchUrl(url) {
  if (!url) return false;
  try {
    const u = new URL(url);
    const host = u.hostname.toLowerCase();
    if (host !== "kleinanzeigen.de" && host !== "www.kleinanzeigen.de") return false;
    const path = u.pathname;
    return path.startsWith("/s-") && !path.startsWith("/s-anzeige/");
  } catch {
    return false;
  }
}

const DEFAULT_BASE_URL = "http://localhost:8000";
const NOTIFICATION_ID = "schnappster-result";
const ENABLED_ICON_PATHS = {
  16: "icons/icon16.png",
  48: "icons/icon48.png",
  128: "icons/icon128.png",
};
const DISABLED_ICON_PATHS = ENABLED_ICON_PATHS;

function getBaseUrl() {
  return new Promise((resolve) => {
    chrome.storage.sync.get({ baseUrl: DEFAULT_BASE_URL }, (items) => {
      let base = (items.baseUrl || DEFAULT_BASE_URL).trim();
      base = base.replace(/\/+$/, "");
      resolve(base || DEFAULT_BASE_URL);
    });
  });
}

function updateActionForTab(tabId, url) {
  if (tabId == null) return;
  const enabled = isKleinanzeigenSearchUrl(url);
  if (enabled) {
    chrome.action.enable(tabId);
    chrome.action.setIcon({ tabId, path: ENABLED_ICON_PATHS });
  } else {
    chrome.action.disable(tabId);
    chrome.action.setIcon({ tabId, path: DISABLED_ICON_PATHS });
    chrome.action.setBadgeText({ tabId, text: "" });
  }
}

function refreshAllTabsActionState() {
  chrome.tabs.query({}, (tabs) => {
    for (const tab of tabs) {
      if (tab.id != null) {
        updateActionForTab(tab.id, tab.url);
      }
    }
  });
}

function showNotification(options) {
  chrome.notifications.create(NOTIFICATION_ID, {
    type: "basic",
    iconUrl: "icons/icon48.png",
    ...options,
  });
}

function showPageToast(tabId, message, isError = false) {
  if (tabId == null) return;
  chrome.scripting.executeScript({
    target: { tabId },
    func: (text, errorState) => {
      const existing = document.getElementById("schnappster-extension-toast");
      if (existing) existing.remove();

      const toast = document.createElement("div");
      toast.id = "schnappster-extension-toast";
      toast.textContent = text;
      toast.style.position = "fixed";
      toast.style.top = "24px";
      toast.style.left = "50%";
      toast.style.transform = "translateX(-50%)";
      toast.style.zIndex = "2147483647";
      toast.style.padding = "14px 20px";
      toast.style.borderRadius = "12px";
      toast.style.fontSize = "16px";
      toast.style.fontWeight = "700";
      toast.style.fontFamily = "system-ui, -apple-system, Segoe UI, Roboto, sans-serif";
      toast.style.color = "#ffffff";
      toast.style.background = errorState ? "#d93025" : "#0f9d58";
      toast.style.boxShadow = "0 10px 30px rgba(0,0,0,0.35)";
      toast.style.opacity = "0";
      toast.style.transition = "opacity 180ms ease, transform 180ms ease";
      toast.style.pointerEvents = "none";
      document.body.appendChild(toast);

      requestAnimationFrame(() => {
        toast.style.opacity = "1";
        toast.style.transform = "translateX(-50%) translateY(0)";
      });

      setTimeout(() => {
        toast.style.opacity = "0";
        toast.style.transform = "translateX(-50%) translateY(-6px)";
      }, 2400);

      setTimeout(() => {
        toast.remove();
      }, 2700);
    },
    args: [message, isError],
  }).catch(() => {
    // Ignore: scripting may fail on restricted pages.
  });
}

function showBadge(tabId, text, color) {
  if (tabId == null) return;
  chrome.action.setBadgeBackgroundColor({ tabId, color });
  chrome.action.setBadgeText({ tabId, text });
  setTimeout(() => {
    chrome.action.setBadgeText({ tabId, text: "" });
  }, 3000);
}

function buildSearchName(rawTitle) {
  const fallback = "Kleinanzeigen-Suche";
  const title = (rawTitle || "").replace(/\u00a0/g, " ").trim();
  if (!title) return fallback;

  // Entfernt einen Domain-Suffix robust, z. B.:
  // " - kleinanzeigen.de", " | kleinanzeigen.de", "... kleinanzeigen.de"
  const withoutDomain = title
    .replace(/\s*(?:[-|:–—]\s*)?kleinanzeigen\.de\s*$/i, "")
    .trim();

  return withoutDomain || fallback;
}

async function addSearchToSchnappster(tab) {
  const url = tab?.url;
  const name = buildSearchName(tab?.title);

  const baseUrl = await getBaseUrl();
  const apiUrl = `${baseUrl}/api/adsearches/`;

  const body = {
    name,
    url,
    is_active: true,
    scrape_interval_minutes: 30,
  };

  try {
    const res = await fetch(apiUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    const text = await res.text();
    let detail = "";
    try {
      const json = JSON.parse(text);
      detail = json.detail ? (Array.isArray(json.detail) ? json.detail.join(", ") : String(json.detail)) : "";
    } catch {
      detail = text.slice(0, 100);
    }

    if (res.ok) {
      showBadge(tab?.id, "OK", "#0f9d58");
      showPageToast(tab?.id, "Suchauftrag erfolgreich hinzugefügt.", false);
      showNotification({
        title: "Schnappster",
        message: "Suchauftrag wurde hinzugefügt.",
      });
    } else {
      const shortReason = res.status === 404
        ? "Backend nicht gefunden (404). Prüfe die Base-URL in den Einstellungen."
        : res.status >= 500
          ? "Serverfehler. Ist das Schnappster-Backend erreichbar?"
          : detail || `Fehler: ${res.status}`;
      showBadge(tab?.id, "ERR", "#d93025");
      showPageToast(tab?.id, shortReason, true);
      showNotification({
        title: "Schnappster – Fehler",
        message: shortReason,
      });
    }
  } catch (err) {
    const message =
      err.message && err.message.includes("Failed to fetch")
        ? "Backend nicht erreichbar. Prüfe die Base-URL und ob Schnappster läuft."
        : (err.message || "Unbekannter Fehler");
    showBadge(tab?.id, "ERR", "#d93025");
    showPageToast(tab?.id, message, true);
    showNotification({
      title: "Schnappster – Fehler",
      message,
    });
  }
}

chrome.action.onClicked.addListener(async (tab) => {
  if (!tab?.url || !isKleinanzeigenSearchUrl(tab.url)) return;
  await addSearchToSchnappster(tab);
});

chrome.tabs.onActivated.addListener(async (activeInfo) => {
  try {
    const tab = await chrome.tabs.get(activeInfo.tabId);
    updateActionForTab(tab.id, tab.url);
  } catch {
    // Tab may be invalid
  }
});

chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.url !== undefined || changeInfo.status === "complete") {
    updateActionForTab(tabId, tab?.url || changeInfo.url);
  }
});

chrome.tabs.onCreated.addListener((tab) => {
  if (tab?.id != null) {
    updateActionForTab(tab.id, tab.url);
  }
});

chrome.windows.onFocusChanged.addListener(() => {
  chrome.tabs.query({ active: true, lastFocusedWindow: true }, (tabs) => {
    const tab = tabs?.[0];
    if (tab?.id != null) {
      updateActionForTab(tab.id, tab.url);
    }
  });
});

chrome.runtime.onStartup.addListener(() => {
  chrome.action.disable();
  refreshAllTabsActionState();
});

chrome.runtime.onInstalled.addListener(() => {
  chrome.action.disable();
  refreshAllTabsActionState();
});

// Safe default: action is disabled everywhere until a matching tab is detected.
chrome.action.disable();
refreshAllTabsActionState();
