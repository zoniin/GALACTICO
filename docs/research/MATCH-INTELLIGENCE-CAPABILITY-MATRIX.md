# Match intelligence capability matrix

Corpus availability and current implementation are separate. `DIRECT` means the
source records it, `DERIVABLE` means explicit computation is possible, `RESEARCH`
needs validation, `BRIDGED` requires a validated paired-corpus bridge, `UNAVAILABLE`
means missing required input, and `REJECTED` means the proposed interpretation
does not survive. No bridge is validated or shipped in this pass.

| Capability | Historical Wyscout | Historical StatsBomb (local only) | LIVE aggregate | VISION | Galáctico estimator / status |
|---|---|---|---|---|---|
| Lineups | DIRECT | DIRECT | DIRECT if licensed feed includes them | RESEARCH | Historical starters/subs shipped; no inferred formation |
| Event timeline | DERIVABLE | DERIVABLE | DIRECT at supplied granularity | RESEARCH | KEY / TACTICAL / ALL shipped; period clock preserved |
| Shot map | DIRECT | DIRECT | UNAVAILABLE without coordinates | RESEARCH | Wyscout shots/penalties/free kicks shipped |
| xG / xG flow | UNAVAILABLE | DIRECT in raw shot object | UNAVAILABLE unless supplied | UNAVAILABLE | No Wyscout xG model; StatsBomb raw enrichment not implemented here |
| Player match stats | DERIVABLE | DERIVABLE | DIRECT at supplied granularity | RESEARCH | Counts and named match vectors shipped |
| Player match summary | DERIVABLE | DERIVABLE | RESEARCH | UNAVAILABLE | Vector; season reliability not inherited |
| Passing network | RESEARCH recipient inference | DIRECT recipients in raw feed | UNAVAILABLE | RESEARCH | Shipped with explicit HEURISTIC edges and coverage; volume/xT toggles |
| Event heatmap | DERIVABLE | DERIVABLE | UNAVAILABLE without coordinates | RESEARCH | Pass-origin shares shipped; no tracking heatmap |
| Team spatial profile | DERIVABLE / RESEARCH interpretation | DERIVABLE | RESEARCH / possible Bridge | RESEARCH | Historical pass-origin descriptors shipped, not off-ball structure |
| Threat flow | DERIVABLE | DERIVABLE | UNAVAILABLE without coordinates | RESEARCH | Positive completed-pass xT, five-minute period bins shipped |
| Top performers | RESEARCH | RESEARCH | RESEARCH | UNAVAILABLE | No universal ordering; inspect components |
| Player rating | REJECTED launch candidates | RESEARCH | RESEARCH | UNAVAILABLE | E-05: no overall contribution scalar identified |
| Momentum | REJECTED xT-as-momentum claim | RESEARCH | RESEARCH | RESEARCH | Not shipped |
| Defensive quality | UNAVAILABLE from counts alone | RESEARCH | RESEARCH | RESEARCH | Counts labeled observations; quality unmeasured |

Only public Pappalardo/Wyscout is served. MatchLabService verifies the cached
provider identity and enforces hosting posture; StatsBomb is never a hosted fallback.
FotMob/SofaScore/WhoScored are product benchmarks only, never ingestion paths.
UEFA remains reference-only. [Corpus documentation and CC BY 4.0 license](https://figshare.com/articles/dataset/Events/7770599).
