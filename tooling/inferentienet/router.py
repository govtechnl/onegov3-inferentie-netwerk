"""Deterministic, explainable routing of one request (or one chunk of work) over the federated network.

All decision rules come from data/policy.yaml and data/network.yaml. The router never calls a language
model and has no hidden state: the same request with the same snapshot of the network always gives the
same decision, with the reasoning in ``Decision.steps``.

Try it:

    python -m inferentienet.router --org gemeenten --tier interactief --data-class vertrouwelijk \\
        --task chat --tokens-in 4000 --tokens-out 400 --load uvo-rc1=0.95
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field

from .model import RELATION_PATH, Coordination, Site, Tier, Window, World, load_world


class RoutingError(ValueError):
    """The request itself is invalid (unknown organisation, tier, data class or task)."""


@dataclass
class Request:
    org: str
    tier: str
    data_class: str
    task: str
    tokens_in: int
    tokens_out: int
    requests: int = 1
    model_class: str | None = None
    id: str = ""


@dataclass
class SiteSnapshot:
    """What a gateway knows about one site at the moment of routing (one 15-minute slot)."""

    capacity_s: float
    load_by_priority: dict[int, float] = field(default_factory=dict)
    external_load_s: float = 0.0
    external_by_tier: dict[str, float] = field(default_factory=dict)

    def load_ahead(self, priority: int) -> float:
        """Work that will be served before new work of this priority."""
        return sum(v for p, v in self.load_by_priority.items() if p <= priority)

    @property
    def total_load_s(self) -> float:
        return sum(self.load_by_priority.values())

    def add(self, priority: int, work_s: float, external: bool, tier: str) -> None:
        self.load_by_priority[priority] = self.load_by_priority.get(priority, 0.0) + work_s
        if external:
            self.external_load_s += work_s
            self.external_by_tier[tier] = self.external_by_tier.get(tier, 0.0) + work_s


@dataclass
class Candidate:
    site: str
    relation: str
    model: str
    work_s: float = 0.0
    est_delay_s: float = 0.0
    toll_s: float = 0.0
    cost_eur: float = 0.0
    utilisation_after: float = 0.0
    external_share_after: float = 0.0
    excluded: list[str] = field(default_factory=list)
    protected: str = ""
    note: str = ""

    @property
    def eligible(self) -> bool:
        return not self.excluded

    @property
    def expected_s(self) -> float:
        """Expected delay plus the switching toll: what the coordinated router compares."""
        return self.est_delay_s + self.toll_s


@dataclass
class Decision:
    request_id: str
    org: str
    tier: str
    data_class: str
    task: str
    model_class: str
    mode: str
    outcome: str
    site: str | None
    model: str | None
    relation: str | None
    work_s: float
    est_delay_s: float
    cost_eur: float
    within_norm: bool
    steps: list[str]
    candidates: list[Candidate]

    @property
    def placed(self) -> bool:
        return self.site is not None

    def to_dict(self) -> dict:
        data = asdict(self)
        for key in ("work_s", "est_delay_s", "cost_eur"):
            data[key] = round(data[key], 4)
        for cand in data["candidates"]:
            for key in (
                "work_s",
                "est_delay_s",
                "toll_s",
                "cost_eur",
                "utilisation_after",
                "external_share_after",
            ):
                cand[key] = round(cand[key], 4)
        return data

    def explain(self) -> str:
        head = f"{self.outcome.upper()}"
        if self.site:
            head += f" -> {self.site} ({self.model})"
        lines = [head, *[f"  {n}. {step}" for n, step in enumerate(self.steps, start=1)]]
        return "\n".join(lines)


def resolve_model_class(req: Request, world: World) -> tuple[str, str]:
    if req.model_class:
        if req.model_class not in world.network.model_classes():
            raise RoutingError(f"unknown model class {req.model_class!r}")
        return req.model_class, f"model class '{req.model_class}' was requested explicitly"
    per_request = req.tokens_in / max(req.requests, 1)
    for n, rule in enumerate(world.policy.task_models, start=1):
        if rule.task != req.task:
            continue
        if rule.max_tokens_in_per_request is not None and per_request > rule.max_tokens_in_per_request:
            continue
        limit = ""
        if rule.max_tokens_in_per_request is not None:
            limit = f" with at most {rule.max_tokens_in_per_request} input tokens per request"
        return (
            rule.model_class,
            f"task_models rule {n} (task '{rule.task}'{limit}) gives '{rule.model_class}'",
        )
    raise RoutingError(f"no task_models rule for task {req.task!r}")


def hard_exclusions(req: Request, site: Site, relation: str, world: World) -> list[str]:
    """Rules that can never be traded off: data class, provider acceptance."""
    reasons: list[str] = []
    data_class = world.policy.data_classes[req.data_class]
    if relation not in data_class.allowed_relations:
        allowed = ", ".join(data_class.allowed_relations)
        reasons.append(f"data class '{data_class.id}' may not go to '{relation}' sites (allowed: {allowed})")
    if relation == "commercieel":
        missing = [p for p in data_class.commercial_requires if p not in site.properties]
        if missing:
            reasons.append(f"commercial site lacks {', '.join(missing)}, required for '{data_class.id}'")
    if relation != "eigen":
        if req.data_class not in site.accepts_data_classes:
            reasons.append(f"site does not accept data class '{req.data_class}' from other organisations")
        if req.tier not in site.accepts_tiers:
            reasons.append(f"site does not accept tier '{req.tier}' from other organisations")
    return reasons


def receiving_protection(
    snap: SiteSnapshot, site: Site, tier: Tier, work_s: float, coord: Coordination
) -> tuple[str, str]:
    """Return (reason it is protected, note). An empty reason means the site may take the work."""
    if tier.receiving_reserve_share > 0:
        used = snap.external_by_tier.get(tier.id, 0.0)
        reserve = tier.receiving_reserve_share * snap.capacity_s
        if used + work_s <= reserve:
            return "", f"within the {tier.receiving_reserve_share:.0%} solidarity reserve for '{tier.id}'"
    utilisation_after = (snap.total_load_s + work_s) / snap.capacity_s
    if utilisation_after > coord.max_utilisation:
        return (
            f"receiving protection, utilisation would become {utilisation_after:.0%} "
            f"(max {coord.max_utilisation:.0%})",
            "",
        )
    external_after = (snap.external_load_s + work_s) / snap.capacity_s
    if external_after > site.max_external_share:
        return (
            f"receiving protection, work from other organisations would become {external_after:.0%} "
            f"of capacity (max {site.max_external_share:.0%} at this site)",
            "",
        )
    return "", ""


def route(
    req: Request,
    snapshots: dict[str, SiteSnapshot],
    world: World,
    mode: str | None = None,
    exclude: Iterable[str] = (),
) -> Decision:
    net, pol = world.network, world.policy
    if req.org not in net.organisations:
        raise RoutingError(f"unknown organisation {req.org!r}")
    if req.tier not in pol.tiers:
        raise RoutingError(f"unknown tier {req.tier!r}")
    if req.data_class not in pol.data_classes:
        raise RoutingError(f"unknown data class {req.data_class!r}")
    tier = pol.tiers[req.tier]
    coord = pol.coordination
    mode = mode or coord.mode
    if mode not in ("naive", "coordinated"):
        raise RoutingError(f"unknown mode {mode!r}")
    excluded_sites = set(exclude)

    model_class, why = resolve_model_class(req, world)
    steps = [
        f"Request {req.id or '(no id)'} from '{req.org}': tier '{tier.id}', data class '{req.data_class}', "
        f"task '{req.task}'.",
        f"Model: {why}.",
    ]

    candidates: list[Candidate] = []
    for site in net.sites.values():
        model = net.model_for(site, model_class)
        if model is None:
            continue
        relation = net.relation(req.org, site)
        cand = Candidate(site=site.id, relation=relation, model=model.id)
        cand.excluded = hard_exclusions(req, site, relation, world)
        if site.id in excluded_sites:
            cand.excluded.append("the receiving gateway refused this request earlier")
        snap = snapshots.get(site.id)
        if snap is None or snap.capacity_s <= 0:
            cand.excluded.append("no capacity available in this slot")
        else:
            work = model.ref_gpu_seconds(req.tokens_in, req.tokens_out)
            rate = snap.capacity_s / pol.slot_seconds
            cand.work_s = work
            cand.est_delay_s = max(0.0, snap.load_ahead(tier.priority) + work - snap.capacity_s) / rate
            if relation != "eigen":
                cand.est_delay_s += net.transfer_overhead_s.get(relation, 0.0)
            cand.cost_eur = site.gpu_hours(work) * site.tariff_eur_per_gpu_hour * tier.price_multiplier
            cand.utilisation_after = (snap.total_load_s + work) / snap.capacity_s
            if relation != "eigen":
                cand.external_share_after = (snap.external_load_s + work) / snap.capacity_s
                if mode == "coordinated":
                    cand.toll_s = coord.toll_fixed_s + coord.toll_runtime_fraction * work / rate
                    cand.protected, cand.note = receiving_protection(snap, site, tier, work, coord)
        candidates.append(cand)

    if not candidates:
        steps.append(f"No site in the network hosts a '{model_class}' model.")
        return _decision(req, model_class, mode, "geweigerd", None, tier, steps, candidates)
    for cand in candidates:
        if cand.excluded:
            steps.append(f"Excluded {cand.site} ({cand.relation}): {'; '.join(cand.excluded)}.")
    eligible = [c for c in candidates if c.eligible]
    if not eligible:
        steps.append("No site meets the hard rules (data class, provider acceptance, capacity): refused.")
        return _decision(req, model_class, mode, "geweigerd", None, tier, steps, candidates)

    own = [c for c in eligible if c.relation == "eigen"]
    remote = [c for c in eligible if c.relation != "eigen"]

    if mode == "naive":
        steps.append(
            "Mode 'naive': no local preference, minimum gain, receiving protection or switching toll."
        )
        if tier.objective == "time":
            best = min(eligible, key=lambda c: (c.est_delay_s, c.relation != "eigen", c.cost_eur, c.site))
            steps.append(f"Fastest option is {best.site} with an expected delay of {best.est_delay_s:.0f} s.")
        else:
            in_time = [c for c in eligible if c.est_delay_s <= tier.max_delay_s] or eligible
            best = min(in_time, key=lambda c: (c.cost_eur, c.est_delay_s, c.site))
            steps.append(f"Cheapest option within the deadline is {best.site} at EUR {best.cost_eur:.4f}.")
        return _decision(req, model_class, mode, None, best, tier, steps, candidates)

    steps.append(
        "Mode 'coordinated': local preference, minimum gain, receiving protection and switching toll."
    )
    open_remote: list[Candidate] = []
    for cand in remote:
        if cand.protected:
            steps.append(f"Skipped {cand.site}: {cand.protected}.")
        else:
            if cand.note:
                steps.append(f"{cand.site} may take the request: {cand.note}.")
            open_remote.append(cand)

    if tier.objective == "time":
        home = min(own, key=lambda c: (c.est_delay_s, c.cost_eur, c.site)) if own else None
        if home and coord.prefer_local and home.est_delay_s <= tier.max_delay_s:
            steps.append(
                f"Own site {home.site}: expected delay {home.est_delay_s:.0f} s is within the norm of "
                f"{tier.max_delay_s:.0f} s for '{tier.id}', so the request stays local."
            )
            return _decision(req, model_class, mode, None, home, tier, steps, candidates)
        if home:
            steps.append(
                f"Own site {home.site}: expected delay {home.est_delay_s:.0f} s exceeds the norm of "
                f"{tier.max_delay_s:.0f} s, so other sites are considered."
            )
        else:
            steps.append(
                f"'{req.org}' has no own site that may run this request; other sites are considered."
            )
        movers = open_remote
        needed = 0.0
        if home:
            needed = max(coord.min_gain_seconds, coord.min_gain_ratio * home.est_delay_s)
            movers = [c for c in open_remote if home.est_delay_s - c.expected_s >= needed]
            if open_remote and not movers:
                alt = min(open_remote, key=lambda c: (c.expected_s, c.cost_eur, c.site))
                steps.append(
                    f"Best alternative {alt.site} would save {home.est_delay_s - alt.expected_s:.0f} s "
                    f"after a switching toll of {alt.toll_s:.0f} s, less than the minimum gain of "
                    f"{needed:.0f} s: "
                    f"the request stays local."
                )
                return _decision(req, model_class, mode, None, home, tier, steps, candidates)
        in_norm = [c for c in movers if c.est_delay_s <= tier.max_delay_s]
        if in_norm:
            best = min(in_norm, key=lambda c: (c.cost_eur, c.expected_s, c.site))
            why_best = f"the cheapest option within the norm of {tier.max_delay_s:.0f} s"
        elif movers:
            best = min(movers, key=lambda c: (c.expected_s, c.cost_eur, c.site))
            why_best = f"no option meets the norm of {tier.max_delay_s:.0f} s, so the fastest one"
        else:
            best = None
        if best:
            gain = (
                f", saving {home.est_delay_s - best.expected_s:.0f} s (minimum {needed:.0f} s)"
                if home
                else ""
            )
            steps.append(
                f"Chose {best.site}, {why_best}: expected delay {best.est_delay_s:.0f} s, switching toll "
                f"{best.toll_s:.0f} s{gain}, cost EUR {best.cost_eur:.4f}."
            )
            return _decision(req, model_class, mode, None, best, tier, steps, candidates)
        if home:
            steps.append(
                "No other site can take the request without being overloaded: it waits at the own site."
            )
            return _decision(req, model_class, mode, None, home, tier, steps, candidates)
        return _defer_or_force(req, model_class, mode, tier, steps, candidates, remote, coord)

    # objective == "cost"
    home = min(own, key=lambda c: (c.cost_eur, c.est_delay_s, c.site)) if own else None
    in_time = [c for c in open_remote if c.expected_s <= tier.max_delay_s]
    best = min(in_time, key=lambda c: (c.cost_eur, c.expected_s, c.site)) if in_time else None
    if home:
        home_in_time = home.est_delay_s <= tier.max_delay_s
        if best and home_in_time:
            saving = home.cost_eur - best.cost_eur
            needed = coord.min_gain_ratio * home.cost_eur
            if saving > 0 and saving >= needed:
                steps.append(
                    f"{best.site} is {saving / home.cost_eur:.0%} cheaper than own site {home.site} and "
                    f"meets the deadline; the minimum gain is {coord.min_gain_ratio:.0%}, so the work moves."
                )
                return _decision(req, model_class, mode, None, best, tier, steps, candidates)
        if best and not home_in_time:
            steps.append(
                f"Own site {home.site} cannot meet the deadline of {tier.max_delay_s / 3600:.1f} h; "
                f"{best.site} can."
            )
            return _decision(req, model_class, mode, None, best, tier, steps, candidates)
        steps.append(
            f"Own site {home.site} costs EUR {home.cost_eur:.4f}; no alternative within the deadline is "
            f"at least {coord.min_gain_ratio:.0%} cheaper, so the work stays local."
        )
        return _decision(req, model_class, mode, None, home, tier, steps, candidates)
    if best:
        steps.append(f"Cheapest option within the deadline is {best.site} at EUR {best.cost_eur:.4f}.")
        return _decision(req, model_class, mode, None, best, tier, steps, candidates)
    if open_remote:
        fastest = min(open_remote, key=lambda c: (c.expected_s, c.cost_eur, c.site))
        steps.append(f"No site meets the deadline; chose the fastest open option {fastest.site}.")
        return _decision(req, model_class, mode, None, fastest, tier, steps, candidates)
    return _defer_or_force(req, model_class, mode, tier, steps, candidates, remote, coord)


def _defer_or_force(
    req: Request,
    model_class: str,
    mode: str,
    tier: Tier,
    steps: list[str],
    candidates: list[Candidate],
    remote: list[Candidate],
    coord: Coordination,
) -> Decision:
    if coord.defer_when_no_capacity or not remote:
        steps.append(
            "Every site that may run this request is protected against overload: deferred to the next slot."
        )
        return _decision(req, model_class, mode, "uitgesteld", None, tier, steps, candidates)
    forced = min(remote, key=lambda c: (c.expected_s, c.cost_eur, c.site))
    steps.append(f"Receiving protection overridden (defer_when_no_capacity is off): {forced.site}.")
    return _decision(req, model_class, mode, None, forced, tier, steps, candidates)


def _decision(
    req: Request,
    model_class: str,
    mode: str,
    outcome: str | None,
    chosen: Candidate | None,
    tier: Tier,
    steps: list[str],
    candidates: list[Candidate],
) -> Decision:
    if chosen is not None:
        outcome = RELATION_PATH[chosen.relation]
    return Decision(
        request_id=req.id,
        org=req.org,
        tier=req.tier,
        data_class=req.data_class,
        task=req.task,
        model_class=model_class,
        mode=mode,
        outcome=outcome or "geweigerd",
        site=chosen.site if chosen else None,
        model=chosen.model if chosen else None,
        relation=chosen.relation if chosen else None,
        work_s=chosen.work_s if chosen else 0.0,
        est_delay_s=chosen.est_delay_s if chosen else 0.0,
        cost_eur=chosen.cost_eur if chosen else 0.0,
        within_norm=bool(chosen) and chosen.est_delay_s <= tier.max_delay_s,
        steps=steps,
        candidates=candidates,
    )


def snapshots_from_utilisation(
    world: World,
    hour: float,
    utilisation: dict[str, float] | None = None,
    extra_windows: dict[str, tuple[Window, ...]] | None = None,
) -> dict[str, SiteSnapshot]:
    """Build snapshots for one slot from a simple 'share of capacity already in use' per site.

    The existing load is put at the highest priority, so it counts as 'ahead' of every new request.
    """
    utilisation = utilisation or {}
    extra_windows = extra_windows or {}
    top = min(t.priority for t in world.policy.tiers.values())
    snaps: dict[str, SiteSnapshot] = {}
    for site in world.network.sites.values():
        capacity = site.rate(hour, extra_windows.get(site.id, ())) * world.policy.slot_seconds
        snap = SiteSnapshot(capacity_s=capacity)
        if capacity > 0 and utilisation.get(site.id):
            snap.load_by_priority[top] = utilisation[site.id] * capacity
        snaps[site.id] = snap
    return snaps


def _parse_loads(values: list[str]) -> dict[str, float]:
    loads: dict[str, float] = {}
    for value in values:
        site, _, share = value.partition("=")
        if not share:
            raise argparse.ArgumentTypeError(f"--load expects SITE=SHARE, got {value!r}")
        loads[site] = float(share)
    return loads


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Route one request and explain the decision.")
    parser.add_argument("--org", required=True)
    parser.add_argument("--tier", default="interactief")
    parser.add_argument("--data-class", required=True)
    parser.add_argument("--task", default="chat")
    parser.add_argument("--model-class", default=None)
    parser.add_argument("--tokens-in", type=int, default=4000)
    parser.add_argument("--tokens-out", type=int, default=400)
    parser.add_argument("--hour", type=float, default=10.0, help="hour of day, for availability windows")
    parser.add_argument(
        "--load", action="append", default=[], metavar="SITE=SHARE", help="share of capacity already in use"
    )
    parser.add_argument("--mode", choices=["naive", "coordinated"], default=None)
    parser.add_argument("--json", action="store_true", help="print the full decision as JSON")
    args = parser.parse_args(argv)

    world = load_world()
    snaps = snapshots_from_utilisation(world, args.hour, _parse_loads(args.load))
    req = Request(
        org=args.org,
        tier=args.tier,
        data_class=args.data_class,
        task=args.task,
        tokens_in=args.tokens_in,
        tokens_out=args.tokens_out,
        model_class=args.model_class,
        id="cli-1",
    )
    try:
        decision = route(req, snaps, world, mode=args.mode)
    except RoutingError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(decision.to_dict(), indent=2, ensure_ascii=False))
    else:
        print(decision.explain())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
