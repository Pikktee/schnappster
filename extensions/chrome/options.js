const DEFAULT_BASE_URL = "http://localhost:8000";

const $ = (id) => document.getElementById(id);

function getBaseUrl() {
  return new Promise((resolve) => {
    chrome.storage.sync.get({ baseUrl: DEFAULT_BASE_URL }, (items) => {
      resolve((items.baseUrl || DEFAULT_BASE_URL).trim().replace(/\/+$/, "") || DEFAULT_BASE_URL);
    });
  });
}

function setStatus(el, text, ok) {
  el.textContent = text;
  el.style.color = ok ? "green" : "#d93025";
  if (text) setTimeout(() => { el.textContent = ""; }, 3000);
}

function renderAuthState() {
  chrome.storage.sync.get({ token: "", userEmail: "" }, (items) => {
    const loggedIn = Boolean(items.token);
    $("loggedIn").style.display = loggedIn ? "block" : "none";
    $("loggedOut").style.display = loggedIn ? "none" : "block";
    if (loggedIn) $("userEmail").textContent = items.userEmail || "";
  });
}

// --- Base-URL ---
$("baseUrl").placeholder = DEFAULT_BASE_URL;
chrome.storage.sync.get({ baseUrl: DEFAULT_BASE_URL }, (items) => {
  $("baseUrl").value = (items.baseUrl || DEFAULT_BASE_URL).replace(/\/+$/, "");
});
$("save").addEventListener("click", () => {
  const value = ($("baseUrl").value.trim().replace(/\/+$/, "")) || DEFAULT_BASE_URL;
  chrome.storage.sync.set({ baseUrl: value }, () => setStatus($("baseStatus"), "Gespeichert.", true));
});

// --- Login ---
$("login").addEventListener("click", async () => {
  const email = $("email").value.trim();
  const password = $("password").value;
  if (!email || !password) {
    setStatus($("loginStatus"), "Bitte E-Mail und Passwort eingeben.", false);
    return;
  }
  const baseUrl = await getBaseUrl();
  setStatus($("loginStatus"), "Anmelden…", true);
  try {
    const res = await fetch(`${baseUrl}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok || !data.access_token) {
      const detail = typeof data.detail === "string" ? data.detail : "Anmeldung fehlgeschlagen.";
      setStatus($("loginStatus"), detail, false);
      return;
    }
    chrome.storage.sync.set({ token: data.access_token, userEmail: email }, () => {
      $("password").value = "";
      setStatus($("loginStatus"), "Angemeldet.", true);
      renderAuthState();
    });
  } catch {
    setStatus($("loginStatus"), "Backend nicht erreichbar. Base-URL prüfen.", false);
  }
});

// --- Logout ---
$("logout").addEventListener("click", () => {
  chrome.storage.sync.remove(["token", "userEmail"], renderAuthState);
});

renderAuthState();
