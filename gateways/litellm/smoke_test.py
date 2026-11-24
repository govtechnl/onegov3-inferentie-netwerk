"""Check what the generated LiteLLM configs do with data-class tags. Needs LiteLLM, no network, no models.

    pip install -r gateways/litellm/requirements.txt
    python gateways/litellm/smoke_test.py

Every deployment in the configs answers with a mock_response, so this only exercises LiteLLM's routing:
tag filtering and fallbacks. Expected output: every line starts with PASS, plus two NOTE lines that show
pitfalls you have to handle yourself.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import yaml
from litellm import Router

HERE = Path(__file__).resolve().parent


def router(org: str) -> Router:
    config = yaml.safe_load((HERE / f"{org}.yaml").read_text(encoding="utf-8"))
    return Router(model_list=config["model_list"], **config["router_settings"])


async def answers(r: Router, model: str, tags: list[str] | None, force_fallback: bool = False, n: int = 8) -> set[str]:
    seen = set()
    for _ in range(n):
        kwargs: dict = {}
        if tags is not None:
            kwargs["metadata"] = {"tags": tags}
        if force_fallback:
            kwargs["mock_testing_fallbacks"] = True
        try:
            resp = await r.acompletion(model=model, messages=[{"role": "user", "content": "hoi"}], **kwargs)
            seen.add(resp.choices[0].message.content)
        except Exception as exc:  # noqa: BLE001 - we want to show any refusal
            seen.add(f"REFUSED ({type(exc).__name__})")
    return seen


def check(label: str, ok: bool, seen: set[str]) -> None:
    print(f"{'PASS' if ok else 'FAIL'}  {label}")
    for answer in sorted(seen):
        print(f"        {answer}")


async def main() -> None:
    gemeenten, uitvoering = router("gemeenten"), router("uitvoering")

    seen = await answers(gemeenten, "middel", ["vertrouwelijk"])
    check("gemeenten, middel, vertrouwelijk: only federation sites", all("federatie" in a for a in seen), seen)

    seen = await answers(gemeenten, "middel", ["intern"], force_fallback=True, n=1)
    check("gemeenten, middel, intern, forced fallback: commercial EU site", any("eu-cloud" in a for a in seen), seen)

    seen = await answers(gemeenten, "middel", ["vertrouwelijk"], force_fallback=True, n=1)
    check("gemeenten, middel, vertrouwelijk, forced fallback: refused", seen == {"REFUSED (InternalServerError)"}, seen)

    seen = await answers(uitvoering, "klein", ["bijzonder"])
    check("uitvoering, klein, bijzonder: own site only", all("lokaal" in a for a in seen), seen)

    seen = await answers(uitvoering, "klein", ["bijzonder"], force_fallback=True, n=1)
    check("uitvoering, klein, bijzonder, forced fallback: refused", all(a.startswith("REFUSED") for a in seen), seen)

    seen = await answers(gemeenten, "middel-extern", None, n=1)
    print("NOTE  a request WITHOUT tags is not filtered: it reaches whatever the model group contains")
    for answer in sorted(seen):
        print(f"        {answer}")

    seen = await answers(gemeenten, "middel-extern", ["bijzonder", "openbaar"], n=1)
    print("NOTE  with two tags, one matching tag is enough: never send more than the one data class")
    for answer in sorted(seen):
        print(f"        {answer}")


if __name__ == "__main__":
    asyncio.run(main())
