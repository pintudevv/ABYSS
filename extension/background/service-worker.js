// ABYSS Cyber Sentinel Background Service Worker (Manifest V3)

const API_URL = "http://localhost:8000/url-scan";
const FALLBACK_API = "https://abyss-1-d265.onrender.com/url-scan";
const LEAK_API = "https://abyss-1-d265.onrender.com/leak-check";

// ---------------------------------------------------------------------------
// FEATURE 1: Right-Click Context Menu ("Scan with ABYSS")
// ---------------------------------------------------------------------------
chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "abyss-scan-link",
    title: "🛡️ Scan Link Safety with ABYSS",
    contexts: ["link"]
  });

  chrome.contextMenus.create({
    id: "abyss-scan-text",
    title: "🛡️ Check Email / Token Leak Status",
    contexts: ["selection"]
  });

  chrome.contextMenus.create({
    id: "abyss-poison-page",
    title: "⚡ Neutralize & Poison Attacker Form",
    contexts: ["page"]
  });
});

chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  if (!tab || !tab.id) return;

  if (info.menuItemId === "abyss-scan-link" && info.linkUrl) {
    try {
      let response;
      try {
        response = await fetch(`${API_URL}?url=${encodeURIComponent(info.linkUrl)}`);
      } catch {
        response = await fetch(`${FALLBACK_API}?url=${encodeURIComponent(info.linkUrl)}`);
      }
      const data = await response.json();
      chrome.tabs.sendMessage(tab.id, { action: "SHOW_CONTEXT_RESULT", type: "LINK", data });
    } catch (e) {
      chrome.tabs.sendMessage(tab.id, { action: "SHOW_CONTEXT_RESULT", type: "ERROR", message: "Failed to query ABYSS URL Analyzer" });
    }
  } else if (info.menuItemId === "abyss-scan-text" && info.selectionText) {
    try {
      const response = await fetch(`${LEAK_API}?email=${encodeURIComponent(info.selectionText.trim())}`);
      const data = await response.json();
      chrome.tabs.sendMessage(tab.id, { action: "SHOW_CONTEXT_RESULT", type: "LEAK", data });
    } catch (e) {
      chrome.tabs.sendMessage(tab.id, { action: "SHOW_CONTEXT_RESULT", type: "ERROR", message: "Failed to query Dark Web Leak Database" });
    }
  } else if (info.menuItemId === "abyss-poison-page") {
    chrome.tabs.sendMessage(tab.id, { action: "POISON_DECOY" });
  }
});

// Listen to Tab Updates
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.status === "complete" && tab.url && tab.url.startsWith("http")) {
    checkTabUrl(tabId, tab.url);
  }
});

async function checkTabUrl(tabId, url) {
  try {
    let response;
    try {
      response = await fetch(`${API_URL}?url=${encodeURIComponent(url)}`);
    } catch {
      response = await fetch(`${FALLBACK_API}?url=${encodeURIComponent(url)}`);
    }

    const data = await response.json();
    if (data.is_phishing || data.risk_score >= 45) {
      chrome.action.setBadgeBackgroundColor({ tabId, color: "#ff3366" });
      chrome.action.setBadgeText({ tabId, text: "WARN" });
    } else {
      chrome.action.setBadgeBackgroundColor({ tabId, color: "#00ff88" });
      chrome.action.setBadgeText({ tabId, text: "SAFE" });
    }
  } catch {
    chrome.action.setBadgeText({ tabId, text: "" });
  }
}

// Listen to Messages from Content Script
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "CHECK_URL_SAFETY" && request.url) {
    fetch(`${API_URL}?url=${encodeURIComponent(request.url)}`)
      .then((res) => res.json())
      .then((data) => sendResponse(data))
      .catch(() => {
        fetch(`${FALLBACK_API}?url=${encodeURIComponent(request.url)}`)
          .then((res) => res.json())
          .then((data) => sendResponse(data))
          .catch((err) => sendResponse({ error: err.toString() }));
      });
    return true; // Keep message channel open for async response
  }
});
