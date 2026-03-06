const DEFAULT_BASE_URL = "http://localhost:8000";

document.getElementById("baseUrl").placeholder = DEFAULT_BASE_URL;

chrome.storage.sync.get({ baseUrl: DEFAULT_BASE_URL }, (items) => {
  document.getElementById("baseUrl").value = (items.baseUrl || DEFAULT_BASE_URL).replace(/\/+$/, "");
});

document.getElementById("save").addEventListener("click", () => {
  let value = document.getElementById("baseUrl").value.trim().replace(/\/+$/, "");
  if (!value) value = DEFAULT_BASE_URL;
  chrome.storage.sync.set({ baseUrl: value }, () => {
    const status = document.getElementById("status");
    status.textContent = "Gespeichert.";
    status.style.color = "green";
    setTimeout(() => {
      status.textContent = "";
    }, 2000);
  });
});
