"""Generate a LiteLLM proxy config per organisation (gateways/litellm/<org>.yaml) from the data files.

Each config makes LiteLLM act as the organisation's local gateway:

* one model group per model class (klein, middel, groot, embedding), pointing at the own site when the
  organisation hosts that class;
* '<class>-federatie' groups for the sites of the other members, and '<class>-extern' groups for research
  and commercial sites, used as fallbacks in that order;
* every deployment is tagged with the data classes it may receive (from policy.yaml and the site's
  acceptance rules). With tag filtering on, a request tagged 'bijzonder' can only reach the own site, and
  a fallback that is not allowed fails instead of leaking data.

All deployments use LiteLLM's mock_response, so no model and no network call is needed. Tested with
LiteLLM 1.110.3, see gateways/litellm/README.md.

    python -m inferentienet.litellm_config            # (re)write gateways/litellm/*.yaml
    python -m inferentienet.litellm_config --check    # fail if a committed config is out of date
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

from . import catalog
from .model import World, load_world

OUT_DIR = catalog.REPO_ROOT / "gateways" / "litellm"
LOCAL_BACKEND = "http://127.0.0.1:9/v1"  # never called: every deployment has a mock_response

HEADER = """\
# LiteLLM proxy config for '{org}' (fictitious), GENERATED from data/network.yaml and data/policy.yaml.
# Do not edit by hand: change the data files and run  python -m inferentienet.litellm_config  in tooling/.
#
# Every deployment answers with a mock_response: no model runs and nothing leaves your machine.
# Run with:  LITELLM_MASTER_KEY=sk-<your-own-random-key> litellm --config {file} --port {port}
# Tag each request with exactly ONE data class, e.g. "metadata": {{"tags": ["vertrouwelijk"]}}.
"""


def allowed_tags(world: World, org: str, site_id: str) -> list[str]:
    """Data classes that this organisation may send to this site, in policy order."""
    net, pol = world.network, world.policy
    site = net.sites[site_id]
    relation = net.relation(org, site)
    tags = []
    for data_class in pol.data_classes.values():
        if relation not in data_class.allowed_relations:
            continue
        if relation != "eigen" and data_class.id not in site.accepts_data_classes:
            continue
        if relation == "commercieel" and any(
            p not in site.properties for p in data_class.commercial_requires
        ):
            continue
        tags.append(data_class.id)
    return tags


def build_config(world: World, org: str) -> dict:
    net = world.network
    model_list: list[dict] = []
    fallbacks: list[dict] = []
    for model_class in net.model_classes():
        groups: list[str] = []
        for relation_group in ("eigen", "federatie", "extern"):
            entries = []
            for site in net.sites.values():
                model = net.model_for(site, model_class)
                if model is None:
                    continue
                relation = net.relation(org, site)
                group_relation = "extern" if relation in ("onderzoek", "commercieel") else relation
                if group_relation != relation_group:
                    continue
                if relation != "eigen" and "interactief" not in site.accepts_tiers:
                    continue  # batch-only sites are left out: LiteLLM tags here only carry the data class
                tags = allowed_tags(world, org, site.id)
                if not tags:
                    continue
                if relation == "federatie":
                    port = net.organisations[site.owner].gateway_port
                    api_base = f"http://127.0.0.1:{port}/federation/v1"
                    label = f"federatie: {site.owner} / {site.id}"
                elif relation == "eigen":
                    api_base = LOCAL_BACKEND
                    label = f"lokaal: {org} / {site.id}"
                else:
                    api_base = LOCAL_BACKEND
                    label = f"extern: {site.id}"
                entries.append(
                    {
                        "litellm_params": {
                            "model": f"openai/{model.id}",
                            "api_base": api_base,
                            "api_key": "not-used",
                            "mock_response": f"[gesimuleerd] {label} / {model.id}",
                            "tags": tags,
                        },
                        "model_info": {"id": f"{org}-{site.id}-{model_class}"},
                    }
                )
            if not entries:
                continue
            name = model_class if not groups else f"{model_class}-{relation_group}"
            for e in entries:
                model_list.append({"model_name": name, **e})
            groups.append(name)
        if len(groups) > 1:
            fallbacks.append({groups[0]: groups[1:]})
    return {
        "model_list": model_list,
        "router_settings": {"enable_tag_filtering": True, "fallbacks": fallbacks},
        "general_settings": {
            # Local demo only: lets you force a fallback with "mock_testing_fallbacks": true in a request.
            "dangerously_allow_mock_testing_request_params": True,
        },
    }


def render(world: World, org: str) -> str:
    port = 4000 + list(world.network.organisations).index(org) + 1
    header = HEADER.format(org=org, file=f"gateways/litellm/{org}.yaml", port=port)
    body = yaml.safe_dump(build_config(world, org), sort_keys=False, allow_unicode=True, width=110)
    return header + body


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate LiteLLM configs per organisation.")
    parser.add_argument("--out", type=Path, default=OUT_DIR)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    world = load_world()
    stale = []
    for org in world.network.organisations:
        path = args.out / f"{org}.yaml"
        text = render(world, org)
        if args.check:
            if not path.exists() or path.read_text(encoding="utf-8") != text:
                stale.append(path.name)
            continue
        args.out.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        print(f"wrote {path}")
    if stale:
        print(f"out of date: {', '.join(stale)}; run without --check", file=sys.stderr)
        return 1
    if args.check:
        print("LiteLLM configs are up to date")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
