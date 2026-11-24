"""Schema checks and cross-references for everything in data/."""

from pathlib import Path

import pytest

from inferentienet import catalog
from inferentienet.model import cross_check


@pytest.mark.parametrize("name", sorted(catalog.CATALOGUES))
def test_catalogue_matches_schema(name):
    data = catalog.load_yaml(catalog.DATA_DIR / catalog.CATALOGUES[name])
    assert catalog.validate(name, data) == []


def test_network_and_policy_are_consistent():
    network = catalog.load("network")
    policy = catalog.load("policy")
    assert cross_check(network, policy) == []


def test_four_roles_from_the_brief_are_present():
    roles = {o["role"] for o in catalog.load("network")["organisations"]}
    assert roles == {"ministerie", "uitvoeringsorganisatie", "provincie", "gemeente"}


def test_every_task_has_a_model_class(world):
    for task in world.policy.tasks:
        assert any(rule.task == task for rule in world.policy.task_models)


def test_scenarios_refer_to_known_ids(world):
    scenarios = catalog.load("scenarios")["scenarios"]
    ids = [s["id"] for s in scenarios]
    assert len(ids) == len(set(ids))
    for scenario in scenarios:
        assert (catalog.DATA_DIR / scenario["demand"]).exists(), scenario["demand"]
        for overlay in scenario["overlays"]:
            assert overlay["start"] < overlay["end"]
            if "org" in overlay:
                assert overlay["org"] in world.network.organisations
            if "site" in overlay:
                assert overlay["site"] in world.network.sites
            if "tier" in overlay:
                assert overlay["tier"] in world.policy.tiers
            if "data_class" in overlay:
                assert overlay["data_class"] in world.policy.data_classes
            if "task" in overlay:
                assert overlay["task"] in world.policy.tasks


def test_demand_file_rows_are_valid(world):
    rows = catalog.read_demand(Path("demand/werkdag.csv"))
    assert rows, "demand file is empty"
    ids = [r["workload_id"] for r in rows]
    assert len(ids) == len(set(ids)), "workload ids must be unique"
    orgs = {r["org"] for r in rows}
    assert orgs == set(world.network.organisations), "demand covers all four fictitious organisations"
    for row in rows:
        assert row["tier"] in world.policy.tiers
        assert row["data_class"] in world.policy.data_classes
        assert row["task"] in world.policy.tasks
        assert row["time"] == f"{row['slot'] // 4:02d}:{(row['slot'] % 4) * 15:02d}"


def test_demand_file_is_reproducible(world):
    from inferentienet.demand import generate

    path = catalog.DATA_DIR / "demand" / "werkdag.csv"
    regenerated = generate(world)
    assert regenerated == catalog.read_demand(path), "run: python -m inferentienet.demand"


def test_litellm_configs_are_up_to_date(world):
    from inferentienet.litellm_config import OUT_DIR, render

    for org in world.network.organisations:
        path = OUT_DIR / f"{org}.yaml"
        assert path.exists(), f"missing {path}"
        assert path.read_text(encoding="utf-8") == render(world, org), (
            "run: python -m inferentienet.litellm_config"
        )
