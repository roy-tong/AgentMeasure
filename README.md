# AgentMeasure website

Temporary official site, published at **<https://roy-tong.github.io/AgentMeasure/>**
via GitHub Pages (currently the classic `gh-pages` branch; intended to switch to
the [`pages.yml`](../.github/workflows/pages.yml) Actions deploy).

One long page, static HTML + CSS + a thin interaction layer. No framework,
no build step — loads fast, easy for any agent (or human) to edit.

```text
website/
├── index.html    # all sections + copy
├── styles.css    # Precision Instrument design system (colors = data states)
├── script.js     # console playback, scroll reveals, nav state
└── assets/       # favicon.svg, social-preview.png (og:image)
```

## Page structure (IA: comprehension → proof → depth)

Layer 1 — understand (5 minutes):

1. Hero — trace console: 1 intent · 2 attempts · 1 operation
2. `#why` — the problem (state inequalities)
3. `#facts` — claim discipline (large ≠ statements: Attempt ≠ Operation,
   Returned ≠ Consumed, Observed ≠ Inferred)
4. `#measure` — measurement chain (Reach → Choice → Use → Utility → Value)
   with spec-status chips and the signature line:
   *defined does not mean observable in every runtime*
5. `#how` — provider-side architecture

Layer 2 — prove / convert:

6. `#available` — what works today (spec sheet: shipped vs in development)
7. `#try` — 2-minute demo terminal
8. `#trial` — external provider trial CTA

Layer 3 — go deeper:

9. `#standard` — runtime observability matrix (mirrors `profiles/*.md`)
10. `#lab` — AgentMeasure vs AgentMeasure Lab
11. `#economy` — long-term thesis (Capability Economy)

## Design principles

1. **Instrument, not SaaS** — measurement console language, mono for facts,
   sans for prose, graph-paper surface.
2. **Colors are data states** — green `#6EF2A3` evidence/confirmed, blue
   `#76A5FF` specification/structure, yellow `#F6C85F` unknown/partial,
   red `#FF6B6B` failure. Never decoration.
3. **Do not make claims stronger than the evidence.** Every status on the page
   (`Spec · Defined / Partial / Draft`, `● / ◐ / ○`) mirrors the repo's specs
   and harness profiles. When the spec moves, this page moves with it.
4. **Graceful degradation** — content is visible without JS (`.js` class gates
   hidden states); animations respect `prefers-reduced-motion`.

## Editing

Copy changes → `index.html`. Visual changes → `styles.css`. To preview locally:

```bash
cd website && python3 -m http.server 4173
# → http://localhost:4173
```

Deploy: commit to `website/` on `main`, then refresh the `gh-pages` snapshot
(until the Actions deploy is enabled):

```bash
git checkout gh-pages
git checkout main -- website/
# move website/* to repo root of that branch, keep .nojekyll, commit, push
```

## Status conventions (keep honest)

- Status strip reflects the current release (`standard/` version, SDK version).
- The `#available` spec sheet mirrors `sdk/`, CI, and `product/` — update the
  numbers (21 tests, 5 profiles) when they change.
- The runtime matrix mirrors `profiles/*.md` — update both together.
- External-trial numbers (“3 MCP/API providers”) mirror `product/AUDIT.md`.
