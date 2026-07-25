// ============================================================================
//  ABYSS CYBER SENTINEL — Content Script v1.2.6
//  Features:
//    1. Email/Sender Hover Safety Inspector (Gmail, Outlook, any webmail)
//    2. Silent Link Phishing Inspector
//    3. Anti-Cookie & Session Token Storage Guard
//    4. Attacker Poisoning & Decoy Injection
//    5. Full-Page Threat Intercept Overlay
//    6. Clipboard Crypto Address Swap Guard
//    7. Webhook Exfiltration Tracker
//    8. Right-Click Context Menu Result Modal
// ============================================================================

(function () {
  "use strict";

  const pageDomain = window.location.hostname.toLowerCase();

  // ─── CONSTANTS ───────────────────────────────────────────────────────────────
  const HIGH_RISK_TLDS = [".xyz", ".top", ".click", ".site", ".fun", ".club", ".zip", ".work", ".tk", ".ml"];
  const BRAND_KEYWORDS = ["nitro", "gift", "stean", "stearm", "metamask-verify", "phantom-connect", "robux", "dlscord", "paypa1", "microsft", "rbl0x"];
  const DISPOSABLE_DOMAINS = ["tempmail", "guerrillamail", "10minutemail", "mailinator", "trashmail", "dispostable", "getairmail", "fakeinbox", "throwawaymail", "yopmail"];

  // ─── ANTI-COOKIE STORAGE GUARD ───────────────────────────────────────────────
  try {
    const guard = document.createElement("script");
    guard.textContent = `(function(){
      const sensitive = ["token","discord","roblosecurity","session","auth","metamask","seed","private_key","jwt"];
      const official = ["discord.com","discordapp.com","roblox.com","google.com","github.com","metamask.io"];
      const host = location.hostname.toLowerCase();
      if (!official.some(h => host.includes(h))) {
        const orig = Storage.prototype.getItem;
        Storage.prototype.getItem = function(k) {
          if (k && sensitive.some(s => k.toLowerCase().includes(s))) return null;
          return orig.apply(this, arguments);
        };
      }
    })();`;
    (document.head || document.documentElement).appendChild(guard);
    guard.remove();
  } catch (e) {}

  // ─── WEBHOOK EXFILTRATION TRACKER ────────────────────────────────────────────
  try {
    const origFetch = window.fetch;
    window.fetch = async function (...args) {
      const url = typeof args[0] === "string" ? args[0] : (args[0] && args[0].url) || "";
      if (url.includes("discord.com/api/webhooks") || url.includes("discordapp.com/api/webhooks")) {
        if (!pageDomain.includes("discord.com") && !pageDomain.includes("discordapp.com")) {
          showAlert("CRITICAL: Blocked unauthorized Discord Webhook data exfiltration!");
          return Promise.reject(new Error("ABYSS blocked webhook exfiltration"));
        }
      }
      return origFetch.apply(this, args);
    };
  } catch (e) {}

  // ─── CLIPBOARD CRYPTO ADDRESS SWAP GUARD ─────────────────────────────────────
  try {
    const CRYPTO_REGEX = /^(0x[a-fA-F0-9]{40}|[13][a-km-zA-HJ-NP-Z1-9]{25,34}|[A-Za-z0-9]{32,44})$/;
    let copiedAddress = "";
    document.addEventListener("copy", () => {
      setTimeout(() => {
        navigator.clipboard.readText().then(text => { if (CRYPTO_REGEX.test(text.trim())) copiedAddress = text.trim(); }).catch(() => {});
      }, 100);
    });
    document.addEventListener("paste", (e) => {
      const pasted = (e.clipboardData || window.clipboardData).getData("text");
      if (copiedAddress && CRYPTO_REGEX.test(pasted.trim()) && pasted.trim() !== copiedAddress) {
        e.preventDefault();
        showAlert("CLIPBOARD GUARD: Crypto address swap detected! Paste blocked.");
      }
    });
  } catch (e) {}

  // ─── EMAIL SAFETY ANALYZER ───────────────────────────────────────────────────
  function analyzeEmail(email) {
    if (!email || !email.includes("@")) return null;
    const [, domain] = email.toLowerCase().split("@");
    if (!domain) return null;

    let score = 100;
    const reasons = [];

    if (DISPOSABLE_DOMAINS.some(d => domain.includes(d))) { score -= 70; reasons.push("Disposable/Temporary Domain"); }
    if (BRAND_KEYWORDS.some(k => domain.includes(k)))     { score -= 65; reasons.push("Brand Spoof/Typosquat"); }
    if (HIGH_RISK_TLDS.some(t => domain.endsWith(t)))     { score -= 30; reasons.push("High-Risk Phishing TLD"); }

    score = Math.max(5, score);
    return {
      email: email.toLowerCase(),
      domain,
      score,
      safe: score >= 70,
      reason: reasons.length ? reasons.join(", ") : "Standard Verified Domain"
    };
  }

  // ─── TOOLTIP ─────────────────────────────────────────────────────────────────
  let tooltip = null;

  function getTooltip() {
    if (tooltip && document.body && document.body.contains(tooltip)) return tooltip;
    tooltip = document.getElementById("__abyss_tip__");
    if (!tooltip) {
      tooltip = document.createElement("div");
      tooltip.id = "__abyss_tip__";
      tooltip.style.cssText = [
        "position:fixed",
        "z-index:2147483647",
        "background:#0f172a",
        "border:1px solid #00d2ff",
        "border-radius:8px",
        "padding:8px 12px",
        "color:#fff",
        "font:700 11px/-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif",
        "pointer-events:none",
        "display:none",
        "box-shadow:0 8px 24px rgba(0,0,0,.7)",
        "max-width:260px",
        "line-height:1.5"
      ].join(";");
    }
    if (document.body) document.body.appendChild(tooltip);
    return tooltip;
  }

  function showTip(html, borderColor, textColor, x, y) {
    const t = getTooltip();
    t.style.border = `1px solid ${borderColor}`;
    t.style.color = textColor;
    t.innerHTML = html;
    t.style.left = Math.min(window.innerWidth  - 270, Math.max(8, x + 14)) + "px";
    t.style.top  = Math.min(window.innerHeight - 90,  Math.max(8, y + 18)) + "px";
    t.style.display = "block";
  }

  function hideTip() {
    const t = document.getElementById("__abyss_tip__");
    if (t) t.style.display = "none";
  }

  // ─── SVG ICONS ───────────────────────────────────────────────────────────────
  const SHIELD_GREEN = `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#00ff88" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;margin-right:5px"><path d="M12 2L3 7v5c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V7z"/><polyline points="9 12 11 14 15 10"/></svg>`;
  const SHIELD_RED   = `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#ff3366" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;margin-right:5px"><path d="M12 2L3 7v5c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V7z"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>`;
  const SHIELD_BLUE  = `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#00d2ff" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;margin-right:5px"><path d="M12 2L3 7v5c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V7z"/><polyline points="9 12 11 14 15 10"/></svg>`;

  function emailTipHTML(r) {
    const icon  = r.safe ? SHIELD_GREEN : SHIELD_RED;
    const color = r.safe ? "#00ff88" : "#ff3366";
    const label = r.safe ? `EMAIL VERIFIED — ${r.score}% SAFE` : `UNSAFE EMAIL — ${r.score}% SAFETY`;
    return `<div style="display:flex;align-items:center;margin-bottom:3px">${icon}<span style="color:${color};font-size:11px;font-weight:800">${label}</span></div><div style="color:#e2e8f0;font-size:11px">${r.email}</div><div style="color:#94a3b8;font-size:10px;margin-top:2px">${r.reason}</div>`;
  }

  // ─── HOVER INSPECTOR ─────────────────────────────────────────────────────────
  function initHoverInspector() {
    let lastEmail = "";
    let lastX = 0, lastY = 0;

    document.addEventListener("mousemove", (e) => {
      lastX = e.clientX; lastY = e.clientY;
    }, { passive: true });

    document.addEventListener("mouseover", (e) => {
      const el = e.target;
      if (!el || el.nodeType !== 1) return;

      // ── 1. Extract email ─────────────────────────────────────────────────────
      let email = "";

      // Step A: Find the nearest Gmail inbox row container
      const row = el.closest(".zA") || el.closest("[role='row']") || el.closest("tr");

      // Step B: Search INSIDE the row for any element with an email attribute
      // (Gmail stores sender email on <span email="sender@domain.com"> which is
      //  a sibling/child of where you hover, NOT a parent — so we must querySelector)
      if (row) {
        const emailEl = row.querySelector("[email]") || row.querySelector("[data-hovercard-id]");
        if (emailEl) {
          const attr = emailEl.getAttribute("email") || emailEl.getAttribute("data-hovercard-id") || "";
          if (attr.includes("@")) email = attr;
        }
      }

      // Step C: mailto: link
      if (!email) {
        const a = el.closest("a[href^='mailto:']");
        if (a) email = a.href.replace("mailto:", "").split("?")[0];
      }

      // Step D: Text content of this element only (not subtree to avoid noise)
      if (!email) {
        const txt = (el.innerText || el.textContent || "").trim();
        if (txt.length < 200) {
          const m = txt.match(/[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/);
          if (m) email = m[0];
        }
      }

      // ── 2. Show tooltip if we have an email ──────────────────────────────────
      if (email && email !== lastEmail) {
        lastEmail = email;
        const r = analyzeEmail(email);
        if (r) {
          showTip(emailTipHTML(r), r.safe ? "#00ff88" : "#ff3366", r.safe ? "#00ff88" : "#ff3366", lastX, lastY);
          return;
        }
      } else if (email && email === lastEmail) {
        // Already showing for this email — just update position
        const t = document.getElementById("__abyss_tip__");
        if (t && t.style.display === "block") {
          t.style.left = Math.min(window.innerWidth  - 270, Math.max(8, lastX + 14)) + "px";
          t.style.top  = Math.min(window.innerHeight - 90,  Math.max(8, lastY + 18)) + "px";
          return;
        }
      }

      // ── 3. No email — check for phishing link ────────────────────────────────
      if (!email) {
        lastEmail = "";
        const a = el.closest("a[href^='http']");
        if (a) {
          try {
            const domain = new URL(a.href).hostname.toLowerCase();
            if (domain !== pageDomain) {
              const phish = HIGH_RISK_TLDS.some(t => domain.endsWith(t)) || BRAND_KEYWORDS.some(k => domain.includes(k));
              if (phish) {
                const icon = `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#ff3366" stroke-width="2.5" stroke-linecap="round" style="vertical-align:middle;margin-right:4px"><path d="M12 2L3 7v5c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V7z"/></svg>`;
                showTip(`${icon}<span style="font-size:11px;font-weight:800">PHISHING LINK: ${domain}</span>`, "#ff3366", "#ff3366", lastX, lastY);
                return;
              }
            }
          } catch (_) {}
        }
        hideTip();
      }
    });

    document.addEventListener("mouseout", (e) => {
      if (!e.relatedTarget || e.relatedTarget.id === "__abyss_tip__") return;
      lastEmail = "";
      hideTip();
    });
  }

  // ─── ATTACKER POISONING ───────────────────────────────────────────────────────
  function injectDecoy() {
    const fake = { seed: "abandon amount abandon amount abandon art", token: "mfa.abyss_decoy_honeypot_token_99218492038", pass: "Pwned_Abyss_Fake!999", email: "decoy@honeypot.abyss.net" };
    let count = 0;
    document.querySelectorAll("input,textarea").forEach(inp => {
      if (["hidden","submit","button"].includes(inp.type)) return;
      const ctx = (inp.placeholder + inp.name + inp.id).toLowerCase();
      inp.value = ctx.includes("seed") || ctx.includes("phrase") ? fake.seed : ctx.includes("token") ? fake.token : inp.type === "email" || ctx.includes("email") ? fake.email : fake.pass;
      inp.dispatchEvent(new Event("input", { bubbles: true }));
      inp.style.border = "2px solid #00d2ff";
      count++;
    });
    showAlert(`ATTACKER POISONED: Injected decoy honeypot data into ${count} fields!`);
    const form = document.querySelector("form");
    if (form) setTimeout(() => { try { form.submit(); } catch (_) {} }, 500);
  }

  // ─── FULL-PAGE THREAT OVERLAY ─────────────────────────────────────────────────
  function renderBlockOverlay(data) {
    if (document.getElementById("__abyss_overlay__")) return;
    const reasons = (data.threat_reasons || []).map(r =>
      `<li style="display:flex;align-items:center;gap:6px;margin-bottom:5px"><svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="#ffaa00" stroke-width="2.5" stroke-linecap="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>${r}</li>`
    ).join("");

    const div = document.createElement("div");
    div.id = "__abyss_overlay__";
    div.style.cssText = "position:fixed;inset:0;z-index:2147483647;background:radial-gradient(circle at center,#1e0914,#050306);display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:24px;font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif;color:#fff";
    div.innerHTML = `
      <div style="margin-bottom:14px;filter:drop-shadow(0 0 20px #ff3366)">
        <svg width="60" height="60" viewBox="0 0 24 24" fill="none" stroke="#ff3366" stroke-width="1.5" stroke-linecap="round"><path d="M12 2L3 7v5c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V7z"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
      </div>
      <div style="font-size:11px;font-weight:800;color:#ff3366;letter-spacing:2px;margin-bottom:8px">ABYSS CYBER SENTINEL — THREAT INTERCEPTED</div>
      <h1 style="font-size:26px;font-weight:900;margin:0 0 12px;color:#fff">PHISHING SITE BLOCKED</h1>
      <p style="font-size:13px;color:#94a3b8;max-width:520px;line-height:1.7;margin-bottom:20px">
        <strong>${pageDomain}</strong> was flagged as a high-risk phishing website targeting your credentials or crypto assets.
      </p>
      ${reasons ? `<ul style="background:rgba(255,255,255,.04);border:1px solid rgba(255,51,102,.3);border-radius:10px;padding:14px 20px;max-width:480px;text-align:left;font-size:12px;color:#cbd5e1;list-style:none;margin-bottom:22px">${reasons}</ul>` : ""}
      <div style="display:flex;gap:12px;flex-wrap:wrap;justify-content:center">
        <button id="__abyss_poison__" style="background:linear-gradient(135deg,#00d2ff,#0072ff);color:#fff;font-weight:800;font-size:13px;border:none;padding:12px 22px;border-radius:8px;cursor:pointer">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" style="vertical-align:middle;margin-right:5px"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>Neutralize & Poison Attacker
        </button>
        <button id="__abyss_bypass__" style="background:transparent;color:#94a3b8;font-weight:700;font-size:12px;border:1px solid rgba(255,255,255,.15);padding:12px 18px;border-radius:8px;cursor:pointer">
          Proceed Anyway (Unsafe)
        </button>
      </div>`;
    document.body.appendChild(div);
    document.getElementById("__abyss_poison__").onclick = () => { div.remove(); injectDecoy(); };
    document.getElementById("__abyss_bypass__").onclick = () => div.remove();
  }

  // ─── FLOATING ALERT BANNER ────────────────────────────────────────────────────
  function showAlert(msg) {
    let el = document.getElementById("__abyss_alert__");
    if (!el) {
      el = document.createElement("div");
      el.id = "__abyss_alert__";
      el.style.cssText = "position:fixed;bottom:20px;right:20px;z-index:2147483646;background:rgba(15,23,42,.97);border:2px solid #00d2ff;border-radius:10px;padding:12px 16px;color:#fff;font-family:-apple-system,sans-serif;font-size:12px;box-shadow:0 10px 30px rgba(0,210,255,.3);display:flex;align-items:center;gap:10px;max-width:340px";
      document.body && document.body.appendChild(el);
    }
    el.innerHTML = `${SHIELD_BLUE}<span>${msg}</span>`;
    clearTimeout(el._t);
    el._t = setTimeout(() => el.remove(), 6000);
  }

  // ─── CONTEXT MENU RESULT MODAL ────────────────────────────────────────────────
  function showModal(type, data) {
    document.getElementById("__abyss_modal__")?.remove();
    const modal = document.createElement("div");
    modal.id = "__abyss_modal__";
    modal.style.cssText = "position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);z-index:2147483647;background:#0f172a;border:2px solid #00d2ff;border-radius:14px;padding:20px 24px;color:#fff;font-family:-apple-system,sans-serif;max-width:420px;width:90%;box-shadow:0 20px 50px rgba(0,210,255,.4)";

    if (type === "LINK") {
      const danger = data.is_phishing || data.risk_score >= 45;
      modal.style.borderColor = danger ? "#ff3366" : "#00ff88";
      modal.innerHTML = `<div style="font-size:12px;font-weight:800;color:${danger ? "#ff3366" : "#00ff88"};margin-bottom:6px">ABYSS LINK SAFETY AUDIT</div><div style="font-size:14px;font-weight:700;word-break:break-all;margin-bottom:10px">${data.domain || data.url}</div><div style="font-size:12px;color:#cbd5e1;margin-bottom:12px">Risk: <strong>${data.risk_score}% (${data.risk_level})</strong></div><div style="font-size:12px;color:#94a3b8;margin-bottom:16px">${data.recommendation}</div><button id="__abyss_close__" style="background:#00d2ff;color:#000;font-weight:800;border:none;padding:8px 16px;border-radius:6px;cursor:pointer;width:100%">Close</button>`;
    } else if (type === "LEAK") {
      modal.style.borderColor = data.is_leaked ? "#ff3366" : "#00ff88";
      modal.innerHTML = `<div style="font-size:12px;font-weight:800;color:${data.is_leaked ? "#ff3366" : "#00ff88"};margin-bottom:6px">ABYSS DARK WEB LEAK AUDIT</div><div style="font-size:14px;font-weight:700;margin-bottom:10px">${data.query_email}</div><div style="font-size:12px;color:#cbd5e1;margin-bottom:12px">${data.is_leaked ? "CRITICAL LEAK DETECTED" : "CLEAN — NO LEAKS FOUND"}</div><div style="font-size:12px;color:#94a3b8;margin-bottom:16px">${data.recommendation}</div><button id="__abyss_close__" style="background:#00d2ff;color:#000;font-weight:800;border:none;padding:8px 16px;border-radius:6px;cursor:pointer;width:100%">Close</button>`;
    } else {
      modal.innerHTML = `<div>${data.message || "Scan complete."}</div><button id="__abyss_close__" style="background:#00d2ff;color:#000;font-weight:800;border:none;padding:8px 16px;border-radius:6px;cursor:pointer;width:100%;margin-top:12px">Close</button>`;
    }

    document.body.appendChild(modal);
    document.getElementById("__abyss_close__").onclick = () => modal.remove();
  }

  // ─── RUNTIME MESSAGES ────────────────────────────────────────────────────────
  if (typeof chrome !== "undefined" && chrome.runtime) {
    chrome.runtime.sendMessage({ action: "CHECK_URL_SAFETY", url: window.location.href }, (resp) => {
      if (resp && (resp.is_phishing || resp.risk_score >= 70)) renderBlockOverlay(resp);
    });

    chrome.runtime.onMessage.addListener((req, _sender, sendResp) => {
      if (req.action === "POISON_DECOY") { injectDecoy(); sendResp({ status: "POISONED" }); }
      else if (req.action === "SHOW_CONTEXT_RESULT") showModal(req.type, req.data);
    });
  }

  // ─── BOOT ────────────────────────────────────────────────────────────────────
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initHoverInspector);
  } else {
    initHoverInspector();
  }

})();
