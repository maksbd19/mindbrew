# live_wax_ester_template_v1

Replace this template after a reviewed live session.

## Steps

1. Paste your anonymized brief into `live_cases.yaml` → `input.raw_brief`.
2. Run a live session with `BREWMIND_OFFLINE=false`.
3. At CP1/CP2, export the approved `ResearchBrief` and primary pathway candidates.
4. Overwrite `fixtures/expected/live_wax_ester_template_v1/brief.json` and `pathways.json`.
5. Re-run: `BREWMIND_OFFLINE=false uv run python -m mindbrew_v2.eval.run_eval --tier live --live`.

## Acceptable variants

- Enzyme naming: FAR / fatty acyl-CoA reductase / wax ester synthase (WS) all OK.
- FBA verdict: `pass` or `marginal` acceptable.
- Target class: `wax_ester` or `lipid` if feedstock is plant oil.
