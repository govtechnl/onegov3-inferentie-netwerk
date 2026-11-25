# Judging criteria

How the expert jury, with expertise in government architecture, inter-governmental collaboration and AI infrastructure, weighs submissions. Four levels: **Must**, **Should**, **Should not**, **Could**. The criteria are those of the challenge brief; the IDs and the right-hand column are added in this repository to help teams, they are not a description of the jury's procedure.

A submission that fails any Must criterion is not a valid submission, regardless of how well it scores on the rest.

## ✅ Must: minimum requirements for a valid submission

| # | Criterion | What makes it visible |
|---|---|---|
| M1 | A federated routing concept with internal **and** external routing between at least two of the four roles: an internal AI gateway (existing or self-built) connected to a central gateway or to the gateways of other organisations. Which part is simulated is labelled explicitly. | A demo or recording of a request that stays local and one that goes to another organisation; a list of what is simulated |
| M2 | The prototype shows on which criteria a request is routed, and which data are needed from both the consumer (afnemer) and the provider (aanbieder). | A table or schema of request data and published provider data; see [routing-criteria.md](routing-criteria.md) |
| M3 | The team names concretely which legal or administrative vehicle (covenant, joint arrangement, service level agreement) would be needed, and why. | A short motivation, linked to the technical design; see [legal-context.md](legal-context.md) |
| M4 | An allocation and settlement mechanism for scarce capacity is explicit: who gets priority, and how usage is charged or settled against capacity supplied, for both the using and the providing party. A worked-out design suffices. | Rules in configuration or code, or a worked-out design; see [market-and-settlement.md](market-and-settlement.md) |
| M5 | The solution is open source and contains a readable explanation of the approach. | Public repository, linked in Alkemio, under an OSI-approved licence (code) and CC BY 4.0 or CC0 (rules, docs) |

## ⭐ Should: distinguishing qualities

| # | Criterion | What it looks like |
|---|---|---|
| S1 | Routing decisions are flexibly configurable and auditable: why did request X go to location Y? | Changing a rule file changes the outcome; every decision has an explanation |
| S2 | A governance sketch: who decides, and what the escalation path is in case of conflict. | Roles, decision rights and an escalation path, for example for changing tariffs or thresholds |
| S3 | Simplicity and robustness: the federated model is easy to roll out, install, connect and manage in a decentralised way. | A new member connects with one configuration; a member that drops out does not break the rest |

## ⚠ Should not: pitfalls to avoid

| # | Pitfall | Why it weakens a submission |
|---|---|---|
| X1 | Pretending the legal framework already exists, or reasoning the problem away | The legal gap is part of the challenge; see M3 |
| X2 | A purely technical demo without an administrative layer, or a purely policy document without a working element | The challenge asks for both sides |
| X3 | Leaving the allocation mechanism implicit | Violates M4 |
| X4 | Suggesting a live connection that is actually simulated, without saying so | Violates the labelling in M1; the jury cannot judge what is real |

## ✨ Could: bonus for outstanding submissions

| # | Bonus | Evidence |
|---|---|---|
| C1 | Alignment with international interoperability frameworks, such as the legal, organisational, semantic and technical layers of the European Interoperability Framework | The design described per layer |
| C2 | A concrete settlement model including token usage | Tariffs per token or per model class, worked out on a scenario |
| C3 | A scaling perspective towards more than the four organisations named | How a fifth or fiftieth member joins, and what changes in governance and settlement |

## How judging works

Musts are pass or fail. Teams pitch per challenge in a first round (10 December, 14:00-15:00), a technical jury reviews every submission in Alkemio, and the best team per challenge goes to the final, where the grand jury scores six criteria from 1 to 5. See [EVENT.md](../EVENT.md#how-judging-works).
