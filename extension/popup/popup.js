const API_URL = "http://localhost:8000/url-scan";
const FALLBACK_API = "https://abyss-1-d265.onrender.com/url-scan";

document.addEventListener("DOMContentLoaded", async () => {
  const domainEl = document.getElementById("domain-name");
  const riskScoreEl = document.getElementById("risk-score");
  const progressFillEl = document.getElementById("progress-bar-fill");
  const riskTagEl = document.getElementById("risk-level-tag");
  const statusBadgeEl = document.getElementById("status-badge");
  const sslStatusEl = document.getElementById("ssl-status");
  const phishingStatusEl = document.getElementById("phishing-status");
  const reasonsBoxEl = document.getElementById("reasons-box");
  const reasonsListEl = document.getElementById("reasons-list");
  const scanBtn = document.getElementById("scan-btn");

  async function getCurrentTabUrl() {
    return new Promise((resolve) => {
      if (typeof chrome !== "undefined" && chrome.tabs) {
        chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
          if (tabs && tabs[0]) {
            resolve(tabs[0].url);
          } else {
            resolve(window.location.href);
          }
        });
      } else {
        resolve(window.location.href);
      }
    });
  }

  async function performScan() {
    const currentUrl = await getCurrentTabUrl();
    if (!currentUrl) {
      domainEl.textContent = "Unknown Tab";
      return;
    }

    try {
      const urlObj = new URL(currentUrl);
      domainEl.textContent = urlObj.hostname;
    } catch {
      domainEl.textContent = currentUrl;
    }

    domainEl.textContent += " (scanning...)";

    try {
      let response;
      try {
        response = await fetch(`${API_URL}?url=${encodeURIComponent(currentUrl)}`);
      } catch {
        response = await fetch(`${FALLBACK_API}?url=${encodeURIComponent(currentUrl)}`);
      }

      const data = await response.json();
      updateUI(data);
    } catch (err) {
      domainEl.textContent = "Offline Scan Mode";
      riskScoreEl.textContent = "0%";
      progressFillEl.style.width = "0%";
    }
  }

  function updateUI(data) {
    const score = data.risk_score || 0;
    const level = data.risk_level || "CLEAN";
    const domain = data.domain || "Unknown";

    domainEl.textContent = domain;
    riskScoreEl.textContent = `${score}%`;
    progressFillEl.style.width = `${score}%`;

    // SSL Status
    if (data.is_https) {
      sslStatusEl.textContent = data.ssl_valid ? "VERIFIED HTTPS" : "INVALID CERT";
      sslStatusEl.className = data.ssl_valid ? "status-value green" : "status-value red";
    } else {
      sslStatusEl.textContent = "UNENCRYPTED HTTP";
      sslStatusEl.className = "status-value red";
    }

    // Phishing Status & Tags
    if (data.is_phishing || score >= 45) {
      statusBadgeEl.textContent = "THREAT BLOCKED";
      statusBadgeEl.className = "badge badge-threat";

      riskTagEl.textContent = `CRITICAL PHISHING RISK (${level})`;
      riskTagEl.className = "risk-tag tag-critical";

      phishingStatusEl.textContent = data.threat_type || "SUSPICIOUS SITE";
      phishingStatusEl.className = "status-value red";

      // Show reasons
      if (data.threat_reasons && data.threat_reasons.length > 0) {
        reasonsListEl.innerHTML = "";
        data.threat_reasons.forEach((reason) => {
          const li = document.createElement("li");
          li.textContent = reason;
          reasonsListEl.appendChild(li);
        });
        reasonsBoxEl.classList.remove("hidden");
      }
    } else {
      statusBadgeEl.textContent = "PROTECTED";
      statusBadgeEl.className = "badge badge-clean";

      riskTagEl.textContent = "SAFE & SECURE WEBSITE";
      riskTagEl.className = "risk-tag tag-clean";

      phishingStatusEl.textContent = "NO PHISHING DETECTED";
      phishingStatusEl.className = "status-value green";

      reasonsBoxEl.classList.add("hidden");
    }
  }

  scanBtn.addEventListener("click", performScan);
  performScan();
});
