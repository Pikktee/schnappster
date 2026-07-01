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

/** Prüft, ob die URL eine Kleinanzeigen-Einzelanzeige (Detailseite) ist. */
function isKleinanzeigenAdUrl(url) {
  if (!url) return false;
  try {
    const u = new URL(url);
    const host = u.hostname.toLowerCase();
    if (host !== "kleinanzeigen.de" && host !== "www.kleinanzeigen.de") return false;
    return u.pathname.startsWith("/s-anzeige/");
  } catch {
    return false;
  }
}

/** Extrahiert die externe Anzeigen-ID aus der Detailseiten-URL (…/titel/<id>-…). */
function extractExternalId(url) {
  try {
    const path = new URL(url).pathname.replace(/\/+$/, "");
    const last = path.split("/").pop() || "";
    const id = last.split("-")[0];
    return /^\d+$/.test(id) ? id : null;
  } catch {
    return null;
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

function getToken() {
  return new Promise((resolve) => {
    chrome.storage.sync.get({ token: "" }, (items) => resolve(items.token || ""));
  });
}

/** Standard-Header inkl. Bearer-Token, falls angemeldet. */
async function authHeaders() {
  const token = await getToken();
  const headers = { "Content-Type": "application/json" };
  if (token) headers.Authorization = `Bearer ${token}`;
  return headers;
}

function updateActionForTab(tabId, url) {
  if (tabId == null) return;
  if (isKleinanzeigenSearchUrl(url)) {
    chrome.action.enable(tabId);
    chrome.action.setTitle({ tabId, title: "Suchauftrag zu Schnappster hinzufügen" });
    chrome.action.setIcon({ tabId, path: ENABLED_ICON_PATHS });
  } else if (isKleinanzeigenAdUrl(url)) {
    chrome.action.enable(tabId);
    chrome.action.setTitle({ tabId, title: "Verhandlungsnachricht einfügen (Schnappster)" });
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
      toast.style.maxWidth = "min(90vw, 520px)";
      toast.style.textAlign = "center";
      document.body.appendChild(toast);

      requestAnimationFrame(() => {
        toast.style.opacity = "1";
        toast.style.transform = "translateX(-50%) translateY(0)";
      });

      setTimeout(() => {
        toast.style.opacity = "0";
        toast.style.transform = "translateX(-50%) translateY(-6px)";
      }, 3600);

      setTimeout(() => {
        toast.remove();
      }, 3900);
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
  const title = (rawTitle || "").replace(/ /g, " ").trim();
  if (!title) return fallback;

  // Entfernt einen Domain-Suffix robust, z. B.:
  // " - kleinanzeigen.de", " | kleinanzeigen.de", "... kleinanzeigen.de"
  const withoutDomain = title
    .replace(/\s*(?:[-|:–—]\s*)?kleinanzeigen\.de\s*$/i, "")
    .trim();

  return withoutDomain || fallback;
}

/** Übersetzt Fetch-/HTTP-Fehler in eine kurze, verständliche Meldung. */
function friendlyHttpReason(status, detail) {
  if (status === 401) return "Nicht angemeldet. Bitte in den Extension-Einstellungen anmelden.";
  if (status === 404) return "Backend nicht gefunden (404). Prüfe die Base-URL in den Einstellungen.";
  if (status >= 500) return "Serverfehler. Ist das Schnappster-Backend erreichbar?";
  return detail || `Fehler: ${status}`;
}

async function addSearchToSchnappster(tab) {
  const url = tab?.url;
  const name = buildSearchName(tab?.title);
  const baseUrl = await getBaseUrl();

  const body = { name, url, is_active: true, scrape_interval_minutes: 30 };

  try {
    const res = await fetch(`${baseUrl}/adsearches/`, {
      method: "POST",
      headers: await authHeaders(),
      body: JSON.stringify(body),
    });

    const text = await res.text();
    let detail = "";
    try {
      const json = JSON.parse(text);
      detail = json.detail
        ? Array.isArray(json.detail) ? json.detail.join(", ") : String(json.detail)
        : "";
    } catch {
      detail = text.slice(0, 100);
    }

    if (res.ok) {
      showBadge(tab?.id, "OK", "#0f9d58");
      showPageToast(tab?.id, "Suchauftrag erfolgreich hinzugefügt.", false);
      showNotification({ title: "Schnappster", message: "Suchauftrag wurde hinzugefügt." });
    } else {
      const reason = friendlyHttpReason(res.status, detail);
      showBadge(tab?.id, "ERR", "#d93025");
      showPageToast(tab?.id, reason, true);
      showNotification({ title: "Schnappster – Fehler", message: reason });
    }
  } catch (err) {
    const message =
      err.message && err.message.includes("Failed to fetch")
        ? "Backend nicht erreichbar. Prüfe die Base-URL und ob Schnappster läuft."
        : err.message || "Unbekannter Fehler";
    showBadge(tab?.id, "ERR", "#d93025");
    showPageToast(tab?.id, message, true);
    showNotification({ title: "Schnappster – Fehler", message });
  }
}

/** Fügt Text in das Kleinanzeigen-Nachrichtenfeld ein (per nativem Setter + Input-Event). */
async function insertMessageIntoContactField(tabId, message) {
  try {
    const results = await chrome.scripting.executeScript({
      target: { tabId },
      func: (msg) => {
        const field =
          document.getElementById("viewad-contact-message") ||
          document.querySelector("textarea[name='message']") ||
          document.querySelector("#viewad-contact-modal-form textarea");
        if (!field) return false;
        const proto = window.HTMLTextAreaElement && window.HTMLTextAreaElement.prototype;
        const setter = proto && Object.getOwnPropertyDescriptor(proto, "value")?.set;
        if (setter) setter.call(field, msg);
        else field.value = msg;
        field.dispatchEvent(new Event("input", { bubbles: true }));
        field.dispatchEvent(new Event("change", { bubbles: true }));
        field.focus();
        field.scrollIntoView({ behavior: "smooth", block: "center" });
        return true;
      },
      args: [message],
    });
    return Boolean(results && results[0] && results[0].result);
  } catch {
    return false;
  }
}

async function negotiateOnAdPage(tab) {
  const externalId = extractExternalId(tab?.url);
  if (!externalId) {
    showPageToast(tab?.id, "Keine Anzeigen-ID in der URL erkannt.", true);
    return;
  }

  const token = await getToken();
  if (!token) {
    showPageToast(tab?.id, "Bitte in den Extension-Einstellungen anmelden.", true);
    showNotification({ title: "Schnappster", message: "Bitte in den Einstellungen anmelden." });
    return;
  }

  const baseUrl = await getBaseUrl();
  const headers = await authHeaders();
  showPageToast(tab?.id, "Schnappster erstellt eine Verhandlungsnachricht…", false);

  // 1. Passende Schnappster-Anzeige über die externe ID finden.
  let ad;
  try {
    const res = await fetch(
      `${baseUrl}/ads/?external_id=${encodeURIComponent(externalId)}&limit=1`,
      { headers },
    );
    if (!res.ok) {
      showPageToast(tab?.id, friendlyHttpReason(res.status, ""), true);
      return;
    }
    const data = await res.json();
    ad = data.items && data.items[0];
  } catch {
    showPageToast(tab?.id, "Backend nicht erreichbar. Base-URL prüfen.", true);
    return;
  }
  if (!ad) {
    showPageToast(
      tab?.id,
      "Diese Anzeige ist (noch) nicht in Schnappster. Lege einen Suchauftrag an, der sie erfasst.",
      true,
    );
    return;
  }

  // 2. Verhandlungsnachricht generieren lassen.
  let result;
  try {
    const res = await fetch(`${baseUrl}/ads/${ad.id}/negotiation-message`, {
      method: "POST",
      headers,
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const detail = typeof data.detail === "string" ? data.detail : "";
      showPageToast(tab?.id, friendlyHttpReason(res.status, detail), true);
      return;
    }
    result = data;
  } catch {
    showPageToast(tab?.id, "Backend nicht erreichbar. Base-URL prüfen.", true);
    return;
  }

  // 3. In das Kleinanzeigen-Nachrichtenfeld einfügen.
  const inserted = await insertMessageIntoContactField(tab?.id, result.message || "");
  if (!inserted) {
    showPageToast(
      tab?.id,
      "Nachrichtenfeld nicht gefunden. Öffne ggf. „Nachricht schreiben“ und stelle sicher, dass du eingeloggt bist.",
      true,
    );
    return;
  }

  const offer =
    typeof result.suggested_offer === "number"
      ? ` (Gebot: ${Math.round(result.suggested_offer)} €)`
      : "";
  showBadge(tab?.id, "OK", "#0f9d58");
  showPageToast(tab?.id, `Verhandlungsnachricht eingefügt${offer}. Bitte prüfen und absenden.`, false);
}

chrome.action.onClicked.addListener(async (tab) => {
  if (!tab?.url) return;
  if (isKleinanzeigenSearchUrl(tab.url)) {
    await addSearchToSchnappster(tab);
  } else if (isKleinanzeigenAdUrl(tab.url)) {
    await negotiateOnAdPage(tab);
  }
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
