// ABYSS Cyber Sentinel Background Service Worker (Manifest V3)

const API_URL = "http://localhost:8000/url-scan";
const FALLBACK_API = "https://abyss-1-d265.onrender.com/url-scan";

// Listen to Tab Updates
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.status === "complete" && tab.url && tab.url.startswith("http")) {
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
