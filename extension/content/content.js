// ABYSS Cyber Sentinel Content Script — Page Phishing & Credential Guard

(function () {
  const pageDomain = window.location.hostname.toLowerCase();
  
  // 1. Monitor Input Fields for Crypto Seed Phrase Stealing
  document.addEventListener("input", (e) => {
    const target = e.target;
    if (target && (target.tagName === "INPUT" || target.tagName === "TEXTAREA")) {
      const val = target.value.trim();
      const words = val.split(/\s+/);
      
      // If user is typing a 12 or 24 word mnemonic seed phrase
      if ((words.length === 12 || words.length === 24) && val.length > 50) {
        // Check if page domain is NOT official metamask / wallet
        if (!pageDomain.includes("metamask.io") && !pageDomain.includes("phantom.app") && !pageDomain.includes("localhost")) {
          showAbyssWarningBanner("CRITICAL SECURITY WARNING: Potential Crypto Seed Phrase Theft Detected on this Site!");
        }
      }
    }
  });

  // 2. Inject ABYSS Floating Shield Warning for Phishing Sites
  function showAbyssWarningBanner(message) {
    if (document.getElementById("abyss-threat-banner")) return;

    const banner = document.createElement("div");
    banner.id = "abyss-threat-banner";
    banner.style.cssText = `
      position: fixed;
      bottom: 20px;
      right: 20px;
      z-index: 999999;
      background: rgba(15, 23, 42, 0.95);
      border: 2px solid #ff3366;
      border-radius: 12px;
      padding: 14px 18px;
      color: #ffffff;
      font-family: -apple-system, sans-serif;
      font-size: 13px;
      box-shadow: 0 10px 30px rgba(255, 51, 102, 0.4);
      display: flex;
      align-items: center;
      gap: 12px;
      backdrop-filter: blur(10px);
    `;

    banner.innerHTML = `
      <span style="font-size:24px;">🛡️</span>
      <div>
        <div style="font-weight:bold; color:#ff3366; font-size:12px; letter-spacing:0.5px;">ABYSS THREAT SENTINEL</div>
        <div style="font-size:11px; margin-top:2px;">${message}</div>
      </div>
      <button id="abyss-close-btn" style="background:transparent; border:none; color:#94a3b8; cursor:pointer; font-size:16px; margin-left:8px;">✕</button>
    `;

    document.body.appendChild(banner);
    document.getElementById("abyss-close-btn").addEventListener("click", () => {
      banner.remove();
    });
  }

  // Send page URL to background worker for silent risk assessment
  if (typeof chrome !== "undefined" && chrome.runtime) {
    chrome.runtime.sendMessage({ action: "CHECK_URL_SAFETY", url: window.location.href }, (response) => {
      if (response && response.is_phishing) {
        showAbyssWarningBanner(`WARNING: ${response.threat_type || 'Phishing Attack Detected'}`);
      }
    });
  }
})();
