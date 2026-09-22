# FraudGuard AI
### *Detect. Analyze. Protect.*
> **AI-Based Fraud and Suspicious Transaction Detection Web Platform**  
> *Built for 24-Hour Student Hackathon 2026*

---

## 📌 Project Overview
**FraudGuard AI** is a financial security and transaction surveillance system built to identify suspicious transactions before they become financial threats. Designed specifically with a custom rectangular visual identity (strict avoidance of generic AI SaaS templates, capsule/pill badges, or floating cards), it combines **heuristic rule scoring** with **unsupervised Machine Learning (Isolation Forest)** and **Explainable AI** to give security analysts immediate, evidence-backed clarity.

---

## 🎯 Problem Statement
Digital payment systems handle billions of transactions daily. Traditional rule engines either miss novel fraud patterns or generate excessive false positives with zero context. Investigators waste hours analyzing black-box alerts. **FraudGuard AI** solves this by providing:
1. Multi-factor behavioral profiling (spending baseline, geographic zones, device cache, velocity).
2. Unsupervised outlier detection using Scikit-Learn Isolation Forest.
3. Plain-language, numbered Explainable AI reasons for instant forensic triage.
4. Coordinated account network graph analysis to detect money mule rings.

---

## 🚀 Key Features

- **Custom Financial-Security Visual Identity**: Clean, responsive layout using deep navy, rich purple, and teal accents with 4px–8px border-radii and rectangular indicators.
- **Dynamic Hybrid Risk Engine**:
  - `Amount Anomaly (+25)`: Flags transactions >3x account average or excessive lump sums.
  - `New Device (+20)`: Detects hardware and browser fingerprint changes.
  - `Unfamiliar Location (+20)`: Catches cross-border or out-of-region transactions.
  - `Unusual Time (+15)`: Identifies late-night off-hours activity.
  - `Burst Frequency (+20)`: Catches velocity spikes (≥5 transactions in 10 minutes).
- **Machine Learning (Isolation Forest)**: 120-estimator ensemble scoring continuous anomaly depth on a 7-dimensional feature plane.
- **Explainable AI (XAI)**: Synthesizes structured, numbered evidence cards (`01`, `02`, `03`...) explaining exactly why an alert was triggered.
- **Live Transaction Attack Simulator**: Interactive demo trigger on the dashboard showing 6-stage telemetry animation from ingestion to alert generation without page reload.
- **Transaction Relationship Network**: Interactive HTML5 Canvas graph uncovering coordinated transfer rings between connected accounts.
- **Batch CSV Ingestion & Export**: Drag-and-drop CSV dataset ingestion with instant risk grading and downloadable investigation reports.
- **Security Incident Workflow**: Incident triage with `Under Investigation` and `Dismiss` actions.

---

## 🛠️ Technology Stack

- **Backend Framework**: Python 3.13, Flask 3.1
- **Database**: SQLite3 (`database/fraudguard.db`)
- **Machine Learning**: Scikit-Learn (Isolation Forest), Pandas, NumPy, Joblib
- **Frontend**: Handcrafted HTML5 & CSS3 (No Bootstrap pills, no Tailwind generic SaaS templates), Vanilla ES6 JavaScript
- **Visualizations**: Chart.js 4.4, HTML5 Canvas Network Physics
- **Icons**: Lucide Icons

---

## 🏗️ System Architecture & Risk Calculation

$$\text{Final Risk Score} = \text{round}\Big(0.60 \times \text{Rule Score} + 0.40 \times \text{ML Anomaly Score}\Big)$$

| Risk Level | Score Range | Classification | Indicator Color | Recommended Action |
|---|---|---|---|---|
| **LOW** | 0 – 30 | Normal | 🟢 Green | Verified Standard Activity |
| **MEDIUM** | 31 – 60 | Review | 🟡 Amber | Secondary MFA Verification |
| **HIGH** | 61 – 80 | Suspicious | 🟠 Orange | Step-up Security Review |
| **CRITICAL** | 81 – 100 | Critical Threat | 🔴 Red | Instant Hold & Alert Dispatch |

