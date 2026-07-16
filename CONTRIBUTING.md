# Contributing to DiamondIQ

We love contributions! Here is how you can help.

## Code of Conduct

This project follows a [Code of Conduct](CODE_OF_CONDUCT.md). By participating you agree to uphold it.

## How to Contribute

### 1. Report Bugs

Open an issue using the **Bug Report** template. Include:
- Steps to reproduce
- Expected vs actual behavior
- Screenshots if applicable
- Your environment (OS, Python version)

### 2. Suggest Features

Open an issue using the **Feature Request** template. Describe:
- The problem you are solving
- Your proposed solution
- Alternatives you considered

### 3. Submit Code

1. Fork the repository
2. Create a branch: `git checkout -b feature/my-feature`
3. Make your changes
4. Run the app and verify nothing is broken
5. Commit with a clear message
6. Push and open a Pull Request

## Development Setup

```bash
git clone https://github.com/zaidbharde/DiamondIQ.git
cd DiamondIQ
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your API keys
python app.py
```

## Pull Request Guidelines

- One feature/fix per PR
- Update documentation if you change public APIs
- Verify the app starts and core routes work
- Keep code style consistent with the existing codebase
- No hardcoded secrets or API keys

## Code Style

- Python: Follow PEP 8
- JavaScript: Standard ES6+
- HTML/CSS: Keep existing conventions
- Import ordering: standard library → third-party → local

## Testing

Run the app and manually verify:
- `GET /` — home page loads
- `POST /predict` — prediction works
- `POST /upload-certificate` — OCR works
- `POST /analyze-image` — vision AI works (if keys configured)
- `GET /history` — history loads and paginates
- `DELETE /history/{id}` — deletion works

## Need Help?

Open a **Question** issue or start a discussion.
