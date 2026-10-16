# Maintainer notes

## Repository layout

| Path | Purpose |
| --- | --- |
| `skills/rapih-in/` | The skill: the only part installed into agents (`SKILL.md`, `references/`, `scripts/`, `agents/openai.yaml`) |
| `tools/sync.py` | Install, update, verify, uninstall from this single source |
| `tools/validate.py` | Static package and documentation checks |
| `tests/` | Helper and install-tool tests (`python -m unittest discover -s tests`) |
| `evals/` | Fixtures, fixture generator, real-agent evaluation harness |
| `docs/evaluation.md` | Recorded evaluation results |
| `assets/branding/` | Logo |

## Release checklist

1. `python -m unittest discover -s tests` passes.
2. `python tools/validate.py` passes.
3. Bump `VERSION` in `skills/rapih-in/scripts/rapihin_state.py` when the helper or the skill contract changes.
4. Re-run the affected evaluation cases (`evals/run_agent_eval.py`) and update `docs/evaluation.md`; never copy old results into a new version's status.
5. Update `README.md` and `README.id.md` together.
6. `python tools/sync.py install` and `python tools/sync.py verify` on each test machine.

## Publishing status

- Public repository: https://github.com/mkautsarpb/rapih-in (created 2026-10-16).
- Issue tracker and support channel: https://github.com/mkautsarpb/rapih-in/issues.
- Star History chart: embedded in both READMEs (2026-10-16).

Not configured yet:
- Release tags and CI badges.

## Enabling the Star History chart

Already done for `mkautsarpb/rapih-in`. To redo it (for example after a rename):

1. Open https://www.star-history.com, enter `OWNER/REPO`, keep the "Date" view.
2. In "Show real-time chart on your README.md", choose **GitHub README.md** and copy the generated snippet. It uses a `<picture>` element with a dark and a light `<source>` and an `<img>` fallback, served from `api.star-history.com`, wrapped in a link to the chart page. At the time of writing the generated snippet has this shape:

   ```html
   <a href="https://www.star-history.com/#OWNER/REPO&Date">
     <picture>
       <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=OWNER/REPO&type=Date&theme=dark" />
       <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=OWNER/REPO&type=Date" />
       <img alt="Star History Chart for OWNER/REPO" src="https://api.star-history.com/svg?repos=OWNER/REPO&type=Date" />
     </picture>
   </a>
   ```

   Prefer the snippet the site generates if it differs from this shape.
3. Replace the placeholder sentence in the "Star History" section of both `README.md` and `README.id.md` with the snippet. Keep the alt text descriptive.
4. Never put a GitHub token (plain, encrypted, or sealed) in the README or the URL. The public embed needs none; a personal token entered on the website stays in your browser.
5. Check the chart in GitHub's light and dark themes. If the service cannot render the chart yet (new repository without stars), leave the explanatory sentence instead of a broken image.
6. Run `python tools/validate.py`.

## Brand

- The name is always written `rapih-in` (lowercase, hyphen).
- `assets/branding/rapih-in-logo.png` is the master raster logo supplied with the project brief (2172 x 724, transparent background). There is no SVG master; do not label the PNG as vector.
- Teal `#038982` on white is about 4.3:1 and on GitHub dark (`#0d1117`) about 4.4:1, which is enough for a large wordmark, so one asset serves both themes. Mint `#70DBA6` is an accent only and must not carry text on white.
