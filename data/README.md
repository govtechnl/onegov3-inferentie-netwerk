# Data

Machine-readable, **fictitious** starter data. YAML is the source of truth; the JSON Schemas in [`schemas/`](schemas/) define the format and CI checks every file against them.

| File | What it holds |
|---|---|
| [`network.yaml`](network.yaml) | Four fictitious organisations (one per role in the brief), their sites with GPUs, speed, models, tariffs, energy use, acceptance rules and availability windows, plus a research site and a commercial EU site |
| [`policy.yaml`](policy.yaml) | The rules: data classes and where they may go, priority tiers, task-to-model rules, coordination rules |
| [`scenarios.yaml`](scenarios.yaml) | Six demo scenarios built from the demand file with overlays |
| [`demand/`](demand/) | Simulated demand for one working day, per 15-minute slot |
| [`schemas/`](schemas/) | JSON Schemas for all of the above |

## Units

- **Reference GPU-seconds**: work measured on a reference GPU. A site with speed factor 1.25 does 1.25 reference GPU-seconds per GPU per second.
- **Slot**: 15 minutes (`slot_seconds: 900` in `policy.yaml`). Slot 0 is 00:00, slot 95 is 23:45.
- **Tariffs and energy** are per actual GPU-hour at a site, in fictitious euros and kWh.

## Rules for this folder

1. **Fictitious only.** No real organisation's capacity, usage, cost or data. The names say "fictief" for a reason.
2. **Ids are stable.** Code, tests and the generated LiteLLM configs refer to organisation, site, data class and tier ids. Add new ones rather than renaming.
3. **Regenerate derived files** after changing `network.yaml` or `policy.yaml`: `python -m inferentienet.demand` and `python -m inferentienet.litellm_config` in `tooling/`.

## Validate locally

```bash
cd tooling
pip install -e .[dev]
pytest -v
```
