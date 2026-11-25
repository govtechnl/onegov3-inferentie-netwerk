# OneGov #3 | Overheid Inferentie Netwerk

> *Shared AI compute between government organisations: route every AI request to free capacity, without sensitive data leaving its own organisation.*

This repository hosts the challenge brief, supporting documents, simulated starter data and optional tooling for challenge 1 of **OneGov #3**, part of the OneGov Hackathon Series hosted by [GovTechNL](https://govtechnl.nl). The question was put forward by Guido Scheuerman (Provincie Zuid-Holland / GovTechNL network / sAIdkick) and concerns a collaboration between Minbzk, the Belastingdienst, Provincie Zuid-Holland and municipalities (through VNG).

- **Theme:** Digital autonomy and sovereignty
- **Date:** 9-10 December 2026
- **Location:** The Hague Tech, Den Haag
- **Challenge owners:** Guido Scheuerman (PZH, main challenge owner), Sahin Özaltun (PZH), Melior Hoekstra (Minbzk), Lennart Marijs (Minbzk), Lotte Schipper (Minbzk), Bas Kooistra (VNG), Bas Nijhuis (Belastingdienst)
- **Tech partner:** [GreenPT](https://greenpt.nl/)
- **Community and team registration:** [alkem.io/onegov-hackathon](https://alkem.io/onegov-hackathon)
- **Contact:** [hack@govtechnl.nl](mailto:hack@govtechnl.nl)
- **Submission deadline:** Thursday 10 December 2026, 14:00, on [Alkemio](https://alkem.io/onegov-hackathon)
- **Programme, prizes, judging and help:** [EVENT.md](EVENT.md)
- **Organised by:** GovTechNL with Digicampus, The Hague Tech, VNG Realisatie, Provincie Zuid-Holland, Platform AI & Overheid and Gemeente Den Haag

## The challenge in one paragraph

Every organisation now sizes its AI compute for its own peak: over-capacity and shortage at the same time, "shortage by design". GPUs are scarce, and sensitive data cannot simply go to a commercial provider. **How do we build a prototype of a government inference network in which a ministry, an executive agency, a province and municipalities share AI compute at peak moments, use an optimal mix of capacity inside and outside government, and pick a model that fits each task, without sensitive data leaving its own organisation and with every owner of data and task keeping its own responsibility?**

The full brief is in [CHALLENGE.md](CHALLENGE.md). New teams start with [START_HERE.md](START_HERE.md).

## What's in here

| Path | Purpose | Status |
|---|---|---|
| [CHALLENGE.md](CHALLENGE.md) | Full challenge brief (English working translation of the Dutch original) | Available |
| [resources/OneGov3_Challenge_Brief_Overheid_Inferentie_Netwerk.pdf](resources/OneGov3_Challenge_Brief_Overheid_Inferentie_Netwerk.pdf) | The Dutch challenge brief (authoritative) | Available |
| [START_HERE.md](START_HERE.md) | Step-by-step start for teams | Available |
| [docs/](docs/) | Architecture, routing criteria, coordination, market and settlement, legal context, simulation, scenarios, judging criteria, precedents, glossary | Available |
| [data/network.yaml](data/network.yaml) | Four fictitious organisations (the four roles in the brief), their sites, GPUs, models, tariffs, plus a research and a commercial site | Available (simulated) |
| [data/policy.yaml](data/policy.yaml) | The rules: data classes, priority tiers, task-to-model rules, coordination rules | Available, change it |
| [data/scenarios.yaml](data/scenarios.yaml) | Six demo scenarios: normal day, peak, enforcement, grid congestion, outage, everything at once | Available (simulated) |
| [data/demand/](data/demand/) | Simulated demand for one working day, four fictitious organisations, per 15 minutes | Available (simulated) |
| [tooling/](tooling/) | Optional Python starter: explainable router, day simulator, settlement, market mock API, federated mock gateways | Available |
| [gateways/litellm/](gateways/litellm/) | A LiteLLM proxy config per organisation, with mock responses and data-class tags | Available |
| [docs/api/](docs/api/) | OpenAPI description of the market mock API | Available |
| [submissions/](submissions/) | Where your team's work goes if you build in a fork of this repository | Empty |
| [resources/](resources/) | Source material: the Dutch brief and links to public GPU traces | Available |

**Everything in this repository is simulated or public.** No real requests, data or capacity figures of the organisations involved pass through it. The four organisations in `data/` are fictitious stand-ins for the four roles in the brief.

## Quick start

```bash
cd tooling
python -m venv .venv
source .venv/bin/activate        # Windows: .\.venv\Scripts\Activate.ps1
pip install -e .[dev]
pytest -v

# Why does this request go where it goes? (a municipality without its own medium-size model,
# confidential data, while the executive agency is at 95%)
python -m inferentienet.router --org gemeenten --data-class vertrouwelijk --task chat --load uvo-rc1=0.95

# Replay a busy day and compare naive routing with coordinated routing
# (coordination protects the partners at the cost of the agency's own delay, see docs/scenarios.md)
python -m inferentienet.simulate --scenario drukke-dag --compare

# Four federated mock gateways (OpenAI-compatible) and a scripted demo
python examples/federation_demo.py

# The market mechanism mock API (approach B)
python -m inferentienet.market_api --port 8200
```

The tooling is optional. **Teams are free to choose any language and approach**, as long as routing, priority and settlement rules are explicit, testable and explained.

## Important to know

- A working prototype does not need to connect real organisations. A simulated environment with realistic scenarios is a valid starting point; label clearly what is simulated.
- The challenge has a technical and a legal-administrative side. Government lawyers walk around during the hackathon to think along. See [docs/legal-context.md](docs/legal-context.md).
- Use an LLM where it helps, but do not let a language model make routing, priority or settlement decisions. Those must be explicit rules.
- Do not commit real requests, personal data, internal capacity figures or credentials. Keep it that way in your submission.

## Licensing

See [CONTRIBUTING.md](CONTRIBUTING.md#licensing-of-contributions) for the canonical rule. In short:

- This **starter repo** ships under **Apache-2.0** (code, see [LICENSE](LICENSE)) and **CC BY 4.0** (data, docs, challenge text, see [LICENSE-DATA](LICENSE-DATA)).
- **Team submissions** must be open source under an **OSI-approved licence** for code (Apache-2.0, MIT, EUPL-1.2, ...) and an open licence (CC BY 4.0 recommended, CC0 accepted) for rules, data and documentation.
- Laws, reports and third-party data sets referenced in the docs keep their own terms. This repo links to them; it does not redistribute them.

## Contributing

Issues and pull requests are welcome, see [CONTRIBUTING.md](CONTRIBUTING.md). Team submissions go through [Alkemio](https://alkem.io/onegov-hackathon); a Pull Request from your team is welcome but optional.

## Submission

Submit on [Alkemio](https://alkem.io/onegov-hackathon) before **Thursday 10 December 2026, 14:00**, with a link to your public repository (your fork or your own), a short explanation of your approach, assumptions and limitations, and your pitch deck. A Pull Request into this repository is optional. See [CHALLENGE.md](CHALLENGE.md#submission) and [EVENT.md](EVENT.md#submission).

## Disclaimer

The prototypes and designs produced during this hackathon are published as open source. The challenge is an innovation exercise: outcomes are not legal advice and not a decision or position of the organisations involved.