---

## 🗄️ Database Schema

1. **`users`**: `id`, `email`, `password_hash`, `name`, `role`, `created_at`
2. **`accounts`**: `id`, `account_id`, `holder_name`, `avg_amount`, `min_amount`, `max_amount`, `normal_locations`, `normal_hours`, `known_devices`, `avg_daily_tx`, `risk_score`, `status`
3. **`transactions`**: `id`, `transaction_id`, `account_id`, `recipient_account_id`, `amount`, `avg_amount`, `location`, `time_str`, `device`, `new_device`, `transactions_10min`, `rule_score`, `ml_score`, `risk_score`, `risk_level`, `status`, `flagged_reasons`, `created_at`
4. **`alerts`**: `id`, `alert_id`, `transaction_id`, `account_id`, `severity`, `message`, `reasons`, `status`, `created_at`
5. **`system_settings`**: `rule_weight`, `ml_weight`, `high_risk_threshold`, `critical_risk_threshold`

---

## 🌐 API Endpoints

- `POST /api/login`: Authenticate analyst
- `GET /api/dashboard`: Aggregated security counters and telemetry
- `GET /api/transactions`: Paginated filterable transaction ledger
- `POST /api/transactions`: Ingest & analyze new transaction
- `GET /api/transactions/<id>`: Transaction detail with explainable AI factors
- `POST /api/simulate`: Live attack simulation with 6-stage telemetry
- `GET /api/accounts`: Behavioral account directory
- `GET /api/accounts/<id>`: Account profile vs baseline comparison
- `GET /api/alerts`: Incident feed
- `POST /api/alerts/<id>/review`: Move alert to Under Investigation
- `POST /api/alerts/<id>/dismiss`: Dismiss resolved alert
- `POST /api/upload`: Process CSV batch ingestion
- `GET /api/export-report`: Download investigation CSV
- `GET /api/analytics`: Chart.js analytical aggregates
- `GET /api/network`: Node & Edge transfer graph data
- `POST /api/settings`: Update rule/ML weights & thresholds

---

## ⚡ Quick Start & Installation

### 1. Prerequisites
- Python 3.10+ installed

### 2. Install Dependencies
```bash
cd fraudguard-ai
pip install -r requirements.txt
```

### 3. Initialize & Seed Database with Realistic Data
```bash
python seed_data.py
```

### 4. Run Application Server
```bash
python app.py
```

Open your browser at: **`http://127.0.0.1:5000`**

---

## 🔑 Demo Credentials

- **Email**: `admin@fraudguard.ai`
- **Password**: `admin123`

---

## 🎬 24-Hour Hackathon Jury Demonstration Flow

1. **Sign In**: Navigate to `http://127.0.0.1:5000/login`, sign in with `admin@fraudguard.ai` / `admin123`.
2. **Dashboard Overview**: View the 5 rectangular Security Overview metrics, Risk Landscape doughnut chart, and weekly activity.
3. **Simulate Attack**: Click the blue **[ Simulate Transaction ]** button on the top right. Watch the 6-stage real-time pipeline animation execute (Rules &rarr; Isolation Forest &rarr; Hybrid Score &rarr; XAI &rarr; Alert Dispatch).
4. **Investigate Threat**: Click **[ Open Full Investigation ]** to view the horizontal risk bar and explainable AI reasons (`01`, `02`, `03`...).
5. **Inspect Fraud Network**: Return to Dashboard, scroll to **Transaction Relationship Analysis** to view coordinated account nodes on the Canvas graph. Click on node `ACC102` to inspect its behavioral profile.
6. **Batch CSV Ingestion**: Navigate to **Upload Data**, click **[ Generate Sample CSV ]**, upload the file, and download the verified audit report.
7. **Security Alerts Feed**: Go to **Alerts**, review or dismiss pending incident tickets.
