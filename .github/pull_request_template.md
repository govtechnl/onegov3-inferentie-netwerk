## Summary

<!-- One paragraph: what does this PR add or change? -->

## Type of contribution

- [ ] **Hackathon team contribution** (optional: your official submission is on Alkemio)
- [ ] Starter-repo improvement (docs, data, tooling, CI)
- [ ] Bug fix
- [ ] Other (describe)

---

## For hackathon team submissions

### Team

- **Team name:**
- **Members:**
- **Folder:** `submissions/<team-name>/`
- **Approach:** [ ] A: federated gateway model [ ] B: market mechanism [ ] Both or own structure

### ✅ Must checklist (jury blocking)

- [ ] **M1** Federated routing concept with internal **and** external routing between at least two of the four roles (an internal AI gateway connected to a central gateway or to the gateways of other organisations). Simulated parts are labelled.
- [ ] **M2** Shown on which criteria a request is routed, and which data are needed from the consumer and from the provider.
- [ ] **M3** The legal or administrative vehicle is named (covenant, joint arrangement, service level agreement), with the reason.
- [ ] **M4** Allocation and settlement for scarce capacity are explicit: who gets priority, and how usage is charged or settled against capacity supplied, for user and provider.
- [ ] **M5** Open source under an OSI-approved licence (code) and CC BY 4.0 or CC0 (rules, docs), with a readable explanation. See [`CONTRIBUTING.md`](../CONTRIBUTING.md#licensing-of-contributions).

### ⭐ Should evidence (linked in the PR body)

- [ ] **S1** Routing decisions are configurable and auditable: why did request X go to location Y?
- [ ] **S2** Governance sketch: who decides, escalation path in case of conflict.
- [ ] **S3** Simple and robust to roll out, install, connect and manage per organisation.

### Hygiene

- [ ] Tests for the routing, priority or settlement rules are included and pass.
- [ ] No real requests, personal data, internal capacity or cost figures, or credentials.
- [ ] Requests without a data classification are refused (fail closed).
- [ ] If an LLM is used: where, why, and which model is described below. It does not make routing, priority or settlement decisions.

### What is simulated

<!-- List every component that is simulated or mocked, and what a real version would need. -->

### Legal or administrative vehicle

<!-- Which vehicle, why, and which questions you discussed with the lawyers. -->

### Reproduction

```bash
# Single command (or short sequence) that runs your prototype from a clean checkout:
```

### Pitch artefacts

- [ ] Pitch deck (max. 10 slides), link or attachment
- [ ] Short explanation of approach, assumptions and limitations, in the PR or the team folder

---

## For starter-repo improvements

- [ ] Data, docs and README updated together.
- [ ] `ruff check .` and `pytest -v` pass locally (`tooling/`).
- [ ] Generated files regenerated if data changed (`python -m inferentienet.demand`, `python -m inferentienet.litellm_config`).
- [ ] CI ([`.github/workflows/validate.yml`](workflows/validate.yml)) is green.
- [ ] Related issue: #
