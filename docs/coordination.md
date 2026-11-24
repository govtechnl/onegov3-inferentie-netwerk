# Coordination: when everyone takes the fastest route

The brief warns, citing recent research, that when every organisation independently picks the "fastest route", this can come at the expense of the local users at the receiving party and of the stability of the network. Teams show how their model arranges coordination: central, federated or hybrid.

## What the research says

[FAIR-Compute: A Roadmap for Fair and Efficient Allocation of Federated Digital Research Infrastructure](https://arxiv.org/abs/2607.28290) (arXiv 2607.28290, July 2026) studies shared research computing. In short, as relevant for this challenge:

- Unmanaged federation can minimise average delay while concentrating load, and potentially harm, on the receiving system. The authors compare this with Braess's paradox from road-traffic economics.
- Their recommendation (FAIRC-5) is coordinated placement through a federation broker, with **minimum-gain thresholds**, **receiving-system utilisation protection** and **switching-cost tolls**, so that a job moves only when the benefit is clear and the receiving system's local users are protected.
- They are candid that on aggregate metrics the naive approach currently looks best in their simulations: the case for coordination rests on protecting local service and stability, not on a lower average delay.

Read the paper itself for the details and limitations; this summary is ours.

## The three rules in the starter

All three live in `coordination` in [`data/policy.yaml`](../data/policy.yaml). `mode: naive` switches them off; `mode: coordinated` switches them on.

| Rule | Setting | Effect |
|---|---|---|
| Prefer local | `prefer_local: true` | A time-sensitive request stays at its own site as long as that site meets the norm of its tier. |
| Minimum gain | `min_gain: {seconds: 30, ratio: 0.20}` | A request only moves when it saves at least 30 seconds and at least 20% of the delay at home, after the toll. Batch work only moves when it is at least 20% cheaper. |
| Receiving protection | `receiving_protection: {max_utilisation: 0.85}` plus `max_external_share` per site | A site does not get work from others when it would become more than 85% busy, or when work for others would exceed its own maximum share. |
| Switching toll | `switching_toll: {fixed_s: 5, runtime_fraction: 0.10}` | Every move is counted as 5 seconds plus 10% of the processing time slower. This is a policy weight, not a real delay. |
| Solidarity reserve | `receiving_reserve_share: 0.10` on tier `kritiek` | Critical work may always use 10% of another member's site, even when it is busy. |
| Defer instead of push | `defer_when_no_capacity: true` | When every allowed site is protected, the request waits for the next 15-minute slot instead of being pushed onto a busy partner. |

## See the trade-off yourself

```bash
cd tooling
python -m inferentienet.simulate --scenario drukke-dag --compare
```

With the starter's data (v0.1), the busy-day scenario gives roughly this picture (see [scenarios.md](scenarios.md) for all scenarios):

| | Naive | Coordinated |
|---|---|---|
| Work run elsewhere | 52% | 24% |
| Own users within norm at the ministry site | 90% | 100% |
| Own users within norm at the province site | 91% | 100% |
| Own users within norm at the overloaded agency | 17% | 7% |
| Mean delay, all work | 1273 s | 6576 s |

So the same pattern as in the paper: coordination protects the partners that help out, and the organisation with the peak carries more of its own peak. Neither column is "the answer". That is exactly the design question.

## Questions for teams

- Who carries the cost of a peak: the organisation that has it, or the federation as a whole? How does your settlement model reflect that?
- Should the thresholds be the same for every member, or depend on what a member contributes?
- Is a solidarity reserve for critical work enough, or should there be an emergency mode in which receiving protection is relaxed? Who may switch it on?
- Central broker, federated rules or hybrid: what does each mean for governance, for trust and for the legal vehicle?
- What happens when the published status is stale? (The mock gateways retry with the next candidate when a receiver refuses.)
