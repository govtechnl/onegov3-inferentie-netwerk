"""The simulator: invariants that must hold in every scenario and mode."""

import pytest

from inferentienet import catalog
from inferentienet.simulate import run

SCENARIOS = [s["id"] for s in catalog.load("scenarios")["scenarios"]]


@pytest.fixture(scope="module")
def results(world):
    return {
        (sc, mode): run(world, sc, mode)
        for sc in ["werkdag", "drukke-dag"]
        for mode in ["naive", "coordinated"]
    }


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_every_scenario_runs(world, scenario):
    result = run(world, scenario)
    assert result.summary["totals"]["chunks"] > 0


def test_hard_rules_hold_in_the_simulation(results, world):
    for result in results.values():
        for r in result.records:
            if not r.site:
                continue
            relation = world.network.relation(r.org, world.network.sites[r.site])
            if r.data_class == "bijzonder":
                assert relation == "eigen", r
            if r.data_class == "vertrouwelijk":
                assert relation in ("eigen", "federatie"), r


def test_all_work_is_served_on_a_normal_day(results):
    totals = results[("werkdag", "coordinated")].summary["totals"]
    assert totals["unfinished_chunks"] == 0
    assert totals["refused_chunks"] == 0
    assert totals["within_norm_share"] > 0.95


def test_work_is_conserved(results, world):
    for result in results.values():
        routed = sum(r.work_s for r in result.records if r.site)
        served = sum(s["served_s"] for s in result.site_slots)
        backlog = sum(s["backlog_s"] for s in result.site_slots if s["slot"] == result.site_slots[-1]["slot"])
        assert served + backlog == pytest.approx(routed, rel=1e-6)


def test_coordination_moves_less_work_and_protects_receiving_sites(results):
    naive = results[("drukke-dag", "naive")].summary
    coordinated = results[("drukke-dag", "coordinated")].summary
    assert coordinated["totals"]["migrated_chunks"] < naive["totals"]["migrated_chunks"]
    for site in ("min-rc1", "prov-dc1"):
        assert (
            coordinated["sites"][site]["own_users_within_norm_share"]
            >= naive["sites"][site]["own_users_within_norm_share"]
        )
        assert coordinated["sites"][site]["external_share"] < naive["sites"][site]["external_share"]


def test_settlement_balances(results):
    for result in results.values():
        positions = result.summary["settlement"]
        receivable = sum(p["receivable_eur"] for p in positions.values())
        payable = sum(p["payable_eur"] for p in positions.values())
        assert receivable == pytest.approx(payable, abs=0.01)
        federation = sum(e.amount_eur for e in result.ledger if e.relation == "federatie")
        assert payable == pytest.approx(federation, abs=0.01)


def test_simulation_is_deterministic(world):
    first = run(world, "netcongestie", "coordinated")
    second = run(world, "netcongestie", "coordinated")
    assert first.summary == second.summary
