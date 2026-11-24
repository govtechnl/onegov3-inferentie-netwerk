"""Market mechanism (approach B): matching order, eligibility and pricing."""

import pytest

from inferentienet.market import Market, MarketError


def test_kritiek_is_matched_before_a_higher_paying_batch_bid(world):
    market = Market(world)
    market.add_offer("uvo-rc1", slot=40, gpu_hours=1.0, min_price_eur=2.0)
    market.add_bid("ministerie", 40, "batch", "intern", "klein", gpu_hours=1.0, max_price_eur=9.0)
    market.add_bid("provincie", 40, "kritiek", "vertrouwelijk", "groot", gpu_hours=1.0, max_price_eur=2.5)
    result = market.clear(40)
    assert [m["org"] for m in result["matches"]] == ["provincie"]
    assert result["unmatched_bids"][0]["org"] == "ministerie"


def test_bijzonder_bids_never_match_another_organisation(world):
    market = Market(world)
    market.add_offer("min-rc1", 10, 5.0, 0.5)
    market.add_offer("eu-cloud", 10, 5.0, 0.5)
    market.add_bid("uitvoering", 10, "interactief", "bijzonder", "klein", 1.0, 10.0)
    assert market.clear(10)["matches"] == []


def test_vertrouwelijk_does_not_match_a_commercial_offer(world):
    market = Market(world)
    market.add_offer("eu-cloud", 12, 5.0, 0.1)
    market.add_offer("prov-dc1", 12, 5.0, 3.0)
    market.add_bid("gemeenten", 12, "interactief", "vertrouwelijk", "middel", 1.0, 4.0)
    matches = market.clear(12)["matches"]
    assert [m["site"] for m in matches] == ["prov-dc1"]


@pytest.mark.parametrize(
    "pricing, expected",
    [("uniform", [3.0, 3.0]), ("pay_as_bid", [5.0, 4.0]), ("pay_as_offer", [2.0, 3.0])],
)
def test_pricing_rules(world, pricing, expected):
    market = Market(world, pricing)
    market.add_offer("uvo-rc1", 20, 1.0, 2.0)
    market.add_offer("min-rc1", 20, 1.0, 3.0)
    market.add_bid("gemeenten", 20, "interactief", "intern", "klein", 1.0, 5.0)
    market.add_bid("provincie", 20, "interactief", "intern", "klein", 1.0, 4.0)
    matches = market.clear(20)["matches"]
    assert [m["price_eur_per_gpu_hour"] for m in matches] == expected


def test_settlement_sums_to_zero(world):
    market = Market(world)
    market.add_offer("uvo-rc1", 30, 2.0, 2.0)
    market.add_bid("gemeenten", 30, "interactief", "intern", "middel", 1.5, 3.0)
    market.clear(30)
    positions = market.settlement()["positions"]
    assert sum(p["net_eur"] for p in positions.values()) == pytest.approx(0)
    assert positions["uitvoering"]["sold_gpu_hours"] == pytest.approx(1.5)


def test_invalid_input_is_rejected(world):
    market = Market(world)
    with pytest.raises(MarketError):
        market.add_offer("onbekend", 1, 1.0, 1.0)
    with pytest.raises(MarketError):
        market.add_bid("gemeenten", 1, "interactief", "geheim", "klein", 1.0, 1.0)
    market.clear(1)
    with pytest.raises(MarketError):
        market.add_offer("uvo-rc1", 1, 1.0, 1.0)
