# Resources

Source material for the challenge.

| What | Status |
|---|---|
| Challenge brief (Dutch, authoritative) | [OneGov3_Challenge_Brief_Overheid_Inferentie_Netwerk.pdf](OneGov3_Challenge_Brief_Overheid_Inferentie_Netwerk.pdf), also on [Alkemio](https://alkem.io/onegov-hackathon) |
| English working translation | [CHALLENGE.md](../CHALLENGE.md) |

## Public GPU cluster traces

For teams that want real-world peak and trough patterns instead of the simulated demand in [`data/demand/`](../data/demand/). These traces come from companies and research labs, not from Dutch government. Check each licence before you use or redistribute data, and do not commit large trace files to this repository.

| Trace | What it is | Link |
|---|---|---|
| Helios (SenseTime) | Jobs from four GPU clusters over six months | [S-Lab-System-Group/HeliosData](https://github.com/S-Lab-System-Group/HeliosData) |
| Alibaba GPU trace (v2023) | GPU cluster trace, CSV | [alibaba/clusterdata, cluster-trace-gpu-v2023](https://github.com/alibaba/clusterdata/tree/master/cluster-trace-gpu-v2023) |
| Microsoft Philly | Jobs and per-minute GPU utilisation, with a parsing notebook | [msr-fiddle/philly-traces](https://github.com/msr-fiddle/philly-traces) |

## Standards that may help

| Standard | Why | Link |
|---|---|---|
| NLgov API Design Rules | Design rules for government APIs, for example for a status or market API | [logius-standaarden.github.io/API-Design-Rules](https://logius-standaarden.github.io/API-Design-Rules/) |
| Algoritmeregister | Public register of government algorithms, with a machine-readable standard; useful if your design registers routing rules | [algoritmes.overheid.nl](https://algoritmes.overheid.nl) |
