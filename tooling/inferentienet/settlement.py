"""Settlement starter: a ledger of capacity used across organisations, with fixed tariffs.

Every placement outside the requesting organisation creates a ledger entry. The provider tariff from
network.yaml is multiplied by the tier's price multiplier from policy.yaml. Net positions show, per
organisation, what it supplied to others and what it used from others, in GPU-hours and in (fictitious)
euros, so that usage can be settled against capacity supplied.

This is deliberately simple. A market-based price (see market.py) or token-based tariffs are natural
extensions for teams.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass

from .model import Site, Tier


@dataclass(frozen=True)
class LedgerEntry:
    slot: int
    request_id: str
    consumer: str
    provider: str
    site: str
    relation: str
    tier: str
    gpu_hours: float
    energy_kwh: float
    tariff_eur_per_gpu_hour: float
    price_multiplier: float
    amount_eur: float

    def to_dict(self) -> dict:
        return asdict(self)


def provider_of(site: Site) -> str:
    """Who gets paid: the owning organisation, or the site itself for research and commercial sites."""
    return site.owner if site.owner else site.id


def entry(
    slot: int, request_id: str, consumer: str, site: Site, relation: str, tier: Tier, work_s: float
) -> LedgerEntry:
    gpu_hours = site.gpu_hours(work_s)
    amount = gpu_hours * site.tariff_eur_per_gpu_hour * tier.price_multiplier
    return LedgerEntry(
        slot=slot,
        request_id=request_id,
        consumer=consumer,
        provider=provider_of(site),
        site=site.id,
        relation=relation,
        tier=tier.id,
        gpu_hours=gpu_hours,
        energy_kwh=gpu_hours * site.kwh_per_gpu_hour,
        tariff_eur_per_gpu_hour=site.tariff_eur_per_gpu_hour,
        price_multiplier=tier.price_multiplier,
        amount_eur=amount,
    )


def net_positions(entries: list[LedgerEntry], organisations: list[str]) -> dict[str, dict[str, float]]:
    """Per organisation: capacity supplied and used, and the money owed in both directions.

    supplied_gpu_hours / receivable_eur   work done for other members of the federation
    used_gpu_hours / payable_eur          work done by other members for this organisation
    external_gpu_hours / external_eur     work bought from research or commercial sites
    net_gpu_hours, net_eur                supplied minus used; positive means the others owe you
    """
    positions: dict[str, dict[str, float]] = {org: defaultdict(float) for org in organisations}
    for e in entries:
        consumer = positions[e.consumer]
        if e.relation == "federatie":
            consumer["used_gpu_hours"] += e.gpu_hours
            consumer["payable_eur"] += e.amount_eur
            provider = positions[e.provider]
            provider["supplied_gpu_hours"] += e.gpu_hours
            provider["receivable_eur"] += e.amount_eur
        else:
            consumer["external_gpu_hours"] += e.gpu_hours
            consumer["external_eur"] += e.amount_eur
    result: dict[str, dict[str, float]] = {}
    for org, values in positions.items():
        keys = (
            "supplied_gpu_hours",
            "used_gpu_hours",
            "external_gpu_hours",
            "receivable_eur",
            "payable_eur",
            "external_eur",
        )
        row = {k: round(values[k], 4) for k in keys}
        row["net_gpu_hours"] = round(values["supplied_gpu_hours"] - values["used_gpu_hours"], 4)
        row["net_eur"] = round(values["receivable_eur"] - values["payable_eur"], 4)
        result[org] = row
    return result
