# Challenge Brief | Overheid Inferentie Netwerk

> **OneGov #3** · Challenge 1 · 9-10 December 2026 · The Hague Tech, Den Haag
>
> *Shared AI compute between government organisations.*
>
> **Put forward by:** Guido Scheuerman (PZH / GovTechNL network / sAIdkick)
> **Challenge owners:** Guido Scheuerman (PZH, main challenge owner, on behalf of the GovTechNL network), Sahin Özaltun (PZH), Melior Hoekstra (Minbzk), Lennart Marijs (Minbzk), Lotte Schipper (Minbzk), Bas Kooistra (VNG), Bas Nijhuis (Belastingdienst, to be confirmed)
> **Contact:** [hack@govtechnl.nl](mailto:hack@govtechnl.nl)

This is an English working translation of the Dutch challenge brief. The authoritative version is the Dutch brief on Alkemio.

*Minbzk, the Belastingdienst, Provincie Zuid-Holland and municipalities (through VNG) want to share AI compute, instead of every organisation sizing for its own peak. Teams build, supported by government lawyers, a prototype of a federated inference network that distributes AI tasks over capacity and models inside and outside government, with attention to data sensitivity, urgency and cost.*

---

## Background

Edition #3 of OneGov is about digital autonomy and sovereignty. From the sAIdkick programme, a question was put forward under the name **overheid inferentie netwerk** (government inference network): a collaboration between Minbzk, the Belastingdienst, Provincie Zuid-Holland and municipalities (through VNG) to share AI compute for inference, instead of every organisation keeping capacity for its own needs.

The core problem: every organisation now sizes for its own peak, which causes structural over-capacity and under-capacity at the same time, "shortage by design". Hardware (GPUs) is also scarce and hard to get, so the point is not buying more but using what is already there more effectively. On top of that, not all data can go to commercial providers: sensitive data should be processed on own infrastructure, while exactly that own capacity is scarce and expensive. The task is therefore to optimise, based on rules, across different kinds of capacity inside and outside government.

