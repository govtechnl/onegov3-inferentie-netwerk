# GreenPT API (optional)

[GreenPT](https://greenpt.nl/), the tech partner of the OneGov Hackathon Series, provides an OpenAI-compatible API with credits per participant. It is an **optional resource** for teams that want real model answers in their demo instead of the simulated ones.

## Where it fits

- **As a real backend behind a gateway.** Replace a simulated site with a GreenPT endpoint, for example by replacing `mock_response` in one deployment of a LiteLLM config in [`gateways/litellm/`](../../gateways/litellm/) with the API base URL and key you receive.
- **To generate realistic requests** for your demo, for example sample questions per task.
- **To explain a routing decision** in plain language for a non-technical audience, based on the decision's explanation.

GreenPT credits are per participant. There is no built-in quota per organisation: if you want to simulate four organisations with their own budgets on top of one API, you build that yourself, which is close to the heart of this challenge.

## Where it should **not** be used

- To make routing, priority or settlement decisions. Those are explicit rules (M2, M4, S1).
- With real data of any organisation. Only simulated or public content.
- Without labelling: if part of your demo uses a real model, say which part.

## Practical notes

- **Access.** Every participant can claim free API credits through GreenPT's sign-up link, shared on [Alkemio](https://alkem.io/onegov-hackathon) and at the kick-off. Documentation: [docs.greenpt.ai](https://docs.greenpt.ai/). Use the API base URL and model names from GreenPT's own documentation.
- **Secrets.** Keep keys in environment variables, never in the repository.
- **Reproducibility.** Pin a model and log prompts and responses where they influence what the user sees.

If your submission uses GreenPT or another LLM, note in your README and your Alkemio submission **where** and **why**.

GreenPT awards a bonus prize to a team that makes good use of its API; GreenPT selects the winner. See [EVENT.md](../../EVENT.md#prizes).
