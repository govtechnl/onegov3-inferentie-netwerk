"""The routing rules from policy.yaml, one behaviour per test."""

import itertools
import random

import pytest

from inferentienet.router import Request, RoutingError, route, snapshots_from_utilisation


def req(
    org="gemeenten",
    tier="interactief",
    data_class="intern",
    task="chat",
    tokens_in=4000,
    tokens_out=400,
    **kw,
):
    return Request(org, tier, data_class, task, tokens_in, tokens_out, **kw)


def test_bijzonder_never_leaves_its_own_organisation(world):
    rng = random.Random(7)
    for org, tier, task, mode in itertools.product(
        world.network.organisations,
        world.policy.tiers,
        ["chat", "samenvatten", "classificeren"],
        ["naive", "coordinated"],
    ):
        loads = {site: rng.choice([0.0, 0.5, 0.9, 1.5, 3.0]) for site in world.network.sites}
        decision = route(
            req(org, tier, "bijzonder", task), snapshots_from_utilisation(world, 10, loads), world, mode
        )
        if decision.site:
            assert decision.relation == "eigen", decision.explain()


def test_vertrouwelijk_never_goes_to_research_or_commercial_sites(world):
    rng = random.Random(11)
    for org, tier, mode in itertools.product(
        world.network.organisations, world.policy.tiers, ["naive", "coordinated"]
    ):
        for _ in range(5):
            loads = {site: rng.choice([0.0, 0.8, 2.0]) for site in world.network.sites}
            decision = route(
                req(org, tier, "vertrouwelijk"), snapshots_from_utilisation(world, 2, loads), world, mode
            )
            if decision.site:
                assert decision.relation in ("eigen", "federatie"), decision.explain()


def test_task_rules_pick_the_model_class(world):
    snaps = snapshots_from_utilisation(world, 10)
    assert route(req(task="zoeken"), snaps, world).model_class == "embedding"
    assert route(req(task="samenvatten", tokens_in=6000), snaps, world).model_class == "klein"
    assert route(req(task="samenvatten", tokens_in=20000), snaps, world).model_class == "middel"
    assert route(req(task="analyse"), snaps, world).model_class == "groot"


def test_stays_local_when_own_site_meets_the_norm(world):
    decision = route(req("ministerie", data_class="intern"), snapshots_from_utilisation(world, 10), world)
    assert decision.outcome == "lokaal"
    assert decision.site == "min-rc1"
    assert "stays local" in decision.steps[-1]


def test_organisation_without_the_model_uses_the_federation(world):
    decision = route(
        req("gemeenten", data_class="vertrouwelijk", task="chat"),
        snapshots_from_utilisation(world, 10),
        world,
    )
    assert decision.outcome == "federatie"
    assert decision.site in ("min-rc1", "uvo-rc1", "prov-dc1")


def test_receiving_protection_skips_a_busy_site(world):
    snaps = snapshots_from_utilisation(world, 10, {"uvo-rc1": 0.95})
    decision = route(req("gemeenten", data_class="vertrouwelijk"), snaps, world, "coordinated")
    assert decision.site != "uvo-rc1"
    assert any("Skipped uvo-rc1: receiving protection" in s for s in decision.steps)


def test_naive_mode_ignores_receiving_protection(world):
    # Everything else busier than uvo-rc1, which is above the protection threshold.
    loads = {"uvo-rc1": 0.95, "min-rc1": 1.5, "prov-dc1": 1.5}
    snaps = snapshots_from_utilisation(world, 10, loads)
    naive = route(req("gemeenten", data_class="vertrouwelijk"), snaps, world, "naive")
    assert naive.site == "uvo-rc1"


def test_minimum_gain_keeps_small_improvements_local(world):
    # Own site about 18 s behind, over the 5 s norm for kritiek. Another site would save less than the
    # minimum gain of 30 s once the transfer overhead and the switching toll are counted.
    snaps = snapshots_from_utilisation(world, 10, {"min-rc1": 1.02})
    decision = route(req("ministerie", tier="kritiek", data_class="intern"), snaps, world, "coordinated")
    assert decision.outcome == "lokaal"
    assert "less than the minimum gain" in decision.steps[-1]
    naive = route(req("ministerie", tier="kritiek", data_class="intern"), snaps, world, "naive")
    assert naive.outcome != "lokaal"


