# Architecture

## Overview

DiamondIQ is a Flask-based web application with a layered architecture: a responsive single-page frontend, a RESTful API backend, an ML inference layer, an OCR pipeline, a multi-provider AI vision system, and a SQLite database.

```text
┌─────────────────────────────────────────────────────┐
│                    Browser (UI)                      │
│  HTML + CSS + JavaScript (Chart.js, Lucide Icons)   │
└──────────────────────┬──────────────────────────────┘
                       │ HTTP / JSON
                       ▼
┌─────────────────────────────────────────────────────┐
│                Flask Web Server                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐   │
│  │  Routes  │  │  Config  │  │  Middleware       │   │
│  │  (REST)  │  │  (.env)  │  │  CSRF, Rate Lim  │   │
│  └────┬─────┘  └──────────┘  └──────────────────┘   │
└───────┼─────────────────────────────────────────────┘
        │
        ├──────────────────────────────────┐
        ▼                                  ▼
┌──────────────────┐           ┌──────────────────────┐
│  ML Service      │           │  AI Service Layer    │
│  ┌────────────┐  │           │  ┌────────────────┐  │
│  │ Predict    │  │           │  │ ai_provider.py  │  │
│  │ Contributions│  │           │  │ (auto-detect)  │  │
│  │ Explanation │  │           │  ├────────────────┤  │
│  └────────────┘  │           │  │ image_analysis  │  │
└──────────────────┘           │  │ OpenAI / Gemini │  │
                                │  └────────────────┘  │
                                └──────────────────────┘
        │                                  │
        ▼                                  ▼
┌──────────────────┐           ┌──────────────────────┐
│  Database Layer  │           │  OCR Service         │
│  ┌────────────┐  │           │  ┌────────────────┐  │
│  │ SQLite    │  │           │  │ Tesseract      │  │
│  │ Predictions│  │           │  │ PyMuPDF (PDF) │  │
│  │ Schema    │  │           │  │ Certificate   │  │
│  │ Migration │  │           │  │ Parsing       │  │
│  └────────────┘  │           │  └────────────────┘  │
└──────────────────┘           └──────────────────────┘
```

## Frontend

- **Single-page application** with JavaScript-driven page switching
- **Pages:** Manual Entry, Certificate Upload, Image Analysis, Result, Dashboard
- **Charts:** Chart.js for feature contributions, price comparison, distributions, timeline
- **Icons:** Lucide Icons via CDN
- **PDF:** jsPDF for client-side report generation
- **Themes:** Dark/light mode with system preference detection and localStorage persistence
- **Responsive:** Glassmorphism design, works on desktop and mobile

## Backend (Flask)

### Routes (`webapp/routes.py`)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | Home page with form, history, metrics |
| `/predict` | POST | Run diamond price prediction |
| `/upload-certificate` | POST | Upload & OCR certificate |
| `/analyze-image` | POST | AI vision analysis of diamond image |
| `/history` | GET | Paginated prediction history |
| `/history/<id>` | GET | Single prediction detail |
| `/history/<id>` | DELETE | Delete a prediction |
| `/history/export/csv` | GET | Export history as CSV |
| `/history/export/json` | GET | Export history as JSON |

### Configuration (`webapp/config.py`)

All environment variables loaded from `.env` via `python-dotenv`. Config class provides Flask app config with sensible defaults.

### Middleware

- **CSRF Protection:** Token-based, validated on POST/DELETE
- **Rate Limiting:** Per-IP deque-based, configurable (default 30/min)
- **Security Headers:** X-Content-Type-Options, X-Frame-Options, Referrer-Policy, Permissions-Policy

## ML Pipeline

### Training (`src/DiamondPricePrediction/components/`)
- **Data Ingestion:** Loads raw CSV, splits train/test
- **Data Transformation:** ColumnTransformer with ordinal encoding, StandardScaler
- **Model Training:** LinearRegression, RandomForest, GradientBoosting with hyperparameter tuning via GridSearchCV

### Inference (`webapp/ml_service.py`)
- **PredictionService:** Lazy-loads model + preprocessor with joblib/pickle
- **Contributions:** Heuristic feature contribution scoring
- **Explanation:** Rule-based price explanation

## OCR Flow

1. User uploads certificate (PDF/JPG/JPEG/PNG)
2. File saved temporarily with UUID filename
3. PDF rendered to image via PyMuPDF (300 DPI)
4. Tesseract OCR extracts text
5. Text merged and parsed for label-value pairs
6. Certificate type detected (GIA/IGI/HRD/AGS/Generic)
7. Fields extracted and returned
8. Temp file deleted in `finally` block

## Vision AI Flow

1. User uploads diamond image (PNG/JPG/JPEG/WEBP)
2. Image validated (format, size ≤ 10 MB)
3. Provider selected via `ai_provider.select_provider()`:
   - `AI_PROVIDER=openai` → uses OpenAI
   - `AI_PROVIDER=gemini` → uses Gemini
   - `AI_PROVIDER=auto` → tries OpenAI, falls back to Gemini
4. Image encoded as base64, sent to vision API with structured prompt
5. Response parsed as JSON with diamond attributes
6. Confidence scores returned alongside suggestions
7. In `auto` mode, falls back to other provider if primary fails

## Prediction Flow

1. User fills form or uploads certificate/image
2. Input validated server-side
3. `PredictionService.predict(inputs)`:
   - DataFrame created → preprocessor transforms → model predicts
   - Contributions scored heuristically
   - Explanation generated from rules
4. `generate_report()` computes quality score + recommendation
5. `analyze_features()` provides XAI analysis
6. Result stored in SQLite with full input + contribution snapshots
7. Response includes prediction, metrics, report, charts data

## Database

- **Engine:** SQLite via `sqlite3` module
- **Location:** `Artifacts/predictions.db`
- **Schema:** `predictions` table with JSON columns for inputs, contributions, XAI
- **Migration:** Auto-adds new columns on startup via `init_db()`
- **Features:** Search, sort (price/quality/date), pagination, CSV/JSON export

## AI Service Layer

### Provider Selection (`webapp/ai_provider.py`)

```text
AI_PROVIDER=openai ──> OPENAI_API_KEY? ──Yes──> openai
                          │ No
                          ▼
                       return None

AI_PROVIDER=gemini ──> GEMINI_API_KEY? ──Yes──> gemini
                          │ No
                          ▼
                       return None

AI_PROVIDER=auto   ──> OPENAI_API_KEY? ──Yes──> openai
                          │ No
                          ▼
                      GEMINI_API_KEY? ──Yes──> gemini
                          │ No
                          ▼
                       return None
```

### Model Selection
- **OpenAI:** `OPENAI_MODEL` env var (default `gpt-4.1-mini`)
- **Gemini:** `GEMINI_MODEL=auto` triggers `genai.list_models()` discovery; preference for stable flash models; cached per process lifetime

## Security Architecture

- **No secrets in code** — all keys loaded from `.env` (gitignored)
- **CSRF tokens** on state-changing endpoints
- **Rate limiting** per IP
- **Input sanitization** via `markupsafe.escape` + whitelist validation
- **Security headers** set on every response
- **Temporary file cleanup** guaranteed via `try/finally`
- **File type whitelist** for uploads
