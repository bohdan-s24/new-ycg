// Handles token save/load/clear from chrome.storage
export async function saveToken(token) {
  if (typeof chrome !== "undefined" && chrome.storage && chrome.storage.local) {
    await chrome.storage.local.set({ ycg_token: token });
  }
}

export async function loadToken() {
  if (typeof chrome !== "undefined" && chrome.storage && chrome.storage.local) {
    const result = await chrome.storage.local.get("ycg_token");
    return result.ycg_token;
  }
  return null;
}

export async function clearToken() {
  if (typeof chrome !== "undefined" && chrome.storage && chrome.storage.local) {
    await chrome.storage.local.remove("ycg_token");
  }
}
