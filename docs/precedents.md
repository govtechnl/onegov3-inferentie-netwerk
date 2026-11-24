# Precedents and technical anchors

The brief names these precedents. The links are to public sources; check them yourself before you quote them.

| Precedent | Trust model | Routing | Suitable for real-time inference? | Links |
|---|---|---|---|---|
| **BOINC (Berkeley)** | Anonymous volunteers + redundancy | Client "pull", server dispatch scoring | No, batch-oriented (hours/days) | [boinc.berkeley.edu](https://boinc.berkeley.edu) |
| **Slurm federation** | Trusted, independent institutions | Sibling jobs + coordination via the origin cluster | Partly, batch/HPC with throughput limits | [Slurm Federation Guide](https://slurm.schedmd.com/federation.html), [slurm-docker-cluster](https://github.com/giovtorres/slurm-docker-cluster) |
| **SURF/NWO (Rekentijd call)** | Trusted institutions, peer review | Periodic quota allocation | No, budget allocated in advance | See the SURF and NWO websites for the current call |
| **EuroHPC AI Factories** | Trusted EU member states/organisations | Tiered access (Playground, Fast Lane, Large Scale) | Partly | [AI Factories access modes](https://eurohpc-ju.europa.eu/ai-factories/ai-factories-access-modes_en) |
| **OpenRouter (+ LiteLLM, self-hostable)** | Commercial, API key | Real-time hub-and-spoke on data policy, latency and cost | Yes, directly transferable pattern | [OpenRouter provider selection](https://openrouter.ai/docs/guides/routing/provider-selection), [OpenRouter zero data retention](https://openrouter.ai/docs/guides/features/zdr), [LiteLLM](https://github.com/BerriAI/litellm), [LiteLLM tag routing](https://docs.litellm.ai/docs/proxy/tag_routing) |

## Notes

- **OpenRouter and LiteLLM** show how to route within one gateway with filters. OpenRouter's provider preferences include filters such as zero data retention (`zdr`) and `data_collection`, which turn data sensitivity into a routing rule. LiteLLM is open source and self-hostable; the configs in [`gateways/litellm/`](../gateways/litellm/) use its tag filtering for data classes.
- **Slurm federation** is a strong example of a trust model: independent, trusted clusters that use each other's free capacity. It is optional reference material for this challenge, not a building block: it is heavy to set up in two days and aimed at batch work.
- **The AI factory in Groningen** (SURF, TNO, AIC4NL and Samenwerking Noord; installation in 2027, fully operational early 2028) is a Dutch example of shared compute, also for public organisations. It is meant for developing and training AI models, so for inference it is a supplementary source of capacity rather than a blueprint. In the simulated data, `onderzoek-ai` plays a comparable role: cheap batch capacity at night.
- **GOPACS** is the inspiration for approach B; see [market-and-settlement.md](market-and-settlement.md) and [gopacs.eu](https://www.gopacs.eu).
- **FAIR-Compute** ([arXiv 2607.28290](https://arxiv.org/abs/2607.28290)) is the source of the coordination warning; see [coordination.md](coordination.md).
- **Policy background:** the letter to parliament of 19 December 2025 with the Ecorys report ([Kamerstuk 26 643, nr. 1451](https://zoek.officielebekendmakingen.nl/kst-26643-1451.pdf)) states that a federated model with smaller multi-site facilities suffices for AI inference.

## Public GPU cluster traces

If you want real-world peak and trough patterns instead of the simulated demand, see [resources/README.md](../resources/README.md) for links to public traces (Helios, Alibaba, Microsoft Philly). They come from companies and research labs, not from Dutch government; use them for the shape of demand, not as figures for the organisations in the brief.
