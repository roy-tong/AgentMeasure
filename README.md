# AgentMeasure website

Live: https://roy-tong.github.io/AgentMeasure/

Static HTML, CSS and JavaScript. The main entry is an AI support buyer with a specific billing, acceptance or renewal task. Buyer services and fee mechanisms are under validation. Local developer tools and the existing $10/$20 services retain their separate scope. Standards, SDK, claims and research remain supporting resources.

## Pages

- `index.html`: buyer decisions, task-fit entry, local tools, distinct developer services and technical evidence.
- `services.html`: canonical service terms, input requirements, application links and refunds.
- `claims.html`: dated technical evidence; no paid-adoption claims.
- `releases.html`: CLI and SDK release information; package versions are independent.
- `first-look.html`: buyer task-fit discussion, evidence requirements and exploratory fee mechanisms; no standard package or recovery promise.
- `recount.html`, `rules/`, `blog/`, `badges.html`: existing tools and research; preserve their evidence boundaries.
- `llms.txt`, `sitemap.xml`, `robots.txt`: public discovery. Repository documents in llms.txt use absolute GitHub URLs.

## Preview and publish

```bash
cd website
python3 -m http.server 4173
```

Edit on `main`. Run AGENTS.md checks and inspect local links before pushing. `.github/workflows/conformance.yml` verifies the repository, updates `status.json`, then mirrors `website/` to the root of `gh-pages`. GitHub Pages publishes that branch. Do not manually overwrite the deployment branch. Verify the conformance run, Pages deployment and live content after pushing.

## Keep current

Use the service page as the public source for pricing and delivery conditions. Do not replace it with an older workspace copy. Date audit statistics and link evidence; do not use engineering counts as proof of customer value. CLI and SDK versions must be checked independently. Preserve historical release notes as historical, rather than rewriting past releases.
