# StealthOS
### Hybrid ML Malware Detection, Deception & Forensic Capture System

StealthOS is a next-generation malware analysis platform that combines static machine learning classifiers, dynamic sandbox profiling (via VirtualBox and Frida), active deception/neutralization layers, and detailed forensic reporting into a unified premium dashboard.

---

## 🚀 Pipeline Architecture

```
                       Upload File (EXE / DLL / ZIP)
                                     │
                                     ▼
                      ┌──────────────────────────────┐
                      │    1. Static Feature Extraction │
                      │  - PE Header & String Analysis│
                      │  - Pack & Entropy Checking   │
                      └──────────────┬───────────────┘
                                     │
                                     ▼
                      ┌──────────────────────────────┐
                      │     2. Dynamic Profiling     │
                      │  - Reverts VM to clean state │
                      │  - AutoLogon Headless Boot   │
                      │  - Inject Frida Hook Engine  │
                      └──────────────┬───────────────┘
                                     │
                                     ▼
                      ┌──────────────────────────────┐
                      │    3. Hybrid Classifier      │
                      │  - XGBoost & Random Forest   │
                      │  - PyTorch Autoencoder (ZD)  │
                      │  - SHAP Feature Explanations │
                      └──────────────┬───────────────┘
                                     │
                                     ▼
                      ┌──────────────────────────────┐
                      │ 4. Deception & Neutralization│
                      │  - Return Fake Success/NULLs │
                      │  - Sinkhole Malicious IPs    │
                      │  - Watchdog Honeypots        │
                      └──────────────┬───────────────┘
                                     │
                                     ▼
                      ┌──────────────────────────────┐
                      │      5. Forensic Engine      │
                      │  - Timeline Reconstruction   │
                      │  - Unified Forensic Report   │
                      └──────────────┬───────────────┘
                                     │
                                     ▼
                         Premium Next.js Dashboard
```

---

## 📁 Repository Structure

```
stealthos/
├── backend/
│   ├── main.py              # FastAPI server (lifespan, CORS, status pollers)
│   ├── static_analysis.py   # Stage 1: PE feature and string extractor (LIEF/pefile)
│   ├── sandbox_runner.py    # Stage 2: VM controller, AutoLogon, guest runner
│   ├── guest_sandbox.py     # Guest side: Frida export injection engine (x86/x64)
│   ├── classifier.py        # Stage 3: ML Engine (XGBoost, RF, PyTorch Autoencoder, SHAP)
│   ├── deception_layer.py   # Stage 4: Frida faking, Network Sinkholing, watchdog decoys
│   ├── forensic_logger.py   # Stage 5: Timeline assembler & JSON/TXT report builder
│   ├── models/              # Saved ML models (xgboost_model.pkl, rf_model.pkl, autoencoder.pt)
│   ├── mock_data/           # Honeypot decoy files (cookies, credit cards, passwords)
│   └── results/             # Analysis outputs (features.json, behavior.json, results.json)
├── frontend/
│   ├── app/
│   │   ├── page.tsx         # Drag-and-drop file upload & dynamic progress pipeline
│   │   └── report/page.tsx  # Interactive glassmorphism threat intelligence dashboard
│   ├── components/          # UI elements (CircularProgress, FileUpload, ThreatReport)
│   └── lib/api.ts           # API client (maps real backend response to UI structure)
└── training/
    ├── train_model.ipynb    # Google Colab notebook for ML classifier training
    ├── test_real_behavior.c # Safe custom binary showcasing hooked API actions
    └── test_suspicious.c    # Safe custom binary showcasing dynamic API resolution
```

---

## 🛠️ Installation & Setup

### 1. Environment Configuration
Create a `.env` file in the `backend/` directory based on `backend/.env.example`:
```env
STEALTHOS_VM_USER=piyuzz
STEALTHOS_VM_PASS=your_guest_vm_password_here
```

### 2. Backend Setup (Python 3.10+)
Install Python dependencies:
```bash
cd backend
pip install -r requirements.txt
```
To run the FastAPI server:
```bash
python main.py
```
The server will start on `http://localhost:8000`. You can view the interactive documentation at `http://localhost:8000/docs`.

### 3. Frontend Setup (Next.js 14+)
Install node modules:
```bash
cd frontend
npm install
```
Build and run the production server:
```bash
npm run build
npm run start
```
The UI dashboard will be accessible at `http://localhost:3000`.

---

## 🧪 VM Sandbox Configuration
For dynamic analysis, ensure a VirtualBox VM named `StealthOS-Sandbox` is set up with:
1. **AutoLogon Enabled**: Windows automatically logs in to the desktop on boot.
2. **Frida Server running**: Frida Server (v17.15.3 recommended) running as a system service.
3. **Headless Default**: Run `VBoxManage modifyvm "StealthOS-Sandbox" --defaultfrontend headless` so snapshots resume headlessly.
4. **Baseline Snapshot**: Take a powered-off snapshot named `clean-baseline`.

---

## 📊 Heuristics and ML Classifiers
* **XGBoost & Random Forest**: Evaluates files based on 2,381 static EMBER features.
* **Autoencoder Anomaly Detection**: Highlights potential Zero-Day threats if the reconstruction loss exceeds the threshold derived during training.
* **SHAP (SHapley Additive exPlanations)**: Calculates the exact impact of top features contributing to the final classification verdict.

---

## 🛡️ Deception Mechanisms
* **Win32 API Hooking**: Frida hooks credential files (`CreateFile`), registry keys (`RegOpenKeyEx`), clipboard data (`GetClipboardData`), and sockets (`connect`). Accesses are faked (`FAKE_SUCCESS`, `INVALID_HANDLE_VALUE`, or `NULL`) to neutralize threat progression.
* **IP Sinkholing**: Blocks exfiltration to C2 servers using blocklists, logging all deflected data.
* **Watcher honeypots**: Watchdog monitors reads of decoy files under `mock_data/` and logs when a process tries to steal honey tokens.

---

## 📜 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/analyze` | Upload EXE/ZIP file and run full 5-stage pipeline |
| `GET` | `/status/{task_id}` | Poll progress (0-100%) and stage descriptions |
| `GET` | `/results/{task_id}` | Fetch structured threat report JSON |
| `GET` | `/results/{task_id}/download` | Download human-readable forensic summary report |
| `DELETE` | `/results/{task_id}` | Delete task files and clear from cache |
| `GET` | `/health` | Verify presence of backend scripts and ML models |