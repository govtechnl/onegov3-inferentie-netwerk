# Market and settlement: priority and paying for capacity (approach B, M4)

Must criterion M4 asks for an explicit allocation and settlement mechanism for scarce capacity: **who gets priority, and how usage is charged or settled against capacity supplied, for both the using and the providing party**. A worked-out design suffices. The starter offers two building blocks.

## 1. Fixed tariffs with settlement against capacity supplied (in the simulator)

[`settlement.py`](../tooling/inferentienet/settlement.py) keeps a ledger of every placement outside the requesting organisation:

- amount = GPU-hours on that site x the site's tariff x the price multiplier of the tier (`kritiek` 1.5, `interactief` 1.0, `batch` 0.6, all fictitious);
- energy = GPU-hours x the site's kWh per GPU-hour, for reporting;
- per organisation: capacity **supplied** to other members and **used** from other members, in GPU-hours and euros, plus what was bought from research or commercial sites.

The net position (supplied minus used) is what makes "settlement against capacity supplied" concrete: an organisation that helps out at someone else's peak builds up a credit, in GPU-hours or in euros. The simulator prints it at the end of every run, and `--out results/` writes the full ledger.

## 2. A market mock API with priority tiers, bids and offers

[`market.py`](../tooling/inferentienet/market.py) and [`market_api.py`](../tooling/inferentienet/market_api.py), described in [api/market-mock.openapi.yaml](api/market-mock.openapi.yaml).

```bash
cd tooling
python -m inferentienet.market_api --port 8200

curl -s localhost:8200/offers -H 'Content-Type: application/json' \
  -d '{"site": "uvo-rc1", "slot": 40, "gpu_hours": 2, "min_price_eur": 2.0}'
curl -s localhost:8200/bids -H 'Content-Type: application/json' \
  -d '{"org": "gemeenten", "slot": 40, "tier": "interactief", "data_class": "intern", "model_class": "middel", "gpu_hours": 1.5, "max_price_eur": 3.0}'
curl -s localhost:8200/clear -H 'Content-Type: application/json' -d '{"slot": 40}'
curl -s localhost:8200/settlement
```

Matching rules, all explicit:

1. Bids are matched in **tier order** first (`kritiek` before `interactief` before `batch`), then by highest maximum price, then first come first served. Public priority beats willingness to pay.
2. Offers are used cheapest first.
3. A bid only matches an offer that the routing rules would also allow: same data-class rules, provider acceptance and model class. An organisation never buys from itself.
4. Pricing, set with `--pricing`: `uniform` (everyone pays the highest accepted offer price, capped at their own maximum), `pay_as_bid` or `pay_as_offer`.

## Where the inspiration comes from, and what is simplified

The brief points to congestion management in the electricity market: categories, a capacity limitation contract, and GOPACS, the platform through which Dutch grid operators solve congestion with flexibility offered by market parties (see the public explanation at [gopacs.eu](https://www.gopacs.eu)). The parallels that are useful here:

- capacity is scarce at a place and a time, not in general;
- parties can offer flexibility (free capacity) or ask for it, per time block;
- some users can agree in advance to use less at peak times in exchange for a fee, the idea behind a capacity limitation contract.

The mock is **not** a model of GOPACS or of any real market. It has one location per offer, no network topology, no grid constraints, no fees and no bidding strategy. It also has no notion of public procurement law, which matters as soon as euros change hands between public bodies; see [legal-context.md](legal-context.md).

## Ideas for teams

- Settle in kind: capacity credits that can only be spent on capacity, instead of euros.
- A token-based tariff (bonus C2): price per 1,000 input and output tokens per model class, derived from the GPU-seconds in `data/network.yaml`.
- Let the simulator use market prices instead of fixed tariffs, for example by clearing each 15-minute slot.
- A reservation or capacity limitation contract: a member agrees in advance to free up capacity at peaks, and gets a fixed fee for being available.
- Who sets the tariffs, and who checks them? That is part of your governance sketch (S2).
