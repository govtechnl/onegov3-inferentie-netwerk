"""Mock federated gateway for approach A: one per organisation, OpenAI-compatible, standard library only.

Each organisation runs one gateway with two faces:

  /v1/chat/completions             the internal gateway for its own users. It routes with the shared rules
                                   (router.py): own site first, otherwise another member or an external site.
  /federation/v1/chat/completions  the external gateway that other members call. It checks its OWN acceptance
                                   rules again (data class, tier, receiving protection) and may refuse.
  /federation/v1/status            the published load of its own sites, read by the other gateways.

No real model runs anywhere: answers are labelled as simulated. Start all four gateways with:

    python -m inferentienet.gateway --all

and send a request (the data class header is required; requests without it are refused):

    curl -s localhost:8104/v1/chat/completions -H 'Content-Type: application/json' \\
      -H 'X-Data-Class: vertrouwelijk' -H 'X-Tier: interactief' -H 'X-Task: chat' \\
      -d '{"model": "auto", "messages": [{"role": "user", "content": "Vat dit dossier samen"}]}'
"""

from __future__ import annotations

import argparse
import itertools
import threading
import time
from collections import OrderedDict
from collections.abc import Callable
from http.server import ThreadingHTTPServer

from .httpjson import JSONHandler, request_json
from .model import Site, World, load_world
from .router import Request as RouteRequest
from .router import RoutingError, SiteSnapshot, hard_exclusions, receiving_protection, route

MAX_ATTEMPTS = 3
MAX_DECISIONS = 500


def _error(message: str, kind: str) -> dict:
    return {"error": {"message": message, "type": kind}}


class SiteState:
    """Simulated load of one site: a backlog of reference GPU-seconds that drains at the site's rate."""

    def __init__(self, site: Site, slot_seconds: int, hour: float, clock: Callable[[], float]):
        self.site = site
        self.slot_seconds = slot_seconds
        self.hour = hour
        self.clock = clock
        self.backlog_s = 0.0
        self.external_s = 0.0
        self.last = clock()

    @property
    def rate(self) -> float:
        return self.site.rate(self.hour)

    def _drain(self) -> None:
        now = self.clock()
        elapsed = max(0.0, now - self.last)
        self.last = now
        if elapsed and self.backlog_s > 0:
            served = min(self.backlog_s, elapsed * self.rate)
            external_share = self.external_s / self.backlog_s
            self.backlog_s -= served
            self.external_s = max(0.0, self.external_s - served * external_share)

    def set_utilisation(self, share: float) -> None:
        self._drain()
        self.backlog_s = max(0.0, share) * self.rate * self.slot_seconds
        self.external_s = 0.0

    def add(self, work_s: float, external: bool) -> None:
        self._drain()
        self.backlog_s += work_s
        if external:
            self.external_s += work_s

    def status(self) -> dict:
        self._drain()
        capacity = self.rate * self.slot_seconds
        return {
            "capacity_s": round(capacity, 3),
            "load_s": round(self.backlog_s, 3),
            "external_load_s": round(self.external_s, 3),
            "utilisation": round(self.backlog_s / capacity, 4) if capacity else None,
        }

    def snapshot(self, top_priority: int) -> SiteSnapshot:
        st = self.status()
        return SiteSnapshot(
            capacity_s=st["capacity_s"],
            load_by_priority={top_priority: st["load_s"]},
            external_load_s=st["external_load_s"],
        )


