"""Generate the simulated demand file data/demand/werkdag.csv (deterministic, seeded).

All demand is invented. Interactive demand follows an office-hours profile per organisation, scaled to a
share of that organisation's own capacity, so the scenarios produce contention. Batch and critical
workloads are fixed lists below. Regenerate with:

    python -m inferentienet.demand            # writes data/demand/werkdag.csv
    python -m inferentienet.demand --check    # fails if the committed file differs
"""

from __future__ import annotations

import argparse
import random
import sys
import tempfile
from pathlib import Path

from . import catalog
from .model import World, load_world
from .router import Request, resolve_model_class

SEED = 20261209
DEFAULT_OUT = catalog.DATA_DIR / "demand" / "werkdag.csv"

# Relative interactive load per hour of the day (0-23); 1.0 is the daily peak.
HOURLY = {
    "kantoor": [
        0.02,
        0.01,
        0.01,
        0.01,
        0.01,
        0.03,
        0.08,
        0.30,
        0.70,
        0.95,
        1.00,
        0.95,
        0.70,
        0.85,
        0.95,
        0.90,
        0.75,
        0.45,
        0.25,
        0.15,
        0.10,
        0.06,
        0.04,
        0.03,
    ],
    "lang": [
        0.03,
        0.02,
        0.02,
        0.02,
        0.02,
        0.04,
        0.10,
        0.40,
        0.75,
        0.95,
        1.00,
        0.95,
        0.80,
        0.90,
        0.95,
        0.95,
        0.90,
        0.80,
        0.65,
        0.45,
        0.25,
        0.10,
        0.06,
        0.04,
    ],
}

# Interactive demand per organisation. peak_share: peak load as a share of the organisation's own capacity.
PROFILES = {
    "ministerie": {
        "profile": "kantoor",
        "peak_share": 0.70,
        "classes": {"openbaar": 0.15, "intern": 0.55, "vertrouwelijk": 0.30},
        "tasks": {"chat": 0.5, "samenvatten": 0.3, "zoeken": 0.2},
    },
    "uitvoering": {
        "profile": "lang",
        "peak_share": 0.75,
        "classes": {"intern": 0.20, "vertrouwelijk": 0.30, "bijzonder": 0.50},
        "tasks": {"chat": 0.4, "samenvatten": 0.3, "classificeren": 0.3},
    },
    "provincie": {
        "profile": "kantoor",
        "peak_share": 0.60,
        "classes": {"openbaar": 0.35, "intern": 0.45, "vertrouwelijk": 0.20},
        "tasks": {"chat": 0.5, "samenvatten": 0.3, "zoeken": 0.2},
    },
    "gemeenten": {
        "profile": "kantoor",
        "peak_share": 1.60,
        "classes": {"openbaar": 0.25, "intern": 0.35, "vertrouwelijk": 0.40},
        "tasks": {"chat": 0.6, "samenvatten": 0.3, "zoeken": 0.1},
    },
}

# Typical tokens per request (input, output) per task.
TASK_SIZE = {
    "chat": (4000, 400),
    "samenvatten": (6000, 600),
    "classificeren": (1500, 20),
    "zoeken": (500, 0),
    "vertalen": (2000, 2000),
    "analyse": (8000, 1500),
}

# (slot, org, tier, data_class, task, requests, name, description)
FIXED_WORKLOADS = [
    (
        4,
        "ministerie",
        "batch",
        "openbaar",
        "samenvatten",
        200_000,
        "archief-samenvatten",
        "Samenvatten openbaar archief",
    ),
    (
        8,
        "gemeenten",
        "batch",
        "openbaar",
        "vertalen",
        20_000,
        "publieksinformatie-vertalen",
        "Vertalen publieksinformatie",
    ),
    (
        41,
        "provincie",
        "kritiek",
        "vertrouwelijk",
        "analyse",
        30,
        "handhaving-melding",
        "Analyse van een melding tijdens handhaving",
    ),
    (
        42,
        "provincie",
        "kritiek",
        "vertrouwelijk",
        "analyse",
        30,
        "handhaving-melding",
        "Analyse van een melding tijdens handhaving",
    ),
    (
        60,
        "ministerie",
        "kritiek",
        "openbaar",
        "vertalen",
        50,
        "crisiscommunicatie-vertalen",
        "Vertalen van crisiscommunicatie",
    ),
    (
        72,
        "ministerie",
        "batch",
        "intern",
        "classificeren",
        300_000,
        "beleidsdocumenten-classificeren",
        "Classificeren beleidsdocumenten",
    ),
    (
        76,
        "provincie",
        "batch",
        "openbaar",
        "analyse",
        10_000,
        "ruimtelijke-plannen-analyse",
        "Analyse ruimtelijke plannen",
    ),
    (
        80,
        "uitvoering",
        "batch",
        "bijzonder",
        "classificeren",
        1_500_000,
        "bezwaarschriften-classificeren",
        "Classificeren bezwaarschriften",
    ),
    (
        88,
        "uitvoering",
        "batch",
        "vertrouwelijk",
        "samenvatten",
        150_000,
        "dossiers-samenvatten",
        "Samenvatten dossiers",
    ),
    (
        92,
        "gemeenten",
        "batch",
        "intern",
        "classificeren",
        800_000,
        "woo-classificeren",
        "Classificeren Woo-documenten",
    ),
]


