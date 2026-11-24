"""Mock market API for approach B (priority tiers, bids, offers, clearing, settlement). Standard library only.

    python -m inferentienet.market_api --port 8200

The API is described in docs/api/market-mock.openapi.yaml. State lives in memory and is lost on restart.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
from http.server import ThreadingHTTPServer
from threading import Lock

from .httpjson import JSONHandler
from .market import PRICING, Market, MarketError
from .model import World, load_world


def make_server(world: World, host: str = "127.0.0.1", port: int = 8200, pricing: str = "uniform"):
    market = Market(world, pricing)
    lock = Lock()

    class Handler(JSONHandler):
        def route(self, method, path, query, body, headers):
            with lock:
                return self._route(method, path, query, body)

        def _route(self, method, path, query, body):
            slot = int(query["slot"]) if "slot" in query else None
            if method == "GET" and path == "/health":
                return 200, {"status": "ok", "simulated": True, "pricing": market.pricing}, {}
            if method == "GET" and path == "/tiers":
                tiers = [asdict(t) for t in sorted(world.policy.tiers.values(), key=lambda t: t.priority)]
                return 200, {"tiers": tiers}, {}
            if method == "GET" and path == "/offers":
                offers = [o for o in market.state()["offers"] if slot is None or o["slot"] == slot]
                return 200, {"offers": offers}, {}
            if method == "GET" and path == "/bids":
                bids = [b for b in market.state()["bids"] if slot is None or b["slot"] == slot]
                return 200, {"bids": bids}, {}
            if method == "GET" and path == "/settlement":
                return 200, market.settlement(), {}
            try:
                if method == "POST" and path == "/offers":
                    offer = market.add_offer(
                        site=body["site"],
                        slot=int(body["slot"]),
                        gpu_hours=float(body["gpu_hours"]),
                        min_price_eur=float(body["min_price_eur"]),
                    )
                    return 201, asdict(offer), {}
                if method == "POST" and path == "/bids":
                    bid = market.add_bid(
                        org=body["org"],
                        slot=int(body["slot"]),
                        tier=body["tier"],
                        data_class=body["data_class"],
                        model_class=body["model_class"],
                        gpu_hours=float(body["gpu_hours"]),
                        max_price_eur=float(body["max_price_eur"]),
                    )
                    return 201, asdict(bid), {}
                if method == "POST" and path == "/clear":
                    return 200, market.clear(int(body["slot"])), {}
                if method == "POST" and path == "/reset":
                    market.reset()
                    return 200, {"status": "reset"}, {}
            except KeyError as exc:
                return 400, {"error": f"missing field {exc.args[0]!r}"}, {}
            except (MarketError, TypeError, ValueError) as exc:
                return 400, {"error": str(exc)}, {}
            return 404, {"error": f"no route for {method} {path}"}, {}

    server = ThreadingHTTPServer((host, port), Handler)
    server.market = market  # type: ignore[attr-defined]
    return server


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the mock market API.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8200)
    parser.add_argument("--pricing", choices=PRICING, default="uniform")
    args = parser.parse_args(argv)
    server = make_server(load_world(), args.host, args.port, args.pricing)
    print(f"Mock market API on http://{args.host}:{args.port} (pricing: {args.pricing}). Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
