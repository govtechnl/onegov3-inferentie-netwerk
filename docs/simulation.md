# Simulation: how the day simulator works

[`simulate.py`](../tooling/inferentienet/simulate.py) replays one day of simulated demand on the fictitious network, 15 minutes at a time, and routes every piece of work with the same router the mock gateways use.

```bash
cd tooling
python -m inferentienet.simulate --scenario werkdag                    # one run, coordinated rules
python -m inferentienet.simulate --scenario drukke-dag --mode naive    # one run, naive rules
python -m inferentienet.simulate --scenario drukke-dag --compare       # both, side by side
python -m inferentienet.simulate --scenario netcongestie --out results # CSVs for your own charts
```

## The model, in six rules

1. **Capacity** is counted in reference GPU-seconds per 15-minute slot: GPUs x speed factor x available share x 900. A faster site does more work per GPU.
2. **Demand** comes from [`data/demand/werkdag.csv`](../data/demand/werkdag.csv), changed by the scenario's overlays. Every row is a workload: a bundle of interactive requests in one slot, or one batch or critical job.
3. **Chunks.** Every workload is split into chunks of at most 300 reference GPU-seconds (`--chunk`). Each chunk is routed separately, with the queue state of that moment.
4. **Queues.** Each site serves its queue in priority order (`kritiek`, `interactief`, `batch`), first come first served within a tier. Work that does not fit carries over to the next slot.
5. **Delay** of a chunk is its finish time minus the end of the slot in which it arrived, plus a fixed transfer overhead when it ran elsewhere. Interactive work spread over its own slot therefore counts as on time.
6. **Deferral.** A chunk that no site may take is routed again in the next slot. After the day, the simulator keeps serving (no new demand) for up to 8 hours so that late work can finish.

## Output

The summary shows, per organisation and tier, the mean and 95th percentile delay, the share of work within the norm of its tier, and where the work ran (`lokaal`, `federatie`, `extern`). Per site it shows utilisation, the share of work done for others, and how the site's **own users** (critical and interactive work) fared. At the end it shows the settlement per organisation.

With `--out DIR` you get `decisions.csv` (one row per chunk, with the last reasoning step), `sites.csv` (per site per slot), `ledger.csv` and `summary.json`.

## What it leaves out

The simulator is a teaching tool, not a capacity planner.

- No real GPU behaviour: no batching effects, memory limits, model loading times or cold starts.
- Work in a slot is treated as a fluid: a site processes its queue at its full rate.
- Queued work is never re-routed; a chunk stays where it was placed.
- Research and commercial sites are modelled like the others; real providers have their own queues and limits.
- Every number in `data/` is invented.

Improving any of these is a fine contribution, as long as you say what you changed.