class Gateway:
    def __init__(
        self,
        world: World,
        org: str,
        peers: dict[str, str] | None = None,
        hour: float = 10.0,
        clock: Callable[[], float] = time.monotonic,
        timeout: float = 3.0,
    ):
        if org not in world.network.organisations:
            raise ValueError(f"unknown organisation {org!r}")
        self.world = world
        self.org = org
        self.peers = dict(peers or {})
        self.timeout = timeout
        slot = world.policy.slot_seconds
        sites = world.network.sites.values()
        self.own = {
            s.id: SiteState(s, slot, hour, clock) for s in sites if s.kind == "overheid" and s.owner == org
        }
        # Research and commercial sites are simulated locally by every gateway.
        self.external = {s.id: SiteState(s, slot, hour, clock) for s in sites if s.kind != "overheid"}
        self.top_priority = min(t.priority for t in world.policy.tiers.values())
        self.decisions: OrderedDict[str, dict] = OrderedDict()
        self.counter = itertools.count(1)
        self.lock = threading.Lock()

    # --- state -------------------------------------------------------------------------------------------
    def status(self) -> dict:
        with self.lock:
            return {
                "org": self.org,
                "simulated": True,
                "sites": {sid: st.status() for sid, st in self.own.items()},
            }

    def set_load(self, loads: dict) -> dict:
        with self.lock:
            for site_id, share in loads.items():
                state = self.own.get(site_id) or self.external.get(site_id)
                if state is None:
                    raise ValueError(
                        f"site {site_id!r} is not run or simulated by the gateway of {self.org!r}"
                    )
                state.set_utilisation(float(share))
        return self.state()

    def state(self) -> dict:
        with self.lock:
            return {
                "org": self.org,
                "own": {sid: st.status() for sid, st in self.own.items()},
                "external": {sid: st.status() for sid, st in self.external.items()},
                "peers": self.peers,
            }

    def _peer_snapshots(self) -> dict[str, SiteSnapshot]:
        snaps: dict[str, SiteSnapshot] = {}
        for peer_org, url in self.peers.items():
            try:
                status, body, _ = request_json(f"{url}/federation/v1/status", timeout=self.timeout)
            except OSError:
                continue
            if status != 200 or not isinstance(body, dict):
                continue
            for site_id, st in body.get("sites", {}).items():
                site = self.world.network.sites.get(site_id)
                if site is None or site.owner != peer_org:
                    continue  # a peer may only report on its own sites
                snaps[site_id] = SiteSnapshot(
                    capacity_s=float(st["capacity_s"]),
                    load_by_priority={self.top_priority: float(st["load_s"])},
                    external_load_s=float(st["external_load_s"]),
                )
        return snaps

    def snapshots(self) -> dict[str, SiteSnapshot]:
        peers = self._peer_snapshots()  # network calls happen outside the lock
        with self.lock:
            snaps = {sid: st.snapshot(self.top_priority) for sid, st in self.own.items()}
            snaps.update({sid: st.snapshot(self.top_priority) for sid, st in self.external.items()})
        snaps.update(peers)
        return snaps

    # --- helpers -----------------------------------------------------------------------------------------
    def _parse(self, body: dict, headers) -> tuple[list, int, int, str | None]:
        messages = body.get("messages")
        if not isinstance(messages, list) or not messages:
            raise ValueError("'messages' must be a non-empty list")
        text = "".join(str(m.get("content", "")) for m in messages if isinstance(m, dict))
        tokens_in = max(1, len(text) // 4)
        tokens_out = int(body.get("max_tokens") or 400)
        model = body.get("model") or "auto"
        if model == "auto":
            model_class = None
        elif model in self.world.network.model_classes():
            model_class = model
        elif model in self.world.network.models:
            model_class = self.world.network.models[model].model_class
        else:
            raise ValueError(f"unknown model {model!r}; use 'auto', a model class or a model id")
        return messages, tokens_in, tokens_out, model_class

    def _completion(
        self, decision_id: str, site: str, model: str, origin: str, tokens_in: int, tokens_out: int
    ):
        return {
            "id": f"chatcmpl-sim-{decision_id}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": (
                            f"[gesimuleerd] Antwoord van {site} ({model}) voor {origin}. "
                            "Er draait geen echt model; dit is een demo-omgeving."
                        ),
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": tokens_in,
                "completion_tokens": tokens_out,
                "total_tokens": tokens_in + tokens_out,
            },
            "simulated": True,
        }

    def _remember(self, decision_id: str, record: dict) -> None:
        with self.lock:
            self.decisions[decision_id] = record
            while len(self.decisions) > MAX_DECISIONS:
                self.decisions.popitem(last=False)

    # --- internal gateway --------------------------------------------------------------------------------
    def handle_chat(self, body: dict, headers) -> tuple[int, dict, dict]:
        data_class = headers.get("X-Data-Class")
        if not data_class:
            return (
                400,
                _error(
                    "X-Data-Class header is required; requests without a data class are refused "
                    "(fail closed)",
                    "invalid_request_error",
                ),
                {},
            )
        tier = headers.get("X-Tier") or "interactief"
        task = headers.get("X-Task") or "chat"
        try:
            messages, tokens_in, tokens_out, model_class = self._parse(body, headers)
        except ValueError as exc:
            return 400, _error(str(exc), "invalid_request_error"), {}
        decision_id = f"{self.org}-{next(self.counter)}"
        req = RouteRequest(
            self.org, tier, data_class, task, tokens_in, tokens_out, model_class=model_class, id=decision_id
        )

        exclude: list[str] = []
        refusals: list[str] = []
        decision = None
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                decision = route(req, self.snapshots(), self.world, exclude=exclude)
            except RoutingError as exc:
                return 400, _error(str(exc), "invalid_request_error"), {}
            decision.steps[2:2] = refusals
            route_headers = {
                "X-Route-Outcome": decision.outcome,
                "X-Route-Site": decision.site or "",
                "X-Route-Decision": decision_id,
                "X-Simulated": "true",
            }
            routing = {
                "decision_id": decision_id,
                "outcome": decision.outcome,
                "site": decision.site,
                "model": decision.model,
                "explain": f"/decisions/{decision_id}",
            }
            if decision.outcome == "federatie":
                site = self.world.network.sites[decision.site]
                url = self.peers.get(site.owner)
                if url is None:
                    reason = f"no gateway address known for '{site.owner}'"
                else:
                    try:
                        status, resp, _ = request_json(
                            f"{url}/federation/v1/chat/completions",
                            payload={"model": decision.model, "messages": messages, "max_tokens": tokens_out},
                            headers={
                                "X-Origin-Org": self.org,
                                "X-Data-Class": data_class,
                                "X-Tier": tier,
                                "X-Task": task,
                                "X-Target-Site": site.id,
                                "X-Decision-Id": decision_id,
                            },
                            timeout=self.timeout,
                        )
                    except OSError as exc:
                        status, resp = 503, _error(f"gateway unreachable: {exc}", "api_error")
                    if status == 200:
                        decision.steps.append(
                            f"The gateway of '{site.owner}' accepted the request for {site.id}."
                        )
                        self._remember(decision_id, decision.to_dict())
                        resp["routing"] = routing
                        return 200, resp, route_headers
                    reason = (resp or {}).get("error", {}).get("message", f"HTTP {status}")
                refusals.append(f"Attempt {attempt}: {decision.site} refused the request ({reason}).")
                exclude.append(decision.site)
                continue
            if decision.outcome in ("lokaal", "extern"):
                with self.lock:
                    state = self.own.get(decision.site) or self.external[decision.site]
                    state.add(decision.work_s, external=decision.outcome != "lokaal")
                self._remember(decision_id, decision.to_dict())
                resp = self._completion(
                    decision_id, decision.site, decision.model, self.org, tokens_in, tokens_out
                )
                resp["routing"] = routing
                return 200, resp, route_headers
            self._remember(decision_id, decision.to_dict())
            if decision.outcome == "uitgesteld":
                route_headers["Retry-After"] = str(self.world.policy.slot_seconds)
                payload = _error("no site may take this request now; deferred", "rate_limit_error")
                payload["routing"] = routing
                return 429, payload, route_headers
            payload = _error("no site may run this request under the rules", "permission_error")
            payload["routing"] = routing
            return 403, payload, route_headers
        if decision is not None:
            decision.steps.append(f"Gave up after {MAX_ATTEMPTS} attempts.")
            self._remember(decision_id, decision.to_dict())
        return (
            503,
            _error("every candidate site refused the request", "api_error"),
            {"X-Route-Decision": decision_id},
        )

    # --- external gateway --------------------------------------------------------------------------------
    def handle_federation(self, body: dict, headers) -> tuple[int, dict, dict]:
        origin = headers.get("X-Origin-Org")
        target = headers.get("X-Target-Site")
        data_class = headers.get("X-Data-Class")
        tier_id = headers.get("X-Tier") or "interactief"
        task = headers.get("X-Task") or "chat"
        if origin not in self.world.network.organisations or origin == self.org:
            return (
                403,
                _error("X-Origin-Org must be another member of the federation", "permission_error"),
                {},
            )
        if not data_class:
            return 400, _error("X-Data-Class header is required", "invalid_request_error"), {}
        if target not in self.own:
            return (
                404,
                _error(f"site {target!r} is not run by the gateway of '{self.org}'", "not_found_error"),
                {},
            )
        try:
            messages, tokens_in, tokens_out, model_class = self._parse(body, headers)
        except ValueError as exc:
            return 400, _error(str(exc), "invalid_request_error"), {}
        if tier_id not in self.world.policy.tiers or data_class not in self.world.policy.data_classes:
            return 400, _error("unknown tier or data class", "invalid_request_error"), {}
        site = self.world.network.sites[target]
        model = self.world.network.model_for(site, model_class) if model_class else None
        if model is None:
            return 400, _error(f"{target} does not host the requested model", "invalid_request_error"), {}
        req = RouteRequest(origin, tier_id, data_class, task, tokens_in, tokens_out, model_class=model_class)
        reasons = hard_exclusions(req, site, "federatie", self.world)
        if reasons:
            return 403, _error("; ".join(reasons), "permission_error"), {}
        work = model.ref_gpu_seconds(tokens_in, tokens_out)
        tier = self.world.policy.tiers[tier_id]
        with self.lock:
            state = self.own[target]
            protected, _ = receiving_protection(
                state.snapshot(self.top_priority), site, tier, work, self.world.policy.coordination
            )
            if protected:
                return 429, _error(protected, "rate_limit_error"), {"Retry-After": "60"}
            state.add(work, external=True)
        decision_id = headers.get("X-Decision-Id") or "?"
        return 200, self._completion(decision_id, site.id, model.id, origin, tokens_in, tokens_out), {}


