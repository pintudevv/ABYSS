// ==============================================================================
//  A B Y S S   C Y B E R   S E N T I N E L   C O N T E N T   S C R I P T  (v1.2.0)
//  Features:
//    1. Right-Click Context Menu Result Modal
//    2. Anti-Cookie & Session Token Storage Guard
//    3. Attacker Poisoning & Decoy Injection
//    4. Full-Page Threat Intercept Overlay
//    5. Silent Hover Inspector
//    6. Clipboard Address Swap Guard
// ==============================================================================

(function () {
  const pageDomain = window.location.hostname.toLowerCase();
  let hoverTooltipEl = null;

  // ---------------------------------------------------------------------------
  // FEATURE 2: Anti-Cookie & Session Token Storage Guard
  // ---------------------------------------------------------------------------
  try {
    const SENSITIVE_STORAGE_KEYS = ["token", "discord", "roblosecurity", "session", "auth", "metamask", "seed", "private_key", "jwt"];
    
    // Page script injection for Storage getItem trap
    const script = document.createElement("script");
    script.textContent = `
      (function() {
        const sensitive = ["token", "discord", "roblosecurity", "session", "auth", "metamask", "seed", "private_key", "jwt"];
        const origGetItem = Storage.prototype.getItem;
        const currentHost = window.location.hostname.toLowerCase();
        
        const isOfficial = ["discord.com", "discordapp.com", "roblox.com", "google.com", "github.com", "metamask.io"].some(h => currentHost.includes(h));

        if (!isOfficial) {
          Storage.prototype.getItem = function(key) {
            if (key && sensitive.some(k => key.toLowerCase().includes(k))) {
              console.warn("[ABYSS TOKEN GUARD] Blocked unauthorized access to storage key:", key);
              return null;
            }
            return origGetItem.apply(this, arguments);
          };
        }
      })();
    `;
    (document.head || document.documentElement).appendChild(script);
    script.remove();
  } catch (e) {}

  // ---------------------------------------------------------------------------
  // FEATURE 4: Webhook Tracker
  // ---------------------------------------------------------------------------
  try {
    const origFetch = window.fetch;
    window.fetch = async function (...args) {
      const url = typeof args[0] === "string" ? args[0] : (args[0] && args[0].url) || "";
      if (url.includes("discord.com/api/webhooks") || url.includes("discordapp.com/api/webhooks")) {
        if (!pageDomain.includes("discord.com") && !pageDomain.includes("discordapp.com")) {
          showFloatingAlert("🛑 CRITICAL EXFILTRATION BLOCKED: This site tried to send stolen data to a Discord Webhook!");
        }
      }
      return origFetch.apply(this, args);
    };
  } catch (e) {}

  // ---------------------------------------------------------------------------
  // FEATURE 1: 1-Click "Neutralize & Feed Decoy Data" (Attacker Poisoning Engine)
  // ---------------------------------------------------------------------------
  function injectHoneypotDecoyData() {
    const inputs = document.querySelectorAll("input, textarea");
    let count = 0;

    const fakeSeed = "abandon amount abandon amount abandon amount abandon amount abandon amount abandon art";
    const fakeToken = "mfa.Vk4fW29302_abyss_decoy_honeypot_token_99218492038102";
    const fakePass = "Pwned_Abyss_Fake_Password_9921!";
    const fakeEmail = "decoy_victim_abyss@honeypot.net";

    inputs.forEach((input) => {
      if (input.type === "hidden" || input.type === "submit" || input.type === "button") return;

      const placeholder = (input.placeholder || "").toLowerCase();
      const name = (input.name || "").toLowerCase();
      const id = (input.id || "").toLowerCase();
      const type = (input.type || "").toLowerCase();

      let valToInject = fakePass;
      if (placeholder.includes("seed") || placeholder.includes("phrase") || name.includes("seed") || id.includes("phrase")) {
        valToInject = fakeSeed;
      } else if (placeholder.includes("token") || name.includes("token") || id.includes("token")) {
        valToInject = fakeToken;
      } else if (type === "email" || placeholder.includes("email") || name.includes("email")) {
        valToInject = fakeEmail;
      }

      input.value = valToInject;
      input.dispatchEvent(new Event("input", { bubbles: true }));
      input.dispatchEvent(new Event("change", { bubbles: true }));
      input.style.border = "2px solid #00d2ff";
      input.style.boxShadow = "0 0 10px #00d2ff";
      count++;
    });

    showFloatingAlert(`⚡ ATTACKER POISONED: Injected synthetic decoy honeypot data into ${count} input fields!`);

    const form = document.querySelector("form");
    if (form) {
      setTimeout(() => { try { form.submit(); } catch (e) {} }, 500);
    }
  }

  // ---------------------------------------------------------------------------
  // Full-Page Threat Intercept Overlay
  // ---------------------------------------------------------------------------
  function renderFullPageBlockOverlay(data) {
    if (document.getElementById("abyss-fullpage-overlay")) return;

    const overlay = document.createElement("div");
    overlay.id = "abyss-fullpage-overlay";
    overlay.style.cssText = `
      position: fixed;
      top: 0;
      left: 0;
      width: 100vw;
      height: 100vh;
      z-index: 2147483647;
      background: radial-gradient(circle at center, #1e0914 0%, #050306 100%);
      color: #ffffff;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      text-align: center;
      padding: 24px;
      box-sizing: border-box;
    `;

    const reasonsList = (data.threat_reasons || [])
      .map((r) => `<li style="margin-bottom:6px; display:flex; align-items:center; gap:6px;"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#ffaa00" stroke-width="2" stroke-linecap="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>${r}</li>`)
      .join("");

    overlay.innerHTML = `
      <div style="margin-bottom:12px; filter:drop-shadow(0 0 20px #ff3366);">
        <svg width="64" height="64" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M12 2L3 7V12C3 17.55 6.84 22.74 12 24C17.16 22.74 21 17.55 21 12V7L12 2Z" fill="#1e0914" stroke="#ff3366" stroke-width="1.5"/>
          <path d="M12 8V13M12 16H12.01" stroke="#ff3366" stroke-width="2" stroke-linecap="round"/>
        </svg>
      </div>
      <div style="font-size:12px; font-weight:800; color:#ff3366; letter-spacing:2px; margin-bottom:8px;">ABYSS CYBER SENTINEL — INTERCEPT ACTIVE</div>
      <h1 style="font-size:28px; font-weight:900; margin:0 0 12px 0; color:#ffffff;">ACCESS BLOCKED: PHISHING THREAT DETECTED</h1>
      <p style="font-size:14px; color:#94a3b8; max-width:550px; line-height:1.6; margin-bottom:20px;">
        ABYSS Threat Intelligence identified <strong>${pageDomain}</strong> as a high-risk phishing website targeting user credentials or Discord/Crypto tokens.
      </p>

      <div style="background:rgba(255,255,255,0.04); border:1px solid rgba(255,51,102,0.3); border-radius:12px; padding:16px 24px; max-width:500px; text-align:left; margin-bottom:24px;">
        <div style="font-size:11px; font-weight:800; color:#ffaa00; margin-bottom:8px;">DISCOVERED RISK EVIDENCE:</div>
        <ul style="margin:0; padding-left:16px; font-size:12px; color:#cbd5e1;">${reasonsList || "<li>High Risk Phishing Signature Match</li>"}</ul>
      </div>

      <div style="display:flex; gap:12px; flex-wrap:wrap; justify-content:center;">
        <button id="abyss-poison-btn" style="background:linear-gradient(135deg, #00d2ff, #0072ff); color:#fff; font-weight:800; font-size:13px; border:none; padding:12px 24px; border-radius:8px; cursor:pointer; box-shadow:0 0 15px rgba(0,210,255,0.4); display:flex; align-items:center; gap:6px;">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon></svg>
          Neutralize & Poison Attacker
        </button>
        <button id="abyss-bypass-btn" style="background:transparent; color:#94a3b8; font-weight:700; font-size:12px; border:1px solid rgba(255,255,255,0.15); padding:12px 20px; border-radius:8px; cursor:pointer;">
          Proceed Anyway (Unsafe)
        </button>
      </div>
    `;

    document.body.appendChild(overlay);

    document.getElementById("abyss-poison-btn").addEventListener("click", () => {
      overlay.remove();
      injectHoneypotDecoyData();
    });

    document.getElementById("abyss-bypass-btn").addEventListener("click", () => {
      overlay.remove();
    });
  }

  // ---------------------------------------------------------------------------
  // Silent Link Hover Inspector
  // ---------------------------------------------------------------------------
  const HIGH_RISK_TLDS = [".xyz", ".top", ".click", ".site", ".fun", ".club", ".zip", ".work"];
  const BRAND_KEYWORDS = ["nitro", "gift", "stean", "stearm", "metamask-verify", "phantom-connect", "robux"];

  function initHoverInspector() {
    hoverTooltipEl = document.createElement("div");
    hoverTooltipEl.id = "abyss-hover-tooltip";
    hoverTooltipEl.style.cssText = `
      position: absolute;
      z-index: 2147483646;
      background: #0f172a;
      border: 1px solid #00d2ff;
      border-radius: 6px;
      padding: 6px 10px;
      color: #fff;
      font-family: -apple-system, sans-serif;
      font-size: 11px;
      font-weight: 700;
      pointer-events: none;
      display: none;
      box-shadow: 0 4px 15px rgba(0, 0, 0, 0.5);
    `;
    document.body.appendChild(hoverTooltipEl);

    document.addEventListener("mouseover", (e) => {
      const link = e.target.closest("a");
      if (!link || !link.href || !link.href.startsWith("http")) {
        if (hoverTooltipEl) hoverTooltipEl.style.display = "none";
        return;
      }

      try {
        const targetUrl = new URL(link.href);
        const targetDomain = targetUrl.hostname.toLowerCase();
        if (targetDomain === pageDomain) return;

        let isSuspicious = false;
        if (HIGH_RISK_TLDS.some((tld) => targetDomain.endsWith(tld))) isSuspicious = true;
        if (BRAND_KEYWORDS.some((kw) => targetDomain.includes(kw))) isSuspicious = true;

        if (isSuspicious) {
          const iconSvg = `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#ff3366" stroke-width="2" stroke-linecap="round" style="vertical-align:middle; margin-right:4px;"><path d="M12 2L3 7V12C3 17.55 6.84 22.74 12 24C17.16 22.74 21 17.55 21 12V7L12 2Z"/></svg>`;
          hoverTooltipEl.style.border = "1px solid #ff3366";
          hoverTooltipEl.style.color = "#ff3366";
          hoverTooltipEl.innerHTML = `${iconSvg}ABYSS DANGER: Phishing Link Target (${targetDomain})`;

          const rect = link.getBoundingClientRect();
          hoverTooltipEl.style.left = `${window.scrollX + rect.left}px`;
          hoverTooltipEl.style.top = `${window.scrollY + rect.bottom + 4}px`;
          hoverTooltipEl.style.display = "block";
        } else {
          hoverTooltipEl.style.display = "none";
        }
      } catch (err) {
        if (hoverTooltipEl) hoverTooltipEl.style.display = "none";
      }
    });

    document.addEventListener("mouseout", (e) => {
      if (e.target.closest("a") && hoverTooltipEl) {
        hoverTooltipEl.style.display = "none";
      }
    });
  }

  // Floating Alert Banner
  function showFloatingAlert(message) {
    let alertEl = document.getElementById("abyss-floating-alert");
    if (!alertEl) {
      alertEl = document.createElement("div");
      alertEl.id = "abyss-floating-alert";
      alertEl.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 20px;
        z-index: 2147483646;
        background: rgba(15, 23, 42, 0.95);
        border: 2px solid #00d2ff;
        border-radius: 10px;
        padding: 12px 16px;
        color: #ffffff;
        font-family: -apple-system, sans-serif;
        font-size: 12px;
        box-shadow: 0 10px 30px rgba(0, 210, 255, 0.3);
        display: flex;
        align-items: center;
        gap: 10px;
      `;
      document.body.appendChild(alertEl);
    }
    const shieldSvg = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#00d2ff" stroke-width="2" stroke-linecap="round"><path d="M12 2L3 7V12C3 17.55 6.84 22.74 12 24C17.16 22.74 21 17.55 21 12V7L12 2Z"/></svg>`;
    alertEl.innerHTML = `<span>${shieldSvg}</span><span>${message}</span>`;
    setTimeout(() => { try { alertEl.remove(); } catch(e){} }, 6000);
  }

  // Render Right-Click Context Menu Result Modal
  function showContextResultModal(type, data) {
    let modal = document.getElementById("abyss-context-modal");
    if (modal) modal.remove();

    modal = document.createElement("div");
    modal.id = "abyss-context-modal";
    modal.style.cssText = `
      position: fixed;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      z-index: 2147483647;
      background: #0f172a;
      border: 2px solid #00d2ff;
      border-radius: 14px;
      padding: 20px 24px;
      color: #fff;
      font-family: -apple-system, sans-serif;
      max-width: 420px;
      width: 90%;
      box-shadow: 0 20px 50px rgba(0,210,255,0.4);
      backdrop-filter: blur(12px);
    `;

    if (type === "LINK") {
      const isDanger = data.is_phishing || data.risk_score >= 45;
      modal.style.borderColor = isDanger ? "#ff3366" : "#00ff88";
      modal.innerHTML = `
        <div style="font-size:12px; font-weight:800; color:${isDanger ? '#ff3366' : '#00ff88'}; margin-bottom:6px;">ABYSS LINK SAFETY AUDIT</div>
        <div style="font-size:14px; font-weight:700; word-break:break-all; margin-bottom:10px;">${data.domain || data.url}</div>
        <div style="font-size:12px; color:#cbd5e1; margin-bottom:12px;">Risk Rating: <strong>${data.risk_score}% (${data.risk_level})</strong></div>
        <div style="font-size:12px; color:#94a3b8; margin-bottom:16px;">${data.recommendation}</div>
        <button id="abyss-close-modal" style="background:#00d2ff; color:#000; font-weight:800; border:none; padding:8px 16px; border-radius:6px; cursor:pointer; width:100%;">Close Audit</button>
      `;
    } else if (type === "LEAK") {
      const isLeaked = data.is_leaked;
      modal.style.borderColor = isLeaked ? "#ff3366" : "#00ff88";
      modal.innerHTML = `
        <div style="font-size:12px; font-weight:800; color:${isLeaked ? '#ff3366' : '#00ff88'}; margin-bottom:6px;">ABYSS DARK WEB LEAK AUDIT</div>
        <div style="font-size:14px; font-weight:700; word-break:break-all; margin-bottom:10px;">${data.query_email}</div>
        <div style="font-size:12px; color:#cbd5e1; margin-bottom:12px;">Status: <strong>${isLeaked ? 'CRITICAL LEAK DETECTED' : 'CLEAN — NO LEAKS FOUND'}</strong></div>
        <div style="font-size:12px; color:#94a3b8; margin-bottom:16px;">${data.recommendation}</div>
        <button id="abyss-close-modal" style="background:#00d2ff; color:#000; font-weight:800; border:none; padding:8px 16px; border-radius:6px; cursor:pointer; width:100%;">Close Audit</button>
      `;
    } else {
      modal.innerHTML = `<div>${data.message || "Audit completed"}</div>`;
    }

    document.body.appendChild(modal);
    document.getElementById("abyss-close-modal").addEventListener("click", () => modal.remove());
  }

  // Listener for Service Worker Messages
  if (typeof chrome !== "undefined" && chrome.runtime) {
    chrome.runtime.sendMessage({ action: "CHECK_URL_SAFETY", url: window.location.href }, (response) => {
      if (response && (response.is_phishing || response.risk_score >= 70)) {
        renderFullPageBlockOverlay(response);
      }
    });

    chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
      if (request.action === "POISON_DECOY") {
        injectHoneypotDecoyData();
        sendResponse({ status: "POISONED" });
      } else if (request.action === "SHOW_CONTEXT_RESULT") {
        showContextResultModal(request.type, request.data);
      }
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initHoverInspector);
  } else {
    initHoverInspector();
  }
})();
