# StealthOS — Project README
==========================

# StealthOS
### Hybrid ML Malware Detection, Deception & Forensic Capture System

A semester project that takes an EXE or ZIP file, runs it through a 4-layer pipeline,
and produces a full threat report of what malware attempted and what was blocked.

---

## Pipeline Overview

```
Upload File (EXE/ZIP)
        │
        ▼
┌───────────────────┐
│  1. DETECTION     │  static_analysis.py + classifier.py
│  ML + PE Analysis │  → features.json, classification_result.json
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│  2. NEUTRALIZE    │  deception_layer.py (Frida)
│  API Hook & Block │  → hooks Windows APIs, returns FAKE SUCCESS
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│  3. DECEPTION     │  deception_layer.py (FakeNet-NG + OpenCanary)
│  Fake Data/Files  │  → malware reads fake passwords, cookies, docs
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│  4. FORENSICS     │  forensic_logger.py (Volatility + all logs)
│  Capture & Report │  → forensic_report.json
└─────────┬─────────┘
          │
          ▼
   Threat Report UI (Next.js)
```

---

## Project Structure

```
stealthos/
├── backend/
│   ├── main.py              # FastAPI server — orchestrates pipeline
│   ├── static_analysis.py   # Step 1: PE/ZIP static feature extraction
│   ├── sandbox_runner.py    # Step 3: Cuckoo sandbox integration
│   ├── classifier.py        # Step 4: ML classifier (XGBoost + RF + Autoencoder)
│   ├── deception_layer.py   # Step 5: Frida + FakeNet-NG + OpenCanary
│   ├── forensic_logger.py   # Step 6: Forensic report builder
│   ├── models/              # Trained model files (.pkl, .pt)
│   ├── mock_data/           # Honeypot decoy files
│   │   ├── fake_passwords.txt
│   │   ├── fake_cookies.db
│   │   ├── fake_credit_cards.txt
│   │   └── fake_contacts.csv
│   ├── results/             # Analysis output JSONs
│   └── requirements.txt
├── frontend/
│   ├── app/
│   │   ├── page.tsx         # Upload page
│   │   └── report/page.tsx  # Threat report page
│   └── components/
│       ├── FileUpload.tsx
│       ├── ProgressBar.tsx
│       └── ThreatReport.tsx
└── training/
    └── train_model.ipynb    # Google Colab training notebook
```

---

## Setup Instructions

### Backend (Python 3.10+)

```bash
cd backend
pip install -r requirements.txt
```

### Step 1 — Static Analysis (works standalone)
```bash
python static_analysis.py path/to/sample.exe
# Output: results/features.json
```

### Cuckoo Sandbox (WSL Ubuntu)
```bash
# In WSL:
pip install cuckoo
cuckoo init
cuckoo community
cuckoo
```

### Running the Full Backend
```bash
uvicorn main:app --reload --port 8000
```

### Frontend (Next.js)
```bash
cd frontend
npm install
npm run dev
```

---

## Tools Used

| Tool | Purpose | Location |
|------|---------|----------|
| pefile | PE header analysis | Windows |
| LIEF | Deep binary analysis | Windows |
| python-magic | File type detection | Windows |
| Cuckoo Sandbox | Dynamic analysis VM | WSL Ubuntu |
| Frida | Windows API hooking | Windows |
| FakeNet-NG | Network sinkhole | Windows |
| OpenCanary | Honeypot file system | Windows |
| Volatility3 | Memory forensics | Windows |
| XGBoost | ML classifier | Python |
| PyTorch | Autoencoder (zero-day) | Python |

---

## API Endpoints

| Method | Endpoint | Description |
|--------|---------|-------------|
| POST | `/analyze` | Upload file, run full pipeline |
| GET | `/status/{task_id}` | Check analysis progress |
| GET | `/results/{task_id}` | Get complete threat report |

---

## Authors
StealthOS Semester Project Team
piyush chaudhary