def test_large_gain_moves_the_request(world):
    snaps = snapshots_from_utilisation(world, 10, {"min-rc1": 3.0})
    decision = route(req("ministerie", data_class="intern"), snaps, world, "coordinated")
    assert decision.outcome in ("federatie", "extern")


def test_kritiek_may_use_the_solidarity_reserve_of_a_busy_site(world):
    # provincie has no 'groot' model; only uvo-rc1 may run vertrouwelijk work on it.
    snaps = snapshots_from_utilisation(world, 10, {"uvo-rc1": 0.95})
    critical = route(req("provincie", "kritiek", "vertrouwelijk", "analyse"), snaps, world, "coordinated")
    assert critical.site == "uvo-rc1"
    assert any("solidarity reserve" in s for s in critical.steps)
    interactive = route(
        req("provincie", "interactief", "vertrouwelijk", "analyse"), snaps, world, "coordinated"
    )
    assert interactive.outcome == "uitgesteld"


def test_defers_when_every_allowed_site_is_protected(world):
    snaps = snapshots_from_utilisation(world, 10, {"min-rc1": 0.95, "uvo-rc1": 0.95, "prov-dc1": 0.95})
    decision = route(req("gemeenten", data_class="vertrouwelijk"), snaps, world, "coordinated")
    assert decision.outcome == "uitgesteld"
    assert decision.site is None


def test_refused_when_no_site_may_run_it(world):
    # gemeenten has no 'middel' model itself, and bijzonder may not leave the organisation.
    decision = route(
        req("gemeenten", data_class="bijzonder", task="chat"), snapshots_from_utilisation(world, 10), world
    )
    assert decision.outcome == "geweigerd"


def test_research_site_only_takes_batch_and_only_at_night(world):
    day = route(
        req("ministerie", "batch", "openbaar", "samenvatten", 6000, 600),
        snapshots_from_utilisation(world, 12),
        world,
    )
    night = route(
        req("ministerie", "batch", "openbaar", "samenvatten", 6000, 600),
        snapshots_from_utilisation(world, 2),
        world,
    )
    assert day.site != "onderzoek-ai"
    assert night.site == "onderzoek-ai", night.explain()
    interactive = route(
        req("ministerie", "interactief", "openbaar"),
        snapshots_from_utilisation(world, 2, {"min-rc1": 3}),
        world,
    )
    assert interactive.site != "onderzoek-ai"


def test_commercial_site_needs_the_required_properties(world):
    from dataclasses import replace

    from inferentienet.model import World

    sites = dict(world.network.sites)
    sites["eu-cloud"] = replace(sites["eu-cloud"], properties=frozenset({"eu_jurisdiction", "zdr"}))
    weaker = World(replace(world.network, sites=sites), world.policy)
    snaps = snapshots_from_utilisation(weaker, 10, {"min-rc1": 3, "uvo-rc1": 3, "prov-dc1": 3})
    decision = route(req("gemeenten", data_class="intern"), snaps, weaker, "naive")
    eu = next(c for c in decision.candidates if c.site == "eu-cloud")
    assert any("no_training" in reason for reason in eu.excluded)


def test_every_decision_is_explained_and_deterministic(world):
    snaps = snapshots_from_utilisation(world, 10, {"uvo-rc1": 0.5})
    first = route(req("gemeenten", data_class="vertrouwelijk", id="x-1"), snaps, world)
    second = route(req("gemeenten", data_class="vertrouwelijk", id="x-1"), snaps, world)
    assert first.to_dict() == second.to_dict()
    assert first.site in first.steps[-1]
    assert len(first.candidates) >= 3


def test_invalid_requests_raise(world):
    snaps = snapshots_from_utilisation(world, 10)
    with pytest.raises(RoutingError):
        route(req(org="onbekend"), snaps, world)
    with pytest.raises(RoutingError):
        route(req(data_class="geheim"), snaps, world)
    with pytest.raises(RoutingError):
        route(req(task="dichten"), snaps, world)
