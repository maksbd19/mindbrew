# sample_live_wax_ester_client_v1

Live-tier sample (case 5 in `gold/sample_cases.yaml`).

## Gold fixtures

- `fixtures/expected/sample_live_wax_ester_client_v1/brief.json`
- `fixtures/expected/sample_live_wax_ester_client_v1/pathways.json`

## Acceptable variants

- Gatekeeper: `PROCEED` only.
- Target class: `wax_ester` or `lipid`.
- FBA verdict: `pass` or `marginal`.
- Enzyme labels: FAR / WS naming variants OK.

## To activate

Copy the case block from `sample_cases.yaml` into `live_cases.yaml`, then:

```bash
BREWMIND_OFFLINE=false uv run python -m mindbrew_v2.eval.run_eval --tier live --live
```
