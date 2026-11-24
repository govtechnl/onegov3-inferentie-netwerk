"""Typed, read-only views on network.yaml and policy.yaml, plus cross-reference checks."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from . import catalog

# Relation between a requesting organisation and a site, and the routing path that goes with it.
RELATION_PATH = {
    "eigen": "lokaal",
    "federatie": "federatie",
    "onderzoek": "extern",
    "commercieel": "extern",
}


@dataclass(frozen=True)
class Organisation:
    id: str
    name: str
    role: str
    gateway_port: int


@dataclass(frozen=True)
class Model:
    id: str
    model_class: str
    gpu_s_per_1k_in: float
    gpu_s_per_1k_out: float

    def ref_gpu_seconds(self, tokens_in: int, tokens_out: int) -> float:
        """Work in reference GPU-seconds for the given number of tokens."""
        return tokens_in / 1000 * self.gpu_s_per_1k_in + tokens_out / 1000 * self.gpu_s_per_1k_out


@dataclass(frozen=True)
class Window:
    start: int
    end: int
    share: float
    reason: str = ""

    def covers(self, hour: float) -> bool:
        return self.start <= hour < self.end


@dataclass(frozen=True)
class Site:
    id: str
    name: str
    kind: str
    owner: str | None
    gpus: int
    speed_factor: float
    models: tuple[str, ...]
    tariff_eur_per_gpu_hour: float
    kwh_per_gpu_hour: float
    accepts_data_classes: tuple[str, ...]
    accepts_tiers: tuple[str, ...]
    max_external_share: float
    properties: frozenset[str]
    availability: tuple[Window, ...]

    def share_at(self, hour: float, extra: tuple[Window, ...] = ()) -> tuple[float, str]:
        """Available share of the site at this hour. Scenario windows (extra) take precedence."""
        for window in (*extra, *self.availability):
            if window.covers(hour):
                return window.share, window.reason
        return 1.0, ""

    def rate(self, hour: float, extra: tuple[Window, ...] = ()) -> float:
        """Capacity in reference GPU-seconds per second."""
        share, _ = self.share_at(hour, extra)
        return self.gpus * self.speed_factor * share

    def gpu_hours(self, ref_gpu_seconds: float) -> float:
        """Actual GPU-hours this site spends on a given amount of reference work."""
        return ref_gpu_seconds / self.speed_factor / 3600


@dataclass(frozen=True)
class Network:
    organisations: dict[str, Organisation]
    models: dict[str, Model]
    sites: dict[str, Site]
    transfer_overhead_s: dict[str, float]

    def relation(self, org_id: str, site: Site) -> str:
        if site.kind == "overheid":
            return "eigen" if site.owner == org_id else "federatie"
        return site.kind

    def model_for(self, site: Site, model_class: str) -> Model | None:
        for model_id in site.models:
            model = self.models[model_id]
            if model.model_class == model_class:
                return model
        return None

    def model_classes(self) -> list[str]:
        return sorted({m.model_class for m in self.models.values()})

    def default_model(self, model_class: str) -> Model:
        for model in self.models.values():
            if model.model_class == model_class:
                return model
        raise KeyError(f"No model of class {model_class!r} in the catalogue")


@dataclass(frozen=True)
class DataClass:
    id: str
    label: str
    allowed_relations: tuple[str, ...]
    commercial_requires: tuple[str, ...]


@dataclass(frozen=True)
class Tier:
    id: str
    label: str
    priority: int
    objective: str
    max_delay_s: float
    price_multiplier: float
    receiving_reserve_share: float


@dataclass(frozen=True)
class TaskRule:
    task: str
    model_class: str
    max_tokens_in_per_request: int | None = None


@dataclass(frozen=True)
class Coordination:
    mode: str
    prefer_local: bool
    min_gain_seconds: float
    min_gain_ratio: float
    max_utilisation: float
    toll_fixed_s: float
    toll_runtime_fraction: float
    defer_when_no_capacity: bool


@dataclass(frozen=True)
class Policy:
    slot_seconds: int
    data_classes: dict[str, DataClass]
    tiers: dict[str, Tier]
    task_models: tuple[TaskRule, ...]
    coordination: Coordination
    currency: str
    tasks: tuple[str, ...] = field(default=())


def build_network(raw: dict) -> Network:
    organisations = {o["id"]: Organisation(**o) for o in raw["organisations"]}
    models = {m["id"]: Model(**m) for m in raw["models"]}
    sites = {}
    for s in raw["sites"]:
        sites[s["id"]] = Site(
            id=s["id"],
            name=s["name"],
            kind=s["kind"],
            owner=s["owner"],
            gpus=s["gpus"],
            speed_factor=s["speed_factor"],
            models=tuple(s["models"]),
            tariff_eur_per_gpu_hour=s["tariff_eur_per_gpu_hour"],
            kwh_per_gpu_hour=s["kwh_per_gpu_hour"],
            accepts_data_classes=tuple(s["accepts_from_others"]["data_classes"]),
            accepts_tiers=tuple(s["accepts_from_others"]["tiers"]),
            max_external_share=s["max_external_share"],
            properties=frozenset(s["properties"]),
            availability=tuple(Window(**w) for w in s["availability"]),
        )
    return Network(organisations, models, sites, dict(raw["transfer_overhead_s"]))


def build_policy(raw: dict) -> Policy:
    coordination = raw["coordination"]
    return Policy(
        slot_seconds=raw["slot_seconds"],
        data_classes={
            d["id"]: DataClass(
                d["id"], d["label"], tuple(d["allowed_relations"]), tuple(d["commercial_requires"])
            )
            for d in raw["data_classes"]
        },
        tiers={
            t["id"]: Tier(
                t["id"],
                t["label"],
                t["priority"],
                t["objective"],
                t["max_delay_s"],
                t["price_multiplier"],
                t["receiving_reserve_share"],
            )
            for t in raw["tiers"]
        },
        task_models=tuple(TaskRule(**r) for r in raw["task_models"]),
        coordination=Coordination(
            mode=coordination["mode"],
            prefer_local=coordination["prefer_local"],
            min_gain_seconds=coordination["min_gain"]["seconds"],
            min_gain_ratio=coordination["min_gain"]["ratio"],
            max_utilisation=coordination["receiving_protection"]["max_utilisation"],
            toll_fixed_s=coordination["switching_toll"]["fixed_s"],
            toll_runtime_fraction=coordination["switching_toll"]["runtime_fraction"],
            defer_when_no_capacity=coordination["defer_when_no_capacity"],
        ),
        currency=raw["settlement"]["currency"],
        tasks=tuple(dict.fromkeys(r["task"] for r in raw["task_models"])),
    )


def cross_check(network_raw: dict, policy_raw: dict) -> list[str]:
    """Return reference errors between network.yaml and policy.yaml (empty when consistent)."""
    errors: list[str] = []

    def unique(kind: str, items: list[dict]) -> set[str]:
        ids = [i["id"] for i in items]
        for dup in sorted({i for i in ids if ids.count(i) > 1}):
            errors.append(f"duplicate {kind} id: {dup}")
        return set(ids)

    org_ids = unique("organisation", network_raw["organisations"])
    model_ids = unique("model", network_raw["models"])
    unique("site", network_raw["sites"])
    class_ids = unique("data class", policy_raw["data_classes"])
    tier_ids = unique("tier", policy_raw["tiers"])
    model_classes = {m["model_class"] for m in network_raw["models"]}
    ports = [o["gateway_port"] for o in network_raw["organisations"]]
    if len(ports) != len(set(ports)):
        errors.append("gateway ports must be unique")

    for site in network_raw["sites"]:
        sid = site["id"]
        if site["kind"] == "overheid" and site["owner"] not in org_ids:
            errors.append(f"site {sid}: owner {site['owner']!r} is not an organisation")
        if site["kind"] != "overheid" and site["owner"] is not None:
            errors.append(f"site {sid}: only 'overheid' sites have an owner")
        for model_id in site["models"]:
            if model_id not in model_ids:
                errors.append(f"site {sid}: unknown model {model_id!r}")
        hosted = [m["model_class"] for m in network_raw["models"] if m["id"] in site["models"]]
        if len(hosted) != len(set(hosted)):
            errors.append(f"site {sid}: hosts more than one model of the same class")
        for dc in site["accepts_from_others"]["data_classes"]:
            if dc not in class_ids:
                errors.append(f"site {sid}: unknown data class {dc!r}")
        for tier in site["accepts_from_others"]["tiers"]:
            if tier not in tier_ids:
                errors.append(f"site {sid}: unknown tier {tier!r}")
        for window in site["availability"]:
            if window["start"] >= window["end"]:
                errors.append(f"site {sid}: availability window must have start < end")

    for rule in policy_raw["task_models"]:
        if rule["model_class"] not in model_classes:
            errors.append(f"task_models: unknown model class {rule['model_class']!r}")
    priorities = [t["priority"] for t in policy_raw["tiers"]]
    if len(priorities) != len(set(priorities)):
        errors.append("tier priorities must be unique")
    return errors


@dataclass(frozen=True)
class World:
    """Everything the router and simulator need, loaded from data/."""

    network: Network
    policy: Policy


def load_world(network_path: Path | None = None, policy_path: Path | None = None) -> World:
    network_raw = catalog.load("network", network_path)
    policy_raw = catalog.load("policy", policy_path)
    errors = cross_check(network_raw, policy_raw)
    if errors:
        raise ValueError("data files are inconsistent:\n  " + "\n  ".join(errors))
    return World(build_network(network_raw), build_policy(policy_raw))
