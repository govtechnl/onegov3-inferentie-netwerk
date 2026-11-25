# Contributing

Thanks for your interest in the **OneGov #3 | Overheid Inferentie Netwerk** challenge repository.

This repo is maintained by **GovTechNL** for challenge 1 of the hackathon on **9-10 December 2026** at The Hague Tech. Contributions are welcome from organisers, mentors, challenge owners, participating teams and the wider community.

## Two contribution flows

### 1. Hackathon teams: build in your fork, submit on Alkemio

This is the primary flow during the hackathon.

1. **Fork** this repository to your team's GitHub account (or start your own repository) and clone it.
2. Build your prototype and rules in your fork. Put everything team-specific under `submissions/<team-name>/` (see [submissions/README.md](submissions/README.md)).
3. Keep your repository **public**, under the licences below.
4. **Submit on [Alkemio](https://alkem.io/onegov-hackathon) before Thursday 10 December, 14:00**, with a link to your repository. See [EVENT.md](EVENT.md#submission).
5. A Pull Request into this repository is welcome but optional. If you open one, use the [pull request template](.github/pull_request_template.md).

### 2. Improving the starter repo

- **Sharpen the simulated data** in [`data/`](data/) (keep it fictitious).
- **Sharpen documentation** under [`docs/`](docs/).
- **Improve the tooling** under [`tooling/`](tooling/).
- **Report issues** using the [issue templates](.github/ISSUE_TEMPLATE/).

## Ground rules

1. **Explicit, testable rules.** Routing, priority and settlement decisions live in code or configuration that can be read and tested without the interface. No decision hidden in a prompt.
2. **Label what is simulated.** In the code, the demo and the pitch. A mock is fine; an unlabelled mock is not.
3. **No real data.** Do not commit real requests, personal data, internal documents, real capacity or cost figures of any organisation, or credentials and API keys. The organisations in `data/` are fictitious; keep them that way.
4. **Data never leaves its column by accident.** If your prototype forwards requests, it refuses requests without a data classification (fail closed).
5. **Open source.** All submitted code and rules are released under the licences below.
6. **Language.** Documentation in this repo is primarily English. Identifiers for data classes, tiers and roles are Dutch, because they come from the Dutch brief. Your pitch and explanation may be in Dutch.

## Development workflow

```bash
cd tooling
python -m venv .venv
source .venv/bin/activate        # Windows: .\.venv\Scripts\Activate.ps1
pip install -e .[dev]
ruff check .
pytest -v
```

CI ([`.github/workflows/validate.yml`](.github/workflows/validate.yml)) runs lint, schema checks and tests on every push and PR. Make sure they pass locally before opening a PR. If you change `data/network.yaml` or `data/policy.yaml`, regenerate the derived files:

```bash
python -m inferentienet.demand            # data/demand/werkdag.csv
python -m inferentienet.litellm_config    # gateways/litellm/*.yaml
```

## Pull requests

- Keep PRs focused, one logical change per PR (a team's hackathon PR is the exception).
- Update the README, data and docs together when behaviour changes.
- Reference the related issue if there is one.

## Code of Conduct

By participating you agree to the [Code of Conduct](CODE_OF_CONDUCT.md) (Contributor Covenant 2.1), including the section on **handling data, capacity information and credentials**.

## Licensing of contributions

This is the **canonical licensing rule** for the repository. All other documents refer back here.

- This **starter repository** is licensed under **Apache-2.0** for code (see [LICENSE](LICENSE)) and **CC BY 4.0** for data, documentation, configuration and challenge text (see [LICENSE-DATA](LICENSE-DATA)).
- **Hackathon team submissions** must be open source under an **OSI-approved licence** for code (Apache-2.0, MIT, EUPL-1.2 or another OSI-approved licence) and an open licence for rules, data and documentation (CC BY 4.0 recommended; CC0 also accepted).
- Code contributed *into this starter repo* is licensed under Apache-2.0; data and documentation under CC BY 4.0.
- Laws, reports and third-party data sets referenced in the docs keep their own terms. Link to them; do not copy them into the repo.

By submitting a contribution you confirm that you have the right to license it under these terms.
