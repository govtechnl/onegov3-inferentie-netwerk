# Start Here (Hackathon Teams)

If you are starting the challenge now, follow this order.

## 1) Understand the scope (10 min)

- Read [CHALLENGE.md](CHALLENGE.md).
- Skim [docs/judging-criteria.md](docs/judging-criteria.md). Every Must is blocking, and there are Musts on both the technical and the legal-administrative side.
- Read [docs/architecture.md](docs/architecture.md): what a federated gateway model is, and how the starter implements one.

## 2) Pick your angle (10 min)

All teams need a routing concept, an explicit allocation and settlement mechanism and a named legal vehicle. Choose where you go deepest:

- **Approach A, federated gateway model:** internal and external routing between organisations. Start with [docs/routing-criteria.md](docs/routing-criteria.md), the mock gateways in [tooling/](tooling/) and the LiteLLM configs in [gateways/litellm/](gateways/litellm/).
- **Approach B, market mechanism:** who gets priority under scarcity, and how usage is settled against capacity supplied. Start with [docs/market-and-settlement.md](docs/market-and-settlement.md) and the market mock API.
- **Coordination:** how do you stop everyone from chasing the fastest route and overloading the partner that helps? Start with [docs/coordination.md](docs/coordination.md) and `python -m inferentienet.simulate --scenario drukke-dag --compare`.

Make sure your team has at least one person who thinks about the legal and governance side. Government lawyers walk around during the hackathon; see [docs/legal-context.md](docs/legal-context.md).

## 3) Set up (10 min)

Fork this repository, then:

```bash
cd tooling
python -m venv .venv
source .venv/bin/activate        # Windows: .\.venv\Scripts\Activate.ps1
pip install -e .[dev]
pytest -v
```

Using another language? Fine. Keep the data files in `data/` as your input, or replace them with your own simulated data, and make sure your rules are testable.

## 4) Make one decision work end-to-end (first hours)

- Route one request and read the explanation:
  `python -m inferentienet.router --org gemeenten --data-class vertrouwelijk --task chat --load uvo-rc1=0.95`
- Change one rule in [data/policy.yaml](data/policy.yaml), for example `max_utilisation` or `min_gain`, and run it again. Did the outcome change the way you expected? Run `pytest` to see which tests notice.
- Start the four mock gateways and send a request over HTTP: `python -m inferentienet.gateway --all`, then see [tooling/README.md](tooling/README.md#mock-gateways) for a `curl` example.

## 5) Scale out and demo

- Replay a day: `python -m inferentienet.simulate --scenario drukke-dag --compare`. See [docs/scenarios.md](docs/scenarios.md) for what each scenario shows.
- Add your own allocation or settlement rule, and show its effect on a scenario.
- Write down the legal or administrative vehicle you would need, and why. Ask the lawyers.

## 6) Keep your submission valid

- Routing, priority and settlement rules are explicit and testable; no decision hidden in a prompt.
- Label clearly what is simulated, in the demo and in the pitch.
- Code and rules open source; put your work in `submissions/<team-name>/`.
- No real requests, personal data, internal capacity figures or credentials.
- Keep your repository public with an open source licence, and submit on [Alkemio](https://alkem.io/onegov-hackathon) before **Thursday 10 December, 14:00**. A Pull Request here is optional.