def make_server(gateway: Gateway, host: str = "127.0.0.1", port: int = 0) -> ThreadingHTTPServer:
    class Handler(JSONHandler):
        def route(self, method, path, query, body, headers):
            if method == "GET" and path == "/health":
                return 200, {"status": "ok", "org": gateway.org, "simulated": True}, {}
            if method == "GET" and path == "/v1/models":
                data = [{"id": "auto", "object": "model", "owned_by": gateway.org}]
                data += [
                    {"id": c, "object": "model", "owned_by": gateway.org}
                    for c in gateway.world.network.model_classes()
                ]
                return 200, {"object": "list", "data": data}, {}
            if method == "POST" and path == "/v1/chat/completions":
                return gateway.handle_chat(body, headers)
            if method == "GET" and path.startswith("/decisions/"):
                decision = gateway.decisions.get(path.rsplit("/", 1)[-1])
                if decision is None:
                    return 404, _error("unknown decision id", "not_found_error"), {}
                return 200, decision, {}
            if method == "GET" and path == "/federation/v1/status":
                return 200, gateway.status(), {}
            if method == "POST" and path == "/federation/v1/chat/completions":
                return gateway.handle_federation(body, headers)
            if method == "GET" and path == "/admin/state":
                return 200, gateway.state(), {}
            if method == "POST" and path == "/admin/load":
                return 200, gateway.set_load(body), {}
            return 404, _error(f"no route for {method} {path}", "not_found_error"), {}

    return ThreadingHTTPServer((host, port), Handler)


