"""Starter for approach B: a simplified market for GPU capacity per 15-minute slot.

Loosely inspired by congestion management in the electricity market: parties post offers (spare capacity
at a minimum price) and bids (capacity needed, with a maximum price and a priority tier) per time block,
and a clearing step matches them. It is NOT a model of GOPACS or of any real market; see
docs/market-and-settlement.md for what is simplified.

Matching rules (all explicit, all testable):

1. Bids are matched in tier order (kritiek before interactief before batch), then by highest maximum
   price, then first come first served. Public priority beats willingness to pay.
2. Offers are used cheapest first.
3. A bid only matches an offer the router would also allow: same data class rules, provider acceptance
   and model class as in policy.yaml and network.yaml. An organisation never buys from itself.
4. Pricing: 'uniform' (everyone pays the highest accepted offer price, capped at their own maximum),
   'pay_as_bid' or 'pay_as_offer'.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass

from .model import World
from .router import Request, hard_exclusions
from .settlement import provider_of

PRICING = ("uniform", "pay_as_bid", "pay_as_offer")


class MarketError(ValueError):
    pass


@dataclass
class Offer:
    id: str
    site: str
    provider: str
    slot: int
    gpu_hours: float
    min_price_eur: float
    remaining: float


@dataclass
class Bid:
    id: str
    org: str
    slot: int
    tier: str
    data_class: str
    model_class: str
    gpu_hours: float
    max_price_eur: float
    remaining: float


@dataclass
class Match:
    slot: int
    bid_id: str
    offer_id: str
    org: str
    site: str
    provider: str
    relation: str
    tier: str
    gpu_hours: float
    price_eur_per_gpu_hour: float
    amount_eur: float
    reason: str


class Market:
    def __init__(self, world: World, pricing: str = "uniform"):
        if pricing not in PRICING:
            raise MarketError(f"pricing must be one of {PRICING}")
        self.world = world
        self.pricing = pricing
        self.reset()

    def reset(self) -> None:
        self.offers: list[Offer] = []
        self.bids: list[Bid] = []
        self.matches: list[Match] = []
        self._cleared: set[int] = set()

    def _check_slot(self, slot: int) -> None:
        if not 0 <= slot < 96:
            raise MarketError("slot must be between 0 and 95 (15-minute blocks of one day)")
        if slot in self._cleared:
            raise MarketError(f"slot {slot} has already been cleared")

    def add_offer(self, site: str, slot: int, gpu_hours: float, min_price_eur: float) -> Offer:
        if site not in self.world.network.sites:
            raise MarketError(f"unknown site {site!r}")
        self._check_slot(slot)
        if gpu_hours <= 0 or min_price_eur < 0:
            raise MarketError("gpu_hours must be positive and min_price_eur non-negative")
        offer = Offer(
            id=f"offer-{len(self.offers) + 1}",
            site=site,
            provider=provider_of(self.world.network.sites[site]),
            slot=slot,
            gpu_hours=gpu_hours,
            min_price_eur=min_price_eur,
            remaining=gpu_hours,
        )
        self.offers.append(offer)
        return offer

    def add_bid(
        self,
        org: str,
        slot: int,
        tier: str,
        data_class: str,
        model_class: str,
        gpu_hours: float,
        max_price_eur: float,
    ) -> Bid:
        net, pol = self.world.network, self.world.policy
        if org not in net.organisations:
            raise MarketError(f"unknown organisation {org!r}")
        if tier not in pol.tiers:
            raise MarketError(f"unknown tier {tier!r}")
        if data_class not in pol.data_classes:
            raise MarketError(f"unknown data class {data_class!r}")
        if model_class not in net.model_classes():
            raise MarketError(f"unknown model class {model_class!r}")
        self._check_slot(slot)
        if gpu_hours <= 0 or max_price_eur < 0:
            raise MarketError("gpu_hours must be positive and max_price_eur non-negative")
        bid = Bid(
            id=f"bid-{len(self.bids) + 1}",
            org=org,
            slot=slot,
            tier=tier,
            data_class=data_class,
            model_class=model_class,
            gpu_hours=gpu_hours,
            max_price_eur=max_price_eur,
            remaining=gpu_hours,
        )
        self.bids.append(bid)
        return bid

    def eligible(self, bid: Bid, offer: Offer) -> tuple[bool, str]:
        net = self.world.network
        site = net.sites[offer.site]
        relation = net.relation(bid.org, site)
        if relation == "eigen":
            return False, "an organisation does not buy its own capacity"
        if net.model_for(site, bid.model_class) is None:
            return False, f"site does not host a '{bid.model_class}' model"
        probe = Request(bid.org, bid.tier, bid.data_class, task="", tokens_in=0, tokens_out=0)
        reasons = hard_exclusions(probe, site, relation, self.world)
        if reasons:
            return False, "; ".join(reasons)
        return True, relation

    def clear(self, slot: int) -> dict:
        self._check_slot(slot)
        tiers = self.world.policy.tiers
        bids = sorted(
            (b for b in self.bids if b.slot == slot and b.remaining > 0),
            key=lambda b: (tiers[b.tier].priority, -b.max_price_eur, int(b.id.split("-")[1])),
        )
        offers = sorted(
            (o for o in self.offers if o.slot == slot and o.remaining > 0),
            key=lambda o: (o.min_price_eur, int(o.id.split("-")[1])),
        )
        provisional: list[tuple[Bid, Offer, float, str]] = []
        for bid in bids:
            for offer in offers:
                if bid.remaining <= 1e-12:
                    break
                if offer.remaining <= 1e-12 or offer.min_price_eur > bid.max_price_eur:
                    continue
                ok, relation = self.eligible(bid, offer)
                if not ok:
                    continue
                quantity = min(bid.remaining, offer.remaining)
                bid.remaining -= quantity
                offer.remaining -= quantity
                provisional.append((bid, offer, quantity, relation))

        clearing = max((o.min_price_eur for _, o, _, _ in provisional), default=None)
        matches: list[Match] = []
        for bid, offer, quantity, relation in provisional:
            if self.pricing == "uniform":
                price = min(clearing, bid.max_price_eur)
            elif self.pricing == "pay_as_bid":
                price = bid.max_price_eur
            else:
                price = offer.min_price_eur
            matches.append(
                Match(
                    slot=slot,
                    bid_id=bid.id,
                    offer_id=offer.id,
                    org=bid.org,
                    site=offer.site,
                    provider=offer.provider,
                    relation=relation,
                    tier=bid.tier,
                    gpu_hours=round(quantity, 6),
                    price_eur_per_gpu_hour=round(price, 4),
                    amount_eur=round(quantity * price, 4),
                    reason=(
                        f"tier '{bid.tier}' (priority {tiers[bid.tier].priority}); "
                        f"offer {offer.min_price_eur:.2f} <= bid {bid.max_price_eur:.2f}; "
                        f"pricing '{self.pricing}'"
                    ),
                )
            )
        self.matches.extend(matches)
        self._cleared.add(slot)
        return {
            "slot": slot,
            "pricing": self.pricing,
            "clearing_price_eur": clearing,
            "matches": [asdict(m) for m in matches],
            "unmatched_bids": [asdict(b) for b in bids if b.remaining > 1e-12],
            "unmatched_offers": [asdict(o) for o in offers if o.remaining > 1e-12],
        }

    def settlement(self) -> dict:
        """Positions per party: what it bought and sold, and the money in both directions."""
        positions: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
        for m in self.matches:
            positions[m.org]["bought_gpu_hours"] += m.gpu_hours
            positions[m.org]["paid_eur"] += m.amount_eur
            positions[m.provider]["sold_gpu_hours"] += m.gpu_hours
            positions[m.provider]["received_eur"] += m.amount_eur
        keys = ("bought_gpu_hours", "paid_eur", "sold_gpu_hours", "received_eur")
        result = {}
        for party in sorted(positions):
            row = {k: round(positions[party][k], 4) for k in keys}
            row["net_eur"] = round(row["received_eur"] - row["paid_eur"], 4)
            result[party] = row
        return {"matches": [asdict(m) for m in self.matches], "positions": result}

    def state(self) -> dict:
        return {
            "pricing": self.pricing,
            "offers": [asdict(o) for o in self.offers],
            "bids": [asdict(b) for b in self.bids],
            "cleared_slots": sorted(self._cleared),
        }
