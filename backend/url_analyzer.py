"""
ABYSS — URL & Website Safety Analyzer Engine
=============================================
Analyzes target web URLs for phishing, brand impersonation, credential theft,
suspicious TLDs, SSL/TLS security flaws, and data exfiltration risk.
"""

from __future__ import annotations

import re
import ssl
import socket
import urllib.parse
import urllib.request
from typing import Dict, Any, List

# High-risk TLDs commonly abused for instant phishing disposable sites
HIGH_RISK_TLDS = {".xyz", ".top", ".click", ".site", ".fun", ".club", ".zip", ".gq", ".ml", ".cf", ".tk", ".work", ".kim", ".fit", ".rest"}

# Known brand keywords targeted by phishing scams
TARGETED_BRANDS = {
    "discord": ["nitro", "gift", "free", "claim", "airdrop", "login", "auth", "verify", "app-nitro"],
    "steam": ["community", "trade", "gift", "login", "stean", "stearm", "offer"],
    "metamask": ["seed", "phrase", "connect", "restore", "wallet", "claim", "verify"],
    "phantom": ["solana", "wallet", "connect", "seed", "airdrop", "claim"],
    "binance": ["login", "verify", "security", "bonus", "withdraw"],
    "roblox": ["robux", "gift", "free", "login", "promo"],
    "netflix": ["account", "update", "billing", "payment"],
    "microsoft": ["login", "office", "onedrive", "verify", "session"],
}

def analyze_url_safety(raw_url: str) -> Dict[str, Any]:
    """
    Analyzes a URL or domain for phishing, scam, and malware threats.
    Returns structured threat evaluation object.
    """
    if not raw_url:
        return {"error": "Empty URL provided", "risk_level": "UNKNOWN"}

    # Ensure scheme
    url_str = raw_url.strip()
    if not url_str.startswith(("http://", "https://")):
        url_str = "https://" + url_str

    try:
        parsed = urllib.parse.urlparse(url_str)
        domain = parsed.netloc.lower()
        if ":" in domain:
            hostname = domain.split(":")[0]
            port = int(domain.split(":")[1])
        else:
            hostname = domain
            port = 443 if parsed.scheme == "https" else 80
    except Exception as e:
        return {"error": f"Invalid URL format: {str(e)}", "risk_level": "UNKNOWN"}

    risk_score = 0
    threat_reasons: List[str] = []
    threat_type = "Clean Website"

    # 1. Check Protocol Security
    is_https = parsed.scheme == "https"
    if not is_https:
        risk_score += 25
        threat_reasons.append("Unencrypted HTTP Protocol (No SSL/TLS encryption)")

    # 2. Check High Risk TLDs
    tld_match = False
    for tld in HIGH_RISK_TLDS:
        if hostname.endswith(tld):
            tld_match = True
            risk_score += 20
            threat_reasons.append(f"High-Risk Phishing TLD Detected ({tld})")
            break

    # 3. Check Brand Impersonation & Typo-squatting
    is_brand_impersonation = False
    for brand, keywords in TARGETED_BRANDS.items():
        if brand in hostname or any(k in hostname for k in keywords):
            # Check if it's NOT the genuine official domain
            official_domains = [f"{brand}.com", f"{brand}.gg", f"{brand}.org", f"store.steampowered.com", f"steampowered.com"]
            if not any(hostname == off or hostname.endswith("." + off) for off in official_domains):
                is_brand_impersonation = True
                risk_score += 45
                threat_reasons.append(f"Brand Impersonation / Phishing Attack targeting [{brand.upper()}]")
                threat_type = f"Phishing Page ({brand.capitalize()} Impersonation)"
                break

    # 4. Check Suspicious URL Path Keywords
    path_lower = parsed.path.lower() + "?" + parsed.query.lower()
    suspicious_path_terms = ["token", "seed", "private_key", "wallet_connect", "nitro-claim", "login.php", "webhooks"]
    for term in suspicious_path_terms:
        if term in path_lower:
            risk_score += 20
            threat_reasons.append(f"Credential Exfiltration Parameter Detected ('{term}')")

    # 5. Check Direct IP Hostname
    if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", hostname):
        risk_score += 30
        threat_reasons.append("Raw IP Address Hostname (Bypassing Domain Name Resolution)")

    # 6. SSL/TLS Certificate Validation (if HTTPS)
    ssl_valid = False
    ssl_issuer = "N/A"
    if is_https:
        try:
            context = ssl.create_default_context()
            context.timeout = 2.0
            with socket.create_connection((hostname, port), timeout=2.0) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    cert = ssock.getpeercert()
                    ssl_valid = True
                    issuer_info = cert.get("issuer", ())
                    for item in issuer_info:
                        for key, val in item:
                            if key == "organizationName" or key == "commonName":
                                ssl_issuer = val
                                break
        except Exception:
            ssl_valid = False
            risk_score += 25
            threat_reasons.append("Invalid or Untrusted SSL Certificate")

    # Calculate final Risk Level
    risk_score = min(risk_score, 100)
    if risk_score >= 70:
        risk_level = "CRITICAL"
        if threat_type == "Clean Website":
            threat_type = "Malicious Phishing / Scam Site"
    elif risk_score >= 45:
        risk_level = "HIGH"
        if threat_type == "Clean Website":
            threat_type = "Suspicious Domain"
    elif risk_score >= 20:
        risk_level = "MEDIUM"
        if threat_type == "Clean Website":
            threat_type = "Low Trust Website"
    else:
        risk_level = "CLEAN"

    return {
        "url": url_str,
        "domain": hostname,
        "is_https": is_https,
        "ssl_valid": ssl_valid,
        "ssl_issuer": ssl_issuer,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "threat_type": threat_type,
        "is_phishing": risk_score >= 45,
        "threat_reasons": threat_reasons,
        "recommendation": "DO NOT ENTER CREDENTIALS OR SEED PHRASES ON THIS SITE!" if risk_score >= 45 else "Website appears clean and safe to visit."
    }