def start_all(
    world: World,
    host: str = "127.0.0.1",
    use_default_ports: bool = True,
    hour: float = 10.0,
    clock: Callable[[], float] = time.monotonic,
) -> list[tuple[Gateway, ThreadingHTTPServer, threading.Thread]]:
    """Start one gateway per organisation in background threads and wire them together as peers."""
    started = []
    for org in world.network.organisations.values():
        gateway = Gateway(world, org.id, hour=hour, clock=clock)
        server = make_server(gateway, host, org.gateway_port if use_default_ports else 0)
        started.append((gateway, server))
    urls = {gw.org: f"http://{host}:{srv.server_address[1]}" for gw, srv in started}
    result = []
    for gateway, server in started:
        gateway.peers = {org: url for org, url in urls.items() if org != gateway.org}
        thread = threading.Thread(target=server.serve_forever, name=f"gateway-{gateway.org}", daemon=True)
        thread.start()
        result.append((gateway, server, thread))
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run mock federated gateways.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--all", action="store_true", help="run all four gateways in one process")
    group.add_argument("--org", help="run the gateway of one organisation")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=None, help="default: gateway_port from network.yaml")
    parser.add_argument(
        "--peer",
        action="append",
        default=[],
        metavar="ORG=URL",
        help="peer gateway (default: localhost ports)",
    )
    parser.add_argument("--hour", type=float, default=10.0, help="hour of day for availability windows")
    args = parser.parse_args(argv)
    world = load_world()

    if args.all:
        started = start_all(world, args.host, hour=args.hour)
        for gateway, server, _ in started:
            print(f"{gateway.org:12} http://{args.host}:{server.server_address[1]}")
        print("All four mock gateways are running. Ctrl+C to stop.")
        try:
            threading.Event().wait()
        except KeyboardInterrupt:
            pass
        for _, server, _ in started:
            server.shutdown()
        return 0

    peers = {
        o.id: f"http://{args.host}:{o.gateway_port}"
        for o in world.network.organisations.values()
        if o.id != args.org
    }
    for value in args.peer:
        org, _, url = value.partition("=")
        peers[org] = url
    gateway = Gateway(world, args.org, peers, hour=args.hour)
    port = args.port or world.network.organisations[args.org].gateway_port
    server = make_server(gateway, args.host, port)
    print(f"Mock gateway of '{args.org}' on http://{args.host}:{port}. Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
