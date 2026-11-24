"""Scripted demo of approach A: four mock gateways, a few requests, and why each one went where it went.

    python examples/federation_demo.py

Starts the four mock gateways on free local ports, sends requests over HTTP like an application would,
and prints the routing decision with its reasons. Everything is simulated.
"""

from __future__ import annotations

from inferentienet.gateway import start_all
from inferentienet.httpjson import request_json
from inferentienet.model import load_world


def ask(urls: dict, org: str, data_class: str, tier: str = "interactief", task: str = "chat") -> None:
    headers = {"X-Data-Class": data_class, "X-Tier": tier, "X-Task": task}
    body = {"model": "auto", "messages": [{"role": "user", "content": "Vat dit dossier samen. " * 300}]}
    status, resp, resp_headers = request_json(f"{urls[org]}/v1/chat/completions", body, headers)
    print(
        f"\n> {org} asks ({data_class}, {tier}, {task}): HTTP {status}, {resp_headers.get('X-Route-Outcome')}"
        f" {resp_headers.get('X-Route-Site') or ''}"
    )
    decision_id = resp_headers.get("X-Route-Decision")
    if decision_id:
        _, decision, _ = request_json(f"{urls[org]}/decisions/{decision_id}")
        for step in decision["steps"][2:]:
            print(f"    - {step}")


def main() -> None:
    world = load_world()
    started = start_all(world, use_default_ports=False)
    urls = {gw.org: f"http://127.0.0.1:{srv.server_address[1]}" for gw, srv, _ in started}
    try:
        print("1. A quiet moment: every organisation has room.")
        ask(urls, "uitvoering", "bijzonder", task="samenvatten")
        ask(urls, "gemeenten", "vertrouwelijk")

        print("\n2. The executive agency is overloaded (its own site at 95%).")
        request_json(f"{urls['uitvoering']}/admin/load", {"uvo-rc1": 0.95})
        ask(urls, "gemeenten", "vertrouwelijk")
        ask(urls, "provincie", "vertrouwelijk", tier="kritiek", task="analyse")

        print("\n3. All government sites are busy.")
        request_json(f"{urls['ministerie']}/admin/load", {"min-rc1": 0.95})
        request_json(f"{urls['provincie']}/admin/load", {"prov-dc1": 0.95})
        ask(urls, "gemeenten", "vertrouwelijk")
        ask(urls, "gemeenten", "intern")

        print("\n4. Data that may never leave its own organisation.")
        request_json(f"{urls['uitvoering']}/admin/load", {"uvo-rc1": 3.0})
        ask(urls, "uitvoering", "bijzonder", task="classificeren")
        ask(urls, "gemeenten", "bijzonder")
    finally:
        for _, server, _ in started:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    main()
