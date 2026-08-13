# MihiMura Sinhala/Tamil PDF reliability fix

This build keeps the existing English PDF flow and hardens Sinhala/Tamil report generation.

## Changes

- Gemini report composition now uses schema-constrained JSON output with Pydantic validation.
- Sinhala/Tamil fallback translation is split into small validated batches; a failed batch retries section-by-section.
- The API returns a clear 503 error for provider/font/runtime failures instead of an opaque 500.
- `uharfbuzz` is installed for ReportLab complex-script shaping.
- Additional Noto Sinhala/Tamil bold-font paths are recognized.

## Render deployment

Prefer deploying `mihimura-backend` with its Dockerfile. It installs `fonts-noto-core`, which supplies the Noto Sinhala/Tamil fonts expected by `reports.py`. If you use a non-Docker Render runtime, install equivalent Noto Sinhala/Tamil fonts in that runtime or set the `MIHIMURA_*_FONT_PATH` variables to existing font paths. Do not point these variables at frontend/public URLs; ReportLab needs local server-side TTF paths.

After deployment, redeploy the backend so the new Python dependency and font/runtime changes are installed.

## Health check after deploy

Open `/api/v1/health` on the backend and check `multilingual_pdf`. A fully prepared production runtime should report `sinhala_font: true`, `tamil_font: true`, `harfbuzz: true`, and `ready: true`.
