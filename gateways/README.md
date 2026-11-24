# Gateways

Two ways to run a federated gateway setup locally, both fully simulated:

| Option | What it is | Start here |
|---|---|---|
| **Python mock gateways** | One OpenAI-compatible gateway per organisation with internal and external routing, the shared rules from `data/policy.yaml`, receiving gateways that re-check their own rules, and an explanation per decision. Standard library only. | [`tooling/README.md`](../tooling/README.md#mock-gateways) |
| **LiteLLM configs** | A LiteLLM proxy config per organisation: own site first, then the federation, then external sites, with data-class tags so that data cannot fall back to a site where it may not go. | [`litellm/README.md`](litellm/README.md) |

They are starting points. Teams can connect an existing gateway of their own, extend one of these, or design something else.
