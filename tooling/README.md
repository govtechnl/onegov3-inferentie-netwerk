# Tooling (optional Python starter)

A small, deterministic starter for the federated inference network. Use it, extend it, or ignore it and build in any language you like. The only hard rules are that routing, priority and settlement rules are explicit and testable, and that what is simulated is labelled.

Requires Python 3.10 or newer. Runtime dependencies: `pyyaml` and `jsonschema`. The mock servers use only the standard library.

## Install

```bash
cd tooling
python -m venv .venv
source .venv/bin/activate        # Windows: .\.venv\Scripts\Activate.ps1
pip install -e .[dev]
pytest -v
```

## What is in here

| Path | What it does |
|---|---|
| `inferentienet/catalog.py` | Loads `data/*.yaml` and the demand CSV, and validates them against `data/schemas/` |
| `inferentienet/model.py` | Typed views on the network and the policy, plus cross-reference checks |
| `inferentienet/router.py` | The routing rules: hard rules, estimates, coordination, an explanation per decision. No AI, no hidden state |
| `inferentienet/simulate.py` | Replays a day of demand per 15-minute slot, naive or coordinated, with metrics per organisation and site |
| `inferentienet/settlement.py` | Ledger and net positions: capacity supplied and used, in GPU-hours and euros |
| `inferentienet/market.py`, `market_api.py` | Approach B: priority tiers, bids, offers, clearing and settlement, as a library and as a mock HTTP API |
| `inferentienet/gateway.py` | Approach A: one OpenAI-compatible mock gateway per organisation, with internal and external routing |
| `inferentienet/demand.py` | Generates `data/demand/werkdag.csv` (seeded, reproducible) |
| `inferentienet/litellm_config.py` | Generates the LiteLLM configs in `gateways/litellm/` |
| `examples/federation_demo.py` | Scripted demo: four gateways, a few requests, and why each went where it went |
| `tests/` | Schema checks, routing rules, simulator invariants, market rules, HTTP mocks |

## Router

```bash
python -m inferentienet.router --org gemeenten --data-class vertrouwelijk --task chat --load uvo-rc1=0.95
python -m inferentienet.router --org provincie --tier kritiek --data-class vertrouwelijk --task analyse --json
python -m inferentienet.router --org ministerie --tier batch --data-class openbaar --task samenvatten --hour 2
```

`--load SITE=SHARE` sets how busy a site already is (1.0 = a full 15-minute slot). `--mode naive` switches the coordination rules off.

## Simulator

```bash
python -m inferentienet.simulate --scenario werkdag
python -m inferentienet.simulate --scenario drukke-dag --compare
python -m inferentienet.simulate --scenario netcongestie --out results
```

See [docs/simulation.md](../docs/simulation.md) and [docs/scenarios.md](../docs/scenarios.md).

## Mock gateways

```bash
python -m inferentienet.gateway --all        # ministerie :8101, uitvoering :8102, provincie :8103, gemeenten :8104
```

In a second terminal:

```bash
# A municipality asks for a medium-size model with confidential data; it has none of its own.
curl -s -i localhost:8104/v1/chat/completions -H 'Content-Type: application/json' \
  -H 'X-Data-Class: vertrouwelijk' -H 'X-Tier: interactief' -H 'X-Task: chat' \
  -d '{"model": "auto", "messages": [{"role": "user", "content": "Vat dit dossier samen"}]}'

# Why did it go there? Use the X-Route-Decision header of the response.
curl -s localhost:8104/decisions/gemeenten-1

# Make the executive agency busy and ask again.
curl -s localhost:8102/admin/load -H 'Content-Type: application/json' -d '{"uvo-rc1": 0.95}'
```

| Endpoint | Purpose |
|---|---|
| `POST /v1/chat/completions` | Internal gateway (OpenAI-compatible). Headers: `X-Data-Class` (required), `X-Tier`, `X-Task`. `model`: `auto`, a model class or a model id |
| `GET /decisions/<id>` | The explanation of a routing decision |
| `GET /v1/models` | Model classes you can ask for |
| `POST /federation/v1/chat/completions` | External gateway, called by other members; re-checks its own rules |
| `GET /federation/v1/status` | Published load of the organisation's own sites |
| `POST /admin/load`, `GET /admin/state` | Demo controls: set how busy a site is, inspect the simulated state |

Or run the scripted demo: `python examples/federation_demo.py`.

## Market mock API

```bash
python -m inferentienet.market_api --port 8200 --pricing uniform
```

See [docs/market-and-settlement.md](../docs/market-and-settlement.md) and [docs/api/market-mock.openapi.yaml](../docs/api/market-mock.openapi.yaml).

## Regenerating derived files

After changing `data/network.yaml` or `data/policy.yaml`:

```bash
python -m inferentienet.demand            # data/demand/werkdag.csv
python -m inferentienet.litellm_config    # gateways/litellm/*.yaml
```

CI fails when they are out of date.