This is less unusual than it sounds. With a letter to parliament of 19 December 2025 on AI infrastructure and the AI factory in Groningen ([Kamerstuk 26 643, nr. 1451](https://zoek.officielebekendmakingen.nl/kst-26643-1451.pdf)), the cabinet sent an Ecorys report. According to Ecorys, a federated model with smaller facilities at multiple sites suffices for AI inference. A letter to parliament of 31 March 2026 confirms that line: a large, central AI gigafactory is mainly relevant for training the most advanced models. Digitale Overheid also describes how municipalities, provinces, executive agencies and central government can more often act as one client, for more economies of scale and more control ("Samen inkopen als opstap naar meer digitale autonomie", June 2026).

## Problem statement

Organisations that use AI compute for policy, public services or enforcement run into the same limits:

- How do you route an AI request to the place with free capacity at that moment, between organisations that trust each other but operate separately in organisational and legal terms?
- How do you choose, per task, the right place and the right model, inside or outside government, based on content, size, sensitivity and urgency?
- How do you get insight into GPU occupancy per location, so a task from the backlog can be scheduled at the right moment, similar to how grid operators use insight into grid congestion?
- How do you give priority under scarcity, and to whom, in which situations (for example a time-critical enforcement process versus a batch job that can wait)?
- How do you settle usage (capacity, time, power) in a way that is fair, traceable and accountable? And how do you prevent expensive capacity from being sized for peak demand and standing largely idle the rest of the time?
- How do you make sure sensitive data, such as tax data of the Belastingdienst, never leaves its own column, not even when the underlying compute is shared?

These questions are central to the challenge.

Criteria that could be used for routing and prioritisation include: sensitivity and classification of the data (GDPR/AVG), urgency and type of assignment, type of language model, required and available capacity, and the tariff (fixed or variable).

## The challenge

> *How do we build a prototype of a government inference network in which Minbzk, the Belastingdienst, Provincie Zuid-Holland and municipalities (through VNG):*
>
> - *share AI compute with each other at peak moments, so scarce GPU capacity is used more effectively;*
> - *use an optimal mix of compute inside and outside government;*
> - *use, per task, a foundation model that fits the content and size of that task;*
>
> *without sensitive data leaving its own organisation, and while keeping the decentralised responsibility of every owner of data and task?*

The intended result: assignments are handled as effectively and efficiently as possible within the limits of law and regulation, and the available capacity (compute, models and network) is used optimally. The challenge therefore has both a technical-functional and a contractual-legal side.

## Two possible approaches

| Approach A: federated gateway model (technical) | Approach B: market mechanism (allocation) |
|---|---|
| Design and build a federated gateway model. Every network partner runs at least a local gateway for internal routing and, connected to it, a gateway for external routing to the other partners. Larger government organisations often already have an internal AI gateway: teams can connect to it or design both gateways themselves. Requests go to the place with free capacity, with filters for data sensitivity, urgency, latency and cost. Whether there are external components in the network is up to the team. Inspired by, but not limited to, OpenRouter/LiteLLM and Slurm federation. | Design a prioritisation and settlement model: who gets priority, when, and how usage is charged or settled against capacity supplied, for both user and provider. Inspired by congestion management in the electricity market (categories, capacity limitation contract, GOPACS) and GPU chargeback models with service tiers (Interactive/Batch/Critical). |

Teams choose one approach, combine both, or design their own structure. A working prototype does not have to actually connect all four organisations: a simulated demo environment with realistic scenarios is a valid starting point. This repository contains such an environment to start from.

## Technical anchors and precedents

| Precedent | Trust model | Routing | Suitable for real-time inference? |
|---|---|---|---|
| **BOINC (Berkeley)** | Anonymous volunteers + redundancy | Client "pull", server dispatch scoring | No, batch-oriented (hours/days) |
| **Slurm federation** | Trusted, independent institutions | Sibling jobs + coordination via the origin cluster | Partly, batch/HPC with throughput limits |
| **SURF/NWO (Rekentijd call)** | Trusted institutions, peer review | Periodic quota allocation | No, budget allocated in advance |
| **EuroHPC AI Factories** | Trusted EU member states/organisations | Tiered access speed (Playground/Fast Lane/Large Scale) | Partly |
| **OpenRouter (+ LiteLLM, self-hostable)** | Commercial, API key | Real-time hub-and-spoke on data policy/latency/cost | Yes, directly transferable pattern |

OpenRouter/LiteLLM shows how to set up routing within one gateway, with filters (zdr/data_collection) that turn data sensitivity into a routing rule. Slurm federation is a strong example of a trust model: independent, trusted clusters that use each other's free capacity, instead of BOINC's model of anonymous volunteers. The AI factory in Groningen (SURF, TNO, AIC4NL and Samenwerking Noord; installation in 2027, fully operational early 2028) is a current Dutch example of shared compute, also for public organisations. The system is meant for developing and training AI models, so for inference it is a supplementary source of capacity rather than a blueprint.

A warning from recent research ([FAIR-Compute, arXiv 2607.28290](https://arxiv.org/abs/2607.28290)): when every organisation independently picks the "fastest route", this can come at the expense of the local users at the receiving party and of the stability of the network, by analogy with Braess's paradox. The report therefore argues for coordinated placement rules through a federation broker, such as a minimum gain before a task moves, protection of the receiving party against overload, and a toll on switching. Teams show how their model arranges that coordination: central, federated or hybrid. See [docs/coordination.md](docs/coordination.md).

More background and links: [docs/precedents.md](docs/precedents.md).

## Resources and starting material

GovTechNL provides this starter repository, based on the building blocks below. Teams are free to deviate from it.

**Approach A: federated gateway model**

| Resource | What it is | In this repository |
|---|---|---|
| LiteLLM (open source) | Self-hostable AI gateway with a built-in mock mode | A config per organisation in [gateways/litellm/](gateways/litellm/), with mock responses and data-class tags. Can be tested without real GPUs. |
| Slurm Federation + slurm-docker-cluster | Official federation documentation plus a Docker Compose Slurm cluster | Optional, only as a reference for the trust model. Not needed for a working prototype and heavy to set up in two days. Links in [docs/precedents.md](docs/precedents.md). |
| Federated mock gateways | One OpenAI-compatible gateway per organisation, internal and external routing, explainable decisions | [tooling/](tooling/) (`python -m inferentienet.gateway --all`) |

**Approach B: market mechanism**

| Resource | What it is | In this repository |
|---|---|---|
| GOPACS / TenneT (congestion management in the electricity market) | Data and technical documentation on prioritisation and settlement under grid congestion | Source of inspiration for the bidding model; see the public explanation at [gopacs.eu](https://www.gopacs.eu). |
| Market mechanism mock API | Simplified, GOPACS-inspired API (priority tiers, bids, settlement) | [tooling/](tooling/) (`python -m inferentienet.market_api`), described in [docs/api/market-mock.openapi.yaml](docs/api/market-mock.openapi.yaml) |

**Shared: demand data and standards**

| Resource | What it is | In this repository |
|---|---|---|
| Public GPU cluster traces (such as Helios, Alibaba, Microsoft Philly) | Realistic peak and trough patterns in GPU use, as CSV | Simulated demand for four fictitious organisations is in [data/demand/](data/demand/). Public traces can be used as an alternative; links in [resources/](resources/README.md). |
| GreenPT API (tech partner) | OpenAI-compatible API with credits per participant | Usable to simulate AI requests; no built-in multi-organisation quota, a team builds that on top. See [docs/integrations/greenpt-api.md](docs/integrations/greenpt-api.md). |

All data in the repository is simulated or public. No real requests, data or capacity figures of the organisations involved pass through the network.

## Deliverables

- A working prototype or demo of the federated network, with an explicit label on which part is simulated.
- The routing, prioritisation and settlement rules as readable configuration or code.
- A short explanation of approach, assumptions and limitations, including the legal or administrative vehicle that would be needed.
- The source code, published open source via GitHub.
- A pitch (max. 3 minutes) and a pitch deck (max. 10 slides).

## Judging criteria

Teams are judged by an expert jury with expertise in government architecture, inter-governmental collaboration and AI infrastructure. Four levels:

### ✅ Must: minimum requirements for a valid submission

- The prototype shows a federated routing concept with internal **and** external routing between at least two of the four roles: an internal AI gateway (existing or self-built) connected to a central gateway or to the gateways of other organisations. Which part is simulated is labelled explicitly.
- The prototype shows on which criteria a request is routed, and which data are needed for that from both the consumer and the provider.
- The team names concretely which legal/administrative vehicle (covenant, joint arrangement, service level agreement) would be needed, and why.
- An allocation and settlement mechanism for scarce capacity is made explicit: who gets priority, and how usage is charged or settled against capacity supplied, for both the using and the providing party. A worked-out design suffices.
- The solution is open source and contains a readable explanation of the approach.

### ⭐ Should: distinguishing qualities

- Routing decisions are flexibly configurable and auditable: why did request X go to location Y?
- A governance sketch: who decides, and what the escalation path is in case of conflict.
- Simplicity and robustness: the federated model is easy to roll out, install, connect and manage in a decentralised way.

### ⚠ Should not: pitfalls to avoid

- Pretending the legal framework already exists, or reasoning the problem away.
- A purely technical demo without an administrative layer, or the other way round a purely policy document without a working element.
- Leaving the allocation mechanism implicit.
- Suggesting a live connection that is actually simulated, without saying so.

### ✨ Could: bonus

- Alignment with international interoperability frameworks, such as the legal, organisational, semantic and technical layers of the European Interoperability Framework.
- A concrete settlement model including token usage.
- A scaling perspective towards more than the four organisations named.

The criteria with IDs (M1 to M5, S1 to S3, X1 to X4, C1 to C3) are in [docs/judging-criteria.md](docs/judging-criteria.md).

## Preconditions

**Infrastructure and energy.** Grid congestion in Zuid-Holland is confirmed: the high-voltage grid has reached its maximum capacity in a large part of the province (Randstedelijke Rekenkamer, 2025). Modern AI hardware also needs much more power and cooling per rack than most existing data centres can handle, and GPUs are scarce. Spreading over several physical locations with different infrastructure reduces vulnerability. That fits the report "Het Rijk in de cloud" of the Algemene Rekenkamer (January 2025): a large part of central government's cloud services is bought from Amazon, Microsoft and Google, and the Rekenkamer calls for weighing alternatives more deliberately and acting as one collaborating government.

**Legal (first exploration, still to be reviewed by the lawyers).** There is no ready-made framework for this combination of a ministry, an executive agency, a province and municipalities. Participation of central government (Minbzk) in a joint arrangement with a province and municipalities is possible, but requires a Royal Decree. A covenant under the existing GDI governance is the more common route. Fiscal secrecy (art. 67 AWR) mainly concerns sharing data, not necessarily the compute itself, provided there is real technical separation. Procurement law has usable exceptions for public-public cooperation (art. 2.24c Aanbestedingswet, art. 25h Wet Markt en Overheid). No existing framework law was found that specifically regulates infrastructure sharing between layers of government. That is a legal gap, and at the same time an interesting insight for the hackathon: the challenge itself could produce a proposal for such a framework arrangement. See the annex for the full picture and the legal expertise needed. During the hackathon, lawyers of the organisations involved walk around the teams to think along about the legal side and help them further. The lawyers prepare together beforehand in a separate meeting.

More in [docs/legal-context.md](docs/legal-context.md).

## Annex: legal expertise needed

A first exploration, not yet legally reviewed, points to five areas of law that are normally handled separately.

1. **Inter-governmental cooperation law / administrative law.** How Minbzk, the province and municipalities can cooperate legally (Wet gemeenschappelijke regelingen, covenants, GDI governance), and whether central government participation requires a Royal Decree.
2. **Tax law / fiscal secrecy.** The scope of art. 67 AWR at the Belastingdienst, and whether a separate legal basis is needed along the lines of the Wet gegevensverwerking door samenwerkingsverbanden (Wgs).
3. **Procurement law.** Whether and how joint purchasing or shared infrastructure can stay outside the obligation to tender (public-public cooperation, Wet Markt en Overheid).
4. **Privacy law (GDPR/AVG).** Joint controllership between several government organisations for a shared AI system.
5. **IT/AI law.** EU AI Act obligations and BIO2 security requirements for shared, multi-tenant infrastructure.

## Submission

Submissions go through **Alkemio**, the central submission and review platform for OneGov. The link to the challenge space follows.

Each team submits, via Alkemio:

1. A **link to the team's Pull Request** on this repository, one PR per team (see [CONTRIBUTING.md](CONTRIBUTING.md)).
2. A **short explanation** of approach, assumptions and limitations, including the legal or administrative vehicle.
3. The **pitch deck** (max. 10 slides, PDF or link).

The Alkemio submission is what the jury scores during the hackathon. The Pull Request is still required: it holds the open source code and rules.

## Disclaimer

The prototypes and designs produced during this hackathon are published as open source. The challenge is an innovation exercise: outcomes are not legal advice and not a decision or position of the organisations involved.

Questions about the hackathon: [hack@govtechnl.nl](mailto:hack@govtechnl.nl)
