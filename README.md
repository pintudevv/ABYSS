# ⚡ ABYSS — Multi-Dimensional Hybrid ML Cyber Threat Detection & Active Deception Platform

<p align="center">
  <img src="https://readme-typing-svg.demolab.com?font=Inter&weight=700&size=24&duration=3000&pause=1000&color=00D2FF&center=true&vCenter=true&width=700&lines=Multi-Dimensional+Hybrid+ML+Threat+Detection;Active+Honeypot+Deception+%26+Network+Sinkhole;Discord+Grabber+%26+Crypto+Drainer+Neutralization;System+Incident+Response+CLI+(abyss)" alt="ABYSS Banner Typing SVG" />
</p>

<p align="center">
  <a href="https://abyss-plum-theta.vercel.app"><img src="https://img.shields.io/badge/Live_Web_App-Vercel-000000?style=for-the-badge&logo=vercel&logoColor=white" /></a>
  <a href="https://abyss-1-d265.onrender.com"><img src="https://img.shields.io/badge/Render_API-Backend-46E3B7?style=for-the-badge&logo=render&logoColor=white" /></a>
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/Next.js-14-000000?style=for-the-badge&logo=nextdotjs&logoColor=white" />
  <img src="https://img.shields.io/badge/Frida-Live_Hooks-E34F26?style=for-the-badge&logo=frida&logoColor=white" />
  <img src="https://img.shields.io/badge/Licence-MIT-00D2FF?style=for-the-badge" />
</p>

---

## 🛡️ Executive Summary

**ABYSS** is an end-to-end, zero-trust cyber threat intelligence, active deception, and incident response platform. Designed to combat modern infostealers, Discord token grabbers, crypto wallet drainers, keyloggers, and ransomware, ABYSS operates across two synchronized surfaces:

