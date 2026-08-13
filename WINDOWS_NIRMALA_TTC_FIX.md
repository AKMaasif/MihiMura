# Windows Nirmala UI TTC fix

Windows 10/11 may provide Nirmala UI as `C:\\Windows\\Fonts\\Nirmala.ttc` rather than separate `.ttf` files.

The backend now auto-detects `Nirmala.ttc` for both Sinhala and Tamil before falling back to the older `.ttf` path or Linux Noto fonts.

For local development you can also set:

```env
MIHIMURA_SINHALA_FONT_PATH=C:\\Windows\\Fonts\\Nirmala.ttc
MIHIMURA_TAMIL_FONT_PATH=C:\\Windows\\Fonts\\Nirmala.ttc
```

Restart the backend and verify `/api/v1/health`. Expected:

```json
"multilingual_pdf": {
  "harfbuzz": true,
  "sinhala_font": true,
  "tamil_font": true,
  "ready": true
}
```
