# Brand assets — drop your generated logos here

Generate images from `../../logo-prompts.md`, then save them here with these exact names. The app picks them up automatically (they're served from `/brand/...`).

| File | From prompt | Used for |
|---|---|---|
| `mascot.png` | #1 Refined hero mascot | The main mascot everywhere (replaces the current `/zatoona.png`). **Transparent PNG.** |
| `favicon.png` | #3 App icon / favicon | Browser tab icon. Export 512×512; also drop `favicon-32.png`, `favicon-16.png` if you have them. |
| `icon-maskable.png` | #3 (padded variant) | PWA / install icon (safe padding). Optional. |
| `wordmark.svg` *(or .png)* | #4 Wordmark + lockup | Optional — the app currently renders the wordmark in the Fredoka font, so you only need this for social/share cards. |

## Mascot mood art (optional, makes the character far more alive)

The mascot animates a single image into 6 moods today. To use **dedicated art per mood**, generate the variants from prompt #2 and drop them in `../mascot/` (see the README there). Then flip `USE_MOOD_ART = true` in `src/components/Mascot.tsx`.

## After adding `mascot.png`

Point the app at it by changing the default in two places (or just overwrite `public/zatoona.png` with your new transparent version — easiest):
- `src/components/Mascot.tsx` → `DEFAULT_SRC`
- `src/components/Brand.tsx` → the `<img src>`
- `index.html` → `<link rel="icon">` to `/brand/favicon.png`