1. 🌐 **Cloud Web Platform ([`abyss-plum-theta.vercel.app`](https://abyss-plum-theta.vercel.app))**: A glassmorphic dark security dashboard with dynamic file uploads, real-time pipeline polling, SHAP explainable AI charts, and attack timeline breakdown.
2. 🖥️ **System Incident Response CLI (`abyss`)**: A 1-word terminal scanner that audits Task Manager processes via PowerShell, verifies Authenticode digital signatures, detects masquerading binaries, offers 1-click `[T]erminate / [N]eutralize / [S]kip` controls, and enforces an **Automated Boot Guard**.

---

## ⚡ Quick 1-Line Installation (Claude Code Style)

Anyone can install the **ABYSS Cyber Incident Sentinel CLI** directly in 1 second without downloading or cloning the repository folder.

### 💻 Windows (PowerShell)
```powershell
irm https://raw.githubusercontent.com/pintudevv/ABYSS/main/install.ps1 | iex
```

### 🐧 Linux / macOS (Bash)
```bash
curl -fsSL https://raw.githubusercontent.com/pintudevv/ABYSS/main/install.sh | sh
```

### 📦 Direct Pip Installation
```bash
pip install git+https://github.com/pintudevv/ABYSS.git
```

Once installed, simply open any terminal and type:
```bash
abyss
```

---

## 📐 End-to-End Pipeline Architecture

```mermaid
flowchart TD
    File["Uploaded Sample / Local System Scan"]
    
    subgraph S1 ["Layer 1: Static PE & YARA Extraction"]
        Static["LIEF & pefile Parsing<br/>PE Section Entropy<br/>Suspicious String Signatures"]
    end

    subgraph S2 ["Layer 2: Dynamic Sandbox Detonation"]
        Sandbox["Frida Hook Engine<br/>Win32 API Trace<br/>Memory & File Audits"]
    end

    subgraph S3 ["Layer 3: Hybrid ML & Zero-Day Model"]
        ML["Dual XGBoost & Random Forest<br/>PyTorch Autoencoder Loss<br/>SHAP Feature Impact"]
    end

    subgraph S4 ["Layer 4: Active Honeypot Deception"]
        Deception["Decoy Discord LevelDB Tokens<br/>Decoy Crypto Seed Vaults<br/>Webhook Network Sinkhole<br/>Keylogger & Screen Capture Nulling"]
    end

    subgraph S5 ["Layer 5: Incident Response CLI (abyss)"]
        CLI["Task Manager Live Process Auditor<br/>Authenticode Signature Check<br/>1-Click Terminate / Neutralize<br/>Boot Guard Windows Startup Sentinel"]
    end

    File --> S1
    S1 --> S2
    S2 --> S3
    S3 --> S4
    S4 --> S5

    classDef default fill:#1e293b,stroke:#00d2ff,stroke-width:2px,color:#fff;
    classDef staticStyle fill:#1e1b4b,stroke:#818cf8,stroke-width:2px,color:#fff;
    classDef dynamicStyle fill:#31103f,stroke:#f43f5e,stroke-width:2px,color:#fff;
    classDef mlStyle fill:#451a03,stroke:#fbbf24,stroke-width:2px,color:#fff;
    classDef deceptionStyle fill:#022c22,stroke:#34d399,stroke-width:2px,color:#fff;
    classDef cliStyle fill:#111827,stroke:#06b6d4,stroke-width:2px,color:#fff;

    class File default;
    class Static staticStyle;
    class Sandbox dynamicStyle;
    class ML mlStyle;
    class Deception deceptionStyle;
    class CLI cliStyle;
```

---

## ✨ Core Security Features

| Icon | Feature Dimension | Implementation Details | Neutralization & Defense Strategy |
| :---: | :--- | :--- | :--- |
| 🪤 | **Discord Token Neutralization** | `backend/mock_data/fake_discord_tokens.json` | Intercepts LevelDB and token reads, returning trackable decoy credentials (`fake_discord_tokens.json`). |
| 🌐 | **Webhook Network Sinkhole** | `backend/deception_layer.py` | Outbound HTTP/socket calls to `discord.com/api/webhooks/` return `200 OK (FAKE_SUCCESS)` with payload sinkholing. |
| 🔑 | **Crypto Drainer Protection** | `backend/mock_data/fake_metamask_seeds.txt` | Serves fake 12-word BIP-39 seed phrases & wallet files whenever a process requests `wallet.dat` or `seed.txt`. |
| ⌨️ | **Keylogger Neutralization** | `SetWindowsHookExW` / `SetWindowsHookExA` | Frida JS hook intercepts keyboard hook registrations and returns `NULL` handles so keyloggers fail. |
| 📸 | **Screenshot Interception** | `BitBlt` / `PrintWindow` | Hooks GDI and User32 screen capture functions, returning `FALSE` blank framebuffers. |
| 🧠 | **Hybrid ML Classifier** | `backend/classifier.py` | Trained on **1,000,000 EMBER samples** (XGBoost, Random Forest, PyTorch Autoencoder for Zero-Day detection). |
| 📊 | **SHAP Explainable AI** | `shap.TreeExplainer` | Ranks top 10 feature impacts explaining the exact technical reasons behind every classification. |
| 🖥️ | **System Incident CLI** | `abyss` / `backend/abyss_cli.py` | 1-word terminal scanner with Task Manager process auditing, Authenticode signature check, and masquerading detection. |
| 🛡️ | **Automated Boot Guard** | `abyss --boot-scan` | Registers `HKCU\...\Run` startup sentinel that runs an automated <2s security check every time Windows boots. |
| 🔒 | **Local Data Vault** | `~/.abyss/` (`C:\Users\<User>\.abyss\`) | Persists offline incident logs (`reports/`), user settings (`config.json`), and signatures (`signatures/`). |

---

## 💻 ABYSS CLI Workflow (`abyss`)

Run the 1-word CLI command from any terminal:

```bash
abyss
```

### Incident Damage Assessment & Interactive Remediation UI

```
==============================================================================
     A B Y S S   C Y B E R   I N C I D E N T   C L I   S C A N N E R
     System Incident Response & Compromise Remediation Engine v1.0
==============================================================================
  [MODE: ADMINISTRATOR (FULL PRIVILEGES)]

[1/5] Scanning Memory & Running Process Threads...
  [OK] Auditing 142 Active Task Manager Processes...

[2/5] Scanning Discord & Browser Session Files...
  [!] Discord session files found in AppData (LevelDB active)
  [OK] Session file audit completed.

[3/5] Auditing Crypto Wallet Vaults & Seed Files...
  [OK] Crypto seed & extension audit completed.

[4/5] Scanning Registry Startup Persistence Keys...
  [OK] Startup Registry Run keys clean (Authenticode verified).

[5/5] Verifying System Hosts File & Driver Integrity...
  [OK] System Hosts file clean.

=== INCIDENT DAMAGE ASSESSMENT SCORECARD ===================================================

 [EXPOSED] AT RISK / EXPOSED DATA ITEMS:
    * Flagged Processes     : 0 active items
    * Session Data Paths    : 5 paths inspected
    * Persistence Keys      : 0 registry items

 [PROTECTED] SAVED & NEUTRALIZED DATA ITEMS:
    * Crypto Seed Vaults    : 100% PROTECTED
    * Neutralized Webhooks  : SINKHOLE READY
    * Saved Cookies/Creds   : SECURED

=== 1-CLICK INTERACTIVE SYSTEM REMEDIATION ===================================================

 [1] Per-Process Action Menu ([T]erminate / [N]eutralize / [S]kip)
 [2] Export Incident Summary Report (saved to ~/.abyss/reports/)
 [3] Toggle Automatic Boot Guard (Auto-scan on Windows Boot) [ENABLED]
 [4] Exit Scanner
```

---

## 📁 Repository Structure

```
ABYSS/
├── backend/
│   ├── main.py               # FastAPI server (lifespan, CORS, status poller)
│   ├── static_analysis.py    # PE Feature & String Extractor (LIEF & pefile)
│   ├── sandbox_runner.py     # Dynamic VM/Guest Sandbox Controller
│   ├── classifier.py         # Hybrid ML Engine (XGBoost, RF, PyTorch Autoencoder, SHAP)
│   ├── deception_layer.py    # Frida API Hooks, Honeypots, & Network Sinkhole
│   ├── forensic_logger.py    # Timeline assembler & JSON/TXT report generator
│   ├── abyss_cli.py          # Cyber Incident Response CLI & Boot Guard Engine
│   ├── mock_data/            # Honeypot decoy files (fake Discord tokens, seeds, cookies)
│   └── models/               # Saved EMBER ML models & PyTorch Autoencoder
├── frontend/
│   ├── app/
│   │   ├── page.tsx          # Drag-and-drop upload & dynamic progress pipeline
│   │   └── report/page.tsx   # Glassmorphic threat report dashboard
│   ├── components/           # UI elements (CircularProgress, FileUpload, ThreatReport)
│   └── lib/api.ts            # API client connected to Render live backend
├── setup.py                  # PyPI package setup for 1-word `abyss` command
├── abyss.bat                 # Direct Windows batch command launcher
├── test_grabber_detection.py # Automated test suite for grabber detection & honeypots
└── test_live_frida_attach.py # Test suite for live Frida PID process attachment
```

---

## 🚀 Quick Start Guide

### 1. Launch Web Application Backend & Frontend
```bash
# Backend (FastAPI)
cd backend
pip install -r requirements.txt
python main.py

# Frontend (Next.js 14)
cd frontend
npm install
npm run dev
```

### 2. Install ABYSS CLI Locally
```bash
# Register global 'abyss' command
pip install -e .

# Run CLI scanner anytime
abyss
```

### 3. Check Neutralized Processes Status
```bash
abyss --status
```

---

## 📄 License
Distributed under the **MIT License**. Created by the **ABYSS Cyber Security Team**.