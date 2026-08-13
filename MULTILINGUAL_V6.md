# MihiMura v6 — English / Sinhala / Tamil AI parity

## What changed

MihiMura AI now treats English, Sinhala and Tamil as first-class conversation languages across the core AI workflow.

### Automatic language detection

The AI chat language selector defaults to **Auto detect**. Each submitted message is inspected using Unicode script detection:

- English / Latin script → English
- Sinhala script → Sinhala
- Tamil script → Tamil

The detected language is sent to FastAPI as the response language for that turn. Manual English / සිංහල / தமிழ் selection remains available as an override.

Auto detection changes the active UI/chat language locally but does not overwrite the user's saved profile-language preference on every message.

### Multilingual intent routing

The deterministic router now recognizes English, Sinhala and Tamil phrases for:

- Simple Chat / explanations
- Weather and climate decisions
- Fertilizer and crop-protection decisions
- Irrigation / field decisions
- Crop-health questions
- Market questions
- Full cultivation / business reports

District and crop extraction also includes Sinhala/Tamil aliases. Native grammatical suffixes are tolerated for district names, e.g. `ගාල්ලේ` and `காலியில்`.

### Native land-area extraction

Common forms are supported, including:

- `1 acre`
- `1 අක්කර`
- `අක්කර 1ක`
- `1 ஏக்கர்`
- `ஏக்கர் 1`
- hectare / perch equivalents where configured

### Decision Support parity

A Sinhala/Tamil weather question now routes to Decision Support, resolves a named Sri Lankan district to its fallback district-centre coordinates when no exact farm GPS is available, selects the weather tool, and answers in the active language. If the live tool fails, the assistant explicitly reports that the live evidence could not be obtained rather than claiming it was checked.

Safety keywords and consequential-action detection also cover Sinhala and Tamil fertilizer/pesticide/irrigation terminology.

### Full Report parity

The active conversation language is stored in structured conversation memory. Full Report generation uses that language for:

- title
- executive summary
- section headings
- paragraphs and bullets
- table headings/cells
- assumptions
- limitations
- next actions

The report composer validates the target language. A Sinhala/Tamil request is not silently replaced by an English PDF if generation/translation fails.

### Unicode PDF rendering

English keeps Helvetica. Sinhala/Tamil use a Unicode TrueType font with shaping enabled.

Local Windows fallback:

- `C:\Windows\Fonts\Nirmala.ttf`
- `C:\Windows\Fonts\NirmalaB.ttf`

The backend Dockerfile installs Noto fonts for Linux deployments. Custom font locations can be configured through `MIHIMURA_SINHALA_FONT_PATH`, `MIHIMURA_SINHALA_BOLD_FONT_PATH`, `MIHIMURA_TAMIL_FONT_PATH`, and `MIHIMURA_TAMIL_BOLD_FONT_PATH`.

No font files are bundled into this project.

## Local test prompts

English:

```text
What is the weather in Galle now?
```

Sinhala:

```text
ගාල්ලේ දැන් කාලගුණය කොහොමද?
```

Tamil:

```text
காலியில் இப்போது வானிலை எப்படி இருக்கிறது?
```

Sinhala report:

```text
පොළොන්නරුවේ අක්කර 1ක වී වගාවට සම්පූර්ණ වාර්තාවක් දෙන්න
```

Tamil report:

```text
பொலன்னறுவையில் 1 ஏக்கர் நெல் சாகுபடிக்கு முழு அறிக்கை கொடு
```

Also test switching languages inside the same conversation:

```text
What is paddy blast?
වී වගාවේ මේ රෝගය වළක්වා ගන්නේ කොහොමද?
இந்த நோய் வந்தால் என்ன செய்ய வேண்டும்?
```

With **Auto detect** selected, each response should follow the language of the current message while retaining the same conversation context.
