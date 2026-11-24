# LiteLLM configs per organisation

[LiteLLM](https://github.com/BerriAI/litellm) is an open-source, self-hostable AI gateway. The four configs here make a LiteLLM proxy act as the local gateway of one fictitious organisation each. They are **generated** from `data/network.yaml` and `data/policy.yaml`; do not edit them by hand, run `python -m inferentienet.litellm_config` in `tooling/`.

Tested with **LiteLLM 1.110.3** (see `requirements.txt`). Other versions may behave differently; check the [LiteLLM docs](https://docs.litellm.ai/docs/proxy/tag_routing) for the version you use.

## What is in a config

- One **model group per model class** (`klein`, `middel`, `groot`, `embedding`), pointing at the organisation's own site when it has that class.
- `<class>-federatie` groups for the sites of the other members, and `<class>-extern` groups for the commercial EU site. They are **fallbacks**, tried in that order.
- Every deployment is **tagged with the data classes it may receive**, from the policy and the site's acceptance rules. With `enable_tag_filtering`, a request tagged `bijzonder` can only reach the own site; a fallback that is not allowed fails instead of leaking data.
- Every deployment answers with LiteLLM's `mock_response`: no model runs and no request leaves your machine. The federation deployments point at the Python mock gateways (`/federation/v1` on ports 8101-8104), but are mocked as well.
- Batch-only sites (the research site) are left out: tags here carry only the data class, not the tier.

## Check it without a server

```bash
pip install -r gateways/litellm/requirements.txt
python gateways/litellm/smoke_test.py
```

The smoke test loads the configs in LiteLLM's `Router` and checks: confidential data from the municipalities only reaches federation sites; internal data falls back to the commercial EU site when forced; confidential data does not; `bijzonder` data at the executive agency stays local and fails closed on fallback.

## Run a proxy

The proxy refuses to start without a master key. Generate your own; never commit it.

```bash
export LITELLM_MASTER_KEY="sk-$(openssl rand -hex 16)"
litellm --config gateways/litellm/gemeenten.yaml --port 4004

curl -s localhost:4004/v1/chat/completions \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY" -H 'Content-Type: application/json' \
  -d '{"model": "middel", "messages": [{"role": "user", "content": "hoi"}], "metadata": {"tags": ["vertrouwelijk"]}}'
```

The tag can also be sent as a header, `x-litellm-tags: vertrouwelijk`. To force a fallback for a demo, add `"mock_testing_fallbacks": true` to the body; the configs allow that with `general_settings.dangerously_allow_mock_testing_request_params`, which is for local demos only.

## Two pitfalls we found (LiteLLM 1.110.3)

1. **A request without tags is not filtered.** In our test it reached whatever deployments the requested model group contains, including the commercial site. Put a check in front of LiteLLM that refuses requests without a data class; the LiteLLM documentation describes hooks that may help, verify them for your version. The Python mock gateways refuse such requests.
2. **One matching tag is enough.** A request tagged `["bijzonder", "openbaar"]` reached the commercial site, because `openbaar` matched. Send exactly one tag: the data class.

`smoke_test.py` prints both as NOTE lines, so you can check whether your version behaves the same.

## Going further

- Remove `mock_response` from a federation deployment to let LiteLLM really call a peer's mock gateway. The peer then needs the origin organisation and data class (the Python mock gateway expects them as `X-Origin-Org` and `X-Data-Class` headers); passing those through is a design question for your team.
- Replace a mocked deployment with the GreenPT API to get real answers for public data; see [docs/integrations/greenpt-api.md](../../docs/integrations/greenpt-api.md).
