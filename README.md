# ◆ DiamondIQ — AI Diamond Valuation Assistant

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.0%2B-lightgrey)](https://flask.palletsprojects.com)
[![Docker](https://img.shields.io/badge/Docker-ready-2496ED.svg)](Dockerfile)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

> **AI-powered diamond valuation assistant** — predicts diamond market price from gemological attributes using a trained ML pipeline, extracts data from GIA/IGI certificates via OCR, analyzes diamond photos with AI vision, and explains every prediction with explainable AI (XAI).

---

## 💎 The Problem

Diamond pricing today is opaque and inconsistent. Buyers, sellers, and jewellers rely on:

- **Rappaport / RapNet price lists** — subscription-based, no ML, no automation
- **Manual GIA/IGI certificate lookup** — slow, paper-dependent
- **Spreadsheet valuation formulas** — static, with no AI or explainability
- **Generic diamond calculators** — no OCR, no vision AI, no dashboard

There's no accessible, intelligent, centralized system for instant, transparent diamond valuation — until now.

## ✨ What DiamondIQ Does

DiamondIQ bridges traditional gemological expertise and modern AI/ML, giving anyone — first-time buyers to professional jewellers — an instant, explainable valuation in three ways: **manual entry**, **certificate OCR upload**, or **AI vision photo analysis**.

| Feature | Description |
|---------|-------------|
| **🔮 Price Prediction** | ML-based price prediction from carat, cut, color, clarity & dimensions (~10ms inference, 93.7% confidence) |
| **📄 Certificate OCR** | Upload a GIA/IGI certificate — Tesseract OCR + fuzzy matching auto-extract attributes |
| **🔍 AI Vision Analysis** | Upload a diamond photo — AI suggests shape, cut, color & polish |
| **🧠 Explainable AI (XAI)** | Shows positive/negative factors and the most influential features behind every price |
| **⭐ Quality Score** | Weighted 0–100 score (Cut 30% · Color 25% · Clarity 25% · Carat 20%) |
| **💰 Investment Recommendation** | Five-tier verdict, from *Luxury Grade* to *Needs Professional Review* |
| **📊 Dashboard** | Live metrics, price/quality distributions, timeline, recommendation breakdown |
| **📈 Charts** | Feature contribution, input overview, price comparison (Chart.js) |
| **📑 PDF Reports** | Professional valuation reports generated client-side (jsPDF) |
| **🌓 Dark/Light Mode** | System-aware with manual toggle, glassmorphism UI |
| **🔗 Share & Copy** | One-click copy, share, or print valuation reports |
| **🔐 Security** | CSRF protection, rate limiting, input sanitization, security headers |
| **🤖 Multi-Provider AI** | Auto-selects OpenAI or Gemini with graceful fallback — no hardcoded models |

---

## 🧠 How It Works

```
User → Web Interface (Browser)
         │
         ├── Manual Entry ──────→ Server Validation ──→ ML Prediction ──→ XAI ──→ Result
         │                              ↑                                        │
         ├── Certificate Upload ────────┘                                        │
         │     File → Validate → OCR → Parse GIA/IGI → Fill Form                │
         │                                                                       │
         └── Image Upload ────────────────────────────────────────────→ AI Vision
               File → Validate → Encode → OpenAI/Gemini → Parse JSON → Fill Form
                                                                                  │
                                                                                  ▼
                                                                          SQLite Database
                                                                                  │
                                                                                  ▼
                                                                          Dashboard
                                                                    (Charts, History, Export)
```

1. User picks an input mode — manual specs, certificate upload, or diamond photo.
2. Certificate uploads are OCR'd (Tesseract + PyMuPDF for PDFs) and parsed for GIA/IGI fields.
3. Photo uploads are sent to OpenAI or Gemini for vision-based attribute estimation.
4. The ML pipeline (preprocessor + LinearRegression model) predicts price.
5. Quality score, investment recommendation, and XAI breakdown are computed.
6. Result is shown with price, confidence, feature contributions, and a downloadable PDF report.
7. Every prediction is persisted to SQLite and reflected live on the dashboard.

---

## 🏗 Architecture

```
┌──────────────────────────────────────────────────────┐
│                    Browser (UI)                        │
│  HTML + CSS + JS (Chart.js, Lucide, jsPDF)            │
│  Pages: Home | Manual | Cert Upload | Image Upload    │
│         | Result | Dashboard                          │
└──────────────────────┬───────────────────────────────┘
                        │ HTTP / JSON
                        ▼
┌──────────────────────────────────────────────────────┐
│                 Flask Web Server                       │
│  Routes (REST/JSON) · Config (.env) · Middleware      │
│  (CSRF, Rate Limiting, Security Headers)              │
└───────┬────────────────────────────────────────────────┘
        │
        ├──────────────┬─────────────────────┐
        ▼              ▼                     ▼
 ┌─────────────┐ ┌──────────────┐   ┌──────────────────┐
 │ ML Service  │ │ AI Vision    │   │ OCR Service       │
 │ Predict ·   │ │ Layer        │   │ Tesseract ·       │
 │ XAI ·       │ │ (OpenAI /    │   │ PyMuPDF ·         │
 │ Quality ·   │ │  Gemini,     │   │ GIA/IGI           │
 │ Report      │ │  auto-fallback)│   │ Certificate Parser│
 └──────┬──────┘ └──────────────┘   └──────────────────┘
        ▼
 ┌─────────────────┐
 │ SQLite Database │
 │ predictions.db  │
 └─────────────────┘
```

- **Frontend**: Vanilla-JS single-page app (no framework overhead), Chart.js dashboard, Lucide icons, jsPDF reports, glassmorphism dark/light UI.
- **Backend**: Flask application factory pattern, blueprint-based routes, `.env`-driven config.
- **AI layer**: `ai_provider.py` resolves OpenAI/Gemini/auto at request time with automatic model discovery and fallback.
- **OCR layer**: Tesseract + PyMuPDF, with a custom GIA/IGI certificate parser that handles OCR text-merging and fuzzy character correction (e.g. `0→o`, `1→l`, `rn→m`).
- **ML layer**: Lazy-loaded scikit-learn pipeline with heuristic feature-contribution scoring for explainability.
- **Database**: SQLite with auto-migrating schema, search/sort/pagination, and CSV/JSON export.

Full breakdown available in [ARCHITECTURE.md](ARCHITECTURE.md).

---

## 🧪 Machine Learning

- **Dataset**: 53,940 diamond records (`gemstone.csv`) with carat, cut, color, clarity, depth, table, and x/y/z dimensions as features; price (₹) as target.
- **Preprocessing**: `ColumnTransformer` — numerical pipeline (median imputation → `StandardScaler`), categorical pipeline (mode imputation → `OrdinalEncoder` → `StandardScaler`).
- **Model selection**: Evaluated `LinearRegression`, `Lasso`, `Ridge`, and `ElasticNet` via GridSearch. **LinearRegression won on R² (~89%)** and was chosen for its speed (~10ms inference) and interpretability.
- **Explainability**: Feature contributions computed heuristically (carat ~44%, dimensions ~16%, cut ~14%, color/clarity ~12% each), feeding directly into the XAI breakdown.

> **Known limitation**: the categorical `OrdinalEncoder` maps `D→0` and `J→6`, which is conceptually reversed since D is the best color grade. LinearRegression compensates with a negative coefficient, and the heuristic scoring engine correctly uses `D=7 → J=1`. A future iteration would reverse the encoder's category order.

---

## 🏗 Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python, Flask 3.x |
| ML | scikit-learn, pandas, numpy, joblib |
| OCR | Tesseract, PyMuPDF |
| Vision AI | OpenAI GPT-4.1-mini, Google Gemini |
| Database | SQLite |
| Frontend | HTML, CSS, JavaScript (vanilla) |
| Charts | Chart.js |
| Icons | Lucide |
| PDF | jsPDF |
| CI/CD | GitHub Actions |

---

## 📁 Project Structure

```
Diamond-Price-Prediction-main/
├── app.py                     # Flask entry point
├── webapp/                    # Core web application
│   ├── __init__.py            # App factory
│   ├── config.py              # Configuration (.env)
│   ├── routes.py              # REST API endpoints
│   ├── database.py            # SQLite operations
│   ├── ml_service.py          # ML inference
│   ├── image_analysis.py      # AI vision analysis
│   ├── ai_provider.py         # Provider selection (auto/openai/gemini)
│   ├── ocr_service.py         # Tesseract OCR
│   ├── validation.py          # Input sanitization
│   ├── quality_score.py       # Quality scoring engine
│   ├── recommendation.py      # Recommendation engine
│   ├── report_generator.py    # Report builder
│   ├── xai.py                 # Explainable AI
│   └── certificate_parser.py  # GIA/IGI certificate parser
├── src/DiamondPricePrediction/ # ML training pipeline
├── static/                    # CSS, JS
├── templates/                 # HTML templates
├── Artifacts/                 # Model, preprocessor, database
├── .env.example               # Environment template
├── requirements.txt
├── Dockerfile
└── ARCHITECTURE.md            # Architecture documentation
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Tesseract OCR ([install guide](https://tesseract-ocr.github.io/))
- pip

### Installation

```bash
# Clone the repository
git clone https://github.com/zaidbharde/DiamondIQ.git
cd DiamondIQ

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys (optional — app works without AI vision)
```

### Run

```bash
python app.py
```

Open **http://127.0.0.1:8080** in your browser.

### Docker

```bash
docker build -t diamondiq .
docker run -p 8080:8080 --env-file .env diamondiq
```

---

## 🌐 Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | `dev-change-this` | Flask secret key |
| `FLASK_DEBUG` | `1` | Debug mode |
| `DATABASE_PATH` | `Artifacts/predictions.db` | SQLite database path |
| `MODEL_PATH` | `Artifacts/model.pkl` | Trained model path |
| `PREPROCESSOR_PATH` | `Artifacts/preprocessor.pkl` | Preprocessor path |
| `RATE_LIMIT_PER_MINUTE` | `30` | Max requests per minute per IP |
| `AI_PROVIDER` | `auto` | `auto`, `openai`, or `gemini` |
| `OPENAI_API_KEY` | — | OpenAI API key |
| `OPENAI_MODEL` | `gpt-4.1-mini` | OpenAI vision model |
| `GEMINI_API_KEY` | — | Google Gemini API key |
| `GEMINI_MODEL` | `auto` | Gemini model or `auto` for discovery |

`AI_PROVIDER=auto` tries OpenAI first and falls back to Gemini if the first fails — the app works fine for manual predictions even with **no API keys configured at all**.

---

## 📖 API Documentation

### `POST /predict`

Predict diamond price from attributes.

**Request:**
```json
{
  "carat": 0.7,
  "depth": 61.5,
  "table": 57.0,
  "x": 5.7,
  "y": 5.72,
  "z": 3.52,
  "cut": "Ideal",
  "color": "G",
  "clarity": "VS2"
}
```

**Response:**
```json
{
  "ok": true,
  "prediction": {
    "id": 1,
    "price": 2719.19,
    "confidence": 93.7,
    "model_used": "LinearRegression",
    "prediction_time_ms": 8.42,
    "explanation": "The price is more affordable because of Ideal cut...",
    "inputs": { "carat": 0.7, "cut": "Ideal", ... },
    "contributions": [
      { "feature": "Carat weight", "score": 35.2, "impact": 957.16 }
    ],
    "quality_score": 78.4,
    "recommendation": { "label": "Good Value", "badge": "good" },
    "xai": { "positive_factors": [...], "negative_factors": [...], "most_influential": [...] }
  }
}
```

### `POST /upload-certificate`
Upload a GIA/IGI certificate for OCR extraction. `multipart/form-data`, field `file` (PDF, JPG, JPEG, PNG), max 16 MB.

### `POST /analyze-image`
Upload a diamond photo for AI vision analysis. `multipart/form-data`, field `file` (PNG, JPG, JPEG, WEBP), max 10 MB.

### `GET /history`
List predictions with pagination.

| Param | Default | Description |
|-------|---------|-------------|
| `search` | — | Search in inputs, model, explanation |
| `sort` | `newest` | `newest`, `price_high`, `price_low`, `quality_high`, `quality_low` |
| `page` | `1` | Page number |

### `DELETE /history/{id}`
Delete a prediction. Requires CSRF token.

### `GET /history/export/csv` · `GET /history/export/json`
Export all predictions as CSV or JSON.

---

## 🧠 AI Provider Configuration

```env
# Auto-select (OpenAI preferred, then Gemini)
AI_PROVIDER=auto

# Force OpenAI
AI_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4.1-mini

# Force Gemini
AI_PROVIDER=gemini
GEMINI_API_KEY=...
GEMINI_MODEL=auto          # Auto-discover best model
GEMINI_MODEL=gemini-flash-latest  # Or specify manually
```

---

## 🎯 Prediction Fields

| Field | Range | Description |
|-------|-------|-------------|
| Carat | 0.1 – 5.0 | Diamond weight |
| Cut | Fair, Good, Very Good, Premium, Ideal | Cut quality |
| Color | D, E, F, G, H, I, J | Color grade (D = best) |
| Clarity | I1, SI2, SI1, VS2, VS1, VVS2, VVS1, IF | Clarity grade |
| Depth | 40% – 80% | Depth percentage |
| Table | 40% – 80% | Table percentage |
| X | 1.0 – 15.0 mm | Length |
| Y | 1.0 – 15.0 mm | Width |
| Z | 0.5 – 10.0 mm | Height |

---

## 🔐 Security

| Measure | Implementation |
|---------|----------------|
| CSRF Protection | Session + meta-tag token, validated via `secrets.compare_digest()` on POST/DELETE |
| Rate Limiting | Per-IP deque-based sliding window, default 30 req/min |
| Input Sanitization | `markupsafe.escape()` on all string inputs |
| File Upload Validation | Whitelisted extensions, size limits, UUID-based temp filenames |
| Security Headers | CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy |
| Secrets | Loaded from `.env`, never committed; `.env.example` provided |
| Session Cookies | HTTPOnly, SameSite=Lax |

---

## ⚠️ Limitations

- ML model uses only 9 features — real-world valuation also factors in fluorescence, symmetry, polish, girdle, and culet.
- LinearRegression assumes a linear price relationship; no interaction terms are captured.
- No authentication or multi-user support — single-user by design.
- SQLite only — no PostgreSQL/MongoDB support yet.
- AI vision requires OpenAI/Gemini API keys and internet access.
- OCR accuracy depends on certificate scan quality.
- No automated test suite (manual verification + CI syntax/import checks only).

---

## 🛣 Roadmap

- [ ] User authentication and multi-user support
- [ ] PostgreSQL/MongoDB support
- [ ] SHAP-based explainability
- [ ] Real diamond image training dataset
- [ ] REST API client library
- [ ] WebSocket-based real-time updates
- [ ] Mobile app (React Native)
- [ ] Blockchain-based certificate verification

---

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) and our [Code of Conduct](CODE_OF_CONDUCT.md).

---

## 📄 License

[MIT](LICENSE) © 2026 Zaid Bharde

---

## 🙏 Acknowledgements

- scikit-learn for the ML pipeline
- OpenAI and Google for AI vision APIs
- Tesseract OCR for text extraction
- Chart.js for interactive visualizations
- Lucide for beautiful icons
- jsPDF for PDF report generation
