# AgentMeasure website

Temporary official site, published at **<https://roy-tong.github.io/AgentMeasure/>**
via GitHub Pages (deployed by [`pages.yml`](../.github/workflows/pages.yml)).

One long page, static HTML + CSS + a thin interaction layer. No framework,
no build step — loads fast, easy for any agent (or human) to edit.

```text
website/
├── index.html    # all sections + copy
├── styles.css    # Precision Instrument design system (colors = data states)
├── script.js     # console playback, scroll reveals, nav state
└── assets/       # favicon.svg, social-preview.png (og:image)
```

## Design principles

1. **Instrument, not SaaS** — measurement console language, mono for facts,
   sans for prose, graph-paper surface.
2. **Colors are data states** — green `#6EF2A3` evidence/confirmed, blue
   `#76A5FF` specification/structure, yellow `#F6C85F` unknown/partial,
   red `#FF6B6B` failure. Never decoration.
3. **Do not make claims stronger than the evidence.** Every status on the page
   (`DEFINED / PARTIAL / DRAFT`, `● / ◐ / ○`) mirrors the repo's specs and
   harness profiles. When the spec moves, this page moves with it.

## Editing

Copy changes → `index.html`. Visual changes → `styles.css`. To preview locally:

```bash
cd website && python3 -m http.server 4173
# → http://localhost:4173
```

Push to `main` (or edit anything under `website/`) and the site redeploys.

## Status conventions (keep honest)

- Status strip reflects the current release (`standard/` version, SDK version).
- The runtime matrix mirrors `profiles/*.md` — update both together.
- External-trial numbers (“3 MCP/API providers”) mirror `product/AUDIT.md`.
