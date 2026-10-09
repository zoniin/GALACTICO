# Architecture

## Layers

The tree below is the long-term module map, not a completeness claim. `bridge`,
VISION, learned role fit, embeddings and opponent utility remain research/stubs.

```

## Implemented historical decision path

`api/player_lab.py` serves the frozen Player Lab and registers `api/decision_lab.py`.
This path renders three code-native pages under `web/` (the planning path below
adds two); JavaScript presents server decisions and never computes eligibility,
coverage or an objective.

| Module | Responsibility |
|---|---|
| `profiles/` | Versioned season estimates, gates and shared-match uncertainty |
| `match_lab/service.py` | Public Pappalardo-only loading, retained provider tags, retrospective xT and file hashes |
| `match_lab/model.py` | Provider-neutral `MatchIntelligence`: timelines, shot locations, positive pass-xT flow, inferred networks and contribution vectors |
| `optimization/historical.py` | Strict prior-date snapshot, independent pre-cutoff xT fit, versioned eligibility, heuristic minima and coherent team-match worlds |
| `optimization/xi/domain.py` | Typed candidates, role-slot templates, requirements, assessments and `XIResult` |
| `optimization/xi/solver.py` | Exact quantized CP-SAT; lexicographic deficits, certification, tie-aware membership, removal and candidate-injection re-solves |

`GET /api/matches` and `/api/matches/{id}` expose the historical match artifacts;
`/{id}/{timeline,shots,network,players,flow,teams}` expose individual sections.
`GET /api/xi/scenarios`, `POST /api/xi/solve` and `POST /api/xi/sensitivity`
serve the decision model. There is no persistent XI store or separate explain
service: the solve returns the contributions, requirements, changes and provenance.

Match Lab's full-season xT is retrospective and cannot feed a historical decision
backtest. XI snapshots refit only on earlier calendar dates. All world inputs,
requirement inputs, formation rules, solver versions and seeds enter provenance;
missing exposure stays missing. Necessary–possible membership bounds include
equivalent optima; a deterministic displayed XI does not resolve those ties.

Opponent conditioning is designed to change requirements, not player ratings.
Only its descriptive team inputs exist. Candidate injection is a transfer
foundation, not a validated recruitment ranking. No universal utility, overall
match rating, learned role adjustment or robust-risk product mode is implemented.
providers/   adapters; provider quirks terminate here
ingestion/   raw -> provider-neutral schema -> Parquet
storage/     DuckDB over Parquet, three tiers kept apart
features/    quality / style / spatial / physical / team
reliability/ the gate; runs before axes are designed
models/      xt, embeddings, role_fit, similarity, complementarity, opponent
bridge/      LIVE aggregates -> LAB axes, with measured error
optimization/xi, squad, transfers, sensitivity
vision/      calibration, detection, tracking, projection, shape
validation/  pre-registered experiments and baselines
api/         FastAPI over prepared state
```

## Implemented planning path

Squad Lab and Transfer Lab stand beside the historical decision path and edit none
of it. `historical.py`, the XI solver and the xT grid are imported from, never
changed: their bytes are hashed into published experiment results.

| Module | Responsibility |
|---|---|
| `storage/public.py` | The one guarded reader of the public frames: hosting guard first, provider column checked, explicit files only |
| `optimization/snapshots.py` | Pre-decision snapshot for any club and decision match or cutoff date under a named eligibility rule set; byte parity with `historical.build_snapshot` for Madrid; `TEAM_MATCHES` or `LEAGUE_MATCHES` worlds |
| `optimization/reference.py` | League distributions of starting-XI requirement sums before a cutoff (descriptive) |
| `optimization/squad/kernel.py` | The exact lexicographic shortfall as a linear epigraph; the same integers as `solve_xi`; conservative floor/ceil for hard statements |
| `optimization/squad/depth.py`, `stress.py`, `brief.py` | Slot depth with attributed drops; exact k-absence stress; the role brief (inverse problem per slot) |
| `optimization/transfers/universe.py`, `injection.py`, `retention.py` | Gated candidate universe; exact forced-inclusion re-solves; the break-even carry-over fraction |
| `domain/evidence.py` | The one mapping from shipped vocabularies to `EvidenceClass`, and composition by the weakest |
| `domain/verdicts.py` | One typed record per preregistered claim; a LOCAL-tier record can label, never gate. Ships empty |
| `domain/thesis.py` | Walks any payload for rating-like keys by exact key |
| `api/runtime.py` | How every new request runs: error mapping, server-owned budgets, result cache with single-flight, the boundary check `finalize`, NaN-free responses |
| `api/shell.py` | What every new page shows: navigation, the not-measured list, evidence and verdict payloads, the copy guard `scan_labels` |
| `api/planning.py`, `squad_lab.py`, `transfer_lab.py` | The declared planning problem and the two lab routers |

Every new response passes `runtime.finalize`: the provider set at any depth of the
payload must be exactly the hosted one, and no key may read like a rating. Every
served label passes `shell.scan_labels`: a word such as "best", "weakness" or
"forecast" may appear only inside a named denial. Product code imports nothing
from `galactico.validation` or `experiments`; `tests/test_research_firewall.py`
parses the imports.

`GET /api/evidence/verdicts` returns the registry. `/squad` and `/transfer` and
their endpoints are listed in the routers. The frontend computes nothing about
football; `web/labs-shared.js` and `web/planning.js` are render functions over
server payloads.

## The provenance core

`galactico.domain.provenance` holds the project's defining abstraction.
`MetricResult` carries value, evidence class, uncertainty, sample size,
reliability and a provenance DAG, and arithmetic propagates all of them.

Three laws, each covered by property tests:

1. **Composition never strengthens.** `(a + b).evidence >= max(a, b)`. No
   sequence of operations can turn a prediction into an observation.
2. **Correlation is preserved where it is known.** Two results carrying draws from
   the same bootstrap replicate set combine element-wise. Different replicate sets
   fall back to quadrature and record `independence-assumed`, because for football
   metrics derived from the same events that assumption is usually false.
3. **Precision follows the uncertainty.** `render()` derives decimal places from
   the standard deviation. Quoting 78.43 when the sd is 6 is a lie about
   precision and is not reachable through the public API.

`explain()` returns value, evidence, grade, reliability, sample size, assumptions
and the full lineage. The question "where did this number come from" always has a
complete answer.

## Comparability

`MetricDefinition.comparable_across` declares which providers may be pooled for a
given metric; `assert_comparable` raises otherwise. Definitions are
content-addressed over formula, inputs and normalisation, so changing what is
computed changes the version hash and invalidates stored results.

## Data tiers

`PUBLIC` may be hosted and is what the demo runs on. `LOCAL_LICENSED` is
downloaded at runtime into a gitignored cache and never served. `TRIAL` is
time-boxed and never a dependency. `assert_may_host` and `assert_may_commit`
enforce it in code; `scripts/check_licensing.py` enforces it in CI.

## Storage

DuckDB over Parquet. Read-heavy analytical workload, one writer, no server to run
or back up. Partitioned by competition-season and provider, because those are the
boundaries that matter for both queries and licensing.

## Testing

Eight categories, and one of them behaves differently from the rest.

| Category | Fails the build? |
|---|---|
| Unit, data/schema, statistical, regression, solver, leakage, licensing | yes |
| Research acceptance | **no** |

A research acceptance test asks whether a model beats its baseline. When it does
not, the model is wrong, not the code. Those are marked `@pytest.mark.research`
and reported separately: a null result is an output, and a build that goes red
because reality disagreed with a hypothesis trains you to stop asking.

