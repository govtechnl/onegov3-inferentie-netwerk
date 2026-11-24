# Scenarios

Six demo scenarios in [`data/scenarios.yaml`](../data/scenarios.yaml). Each starts from the simulated working day and applies overlays. All numbers are fictitious.

| Scenario | What happens | What it shows |
|---|---|---|
| `werkdag` | A normal weekday: office peaks, batch work in the evening and at night. The municipalities lack capacity and have no medium-size model of their own. | Everyday federation: small organisations lean on larger ones; cheap night capacity at the research site is used for batch work. |
| `piek-uitvoering` | The executive agency gets 2.5 times its usual interactive demand from 08:00 to 20:00. Half of it is `bijzonder` and may not leave the agency. | The limits of sharing: data that must stay home stays home. Coordination protects the partners, at the cost of the agency's own delay. |
| `handhaving` | The province runs a time-critical enforcement analysis from 10:00 to 12:00 with a large model it does not have, on confidential data. | Priority and the solidarity reserve: critical work gets through, even at a busy partner. |
| `netcongestie` | The agency's site loses half its power from 16:00 to 21:00 while its staff are still working. | Capacity that changes during the day, and how the network absorbs it. |
| `storing-ministerie` | The ministry's site is down from 09:00 to 13:00. | Resilience: spreading over several locations, and deferral when partners are busy. |
| `drukke-dag` | Peak at the agency, enforcement at the province and grid congestion, all on one day. | The clearest comparison of naive and coordinated routing. |

## Results with the starter data (v0.1)

From `python -m inferentienet.simulate --scenario <id> --compare`. These numbers change as soon as you change `data/`; they are here so you can check that your setup works and to start the discussion, not as findings about real organisations.

| Scenario | Mode | Mean delay (s) | Work within norm | Work run elsewhere | Own users within norm at min-rc1 / uvo-rc1 / prov-dc1 | Paid outside government (EUR) |
|---|---|---|---|---|---|---|
| `werkdag` | naive | 146 | 100% | 21% | 100% / 100% / 100% | 16.93 |
| `werkdag` | coordinated | 132 | 100% | 17% | 100% / 100% / 100% | 29.66 |
| `piek-uitvoering` | naive | 450 | 60% | 49% | 98% / 35% / 97% | 239.46 |
| `piek-uitvoering` | coordinated | 4099 | 52% | 23% | 100% / 7% / 100% | 142.78 |
| `handhaving` | naive | 145 | 100% | 21% | 100% / 100% / 100% | 16.93 |
| `handhaving` | coordinated | 131 | 100% | 17% | 100% / 100% / 100% | 29.66 |
| `netcongestie` | naive | 643 | 100% | 23% | 100% / 100% / 100% | 16.93 |
| `netcongestie` | coordinated | 223 | 99% | 19% | 100% / 98% / 100% | 31.10 |
| `storing-ministerie` | naive | 147 | 99% | 28% | 100% / 99% / 100% | 17.37 |
| `storing-ministerie` | coordinated | 133 | 99% | 22% | 100% / 98% / 100% | 33.10 |
| `drukke-dag` | naive | 1273 | 53% | 52% | 90% / 17% / 91% | 258.40 |
| `drukke-dag` | coordinated | 6576 | 52% | 24% | 100% / 7% / 100% | 142.78 |

Reading guide:

- On a normal day both modes work; coordination moves less work around.
- In the peak scenarios, naive routing spreads the peak over the partners: their own users notice it, the agency less so. Coordinated routing protects the partners and leaves the peak largely with the agency.
- With grid congestion, coordinated routing also gives the lower mean delay in this setup. Finding out why, with `--out` and the decisions file, is a good first exercise.

## Add your own scenario

Add an entry to `data/scenarios.yaml` with overlays of type `demand_multiplier`, `extra_workload` or `availability` (see the schema in [`data/schemas/scenarios.schema.json`](../data/schemas/scenarios.schema.json)). `pytest` checks that every scenario runs.
