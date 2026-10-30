# Verovo brand assets

Short version: the wordmark is dark art and lives on light surfaces. The owl mark
is the only piece designed to sit on dark surfaces, and in this repository it sits
on a light plate so the eye whites survive.

## Files

| File | Use |
|---|---|
| `assets/verovo-logo.png` | Wordmark, transparent, dark ink. Light backgrounds only. |
| `assets/verovo-logo-card.png` | Wordmark on a rounded light plate, transparent around the plate. READMEs, decks, anywhere the background is unknown. |
| `assets/verovo-mark.png` | Owl mark (the two eyes and the tuft), transparent. Favicons, avatars, nav lockups. |
| `website/assets/favicon.svg` | 64×64 icon: light plate, owl mark, 1.5px border. |
| `website/assets/favicon-256.png` | 256×256 raster of the same icon (aimed at 180/192px consumers). |
| `assets/social-preview.png` | 1280×640 Open Graph / social card. Source: `website/assets/social-preview.html`. |
| `assets/quality-ladder.png` | 1600×863 caller-identity diagram. Source: `assets/quality-ladder.html`. |
| `assets/verovo-stack.svg` | Vector measurement-stack diagram. |

Rendered images are generated, not hand-edited. Regenerate with headless Chrome at
2× and downscale:

```bash
chrome --headless=new --hide-scrollbars --window-size=1280,640 \
  --force-device-scale-factor=2 --screenshot=og.png \
  file://$PWD/website/assets/social-preview.html
```

## Rules

1. **Wordmark on light surfaces only.** The "vero" letterforms are near-black
   (`#0D1330`); they disappear on `--bg` (`#090C10`). Do not recolour them.
2. **Dark UI uses a plate.** A light plate (`#F2F5F7`, 6px radius, 4px/7px padding)
   carries the mark or the wordmark. See `.brand-plate` in `website/styles.css`.
   Do not outline, shadow or tint the artwork.
3. **Do not invent a dark-mode wordmark.** The eye whites are paper-white and
   connect to the background in the supplied art; recolouring them produces a
   variant the designer never drew.
4. **Clear space** is at least the height of the owl mark's pupil (~9% of the
   wordmark height) on all four sides.
5. **Minimum size**: wordmark 96px wide on screen, 24mm in print. Below that use the
   mark alone.
6. **Mark only when square.** The mark is ~1.86:1; crop to the two eyes for avatars,
   never stretch or rotate it.
7. **Colours** come from the artwork, not from the site palette: ink `#0D1330`,
   gradient `#2E6BFF → #6E3BFF`, eye white `#FFFFFF`, surface `#090C10`, plate
   `#F2F5F7`.

## Naming

`Verovo` in sentences and titles; `verovo` in identifiers (packages, commands,
environment variables, directories, schema namespaces, URLs); `VEROVO` only inside
constants such as `VEROVO_EVENTS_DIR`.
