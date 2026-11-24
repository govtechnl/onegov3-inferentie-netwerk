"""Replay a day of simulated demand on the federated network, one 15-minute slot at a time.

Model (deliberately simple, see docs/simulation.md):

* Capacity is counted in reference GPU-seconds per slot: gpus x speed_factor x available share x 900.
* Every workload in the demand file is split into chunks of at most ``chunk_s`` reference GPU-seconds.
  Each chunk is routed separately by the router, with the queue state of that moment.
* Each site serves its queue in priority order (kritiek, interactief, batch), first come first served
  within a tier. Work that does not fit in a slot carries over to the next slot.
* Delay of a chunk = finish time minus the end of the slot in which it arrived (work spread over its own
  slot counts as on time), plus a fixed transfer overhead when it ran elsewhere.
* Deferred chunks (no site may take them) are routed again in the next slot.

    python -m inferentienet.simulate --scenario drukke-dag --compare
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path

from . import catalog
from .model import Window, World, load_world
from .router import Request, SiteSnapshot, resolve_model_class, route
from .settlement import LedgerEntry, entry, net_positions

DAY_SLOTS = 96


@dataclass
class Chunk:
    seq: int
    chunk_id: str
    workload_id: str
    arrival_slot: int
    request: Request
    description: str = ""
    attempts: int = 0


@dataclass
class Job:
    seq: int
    chunk_id: str
    org: str
    tier: str
    priority: int
    site: str
    relation: str
    arrival_slot: int
    work_s: float
    remaining_s: float
    external: bool
    delay_s: float | None = None


@dataclass
class Record:
    chunk_id: str
    workload_id: str
    arrival_slot: int
    routed_slot: int
    org: str
    tier: str
    data_class: str
    task: str
    model_class: str
    outcome: str
    site: str
    model: str
    work_s: float
    est_delay_s: float
    realized_delay_s: float | None
    cost_eur: float
    deferrals: int
    reason: str


@dataclass
class SimResult:
    scenario: str
    mode: str
    records: list[Record]
    site_slots: list[dict]
    ledger: list[LedgerEntry]
    summary: dict = field(default_factory=dict)


def _hhmm(slot: int) -> str:
    return f"{slot // 4:02d}{(slot % 4) * 15:02d}"


def scenario_by_id(scenario_id: str) -> dict:
    scenarios = catalog.load("scenarios")["scenarios"]
    for scenario in scenarios:
        if scenario["id"] == scenario_id:
            return scenario
    known = ", ".join(s["id"] for s in scenarios)
    raise KeyError(f"unknown scenario {scenario_id!r} (known: {known})")


def apply_overlays(
    rows: list[dict], overlays: list[dict]
) -> tuple[list[dict], dict[str, tuple[Window, ...]]]:
    """Return the demand rows and extra availability windows for a scenario."""
    rows = [dict(r) for r in rows]
    windows: dict[str, list[Window]] = defaultdict(list)
    for overlay in overlays:
        start, end = overlay["start"] * 4, overlay["end"] * 4
        if overlay["type"] == "demand_multiplier":
            for row in rows:
                if row["org"] != overlay["org"] or not start <= row["slot"] < end:
                    continue
                if "tier" in overlay and row["tier"] != overlay["tier"]:
                    continue
                factor = overlay["factor"]
                row["requests"] = max(1, round(row["requests"] * factor))
                row["tokens_in"] = round(row["tokens_in"] * factor)
                row["tokens_out"] = round(row["tokens_out"] * factor)
                row["ref_gpu_seconds"] = round(row["ref_gpu_seconds"] * factor, 3)
        elif overlay["type"] == "extra_workload":
            for slot in range(start, end):
                n = overlay["requests_per_slot"]
                rows.append(
                    {
                        "slot": slot,
                        "time": f"{slot // 4:02d}:{(slot % 4) * 15:02d}",
                        "workload_id": f"{overlay['id']}-{_hhmm(slot)}",
                        "org": overlay["org"],
                        "tier": overlay["tier"],
                        "data_class": overlay["data_class"],
                        "task": overlay["task"],
                        "requests": n,
                        "tokens_in": n * overlay["tokens_in_per_request"],
                        "tokens_out": n * overlay["tokens_out_per_request"],
                        "ref_gpu_seconds": 0.0,
                        "description": overlay.get("description", ""),
                    }
                )
        elif overlay["type"] == "availability":
            windows[overlay["site"]].append(
                Window(overlay["start"], overlay["end"], overlay["share"], overlay.get("reason", ""))
            )
    return rows, {site: tuple(ws) for site, ws in windows.items()}


def make_chunks(rows: list[dict], world: World, chunk_s: float) -> dict[int, list[Chunk]]:
    """Split every workload into chunks of at most chunk_s reference GPU-seconds."""
    arrivals: dict[int, list[Chunk]] = defaultdict(list)
    seq = 0
    for row in sorted(rows, key=lambda r: (r["slot"], r["workload_id"])):
        base = Request(
            org=row["org"],
            tier=row["tier"],
            data_class=row["data_class"],
            task=row["task"],
            tokens_in=row["tokens_in"],
            tokens_out=row["tokens_out"],
            requests=row["requests"],
            id=row["workload_id"],
        )
        model_class, _ = resolve_model_class(base, world)
        work = world.network.default_model(model_class).ref_gpu_seconds(row["tokens_in"], row["tokens_out"])
        n = max(1, min(row["requests"], math.ceil(work / chunk_s)))
        for k in range(n):
            share_in = row["tokens_in"] // n + (1 if k < row["tokens_in"] % n else 0)
            share_out = row["tokens_out"] // n + (1 if k < row["tokens_out"] % n else 0)
            share_req = row["requests"] // n + (1 if k < row["requests"] % n else 0)
            chunk_id = row["workload_id"] if n == 1 else f"{row['workload_id']}#{k + 1}"
            request = Request(
                org=row["org"],
                tier=row["tier"],
                data_class=row["data_class"],
                task=row["task"],
                tokens_in=share_in,
                tokens_out=share_out,
                requests=max(1, share_req),
                model_class=model_class,
                id=chunk_id,
            )
            arrivals[row["slot"]].append(
                Chunk(seq, chunk_id, row["workload_id"], row["slot"], request, row["description"])
            )
            seq += 1
    return arrivals


def run(
    world: World,
    scenario_id: str,
    mode: str | None = None,
    chunk_s: float = 300.0,
    drain_slots: int = 32,
) -> SimResult:
    scenario = scenario_by_id(scenario_id)
    mode = mode or world.policy.coordination.mode
    rows, windows = apply_overlays(catalog.read_demand(Path(scenario["demand"])), scenario["overlays"])
    arrivals = make_chunks(rows, world, chunk_s)
    net, pol = world.network, world.policy
    slot_s = pol.slot_seconds

    queues: dict[str, list[Job]] = {site_id: [] for site_id in net.sites}
    pending: list[Chunk] = []
    records: list[Record] = []
    jobs_by_record: dict[int, Job] = {}
    site_slots: list[dict] = []
    ledger: list[LedgerEntry] = []

    for t in range(DAY_SLOTS + drain_slots):
        hour = (t % DAY_SLOTS) / 4
        snaps: dict[str, SiteSnapshot] = {}
        for site in net.sites.values():
            snap = SiteSnapshot(capacity_s=site.rate(hour, windows.get(site.id, ())) * slot_s)
            for job in queues[site.id]:
                snap.add(job.priority, job.remaining_s, job.external, job.tier)
            snaps[site.id] = snap

        todo = pending + (arrivals.get(t, []) if t < DAY_SLOTS else [])
        pending = []
        todo.sort(key=lambda c: (pol.tiers[c.request.tier].priority, c.arrival_slot, c.seq))
        for chunk in todo:
            decision = route(chunk.request, snaps, world, mode=mode)
            if decision.outcome == "uitgesteld":
                chunk.attempts += 1
                pending.append(chunk)
                continue
            record = Record(
                chunk_id=chunk.chunk_id,
                workload_id=chunk.workload_id,
                arrival_slot=chunk.arrival_slot,
                routed_slot=t,
                org=chunk.request.org,
                tier=chunk.request.tier,
                data_class=chunk.request.data_class,
                task=chunk.request.task,
                model_class=decision.model_class,
                outcome=decision.outcome,
                site=decision.site or "",
                model=decision.model or "",
                work_s=decision.work_s,
                est_delay_s=decision.est_delay_s,
                realized_delay_s=None,
                cost_eur=decision.cost_eur,
                deferrals=chunk.attempts,
                reason=decision.steps[-1],
            )
            records.append(record)
            if not decision.placed:
                continue
            tier = pol.tiers[chunk.request.tier]
            external = decision.relation != "eigen"
            job = Job(
                seq=chunk.seq,
                chunk_id=chunk.chunk_id,
                org=chunk.request.org,
                tier=tier.id,
                priority=tier.priority,
                site=decision.site,
                relation=decision.relation,
                arrival_slot=chunk.arrival_slot,
                work_s=decision.work_s,
                remaining_s=decision.work_s,
                external=external,
            )
            queues[decision.site].append(job)
            jobs_by_record[len(records) - 1] = job
            snaps[decision.site].add(tier.priority, decision.work_s, external, tier.id)
            if external:
                site = net.sites[decision.site]
                ledger.append(
                    entry(
                        t, chunk.chunk_id, chunk.request.org, site, decision.relation, tier, decision.work_s
                    )
                )

        for site in net.sites.values():
            capacity = snaps[site.id].capacity_s
            rate = capacity / slot_s if capacity else 0.0
            queue = sorted(queues[site.id], key=lambda j: (j.priority, j.arrival_slot, j.seq))
            used = external_used = 0.0
            for job in queue:
                if used >= capacity:
                    break
                served = min(job.remaining_s, capacity - used)
                used += served
                job.remaining_s -= served
                if job.external:
                    external_used += served
                if job.remaining_s <= 1e-9:
                    job.remaining_s = 0.0
                    finish = t * slot_s + used / rate
                    overhead = net.transfer_overhead_s.get(job.relation, 0.0) if job.external else 0.0
                    job.delay_s = max(0.0, finish - (job.arrival_slot + 1) * slot_s) + overhead
            queues[site.id] = [j for j in queue if j.remaining_s > 0]
            site_slots.append(
                {
                    "slot": t,
                    "site": site.id,
                    "capacity_s": round(capacity, 3),
                    "served_s": round(used, 3),
                    "external_served_s": round(external_used, 3),
                    "backlog_s": round(sum(j.remaining_s for j in queues[site.id]), 3),
                    "utilisation": round(used / capacity, 4) if capacity else None,
                }
            )
        if t >= DAY_SLOTS and not pending and not any(queues.values()):
            break

    for index, job in jobs_by_record.items():
        records[index].realized_delay_s = job.delay_s
    for chunk in pending:
        records.append(
            Record(
                chunk.chunk_id,
                chunk.workload_id,
                chunk.arrival_slot,
                -1,
                chunk.request.org,
                chunk.request.tier,
                chunk.request.data_class,
                chunk.request.task,
                chunk.request.model_class or "",
                "uitgesteld",
                "",
                "",
                0.0,
                0.0,
                None,
                0.0,
                chunk.attempts,
                "still deferred at the end of the simulation",
            )
        )
    result = SimResult(scenario_id, mode, records, site_slots, ledger)
    result.summary = summarise(result, world)
    return result


def _weighted_mean(pairs: list[tuple[float, float]]) -> float | None:
    total = sum(w for _, w in pairs)
    return sum(v * w for v, w in pairs) / total if total else None


def _p95(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, math.ceil(0.95 * len(ordered)) - 1)]


def summarise(result: SimResult, world: World) -> dict:
    pol, net = world.policy, world.network
    placed = [r for r in result.records if r.site]
    finished = [r for r in placed if r.realized_delay_s is not None]

    org_tier: dict[str, dict] = {}
    for org in net.organisations:
        for tier in pol.tiers.values():
            rs = [r for r in result.records if r.org == org and r.tier == tier.id]
            if not rs:
                continue
            done = [r for r in rs if r.site and r.realized_delay_s is not None]
            work = sum(r.work_s for r in rs if r.site)
            within = sum(r.work_s for r in done if r.realized_delay_s <= tier.max_delay_s)
            outcome_work = defaultdict(float)
            for r in rs:
                if r.site:
                    outcome_work[r.outcome] += r.work_s
            mean = _weighted_mean([(r.realized_delay_s, r.work_s) for r in done])
            p95 = _p95([r.realized_delay_s for r in done])
            org_tier[f"{org}/{tier.id}"] = {
                "chunks": len(rs),
                "gpu_hours_ref": round(work / 3600, 3),
                "mean_delay_s": round(mean, 1) if mean is not None else None,
                "p95_delay_s": round(p95, 1) if p95 is not None else None,
                "within_norm_share": round(within / work, 4) if work else None,
                "work_share": {k: round(v / work, 4) for k, v in sorted(outcome_work.items())}
                if work
                else {},
                "deferred_chunks": sum(1 for r in rs if r.deferrals > 0),
                "refused_chunks": sum(1 for r in rs if r.outcome == "geweigerd"),
                "unfinished_chunks": sum(
                    1 for r in rs if r.outcome == "uitgesteld" or (r.site and r.realized_delay_s is None)
                ),
            }

    sites: dict[str, dict] = {}
    for site in net.sites.values():
        slots = [s for s in result.site_slots if s["site"] == site.id]
        day = [s for s in slots if s["slot"] < DAY_SLOTS]
        capacity = sum(s["capacity_s"] for s in day)
        served_day = sum(s["served_s"] for s in day)
        served = sum(s["served_s"] for s in slots)
        external = sum(s["external_served_s"] for s in slots)
        # The site's own users in the time-sensitive tiers (kritiek, interactief): the people that
        # receiving protection is meant to protect.
        own = [
            r
            for r in finished
            if r.site == site.id and r.org == site.owner and pol.tiers[r.tier].objective == "time"
        ]
        own_mean = _weighted_mean([(r.realized_delay_s, r.work_s) for r in own])
        own_work = sum(r.work_s for r in own)
        own_within = sum(r.work_s for r in own if r.realized_delay_s <= pol.tiers[r.tier].max_delay_s)
        sites[site.id] = {
            "utilisation": round(served_day / capacity, 4) if capacity else None,
            "external_share": round(external / served, 4) if served else None,
            "own_users_mean_delay_s": round(own_mean, 1) if own_mean is not None else None,
            "own_users_within_norm_share": round(own_within / own_work, 4) if own_work else None,
            "peak_backlog_s": round(max((s["backlog_s"] for s in slots), default=0.0), 1),
        }

    total_work = sum(r.work_s for r in placed)
    migrated = [r for r in placed if r.outcome != "lokaal"]
    within_total = 0.0
    for r in finished:
        if r.realized_delay_s <= pol.tiers[r.tier].max_delay_s:
            within_total += r.work_s
    mean_all = _weighted_mean([(r.realized_delay_s, r.work_s) for r in finished])
    totals = {
        "chunks": len(result.records),
        "gpu_hours_ref": round(total_work / 3600, 3),
        "migrated_chunks": len(migrated),
        "migrated_work_share": round(sum(r.work_s for r in migrated) / total_work, 4) if total_work else 0.0,
        "mean_delay_s": round(mean_all, 1) if mean_all is not None else None,
        "within_norm_share": round(within_total / total_work, 4) if total_work else None,
        "deferred_chunks": sum(1 for r in result.records if r.deferrals > 0),
        "refused_chunks": sum(1 for r in result.records if r.outcome == "geweigerd"),
        "unfinished_chunks": sum(
            1 for r in result.records if r.outcome == "uitgesteld" or (r.site and r.realized_delay_s is None)
        ),
        "federation_eur": round(sum(e.amount_eur for e in result.ledger if e.relation == "federatie"), 2),
        "external_eur": round(sum(e.amount_eur for e in result.ledger if e.relation != "federatie"), 2),
    }
    return {
        "scenario": result.scenario,
        "mode": result.mode,
        "totals": totals,
        "org_tier": org_tier,
        "sites": sites,
        "settlement": net_positions(result.ledger, list(net.organisations)),
    }


def write_outputs(result: SimResult, out_dir: Path, suffix: str = "") -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / f"decisions{suffix}.csv").open("w", encoding="utf-8", newline="") as fh:
        fields = list(asdict(result.records[0]).keys()) if result.records else []
        writer = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for record in result.records:
            writer.writerow(asdict(record))
    with (out_dir / f"sites{suffix}.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(result.site_slots[0].keys()), lineterminator="\n")
        writer.writeheader()
        writer.writerows(result.site_slots)
    with (out_dir / f"ledger{suffix}.csv").open("w", encoding="utf-8", newline="") as fh:
        fields = list(LedgerEntry.__dataclass_fields__)
        writer = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for e in result.ledger:
            writer.writerow(e.to_dict())
    (out_dir / f"summary{suffix}.json").write_text(
        json.dumps(result.summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def _fmt(value, pattern: str = "{:.0f}") -> str:
    return "-" if value is None else pattern.format(value)


def print_summary(summary: dict) -> None:
    t = summary["totals"]
    print(f"Scenario '{summary['scenario']}', mode '{summary['mode']}'")
    print(
        f"  work {t['gpu_hours_ref']:.1f} ref GPU-h in {t['chunks']} chunks"
        f" | mean delay {_fmt(t['mean_delay_s'])} s"
        f" | within norm {_fmt(t['within_norm_share'], '{:.0%}')} | moved {t['migrated_work_share']:.0%}"
    )
    print(
        f"  deferred {t['deferred_chunks']} | refused {t['refused_chunks']}"
        f" | unfinished {t['unfinished_chunks']}"
        f" | federation EUR {t['federation_eur']:.2f} | external EUR {t['external_eur']:.2f}"
    )
    print("\n  org/tier                  mean s   p95 s  in norm  lokaal  federatie  extern")
    for key, v in summary["org_tier"].items():
        share = v["work_share"]
        print(
            f"  {key:24} {_fmt(v['mean_delay_s']):>7} {_fmt(v['p95_delay_s']):>7} "
            f"{_fmt(v['within_norm_share'], '{:.0%}'):>8} {share.get('lokaal', 0):>7.0%} "
            f"{share.get('federatie', 0):>10.0%} {share.get('extern', 0):>7.0%}"
        )
    print("\n  site           utilisation  external share  own users: mean delay s  in norm  peak backlog s")
    for key, v in summary["sites"].items():
        print(
            f"  {key:14} {_fmt(v['utilisation'], '{:.0%}'):>11} {_fmt(v['external_share'], '{:.0%}'):>15} "
            f"{_fmt(v['own_users_mean_delay_s']):>24} {_fmt(v['own_users_within_norm_share'], '{:.0%}'):>8}"
            f" {_fmt(v['peak_backlog_s']):>15}"
        )
    print("\n  settlement      supplied GPU-h  used GPU-h  receivable  payable  external   net EUR")
    for org, v in summary["settlement"].items():
        print(
            f"  {org:14} {v['supplied_gpu_hours']:>15.2f} {v['used_gpu_hours']:>11.2f}"
            f" {v['receivable_eur']:>11.2f} {v['payable_eur']:>8.2f} {v['external_eur']:>9.2f}"
            f" {v['net_eur']:>9.2f}"
        )


def print_comparison(naive: dict, coordinated: dict) -> None:
    print(f"Scenario '{naive['scenario']}': naive versus coordinated routing\n")
    rows = [
        ("mean delay, all work (s)", "mean_delay_s", "{:.0f}"),
        ("work within its norm", "within_norm_share", "{:.0%}"),
        ("work run elsewhere", "migrated_work_share", "{:.0%}"),
        ("chunks moved", "migrated_chunks", "{:.0f}"),
        ("chunks deferred at least once", "deferred_chunks", "{:.0f}"),
        ("paid to research/commercial (EUR)", "external_eur", "{:.2f}"),
    ]
    print(f"  {'':40} {'naive':>12} {'coordinated':>12}")
    for label, key, pattern in rows:
        print(
            f"  {label:40} {_fmt(naive['totals'][key], pattern):>12}"
            f" {_fmt(coordinated['totals'][key], pattern):>12}"
        )
    print("\n  Per site: own users (kritiek + interactief) within norm, and share of work done for others")
    print(f"  {'site':14} {'own in norm':>12} {'coordinated':>12} {'for others':>11} {'coordinated':>12}")
    for site, v in naive["sites"].items():
        c = coordinated["sites"][site]
        print(
            f"  {site:14} {_fmt(v['own_users_within_norm_share'], '{:.0%}'):>12}"
            f" {_fmt(c['own_users_within_norm_share'], '{:.0%}'):>12}"
            f" {_fmt(v['external_share'], '{:.0%}'):>11} {_fmt(c['external_share'], '{:.0%}'):>12}"
        )
    print("\n  Per organisation and tier: mean delay (s) and work within norm")
    print(f"  {'org/tier':24} {'naive':>8} {'in norm':>8} {'coord.':>8} {'in norm':>8}")
    for key, v in naive["org_tier"].items():
        c = coordinated["org_tier"].get(key, {})
        print(
            f"  {key:24} {_fmt(v['mean_delay_s']):>8} {_fmt(v['within_norm_share'], '{:.0%}'):>8}"
            f" {_fmt(c.get('mean_delay_s')):>8} {_fmt(c.get('within_norm_share'), '{:.0%}'):>8}"
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Simulate a day of demand on the federated network.")
    parser.add_argument("--scenario", default="werkdag", help="scenario id from data/scenarios.yaml")
    parser.add_argument("--mode", choices=["naive", "coordinated"], default=None)
    parser.add_argument("--compare", action="store_true", help="run naive and coordinated and compare")
    parser.add_argument("--chunk", type=float, default=300.0, help="chunk size in reference GPU-seconds")
    parser.add_argument("--out", type=Path, default=None, help="directory for decisions/sites/ledger CSVs")
    parser.add_argument("--json", action="store_true", help="print the summary as JSON")
    args = parser.parse_args(argv)

    world = load_world()
    if args.compare:
        naive = run(world, args.scenario, "naive", args.chunk)
        coordinated = run(world, args.scenario, "coordinated", args.chunk)
        if args.out:
            write_outputs(naive, args.out, "-naive")
            write_outputs(coordinated, args.out, "-coordinated")
        if args.json:
            print(json.dumps({"naive": naive.summary, "coordinated": coordinated.summary}, indent=2))
        else:
            print_comparison(naive.summary, coordinated.summary)
        return 0
    result = run(world, args.scenario, args.mode, args.chunk)
    if args.out:
        write_outputs(result, args.out)
    if args.json:
        print(json.dumps(result.summary, indent=2, ensure_ascii=False))
    else:
        print_summary(result.summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
