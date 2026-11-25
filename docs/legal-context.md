# Legal and administrative context (M3)

> A first exploration from the challenge brief, **not yet reviewed by lawyers and not legal advice**. During the hackathon, lawyers of the organisations involved walk around the teams to think along about the legal side. They prepare together beforehand in a separate meeting. Use them. Which lawyers join, and at what times, is still to be confirmed; it will be announced on [Alkemio](https://alkem.io/onegov-hackathon).

Must criterion M3 asks teams to name concretely **which legal or administrative vehicle would be needed, and why**. Should-not criterion X1 warns against pretending the legal framework already exists, or reasoning the problem away.

## The starting point in the brief

- There is no ready-made framework for this combination of a ministry, an executive agency, a province and municipalities.
- Participation of central government (Minbzk) in a joint arrangement with a province and municipalities is possible, but requires a Royal Decree. A covenant under the existing GDI governance is the more common route.
- Fiscal secrecy (art. 67 AWR) mainly concerns sharing data, not necessarily the compute itself, provided there is real technical separation.
- Procurement law has usable exceptions for public-public cooperation (art. 2.24c Aanbestedingswet, art. 25h Wet Markt en Overheid).
- No existing framework law was found that specifically regulates infrastructure sharing between layers of government. That is a gap, and an opportunity: the challenge itself could produce a proposal for such a framework arrangement.

## Possible vehicles named in the brief

| Vehicle | In one line | Questions to work out |
|---|---|---|
| Covenant (convenant) | Agreement between the parties, for example under the existing GDI governance | How binding is it? Who settles disputes? Does it cover data processing and liability? |
| Joint arrangement (gemeenschappelijke regeling) | A formal cooperation body under the Wet gemeenschappelijke regelingen | What does central government participation require? Is a new public body proportionate for this? |
| Service level agreement (dienstverleningsovereenkomst) | One party delivers compute as a service to others | Who is the provider, and how does that relate to procurement law and the Wet Markt en Overheid? |

Teams may also propose something else, including the framework arrangement the brief mentions. Say why it fits your technical design: a central broker, a federation of equal gateways and a market each ask for different agreements.

## Five areas of law (annex of the brief)

1. **Inter-governmental cooperation law / administrative law.** How the ministry, the province and municipalities can cooperate legally (Wet gemeenschappelijke regelingen, covenants, GDI governance), and whether central government participation requires a Royal Decree.
2. **Tax law / fiscal secrecy.** The scope of art. 67 AWR, and whether a separate legal basis is needed along the lines of the Wet gegevensverwerking door samenwerkingsverbanden (Wgs).
3. **Procurement law.** Whether and how joint purchasing or shared infrastructure can stay outside the obligation to tender (public-public cooperation, Wet Markt en Overheid).
4. **Privacy law (GDPR/AVG).** Joint controllership between several government organisations for a shared AI system.
5. **IT/AI law.** EU AI Act obligations and BIO2 security requirements for shared, multi-tenant infrastructure.

## How the technical design touches the legal questions

| Design choice | Legal question it raises |
|---|---|
| A request runs on another member's site | Who is controller and who is processor? Is a processing agreement needed per pair of members, or one for the federation? |
| `bijzonder` never leaves its own organisation | Is technical separation enough for fiscal secrecy, or is a legal basis needed anyway? |
| A central broker sees all requests and loads | What may the broker see? Is the broker itself a processor? |
| Members pay each other for capacity | Is that a public contract? Does the public-public exception apply? Are the tariffs cost-based? |
| A commercial EU provider takes `openbaar` and `intern` work | Which contract terms (EU jurisdiction, zero data retention, no training) are needed, and how are they verified? |
| Routing decisions are logged and explained | Retention periods, transparency obligations, and use of the logs in case of a dispute. |

Write down which of these your design raises, what you assume, and what you asked the lawyers.
