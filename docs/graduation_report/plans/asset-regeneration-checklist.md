# Asset Regeneration Checklist

## Goal

Make `graduation_report/figures/` reproducible from code and latest validated experiment outputs.

## Checklist

- [ ] Inventory all files under `graduation_report/figures/`.
- [ ] Map each file to a generator in `docs/graduation_report/code/` or mark as missing generator.
- [ ] For missing generators, create script or mermaid/drawio source in `docs/graduation_report/code/`.
- [ ] Define standard output path for each generator.
- [ ] Ensure generator reads latest validated result source, not stale copied numbers.
- [ ] Add support for tables rendered as `.tex` where needed.
- [ ] Add support for thesis-ready chart labels, legends, and font sizing.
- [ ] Add support for deterministic reruns.
- [ ] Document commands used to regenerate all Chapter 2 and Chapter 3 visual assets.
- [ ] Rebuild and verify output diffs.
