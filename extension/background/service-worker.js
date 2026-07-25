// ABYSS Cyber Sentinel — Background Service Worker v1.2.7

const API_URL      = "http://localhost:8000/url-scan";
const FALLBACK_API = "https://abyss-1-d265.onrender.com/url-scan";
const LEAK_API     = "https://abyss-1-d265.onrender.com/leak-check";

// Simple in-memory cache so we don't hammer APIs
const _cache = {};
function cached(key, fn, ttlMs = 300_000) {
  if (_cache[key] && Date.now() - _cache[key].ts < ttlMs) return Promise.resolve(_cache[key].val);
  return fn().then(val => { _cache[key] = { val, ts: Date.now() }; return val; });
}

// ─── CONTEXT MENUS ───────────────────────────────────────────────────────────
chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({ id: "abyss-scan-link",  title: "Scan Link Safety with ABYSS",       contexts: ["link"]      });
  chrome.contextMenus.create({ id: "abyss-scan-text",  title: "Check Email / Token Leak Status",   contexts: ["selection"] });
  chrome.contextMenus.create({ id: "abyss-poison-page",title: "Neutralize & Poison Attacker Form", contexts: ["page"]      });
});

chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  if (!tab || !tab.id) return;

  if (info.menuItemId === "abyss-scan-link" && info.linkUrl) {
    try {
      let resp;
      try { resp = await fetch(`${API_URL}?url=${encodeURIComponent(info.linkUrl)}`); }
      catch { resp = await fetch(`${FALLBACK_API}?url=${encodeURIComponent(info.linkUrl)}`); }
      chrome.tabs.sendMessage(tab.id, { action: "SHOW_CONTEXT_RESULT", type: "LINK", data: await resp.json() });
    } catch {
      chrome.tabs.sendMessage(tab.id, { action: "SHOW_CONTEXT_RESULT", type: "ERROR", data: { message: "Failed to query ABYSS URL Analyzer" } });
    }

  } else if (info.menuItemId === "abyss-scan-text" && info.selectionText) {
    try {
      const resp = await fetch(`${LEAK_API}?email=${encodeURIComponent(info.selectionText.trim())}`);
      chrome.tabs.sendMessage(tab.id, { action: "SHOW_CONTEXT_RESULT", type: "LEAK", data: await resp.json() });
    } catch {
      chrome.tabs.sendMessage(tab.id, { action: "SHOW_CONTEXT_RESULT", type: "ERROR", data: { message: "Failed to query Dark Web Leak Database" } });
    }

  } else if (info.menuItemId === "abyss-poison-page") {
    chrome.tabs.sendMessage(tab.id, { action: "POISON_DECOY" });
  }
});

// ─── TAB URL SAFETY CHECK (badge) ────────────────────────────────────────────
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.status === "complete" && tab.url && tab.url.startsWith("http")) {
    checkTabUrl(tabId, tab.url);
  }
});

async function checkTabUrl(tabId, url) {
  try {
    let resp;
    try { resp = await fetch(`${API_URL}?url=${encodeURIComponent(url)}`); }
    catch { resp = await fetch(`${FALLBACK_API}?url=${encodeURIComponent(url)}`); }
    const data = await resp.json();
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

// ─── MESSAGE HANDLER ─────────────────────────────────────────────────────────
chrome.runtime.onMessage.addListener((req, _sender, sendResp) => {

  // Existing: page URL safety
  if (req.action === "CHECK_URL_SAFETY" && req.url) {
    fetch(`${API_URL}?url=${encodeURIComponent(req.url)}`)
      .then(r => r.json()).then(sendResp)
      .catch(() => fetch(`${FALLBACK_API}?url=${encodeURIComponent(req.url)}`).then(r => r.json()).then(sendResp).catch(e => sendResp({ error: e.toString() })));
    return true;
  }

  // NEW: Domain Age Check via RDAP (no API key needed, public standard)
  if (req.action === "CHECK_DOMAIN_AGE" && req.domain) {
    cached("age_" + req.domain, async () => {
      // Try RDAP bootstrap — works for .com/.net/.org and most gTLDs
      const rdapUrl = `https://rdap.org/domain/${req.domain}`;
      try {
        const resp = await fetch(rdapUrl, { signal: AbortSignal.timeout(4000) });
        if (!resp.ok) return { agedays: null, registered: null };
        const data = await resp.json();
        // Find registration date in RDAP events
        const reg = (data.events || []).find(ev => ev.eventAction === "registration");
        if (!reg) return { agedays: null, registered: null };
        const regDate = new Date(reg.eventDate);
        const agedays = Math.floor((Date.now() - regDate.getTime()) / 86400000);
        return { agedays, registered: reg.eventDate.split("T")[0] };
      } catch {
        return { agedays: null, registered: null };
      }
    }).then(sendResp).catch(() => sendResp({ agedays: null, registered: null }));
    return true;
  }

  // NEW: URL Unshortener — resolves final destination of short URLs
  if (req.action === "UNSHORTEN_URL" && req.url) {
    cached("short_" + req.url, async () => {
      try {
        // Use a public unshortening API (no-CORS approach via background)
        const resp = await fetch(req.url, {
          method: "HEAD",
          redirect: "follow",
          signal: AbortSignal.timeout(5000)
        });
        return { finalUrl: resp.url };
      } catch {
        // Fallback: try unshorten.me public API
        try {
          const r = await fetch(`https://unshorten.me/s/${encodeURIComponent(req.url)}`, { signal: AbortSignal.timeout(4000) });
          const text = await r.text();
          const m = text.match(/href="([^"]+)"/);
          return { finalUrl: m ? m[1] : req.url };
        } catch {
          return { finalUrl: req.url };
        }
      }
    }).then(sendResp).catch(() => sendResp({ finalUrl: req.url }));
    return true;
  }

});
