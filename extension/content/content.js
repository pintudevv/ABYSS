// ============================================================================
//  ABYSS CYBER SENTINEL — Content Script v1.2.7
//  Features:
//    1. Email Hover Safety Inspector — Gmail row detection + domain age check
//    2. Phishing Link Detector on hover
//    3. URL Unshortener — reveal bit.ly/tinyurl final destination on hover
//    4. Dangerous Attachment Warning — badges on .exe/.zip/.dmg links
//    5. Attacker Poisoning & Decoy Injection
//    6. Full-Page Threat Intercept Overlay
//    7. Clipboard Crypto Address Swap Guard
//    8. Webhook Exfiltration Blocker
//    9. Right-Click Context Menu Result Modal
// ============================================================================

(function () {
  "use strict";

  const pageDomain = window.location.hostname.toLowerCase();

  // ─── CONSTANTS ───────────────────────────────────────────────────────────────
  const HIGH_RISK_TLDS    = [".xyz", ".top", ".click", ".site", ".fun", ".club", ".zip", ".work", ".tk", ".ml", ".ga", ".cf"];
  const BRAND_KEYWORDS    = ["nitro", "gift", "stean", "stearm", "metamask-verify", "phantom-connect", "robux", "dlscord", "paypa1", "microsft", "rbl0x"];
  const DISPOSABLE_DOMAINS= ["tempmail", "guerrillamail", "10minutemail", "mailinator", "trashmail", "dispostable", "getairmail", "fakeinbox", "throwawaymail", "yopmail"];
  const SHORT_LINK_HOSTS  = ["bit.ly","bitly.com","t.co","tinyurl.com","goo.gl","ow.ly","short.link","rb.gy","cutt.ly","is.gd","buff.ly","tiny.cc","lnkd.in","fb.me","ift.tt","dl.vg"];
  const DANGEROUS_EXTS    = [".exe",".msi",".bat",".cmd",".vbs",".ps1",".sh",".dmg",".pkg",".apk",".jar",".scr",".pif",".com",".lnk",".hta",".rar",".7z"];

  // ─── WEBHOOK EXFILTRATION BLOCKER ────────────────────────────────────────────
  try {
    const origFetch = window.fetch;
    window.fetch = async function (...args) {
      const url = typeof args[0] === "string" ? args[0] : (args[0]?.url) || "";
      if ((url.includes("discord.com/api/webhooks") || url.includes("discordapp.com/api/webhooks")) &&
          !pageDomain.includes("discord.com") && !pageDomain.includes("discordapp.com")) {
        showAlert("CRITICAL: Blocked Discord Webhook data exfiltration!");
        return Promise.reject(new Error("ABYSS blocked webhook exfiltration"));
      }
      return origFetch.apply(this, args);
    };
  } catch (e) {}

  // ─── CLIPBOARD CRYPTO SWAP GUARD ─────────────────────────────────────────────
  try {
    const CRYPTO_RE = /^(0x[a-fA-F0-9]{40}|[13][a-km-zA-HJ-NP-Z1-9]{25,34}|[A-Za-z0-9]{32,44})$/;
    let _copied = "";
    document.addEventListener("copy", () => {
      setTimeout(() => navigator.clipboard.readText().then(t => { if (CRYPTO_RE.test(t.trim())) _copied = t.trim(); }).catch(() => {}), 100);
    });
    document.addEventListener("paste", e => {
      const p = (e.clipboardData || window.clipboardData).getData("text");
      if (_copied && CRYPTO_RE.test(p.trim()) && p.trim() !== _copied) {
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
    return { email: email.toLowerCase(), domain, score, safe: score >= 70, reason: reasons.length ? reasons.join(", ") : "Standard Verified Domain" };
  }

  // ─── TOOLTIP ENGINE ──────────────────────────────────────────────────────────
  let _tip = null;
  function getTip() {
    if (_tip && document.body?.contains(_tip)) return _tip;
    _tip = document.getElementById("__abyss_tip__");
    if (!_tip) {
      _tip = document.createElement("div");
      _tip.id = "__abyss_tip__";
      _tip.style.cssText = "position:fixed;z-index:2147483647;background:#0f172a;border:1px solid #00d2ff;border-radius:8px;padding:8px 12px;color:#fff;font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif;font-size:11px;font-weight:700;pointer-events:none;display:none;box-shadow:0 8px 24px rgba(0,0,0,.8);max-width:280px;line-height:1.6";
    }
    document.body?.appendChild(_tip);
    return _tip;
  }

  function showTip(html, border, x, y) {
    const t = getTip();
    t.style.border = `1px solid ${border}`;
    t.innerHTML = html;
    t.style.left = Math.min(window.innerWidth  - 295, Math.max(8, x + 14)) + "px";
    t.style.top  = Math.min(window.innerHeight - 100, Math.max(8, y + 18)) + "px";
    t.style.display = "block";
  }

  function hideTip() { document.getElementById("__abyss_tip__")?.style && (document.getElementById("__abyss_tip__").style.display = "none"); }
  function moveTip(x, y) {
    const t = document.getElementById("__abyss_tip__");
    if (t && t.style.display === "block") {
      t.style.left = Math.min(window.innerWidth  - 295, Math.max(8, x + 14)) + "px";
      t.style.top  = Math.min(window.innerHeight - 100, Math.max(8, y + 18)) + "px";
    }
  }

  // ─── SVG ICONS ───────────────────────────────────────────────────────────────
  const ICO_SAFE     = `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#00ff88" stroke-width="2.5" stroke-linecap="round" style="vertical-align:middle;margin-right:5px"><path d="M12 2L3 7v5c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V7z"/><polyline points="9 12 11 14 15 10"/></svg>`;
  const ICO_DANGER   = `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#ff3366" stroke-width="2.5" stroke-linecap="round" style="vertical-align:middle;margin-right:5px"><path d="M12 2L3 7v5c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V7z"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>`;
  const ICO_INFO     = `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#00d2ff" stroke-width="2.5" stroke-linecap="round" style="vertical-align:middle;margin-right:5px"><path d="M12 2L3 7v5c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V7z"/><polyline points="9 12 11 14 15 10"/></svg>`;
  const ICO_WARN     = `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#ffaa00" stroke-width="2.5" stroke-linecap="round" style="vertical-align:middle;margin-right:5px"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`;
  const ICO_LINK     = `<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="#00d2ff" stroke-width="2.5" stroke-linecap="round" style="vertical-align:middle;margin-right:5px"><path d="M10 13a5 5 0 007.54.54l3-3a5 5 0 00-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 00-7.54-.54l-3 3a5 5 0 007.07 7.07l1.71-1.71"/></svg>`;

  // ─── TOOLTIP HTML BUILDERS ───────────────────────────────────────────────────
  function emailHTML(r, ageDays, regDate) {
    const icon  = r.safe ? ICO_SAFE : ICO_DANGER;
    const color = r.safe ? "#00ff88" : "#ff3366";
    const label = r.safe ? `VERIFIED — ${r.score}% SAFE` : `SUSPICIOUS — ${r.score}% SAFETY`;

    let ageHtml = "";
    if (ageDays !== null && ageDays !== undefined) {
      if (ageDays < 30) {
        ageHtml = `<div style="margin-top:4px;padding:3px 6px;background:rgba(255,51,102,.15);border-radius:4px;color:#ff3366;font-size:10px">${ICO_DANGER}NEW DOMAIN: ${ageDays}d old — HIGH RISK</div>`;
      } else if (ageDays < 180) {
        ageHtml = `<div style="margin-top:4px;color:#ffaa00;font-size:10px">${ICO_WARN}Domain age: ${ageDays} days (relatively new)</div>`;
      } else {
        ageHtml = `<div style="margin-top:4px;color:#64748b;font-size:10px">Domain registered: ${regDate}</div>`;
      }
    }

    return `<div style="display:flex;align-items:center;margin-bottom:3px">${icon}<span style="color:${color};font-weight:800">${label}</span></div><div style="color:#e2e8f0;font-size:11px">${r.email}</div><div style="color:#94a3b8;font-size:10px;margin-top:2px">${r.reason}</div>${ageHtml}`;
  }

  // ─── DOMAIN AGE CACHE & LOOKUP ───────────────────────────────────────────────
  const _ageCache = {};
  function getDomainAge(domain) {
    return new Promise(resolve => {
      if (_ageCache[domain] !== undefined) { resolve(_ageCache[domain]); return; }
      if (typeof chrome !== "undefined" && chrome.runtime) {
        chrome.runtime.sendMessage({ action: "CHECK_DOMAIN_AGE", domain }, resp => {
          const val = resp || { agedays: null, registered: null };
          _ageCache[domain] = val;
          resolve(val);
        });
      } else { resolve({ agedays: null, registered: null }); }
    });
  }

  // ─── URL UNSHORTEN CACHE & LOOKUP ────────────────────────────────────────────
  const _shortCache = {};
  function unshortenUrl(url) {
    return new Promise(resolve => {
      if (_shortCache[url] !== undefined) { resolve(_shortCache[url]); return; }
      if (typeof chrome !== "undefined" && chrome.runtime) {
        chrome.runtime.sendMessage({ action: "UNSHORTEN_URL", url }, resp => {
          const val = resp?.finalUrl || url;
          _shortCache[url] = val;
          resolve(val);
        });
      } else { resolve(url); }
    });
  }

  // ─── HOVER INSPECTOR ─────────────────────────────────────────────────────────
  function initHoverInspector() {
    let lastKey  = "";  // tracks what's currently showing to avoid duplicate lookups
    let lastX = 0, lastY = 0;

    document.addEventListener("mousemove", e => { lastX = e.clientX; lastY = e.clientY; }, { passive: true });

    document.addEventListener("mouseover", async (e) => {
      const el = e.target;
      if (!el || el.nodeType !== 1) return;

      // ──────────────────────────────────────────────────────────────────────────
      // PRIORITY 1 — EMAIL (Gmail row detection)
      // ──────────────────────────────────────────────────────────────────────────
      let email = "";
      const row = el.closest(".zA") || el.closest("[role='row']") || el.closest("tr");
      if (row) {
        const emailEl = row.querySelector("[email]") || row.querySelector("[data-hovercard-id]");
        if (emailEl) {
          const attr = emailEl.getAttribute("email") || emailEl.getAttribute("data-hovercard-id") || "";
          if (attr.includes("@")) email = attr;
        }
      }
      if (!email) {
        const a = el.closest("a[href^='mailto:']");
        if (a) email = a.href.replace("mailto:", "").split("?")[0];
      }
      if (!email) {
        const txt = (el.innerText || el.textContent || "").trim();
        if (txt.length < 200) { const m = txt.match(/[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/); if (m) email = m[0]; }
      }

      if (email) {
        if (email === lastKey) { moveTip(lastX, lastY); return; }
        lastKey = email;
        const r = analyzeEmail(email);
        if (!r) return;
        // Show instantly with basic info, then enrich with domain age
        showTip(emailHTML(r, null, null), r.safe ? "#00ff88" : "#ff3366", lastX, lastY);
        const { agedays, registered } = await getDomainAge(r.domain);
        if (lastKey === email) showTip(emailHTML(r, agedays, registered), r.safe && agedays >= 30 ? "#00ff88" : "#ff3366", lastX, lastY);
        return;
      }

      // ──────────────────────────────────────────────────────────────────────────
      // PRIORITY 2 — SHORTLINK UNSHORTENER
      // ──────────────────────────────────────────────────────────────────────────
      const anchor = el.closest("a[href^='http'], a[href^='https']");
      if (anchor) {
        try {
          const href   = anchor.href;
          const domain = new URL(href).hostname.replace("www.", "");

          if (SHORT_LINK_HOSTS.includes(domain)) {
            if (href === lastKey) { moveTip(lastX, lastY); return; }
            lastKey = href;
            showTip(`${ICO_LINK}<span style="color:#00d2ff;font-weight:800">SHORTLINK DETECTED</span><div style="color:#94a3b8;font-size:10px;margin-top:3px;word-break:break-all">${href}</div><div style="color:#64748b;font-size:10px;margin-top:2px">Resolving real destination...</div>`, "#00d2ff", lastX, lastY);
            const finalUrl = await unshortenUrl(href);
            if (lastKey !== href) return;
            let finalDomain = finalUrl;
            try { finalDomain = new URL(finalUrl).hostname; } catch (_) {}
            const isRisky = HIGH_RISK_TLDS.some(t => finalDomain.endsWith(t)) || BRAND_KEYWORDS.some(k => finalDomain.includes(k));
            showTip(
              `${isRisky ? ICO_DANGER : ICO_INFO}<span style="color:${isRisky ? "#ff3366" : "#00d2ff"};font-weight:800">SHORTLINK → ${isRisky ? "SUSPICIOUS" : "RESOLVED"}</span>` +
              `<div style="color:#e2e8f0;font-size:10px;margin-top:3px;word-break:break-all">${finalUrl}</div>` +
              (isRisky ? `<div style="color:#ff3366;font-size:10px;margin-top:2px">⚠ Destination looks risky</div>` : ""),
              isRisky ? "#ff3366" : "#00d2ff", lastX, lastY
            );
            return;
          }

          // ──────────────────────────────────────────────────────────────────────
          // PRIORITY 3 — PHISHING LINK DETECTOR
          // ──────────────────────────────────────────────────────────────────────
          if (domain !== pageDomain) {
            const phish = HIGH_RISK_TLDS.some(t => domain.endsWith(t)) || BRAND_KEYWORDS.some(k => domain.includes(k));
            if (phish) {
              if (href === lastKey) { moveTip(lastX, lastY); return; }
              lastKey = href;
              showTip(`${ICO_DANGER}<span style="color:#ff3366;font-weight:800">PHISHING LINK</span><div style="color:#94a3b8;font-size:10px;margin-top:3px;word-break:break-all">${domain}</div>`, "#ff3366", lastX, lastY);
              return;
            }
          }
        } catch (_) {}
      }

      // Nothing matched
      lastKey = "";
      hideTip();
    });

    document.addEventListener("mouseout", e => {
      if (!e.relatedTarget || e.relatedTarget.id === "__abyss_tip__") return;
      lastKey = "";
      hideTip();
    });
  }

  // ─── FEATURE: DANGEROUS ATTACHMENT BADGES ────────────────────────────────────
  function scanAttachmentLinks(root) {
    const links = root.querySelectorAll ? root.querySelectorAll("a[href]") : [];
    links.forEach(a => {
      if (a.dataset.abyssScanned) return;
      a.dataset.abyssScanned = "1";
      try {
        const path = new URL(a.href).pathname.toLowerCase();
        const isDangerous = DANGEROUS_EXTS.some(ext => path.endsWith(ext));
        if (!isDangerous) return;

        // Inject a small warning badge inline next to the link
        const badge = document.createElement("span");
        badge.title = "ABYSS WARNING: Dangerous file type — verify before downloading";
        badge.style.cssText = "display:inline-flex;align-items:center;gap:3px;background:rgba(255,51,102,.15);border:1px solid #ff3366;border-radius:4px;padding:1px 5px;margin-left:5px;font-size:10px;font-weight:800;color:#ff3366;font-family:-apple-system,sans-serif;cursor:help;vertical-align:middle;white-space:nowrap";
        badge.innerHTML = `<svg width="9" height="9" viewBox="0 0 24 24" fill="none" stroke="#ff3366" stroke-width="3" stroke-linecap="round"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>UNSAFE FILE`;
        a.after(badge);
      } catch (_) {}
    });
  }

  function initAttachmentScanner() {
    // Scan existing links
    scanAttachmentLinks(document);

    // Watch for new links added dynamically (SPAs, Gmail lazy loading)
    const obs = new MutationObserver(mutations => {
      for (const m of mutations) {
        for (const node of m.addedNodes) {
          if (node.nodeType === 1) scanAttachmentLinks(node);
        }
      }
    });
    obs.observe(document.body || document.documentElement, { childList: true, subtree: true });
  }

  // ─── ATTACKER DECOY INJECTION ─────────────────────────────────────────────────
  function injectDecoy() {
    const fake = { seed: "abandon amount abandon amount abandon art", token: "mfa.abyss_decoy_honeypot_token_99218492038", pass: "Pwned_Abyss_Fake!999", email: "decoy@honeypot.abyss.net" };
    let count = 0;
    document.querySelectorAll("input,textarea").forEach(inp => {
      if (["hidden", "submit", "button"].includes(inp.type)) return;
      const ctx = (inp.placeholder + inp.name + inp.id).toLowerCase();
      inp.value = ctx.includes("seed") || ctx.includes("phrase") ? fake.seed : ctx.includes("token") ? fake.token : inp.type === "email" || ctx.includes("email") ? fake.email : fake.pass;
      inp.dispatchEvent(new Event("input", { bubbles: true }));
      inp.style.border = "2px solid #00d2ff";
      count++;
    });
    showAlert(`ATTACKER POISONED: Injected decoy into ${count} fields!`);
    const form = document.querySelector("form");
    if (form) setTimeout(() => { try { form.submit(); } catch (_) {} }, 500);
  }

  // ─── FULL-PAGE THREAT OVERLAY ─────────────────────────────────────────────────
  function renderBlockOverlay(data) {
    if (document.getElementById("__abyss_overlay__")) return;
    const reasons = (data.threat_reasons || []).map(r =>
      `<li style="display:flex;align-items:center;gap:6px;margin-bottom:5px">${ICO_WARN}${r}</li>`
    ).join("");
    const div = document.createElement("div");
    div.id = "__abyss_overlay__";
    div.style.cssText = "position:fixed;inset:0;z-index:2147483647;background:radial-gradient(circle at center,#1e0914,#050306);display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:24px;font-family:-apple-system,sans-serif;color:#fff";
    div.innerHTML = `
      <div style="margin-bottom:14px;filter:drop-shadow(0 0 20px #ff3366)"><svg width="60" height="60" viewBox="0 0 24 24" fill="none" stroke="#ff3366" stroke-width="1.5" stroke-linecap="round"><path d="M12 2L3 7v5c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V7z"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg></div>
      <div style="font-size:11px;font-weight:800;color:#ff3366;letter-spacing:2px;margin-bottom:8px">ABYSS CYBER SENTINEL — THREAT INTERCEPTED</div>
      <h1 style="font-size:26px;font-weight:900;margin:0 0 12px">PHISHING SITE BLOCKED</h1>
      <p style="font-size:13px;color:#94a3b8;max-width:520px;line-height:1.7;margin-bottom:20px"><strong>${pageDomain}</strong> was flagged as a high-risk phishing site.</p>
      ${reasons ? `<ul style="background:rgba(255,255,255,.04);border:1px solid rgba(255,51,102,.3);border-radius:10px;padding:14px 20px;max-width:480px;text-align:left;font-size:12px;color:#cbd5e1;list-style:none;margin-bottom:22px">${reasons}</ul>` : ""}
      <div style="display:flex;gap:12px;flex-wrap:wrap;justify-content:center">
        <button id="__abyss_poison__" style="background:linear-gradient(135deg,#00d2ff,#0072ff);color:#fff;font-weight:800;font-size:13px;border:none;padding:12px 22px;border-radius:8px;cursor:pointer">Neutralize &amp; Poison Attacker</button>
        <button id="__abyss_bypass__" style="background:transparent;color:#94a3b8;font-weight:700;font-size:12px;border:1px solid rgba(255,255,255,.15);padding:12px 18px;border-radius:8px;cursor:pointer">Proceed Anyway (Unsafe)</button>
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
      el.style.cssText = "position:fixed;bottom:20px;right:20px;z-index:2147483646;background:rgba(15,23,42,.97);border:2px solid #00d2ff;border-radius:10px;padding:12px 16px;color:#fff;font-family:-apple-system,sans-serif;font-size:12px;font-weight:700;box-shadow:0 10px 30px rgba(0,210,255,.3);display:flex;align-items:center;gap:10px;max-width:340px";
      document.body?.appendChild(el);
    }
    el.innerHTML = `${ICO_INFO}<span>${msg}</span>`;
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
      modal.innerHTML = `<div style="font-size:13px;margin-bottom:12px">${data.message || "Scan complete."}</div><button id="__abyss_close__" style="background:#00d2ff;color:#000;font-weight:800;border:none;padding:8px 16px;border-radius:6px;cursor:pointer;width:100%">Close</button>`;
    }
    document.body.appendChild(modal);
    document.getElementById("__abyss_close__").onclick = () => modal.remove();
  }

  // ─── RUNTIME MESSAGES ────────────────────────────────────────────────────────
  if (typeof chrome !== "undefined" && chrome.runtime) {
    chrome.runtime.sendMessage({ action: "CHECK_URL_SAFETY", url: window.location.href }, resp => {
      if (resp && (resp.is_phishing || resp.risk_score >= 70)) renderBlockOverlay(resp);
    });
    chrome.runtime.onMessage.addListener((req, _sender, sendResp) => {
      if (req.action === "POISON_DECOY") { injectDecoy(); sendResp({ status: "POISONED" }); }
      else if (req.action === "SHOW_CONTEXT_RESULT") showModal(req.type, req.data);
    });
  }

  // ─── BOOT ────────────────────────────────────────────────────────────────────
  function boot() {
    initHoverInspector();
    initAttachmentScanner();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();

})();
