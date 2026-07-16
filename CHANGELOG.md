# Changelog

All notable changes to DiamondIQ are documented here.

## [1.0.0] — 2026-07-13

### Added
- AI-powered diamond price prediction using trained scikit-learn pipeline
- Diamond image analysis with multi-provider AI vision (OpenAI + Gemini)
- Automatic AI provider selection (`AI_PROVIDER=auto/openai/gemini`)
- Automatic Gemini model discovery (`GEMINI_MODEL=auto`)
- Certificate OCR upload (GIA/IGI) with text extraction
- Professional PDF valuation report generation
- Interactive charts (feature contribution, input overview, price comparison)
- Dashboard with metrics, price distribution, quality distribution, timeline
- Searchable prediction history with pagination, CSV/JSON export
- Glassmorphism responsive UI with dark/light mode
- Client-side and server-side input validation
- CSRF protection, rate limiting, security headers
- XAI (Explainable AI) with positive/negative factor analysis
- Quality scoring engine (cut/color/clarity/carat weighting)
- Recommendation engine (Luxury Grade → Needs Review)
- RESTful API for predictions, history, and certificate upload
- SQLite database with automatic schema migration
- Dark/light mode toggle with system preference detection
- Keyboard shortcuts (Ctrl+Enter, Ctrl+R, Ctrl+K)
- Copy, share, print, and PDF download of valuation reports
- Full Docker support

### Changed
- Refactored AI provider system into dedicated `ai_provider.py` module
- Updated Gemini model from deprecated `gemini-2.0-flash-exp` to `gemini-flash-latest`
- Added `python-dotenv` for automatic `.env` loading
- Added `google-generativeai` to dependencies
- Improved error handling with graceful provider fallback
- Standardized shared `ANALYSIS_PROMPT` across providers

### Fixed
- `sqlite3.OperationalError` from empty `DATABASE_PATH` env var
- `.env` file not being loaded at startup
- Unused `AI_PROVIDER` variable in original code
- Hardcoded model names causing 404 errors

### Security
- No API keys or secrets committed to repository
- `.env` in `.gitignore`
- CSRF tokens on all state-changing requests
- Rate limiting on all POST endpoints
- Input sanitization with `markupsafe.escape`
- Security headers (X-Content-Type-Options, X-Frame-Options, Referrer-Policy, Permissions-Policy)
- Temporary upload files cleaned up after processing
