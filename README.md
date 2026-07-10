# 🧬 TwinCare AI — Personal Health Intelligence Platform

> **AI-powered Digital Twin** that transforms blood reports into actionable health intelligence with explainable risk prediction and a conversational health copilot.

![Status](https://img.shields.io/badge/status-hackathon%20MVP-brightgreen)
![Python](https://img.shields.io/badge/python-3.11-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688)
![PyTorch](https://img.shields.io/badge/PyTorch-2.5-ee4c2c)
![AMD ROCm](https://img.shields.io/badge/AMD-ROCm%20compatible-ed1c24)

---

## 🚀 What It Does

Upload a blood report → AI extracts biomarkers → Digital Twin updates → Heart disease risk predicted with SHAP explanations → Ask your AI Health Copilot about your data.

**One Demo Flow:**
1. **Sign up** with email/password
2. **Upload** a blood report (PDF/image)
3. **See** extracted biomarkers and health score on the Dashboard
4. **View** heart disease risk prediction with explainable AI (SHAP waterfall)
5. **Ask** the AI Copilot: "What does my cholesterol level mean?"

---

## 🏗️ Architecture

```
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│   React Frontend │────▶│  FastAPI Backend  │────▶│   PostgreSQL     │
│   (TypeScript)   │     │  (Python 3.13)   │     │   (Data Store)   │
└──────────────────┘     └────────┬─────────┘     └──────────────────┘
                                  │
                    ┌─────────────┼─────────────┐
                    ▼             ▼             ▼
            ┌──────────┐  ┌──────────┐  ┌──────────┐
            │ OCR      │  │ LightGBM │  │ Fireworks│
            │ Pipeline │  │ Heart    │  │ API      │
            │(Tesseract)│  │ Model   │  │ (Gemma)  │
            └──────────┘  │ + SHAP   │  └──────────┘
                          │ (CPU)    │
                          └──────────┘
```

---

## 🛠️ Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Frontend | React + TypeScript + TailwindCSS | UI via Natively Builder |
| Backend | FastAPI + SQLAlchemy + PostgreSQL | REST API + business logic |
| OCR | Tesseract + pdf2image | Report text extraction |
| Risk Model | LightGBM (CPU) | Heart disease risk prediction |
| Explainability | SHAP TreeExplainer | Live feature attribution |
| LLM | Fireworks API (Gemma 2) | Health Copilot + NER fallback |
| Deployment | Docker Compose | One-command launch |

---

## ⚡ Quick Start

### Prerequisites
- Docker & Docker Compose
- (Optional) Fireworks AI API key for the Copilot

### 1. Clone & Configure

```bash
git clone https://github.com/YOUR_USERNAME/twincareAI.git
cd twincareAI
cp .env.example .env
# Edit .env and add your FIREWORKS_API_KEY
```

### 2. Launch

```bash
docker compose up --build
```

### 3. Seed Demo Data (Optional)

```bash
docker compose exec backend python seed_data/seed.py
```

### 4. Access

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| Health Check | http://localhost:8000/health |

**Demo Login:** `demo@twincare.ai` / `demo123`

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/register` | Register new user |
| POST | `/api/v1/auth/login` | Login, get JWT token |
| GET | `/api/v1/auth/me` | Get current user profile |
| POST | `/api/v1/reports/upload` | Upload health report |
| GET | `/api/v1/reports/{id}/status` | Check processing status |
| GET | `/api/v1/reports` | List all reports |
| GET | `/api/v1/reports/{id}/biomarkers` | Get extracted biomarkers |
| GET | `/api/v1/digital-twin` | Get Digital Twin state |
| GET | `/api/v1/risk-predictions` | Get risk predictions |
| GET | `/api/v1/risk-predictions/{id}` | Get prediction details + SHAP |
| POST | `/api/v1/copilot/chat` | Chat with AI Health Copilot |
| GET | `/api/v1/copilot/history` | Get chat history |
| GET | `/api/v1/dashboard` | Get aggregated dashboard data |

---

## 🤖 AMD GPU Usage

The heart disease model comparison and development phase utilized **PyTorch on AMD ROCm** (for neural network training and validation):

- **Model Selection & Comparison**: AMD GPU environment compared PyTorch MLPs, XGBoost, and LightGBM models.
- **Production Inference**: The selected production model is a LightGBM gradient-boosted tree classifier, which runs efficiently on CPU during inference.
- **Gemma Copilot**: The AI Health Copilot uses **Gemma 2 via Fireworks AI** (optimized for AMD hardware).

---

## 🗃️ Model Card: TwinCare AI CVD Risk Model (v3)

### Overview
- **Model Type**: Calibrated LightGBM (via 5-fold cross-validated Platt/Sigmoid Calibration)
- **Task**: 10-year risk prediction of future Coronary Heart Disease (CHD)
- **Dataset**: Framingham Heart Study (4,240 records, 17 features)
- **Inputs**: 15 patient intake & biomarker fields + 2 derived features (Pulse Pressure and Mean Arterial Pressure)
- **Decision Threshold**: 0.15 (optimized for screening sensitivity post-calibration)

### Performance Evaluation
Evaluating the production calibrated LightGBM model on held-out test data (Stratified 20% Split):
- **AUC-ROC**: **0.684** (honest stratified validation, an improvement over the uncalibrated 0.664)
- **Recall (Sensitivity)**: **65.8%** (at 0.15 threshold, correctly flagging the majority of positive cases)
- **Precision**: **23.9%** (screening tool trade-off: 1 in 4 flagged patients has true risk, framing results as "worth a closer clinical look")
- **F1 Score**: **0.350**
- **Average Predicted Probability**: **15.6%** (perfectly calibrated to match the true baseline CHD prevalence rate of 15.2% in the training data, resolving the 37.8% raw uncalibrated inflation)

### Key Limitations
- **Dated Dataset**: Framingham data is historical (30-70 years old) and single-population (Framingham, MA), so it may not generalize perfectly to all demographics.
- **Screening Tool Focus**: Optimizing for high Recall leads to false positives. The model should be framed as a screening aid rather than a diagnostic tool.

---

## 📁 Project Structure

```
twincareAI/
├── docker-compose.yml          # One-command launch
├── .env.example                # Configuration template
├── CHANGES.md                  # Model pass changelog (v1 -> v2 -> v3)
├── README.md                   # You are here
├── backend/
│   ├── Dockerfile
│   ├── main.py                 # FastAPI app
│   ├── config.py               # Settings
│   ├── database.py             # PostgreSQL connection
│   ├── models/                 # SQLAlchemy models (7 tables)
│   ├── schemas/                # Pydantic request/response
│   ├── routers/                # API endpoints
│   ├── services/               # Business logic
│   ├── ai/                     # AI pipelines (OCR, model, SHAP, LLM)
│   ├── utils/                  # Security, biomarker ranges
│   └── seed_data/              # Demo data seeder
├── frontend/                   # React app (Natively Builder)
└── notebooks/                  # Historical and v3 training notebooks
```

---

## ⚠️ Disclaimer

**TwinCare AI is a decision-support and preventive-health tool, NOT a diagnostic tool.** All predictions and AI responses include disclaimers. This application uses synthetic/public sample data and has not undergone clinical validation. Always consult a qualified healthcare professional for medical advice.

---

## 🔮 Future Roadmap

- Multi-modal ingestion (X-rays, CT scans, wearable data)
- 5-year health trajectory simulation
- Medical literature RAG (PubMed/clinical guidelines)
- Clinical EHR integration (HL7 FHIR)
- On-premise AMD GPU deployment for hospitals
- Multi-language Copilot support

---

## 📝 License

MIT License — Built for AMD Developer Hackathon: ACT II

---

*Built with ❤️ and AMD ROCm*
