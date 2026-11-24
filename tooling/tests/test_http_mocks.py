"""The mock market API and the mock federated gateways, over real HTTP on free local ports."""

import threading
from pathlib import Path

import pytest
import yaml

from inferentienet.gateway import start_all
from inferentienet.httpjson import request_json
from inferentienet.market_api import make_server as make_market_server

API_SPEC = Path(__file__).resolve().parents[2] / "docs" / "api" / "market-mock.openapi.yaml"


@pytest.fixture()
def market_url(world):
    server = make_market_server(world, port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()
    server.server_close()


@pytest.fixture()
def gateways(world):
    frozen = lambda: 0.0  # noqa: E731 - no time passes, so load does not drain during a test
    started = start_all(world, use_default_ports=False, clock=frozen)
    urls = {gw.org: f"http://127.0.0.1:{srv.server_address[1]}" for gw, srv, _ in started}
    yield urls
    for _, server, _ in started:
        server.shutdown()
        server.server_close()


def chat(url, data_class=None, tier="interactief", task="chat", model="auto"):
    headers = {"X-Tier": tier, "X-Task": task}
    if data_class:
        headers["X-Data-Class"] = data_class
    body = {"model": model, "messages": [{"role": "user", "content": "Vat dit dossier samen. " * 200}]}
    return request_json(f"{url}/v1/chat/completions", body, headers)


def test_market_api_round_trip(market_url):
    status, _, _ = request_json(
        f"{market_url}/offers", {"site": "uvo-rc1", "slot": 40, "gpu_hours": 2, "min_price_eur": 2.0}
    )
    assert status == 201
    bid = {
        "org": "gemeenten",
        "slot": 40,
        "tier": "interactief",
        "data_class": "intern",
        "model_class": "middel",
        "gpu_hours": 1.5,
        "max_price_eur": 3.0,
    }
    assert request_json(f"{market_url}/bids", bid)[0] == 201
    status, result, _ = request_json(f"{market_url}/clear", {"slot": 40})
    assert status == 200 and result["matches"][0]["site"] == "uvo-rc1"
    status, settlement, _ = request_json(f"{market_url}/settlement")
    assert settlement["positions"]["gemeenten"]["paid_eur"] == pytest.approx(3.0)


def test_market_api_rejects_bad_input(market_url):
    status, body, _ = request_json(f"{market_url}/bids", {"org": "gemeenten"})
    assert status == 400 and "missing field" in body["error"]


def test_market_openapi_spec_is_valid():
    from openapi_spec_validator import validate

    validate(yaml.safe_load(API_SPEC.read_text(encoding="utf-8")))


def test_gateway_requires_a_data_class(gateways):
    status, body, _ = chat(gateways["gemeenten"])
    assert status == 400
    assert "X-Data-Class" in body["error"]["message"]


def test_gateway_routes_locally_first(gateways):
    status, body, headers = chat(gateways["uitvoering"], "bijzonder")
    assert status == 200
    assert headers["X-Route-Outcome"] == "lokaal" and headers["X-Route-Site"] == "uvo-rc1"
    assert body["simulated"] is True


def test_bijzonder_waits_at_home_when_the_own_site_is_full(gateways):
    request_json(f"{gateways['uitvoering']}/admin/load", {"uvo-rc1": 3.0})
    status, body, headers = chat(gateways["uitvoering"], "bijzonder")
    assert status == 200 and headers["X-Route-Site"] == "uvo-rc1"
    _, decision, _ = request_json(f"{gateways['uitvoering']}{body['routing']['explain']}")
    assert decision["within_norm"] is False


def test_federation_request_is_accepted_and_counted_by_the_receiver(gateways):
    status, body, headers = chat(gateways["gemeenten"], "vertrouwelijk")
    assert status == 200 and headers["X-Route-Outcome"] == "federatie"
    site = headers["X-Route-Site"]
    owner = {"min-rc1": "ministerie", "uvo-rc1": "uitvoering", "prov-dc1": "provincie"}[site]
    _, status_body, _ = request_json(f"{gateways[owner]}/federation/v1/status")
    assert status_body["sites"][site]["external_load_s"] > 0
    assert site in body["choices"][0]["message"]["content"]


def test_busy_peer_is_skipped_using_its_published_status(gateways):
    request_json(f"{gateways['uitvoering']}/admin/load", {"uvo-rc1": 0.95})
    status, _, headers = chat(gateways["gemeenten"], "vertrouwelijk")
    assert status == 200 and headers["X-Route-Site"] in ("min-rc1", "prov-dc1")


def test_receiver_enforces_its_own_rules(gateways):
    headers = {"X-Origin-Org": "gemeenten", "X-Target-Site": "uvo-rc1", "X-Data-Class": "bijzonder"}
    body = {"model": "nl-middel-32b", "messages": [{"role": "user", "content": "x"}]}
    status, resp, _ = request_json(f"{gateways['uitvoering']}/federation/v1/chat/completions", body, headers)
    assert status == 403 and "bijzonder" in resp["error"]["message"]
    request_json(f"{gateways['uitvoering']}/admin/load", {"uvo-rc1": 0.95})
    headers["X-Data-Class"] = "intern"
    status, resp, _ = request_json(f"{gateways['uitvoering']}/federation/v1/chat/completions", body, headers)
    assert status == 429 and "receiving protection" in resp["error"]["message"]


def test_deferred_when_every_allowed_site_is_busy(gateways):
    for org, site in (("ministerie", "min-rc1"), ("uitvoering", "uvo-rc1"), ("provincie", "prov-dc1")):
        request_json(f"{gateways[org]}/admin/load", {site: 0.95})
    status, body, headers = chat(gateways["gemeenten"], "vertrouwelijk")
    assert status == 429
    assert headers["Retry-After"] == "900"
    assert body["routing"]["outcome"] == "uitgesteld"
