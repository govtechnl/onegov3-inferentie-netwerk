# Routing criteria: what decides where a request goes (M2)

Must criterion M2 asks teams to show **on which criteria a request is routed, and which data are needed for that from both the consumer and the provider**. This page lists what the starter uses. Treat it as a starting point: add, remove or replace criteria, as long as you can say where each piece of data comes from.

## Data the consumer sends with every request

| Data | Example | Why it is needed | In the starter |
|---|---|---|---|
| Requesting organisation | `gemeenten` | Determines the relation with every site: own, federation, research or commercial | The gateway's own organisation; not taken from the client |
| Data class | `vertrouwelijk` | Hard rule: where data may go at all | Header `X-Data-Class`, **required** (fail closed) |
| Tier (urgency) | `kritiek`, `interactief`, `batch` | Priority under scarcity, norm for delay, price multiplier | Header `X-Tier`, default `interactief` |
| Task | `samenvatten` | Picks a model class that fits the task | Header `X-Task`, default `chat` |
| Size | input and output tokens | Work estimate, model choice for long documents | Estimated from the messages and `max_tokens` |
| Model (optional) | `middel` or `nl-middel-32b` | When the client knows what it needs | `model` field, `auto` lets the rules decide |

## Data every provider publishes

| Data | Example | Why it is needed | In the starter |
|---|---|---|---|
| Models hosted | `nl-klein-8b`, `nl-middel-32b` | Can this site run the task at all? | `data/network.yaml` |
| Capacity | 12 GPUs x speed 1.25 | How much work fits in a 15-minute slot | `data/network.yaml` |
| Availability windows | research site only at night; grid congestion 16:00-21:00 | Capacity changes during the day | `data/network.yaml`, scenario overlays |
| Current load | 85% of this slot, of which 10% for others | Expected delay, receiving protection | `GET /federation/v1/status` |
| Acceptance rules | accepts `openbaar`, `intern` from others; only `batch` | The provider's own decision on what it takes | `accepts_from_others` in `data/network.yaml` |
| Maximum share for others | 25% of capacity | Protects the provider's own users | `max_external_share` |
| Properties | EU jurisdiction, zero data retention, no training | Conditions for commercial use of some data classes | `properties` |
| Tariff and energy | EUR 2.10 per GPU-hour, 1.0 kWh per GPU-hour | Cost comparison and settlement | `data/network.yaml` (fictitious) |

## Shared rules all members agree on

In `data/policy.yaml`:

- **Data classes** and the relations they may go to. In the starter: `openbaar` and `intern` may go anywhere (commercial only with EU jurisdiction and zero data retention, and for `intern` also no training on the data), `vertrouwelijk` stays within the federation of government organisations, `bijzonder` never leaves its own organisation.
- **Tiers** with a priority, an objective (time or cost), a norm for delay and a price multiplier. `kritiek` also has a solidarity reserve: 10% of every site that other members may use for critical work, even when that site is busy.
- **Task-to-model rules**, first match wins. Long summaries (more than 8,000 input tokens per request) go to a medium-size model, short ones to a small model.
- **Coordination rules**: prefer local, minimum gain, receiving protection and a switching toll. See [coordination.md](coordination.md).

These classes and numbers are a simplification for the hackathon, not an official classification scheme. Mapping them to BIO2, the GDPR/AVG and fiscal secrecy is part of the challenge.

## The decision, step by step

[`router.py`](../tooling/inferentienet/router.py) takes these steps for every request. Each step is written to the decision's explanation.

1. **Model class.** From the request, or from the first matching task rule.
2. **Hard rules per site.** A site is excluded when it does not host that model class, when the data class may not go to that relation, when a commercial site lacks a required property, when the site does not accept this data class or tier from others, or when it has no capacity in this slot. These rules are never traded off.
3. **Estimates per remaining site.** Expected delay (work already ahead of this tier, plus this request, beyond what fits in the slot, plus transfer overhead), cost (GPU-hours x tariff x tier multiplier), utilisation and share for others after placement.
4. **Coordinated mode only:** receiving protection (skip sites that would get too busy or exceed their share for others, unless critical work fits in the solidarity reserve) and a switching toll on remote sites.
5. **Choice.**
   - Time tiers (`kritiek`, `interactief`): stay at the own site when it meets the norm. Otherwise consider sites that save at least the minimum gain after the toll; pick the cheapest one that meets the norm, or else the fastest.
   - Cost tier (`batch`): pick the cheapest site that meets the deadline; move only when it is at least 20% cheaper than the own site, or when the own site cannot meet the deadline.
6. **Outcome.** `lokaal`, `federatie` or `extern` with a site; `uitgesteld` (deferred to the next slot) when every allowed site is protected; `geweigerd` when no site may run the request at all.

Run `python -m inferentienet.router --help` to try combinations, or `--json` to see all candidates with their numbers.