def _time(slot: int) -> str:
    return f"{slot // 4:02d}:{(slot % 4) * 15:02d}"


def _row(
    world: World,
    slot: int,
    org: str,
    tier: str,
    data_class: str,
    task: str,
    requests: int,
    workload_id: str,
    description: str,
) -> dict:
    tokens_in_per, tokens_out_per = TASK_SIZE[task]
    probe = Request(org, tier, data_class, task, tokens_in_per, tokens_out_per)
    model_class, _ = resolve_model_class(probe, world)
    model = world.network.default_model(model_class)
    tokens_in, tokens_out = requests * tokens_in_per, requests * tokens_out_per
    return {
        "slot": slot,
        "time": _time(slot),
        "workload_id": workload_id,
        "org": org,
        "tier": tier,
        "data_class": data_class,
        "task": task,
        "requests": requests,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "ref_gpu_seconds": round(model.ref_gpu_seconds(tokens_in, tokens_out), 3),
        "description": description,
    }


def generate(world: World, seed: int = SEED) -> list[dict]:
    rng = random.Random(seed)
    rows: list[dict] = []
    for org, profile in PROFILES.items():
        own_capacity = sum(
            s.gpus * s.speed_factor * world.policy.slot_seconds
            for s in world.network.sites.values()
            if s.owner == org
        )
        for slot in range(96):
            noise = 0.9 + 0.2 * rng.random()
            load = profile["peak_share"] * own_capacity * HOURLY[profile["profile"]][slot // 4] * noise
            for data_class, class_share in profile["classes"].items():
                for task, task_share in profile["tasks"].items():
                    tokens_in_per, tokens_out_per = TASK_SIZE[task]
                    probe = Request(org, "interactief", data_class, task, tokens_in_per, tokens_out_per)
                    model_class, _ = resolve_model_class(probe, world)
                    per_request = world.network.default_model(model_class).ref_gpu_seconds(
                        tokens_in_per, tokens_out_per
                    )
                    requests = round(load * class_share * task_share / per_request)
                    if requests < 1:
                        continue
                    workload_id = f"{org}-{_time(slot).replace(':', '')}-{data_class}-{task}"
                    rows.append(
                        _row(world, slot, org, "interactief", data_class, task, requests, workload_id, "")
                    )
    for slot, org, tier, data_class, task, requests, name, description in FIXED_WORKLOADS:
        workload_id = f"{org}-{_time(slot).replace(':', '')}-{name}"
        rows.append(_row(world, slot, org, tier, data_class, task, requests, workload_id, description))
    rows.sort(key=lambda r: (r["slot"], r["workload_id"]))
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate the simulated demand file.")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument(
        "--check", action="store_true", help="compare with the existing file instead of writing"
    )
    args = parser.parse_args(argv)
    rows = generate(load_world(), args.seed)
    if args.check:
        with tempfile.TemporaryDirectory() as tmp:
            fresh = Path(tmp) / "fresh.csv"
            catalog.write_demand(fresh, rows)
            if fresh.read_text(encoding="utf-8") != args.out.read_text(encoding="utf-8"):
                print(f"{args.out} differs from a fresh generation; run without --check", file=sys.stderr)
                return 1
        print(f"{args.out} is up to date ({len(rows)} rows)")
        return 0
    args.out.parent.mkdir(parents=True, exist_ok=True)
    catalog.write_demand(args.out, rows)
    print(f"wrote {len(rows)} rows to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
